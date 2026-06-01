#!/usr/bin/env python3
"""
Tiny Tales — Full animated episode producer.
Hook → Title → Story (animated) → Lesson → CTA
Vertical 1080x1920 for TikTok/Reels/Shorts.
"""
import asyncio, json, subprocess, sys, shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image
import edge_tts

sys.path.insert(0, str(Path(__file__).parent.parent))
from tinytales.animator import (
    hook_sequence, title_sequence, dialogue_sequence,
    lesson_sequence, gradient_bg, font, FPS, W, H
)

SCRIPTS_DIR  = Path("tinytales/scripts")
AUDIO_DIR    = Path("tinytales/audio")
OUTPUT_DIR   = Path("tinytales/output")
ICLOUD_SHORT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Tiny Tales - Shorts"
ICLOUD_LONG  = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Tiny Tales - YouTube"

THEMES = [
    {"bg1":(15,10,35),  "bg2":(35,20,70),  "accent":(180,120,255), "text":(255,255,255)},
    {"bg1":(5,25,12),   "bg2":(15,55,28),  "accent":(80,225,120),  "text":(255,255,255)},
    {"bg1":(35,8,8),    "bg2":(65,18,18),  "accent":(255,90,70),   "text":(255,255,255)},
    {"bg1":(8,22,38),   "bg2":(18,45,75),  "accent":(70,175,255),  "text":(255,255,255)},
    {"bg1":(32,22,5),   "bg2":(65,45,10),  "accent":(255,195,45),  "text":(255,255,255)},
    {"bg1":(30,5,25),   "bg2":(60,10,50),  "accent":(255,100,200), "text":(255,255,255)},
]

async def speak_async(text, voice, path, rate="-5%"):
    text = ' '.join(text.replace('"',"'").replace('&','and').split())
    if text:
        await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))

def speak(text, voice, path, rate="-5%"):
    asyncio.run(speak_async(text, voice, path, rate))

def dur(path):
    r = subprocess.run(['ffprobe','-v','quiet','-print_format','json',
                       '-show_format',str(path)], capture_output=True, text=True)
    try: return float(json.loads(r.stdout)['format']['duration'])
    except: return 3.0

def frames_to_mp4(frames, audio_path, out_path, target_dur=None):
    import shutil, tempfile
    tmp = Path(tempfile.mkdtemp(prefix="tinytales_"))
    try:
        for i,f in enumerate(frames):
            Image.fromarray(f).save(str(tmp/f"f{i:06d}.png"))
        d = target_dur or dur(audio_path)
        fps = len(frames)/d if d > 0 else FPS
        r = subprocess.run([
            "ffmpeg","-y","-framerate",str(round(fps,3)),
            "-i",str(tmp/"f%06d.png"),"-stream_loop","-1","-i",str(audio_path),
            "-c:v","libx264","-c:a","aac",
            "-t",str(target_dur or 60),
            "-pix_fmt","yuv420p","-movflags","+faststart",str(out_path)
        ], capture_output=True)
        if r.returncode != 0:
            print("  ffmpeg error:", r.stderr.decode()[-300:])
            raise subprocess.CalledProcessError(r.returncode, "ffmpeg")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def produce(script_path):
    script    = json.loads(Path(script_path).read_text())
    ep_num    = script["ep_num"]
    title     = script["title"]
    slug      = script.get("slug","episode")
    date      = script["date"]
    c1        = script["char1"]
    c2        = script["char2"]
    dialogue  = script["dialogue"]
    lesson    = script.get("lesson","Working together is always better!")
    hook_text = script.get("hook", title.upper())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_dir = AUDIO_DIR / f"ep{ep_num:03d}"
    audio_dir.mkdir(parents=True, exist_ok=True)

    theme = THEMES[ep_num % len(THEMES)]
    print(f"\nProducing EP{ep_num:03d}: {title}")
    print(f"  HOOK: {hook_text}")
    print(f"  {c1['emoji']} {c1['name']}  +  {c2['emoji']} {c2['name']}")

    # ── Generate all audio ─────────────────────────────────────────
    print("  Generating voices...")
    audio_parts = []
    for i, line in enumerate(dialogue):
        spk, txt = line["speaker"], line["text"]
        ap = audio_dir / f"{i:03d}.mp3"
        if spk == "NARRATOR": voice, rate = "en-US-JennyNeural", "-8%"
        elif spk == c1["name"]: voice, rate = c1["voice"], "-3%"
        else: voice, rate = c2["voice"], "-3%"
        if not ap.exists():
            speak(txt, voice, ap, rate)
        if ap.exists():
            audio_parts.append((line, ap, dur(ap)))

    if not audio_parts:
        print("  No audio generated"); return

    # Combined audio
    combined = audio_dir / "combined.mp3"
    lst = audio_dir / "list.txt"
    lst.write_text('\n'.join(f"file '{p.resolve()}'" for _,p,_ in audio_parts))
    subprocess.run(['ffmpeg','-f','concat','-safe','0','-i',str(lst),
                   '-c','copy','-y',str(combined)], capture_output=True)
    total_audio = dur(combined)
    print(f"  Audio: {total_audio:.0f}s ({total_audio/60:.1f} min)")

    # ── Build frames ───────────────────────────────────────────────
    print("  Animating...")
    all_frames = []

    # Hook sequence (1.5s, no audio — plays over start of combined)
    hook_emoji = c1["emoji"]
    all_frames += hook_sequence(hook_text, hook_emoji, theme, n_frames=45)

    # Title sequence (2s)
    all_frames += title_sequence(title, c1, c2, ep_num, theme, n_frames=60)

    # Dialogue — each line animated
    for i, (line, ap, line_dur) in enumerate(audio_parts):
        spk = line["speaker"]
        txt = line["text"]
        emoji = "📖" if spk=="NARRATOR" else (c1["emoji"] if spk==c1["name"] else c2["emoji"])
        is_c1 = spk == c1["name"]
        frames = dialogue_sequence(txt, spk, emoji, theme, line_dur, is_speaker1=is_c1)
        all_frames += frames

    # Lesson sequence (2.5s)
    all_frames += lesson_sequence(lesson, theme, n_frames=75)

    # ── Render ─────────────────────────────────────────────────────
    print(f"  Rendering {len(all_frames)} frames...")
    out = OUTPUT_DIR / f"{date}-ep{ep_num:03d}-{slug}.mp4"

    frame_dur = len(all_frames) / FPS
    frames_to_mp4(all_frames, combined, out, target_dur=frame_dur)
    size_mb = out.stat().st_size//1024//1024
    print(f"  Done: {out.name} ({size_mb}MB, {frame_dur/60:.1f} min)")

    # ── Save to iCloud ─────────────────────────────────────────────
    for folder, name in [
        (ICLOUD_LONG,  f"EP{ep_num:03d} - {title[:50]}.mp4"),
        (ICLOUD_SHORT, f"EP{ep_num:03d} - {title[:50]} [SHORT].mp4"),
    ]:
        folder.mkdir(exist_ok=True)
        shutil.copy(out, folder/name)
    print(f"  → iCloud saved ✓")

    # macOS notification
    subprocess.Popen(["osascript","-e",
        f'display notification "{title}" with title "🐱 New Tiny Tales!" sound name "Glass"'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

if __name__ == "__main__":
    scripts = sorted(SCRIPTS_DIR.glob("ep*.json"))
    if not scripts:
        print("Run generate_story.py first."); sys.exit(1)
    produce(scripts[-1])
