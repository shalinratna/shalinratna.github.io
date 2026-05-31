#!/usr/bin/env python3
"""Builds Spotify/Apple Podcasts RSS feed for Dark Files."""
import json
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SITE_URL = "https://shalinratna.github.io"
PODCAST_URL = f"{SITE_URL}/podcast"
EPISODES_DIR = Path("podcast/episodes")
SCRIPTS_DIR = Path("podcast/scripts")
DOCS_DIR = Path("docs/podcast")

SHOW = {
    "title": "Dark Files",
    "description": (
        "Two hosts. Countless cases. Dark Files dives deep into the most chilling "
        "true crime stories — cold cases, unsolved murders, and the cases that haunt us. "
        "New episodes every week. Be wrapt up, be nosy, stay safe."
    ),
    "author": "Dark Files Podcast",
    "language": "en-us",
    "category": "True Crime",
    "explicit": "true",
}

def get_duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True, text=True
    )
    try:
        s = float(json.loads(r.stdout)['format']['duration'])
        h, m, sec = int(s//3600), int((s%3600)//60), int(s%60)
        return f"{h:02d}:{m:02d}:{sec:02d}"
    except:
        return "00:30:00"

def build_cover():
    cover = Path("podcast/cover.jpg")
    if cover.exists():
        return
    SIZE = 3000
    img = Image.new("RGB", (SIZE, SIZE), (8, 8, 12))
    draw = ImageDraw.Draw(img)

    # Dark gradient
    for y in range(SIZE):
        v = int(8 + 12 * y/SIZE)
        draw.line([(0,y),(SIZE,y)], fill=(v, v//2, v))

    def font(size, bold=False):
        for p in [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc"
        ]:
            if Path(p).exists():
                try:
                    return ImageFont.truetype(p, size)
                except: pass
        return ImageFont.load_default()

    # Red accent line
    draw.rectangle([0, 0, SIZE, 40], fill=(180, 20, 20))
    draw.rectangle([0, SIZE-40, SIZE, SIZE], fill=(180, 20, 20))

    # Crime scene tape effect
    draw.rectangle([0, SIZE//2-25, SIZE, SIZE//2+25], fill=(180, 20, 20))

    # Main title
    f_main = font(380, bold=True)
    draw.text((SIZE//2, SIZE//2-280), "DARK", font=f_main, fill=(255,255,255), anchor="mm")
    draw.text((SIZE//2, SIZE//2+300), "FILES", font=f_main, fill=(255,255,255), anchor="mm")

    # Tagline
    f_tag = font(110)
    draw.text((SIZE//2, SIZE//2-530), "TRUE CRIME PODCAST", font=f_tag,
             fill=(180,20,20), anchor="mm")

    img.save(str(cover), quality=95)
    print("  Cover art created: podcast/cover.jpg")

def build_rss(episodes):
    items = ""
    for ep in episodes:
        pub = formatdate(
            datetime.strptime(ep["date"], "%Y-%m-%d")
            .replace(tzinfo=timezone.utc).timestamp(), usegmt=True
        )
        guid = hashlib.md5(ep["url"].encode()).hexdigest()
        items += f"""
    <item>
      <title>{ep['title']}</title>
      <description><![CDATA[{ep['description']}]]></description>
      <pubDate>{pub}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <enclosure url="{ep['url']}" length="{ep['size']}" type="audio/mpeg"/>
      <itunes:title>{ep['title']}</itunes:title>
      <itunes:episode>{ep['ep_num']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:duration>{ep['duration']}</itunes:duration>
      <itunes:explicit>true</itunes:explicit>
      <itunes:author>{SHOW['author']}</itunes:author>
    </item>"""

    now = formatdate(usegmt=True)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{SHOW['title']}</title>
    <link>{SITE_URL}</link>
    <description>{SHOW['description']}</description>
    <language>{SHOW['language']}</language>
    <pubDate>{now}</pubDate>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{SHOW['author']}</itunes:author>
    <itunes:image href="{PODCAST_URL}/cover.jpg"/>
    <itunes:category text="{SHOW['category']}"/>
    <itunes:explicit>{SHOW['explicit']}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    {items}
  </channel>
</rss>"""

def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ep_docs = DOCS_DIR / "episodes"
    ep_docs.mkdir(exist_ok=True)

    build_cover()
    shutil.copy("podcast/cover.jpg", DOCS_DIR / "cover.jpg")

    # Match episodes to scripts
    episodes = []
    for mp3 in sorted(EPISODES_DIR.glob("ep*.mp3")):
        ep_num = int(mp3.stem[2:5])
        scripts = list(SCRIPTS_DIR.glob(f"ep{ep_num:03d}*.json"))
        if not scripts:
            continue
        script = json.loads(scripts[0].read_text())

        # Copy to docs
        dest = ep_docs / mp3.name
        if not dest.exists():
            shutil.copy(mp3, dest)

        episodes.append({
            "ep_num": ep_num,
            "title": script.get("title", f"Episode {ep_num}"),
            "description": script.get("description", ""),
            "date": script.get("date", datetime.now().strftime("%Y-%m-%d")),
            "url": f"{PODCAST_URL}/episodes/{mp3.name}",
            "size": mp3.stat().st_size,
            "duration": get_duration(mp3),
            "slug": script.get("slug", ""),
        })

    rss = build_rss(episodes)
    feed = DOCS_DIR / "feed.xml"
    feed.write_text(rss, encoding='utf-8')

    print(f"  Feed: {PODCAST_URL}/feed.xml")
    print(f"  Episodes: {len(episodes)}")
    if episodes:
        print(f"\n  SUBMIT ONCE TO GO LIVE:")
        print(f"  Spotify → podcasters.spotify.com → Add podcast → paste feed URL")
        print(f"  Apple   → podcastsconnect.apple.com → Add show → paste feed URL")
        print(f"  Feed URL: {PODCAST_URL}/feed.xml")

if __name__ == "__main__":
    main()
