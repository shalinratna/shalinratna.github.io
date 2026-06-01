#!/usr/bin/env python3
"""
Auto-publishes all site articles to Medium Partner Program.
Medium pays per read — some finance articles earn $50-200/month each.
Zero extra content — just repurposes what's already written.

Setup: Get your Medium Integration Token from medium.com/me/settings → Integration tokens
Save token: echo "YOUR_TOKEN" > medium/token.txt
Then run: python3 medium/publish_medium.py
"""
import json
import requests
import time
from pathlib import Path
from datetime import datetime

TOKEN_FILE = Path("medium/token.txt")
PUBLISHED_LOG = Path("medium/published.json")
ARTICLES_DIR = Path("articles")
SITE_URL = "https://shalinratna.github.io"

def get_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    print("""
Medium token not found.

1. Go to: medium.com/me/settings
2. Scroll to 'Integration tokens'
3. Create a token named 'Dark Files Auto Publisher'
4. Run: echo 'YOUR_TOKEN' > medium/token.txt
5. Run this script again
""")
    return None

def get_user_id(token):
    r = requests.get("https://api.medium.com/v1/me",
                    headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]

def get_published():
    if PUBLISHED_LOG.exists():
        return set(json.loads(PUBLISHED_LOG.read_text()))
    return set()

def save_published(published):
    PUBLISHED_LOG.write_text(json.dumps(list(published), indent=2))

def read_article(filepath):
    content = filepath.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return {}, content
    parts = content.split('---', 2)
    fm = {}
    for line in parts[1].strip().split('\n'):
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip().strip('"').strip("'")
    body = parts[2].strip() if len(parts) > 2 else content
    return fm, body

def publish_article(token, user_id, fm, body, slug):
    title = fm.get('title', slug.replace('-', ' ').title())
    tags_raw = fm.get('tags', '["AI", "Money", "Finance"]')
    try:
        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        tags = [str(t).strip() for t in tags[:5]]
    except:
        tags = ["AI", "Money", "Personal Finance"]

    # Add canonical link back to original site (good for SEO)
    canonical = f"{SITE_URL}/articles/{slug}/"
    footer = f"\n\n---\n*Originally published at [{SITE_URL}]({canonical})*"

    payload = {
        "title": title,
        "contentFormat": "markdown",
        "content": body + footer,
        "tags": tags,
        "publishStatus": "public",
        "canonicalUrl": canonical,
        "notifyFollowers": True,
    }

    r = requests.post(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload
    )

    if r.status_code in (200, 201):
        post_id = r.json()["data"]["id"]
        url = r.json()["data"]["url"]
        print(f"  Published: {title[:50]} → {url}")
        return True
    else:
        print(f"  Failed ({r.status_code}): {r.text[:100]}")
        return False

def main():
    token = get_token()
    if not token:
        return

    print("Connecting to Medium...")
    user_id = get_user_id(token)
    published = get_published()

    articles = sorted(ARTICLES_DIR.glob("*.md"))
    unpublished = [a for a in articles if a.stem not in published]
    print(f"Found {len(unpublished)} unpublished articles")

    # Publish up to 5 per run (Medium rate limits)
    batch = unpublished[:5]
    for art_file in batch:
        fm, body = read_article(art_file)
        slug = fm.get('slug', art_file.stem)
        if publish_article(token, user_id, fm, body, slug):
            published.add(art_file.stem)
            save_published(published)
            time.sleep(3)  # Be gentle with the API

    remaining = len(unpublished) - len(batch)
    print(f"\nPublished {len(batch)} articles. {remaining} remaining.")
    if remaining > 0:
        print("Run again tomorrow to publish more (Medium rate limits).")

if __name__ == "__main__":
    main()
