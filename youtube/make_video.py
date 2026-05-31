#!/usr/bin/env python3
"""
Builds a 1080p YouTube video from a script JSON file.
Flow: script → TTS audio → slide images → combine → MP4
"""
import json
import sys
import subprocess
import textwrap
from pathlib import Path
from datetime import datetime
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

W, H = 1920, 1080
FPS = 24

PALETTE = {
    "bg_dark":    "#0f0f1a",
    "bg_card":    "#1a1a2e",
    "accent":     "#6c63ff",
    "accent2":    "#ff6584",
    "text":       "#ffffff",
    "subtext":    "#b0b0cc",
    "highlight":  "#ffd700",
}

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def get_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                from PIL import ImageFont
                return ImageFont.truetype(p, size)
            except:
                pass
    from PIL import ImageFont
    return ImageFont.load_default()

def draw_gradient_bg(img):
    draw = ImageDraw.Draw(img)
    top = hex_to_rgb(PALETTE["bg_dark"])
    bot = hex_to_rgb(PALETTE["bg_card"])
    for y in range(H):
        r = int(top[0] + (bot[0]-top[0]) * y/H)
        g = int(top[1] + (bot[1]-top[1]) * y/H)
        b = int(top[2] + (bot[2]-top[2]) * y/H)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

def draw_accent_bar(draw, y=8):
    draw.rectangle([0, 0, W, y], fill=hex_to_rgb(PALETTE["accent"]))
    draw.rectangle([0, H-y, W, H], fill=hex_to_rgb(PALETTE["accent"]))

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = ' '.join(current + [word])
        bbox = draw.textbbox((0,0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))
    return lines

def make_title_slide(title, channel="AI Money Tools"):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(img)
    draw_accent_bar(draw)

    # Decorative circle
    draw.ellipse([W//2-300, H//2-300, W//2+300, H//2+300],
                 fill=(*hex_to_rgb(PALETTE["accent"]), 30) if False else hex_to_rgb("#16162a"))

    # Channel name
    f_ch = get_font(36)
    draw.text((W//2, 120), channel, font=f_ch, fill=hex_to_rgb(PALETTE["accent"]), anchor="mm")

    # Title
    f_title = get_font(72, bold=True)
    lines = wrap_text(title, f_title, W - 200, draw)
    total_h = len(lines) * 90
    y = H//2 - total_h//2
    for line in lines:
        draw.text((W//2, y), line, font=f_title, fill=hex_to_rgb(PALETTE["text"]), anchor="mm")
        y += 90

    # Divider
    draw.rectangle([W//2-200, H//2+total_h//2+30, W//2+200, H//2+total_h//2+36],
                   fill=hex_to_rgb(PALETTE["accent"]))
    return img

def make_content_slide(section_title, body_text, section_num, total_sections):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(img)
    draw_accent_bar(draw)

    # Progress bar
    progress = section_num / total_sections
    draw.rectangle([0, 8, int(W*progress), 16], fill=hex_to_rgb(PALETTE["accent2"]))

    # Section number badge
    f_badge = get_font(28, bold=True)
    badge_text = f"  {section_num} / {total_sections}  "
    draw.rounded_rectangle([60, 60, 60+len(badge_text)*18, 110], radius=25,
                            fill=hex_to_rgb(PALETTE["accent"]))
    draw.text((60+len(badge_text)*9, 85), badge_text, font=f_badge,
              fill=hex_to_rgb(PALETTE["text"]), anchor="mm")

    # Section title
    f_head = get_font(64, bold=True)
    draw.text((W//2, 180), section_title, font=f_head,
              fill=hex_to_rgb(PALETTE["highlight"]), anchor="mm")

    # Divider
    draw.rectangle([W//2-300, 220, W//2+300, 226], fill=hex_to_rgb(PALETTE["accent"]))

    # Body text
    f_body = get_font(38)
    sentences = [s.strip() for s in body_text.replace('\n', ' ').split('.') if s.strip()][:5]
    y = 280
    for sentence in sentences:
        lines = wrap_text(f"• {sentence}.", f_body, W - 200, draw)
        for line in lines:
            if y < H - 100:
                draw.text((120, y), line, font=f_body,
                          fill=hex_to_rgb(PALETTE["subtext"]))
                y += 58
        y += 10

    return img

def make_outro_slide(title, channel="AI Money Tools"):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    draw_gradient_bg(img)
    draw_accent_bar(draw)

    f_big = get_font(80, bold=True)
    f_sub = get_font(44)
    f_sm = get_font(36)

    draw.text((W//2, H//2 - 160), "Thanks for watching!", font=f_big,
              fill=hex_to_rgb(PALETTE["text"]), anchor="mm")
    draw.rectangle([W//2-250, H//2-100, W//2+250, H//2-94],
                   fill=hex_to_rgb(PALETTE["accent"]))
    draw.text((W//2, H//2 - 20), "👍 Like  •  🔔 Subscribe  •  💬 Comment",
              font=f_sub, fill=hex_to_rgb(PALETTE["highlight"]), anchor="mm")
    draw.text((W//2, H//2 + 80), channel, font=f_sub,
              fill=hex_to_rgb(PALETTE["accent"]), anchor="mm")
    draw.text((W//2, H//2 + 160), "New videos every week", font=f_sm,
              fill=hex_to_rgb(PALETTE["subtext"]), anchor="mm")
    return img

def text_to_speech(text, path):
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(str(path))

def get_audio_duration(path):
    clip = AudioFileClip(str(path))
    dur = clip.duration
    clip.close()
    return dur

def build_video(script_path):
    with open(script_path) as f:
        script = json.load(f)

    date = datetime.now().strftime("%Y-%m-%d")
    fname = script.get("filename", "video")
    out_dir = Path("youtube/video")
    audio_dir = Path("youtube/audio") / fname
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    title = script.get("title", "AI Money Tips")
    sections = script.get("sections", [])
    section_titles = script.get("section_titles", [f"Tip {i+1}" for i in range(len(sections))])
    hook = script.get("hook", "")
    intro = script.get("intro", "")
    outro = script.get("outro", "")

    print("Generating TTS audio...")
    segments = []

    # Hook + intro
    hook_intro_text = f"{hook} {intro}"
    hook_audio = audio_dir / "00_hook.mp3"
    text_to_speech(hook_intro_text, hook_audio)
    segments.append(("title", title, hook_audio))

    # Sections
    for i, (sec_text, sec_title) in enumerate(zip(sections, section_titles)):
        audio_path = audio_dir / f"{i+1:02d}_section.mp3"
        text_to_speech(f"{sec_title}. {sec_text}", audio_path)
        segments.append(("section", (sec_title, sec_text, i+1, len(sections)), audio_path))

    # Outro
    outro_audio = audio_dir / "99_outro.mp3"
    text_to_speech(outro, outro_audio)
    segments.append(("outro", title, outro_audio))

    print("Building video clips...")
    clips = []

    for seg_type, seg_data, audio_path in segments:
        duration = get_audio_duration(audio_path)

        if seg_type == "title":
            img = make_title_slide(seg_data)
        elif seg_type == "section":
            sec_title, sec_text, num, total = seg_data
            img = make_content_slide(sec_title, sec_text, num, total)
        else:
            img = make_outro_slide(seg_data)

        img_path = audio_dir / f"slide_{seg_type}.png"
        img.save(str(img_path))

        video_clip = ImageClip(str(img_path)).with_duration(duration).with_fps(FPS)
        audio_clip = AudioFileClip(str(audio_path))
        video_clip = video_clip.with_audio(audio_clip)
        clips.append(video_clip)

    print("Rendering final video...")
    final = concatenate_videoclips(clips, method="compose")
    out_path = out_dir / f"{date}-{fname}.mp4"
    final.write_videofile(str(out_path), fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None)

    for clip in clips:
        clip.close()
    final.close()

    print(f"Video saved: {out_path}")
    return out_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        scripts = sorted(Path("youtube/scripts").glob("*.json"))
        if not scripts:
            print("No scripts found. Run generate_script.py first.")
            sys.exit(1)
        script_path = scripts[-1]
    else:
        script_path = Path(sys.argv[1])

    build_video(script_path)
