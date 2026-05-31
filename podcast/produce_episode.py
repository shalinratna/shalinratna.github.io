#!/usr/bin/env python3
"""
Produces Dark Files podcast audio.
Two distinct voices (Ashley + Brit), atmospheric background, Crime Junkie feel.
"""
import json
import subprocess
import sys
import numpy as np
from pathlib import Path

SCRIPTS_DIR = Path("podcast/scripts")
EPISODES_DIR = Path("podcast/episodes")

# Voice assignments — two distinct macOS voices
VOICES = {
    "ASHLEY": ["Samantha", "Ava", "Karen"],   # Narrator — calm, clear
    "BRIT":   ["Kate", "Moira", "Fiona"],      # Reactor — different accent/tone
}

def get_best_voice(candidates):
    """Pick first available voice from candidates."""
    try:
        result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, timeout=10)
        available = result.stdout + result.stderr
        for v in candidates:
            if v in available:
                return v
    except:
        pass
    return "Samantha"  # universal fallback

def speak(text, voice, out_path):
    """Convert text to speech using macOS say command."""
    text = text.replace('"', "'").replace('&', 'and').replace('\n', ' ')
    text = ' '.join(text.split())
    if not text:
        return False

    aiff = str(out_path).replace('.mp3', '.aiff')
    tmp = Path(aiff).parent / f"tmp_{Path(out_path).stem}.txt"
    tmp.write_text(text, encoding='utf-8')

    result = subprocess.run(
        ['say', '-v', voice, '-o', aiff, '-f', str(tmp)],
        capture_output=True, timeout=180
    )
    tmp.unlink(missing_ok=True)

    if result.returncode != 0:
        # Try default voice
        result = subprocess.run(
            ['say', '-o', aiff, text[:500]],
            capture_output=True, timeout=60
        )

    if Path(aiff).exists():
        subprocess.run(
            ['ffmpeg', '-i', aiff, '-ar', '44100', '-ac', '2', '-b:a', '128k', '-y', str(out_path)],
            capture_output=True, check=True
        )
        Path(aiff).unlink(missing_ok=True)
        return True
    return False

def make_ambient_music(duration_seconds, out_path):
    """Generate atmospheric true crime background music (subtle drone)."""
    sr = 44100
    t = np.linspace(0, duration_seconds, int(sr * duration_seconds))

    # Low drone base frequency
    drone = 0.15 * np.sin(2 * np.pi * 55 * t)
    # Subtle overtone
    drone += 0.08 * np.sin(2 * np.pi * 82.5 * t)
    # Very soft high shimmer
    drone += 0.04 * np.sin(2 * np.pi * 220 * t + np.sin(2 * np.pi * 0.1 * t))

    # Fade in/out
    fade = int(sr * 3)
    drone[:fade] *= np.linspace(0, 1, fade)
    drone[-fade:] *= np.linspace(1, 0, fade)

    # Normalize
    drone = (drone * 32767 * 0.3).astype(np.int16)
    stereo = np.column_stack([drone, drone])

    # Write as WAV then convert
    wav_path = str(out_path).replace('.mp3', '.wav')
    import wave, struct
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

    subprocess.run(
        ['ffmpeg', '-i', wav_path, '-b:a', '128k', '-y', str(out_path)],
        capture_output=True
    )
    Path(wav_path).unlink(missing_ok=True)

def get_mp3_duration(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True, text=True
    )
    try:
        return float(json.loads(result.stdout)['format']['duration'])
    except:
        return 0.0

def mix_audio_with_music(voice_mp3, music_mp3, out_path):
    """Mix voice (foreground) with ambient music (background at -18dB)."""
    subprocess.run([
        'ffmpeg', '-i', str(voice_mp3), '-i', str(music_mp3),
        '-filter_complex',
        '[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[out]',
        '-map', '[out]', '-b:a', '128k', '-y', str(out_path)
    ], capture_output=True, check=True)

def produce(script_path):
    script = json.loads(Path(script_path).read_text())
    ep_num = script.get("ep_num", 1)
    slug = script.get("slug", "episode")
    title = script.get("title", "Dark Files Episode")
    dialogue = script.get("dialogue", [])

    EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = Path("podcast/work") / f"ep{ep_num:03d}"
    work_dir.mkdir(parents=True, exist_ok=True)

    ashley_voice = get_best_voice(VOICES["ASHLEY"])
    brit_voice = get_best_voice(VOICES["BRIT"])
    print(f"Producing: {title}")
    print(f"  Ashley voice: {ashley_voice} | Brit voice: {brit_voice}")

    if not dialogue:
        print("  No dialogue found in script.")
        return None

    # Generate each line
    part_files = []
    for i, line in enumerate(dialogue):
        speaker = line["speaker"]
        text = line["text"]
        if not text.strip():
            continue

        voice = ashley_voice if speaker == "ASHLEY" else brit_voice
        out = work_dir / f"{i:03d}_{speaker.lower()}.mp3"

        if not out.exists():
            success = speak(text, voice, out)
            if not success:
                continue

        if out.exists():
            part_files.append(out)
            print(f"  [{i+1}/{len(dialogue)}] {speaker}: {text[:40]}...")

    if not part_files:
        print("  No audio parts generated.")
        return None

    # Concatenate all voice parts
    voice_combined = work_dir / "voice_combined.mp3"
    list_file = work_dir / "concat.txt"
    list_file.write_text('\n'.join(f"file '{p.resolve()}'" for p in part_files))
    subprocess.run(
        ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
         '-c', 'copy', '-y', str(voice_combined)],
        capture_output=True
    )

    # Generate ambient background music
    total_dur = get_mp3_duration(voice_combined)
    music_file = work_dir / "ambient.mp3"
    print(f"  Generating {total_dur:.0f}s atmospheric background...")
    make_ambient_music(total_dur + 10, music_file)

    # Mix voice + music
    final_path = EPISODES_DIR / f"ep{ep_num:03d}-{slug}.mp3"
    print(f"  Mixing final audio...")
    mix_audio_with_music(voice_combined, music_file, final_path)

    # Cleanup work files
    list_file.unlink(missing_ok=True)

    size_mb = final_path.stat().st_size / 1024 / 1024
    print(f"  Done: {final_path.name} ({size_mb:.1f}MB, {total_dur/60:.1f} min)")
    return final_path

if __name__ == "__main__":
    scripts = sorted(SCRIPTS_DIR.glob("*.json"))
    if not scripts:
        print("No scripts found. Run generate_episode.py first.")
        sys.exit(1)
    produce(scripts[-1])
