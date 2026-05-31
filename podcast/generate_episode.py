#!/usr/bin/env python3
"""
Generates Dark Files true crime podcast scripts.
Crime Junkie style — two hosts, conversational, obsessive detail.
"""
import json
import re
import requests
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
CASES_FILE = Path("podcast/cases.json")
SCRIPTS_DIR = Path("podcast/scripts")

PROMPT = """You are writing a script for "Dark Files" — a true crime podcast exactly like Crime Junkie.

Two hosts:
- ASHLEY: The main storyteller. Calm, detailed, methodical. Knows every fact.
- BRIT: The co-host reactor. Occasionally interjects, asks questions, expresses horror.

Case to cover: {case}

Write a full podcast episode script. Use ONLY this format:

TITLE: [Episode title — punchy, 8 words max, like Crime Junkie titles]
DESCRIPTION: [150 char episode description for Spotify]
SLUG: [lowercase-hyphen-slug]

SCRIPT:
ASHLEY: [Opening hook — one shocking sentence about the case. No "welcome back" yet.]
BRIT: [Short horrified or curious reaction — 1 sentence]
ASHLEY: Welcome back to Dark Files. I'm Ashley.
BRIT: And I'm Brit.
ASHLEY: Today we're covering [case name], and I have to warn you — this one is deeply unsettling.
BRIT: [1 sentence reaction — "I've been waiting for you to cover this one" or similar]
ASHLEY: [Set the scene. Town, time period, victim background. 4-5 sentences. Specific details.]
BRIT: [Short reaction or question — "How old were they?" or "Wait, so..." — 1-2 sentences]
ASHLEY: [Continue story — timeline of events leading up to the crime. 5-6 sentences.]
BRIT: [React to the most disturbing detail just mentioned — 1-2 sentences]
ASHLEY: [The crime itself — what happened, what was found, what was strange. 5-6 sentences.]
BRIT: [Express disbelief or horror at something specific — 1-2 sentences]
ASHLEY: [The investigation — who was suspected, what evidence existed, what went wrong. 5-6 sentences.]
BRIT: [Ask a natural question a listener would have — 1-2 sentences]
ASHLEY: [Answer the question, go deeper into suspects or evidence. 4-5 sentences.]
BRIT: [React to the most suspicious or chilling detail — 1-2 sentences]
ASHLEY: [Where the case stands today — solved, cold, or recently reopened. 4-5 sentences.]
BRIT: [Final reaction — "This is the kind of case that keeps me up at night" type ending — 1-2 sentences]
ASHLEY: If you have any information about this case, please contact [relevant tip line or law enforcement]. As always, be wrapt up, be nosy, and stay safe out there.
BRIT: See you next week.

Rules:
- ASHLEY speaks in long, detailed paragraphs with specific facts
- BRIT speaks in short punchy reactions, never more than 2 sentences
- Never make up specific names, dates, or facts you're not sure about — say "allegedly" or "reportedly"
- Keep it factual and respectful to victims
- Total length: 1200-1500 words of dialogue
- No music cues or stage directions in the script
"""

def call_ollama(prompt):
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.7, "num_predict": 2500}},
        timeout=300
    )
    return resp.json()["response"]

def parse_script(raw, case):
    lines = raw.strip().split('\n')
    data = {
        "case": case,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "title": "", "description": "", "slug": "",
        "dialogue": []  # list of {"speaker": "ASHLEY"|"BRIT", "text": "..."}
    }

    in_script = False
    current_speaker = None
    current_lines = []

    def flush():
        if current_speaker and current_lines:
            text = ' '.join(' '.join(current_lines).split())
            if text:
                data["dialogue"].append({"speaker": current_speaker, "text": text})

    for line in lines:
        s = line.strip()
        if s.startswith("TITLE:"):
            data["title"] = s[6:].strip()
        elif s.startswith("DESCRIPTION:"):
            data["description"] = s[12:].strip()
        elif s.startswith("SLUG:"):
            slug = s[5:].strip()
            data["slug"] = re.sub(r'[^a-z0-9-]', '', slug.lower())[:55]
        elif s == "SCRIPT:":
            in_script = True
        elif in_script:
            if s.startswith("ASHLEY:"):
                flush(); current_speaker = "ASHLEY"; current_lines = [s[7:].strip()]
            elif s.startswith("BRIT:"):
                flush(); current_speaker = "BRIT"; current_lines = [s[5:].strip()]
            elif current_speaker and s:
                current_lines.append(s)

    flush()

    if not data["title"]:
        data["title"] = case[:60]
    if not data["slug"]:
        slug = re.sub(r'[^a-z0-9\s]', '', data["title"].lower())
        data["slug"] = re.sub(r'\s+', '-', slug.strip())[:55]

    return data

def load_cases():
    return json.loads(CASES_FILE.read_text())

def save_cases(d):
    CASES_FILE.write_text(json.dumps(d, indent=2))

def get_next_case(data):
    for c in data["cases"]:
        if c not in data["used"]:
            return c
    return None

def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_cases()
    case = get_next_case(data)
    if not case:
        print("All cases used. Add more to cases.json")
        return

    print(f"Generating episode: {case[:60]}...")
    raw = call_ollama(PROMPT.format(case=case))
    script = parse_script(raw, case)

    ep_num = len(data["used"]) + 1
    script["ep_num"] = ep_num
    fname = f"ep{ep_num:03d}-{script['slug']}.json"
    (SCRIPTS_DIR / fname).write_text(json.dumps(script, indent=2))

    data["used"].append(case)
    save_cases(data)

    print(f"Saved: {fname}")
    print(f"Title: {script['title']}")
    print(f"Dialogue lines: {len(script['dialogue'])}")
    return SCRIPTS_DIR / fname

if __name__ == "__main__":
    main()
