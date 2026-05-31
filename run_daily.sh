#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="/Users/shalin/Documents/Projects/ai-income/logs/daily.log"
echo "[$(date)] Starting daily pipeline..." >> "$LOG"

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    /opt/homebrew/bin/ollama serve >> "$LOG" 2>&1 &
    sleep 8
fi

# Generate new articles
/usr/bin/python3 generate.py >> "$LOG" 2>&1

# Build the site
/usr/bin/python3 build_site.py >> "$LOG" 2>&1

# Commit and push
git add articles/ docs/
git diff --cached --quiet && echo "[$(date)] Nothing new to commit." >> "$LOG" && exit 0
git commit -m "Daily update: $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1

# Push docs/ to gh-pages branch (live site at shalinratna.github.io)
git subtree push --prefix docs origin gh-pages >> "$LOG" 2>&1

echo "[$(date)] Pipeline complete." >> "$LOG"
