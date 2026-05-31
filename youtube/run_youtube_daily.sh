#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="youtube/youtube_daily.log"
echo "[$(date)] ===== YouTube Pipeline Starting =====" >> "$LOG"

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    /opt/homebrew/bin/ollama serve >> "$LOG" 2>&1 &
    sleep 8
fi

# 1. Generate script (series-aware Money Brain episode)
echo "[$(date)] Generating script..." >> "$LOG"
/usr/bin/python3 youtube/generate_script_v2.py >> "$LOG" 2>&1

# 2. Fetch stock footage from Pexels
echo "[$(date)] Fetching footage..." >> "$LOG"
/usr/bin/python3 youtube/fetch_footage.py >> "$LOG" 2>&1

# 3. Render full YouTube video
echo "[$(date)] Rendering video..." >> "$LOG"
/usr/bin/python3 youtube/make_video_v2.py >> "$LOG" 2>&1

# 4. Cut 60-second short for TikTok/Reels
echo "[$(date)] Creating short..." >> "$LOG"
/usr/bin/python3 youtube/make_shorts.py >> "$LOG" 2>&1

# 5. Upload to YouTube (needs client_secrets.json)
if [ -f "youtube/client_secrets.json" ]; then
    echo "[$(date)] Uploading to YouTube..." >> "$LOG"
    /usr/bin/python3 youtube/upload_youtube.py >> "$LOG" 2>&1
else
    echo "[$(date)] Skipping YouTube upload — no credentials yet" >> "$LOG"
fi

echo "[$(date)] ===== Pipeline Complete =====" >> "$LOG"
