#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="youtube/youtube_daily.log"
echo "[$(date)] Starting YouTube pipeline..." >> "$LOG"

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    /opt/homebrew/bin/ollama serve >> "$LOG" 2>&1 &
    sleep 8
fi

# Generate script
/usr/bin/python3 youtube/generate_script.py >> "$LOG" 2>&1

# Make video
/usr/bin/python3 youtube/make_video.py >> "$LOG" 2>&1

# Upload to YouTube
/usr/bin/python3 youtube/upload_youtube.py >> "$LOG" 2>&1

echo "[$(date)] YouTube pipeline complete." >> "$LOG"
