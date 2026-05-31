#!/usr/bin/env python3
"""
Auto-cuts a 60-second vertical (9:16) short from the main YouTube video.
Posts to TikTok & Instagram Reels folder — same content, 3x platforms.
"""
import sys
import numpy as np
from pathlib import Path
from moviepy import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont

SW, SH = 1080, 1920  # vertical 9:16

def get_font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def make_short(video_path, title="", start=0, duration=58):
    video_path = Path(video_path)
    out_dir = Path("youtube/shorts")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"short-{video_path.stem}.mp4"

    if out_path.exists():
        print(f"Short already exists: {out_path.name}")
        return out_path

    print(f"Creating short from: {video_path.name}")
    vid = VideoFileClip(str(video_path))

    # Use first 58 seconds (hook is always the most engaging)
    clip = vid.subclipped(start, min(start + duration, vid.duration))

    # Center-crop to vertical 9:16
    # Original is 1920x1080, we want 1080x1920 vertical
    # Crop center 608px wide from 1080p → scale to 1080 wide
    crop_w = int(clip.h * SW / SH)
    x1 = (clip.w - crop_w) // 2
    clip = clip.cropped(x1=x1, x2=x1+crop_w).resized((SW, SH))

    # Add watermark overlay
    overlay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Top branding bar
    draw.rectangle([0, 0, SW, 100], fill=(0, 0, 0, 200))
    f = get_font(44, bold=True)
    draw.text((SW//2, 50), "💰 Money Brain", font=f, fill=(108, 99, 255), anchor="mm")

    # Bottom CTA
    draw.rectangle([0, SH-120, SW, SH], fill=(0, 0, 0, 200))
    f2 = get_font(38)
    draw.text((SW//2, SH-60), "Follow for daily money tips 🔥", font=f2,
             fill=(255, 215, 0), anchor="mm")

    overlay_clip = ImageClip(np.array(overlay)).with_duration(clip.duration).with_fps(24)
    final = CompositeVideoClip([clip.with_fps(24), overlay_clip])

    final.write_videofile(str(out_path), fps=24, codec="libx264",
                         audio_codec="aac", logger=None, preset="fast")
    clip.close()
    final.close()
    vid.close()

    print(f"Short ready: {out_path.name}")
    return out_path

if __name__ == "__main__":
    videos = sorted(Path("youtube/video").glob("*.mp4"))
    if not videos:
        print("No videos found.")
        sys.exit(1)
    scripts = sorted(Path("youtube/scripts").glob("*.json"))
    title = ""
    if scripts:
        import json
        title = json.loads(scripts[-1].read_text()).get("title", "")
    make_short(videos[-1], title)
