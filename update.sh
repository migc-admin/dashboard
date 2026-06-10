#!/bin/bash
# MIGC Dashboard — build data.js from Excel and push to GitHub
# Usage: ./update.sh
#        ./update.sh "Custom commit message"

set -e  # exit on any error

MSG="${1:-Update tournament data — $(date '+%b %d, %Y')}"

echo "=== Building data.js from Excel files ==="
python3 build.py

echo ""
echo "=== Staging files ==="
git add data.js index.html build.py update.sh MIGC_Season_Dashboard.xlsx MIGC_All_Years_Master.xlsx

# Only commit if there are staged changes
if git diff --cached --quiet; then
  echo "Nothing changed — skipping commit."
else
  git commit -m "$MSG"
  echo ""
  echo "=== Pushing to GitHub ==="
  git push
  echo ""
  echo "✓ Done! Dashboard updated on GitHub Pages."
fi
