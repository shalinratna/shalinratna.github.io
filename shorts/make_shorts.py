#!/usr/bin/env python3
"""
Short-form video factory — TikTok / Instagram Reels / YouTube Shorts
Generates 5 videos per day, ready to post. Saves to iCloud automatically.

Formats:
  - "Did You Know" finance facts (15-30s)
  - "POV" money story (30-45s)
  - AI tip of the day (20-30s)
  - Talking animal (15-20s)
  - Quote card (10-15s)
"""
import asyncio
import json
import subprocess
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_client import generate as ai

W, H = 1080, 1920  # Vertical 9:16

ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Shorts - Post These"
VIDEO_DIR = Path("shorts/output")
POSTED_LOG = Path("shorts/posted.json")

# ── Colour palettes per video type ───────────────────────────────────
PALETTES = {
    "fact":    {"bg": (8,8,20),    "accent": (255,200,0),    "text": (255,255,255), "sub": (180,180,200)},
    "tip":     {"bg": (5,20,8),    "accent": (50,220,80),    "text": (255,255,255), "sub": (160,220,170)},
    "pov":     {"bg": (20,5,20),   "accent": (200,100,255),  "text": (255,255,255), "sub": (200,180,220)},
    "animal":  {"bg": (20,12,5),   "accent": (255,150,50),   "text": (255,255,255), "sub": (220,200,160)},
    "quote":   {"bg": (5,5,5),     "accent": (255,255,255),  "text": (255,255,255), "sub": (150,150,150)},
}

ANIMAL_EMOJI = ["🐱", "🐶", "🐸", "🦊", "🐼", "🐨", "🦁", "🐯", "🐺", "🦝"]

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
        test = ' '.join(cur + [w])
        if draw.textbbox((0,0), test, font=fnt)[2] > max_w and cur:
            lines.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(' '.join(cur))
    return lines

def make_gradient(p, w=W, h=H):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    bg = p["bg"]
    acc = p["accent"]
    for y in range(h):
        t = y / h
        r = int(bg[0] + (acc[0]-bg[0]) * t * 0.15)
        g = int(bg[1] + (acc[1]-bg[1]) * t * 0.15)
        b = int(bg[2] + (acc[2]-bg[2]) * t * 0.15)
        img[y] = [r, g, b]
    # Vignette
    cx, cy = w/2, h/2
    Y, X = np.ogrid[:h, :w]
    vig = np.clip(1 - np.sqrt((X-cx)**2+(Y-cy)**2)/(max(w,h)*0.75), 0, 1)
    for c in range(3): img[:,:,c] = (img[:,:,c]*vig).astype(np.uint8)
    return img

# ── Video type makers ─────────────────────────────────────────────────

def make_fact_video(hook, fact, source="", p_key="fact"):
    """Did You Know style — hook + fact reveal."""
    p = PALETTES[p_key]
    frames = []
    total_frames = FPS * 28

    for i in range(total_frames):
        t = i / total_frames
        bg = make_gradient(p)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        # Top bar
        draw.rectangle([0, 0, W, 8], fill=p["accent"])

        # "DID YOU KNOW?" badge
        f_badge = font(32, bold=True)
        badge = "💡 DID YOU KNOW?"
        bw = draw.textbbox((0,0), badge, font=f_badge)[2] + 40
        draw.rounded_rectangle([W//2-bw//2, 120, W//2+bw//2, 175],
                               radius=25, fill=p["accent"])
        draw.text((W//2, 147), badge, font=f_badge, fill=p["bg"], anchor="mm")

        # Hook (appears first 10s)
        if t < 0.4:
            alpha = min(1.0, t / 0.08)
            f_hook = font(68, bold=True)
            hook_lines = wrap(hook.upper(), f_hook, W-80, draw)
            y = H//2 - (len(hook_lines)*85)//2
            for line in hook_lines:
                c = tuple(int(c*alpha) for c in p["text"])
                draw.text((W//2+2, y+2), line, font=f_hook, fill=(0,0,0), anchor="mm")
                draw.text((W//2, y), line, font=f_hook, fill=c, anchor="mm")
                y += 85
        else:
            # Fact reveal
            alpha = min(1.0, (t-0.4) / 0.1)
            f_fact = font(52)
            fact_lines = wrap(fact, f_fact, W-80, draw)
            y = H//2 - (len(fact_lines)*70)//2
            for line in fact_lines:
                c = tuple(int(c*alpha) for c in p["sub"])
                draw.text((W//2+1, y+1), line, font=f_fact, fill=(0,0,0), anchor="mm")
                draw.text((W//2, y), line, font=f_fact, fill=c, anchor="mm")
                y += 70

        # CTA bottom
        f_cta = font(30, bold=True)
        draw.text((W//2, H-80), "Follow for daily money facts 💰",
                 font=f_cta, fill=p["accent"], anchor="mm")

        # Progress bar
        draw.rectangle([0, H-8, int(W*t), H], fill=p["accent"])
        frames.append(np.array(img))

    return frames

def make_animal_video(animal_emoji, voiceover_text, p_key="animal"):
    """Cute animal face + funny/wise voiceover about money."""
    p = PALETTES[p_key]
    frames = []
    total_frames = FPS * 18

    for i in range(total_frames):
        t = i / total_frames
        bg = make_gradient(p)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, W, 8], fill=p["accent"])

        # Giant animal emoji — the "face"
        f_animal = font(320, bold=True)
        # Slight bobbing animation
        bob = int(np.sin(t * 8 * np.pi) * 12)
        draw.text((W//2, H//3 - 60 + bob), animal_emoji,
                 font=f_animal, anchor="mm")

        # Speech bubble effect for voiceover text
        if t > 0.15:
            alpha = min(1.0, (t-0.15)/0.1)
            # Bubble background
            f_speech = font(48)
            speech_lines = wrap(voiceover_text, f_speech, W-120, draw)
            text_h = len(speech_lines) * 65 + 40
            bub_y = H//2 + 80
            draw.rounded_rectangle([40, bub_y, W-40, bub_y+text_h],
                                   radius=20, fill=(255,255,255,0) if False else (30,25,20))
            # Bubble pointer
            draw.polygon([(W//2-30, bub_y), (W//2+30, bub_y), (W//2, bub_y-25)],
                        fill=(30,25,20))
            y = bub_y + 20
            for line in speech_lines:
                c = tuple(int(c*alpha) for c in p["text"])
                draw.text((W//2, y), line, font=f_speech, fill=c, anchor="mm")
                y += 65

        # Channel name
        f_ch = font(28, bold=True)
        draw.text((W//2, H-75), "AI Money Tools 💰",
                 font=f_ch, fill=p["accent"], anchor="mm")

        frames.append(np.array(img))

    return frames

def make_pov_video(pov_hook, steps, p_key="pov"):
    """POV you did something with AI — storytelling format."""
    p = PALETTES[p_key]
    frames = []
    total_frames = FPS * 45

    all_text = [pov_hook] + steps
    text_dur = total_frames // len(all_text)

    for i in range(total_frames):
        t = i / total_frames
        bg = make_gradient(p)
        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, W, 8], fill=p["accent"])

        # POV header
        f_pov = font(52, bold=True)
        draw.text((W//2, 130), "POV:", font=f_pov, fill=p["accent"], anchor="mm")

        # Current text segment
        seg = min(int(i / text_dur), len(all_text)-1)
        text = all_text[seg]
        seg_t = (i % text_dur) / text_dur
        alpha = min(1.0, seg_t / 0.15)

        f_main = font(62, bold=True) if seg == 0 else font(54)
        lines = wrap(text, f_main, W-80, draw)
        y = H//2 - (len(lines)*80)//2
        for line in lines:
            c = tuple(int(c*alpha) for c in (p["text"] if seg == 0 else p["sub"]))
            draw.text((W//2+2, y+2), line, font=f_main, fill=(0,0,0), anchor="mm")
            draw.text((W//2, y), line, font=f_main, fill=c, anchor="mm")
            y += 80

        # Step indicator
        if seg > 0:
            f_step = font(30)
            draw.text((W//2, H-110), f"Step {seg} of {len(steps)}",
                     font=f_step, fill=p["accent"], anchor="mm")

        f_cta = font(28)
        draw.text((W//2, H-65), "Follow for more AI money tips 🚀",
                 font=f_cta, fill=p["sub"], anchor="mm")

        draw.rectangle([0, H-8, int(W*t), H], fill=p["accent"])
        frames.append(np.array(img))

    return frames

FPS = 30

async def tts_async(text, out_path, voice="en-US-AriaNeural", rate="+10%"):
    text = ' '.join(text.replace('"',"'").replace('&','and').split())
    if not text: return
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(out_path))

def tts(text, out_path, voice="en-US-AriaNeural", rate="+10%"):
    asyncio.run(tts_async(text, out_path, voice, rate))

def frames_to_video(frames, audio_path, out_path):
    """Convert frame array + audio to MP4."""
    import tempfile, os
    tmp_frames = Path("shorts/tmp_frames")
    tmp_frames.mkdir(parents=True, exist_ok=True)

    # Write frames as PNG sequence
    for i, frame in enumerate(frames):
        Image.fromarray(frame).save(str(tmp_frames / f"frame_{i:05d}.png"))

    # Combine with ffmpeg
    dur = get_audio_duration(audio_path)
    n_frames = len(frames)
    fps_actual = n_frames / dur if dur > 0 else FPS

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps_actual),
        "-i", str(tmp_frames / "frame_%05d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-pix_fmt", "yuv420p",
        str(out_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    # Cleanup
    for f in tmp_frames.glob("*.png"):
        f.unlink()

def get_audio_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                       '-show_format', str(path)], capture_output=True, text=True)
    try: return float(json.loads(r.stdout)['format']['duration'])
    except: return 20.0

def to_icloud(path, name):
    import shutil
    ICLOUD.mkdir(exist_ok=True)
    dest = ICLOUD / name
    shutil.copy(path, dest)
    print(f"  → iCloud: {name}")

def generate_daily_scripts():
    """Use Claude to generate today's 5 short-form video scripts."""
    prompt = """Generate 5 short-form video scripts for TikTok/Instagram Reels/YouTube Shorts about AI tools and making money.

Reply in this EXACT JSON format:
{
  "videos": [
    {
      "type": "fact",
      "hook": "SHOCKING one-liner question or stat — all caps, 6 words max",
      "fact": "The surprising answer — 1-2 sentences, specific with numbers",
      "voiceover": "Full voiceover script — casual, exciting, 40-60 words"
    },
    {
      "type": "animal",
      "animal": "🐱",
      "voiceover": "What the animal is 'saying' — funny, wise comment about money or AI — 30-40 words, first person"
    },
    {
      "type": "pov",
      "hook": "POV: you just [did something with AI] and made money",
      "steps": ["Step 1 result", "Step 2 result", "Step 3 result — the payoff"],
      "voiceover": "Full voiceover — 50-70 words, storytelling format"
    },
    {
      "type": "fact",
      "hook": "Another shocking hook",
      "fact": "Another surprising fact about AI or money",
      "voiceover": "40-60 word voiceover"
    },
    {
      "type": "animal",
      "animal": "🐶",
      "voiceover": "Dog saying something funny and wise about passive income — 30-40 words"
    }
  ]
}

Make the content genuinely interesting and surprising. Real numbers. Specific AI tools. Things people would screenshot and share."""

    raw = ai(prompt, model="sonnet", max_tokens=2000)
    # Extract JSON
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        return json.loads(m.group())
    return None

def produce_video(script, idx, date):
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    audio_dir = Path("shorts/audio")
    audio_dir.mkdir(exist_ok=True)

    vtype = script.get("type", "fact")
    audio_path = audio_dir / f"{date}_{idx:02d}_{vtype}.mp3"

    voiceover = script.get("voiceover", "")
    if not voiceover:
        if vtype == "fact":
            voiceover = f"{script.get('hook','')}. {script.get('fact','')}"
        elif vtype == "pov":
            voiceover = f"{script.get('hook','')}. {'. '.join(script.get('steps',[]))}"

    # Generate audio
    voice = "en-US-GuyNeural" if vtype == "animal" else "en-US-AriaNeural"
    rate = "+15%" if vtype == "animal" else "+10%"
    tts(voiceover, audio_path, voice=voice, rate=rate)

    # Generate frames
    if vtype == "fact":
        frames = make_fact_video(
            script.get("hook", "YOU WON'T BELIEVE THIS"),
            script.get("fact", ""),
        )
    elif vtype == "animal":
        frames = make_animal_video(
            script.get("animal", "🐱"),
            script.get("voiceover", ""),
        )
    elif vtype == "pov":
        frames = make_pov_video(
            script.get("hook", ""),
            script.get("steps", []),
        )
    else:
        frames = make_fact_video(
            script.get("hook", ""),
            script.get("fact", ""),
        )

    out_name = f"{date}_{idx:02d}_{vtype}.mp4"
    out_path = VIDEO_DIR / out_name
    frames_to_video(frames, audio_path, out_path)
    to_icloud(out_path, out_name)
    print(f"  Video {idx}: {vtype} — {out_path.name}")
    return out_path

def main():
    date = datetime.now().strftime("%Y-%m-%d")
    print(f"Generating 5 short-form videos for {date}...")

    scripts = generate_daily_scripts()
    if not scripts:
        print("Script generation failed.")
        return

    for i, script in enumerate(scripts.get("videos", []), 1):
        try:
            produce_video(script, i, date)
        except Exception as e:
            print(f"  Video {i} failed: {e}")

    print(f"\nDone! Check iCloud Drive → 'Shorts - Post These'")
    print("Post them to TikTok, Reels, and YouTube Shorts manually — takes 5 min")

if __name__ == "__main__":
    main()
