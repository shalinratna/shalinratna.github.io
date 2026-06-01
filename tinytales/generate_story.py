#!/usr/bin/env python3
"""
Tiny Tales — AI story generator for kids/families.
Talking animals, inanimate objects, vegetables, toys.
Each story teaches a simple lesson. 3-5 minutes long.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_client import generate as ai

SCRIPTS_DIR = Path("tinytales/scripts")

# Character bank — emoji + personality + voice
CHARACTERS = {
    # Animals
    "cat":      {"emoji": "🐱", "name": "Luna",    "voice": "en-US-AriaNeural",    "personality": "curious, clever, a little sassy"},
    "dog":      {"emoji": "🐶", "name": "Biscuit",  "voice": "en-US-GuyNeural",     "personality": "loyal, enthusiastic, goofy"},
    "bear":     {"emoji": "🐻", "name": "Bruno",    "voice": "en-GB-RyanNeural",    "personality": "slow, wise, gentle giant"},
    "bunny":    {"emoji": "🐰", "name": "Pip",      "voice": "en-AU-NatashaNeural", "personality": "nervous, sweet, very fast"},
    "fox":      {"emoji": "🦊", "name": "Rusty",    "voice": "en-US-GuyNeural",     "personality": "clever, mischievous, kind underneath"},
    "owl":      {"emoji": "🦉", "name": "Professor","voice": "en-GB-RyanNeural",    "personality": "wise, formal, secretly loves jokes"},
    "duck":     {"emoji": "🦆", "name": "Ducky",    "voice": "en-AU-NatashaNeural", "personality": "cheerful, splashy, loves puddles"},
    "elephant": {"emoji": "🐘", "name": "Ellie",    "voice": "en-US-JennyNeural",   "personality": "never forgets, very polite, kind"},
    # Kitchen objects
    "salt":     {"emoji": "🧂", "name": "Sally",    "voice": "en-US-JennyNeural",   "personality": "confident, thinks she's the best"},
    "pepper":   {"emoji": "🫙", "name": "Pete",     "voice": "en-GB-RyanNeural",    "personality": "dramatic, spicy personality, easily sneezes"},
    "spoon":    {"emoji": "🥄", "name": "Spoonie",  "voice": "en-AU-NatashaNeural", "personality": "helpful, always wants to stir things up"},
    "fork":     {"emoji": "🍴", "name": "Forky",    "voice": "en-US-GuyNeural",     "personality": "sharp-witted, protective"},
    "pot":      {"emoji": "🍲", "name": "Big Pot",  "voice": "en-GB-RyanNeural",    "personality": "boisterous, warm, loves bringing everyone together"},
    "teapot":   {"emoji": "🫖", "name": "Tessie",   "voice": "en-US-JennyNeural",   "personality": "proper, a little old-fashioned, very comforting"},
    # Vegetables/fruit
    "carrot":   {"emoji": "🥕", "name": "Carl",     "voice": "en-US-GuyNeural",     "personality": "athletic, competitive, always crunching"},
    "broccoli": {"emoji": "🥦", "name": "Brock",    "voice": "en-GB-RyanNeural",    "personality": "misunderstood, actually cool, tree-shaped pride"},
    "tomato":   {"emoji": "🍅", "name": "Tommy",    "voice": "en-US-AriaNeural",    "personality": "confused about being fruit OR vegetable"},
    "apple":    {"emoji": "🍎", "name": "Rosie",    "voice": "en-AU-NatashaNeural", "personality": "bright, healthy, teacher's favourite"},
    # Stationery/toys
    "pencil":   {"emoji": "✏️",  "name": "Penny",    "voice": "en-US-AriaNeural",    "personality": "creative, gets shorter with worry"},
    "eraser":   {"emoji": "🧹",  "name": "Ernie",    "voice": "en-US-GuyNeural",     "personality": "fixes mistakes, very forgiving"},
    "book":     {"emoji": "📚",  "name": "Booker",   "voice": "en-GB-RyanNeural",    "personality": "knows everything, excited to share"},
    "crayon":   {"emoji": "🖍️",  "name": "Crimson",  "voice": "en-AU-NatashaNeural", "personality": "colourful, expressive, different is beautiful"},
    # Nature
    "sun":      {"emoji": "☀️",  "name": "Sunny",    "voice": "en-US-JennyNeural",   "personality": "warm, uplifting, maybe a bit much in summer"},
    "cloud":    {"emoji": "⛅",  "name": "Cloudy",   "voice": "en-US-AriaNeural",    "personality": "misunderstood, just wants to help with rain"},
    "moon":     {"emoji": "🌙",  "name": "Luna",     "voice": "en-AU-NatashaNeural", "personality": "calm, mysterious, loves stars"},
    "star":     {"emoji": "⭐",  "name": "Stella",   "voice": "en-US-AriaNeural",    "personality": "ambitious, wants to shine brightest"},
}

# Story templates for variety
STORY_TYPES = [
    "two objects who think they're better than each other learn they need each other",
    "a character who is afraid of something learns to be brave",
    "a character feels left out but discovers their unique gift",
    "two characters from completely different worlds become best friends",
    "a character makes a mistake and learns how to make it right",
    "a character who always wants to be first learns that helping others matters more",
    "a very small character shows that size doesn't matter",
    "a character who thinks they're boring discovers they're actually amazing",
    "two characters who seem like opposites discover they're perfect partners",
    "a character learns that asking for help is a strength not a weakness",
]

PROMPT = """Write a short animated story for children ages 3-8 called "Tiny Tales".

Characters: {char1_name} ({char1_emoji}, {char1_personality}) and {char2_name} ({char2_emoji}, {char2_personality})
Story type: {story_type}
Setting: {setting}

Write a warm, funny, engaging story with a clear life lesson.

Use ONLY this exact format:

TITLE: [Catchy episode title — 5-7 words]
LESSON: [The simple life lesson in one sentence]
DESCRIPTION: [YouTube description — 100 chars, exciting for parents]

STORY:
NARRATOR: [Set the scene warmly — 2-3 sentences. Describe where we are and introduce our characters.]
{char1_name_upper}: [First line — establish personality immediately. Funny or charming.]
{char2_name_upper}: [React to {char1_name} — establish their personality. Maybe they disagree or are surprised.]
NARRATOR: [Move story forward — something happens that creates the problem or conflict. 2 sentences.]
{char1_name_upper}: [React to the problem — in character. Maybe too confident or too scared.]
{char2_name_upper}: [Their reaction — shows their different personality. Add humor.]
NARRATOR: [The problem gets bigger or more interesting. 1-2 sentences.]
{char1_name_upper}: [Things aren't going well — moment of doubt or challenge for this character.]
{char2_name_upper}: [They try to help or make it worse accidentally — funny moment.]
NARRATOR: [The turning point — something changes or a new idea appears. 1 sentence.]
{char1_name_upper}: [Realization or brave decision — this is the heart of the lesson.]
{char2_name_upper}: [Support, surprise, or join in — they're in this together now.]
NARRATOR: [They work together / solve the problem. The lesson becomes clear. 2 sentences.]
{char1_name_upper}: [Celebrate or express what they learned — warm, genuine.]
{char2_name_upper}: [Agree and add their perspective on the lesson — sweet ending line.]
NARRATOR: [Closing — wrap up warmly, speak directly to young viewers. Include the lesson gently. 2-3 sentences.]

Rules:
- Every line must be SHORT — 1-2 sentences max. Kids lose attention fast.
- Include at least 2 genuinely funny moments
- The lesson must feel EARNED not preachy
- Characters must sound distinct — their personality shows in HOW they speak
- Use simple words (ages 3-8)
- Total story: 14-18 lines of dialogue
- Make it feel like a real animated show — warm, silly, heartfelt
"""

SETTINGS = [
    "a cozy kitchen counter", "a sunny garden", "a school supply drawer",
    "a vegetable patch", "a forest clearing", "a bookshelf",
    "a night sky", "a rainy day windowsill", "a kitchen table set for dinner",
    "a toy box", "a refrigerator shelf", "a classroom desk",
]

import random

def get_character_pair():
    """Pick two interesting characters that work well together."""
    pairs = [
        ("salt", "pepper"), ("sun", "cloud"), ("pencil", "eraser"),
        ("carrot", "broccoli"), ("spoon", "fork"), ("cat", "dog"),
        ("bear", "bunny"), ("fox", "owl"), ("apple", "tomato"),
        ("moon", "star"), ("book", "crayon"), ("teapot", "pot"),
        ("duck", "elephant"), ("cat", "bunny"), ("bear", "fox"),
    ]
    pair = random.choice(pairs)
    c1 = CHARACTERS[pair[0]]
    c2 = CHARACTERS[pair[1]]
    return pair[0], c1, pair[1], c2

def load_used():
    f = SCRIPTS_DIR / "used_pairs.json"
    return json.loads(f.read_text()) if f.exists() else []

def save_used(used):
    (SCRIPTS_DIR / "used_pairs.json").write_text(json.dumps(used, indent=2))

def parse_story(raw, c1, c2):
    data = {"title": "", "lesson": "", "description": "", "dialogue": []}
    in_story = False
    current_speaker = None
    current_lines = []

    def flush():
        if current_speaker and current_lines:
            text = ' '.join(' '.join(current_lines).split()).strip()
            if text:
                data["dialogue"].append({"speaker": current_speaker, "text": text})

    # All known speaker prefixes
    c1up = c1["name"].upper() + ":"
    c2up = c2["name"].upper() + ":"

    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.startswith("TITLE:"): data["title"] = s[6:].strip()
        elif s.startswith("LESSON:"): data["lesson"] = s[7:].strip()
        elif s.startswith("DESCRIPTION:"): data["description"] = s[12:].strip()
        elif s == "STORY:":
            in_story = True; continue

        # Parse dialogue — works with or without STORY: marker
        if s.startswith("NARRATOR:"):
            flush(); current_speaker = "NARRATOR"; current_lines = [s[9:].strip()]
        elif s.startswith(c1up):
            flush(); current_speaker = c1["name"]; current_lines = [s[len(c1up):].strip()]
        elif s.startswith(c2up):
            flush(); current_speaker = c2["name"]; current_lines = [s[len(c2up):].strip()]
        elif current_speaker and not any(s.startswith(p) for p in ["TITLE:","LESSON:","DESCRIPTION:","STORY:"]):
            current_lines.append(s)

    flush()

    # Fallbacks if model didn't use structured format
    if not data["title"]:
        data["title"] = f"The Adventure of {c1['name']} and {c2['name']}"
    if not data["lesson"]:
        data["lesson"] = "Working together makes everything better"
    if not data["dialogue"]:
        # Re-parse more loosely — any "NAME: text" pattern
        for line in raw.split('\n'):
            s = line.strip()
            for name in [c1["name"], c2["name"], "Narrator", "NARRATOR"]:
                if s.upper().startswith(name.upper() + ":"):
                    speaker = "NARRATOR" if "narrator" in name.lower() else name.title()
                    text = s[len(name)+1:].strip()
                    if text:
                        data["dialogue"].append({"speaker": speaker, "text": text})
                    break

    return data

def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    key1, c1, key2, c2 = get_character_pair()
    story_type = random.choice(STORY_TYPES)
    setting = random.choice(SETTINGS)

    ep_num = len(list(SCRIPTS_DIR.glob("ep*.json"))) + 1
    print(f"Generating EP{ep_num:03d}: {c1['name']} & {c2['name']} — {story_type[:40]}...")

    raw = ai(PROMPT.format(
        char1_name=c1["name"], char1_emoji=c1["emoji"], char1_personality=c1["personality"],
        char2_name=c2["name"], char2_emoji=c2["emoji"], char2_personality=c2["personality"],
        char1_name_upper=c1["name"].upper(), char2_name_upper=c2["name"].upper(),
        story_type=story_type, setting=setting,
    ), model="sonnet", max_tokens=2000)

    script = parse_story(raw, c1, c2)
    script.update({
        "ep_num": ep_num,
        "char1_key": key1, "char2_key": key2,
        "char1": c1, "char2": c2,
        "story_type": story_type, "setting": setting,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "slug": re.sub(r'[^a-z0-9]+', '-', script.get("title","").lower())[:50],
    })

    fname = f"ep{ep_num:03d}-{script['slug']}.json"
    (SCRIPTS_DIR / fname).write_text(json.dumps(script, indent=2))

    print(f"Title: {script['title']}")
    print(f"Lesson: {script['lesson']}")
    print(f"Lines: {len(script['dialogue'])}")
    return SCRIPTS_DIR / fname

if __name__ == "__main__":
    main()
