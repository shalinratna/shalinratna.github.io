#!/usr/bin/env python3
"""
Tiny Tales — Video producer.
Generates animated-style scenes: cute characters, colorful backgrounds,
speech bubbles, smooth transitions. Saves full episode + 60s short to iCloud.
"""
import asyncio, json, subprocess, sys, random
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

sys.path.insert(0, str(Path(__file__).parent.parent))

SCRIPTS_DIR  = Path("tinytales/scripts")
AUDIO_DIR    = Path("tinytales/audio")
OUTPUT_DIR   = Path("tinytales/output")
SHORTS_DIR   = Path("tinytales/shorts")
ICLOUD_LONG  = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Tiny Tales - YouTube"
ICLOUD_SHORT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Tiny Tales - Shorts"

W, H   = 1920, 1080
SW, SH = 1080, 1920
FPS    = 24

# ── Colour themes per setting ──────────────────────────────────────
THEMES = {
    "kitchen":  {"sky": (255,240,200), "ground": (210,180,140), "accent": (255,160,50)},
    "garden":   {"sky": (135,206,235), "ground": (100,180,80),  "accent": (255,200,0)},
    "forest":   {"sky": (100,160,100), "ground": (60,120,60),   "accent": (255,220,100)},
    "night":    {"sky": (20,20,60),    "ground": (40,30,80),    "accent": (255,230,100)},
    "school":   {"sky": (220,235,255), "ground": (180,200,220), "accent": (80,160,255)},
    "default":  {"sky": (200,230,255), "ground": (150,200,150), "accent": (255,200,50)},
}

def get_theme(setting):
    s = setting.lower()
    if any(w in s for w in ["kitchen","counter","dinner","table","fridge"]): return THEMES["kitchen"]
    if any(w in s for w in ["garden","patch","vegetable","sunny","outdoor"]): return THEMES["garden"]
    if any(w in s for w in ["forest","clearing","tree","wood"]): return THEMES["forest"]
    if any(w in s for w in ["night","sky","moon","star"]): return THEMES["night"]
    if any(w in s for w in ["school","class","desk","drawer","box"]): return THEMES["school"]
    return THEMES["default"]

def font(size, bold=False):
    for p in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def wrap(text, fnt, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        if draw.textbbox((0,0), ' '.join(cur+[w]), font=fnt)[2] > max_w and cur:
            lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines

# ── Scene rendering ────────────────────────────────────────────────

def draw_background(draw, theme, w=W, h=H):
    """Simple illustrated background."""
    sky = theme["sky"]
    ground = theme["ground"]
    horizon = int(h * 0.62)
    # Sky
    for y in range(horizon):
        t = y/horizon
        r = int(sky[0] * (1-t*0.2))
        g = int(sky[1] * (1-t*0.1))
        b = int(sky[2])
        draw.line([(0,y),(w,y)], fill=(r,g,b))
    # Ground
    for y in range(horizon, h):
        t = (y-horizon)/(h-horizon)
        r = int(ground[0] * (1-t*0.3))
        g = int(ground[1] * (1-t*0.3))
        b = int(ground[2] * (1-t*0.3))
        draw.line([(0,y),(w,y)], fill=(r,g,b))
    # Ground line
    draw.ellipse([-100, horizon-30, w+100, horizon+60],
                fill=tuple(int(c*0.9) for c in ground))

def draw_clouds(draw, t, theme, w=W, h=H):
    """Slowly moving clouds."""
    cloud_color = (255, 255, 255, 180)
    offsets = [(int((t*15 + x*350) % (w+200)) - 100, y)
               for x, y in enumerate([80, 130, 60, 110])]
    for cx, cy in offsets:
        for dx, dy, r in [(-40,0,55),(0,-20,65),(40,0,55),(80,0,50),(-80,10,45)]:
            draw.ellipse([cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r],
                        fill=(240,245,255))

def draw_character(draw, emoji, x, y, size, expression="happy", bounce=0):
    """Draw an emoji character with a simple body."""
    f_emoji = font(size)
    # Shadow
    draw.ellipse([x-size//3, y+size-15, x+size//3, y+size+5], fill=(0,0,0,60) if False else (100,120,80))
    # Character
    draw.text((x, y+bounce), emoji, font=f_emoji, anchor="mm")

def draw_speech_bubble(draw, text, x, y, pointing="left", color=(255,255,255), w=W, h=H):
    """Draw a speech bubble with text."""
    f_text = font(36)
    lines = wrap(text, f_text, 500, draw)
    pad = 20
    line_h = 48
    bw = min(540, max(200, max(draw.textbbox((0,0), l, font=f_text)[2] for l in lines) + pad*2))
    bh = len(lines) * line_h + pad*2

    # Position bubble to stay on screen
    bx = max(20, min(x-bw//2, w-bw-20))
    by = max(20, y - bh - 40)

    # Bubble body
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=20, fill=color,
                           outline=(200,200,220), width=3)
    # Pointer
    px = max(bx+30, min(x, bx+bw-30))
    py_top = by+bh
    draw.polygon([(px-15, py_top), (px+15, py_top), (px, py_top+25)], fill=color)

    # Text
    ty = by + pad
    for line in lines:
        draw.text((bx+pad, ty), line, font=f_text, fill=(30,30,50))
        ty += line_h

def draw_scene_text(draw, text, w=W, h=H):
    """Narrator text at bottom of screen."""
    f = font(34)
    lines = wrap(text, f, w-120, draw)
    # Background bar
    draw.rectangle([0, h-130, w, h], fill=(0,0,0,180) if False else (20,18,35))
    draw.rectangle([0, h-132, w, h-130], fill=(255,200,50))
    y = h - 115
    for line in lines[:3]:
        draw.text((w//2, y), line, font=f, fill=(240,235,255), anchor="mm")
        y += 42

def draw_title_banner(draw, show_name, ep_title, w=W, h=H):
    """Show title and episode name."""
    draw.rectangle([0, 0, w, 100], fill=(255,200,50))
    f_show = font(42, bold=True)
    f_ep = font(32)
    draw.text((w//2, 30), show_name.upper(), font=f_show, fill=(30,20,10), anchor="mm")
    draw.text((w//2, 72), ep_title, font=f_ep, fill=(80,50,20), anchor="mm")

def make_frame(scene_data, t, w=W, h=H):
    """Render one video frame."""
    theme = scene_data["theme"]
    c1_emoji = scene_data["c1_emoji"]
    c2_emoji = scene_data["c2_emoji"]
    speaker = scene_data.get("speaker", "NARRATOR")
    text = scene_data.get("text", "")
    show_name = scene_data.get("show_name", "Tiny Tales")
    ep_title = scene_data.get("ep_title", "")
    title_card = scene_data.get("title_card", False)

    img = Image.new("RGB", (w, h), theme["sky"])
    draw = ImageDraw.Draw(img)
    draw_background(draw, theme, w, h)
    draw_clouds(draw, t, theme, w, h)

    # Characters with bounce animation
    bounce1 = int(np.sin(t*6)*5) if speaker == list(scene_data.get("c1_name",""))[0] else 0
    bounce2 = int(np.sin(t*6)*5) if speaker == list(scene_data.get("c2_name",""))[0] else 0

    char_y = int(h * 0.52)
    char_size = 140

    # Character 1 (left side)
    draw_character(draw, c1_emoji, int(w*0.28), char_y, char_size, bounce=bounce1)
    # Character 2 (right side)
    draw_character(draw, c2_emoji, int(w*0.72), char_y, char_size, bounce=bounce2)

    # Character names
    f_name = font(28, bold=True)
    draw.text((int(w*0.28), char_y+char_size+15), scene_data.get("c1_name",""),
             font=f_name, fill=(60,40,20), anchor="mm")
    draw.text((int(w*0.72), char_y+char_size+15), scene_data.get("c2_name",""),
             font=f_name, fill=(60,40,20), anchor="mm")

    # Speech bubble or narrator box
    if text:
        if speaker == "NARRATOR":
            draw_scene_text(draw, text, w, h)
        elif speaker == scene_data.get("c1_name"):
            draw_speech_bubble(draw, text, int(w*0.28), char_y-20, w=w, h=h)
        elif speaker == scene_data.get("c2_name"):
            draw_speech_bubble(draw, text, int(w*0.72), char_y-20, w=w, h=h,
                              color=(255,240,220))

    # Title banner
    if ep_title:
        draw_title_banner(draw, show_name, ep_title, w, h)

    # Title card overlay
    if title_card:
        overlay = Image.new("RGBA", (w,h), (0,0,0,160))
        img = Image.composite(overlay.convert("RGB"), img,
                             Image.new("L", (w,h), 160))
        draw = ImageDraw.Draw(img)
        f_tt = font(110, bold=True)
        f_sub = font(50)
        draw.text((w//2, h//2-80), show_name.upper(), font=f_tt,
                 fill=(255,200,50), anchor="mm")
        draw.text((w//2, h//2+40), f"Episode {scene_data.get('ep_num',1)}",
                 font=f_sub, fill=(255,255,255), anchor="mm")
        draw.text((w//2, h//2+105), ep_title,
                 font=f_sub, fill=(220,220,240), anchor="mm")

    return np.array(img)

# ── Audio ──────────────────────────────────────────────────────────

async def speak_async(text, voice, out_path, rate="-5%"):
    text = ' '.join(text.replace('"',"'").replace('&','and').split())
    if not text: return
    c = edge_tts.Communicate(text, voice=voice, rate=rate)
    await c.save(str(out_path))

def speak(text, voice, out_path, rate="-5%"):
    asyncio.run(speak_async(text, voice, out_path, rate))

def get_duration(path):
    r = subprocess.run(['ffprobe','-v','quiet','-print_format','json',
                       '-show_format',str(path)], capture_output=True, text=True)
    try: return float(json.loads(r.stdout)['format']['duration'])
    except: return 4.0

def frames_to_video(frames, audio_path, out_path):
    tmp = Path("tinytales/tmp")
    tmp.mkdir(exist_ok=True)
    for i, f in enumerate(frames):
        Image.fromarray(f).save(str(tmp/f"f{i:06d}.png"))
    dur = get_duration(audio_path)
    fps = len(frames)/dur if dur > 0 else FPS
    subprocess.run([
        "ffmpeg","-y","-framerate",str(fps),
        "-i",str(tmp/"f%06d.png"),"-i",str(audio_path),
        "-c:v","libx264","-c:a","aac","-shortest","-pix_fmt","yuv420p",
        str(out_path)
    ], capture_output=True, check=True)
    for f in tmp.glob("*.png"): f.unlink()

# ── Main producer ──────────────────────────────────────────────────

def produce(script_path):
    script = json.loads(Path(script_path).read_text())
    ep_num  = script["ep_num"]
    title   = script["title"]
    slug    = script["slug"]
    date    = script["date"]
    c1      = script["char1"]
    c2      = script["char2"]
    dialogue= script["dialogue"]
    setting = script.get("setting","")
    lesson  = script.get("lesson","")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SHORTS_DIR.mkdir(parents=True, exist_ok=True)

    theme = get_theme(setting)
    show_name = "Tiny Tales"

    print(f"Producing: EP{ep_num:03d} — {title}")
    print(f"  {c1['emoji']} {c1['name']}  +  {c2['emoji']} {c2['name']}")

    # Generate audio for each line
    print("  Generating voices...")
    audio_parts = []
    work_audio = AUDIO_DIR / f"ep{ep_num:03d}"
    work_audio.mkdir(exist_ok=True)

    for i, line in enumerate(dialogue):
        spk = line["speaker"]
        txt = line["text"]
        if spk == "NARRATOR":
            voice = "en-US-JennyNeural"
            rate  = "-8%"
        elif spk == c1["name"]:
            voice = c1["voice"]
            rate  = "-5%"
        else:
            voice = c2["voice"]
            rate  = "-5%"

        ap = work_audio / f"{i:03d}.mp3"
        if not ap.exists():
            speak(txt, voice, ap, rate)
        if ap.exists():
            audio_parts.append((i, line, ap))

    if not audio_parts:
        print("  No audio generated — check API key")
        return

    # Concatenate all audio
    combined_audio = work_audio / "combined.mp3"
    lst = work_audio / "list.txt"
    lst.write_text('\n'.join(f"file '{p.resolve()}'" for _,_,p in audio_parts))
    subprocess.run(['ffmpeg','-f','concat','-safe','0','-i',str(lst),
                   '-c','copy','-y',str(combined_audio)], capture_output=True)

    total_dur = get_duration(combined_audio)
    print(f"  Total duration: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # Render frames
    print("  Rendering frames...")
    all_frames = []

    # Title card (3 seconds)
    scene = {"theme":theme,"c1_emoji":c1["emoji"],"c2_emoji":c2["emoji"],
             "c1_name":c1["name"],"c2_name":c2["name"],
             "show_name":show_name,"ep_title":title,"ep_num":ep_num,
             "speaker":"","text":"","title_card":True}
    for f in range(FPS*3):
        all_frames.append(make_frame(scene, f/FPS))

    # Story frames — time each slide to its audio
    time_per_line = total_dur / len(audio_parts)
    for idx, (i, line, ap) in enumerate(audio_parts):
        line_dur = get_duration(ap)
        n_frames = max(FPS*2, int(line_dur * FPS))
        scene = {"theme":theme,"c1_emoji":c1["emoji"],"c2_emoji":c2["emoji"],
                "c1_name":c1["name"],"c2_name":c2["name"],
                "show_name":show_name,"ep_title":title,"ep_num":ep_num,
                "speaker":line["speaker"],"text":line["text"],"title_card":False}
        for f in range(n_frames):
            all_frames.append(make_frame(scene, (f + idx*n_frames)/FPS))

    # Outro (3 seconds)
    outro_scene = {**scene, "text": f"The End! Remember: {lesson}", "speaker":"NARRATOR"}
    for f in range(FPS*3):
        all_frames.append(make_frame(outro_scene, f/FPS))

    # Render full video
    out_path = OUTPUT_DIR / f"{date}-ep{ep_num:03d}-{slug}.mp4"
    print(f"  Encoding video...")
    frames_to_video(all_frames, combined_audio, out_path)
    print(f"  Done: {out_path.name} ({out_path.stat().st_size//1024//1024}MB)")

    # 60s short (vertical)
    _make_short(out_path, ep_num, slug, title, date)

    # Copy to iCloud
    import shutil
    ICLOUD_LONG.mkdir(exist_ok=True)
    ICLOUD_SHORT.mkdir(exist_ok=True)
    shutil.copy(out_path, ICLOUD_LONG / f"EP{ep_num:03d} - {title[:55]}.mp4")
    print(f"  → iCloud: Tiny Tales - YouTube")

    return out_path

def _make_short(video_path, ep_num, slug, title, date):
    """Crop to vertical 9:16, trim to 60s."""
    try:
        from moviepy import VideoFileClip
        vid = VideoFileClip(str(video_path))
        clip = vid.subclipped(0, min(58, vid.duration))
        cw = int(clip.h * SW/SH)
        x1 = max(0,(clip.w-cw)//2)
        clip = clip.cropped(x1=x1, x2=x1+cw).resized((SW,SH))
        out = SHORTS_DIR / f"{date}-ep{ep_num:03d}-short.mp4"
        clip.write_videofile(str(out), fps=FPS, codec="libx264",
                            audio_codec="aac", logger=None, preset="fast")
        clip.close(); vid.close()
        import shutil
        ICLOUD_SHORT.mkdir(exist_ok=True)
        shutil.copy(out, ICLOUD_SHORT / f"EP{ep_num:03d} - {title[:55]} [SHORT].mp4")
        print(f"  → iCloud: Tiny Tales - Shorts")
    except Exception as e:
        print(f"  Short failed: {e}")

if __name__ == "__main__":
    scripts = sorted(SCRIPTS_DIR.glob("ep*.json"))
    if not scripts:
        print("No scripts. Run generate_story.py first.")
        sys.exit(1)
    produce(scripts[-1])
