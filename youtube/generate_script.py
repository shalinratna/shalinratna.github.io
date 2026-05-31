#!/usr/bin/env python3
import json
import re
import requests
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

PROMPT = """Write a YouTube video script about: {topic}

Use this exact format:

TITLE: [YouTube title, 60-70 chars, curiosity-driven, includes keyword]
DESCRIPTION: [YouTube description, 200-250 chars, includes keyword + value hook]
TAGS: [tag1, tag2, tag3, tag4, tag5, tag6, tag7]
FILENAME: [lowercase-slug-no-spaces]

HOOK:
[15-20 second hook. Start with a shocking stat or question. Grab attention immediately. 2-3 sentences.]

INTRO:
[30-40 seconds. Tell them exactly what they'll learn and why it matters. Build curiosity. 3-4 sentences.]

SECTION_1_TITLE: [short title]
SECTION_1:
[90-120 seconds of content. Specific, actionable. Include exact steps or examples. 5-7 sentences.]

SECTION_2_TITLE: [short title]
SECTION_2:
[90-120 seconds of content. Specific, actionable. 5-7 sentences.]

SECTION_3_TITLE: [short title]
SECTION_3:
[90-120 seconds of content. Specific, actionable. 5-7 sentences.]

SECTION_4_TITLE: [short title]
SECTION_4:
[90-120 seconds of content. Specific, actionable. 5-7 sentences.]

SECTION_5_TITLE: [short title]
SECTION_5:
[90-120 seconds of content. Specific, actionable. 5-7 sentences.]

OUTRO:
[30-40 seconds. Recap the 3 biggest takeaways. Tell them to like and subscribe. Tease the next video topic. 3-4 sentences.]

Requirements:
- Conversational, direct tone — like a knowledgeable friend explaining this
- Never say "in this video" — say "right now" or "today"
- Include specific numbers, tools, and real examples
- Total script: 8-10 minutes when read aloud (~1200-1500 words)
"""

def generate_script(topic):
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": PROMPT.format(topic=topic),
              "stream": False, "options": {"temperature": 0.7, "num_predict": 2500}},
        timeout=300
    )
    return resp.json()["response"]

def parse_script(raw, topic):
    lines = raw.strip().split('\n')
    data = {"topic": topic, "sections": [], "section_titles": []}

    # Single-line fields
    inline_fields = {"TITLE:": "title", "DESCRIPTION:": "description",
                     "TAGS:": "tags", "FILENAME:": "filename"}
    # Multi-line block fields
    block_fields = {"HOOK:": "hook", "INTRO:": "intro", "OUTRO:": "outro"}
    # All block starters (for detecting end of a block)
    all_blocks = set(block_fields.keys()) | {"SECTION_"}

    current_block = None   # key name in data
    current_lines = []
    current_section_idx = None

    def flush_block():
        if current_block and current_lines:
            data[current_block] = '\n'.join(current_lines).strip()
        elif current_section_idx is not None and current_lines:
            data["sections"].append('\n'.join(current_lines).strip())

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check inline fields first
        matched_inline = False
        for prefix, key in inline_fields.items():
            if stripped.startswith(prefix):
                flush_block(); current_block = None; current_section_idx = None; current_lines = []
                data[key] = stripped[len(prefix):].strip()
                matched_inline = True
                break

        if matched_inline:
            i += 1
            continue

        # Check section title
        m = re.match(r'SECTION_(\d+)_TITLE:\s*(.*)', stripped)
        if m:
            flush_block(); current_block = None; current_section_idx = None; current_lines = []
            data["section_titles"].append(m.group(2).strip())
            i += 1
            continue

        # Check section content start
        m2 = re.match(r'SECTION_(\d+):\s*$', stripped)
        if m2:
            flush_block(); current_block = None
            current_section_idx = int(m2.group(1))
            current_lines = []
            i += 1
            continue

        # Check block fields
        matched_block = False
        for prefix, key in block_fields.items():
            if stripped == prefix.rstrip(':') + ':' or stripped.startswith(prefix):
                flush_block()
                current_block = key
                current_section_idx = None
                current_lines = []
                inline_content = stripped[len(prefix):].strip()
                if inline_content:
                    current_lines.append(inline_content)
                matched_block = True
                break

        if not matched_block and (current_block or current_section_idx is not None):
            current_lines.append(line)

        i += 1

    flush_block()

    if not data.get("filename"):
        slug = re.sub(r'[^a-z0-9\s]', '', data.get("title", topic).lower())
        data["filename"] = re.sub(r'\s+', '-', slug)[:50]

    if isinstance(data.get("tags"), str):
        data["tags"] = [t.strip() for t in data["tags"].split(',')]

    # Fallbacks so nothing is empty
    for key in ("hook", "intro", "outro"):
        if not data.get(key):
            data[key] = data.get("title", topic)

    return data

def save_script(data):
    out_dir = Path("youtube/scripts")
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    fname = f"{date}-{data['filename']}.json"
    path = out_dir / fname
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return path

def load_topics():
    with open("topics.json") as f:
        return json.load(f)

def get_next_video_topic(data):
    used = set(data.get("used_video", []))
    for t in data["topics"]:
        if t not in used:
            return t
    return None

def mark_video_used(data, topic):
    if "used_video" not in data:
        data["used_video"] = []
    data["used_video"].append(topic)
    with open("topics.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    data = load_topics()
    topic = get_next_video_topic(data)
    if not topic:
        print("No topics left")
        exit(0)
    print(f"Generating script: {topic}")
    raw = generate_script(topic)
    script = parse_script(raw, topic)
    path = save_script(script)
    mark_video_used(data, topic)
    print(f"Saved: {path}")
    print(f"Title: {script.get('title', 'N/A')}")
