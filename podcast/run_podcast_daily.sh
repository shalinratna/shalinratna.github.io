#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="podcast/podcast_daily.log"
echo "[$(date)] ===== Dark Files Pipeline Starting =====" >> "$LOG"

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    /opt/homebrew/bin/ollama serve >> "$LOG" 2>&1 &
    sleep 8
fi

# 1. Generate episode script
echo "[$(date)] Generating script..." >> "$LOG"
/usr/bin/python3 podcast/generate_episode.py >> "$LOG" 2>&1

# 2. Produce audio (two voices + ambient music)
echo "[$(date)] Producing audio..." >> "$LOG"
/usr/bin/python3 podcast/produce_episode.py >> "$LOG" 2>&1

# 3. Build RSS feed
echo "[$(date)] Building RSS feed..." >> "$LOG"
/usr/bin/python3 podcast/build_feed.py >> "$LOG" 2>&1

# 4. Push to GitHub Pages
git add podcast/ docs/podcast/ >> "$LOG" 2>&1
git diff --cached --quiet && echo "[$(date)] Nothing to commit." >> "$LOG" && exit 0
git commit -m "Dark Files: new episode $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1
git subtree push --prefix docs origin gh-pages >> "$LOG" 2>&1

echo "[$(date)] ===== Podcast Pipeline Complete =====" >> "$LOG"
