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

# Alternate: real case on odd days, fiction on even days
DAY=$(date +%d | sed 's/^0//')
if [ $((DAY % 2)) -eq 1 ]; then
    echo "[$(date)] Generating REAL CASE episode..." >> "$LOG"
    /usr/bin/python3 podcast/generate_episode.py >> "$LOG" 2>&1
else
    echo "[$(date)] Generating FICTION episode..." >> "$LOG"
    /usr/bin/python3 podcast/generate_fiction.py >> "$LOG" 2>&1
fi

# Produce audio (Kokoro TTS — human voices + atmospheric music)
echo "[$(date)] Producing audio with Kokoro TTS..." >> "$LOG"
/usr/bin/python3 podcast/produce_episode.py >> "$LOG" 2>&1

# Build RSS feed
echo "[$(date)] Building RSS feed..." >> "$LOG"
/usr/bin/python3 podcast/build_feed.py >> "$LOG" 2>&1

# Push live
git add podcast/ docs/podcast/ >> "$LOG" 2>&1
git diff --cached --quiet && echo "[$(date)] Nothing to commit." >> "$LOG" && exit 0
git commit -m "Dark Files: $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1
git subtree push --prefix docs origin gh-pages >> "$LOG" 2>&1

echo "[$(date)] ===== Complete. Episode in iCloud Drive. =====" >> "$LOG"
