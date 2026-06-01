#!/usr/bin/env python3
"""Series-aware script generator for Money Brain YouTube channel."""
import json
import re
from datetime import datetime
from pathlib import Path
import sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent if "/" in __file__ else __import__("pathlib").Path(".")))
from ai_client import generate as _ai_generate

SERIES_FILE = Path("youtube/topics_series.json")
SCRIPTS_DIR = Path("youtube/scripts")

PROMPT = """Write a YouTube script for the "Money Brain" channel. Topic: {topic}
Series: {series_name}, Episode {ep_num}

Reply using ONLY these exact labels, one per line where shown, then the content below:

TITLE: [65 char YouTube title with power words]
THUMBNAIL: [6 word punchy thumbnail text]
TAGS: make money online, {series_name}, wealth building, AI tools, passive income, financial freedom, money mindset, side hustle, invest money, ChatGPT money
FOOTAGE: money success, businessman laptop, financial freedom, investing charts, motivation hustle

HOOK:
[3 shocking sentences. No hello. Start with a stat. Make them need to keep watching.]

INTRO:
[2-3 sentences. Tell them what they learn today. Mention this is Episode {ep_num} of {series_name}.]

PART1_TITLE: [5 word section title]
PART1:
[150 words. Specific, real numbers, surprising insight.]

PART2_TITLE: [5 word section title]
PART2:
[150 words. Actionable steps. Real examples.]

PART3_TITLE: [5 word section title]
PART3:
[150 words. Common mistakes. What most people get wrong.]

PART4_TITLE: [5 word section title]
PART4:
[150 words. Advanced tactic. The insider move.]

PART5_TITLE: [5 word section title]
PART5:
[150 words. The action plan. What to do this week.]

OUTRO:
[3 sentences. Recap the #1 takeaway. Tease next episode. Tell them to subscribe to Money Brain.]
"""

def call_ollama(prompt, tokens=3000):
    return _ai_generate(prompt, model="sonnet", max_tokens=tokens)


def parse_script(raw, series, ep):
    data = {
        "series_name": series["name"],
        "playlist": series["playlist"],
        "ep_num": ep["ep"],
        "topic": ep["topic"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "title": "", "thumbnail_text": "", "tags": [],
        "pexels_keywords": [], "hook": "", "intro": "", "outro": "",
        "sections": [], "section_titles": [], "section_footage": [],
    }

    # Split into blocks by label
    blocks = {}
    current_label = None
    current_lines = []

    for line in raw.split('\n'):
        s = line.strip()
        # Check for single-line labels
        for label in ["TITLE:", "THUMBNAIL:", "TAGS:", "FOOTAGE:"]:
            if s.startswith(label):
                if current_label:
                    blocks[current_label] = '\n'.join(current_lines).strip()
                current_label = label.rstrip(':')
                blocks[current_label] = s[len(label):].strip()
                current_label = None
                current_lines = []
                break
        else:
            # Multi-line blocks
            block_labels = ["HOOK:", "INTRO:", "OUTRO:",
                           "PART1:", "PART2:", "PART3:", "PART4:", "PART5:",
                           "PART1_TITLE:", "PART2_TITLE:", "PART3_TITLE:",
                           "PART4_TITLE:", "PART5_TITLE:"]
            matched = False
            for label in block_labels:
                if s == label or s.startswith(label + ' '):
                    if current_label:
                        blocks[current_label] = '\n'.join(current_lines).strip()
                    current_label = label.rstrip(':')
                    current_lines = [s[len(label):].strip()] if s.startswith(label + ' ') else []
                    matched = True
                    break
            if not matched and current_label:
                current_lines.append(line)

    if current_label:
        blocks[current_label] = '\n'.join(current_lines).strip()

    # Map blocks to data
    data["title"] = blocks.get("TITLE", ep["topic"][:70])
    data["thumbnail_text"] = blocks.get("THUMBNAIL", "")
    data["hook"] = blocks.get("HOOK", ep["topic"])
    data["intro"] = blocks.get("INTRO", "")
    data["outro"] = blocks.get("OUTRO", "Subscribe to Money Brain for more.")

    if blocks.get("TAGS"):
        data["tags"] = [t.strip() for t in blocks["TAGS"].split(',')]
    if blocks.get("FOOTAGE"):
        data["pexels_keywords"] = [t.strip() for t in blocks["FOOTAGE"].split(',')]

    for i in range(1, 6):
        sec = blocks.get(f"PART{i}", "")
        title = blocks.get(f"PART{i}_TITLE", f"Part {i}")
        footage = data["pexels_keywords"][i-1] if i-1 < len(data["pexels_keywords"]) else "money success"
        data["sections"].append(sec)
        data["section_titles"].append(title)
        data["section_footage"].append(footage)

    # Filename
    slug = re.sub(r'[^a-z0-9\s]', '', data["title"].lower())
    data["filename"] = re.sub(r'\s+', '-', slug.strip())[:55]

    return data

def load_series():
    return json.loads(SERIES_FILE.read_text())

def save_series(d):
    SERIES_FILE.write_text(json.dumps(d, indent=2))

def get_next_episode(data):
    used = set(data.get("used_episodes", []))
    for series in data["series"]:
        for ep in series["episodes"]:
            if f"{series['name']}_{ep['ep']}" not in used:
                return series, ep
    return None, None

def replenish_series(data):
    """Auto-generates a new series of 10 episodes when all are used."""
    used = set(data.get("used_episodes", []))
    total = sum(len(s["episodes"]) for s in data["series"])
    remaining = total - len(used)
    if remaining > 3:
        return

    print("Generating new Money Brain series...")
    prompt = """Generate a new YouTube series for a channel called "Money Brain" about wealth, AI tools, and financial freedom for men.

Format:
SERIES_NAME: [series name]
1. [episode topic — specific, bold, curiosity-driving]
2. [episode topic]
... (10 episodes total)

Make the topics specific, provocative, and search-friendly. Focus on money mindset, AI tools, investing, side hustles.

Generate one complete series of 10 episodes now:"""

    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.85, "num_predict": 800}},
        timeout=180
    )
    raw = resp.json()["response"]
    lines = raw.strip().split('\n')
    series_name = "Money Brain Unlocked"
    episodes = []
    for line in lines:
        line = line.strip()
        if line.startswith("SERIES_NAME:"):
            series_name = line[12:].strip()
        else:
            topic = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            if len(topic) > 20:
                episodes.append({"ep": len(episodes)+1, "topic": topic})
        if len(episodes) >= 10:
            break

    if episodes:
        data["series"].append({
            "name": series_name,
            "playlist": series_name,
            "episodes": episodes
        })
        save_series(data)
        print(f"Added new series: '{series_name}' with {len(episodes)} episodes.")

def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_series()
    replenish_series(data)
    data = load_series()
    series, ep = get_next_episode(data)
    if not series:
        print("All episodes used — replenishment failed, check logs.")
        return

    print(f"[{series['name']}] Ep {ep['ep']}: {ep['topic'][:60]}...")
    raw = call_ollama(PROMPT.format(
        topic=ep["topic"], series_name=series["name"], ep_num=ep["ep"]
    ))
    script = parse_script(raw, series, ep)

    fname = f"{script['date']}-s{ep['ep']:02d}-{script['filename']}.json"
    (SCRIPTS_DIR / fname).write_text(json.dumps(script, indent=2))

    data["used_episodes"].append(f"{series['name']}_{ep['ep']}")
    save_series(data)

    print(f"Saved: {fname}")
    print(f"Title: {script['title']}")
    print(f"Sections: {len([s for s in script['sections'] if s])}")
    return SCRIPTS_DIR / fname

if __name__ == "__main__":
    main()
