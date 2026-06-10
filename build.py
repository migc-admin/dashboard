#!/usr/bin/env python3
"""
MIGC Dashboard build script
Reads both Excel files and generates data.js.
Also migrates index.html to load data.js externally (one-time, idempotent).

Usage:
    python3 build.py
"""

import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("Missing dependency: run  pip3 install pandas openpyxl")

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent
SEASON_XL  = ROOT / "MIGC_Season_Dashboard.xlsx"
HIST_XL    = ROOT / "MIGC_All_Years_Master.xlsx"
DATA_JS    = ROOT / "data.js"
INDEX_HTML = ROOT / "index.html"

# ── Helpers ─────────────────────────────────────────────────────────────────

def clean_str(v):
    """Return None for NaN/nan/empty, else stripped string."""
    if pd.isna(v):
        return None
    s = str(v).strip()
    return None if s in ("", "nan", "—", "-") else s

def clean_int(v):
    if pd.isna(v):
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        s = str(v).strip()
        return None if s in ("", "nan", "TBD", "—", "-") else int(float(s))

def clean_float(v):
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        s = str(v).strip().replace("$", "").replace(",", "")
        return None if s in ("", "nan") else float(s)

def clean_payout(v):
    """Strip $ and commas, return float or 0."""
    if pd.isna(v):
        return 0.0
    s = str(v).strip().replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0

def fmt_date(v):
    """Convert Excel date to 'Jan 31, 2026' format."""
    if pd.isna(v):
        return str(v)
    if hasattr(v, "strftime"):
        # %-d = no-pad day on macOS/Linux
        try:
            return v.strftime("%b %-d, %Y")
        except ValueError:
            return v.strftime("%b %d, %Y").replace(" 0", " ")
    # Already a string
    return str(v).strip()

def placement_from_category(cat):
    """Derive numeric placement string from historical category name."""
    c = str(cat).lower()
    if "1st" in c:
        return "1"
    if "2nd" in c:
        return "2"
    if "3rd" in c:
        return "3"
    return "Winner"

def js_block(name, value, *, is_set=False):
    """Render a const declaration as a JS block."""
    if is_set:
        members = json.dumps(value, ensure_ascii=False)
        # Strip outer [] and wrap in Set()
        inner = members[1:-1]
        return f"const {name} = new Set([{inner}]);\n"
    serialized = json.dumps(value, indent=2, ensure_ascii=False)
    return f"const {name} = {serialized};\n"

# ── Read Season Dashboard ────────────────────────────────────────────────────

print("Reading MIGC_Season_Dashboard.xlsx …")
xl_s = pd.read_excel(SEASON_XL, sheet_name=None, dtype=str)

# PLAYERS ─────────────────────────────────────────────────────────────────────
players_raw = pd.read_excel(SEASON_XL, sheet_name="Players")
PLAYERS = []
for _, r in players_raw.iterrows():
    PLAYERS.append({
        "id":     int(r["Player_ID"]),
        "name":   str(r["Player_Name"]).strip(),
        "status": str(r["Status"]).strip(),
        "team":   str(r["TGL Team"]).strip() if pd.notna(r["TGL Team"]) else "None",
    })

# TOURNAMENTS ─────────────────────────────────────────────────────────────────
tourns_raw = pd.read_excel(SEASON_XL, sheet_name="Tournament_Info")
TOURNAMENTS = []
for _, r in tourns_raw.iterrows():
    TOURNAMENTS.append({
        "id":     str(r["Tournament_ID"]).strip(),
        "name":   str(r["Tournament_Name"]).strip(),
        "date":   fmt_date(r["Date"]),
        "course": str(r["Course"]).strip(),
        "tgl":    str(r["TGL Event"]).strip().lower() == "yes",
    })

# RESULTS + TGL_PARTICIPANTS ──────────────────────────────────────────────────
results_raw = pd.read_excel(SEASON_XL, sheet_name="Tournament_Results")
RESULTS = []
TGL_PARTICIPANTS = {}

for _, r in results_raw.iterrows():
    tid = str(r["Tournament ID"]).strip()
    RESULTS.append({
        "tid":    tid,
        "pid":    clean_int(r["Player ID"]),
        "player": str(r["Player"]).strip(),
        "flight": str(r["Flight"]).strip() if pd.notna(r["Flight"]) else None,
        "hcp":    clean_int(r["Handicap"]),
        "gross":  clean_int(r["Gross"]),
        "net":    clean_int(r["Net"]),
        "f9":     clean_int(r["Front 9"]),
        "b9":     clean_int(r["Back 9"]),
        "putts":  clean_int(r["Putts"]),
    })
    # Collect TGL opt-ins
    if str(r.get("TGL Player", "")).strip() == "Yes":
        TGL_PARTICIPANTS.setdefault(tid, []).append(str(r["Player"]).strip())

# ACHIEVEMENTS ────────────────────────────────────────────────────────────────
ach_raw = pd.read_excel(SEASON_XL, sheet_name="Tournament_Acheivements")
ACHIEVEMENTS = []
for _, r in ach_raw.iterrows():
    pl_raw = r["Placement"]
    if pd.isna(pl_raw):
        pl = "Winner"
    elif str(pl_raw).strip() == "Winner":
        pl = "Winner"
    else:
        pl = str(int(float(str(pl_raw).strip())))
    ACHIEVEMENTS.append({
        "tid":    str(r["Tournament ID"]).strip(),
        "pid":    clean_int(r["Player ID"]),
        "player": str(r["Player"]).strip(),
        "cat":    str(r["Category"]).strip(),
        "pl":     pl,
        "amt":    clean_float(r["Amount"]) or 0.0,
    })

# SKINS ───────────────────────────────────────────────────────────────────────
skins_raw = pd.read_excel(SEASON_XL, sheet_name="Tournament_Skins")
SKINS = []
for _, r in skins_raw.iterrows():
    SKINS.append({
        "tid":    str(r["Tournament ID"]).strip(),
        "pid":    clean_int(r["Player ID"]),
        "player": str(r["Player"]).strip(),
        "cat":    str(r["Category"]).strip(),
        "total":  clean_int(r["Total"]) or 0,
        "amt":    clean_float(r["Amount"]) or 0.0,
    })

# ── Read Historical Master ───────────────────────────────────────────────────

print("Reading MIGC_All_Years_Master.xlsx …")

# MAIN (historical achievements) ──────────────────────────────────────────────
main_raw = pd.read_excel(HIST_XL, sheet_name="Main Results")
MAIN = []
for _, r in main_raw.iterrows():
    cat = str(r["Category"]).strip() if pd.notna(r["Category"]) else ""
    MAIN.append({
        "year":          str(int(float(str(r["Year"])))) if pd.notna(r["Year"]) else None,
        "tournament_id": str(r["Tournament ID"]).strip(),
        "category":      cat,
        "player":        str(r["Player"]).strip() if pd.notna(r["Player"]) else None,
        "flight":        clean_str(r["Flight"]),
        "gross":         clean_str(r["Gross"]),
        "net":           clean_str(r["Net"]),
        "placement":     (str(int(float(str(r["Placement"])))).strip()
                          if pd.notna(r.get("Placement")) and str(r.get("Placement","")).strip() not in ("", "Winner", "nan")
                          else "Winner"),
        "payout":        clean_payout(r["Payout"]),
    })

# HIST_SKINS ───────────────────────────────────────────────────────────────────
hist_skins_raw = pd.read_excel(HIST_XL, sheet_name="Skins")
HIST_SKINS = []
for _, r in hist_skins_raw.iterrows():
    HIST_SKINS.append({
        "year":          str(int(float(str(r["Year"])))) if pd.notna(r["Year"]) else None,
        "tournament_id": str(r["Tournament ID"]).strip(),
        "category":      str(r["Category"]).strip() if pd.notna(r["Category"]) else None,
        "player":        str(r["Player"]).strip() if pd.notna(r["Player"]) else None,
        "flight":        clean_str(r["Flight"]),
        "skins":         clean_int(r["Skins"]) or 0,
        "payout":        clean_payout(r["Payout"]),
    })

# HIST_TOURNAMENTS ─────────────────────────────────────────────────────────────
hist_tourns_raw = pd.read_excel(HIST_XL, sheet_name="Tournament Reference")
HIST_TOURNAMENTS = []
for _, r in hist_tourns_raw.iterrows():
    # Skip summary/header rows — must be a 4-digit year >= 2000
    try:
        yr = int(float(str(r["Year"])))
        if yr < 2000:
            continue
    except (ValueError, TypeError):
        continue
    HIST_TOURNAMENTS.append({
        "tournament_id": str(r["Tournament ID"]).strip(),
        "year":          str(int(float(str(r["Year"])))) if pd.notna(r["Year"]) else None,
        "number":        str(r["Tournament #"]).strip() if pd.notna(r["Tournament #"]) else None,
        "course":        str(r["Course / Venue"]).strip() if pd.notna(r["Course / Venue"]) else None,
        "notes":         clean_str(r["Notes"]),
    })

# ── Merge 2026 into historical arrays ────────────────────────────────────────

# MAIN ← 2026 ACHIEVEMENTS
for a in ACHIEVEMENTS:
    # Derive flight from category (e.g. "Flight A - Overall" → "A")
    flight = None
    if "Flight A" in a["cat"]:
        flight = "A"
    elif "Flight B" in a["cat"]:
        flight = "B"
    MAIN.append({
        "year":          "2026",
        "tournament_id": a["tid"],
        "category":      a["cat"],
        "player":        a["player"],
        "flight":        flight,
        "gross":         None,
        "net":           None,
        "placement":     a["pl"],
        "payout":        a["amt"],
    })

# HIST_SKINS ← 2026 SKINS
for s in SKINS:
    flight = None
    if "Flight A" in s["cat"]:
        flight = "A"
    elif "Flight B" in s["cat"]:
        flight = "B"
    HIST_SKINS.append({
        "year":          "2026",
        "tournament_id": s["tid"],
        "category":      s["cat"],
        "player":        s["player"],
        "flight":        flight,
        "skins":         s["total"],
        "payout":        s["amt"],
    })

# HIST_TOURNAMENTS ← 2026 TOURNAMENTS (only those with results)
completed_tids = {r["tid"] for r in RESULTS}
for i, t in enumerate(TOURNAMENTS, 1):
    if t["id"] not in completed_tids:
        continue
    HIST_TOURNAMENTS.append({
        "tournament_id": t["id"],
        "year":          "2026",
        "number":        str(i),
        "course":        t["course"],
        "notes":         None,
    })

# Sort all three by year then tournament_id
MAIN.sort(key=lambda r: (r["year"] or "", r["tournament_id"] or ""))
HIST_SKINS.sort(key=lambda r: (r["year"] or "", r["tournament_id"] or ""))
HIST_TOURNAMENTS.sort(key=lambda r: (r["year"] or "", r["tournament_id"] or ""))

# HIST_GUESTS (manually maintained — add names here as needed) ─────────────────
HIST_GUESTS = [
    "Mat Vigil", "Jeff Carey", "Jason Payton", "Med Baheta", "Lucas Bouloy",
    "Brian Anderson", "Gary Ryback",
    "Young Park", "Ryo Higurashi", "Ted Setvanpour", "Gary Molina",
    "Robert Siemienczuk", "Charles Figueroa",
]

# ── Write data.js ────────────────────────────────────────────────────────────

print(f"Writing {DATA_JS} …")
lines = [
    f"// Generated by build.py — do not edit manually\n",
    "\n",
    "// ── Historical ────────────────────────────────────────────────────────────────\n",
    "\n",
    js_block("HIST_GUESTS", HIST_GUESTS, is_set=True),
    "\n",
    js_block("MAIN", MAIN),
    "\n",
    js_block("HIST_SKINS", HIST_SKINS),
    "\n",
    js_block("HIST_TOURNAMENTS", HIST_TOURNAMENTS),
    "\n",
    "// ── 2026 Season ───────────────────────────────────────────────────────────────\n",
    "\n",
    js_block("PLAYERS", PLAYERS),
    "\n",
    js_block("TOURNAMENTS", TOURNAMENTS),
    "\n",
    js_block("TGL_PARTICIPANTS", TGL_PARTICIPANTS),
    "\n",
    js_block("RESULTS", RESULTS),
    "\n",
    js_block("ACHIEVEMENTS", ACHIEVEMENTS),
    "\n",
    js_block("SKINS", SKINS),
    "\n",
]

DATA_JS.write_text("".join(lines), encoding="utf-8")
print(f"  ✓  {len(PLAYERS)} players, {len(TOURNAMENTS)} tournaments, "
      f"{len(RESULTS)} results, {len(ACHIEVEMENTS)} achievements, "
      f"{len(SKINS)} skins rows")
print(f"  ✓  {len(MAIN)} historical rows, {len(HIST_SKINS)} historical skins, "
      f"{len(HIST_TOURNAMENTS)} historical tournaments")

# ── Migrate index.html (one-time, idempotent) ────────────────────────────────

html = INDEX_HTML.read_text(encoding="utf-8")

if '<script src="data.js">' in html:
    print("index.html already migrated — skipping.")
else:
    print("Migrating index.html to load data.js externally …")

    # Variables whose inline declarations will be stripped from the HTML.
    DATA_VARS = {
        "HIST_GUESTS", "MAIN", "HIST_SKINS", "HIST_TOURNAMENTS",
        "PLAYERS", "TOURNAMENTS", "TGL_PARTICIPANTS",
        "RESULTS", "ACHIEVEMENTS", "SKINS",
    }

    out_lines = []
    in_data   = False
    script_injected = False

    for line in html.splitlines(keepends=True):
        stripped = line.strip()

        # ── strip inline data blocks ──────────────────────────────────────────
        if in_data:
            # End of a multiline block: line is exactly "];" or "};" or "});"
            if stripped in ("];", "};", "]);"):
                in_data = False
            continue  # skip all lines inside a data block

        skip = False
        for var in DATA_VARS:
            if re.match(rf"^const\s+{var}\b", stripped):
                # Single-line declaration (ends with ";" on same line after "[" or "{")
                if stripped.endswith("];") or stripped.endswith("};") or stripped.endswith("]);"):
                    skip = True
                else:
                    in_data = True
                    skip = True
                break

        if skip:
            continue

        # ── inject <script src="data.js"> before the first <script> ──────────
        if not script_injected and stripped == "<script>":
            out_lines.append('<script src="data.js"></script>\n')
            script_injected = True

        out_lines.append(line)

    INDEX_HTML.write_text("".join(out_lines), encoding="utf-8")
    print("  ✓  index.html migrated.")

print("\nDone! Run ./update.sh to commit and push.")
