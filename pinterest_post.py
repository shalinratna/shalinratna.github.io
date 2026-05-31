#!/usr/bin/env python3
"""
Auto-posts Pinterest pins via Pinterest API v5.
One-time setup: create Pinterest Business account, get access token.
Run: python3 pinterest_post.py --setup   (first time)
Run: python3 pinterest_post.py           (daily auto-post)
"""
import json
import sys
import requests
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path("pinterest_config.json")
PINS_DIR = Path("pinterest_pins")
POSTED_LOG = Path("pinterest_posted.json")
SITE_URL = "https://shalinratna.github.io"
BOARD_NAME = "AI Money & Productivity Tips"

def load_config():
    if not CONFIG_FILE.exists():
        print("""
Pinterest not configured yet.

1. Go to: https://developers.pinterest.com/apps/
2. Create an app → get Access Token
3. Create a board called 'AI Money & Productivity Tips'
4. Run: python3 pinterest_post.py --setup
""")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())

def setup():
    token = input("Paste your Pinterest Access Token: ").strip()
    board_id = input("Paste your Pinterest Board ID: ").strip()
    config = {"access_token": token, "board_id": board_id}
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    print("Saved! Run python3 pinterest_post.py to start posting.")

def get_posted():
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()))
    return set()

def save_posted(posted):
    POSTED_LOG.write_text(json.dumps(list(posted), indent=2))

def get_article_data(slug):
    articles_dir = Path("articles")
    for md_file in articles_dir.glob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        if not content.startswith('---'):
            continue
        parts = content.split('---', 2)
        fm = {}
        for line in parts[1].strip().split('\n'):
            if ':' in line:
                k, _, v = line.partition(':')
                fm[k.strip()] = v.strip().strip('"').strip("'")
        if fm.get('slug') == slug:
            return fm
    return {}

def post_pin(config, pin_path, article_data):
    slug = pin_path.stem
    title = article_data.get('title', slug.replace('-', ' ').title())
    desc = article_data.get('description', article_data.get('meta', ''))
    url = f"{SITE_URL}/articles/{slug}/"

    # Upload image
    with open(pin_path, 'rb') as f:
        upload_resp = requests.post(
            "https://api.pinterest.com/v5/media",
            headers={"Authorization": f"Bearer {config['access_token']}"},
            files={"": f}
        )

    if upload_resp.status_code not in (200, 201):
        print(f"Upload failed: {upload_resp.text}")
        return False

    media_id = upload_resp.json().get("media_id")

    pin_data = {
        "board_id": config["board_id"],
        "title": title[:100],
        "description": f"{desc}\n\nRead more: {url}",
        "link": url,
        "media_source": {
            "source_type": "image_url",
            "url": f"https://api.pinterest.com/v5/media/{media_id}"
        }
    }

    resp = requests.post(
        "https://api.pinterest.com/v5/pins",
        headers={
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json"
        },
        json=pin_data
    )

    if resp.status_code in (200, 201):
        print(f"Posted: {title[:60]}")
        return True
    else:
        print(f"Post failed: {resp.text}")
        return False

def main():
    if "--setup" in sys.argv:
        setup()
        return

    config = load_config()
    posted = get_posted()

    pins = sorted(PINS_DIR.glob("*.png"))
    unposted = [p for p in pins if p.stem not in posted]

    if not unposted:
        print("All pins posted. Generate more articles first.")
        return

    # Post 3 pins per day (Pinterest sweet spot)
    to_post = unposted[:3]
    for pin_path in to_post:
        article_data = get_article_data(pin_path.stem)
        if post_pin(config, pin_path, article_data):
            posted.add(pin_path.stem)
            save_posted(posted)

    print(f"Done. {len(unposted)-len(to_post)} pins remaining in queue.")

if __name__ == "__main__":
    main()
