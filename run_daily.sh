#!/bin/bash
set -e
cd /Users/shalin/Documents/Projects/ai-income

LOG="/Users/shalin/Documents/Projects/ai-income/logs/daily.log"
echo "[$(date)] ===== Daily Pipeline Starting =====" >> "$LOG"

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    /opt/homebrew/bin/ollama serve >> "$LOG" 2>&1 &
    sleep 8
fi

# 1. Generate 3 new SEO articles
/usr/bin/python3 generate.py >> "$LOG" 2>&1

# 2. Build site + AdSense + affiliate links
/usr/bin/python3 build_site.py >> "$LOG" 2>&1

# 3. Pinterest images for new articles
/usr/bin/python3 pinterest_images.py >> "$LOG" 2>&1

# 4. Post to Pinterest (if configured)
/usr/bin/python3 pinterest_post.py >> "$LOG" 2>&1

# 5. Publish 5 articles to Medium (if token configured)
if [ -f "medium/token.txt" ]; then
    /usr/bin/python3 medium/publish_medium.py >> "$LOG" 2>&1
fi

# 6. Push to GitHub Pages
git add articles/ docs/ pinterest_pins/ medium/
git diff --cached --quiet && echo "[$(date)] Nothing to commit." >> "$LOG" && exit 0
git commit -m "Daily: $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1
git subtree push --prefix docs origin gh-pages >> "$LOG" 2>&1

echo "[$(date)] ===== Daily Pipeline Complete =====" >> "$LOG"
