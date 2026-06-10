# MIGC Dashboard — Project Instructions

## Overview

This is a standalone single-file HTML dashboard for **Mulligan's Island Golf Club (MIGC)**, a Southern California recreational golf group. It tracks 2026 season results plus all-time historical records (2021–present).

**File:** `index.html`  
**Stack:** Vanilla HTML + CSS + JavaScript. No frameworks, no backend, no build step.  
**Hosting:** GitHub Pages (static). The file is fully self-contained — all data is embedded as JS arrays, including the club logo as a base64 PNG.

---

## Tab Structure

| Tab | Purpose |
|---|---|
| Dashboard | KPIs, Season Schedule, TGL Standings widget, Flight Leaderboards, DHL Money List |
| TGL | Full team standings + per-team player breakdowns |
| Achievements | Tournament Achievements, Skins, Results (all filterable) |
| Insights | 9 season stat cards |
| Player Scoring | Full gross/net scoring table |
| History | All-time leaderboards, All-Time Leaders KPIs, Tournament archive |

---

## Design System

| Token | Value | Usage |
|---|---|---|
| `--augusta` | `#1B4332` | Header, primary dark green |
| `--fairway` | `#2D6A4F` | Section headers, table `thead` background |
| `--gold` | `#D4AF37` | Accents, 1st place, borders |
| `--charcoal` | `#212529` | Body text |
| `--muted` | `#6c757d` | Secondary text, labels |
| `--border` | `#dee2e6` | Table borders |
| `--bg` | `#EEF1EC` | Page background |

**Fonts:** Playfair Display (headers/display), DM Sans (body/tables) — loaded via Google Fonts CDN.  
**Logo:** MIGC_Round.png embedded as base64 in the header (upper right, 100×100px).  
**Instagram:** `@sdmulligansgc` → `https://www.instagram.com/sdmulligansgc/` (footer link with SVG icon).

---

## Key Terminology

- **Flights:** Flight A and Flight B (handicap-based groupings within each tournament)
- **TGL:** Team Golf League — four teams compete for season points based on finish position
- **DHL Money List:** Achievements-only earnings tracker (excludes skins), members only
- **Donkey Score:** Highest gross score per flight per tournament — emoji is `&#x1FACF;` (🫏), not a swan
- **CTP / Greenie:** Closest to the Pin; multiple Winner rows for one player in one tournament = multiple KP holes won (intentional, not a data error)
- **Skins:** Hole-by-hole betting game tracked separately from achievements

---

## Data Architecture

All data lives in the `<script>` block as JavaScript `const` arrays.

### 2026 Season Arrays

| Variable | Description |
|---|---|
| `PLAYERS` | Master player registry — id, name, status (Member/Guest), TGL team |
| `TOURNAMENTS` | Season schedule — id, name, date, course, `tgl: true/false` |
| `TGL_PARTICIPANTS` | Object keyed by tournament ID listing which players opted into TGL |
| `RESULTS` | Raw scorecards — tid, player, flight, hcp, gross, net, f9, b9, putts |
| `ACHIEVEMENTS` | Placement + payout per player per category per tournament |
| `SKINS` | Skins results — tid, player, category, total skins, amount |

### History Arrays (prefixed to avoid conflicts)

| Variable | Description |
|---|---|
| `MAIN` | All historical achievement records (2021–2025) |
| `HIST_SKINS` | Historical skins records |
| `HIST_TOURNAMENTS` | Historical tournament reference data |
| `HIST_GUESTS` | Set of guest player names for the history tab |

**All history JS functions and DOM IDs are prefixed with `hist-`** to prevent naming conflicts with the 2026 dashboard.

---

## Business Rules

### Scoring & Results
- Net = Gross − Handicap
- Lower net = better placement
- Flights A and B are ranked and paid out separately
- Tied placements: duplicate rows with same placement value — this is intentional, represents split payout

### TGL Points
- Only applies to tournaments where `tgl: true` (2026_01 was NOT a TGL event)
- Players who "opted in" are listed in `TGL_PARTICIPANTS[tid]`
- **Formula:** N players in flight → 1st place earns N pts, last earns 1 pt
- **Ties split:** two players tied for 1st in a 14-player flight each earn (14+13)/2 = 13.5 pts
- Players not in TGL earn no points but still affect the ranking
- Players with `team: "None"` are excluded from TGL team standings
- Team total = sum of all participating members' points across all TGL tournaments

### TGL Teams
- **The Money Team** | `#1A6B65`
- **19th Hole Cartel** | `#E9724C`
- **Just the Tips** | `#2563EB`
- **White Rice** | `#7C3AED`

### Money / Achievements
- DHL Money List: achievements only (no skins), members only, Top 10 default with All toggle
- Guest players appear in results/achievements but are excluded from the money list
- Guests are tagged with a small `Guest` badge in tables

### Navigation from Schedule
- Clicking a past tournament row in the Schedule table calls `gotoAch(tid)` which switches to the Achievements tab and pre-selects that tournament in the Achievements, Skins, and Results filters simultaneously

---

## Guest Status

### 2026 Season Guests
Lucas Bouloy (id:40), Mat Vigil (id:41), Jeff Carey (id:42), Jason Payton (id:43), Med Baheta (id:44), Devin Lerner (id:45), Tyler Nichols (id:46)

### Historical Guests (`HIST_GUESTS` Set)
Mat Vigil, Jeff Carey, Jason Payton, Med Baheta, Lucas Bouloy, Brian Anderson, Gary Ryback, Young Park, Ryo Higurashi, Ted Setvanpour, Gary Molina, Robert Siemienczuk, Charles Figueroa

**Not guests (confirmed members):** Dan Ko, Shirley Ng, Tak Shishido — do NOT add these back to HIST_GUESTS.

---

## Historical Data Decisions

These were deliberate choices — do not change without explicit instruction:

| Decision | Detail |
|---|---|
| Category normalization | Historical categories mapped to 2026 schema: `Strokeplay 1st` → `Flight A - Overall` pl:`1`, `Greenie` → `Closest to the Pin`, `Low Net Front` → `Front 9`, etc. |
| Pre-2023 skins | No flight split in early years — stored with `flight: null`, displayed with `—` |
| 2022_09 El Dorado | Intentional data gap — excluded |
| 2025_XX Skylinks | Intentional data gap — excluded |
| 2024_09 Arrowood | Non-standard payouts included as-is |
| Danny Lopez in 2021_02 | The player is listed as "Daniel Lopez" in the data but refers to Danny Lopez — this is correct |
| Duplicate Greenie rows | Same player, same tournament, multiple CTP rows = multiple KP holes won, intentional |

---

## File Size Notes

The file is ~706KB because the club logo is base64-encoded inline. This is intentional for portability. If size becomes a concern, the logo can be moved to a separate `MIGC_Round.png` file and referenced with `<img src="MIGC_Round.png">`, which would bring the HTML back under ~100KB.

---

## Update Process (After Each Tournament)

1. Add rows to `RESULTS` for all players in the new tournament
2. Add rows to `ACHIEVEMENTS` for all placements and payouts
3. Add rows to `SKINS` for all skins winners
4. Add the tournament to `TGL_PARTICIPANTS[tid]` with the list of participating players
5. Verify `TOURNAMENTS` has the correct entry (should already be there for scheduled events)
6. Run a brace-balance check on the JS before committing: `{` count should equal `}` count

---

## Known Gotchas

- **Player ID 39** is assigned to Charles Tran — a historical quirk, distinguish by name
- `Low Putts` with `pl:"1"` is treated the same as `pl:"Winner"` in display logic
- Sort icons use `&#8645;` (⇅) for unsorted, `&#9650;` (▲) for ascending, `&#9661;` (▽) for descending — `&#9660;` (▼ filled) was deliberately replaced
- The donkey emoji is `&#x1FACF;` — do not use `&#129442;` (that's a swan) or `&#129451;` (also incorrect rendering on some systems)
- History tab DOM IDs all prefixed with `hist-` (e.g. `hist-lb-year-filter`, `hist-kpi-grid`)
- History JS functions all prefixed with `hist` or `populateHist` to avoid collisions with dashboard functions
