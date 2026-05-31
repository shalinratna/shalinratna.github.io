#!/usr/bin/env python3
"""
Produces Dark Files podcast audio using Kokoro TTS.
Morgan = calm American narrator. Taylor = British co-host reactor.
Sounds genuinely human — not robotic.
"""
import asyncio
import json
import subprocess
import sys
import numpy as np
import edge_tts
from pathlib import Path

SCRIPTS_DIR = Path("podcast/scripts")
EPISODES_DIR = Path("podcast/episodes")

# Microsoft Neural voices — sound genuinely human, free, no API key
MORGAN_VOICE = "en-US-AriaNeural"    # Calm, warm American female narrator
TAYLOR_VOICE = "en-GB-SoniaNeural"   # British female — distinct accent, reactive

async def speak_async(text, voice, out_path):
    """edge-tts: Microsoft neural TTS, sounds extremely human."""
    text = text.strip().replace('"', "'").replace('&', 'and')
    text = ' '.join(text.split())
    if not text:
        return False
    try:
        communicate = edge_tts.Communicate(text, voice=voice, rate="-5%", volume="+10%")
        await communicate.save(str(out_path))
        return out_path.exists() and out_path.stat().st_size > 1000
    except Exception as e:
        print(f"  edge-tts failed: {e}")
        return False

def speak(text, voice, out_path):
    return asyncio.run(speak_async(text, voice, out_path))

def make_ambient(duration_seconds, out_path, dark=True):
    """Generate atmospheric background drone."""
    sr = 44100
    t = np.linspace(0, duration_seconds, int(sr * duration_seconds))
    if dark:
        # True crime atmosphere: low, ominous
        audio = 0.12 * np.sin(2 * np.pi * 40 * t)
        audio += 0.07 * np.sin(2 * np.pi * 60 * t)
        audio += 0.04 * np.sin(2 * np.pi * 80 * t + np.sin(2 * np.pi * 0.05 * t) * 2)
        audio += 0.02 * np.random.randn(len(t)) * 0.3  # subtle texture
    else:
        # Slightly lighter for fiction
        audio = 0.10 * np.sin(2 * np.pi * 55 * t)
        audio += 0.06 * np.sin(2 * np.pi * 110 * t)
        audio += 0.03 * np.sin(2 * np.pi * 220 * t + np.sin(2 * np.pi * 0.1 * t))

    fade = int(sr * 4)
    audio[:fade] *= np.linspace(0, 1, fade)
    audio[-fade:] *= np.linspace(1, 0, fade)
    audio = (np.clip(audio, -1, 1) * 32767 * 0.4).astype(np.int16)
    stereo = np.column_stack([audio, audio])

    wav = str(out_path).replace('.mp3', '.wav')
    import wave
    with wave.open(wav, 'w') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())
    subprocess.run(['ffmpeg', '-i', wav, '-b:a', '128k', '-y', str(out_path)],
                  capture_output=True)
    Path(wav).unlink(missing_ok=True)

def get_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                       '-show_format', str(path)], capture_output=True, text=True)
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except:
        return 0.0

def mix(voice_mp3, music_mp3, out_path):
    """Voice foreground + ambient background at low volume."""
    subprocess.run([
        'ffmpeg', '-i', str(voice_mp3), '-i', str(music_mp3),
        '-filter_complex',
        '[1:a]volume=0.10[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=4[out]',
        '-map', '[out]', '-b:a', '128k', '-y', str(out_path)
    ], capture_output=True, check=True)

def produce(script_path):
    script = json.loads(Path(script_path).read_text())
    ep_num = script.get("ep_num", 1)
    slug = script.get("slug", "episode")
    title = script.get("title", "Dark Files Episode")
    dialogue = script.get("dialogue", [])
    is_fiction = script.get("fiction", False)

    EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = Path("podcast/work") / f"ep{ep_num:03d}"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'[FICTION] ' if is_fiction else ''}Producing: {title}")
    print(f"  Morgan: {MORGAN_VOICE} | Taylor: {TAYLOR_VOICE} (Microsoft Neural)")

    if not dialogue:
        print("  No dialogue found.")
        return None

    part_files = []
    for i, line in enumerate(dialogue):
        speaker = line["speaker"]
        text = line["text"]
        if not text.strip():
            continue

        voice = MORGAN_VOICE if speaker in ("MORGAN", "ASHLEY") else TAYLOR_VOICE
        out = work_dir / f"{i:03d}_{speaker.lower()}.mp3"

        if not out.exists():
            ok = speak(text, voice, out)
            if not ok:
                continue

        if out.exists():
            part_files.append(out)
            print(f"  [{i+1}/{len(dialogue)}] {speaker}: {text[:50]}...")

    if not part_files:
        print("  Failed to generate audio.")
        return None

    # Concatenate voice parts
    combined = work_dir / "voice_combined.mp3"
    lst = work_dir / "concat.txt"
    lst.write_text('\n'.join(f"file '{p.resolve()}'" for p in part_files))
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(lst),
                   '-c', 'copy', '-y', str(combined)], capture_output=True)

    dur = get_duration(combined)
    music = work_dir / "ambient.mp3"
    print(f"  Generating {dur:.0f}s atmosphere...")
    make_ambient(dur + 6, music, dark=not is_fiction)

    final = EPISODES_DIR / f"ep{ep_num:03d}-{slug}.mp3"
    print(f"  Mixing final audio...")
    mix(combined, music, final)
    lst.unlink(missing_ok=True)

    mb = final.stat().st_size / 1024 / 1024
    print(f"  Done: {final.name} ({mb:.1f}MB, {dur/60:.1f} min)")

    # Auto-copy to iCloud Drive
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Dark Files"
    icloud.mkdir(exist_ok=True)
    ep_label = "[FICTION] " if is_fiction else ""
    dest = icloud / f"EP{ep_num:03d} - {ep_label}{title}.mp3"
    import shutil
    shutil.copy(final, dest)
    print(f"  Saved to iCloud: {dest.name}")

    return final

if __name__ == "__main__":
    scripts = sorted(SCRIPTS_DIR.glob("*.json"))
    if not scripts:
        print("No scripts found. Run generate_episode.py first.")
        sys.exit(1)
    produce(scripts[-1])
