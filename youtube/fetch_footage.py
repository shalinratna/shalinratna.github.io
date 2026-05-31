#!/usr/bin/env python3
"""Downloads stock footage from Pexels API for each video section."""
import json
import os
import requests
from pathlib import Path

PEXELS_KEY_FILE = Path("youtube/pexels_key.txt")
FOOTAGE_DIR = Path("youtube/footage")

FALLBACK_KEYWORDS = [
    "money cash", "businessman success", "laptop working",
    "city skyline", "financial charts", "motivated man"
]

def get_key():
    if PEXELS_KEY_FILE.exists():
        return PEXELS_KEY_FILE.read_text().strip()
    return os.environ.get("PEXELS_API_KEY", "")

def search_video(keyword, api_key, orientation="landscape"):
    headers = {"Authorization": api_key}
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params={"query": keyword, "per_page": 5, "orientation": orientation,
                "size": "medium"},
        timeout=30
    )
    if resp.status_code != 200:
        return None
    videos = resp.json().get("videos", [])
    if not videos:
        return None
    # Pick shortest clip between 5-30 seconds for good flow
    for v in videos:
        dur = v.get("duration", 99)
        if 5 <= dur <= 30:
            files = v.get("video_files", [])
            hd = [f for f in files if f.get("quality") in ("hd", "sd") and f.get("width", 0) >= 1280]
            if hd:
                return hd[0]["link"]
    # fallback to first video
    files = videos[0].get("video_files", [])
    sd = [f for f in files if f.get("quality") in ("hd", "sd")]
    return sd[0]["link"] if sd else None

def download_video(url, path):
    resp = requests.get(url, stream=True, timeout=60)
    with open(path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024*1024):
            f.write(chunk)

def fetch_for_script(script_data):
    api_key = get_key()
    if not api_key:
        print("No Pexels API key. Add it to youtube/pexels_key.txt")
        return {}

    fname = script_data.get("filename", "video")
    out_dir = FOOTAGE_DIR / fname
    out_dir.mkdir(parents=True, exist_ok=True)

    footage_map = {}

    # Sections
    keywords = script_data.get("section_footage", [])
    if not keywords:
        keywords = FALLBACK_KEYWORDS[:5]

    for i, kw in enumerate(keywords):
        out_path = out_dir / f"section_{i+1}.mp4"
        if out_path.exists():
            footage_map[f"section_{i+1}"] = str(out_path)
            continue
        print(f"  Fetching footage: '{kw}'...")
        url = search_video(kw, api_key)
        if not url:
            url = search_video(FALLBACK_KEYWORDS[i % len(FALLBACK_KEYWORDS)], api_key)
        if url:
            download_video(url, out_path)
            footage_map[f"section_{i+1}"] = str(out_path)
            print(f"  Downloaded: section_{i+1}.mp4")
        else:
            footage_map[f"section_{i+1}"] = None

    # Intro/outro/hook footage
    for seg, kw in [("hook", "money motivation"), ("intro", "success mindset"), ("outro", "subscribe notification")]:
        out_path = out_dir / f"{seg}.mp4"
        if out_path.exists():
            footage_map[seg] = str(out_path)
            continue
        url = search_video(kw, api_key)
        if url:
            download_video(url, out_path)
            footage_map[seg] = str(out_path)

    return footage_map

if __name__ == "__main__":
    import sys
    from pathlib import Path
    scripts = sorted(Path("youtube/scripts").glob("*.json"))
    if not scripts:
        print("No scripts found.")
        sys.exit(1)
    script = json.loads(scripts[-1].read_text())
    footage = fetch_for_script(script)
    print(f"Downloaded {len(footage)} footage clips")
