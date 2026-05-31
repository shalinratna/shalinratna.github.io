#!/usr/bin/env python3
"""
Professional video producer for Money Brain YouTube channel.
Uses real stock footage + neural TTS + text overlays + series branding.
"""
import json
import subprocess
import sys
import textwrap
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

W, H = 1920, 1080
FPS = 24
CHANNEL = "Money Brain"
BRAND_COLOR = (108, 99, 255)   # purple
ACCENT_COLOR = (255, 215, 0)   # gold
TEXT_COLOR = (255, 255, 255)
BG_OVERLAY = (0, 0, 0, 160)    # semi-transparent black

def get_font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
    ]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()

def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and cur:
            lines.append(' '.join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(' '.join(cur))
    return lines

def make_overlay_frame(title, subtitle="", section_num=None, total_sections=None,
                        show_channel=True, is_outro=False):
    """Creates a transparent overlay frame with text branding."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bottom gradient bar
    bar_h = 280
    for y in range(bar_h):
        alpha = int(200 * (1 - y / bar_h))
        draw.line([(0, H - bar_h + y), (W, H - bar_h + y)], fill=(0, 0, 0, alpha))

    # Top bar for channel branding
    if show_channel:
        draw.rectangle([0, 0, W, 70], fill=(0, 0, 0, 180))
        f_ch = get_font(32, bold=True)
        draw.text((30, 35), f"● {CHANNEL}", font=f_ch, fill=BRAND_COLOR, anchor="lm")
        if section_num and total_sections:
            draw.text((W - 30, 35), f"Ep • {section_num}/{total_sections}",
                     font=f_ch, fill=ACCENT_COLOR, anchor="rm")

    # Section label
    if subtitle:
        f_sub = get_font(38, bold=True)
        label_w = draw.textbbox((0, 0), subtitle, font=f_sub)[2] + 40
        draw.rounded_rectangle([40, H - bar_h + 20, 40 + label_w, H - bar_h + 75],
                               radius=8, fill=(*BRAND_COLOR, 230))
        draw.text((60, H - bar_h + 47), subtitle, font=f_sub,
                 fill=(255, 255, 255), anchor="lm")

    # Main title
    if title:
        f_title = get_font(72, bold=True) if len(title) < 40 else get_font(58, bold=True)
        lines = wrap_text(title, f_title, W - 100, draw)
        y = H - 180 if subtitle else H - 140
        for line in lines[:3]:
            # Shadow
            draw.text((52, y + 2), line, font=f_title, fill=(0, 0, 0, 200), anchor="lm")
            draw.text((50, y), line, font=f_title, fill=TEXT_COLOR, anchor="lm")
            y += 85

    # Outro elements
    if is_outro:
        draw.rectangle([0, 0, W, H], fill=(0, 0, 0, 200))
        f_big = get_font(90, bold=True)
        f_sub2 = get_font(48)
        draw.text((W//2, H//2 - 100), "Subscribe for more", font=f_big,
                 fill=TEXT_COLOR, anchor="mm")
        draw.text((W//2, H//2 + 20), "New episodes every week", font=f_sub2,
                 fill=ACCENT_COLOR, anchor="mm")
        draw.text((W//2, H//2 + 100), f"🔔 {CHANNEL}", font=f_sub2,
                 fill=BRAND_COLOR, anchor="mm")

    return overlay

def overlay_on_video(video_path, audio_path, title, subtitle="",
                     section_num=None, total=None, is_outro=False):
    """Takes stock footage + audio + text → returns composed clip."""
    audio_dur = AudioFileClip(str(audio_path)).duration

    if video_path and Path(video_path).exists():
        vid = VideoFileClip(str(video_path))
        # Loop video if shorter than audio
        if vid.duration < audio_dur:
            loops = int(audio_dur / vid.duration) + 1
            clips = [vid] * loops
            vid = concatenate_videoclips(clips).subclipped(0, audio_dur)
        else:
            vid = vid.subclipped(0, audio_dur)
        vid = vid.resized((W, H))
    else:
        # Fallback: solid color background as numpy array
        bg = np.zeros((H, W, 3), dtype=np.uint8)
        bg[:, :] = [15, 15, 30]
        vid = ImageClip(bg).with_duration(audio_dur).with_fps(FPS)

    # Create overlay — convert RGBA PIL image to numpy
    overlay_img = make_overlay_frame(title, subtitle, section_num, total, is_outro=is_outro)
    overlay_arr = np.array(overlay_img)
    overlay_clip = ImageClip(overlay_arr).with_duration(audio_dur).with_fps(FPS)

    # Composite
    composed = CompositeVideoClip([vid.with_fps(FPS), overlay_clip])

    # Add audio
    audio = AudioFileClip(str(audio_path))
    composed = composed.with_audio(audio).with_duration(audio_dur)

    return composed

def tts(text, output_path, voice="Samantha"):
    """macOS neural TTS — sounds natural, completely free."""
    # Clean text for say command
    text = text.replace('"', "'").replace('&', 'and').replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())  # normalize whitespace
    aiff = str(output_path).replace('.mp3', '.aiff')
    # Write text to temp file to avoid shell escaping issues
    tmp = Path(aiff).parent / "tmp_say.txt"
    tmp.write_text(text, encoding='utf-8')
    result = subprocess.run(['say', '-v', voice, '-o', aiff, '-f', str(tmp)],
                           capture_output=True, timeout=180)
    if result.returncode != 0:
        result2 = subprocess.run(['say', '-o', aiff, '-f', str(tmp)],
                                capture_output=True, timeout=180)
        if result2.returncode != 0:
            # Last resort: gTTS
            from gtts import gTTS
            gTTS(text=text, lang='en').save(str(output_path))
            tmp.unlink(missing_ok=True)
            return
    tmp.unlink(missing_ok=True)
    subprocess.run(['ffmpeg', '-i', aiff, '-y', str(output_path)],
                  capture_output=True, check=True)
    Path(aiff).unlink(missing_ok=True)

def make_thumbnail(script_data, out_path):
    """Eye-catching thumbnail with bold text."""
    thumbnail_text = script_data.get("thumbnail_text", script_data.get("title", "")[:30])
    ep = script_data.get("ep_num", 1)
    series = script_data.get("series_name", "")

    img = Image.new("RGB", (1280, 720), (10, 10, 20))
    draw = ImageDraw.Draw(img)

    # Gradient bg
    for y in range(720):
        r = int(15 + 20 * y/720)
        draw.line([(0,y),(1280,y)], fill=(r, 10, int(40 * y/720)))

    # Accent elements
    draw.ellipse([800, -100, 1400, 500], fill=(108, 99, 255, 40) if False else (20, 15, 60))
    draw.rectangle([0, 0, 1280, 8], fill=BRAND_COLOR)
    draw.rectangle([0, 712, 1280, 720], fill=ACCENT_COLOR)

    # Episode badge
    f_badge = get_font(36, bold=True)
    badge = f"EP. {ep:02d}"
    draw.rounded_rectangle([40, 40, 40+len(badge)*22+20, 95], radius=12, fill=BRAND_COLOR)
    draw.text((50+len(badge)*11, 67), badge, font=f_badge, fill=(255,255,255), anchor="mm")

    # Series name
    f_series = get_font(30)
    draw.text((40, 110), series.upper(), font=f_series, fill=ACCENT_COLOR, anchor="lm")

    # Main text — huge and bold
    words = thumbnail_text.upper().split()
    lines = []
    cur = []
    for w in words:
        if len(' '.join(cur + [w])) > 18 and cur:
            lines.append(' '.join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(' '.join(cur))

    f_main = get_font(130 if len(lines) <= 2 else 100, bold=True)
    y = 200
    for line in lines[:3]:
        draw.text((50, y+3), line, font=f_main, fill=(0,0,0), anchor="lm")  # shadow
        draw.text((50, y), line, font=f_main, fill=(255,255,255), anchor="lm")
        y += 140

    # Channel name bottom
    f_ch = get_font(40, bold=True)
    draw.text((640, 680), CHANNEL.upper(), font=f_ch, fill=BRAND_COLOR, anchor="mm")

    img.save(str(out_path), quality=95)
    print(f"Thumbnail: {out_path.name}")

def build_video(script_path, footage_map=None):
    script = json.loads(Path(script_path).read_text())

    fname = script.get("filename", "video")
    date = script.get("date", datetime.now().strftime("%Y-%m-%d"))
    ep = script.get("ep_num", 1)
    series = script.get("series_name", "")

    audio_dir = Path("youtube/audio") / fname
    video_dir = Path("youtube/video")
    thumb_dir = Path("youtube/thumbnails")
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    title = script.get("title", "")
    sections = script.get("sections", [])
    section_titles = script.get("section_titles", [])
    footage_keys = script.get("section_footage", [])
    hook = script.get("hook", "")
    intro = script.get("intro", "")
    outro = script.get("outro", "")
    total_secs = len(sections)

    # Pick best available voice
    voice = "Samantha"
    try:
        result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, timeout=10)
        voices_out = result.stdout + result.stderr
        for preferred in ["Ava", "Tom", "Alex", "Samantha"]:
            if preferred in voices_out:
                voice = preferred
                break
    except:
        pass

    print(f"Building: {title[:60]}")
    print(f"Voice: {voice} | Sections: {total_secs}")

    segments = []

    # Hook segment
    hook_audio = audio_dir / "00_hook.mp3"
    if not hook_audio.exists():
        print("  TTS: Hook...")
        tts(hook, hook_audio, voice)
    hook_footage = footage_map.get("hook") if footage_map else None
    segments.append(("hook", hook, "", hook_footage, hook_audio, None, None))

    # Intro segment
    intro_audio = audio_dir / "01_intro.mp3"
    if not intro_audio.exists():
        print("  TTS: Intro...")
        tts(intro, intro_audio, voice)
    intro_footage = footage_map.get("intro") if footage_map else None
    segments.append(("intro", title, "Introduction", intro_footage, intro_audio, None, None))

    # Content sections
    for i, (text, sec_title) in enumerate(zip(sections, section_titles)):
        audio_path = audio_dir / f"{i+2:02d}_section.mp3"
        if not audio_path.exists():
            print(f"  TTS: Section {i+1} — {sec_title[:40]}...")
            tts(text, audio_path, voice)
        footage_key = f"section_{i+1}"
        footage_path = footage_map.get(footage_key) if footage_map else None
        segments.append(("section", sec_title, f"Part {i+1}", footage_path, audio_path, i+1, total_secs))

    # Outro
    outro_audio = audio_dir / "99_outro.mp3"
    if not outro_audio.exists():
        print("  TTS: Outro...")
        tts(outro, outro_audio, voice)
    segments.append(("outro", "Subscribe", "", None, outro_audio, None, None))

    # Render clips
    print("  Rendering video clips...")
    clips = []
    for seg_type, seg_title, seg_sub, footage_path, audio_path, sec_num, total in segments:
        is_outro = seg_type == "outro"
        clip = overlay_on_video(
            footage_path, audio_path,
            seg_title if seg_type != "outro" else "",
            seg_sub, sec_num, total, is_outro
        )
        clips.append(clip)

    print("  Concatenating final video...")
    final = concatenate_videoclips(clips, method="compose")

    out_path = video_dir / f"{date}-ep{ep:02d}-{fname}.mp4"
    final.write_videofile(
        str(out_path), fps=FPS, codec="libx264",
        audio_codec="aac", threads=4, logger=None,
        preset="fast"
    )

    for c in clips:
        c.close()
    final.close()

    # Thumbnail
    thumb_path = thumb_dir / f"{date}-ep{ep:02d}-{fname}.jpg"
    make_thumbnail(script, thumb_path)

    print(f"  Done: {out_path.name} ({out_path.stat().st_size//1024//1024}MB)")
    return out_path, thumb_path

if __name__ == "__main__":
    from fetch_footage import fetch_for_script
    scripts = sorted(Path("youtube/scripts").glob("*.json"))
    if not scripts:
        print("No scripts. Run generate_script_v2.py first.")
        sys.exit(1)
    script_path = scripts[-1]
    script_data = json.loads(script_path.read_text())
    footage = fetch_for_script(script_data)
    build_video(script_path, footage)
