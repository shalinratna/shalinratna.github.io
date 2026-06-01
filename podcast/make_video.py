#!/usr/bin/env python3
"""
Dark Files — Cinematic True Crime Video Generator.
Atmospheric animated backgrounds + text reveals + voiceover.
No stock footage needed — everything generated locally.
Produces 10-15 min YouTube video + 60s TikTok/Reels cut.
"""
import json
import subprocess
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    ImageClip, AudioFileClip, TextClip,
    concatenate_videoclips, CompositeVideoClip
)

W, H = 1920, 1080
FPS = 24
SHORTS_W, SHORTS_H = 1080, 1920

SCRIPTS_DIR = Path("podcast/scripts")
EPISODES_DIR = Path("podcast/episodes")
VIDEO_DIR = Path("podcast/video")
SHORTS_DIR = Path("podcast/shorts")

# Dark cinematic color palette
BLACK     = (0, 0, 0)
NEAR_BLACK = (8, 5, 12)
DEEP_RED  = (120, 15, 15)
BLOOD_RED = (180, 20, 20)
DIM_WHITE = (220, 215, 225)
GREY      = (100, 95, 110)
PURPLE    = (60, 20, 80)

def get_font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def make_atmospheric_frame(t, w=W, h=H, seed=0):
    """Generate one frame of atmospheric dark background with particles."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Deep gradient base
    for y in range(h):
        r = int(8 + 4 * y/h)
        g = int(5 + 2 * y/h)
        b = int(12 + 8 * y/h)
        img[y, :] = [r, g, b]

    # Vignette — dark edges
    cx, cy = w/2, h/2
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X-cx)**2 + (Y-cy)**2)
    vignette = np.clip(1 - dist / (max(w,h)*0.65), 0, 1)
    for c in range(3):
        img[:,:,c] = (img[:,:,c] * vignette).astype(np.uint8)

    # Animated particles (dust/fog effect)
    n_particles = 200
    px = (rng.random(n_particles) * w + np.sin(t * 0.3 + rng.random(n_particles)*10) * 20).astype(int) % w
    py = ((rng.random(n_particles) * h + t * 8 * rng.uniform(0.3, 1.2, n_particles)) % h).astype(int)
    brightness = rng.integers(15, 45, n_particles)
    for i in range(n_particles):
        x, y = px[i], py[i]
        b = int(brightness[i])
        if 0 <= x < w and 0 <= y < h:
            img[max(0,y-1):y+2, max(0,x-1):x+2] = np.clip(
                img[max(0,y-1):y+2, max(0,x-1):x+2].astype(int) + b, 0, 255
            )

    # Subtle red glow in corner
    glow_x, glow_y = int(w * 0.15), int(h * 0.85)
    Y2, X2 = np.ogrid[:h, :w]
    glow = np.exp(-((X2-glow_x)**2 + (Y2-glow_y)**2) / (2 * (w*0.12)**2))
    img[:,:,0] = np.clip(img[:,:,0].astype(float) + glow * 35, 0, 255).astype(np.uint8)

    return img

def make_title_card(title, subtitle="", ep_num=1):
    """Generate a cinematic title card image."""
    img_pil = Image.fromarray(make_atmospheric_frame(0))
    draw = ImageDraw.Draw(img_pil)

    # Red top bar
    draw.rectangle([0, 0, W, 5], fill=BLOOD_RED)

    # Show name
    f_show = get_font(38, bold=True)
    draw.text((W//2, 80), "DARK FILES", font=f_show, fill=BLOOD_RED, anchor="mm",
             spacing=8)

    # Episode badge
    f_ep = get_font(28)
    draw.text((W//2, 130), f"EPISODE {ep_num:02d}", font=f_ep, fill=GREY, anchor="mm")

    # Main title — break into lines
    f_title = get_font(90, bold=True)
    words = title.upper().split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=f_title)[2] > W-140 and cur:
            lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))

    y = H//2 - (len(lines) * 100)//2
    for line in lines:
        # Drop shadow
        draw.text((W//2+3, y+3), line, font=f_title, fill=(0,0,0), anchor="mm")
        draw.text((W//2, y), line, font=f_title, fill=DIM_WHITE, anchor="mm")
        y += 105

    # Divider
    draw.rectangle([W//2-200, y+20, W//2+200, y+24], fill=BLOOD_RED)

    if subtitle:
        f_sub = get_font(36)
        draw.text((W//2, y+60), subtitle, font=f_sub, fill=GREY, anchor="mm")

    return np.array(img_pil)

def make_text_slide(text, speaker="MORGAN", progress=0.0, case_name=""):
    """Text overlay slide with atmospheric background."""
    bg = make_atmospheric_frame(progress * 10)
    img_pil = Image.fromarray(bg)
    draw = ImageDraw.Draw(img_pil)

    # Bottom gradient for text readability
    for y in range(H//2, H):
        alpha = (y - H//2) / (H//2)
        draw.line([(0,y),(W,y)],
                 fill=tuple(int(c * (1-alpha*0.85)) for c in bg[y, W//2]))

    # Speaker label
    if speaker == "MORGAN":
        color = (200, 170, 255)
        label = "MORGAN"
    else:
        color = (255, 170, 150)
        label = "TAYLOR"

    f_label = get_font(28, bold=True)
    label_w = draw.textbbox((0,0), label, font=f_label)[2] + 32
    draw.rounded_rectangle([60, H-200, 60+label_w, H-160], radius=4,
                           fill=(*[int(c*0.3) for c in color], 200) if False else (30,20,40))
    draw.text((76, H-180), label, font=f_label, fill=color, anchor="lm")

    # Main dialogue text
    f_text = get_font(42)
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=f_text)[2] > W-120 and cur:
            lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))

    lines = lines[-3:]  # Show last 3 lines max
    y_start = H - 145 - (len(lines)-1) * 55
    for line in lines:
        draw.text((60, y_start+2), line, font=f_text, fill=(0,0,0))
        draw.text((60, y_start), line, font=f_text, fill=DIM_WHITE)
        y_start += 55

    # Progress bar
    draw.rectangle([0, H-8, int(W*progress), H], fill=BLOOD_RED)

    # Case name watermark
    if case_name:
        f_case = get_font(22)
        draw.text((W-20, 20), case_name[:50], font=f_case, fill=GREY, anchor="ra")

    return np.array(img_pil)

def make_chapter_card(chapter_title, chapter_num, total):
    """Chapter break card."""
    img_pil = Image.fromarray(make_atmospheric_frame(chapter_num * 5))
    draw = ImageDraw.Draw(img_pil)

    draw.rectangle([0, 0, W, 5], fill=BLOOD_RED)
    draw.rectangle([0, H-5, W, H], fill=BLOOD_RED)

    f_ch = get_font(30)
    f_title = get_font(70, bold=True)

    draw.text((W//2, H//2-80), f"CHAPTER {chapter_num} OF {total}", font=f_ch,
             fill=GREY, anchor="mm")
    draw.rectangle([W//2-150, H//2-45, W//2+150, H//2-41], fill=BLOOD_RED)

    words = chapter_title.upper().split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=f_title)[2] > W-160 and cur:
            lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))

    y = H//2 + 10
    for line in lines:
        draw.text((W//2+2, y+2), line, font=f_title, fill=(0,0,0), anchor="mm")
        draw.text((W//2, y), line, font=f_title, fill=DIM_WHITE, anchor="mm")
        y += 85

    return np.array(img_pil)

def make_outro_card(show_name="DARK FILES"):
    img_pil = Image.fromarray(make_atmospheric_frame(99))
    draw = ImageDraw.Draw(img_pil)
    draw.rectangle([0, 0, W, 5], fill=BLOOD_RED)

    f_sub = get_font(40)
    f_main = get_font(90, bold=True)
    f_cta = get_font(36)

    draw.text((W//2, H//2-160), "SUBSCRIBE TO", font=f_sub, fill=GREY, anchor="mm")
    draw.text((W//2+2, H//2-52), show_name, font=f_main, fill=(0,0,0), anchor="mm")
    draw.text((W//2, H//2-55), show_name, font=f_main, fill=BLOOD_RED, anchor="mm")
    draw.rectangle([W//2-200, H//2+30, W//2+200, H//2+34], fill=GREY)
    draw.text((W//2, H//2+80), "New episodes every week", font=f_cta, fill=GREY, anchor="mm")
    draw.text((W//2, H//2+140), "🔔 Turn on notifications", font=f_cta, fill=DIM_WHITE, anchor="mm")

    return np.array(img_pil)

def get_audio_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                       '-show_format', str(path)], capture_output=True, text=True)
    try: return float(json.loads(r.stdout)['format']['duration'])
    except: return 5.0

def build_video(script_path, ep_audio_path):
    script = json.loads(Path(script_path).read_text())
    ep_num = script.get("ep_num", 1)
    slug = script.get("slug", "episode")
    title = script.get("title", "Dark Files")
    dialogue = script.get("dialogue", [])
    is_fiction = script.get("fiction", False)
    date = script.get("date", datetime.now().strftime("%Y-%m-%d"))

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    SHORTS_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = Path("podcast/work") / f"ep{ep_num:03d}"

    print(f"Building video: {title}")

    # Load full episode audio
    full_audio = AudioFileClip(str(ep_audio_path))
    total_dur = full_audio.duration
    print(f"  Audio duration: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    clips = []

    # 1. Title card (5 seconds)
    title_arr = make_title_card(title, "True Crime" if not is_fiction else "Dark Files Fiction", ep_num)
    title_clip = ImageClip(title_arr).with_duration(5).with_fps(FPS)
    clips.append(title_clip)

    # 2. Dialogue slides — one per line, synced to audio duration
    if dialogue:
        time_per_line = total_dur / len(dialogue)
        chapter_size = max(1, len(dialogue) // 4)

        for i, line in enumerate(dialogue):
            speaker = line["speaker"]
            text = line["text"]
            progress = i / len(dialogue)

            # Chapter card every ~25% of episode
            if i > 0 and i % chapter_size == 0:
                ch_num = i // chapter_size
                ch_arr = make_chapter_card(
                    f"{'The Investigation' if ch_num==1 else 'The Discovery' if ch_num==2 else 'The Aftermath'}",
                    ch_num, 3
                )
                ch_clip = ImageClip(ch_arr).with_duration(2.5).with_fps(FPS)
                clips.append(ch_clip)

            slide_arr = make_text_slide(text, speaker, progress, title[:35])
            dur = max(time_per_line * 0.9, 3.0)
            slide_clip = ImageClip(slide_arr).with_duration(dur).with_fps(FPS)
            clips.append(slide_clip)

    # 3. Outro card (5 seconds)
    outro_arr = make_outro_card()
    outro_clip = ImageClip(outro_arr).with_duration(5).with_fps(FPS)
    clips.append(outro_clip)

    # Concatenate video
    print("  Rendering video...")
    video = concatenate_videoclips(clips, method="compose")

    # Sync to audio — trim or extend
    vid_dur = video.duration
    if vid_dur > total_dur + 10:
        video = video.subclipped(0, total_dur + 5)

    # Add full audio
    video = video.with_audio(full_audio)

    out_path = VIDEO_DIR / f"{date}-ep{ep_num:03d}-{slug}.mp4"
    print(f"  Encoding: {out_path.name}...")
    video.write_videofile(
        str(out_path), fps=FPS, codec="libx264",
        audio_codec="aac", threads=4, preset="fast", logger=None
    )
    video.close()
    full_audio.close()
    print(f"  Done: {out_path.name} ({out_path.stat().st_size//1024//1024}MB)")

    # Make 60s vertical short
    _make_short(out_path, ep_num, slug, title, date)

    # Copy to iCloud
    _to_icloud(out_path, ep_num, title, is_fiction)
    return out_path

def _make_short(video_path, ep_num, slug, title, date):
    """Cut first 60s, crop to vertical 9:16."""
    try:
        vid = VideoFileClip(str(video_path))
        clip = vid.subclipped(0, min(58, vid.duration))

        # Center crop to vertical
        crop_w = int(clip.h * SHORTS_W / SHORTS_H)
        x1 = max(0, (clip.w - crop_w) // 2)
        clip = clip.cropped(x1=x1, x2=x1+crop_w).resized((SHORTS_W, SHORTS_H))

        out = SHORTS_DIR / f"{date}-ep{ep_num:03d}-short-{slug}.mp4"
        clip.write_videofile(str(out), fps=FPS, codec="libx264",
                            audio_codec="aac", logger=None, preset="fast")
        clip.close()
        vid.close()
        print(f"  Short: {out.name}")
        _to_icloud(out, ep_num, f"{title} [SHORT]", False, folder="Dark Files Shorts")
    except Exception as e:
        print(f"  Short failed: {e}")

def _to_icloud(path, ep_num, title, is_fiction, folder="Dark Files Videos"):
    import shutil
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs" / folder
    icloud.mkdir(exist_ok=True)
    prefix = "[FICTION] " if is_fiction else ""
    dest = icloud / f"EP{ep_num:03d} - {prefix}{title[:55]}.mp4"
    shutil.copy(path, dest)
    print(f"  → iCloud: {dest.name}")

if __name__ == "__main__":
    from moviepy import VideoFileClip
    scripts = sorted(SCRIPTS_DIR.glob("ep*.json"))
    episodes = sorted(EPISODES_DIR.glob("ep*.mp3"))
    if not scripts or not episodes:
        print("Run generate_episode.py and produce_episode.py first.")
        sys.exit(1)
    # Match latest script to latest episode
    script_path = scripts[-1]
    audio_path = episodes[-1]
    build_video(script_path, audio_path)
