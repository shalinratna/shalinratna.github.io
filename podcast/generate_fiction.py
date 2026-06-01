#!/usr/bin/env python3
"""
Generates original Dark Files FICTION episodes.
Completely original crime stories — no real people, no real cases.
Labeled clearly as fiction. Can go darker and more dramatic than real cases.
"""
import json
import re
import sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent if "/" in __file__ else __import__("pathlib").Path(".")))
from ai_client import generate as _ai_generate
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path("podcast/scripts")
USED_FILE = Path("podcast/fiction_used.json")

FICTION_PROMPTS = [
    "A woman in a small Pacific Northwest town starts receiving letters from someone who claims to know what really happened to her missing sister 10 years ago",
    "A retired detective gets an anonymous package containing crime scene photos from a murder he closed — but the evidence proves the wrong man was convicted",
    "A true crime podcaster starts receiving tips about a serial killer — but the tips describe crimes that haven't happened yet",
    "A woman discovers her newly deceased husband had a second family in another state — and that his first wife died under suspicious circumstances",
    "Three hikers find human remains in a national forest — but when they report it, local police insist no one has been reported missing in the area for 20 years",
    "A man doing genealogy research discovers he was adopted — and that his biological father is currently on death row for a crime the man realizes he committed himself",
    "A new true crime podcast host starts covering a cold case — and begins receiving messages from someone who claims to be the killer",
    "A woman's husband vanishes without a trace, leaving behind only a burner phone with one number saved in it",
    "A small town's beloved doctor is found dead, and the investigation reveals he had been secretly treating patients off the books for years",
    "A woman inherits her estranged aunt's house and finds a hidden room containing evidence of crimes spanning three decades",
    "A neighborhood watch volunteer starts suspecting his next-door neighbor is the serial killer known as the Highway Phantom",
    "A forensic accountant discovers that a charity for missing children has been used to launder money — and that the children never existed",
    "A podcaster covering the death of a social media influencer realizes the 'accident' was a warning to someone still alive",
    "A woman's therapist is found murdered the same day she was going to reveal something about her most dangerous patient",
    "A cold case investigator exhumes a grave and finds the wrong body — and the real person is very much alive somewhere",
    "A true crime writer researching a 1970s serial killer discovers the killings never actually stopped — they just got smarter",
    "A woman realizes the man she married is using a stolen identity — and the real man has been missing for 15 years",
    "A small town's entire police department quits overnight, leaving behind a note that says 'We know what's in the water'",
    "A death row inmate convinces a journalist he's innocent — and gives her a coded message that leads to a living victim",
    "A woman starts finding objects from strangers' lives hidden in the walls of her new house — and a pattern emerges",
]

PROMPT = """Write a Dark Files podcast episode. This is FICTION — an original crime story, not a real case.

Story concept: {concept}

Two hosts:
- MORGAN: The main storyteller. She's presenting this as a "Dark Files Original" — a story submitted to them or a fictional case they're exploring. Calm, detailed, suspenseful.
- TAYLOR: Co-host. Reacts with genuine shock, horror, curiosity. Short punchy reactions.

Use ONLY this format:

TITLE: [Gripping fictional title — 6-8 words]
DESCRIPTION: [150 char Spotify description — make it sound irresistible]
SLUG: [lowercase-hyphen-slug]

SCRIPT:
MORGAN: [Hook — most terrifying or shocking sentence of the story. No intro yet.]
TAYLOR: [One horrified reaction]
MORGAN: Welcome back to Dark Files. I'm Morgan. Today we have something different for you — a Dark Files Original. This is a work of fiction, but trust me, it'll keep you up at night.
TAYLOR: And I'm Taylor. Morgan warned me about this one and I still wasn't ready.
MORGAN: [Set the scene — fictional town, character, atmosphere. Rich and vivid. 4-5 sentences.]
TAYLOR: [React to the most unsettling detail — 1-2 sentences]
MORGAN: [Deepen the mystery. What's wrong. What doesn't add up. Build dread. 5-6 sentences.]
TAYLOR: [Ask the question the listener is thinking — 1-2 sentences]
MORGAN: [The discovery or reveal. Something shocking. 5-6 sentences. Maximum tension.]
TAYLOR: [Express genuine horror or disbelief — 1-2 sentences]
MORGAN: [The investigation unravels. Twist. More complexity. 5-6 sentences.]
TAYLOR: [Can't believe detail just revealed — 1-2 sentences]
MORGAN: [The darkest part of the story. What really happened. Don't hold back. 5-6 sentences.]
TAYLOR: [Visceral reaction — 1-2 sentences]
MORGAN: [Resolution or deliberate lack of resolution. Ambiguous ending works great. 4-5 sentences.]
TAYLOR: [Final haunting thought — 1-2 sentences]
MORGAN: That's our Dark Files Original for today. Remember — this story is fiction. But the darkness it reflects? That's very real. Stay safe out there.
TAYLOR: Sleep tight.

Rules:
- MORGAN uses vivid, cinematic language — you're writing a psychological thriller
- TAYLOR's reactions must feel genuinely human and surprised
- No real people, real places, or real cases
- Can be darker and more extreme than real cases — this is fiction
- Include specific sensory details that create atmosphere
- Build suspense methodically — don't rush the reveal
- Total word count: 1200-1500 words
"""

def call_ollama(prompt, tokens=3000):
    return _ai_generate(prompt, model="sonnet", max_tokens=tokens)


def parse_script(raw, concept):
    data = {
        "case": concept, "fiction": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "title": "", "description": "", "slug": "",
        "dialogue": []
    }
    in_script = False
    current_speaker = None
    current_lines = []

    def flush():
        if current_speaker and current_lines:
            text = ' '.join(' '.join(current_lines).split())
            if text:
                data["dialogue"].append({"speaker": current_speaker, "text": text})

    for line in raw.split('\n'):
        s = line.strip()
        if s.startswith("TITLE:"): data["title"] = s[6:].strip()
        elif s.startswith("DESCRIPTION:"): data["description"] = s[12:].strip()
        elif s.startswith("SLUG:"):
            data["slug"] = re.sub(r'[^a-z0-9-]', '', s[5:].strip().lower())[:55]
        elif s == "SCRIPT:":
            in_script = True
        elif in_script:
            if s.startswith("MORGAN:"):
                flush(); current_speaker = "MORGAN"; current_lines = [s[7:].strip()]
            elif s.startswith("TAYLOR:"):
                flush(); current_speaker = "TAYLOR"; current_lines = [s[7:].strip()]
            elif current_speaker and s:
                current_lines.append(s)
    flush()

    if not data["title"]:
        data["title"] = f"Dark Files Fiction: {concept[:40]}"
    if not data["slug"]:
        slug = re.sub(r'[^a-z0-9\s]', '', data["title"].lower())
        data["slug"] = re.sub(r'\s+', '-', slug.strip())[:55]

    return data

def load_used():
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text())
    return []

def save_used(used):
    USED_FILE.write_text(json.dumps(used, indent=2))

def get_next_concept():
    used = load_used()
    for c in FICTION_PROMPTS:
        if c not in used:
            return c
    # Generate new concepts when exhausted
    prompt = """Generate 15 original crime fiction story concepts for a podcast.
Each must be a one-sentence story premise — dark, original, compelling.
No real people or places. Reply with a numbered list only."""
    raw = call_ollama(prompt)
    new = []
    for line in raw.strip().split('\n'):
        line = re.sub(r'^\d+[\.\)]\s*', '', line.strip())
        if len(line) > 20 and line not in FICTION_PROMPTS:
            new.append(line)
            FICTION_PROMPTS.append(line)
    return new[0] if new else FICTION_PROMPTS[0]

def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Count total scripts to get episode number
    all_scripts = sorted(SCRIPTS_DIR.glob("ep*.json"))
    ep_num = len(all_scripts) + 1

    concept = get_next_concept()
    print(f"Generating FICTION episode {ep_num}: {concept[:60]}...")

    raw = call_ollama(PROMPT.format(concept=concept))
    script = parse_script(raw, concept)
    script["ep_num"] = ep_num

    fname = f"ep{ep_num:03d}-fiction-{script['slug']}.json"
    (SCRIPTS_DIR / fname).write_text(json.dumps(script, indent=2))

    used = load_used()
    used.append(concept)
    save_used(used)

    print(f"Saved: {fname}")
    print(f"Title: {script['title']}")
    print(f"Dialogue lines: {len(script['dialogue'])}")

if __name__ == "__main__":
    main()
