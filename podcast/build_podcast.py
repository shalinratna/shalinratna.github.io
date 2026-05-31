#!/usr/bin/env python3
"""
Auto-generates a Spotify/Apple Podcasts-compatible RSS feed
from Money Brain YouTube audio files.

Same content as YouTube = zero extra work = extra revenue stream.
Monetized via Spotify Audience Network (~$15-25 CPM).

Submit feed URL once at:
- Spotify: podcasters.spotify.com
- Apple:   podcastsconnect.apple.com
Then never touch it again — episodes auto-publish forever.
"""
import json
import shutil
import hashlib
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path

SITE_URL = "https://shalinratna.github.io"
PODCAST_URL = f"{SITE_URL}/podcast"
FEED_URL = f"{PODCAST_URL}/feed.xml"

PODCAST = {
    "title": "Money Brain",
    "description": (
        "The no-fluff podcast for men who want to build wealth using AI tools, "
        "smart investing, and modern money mindset. New episodes every week."
    ),
    "author": "Money Brain",
    "email": "moneybrain.podcast@gmail.com",  # update after creating Gmail
    "language": "en-us",
    "category": "Business",
    "subcategory": "Investing",
    "image_url": f"{PODCAST_URL}/cover.jpg",
    "explicit": "false",
}

def get_audio_duration(path):
    """Get MP3 duration in seconds using ffprobe."""
    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_format', path],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        return 600.0  # fallback 10 min

def format_duration(seconds):
    """Format seconds as HH:MM:SS for podcast RSS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_episodes():
    """Find all Money Brain audio files and match with scripts."""
    scripts_dir = Path("youtube/scripts")
    audio_base = Path("youtube/audio")
    episodes = []

    scripts = sorted(scripts_dir.glob("s*-*.json"))
    for script_path in scripts:
        script = json.loads(script_path.read_text())
        fname = script.get("filename", "")
        audio_dir = audio_base / fname

        # Combine all audio files into one episode file
        ep_num = script.get("ep_num", 1)
        series = script.get("series_name", "Money Brain")
        title = script.get("title", fname)
        date_str = script.get("date", datetime.now().strftime("%Y-%m-%d"))

        # Check if combined episode audio exists
        ep_audio = Path("podcast/episodes") / f"ep{ep_num:03d}-{fname}.mp3"

        if not ep_audio.exists() and audio_dir.exists():
            # Concatenate all audio files for this episode
            parts = sorted(audio_dir.glob("*.mp3"))
            if parts:
                _combine_audio(parts, ep_audio)

        if ep_audio.exists():
            size = ep_audio.stat().st_size
            dur = get_audio_duration(str(ep_audio))
            episodes.append({
                "title": title,
                "ep_num": ep_num,
                "series": series,
                "filename": ep_audio.name,
                "url": f"{PODCAST_URL}/episodes/{ep_audio.name}",
                "size": size,
                "duration": format_duration(dur),
                "date": date_str,
                "description": script.get("description", title),
                "tags": script.get("tags", []),
            })

    return sorted(episodes, key=lambda e: e["ep_num"])

def _combine_audio(parts, out_path):
    """Concatenate MP3 files into one episode."""
    import subprocess
    out_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_path.parent / "concat_list.txt"
    list_file.write_text('\n'.join(f"file '{p.resolve()}'" for p in parts))
    subprocess.run(
        ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
         '-c', 'copy', '-y', str(out_path)],
        capture_output=True
    )
    list_file.unlink(missing_ok=True)
    if out_path.exists():
        print(f"  Created episode: {out_path.name}")

def build_cover():
    """Generate podcast cover art (3000x3000, required by Spotify/Apple)."""
    from PIL import Image, ImageDraw, ImageFont

    cover_path = Path("podcast/cover.jpg")
    if cover_path.exists():
        return

    cover_path.parent.mkdir(exist_ok=True)
    SIZE = 3000
    img = Image.new("RGB", (SIZE, SIZE), (10, 10, 20))
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(SIZE):
        r = int(10 + 20 * y/SIZE)
        g = int(10 + 5 * y/SIZE)
        b = int(20 + 40 * y/SIZE)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))

    # Accent circles
    draw.ellipse([SIZE//2-800, SIZE//2-800, SIZE//2+800, SIZE//2+800],
                 fill=(20, 18, 50))
    draw.ellipse([SIZE//2-700, SIZE//2-700, SIZE//2+700, SIZE//2+700],
                 fill=(15, 12, 40))

    def get_font(size, bold=False):
        for p in [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            if Path(p).exists():
                try:
                    from PIL import ImageFont
                    return ImageFont.truetype(p, size)
                except:
                    pass
        from PIL import ImageFont
        return ImageFont.load_default()

    # Money icon
    f_icon = get_font(600, bold=True)
    draw.text((SIZE//2, SIZE//2 - 300), "💰", font=f_icon, anchor="mm")

    # Title
    f_title = get_font(280, bold=True)
    draw.text((SIZE//2, SIZE//2 + 250), "MONEY", font=f_title,
             fill=(255, 255, 255), anchor="mm")
    draw.text((SIZE//2, SIZE//2 + 560), "BRAIN", font=f_title,
             fill=(108, 99, 255), anchor="mm")

    # Tagline
    f_tag = get_font(130)
    draw.text((SIZE//2, SIZE//2 + 850), "AI-Powered Wealth Building",
             font=f_tag, fill=(180, 180, 220), anchor="mm")

    # Border
    draw.rectangle([0, 0, SIZE, 30], fill=(108, 99, 255))
    draw.rectangle([0, SIZE-30, SIZE, SIZE], fill=(108, 99, 255))

    img.save(str(cover_path), quality=95)
    print(f"  Cover art created: {cover_path}")

def build_rss(episodes):
    """Generate iTunes/Spotify compatible RSS 2.0 feed."""
    now_rfc = formatdate(usegmt=True)

    items = ""
    for ep in episodes:
        pub_date = formatdate(
            datetime.strptime(ep["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc).timestamp(),
            usegmt=True
        )
        tags_str = ", ".join(ep["tags"][:5]) if ep["tags"] else "money, AI, wealth"
        guid = hashlib.md5(ep["url"].encode()).hexdigest()

        items += f"""
    <item>
      <title>{ep['title']}</title>
      <description><![CDATA[{ep['description']}<br/><br/>Part of the {ep['series']} series on Money Brain. Topics: {tags_str}.]]></description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <enclosure url="{ep['url']}" length="{ep['size']}" type="audio/mpeg"/>
      <itunes:title>{ep['title']}</itunes:title>
      <itunes:episode>{ep['ep_num']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:duration>{ep['duration']}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:author>{PODCAST['author']}</itunes:author>
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:spotify="https://www.spotify.com/ns/rss">
  <channel>
    <title>{PODCAST['title']}</title>
    <link>{SITE_URL}</link>
    <description>{PODCAST['description']}</description>
    <language>{PODCAST['language']}</language>
    <pubDate>{now_rfc}</pubDate>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <itunes:author>{PODCAST['author']}</itunes:author>
    <itunes:email>{PODCAST['email']}</itunes:email>
    <itunes:image href="{PODCAST['image_url']}"/>
    <itunes:category text="{PODCAST['category']}">
      <itunes:category text="{PODCAST['subcategory']}"/>
    </itunes:category>
    <itunes:explicit>{PODCAST['explicit']}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    {items}
  </channel>
</rss>"""

def main():
    print("Building Money Brain Podcast RSS feed...")
    Path("podcast/episodes").mkdir(parents=True, exist_ok=True)

    build_cover()
    episodes = get_episodes()
    print(f"  Found {len(episodes)} episodes")

    rss = build_rss(episodes)
    feed_path = Path("podcast/feed.xml")
    feed_path.write_text(rss, encoding='utf-8')
    print(f"  RSS feed: {feed_path}")

    # Copy to docs/ for GitHub Pages hosting
    docs_podcast = Path("docs/podcast")
    docs_podcast.mkdir(exist_ok=True)
    shutil.copy("podcast/feed.xml", "docs/podcast/feed.xml")

    ep_docs = docs_podcast / "episodes"
    ep_docs.mkdir(exist_ok=True)
    for ep_file in Path("podcast/episodes").glob("*.mp3"):
        dest = ep_docs / ep_file.name
        if not dest.exists():
            shutil.copy(ep_file, dest)
            print(f"  Deployed: {ep_file.name}")

    if Path("podcast/cover.jpg").exists():
        shutil.copy("podcast/cover.jpg", "docs/podcast/cover.jpg")

    print(f"\n  Feed URL: {FEED_URL}")
    print(f"  Episodes: {len(episodes)}")
    print(f"\n  Submit feed to Spotify: podcasters.spotify.com")
    print(f"  Submit feed to Apple:   podcastsconnect.apple.com")

if __name__ == "__main__":
    main()
