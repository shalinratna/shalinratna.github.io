#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="tinytales/tinytales.log"
echo "[$(date)] ===== Tiny Tales Pipeline Starting =====" >> "$LOG"

# Generate story script
echo "[$(date)] Writing story..." >> "$LOG"
/usr/bin/python3 tinytales/generate_story.py >> "$LOG" 2>&1

# Produce episode (video + audio + short)
echo "[$(date)] Producing episode..." >> "$LOG"
/usr/bin/python3 tinytales/make_episode.py >> "$LOG" 2>&1

# Notify
osascript -e 'display notification "New Tiny Tales episode ready in iCloud!" with title "🐱 Tiny Tales" sound name "Glass"' 2>/dev/null

echo "[$(date)] ===== Done =====" >> "$LOG"
