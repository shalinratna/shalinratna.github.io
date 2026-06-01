#!/usr/bin/env python3
"""
Generates Dark Files true crime podcast scripts.
Feels like two real friends hosting a show — natural, warm, funny, then chilling.
"""
import json
import re
import sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent if "/" in __file__ else __import__("pathlib").Path(".")))
from ai_client import generate as _ai_generate
from datetime import datetime
from pathlib import Path

CASES_FILE = Path("podcast/cases.json")
SCRIPTS_DIR = Path("podcast/scripts")

# Character bibles — consistent across every episode
MORGAN_BIO = """
MORGAN's personality:
- 29, originally from San Diego, now in Portland Oregon
- Warm, funny, slightly self-deprecating, obsessed with true crime since she was 12
- Has a golden retriever named Biscuit who appears in stories constantly
- Drinks too much iced coffee, terrible at hiking despite trying every weekend
- Dark sense of humor — laughs at her own inappropriate jokes then immediately feels bad
- Catchphrases: "Okay so here's the thing...", "And THIS is where it gets unhinged", "I cannot stress this enough"
- Tendency to go on tangents about random details she finds fascinating
- Gets genuinely emotional about victims — her voice softens when she talks about them
"""

TAYLOR_BIO = """
TAYLOR's personality:
- 31, grew up in Manchester UK, moved to the US at 22, never left
- Sarcastic, quick, warm underneath the dry humor
- Has a boyfriend named Jake who she references — he's very normal and confused by her true crime obsession
- Wine drinker, calls herself a "functional disaster"
- Reactions are fast and sharp: "Sorry WHAT", "Absolutely not", "I cannot with this"
- Tends to make dark jokes then immediately say "too soon? probably too soon"
- Genuinely freaked out by the cases — covers it with humor
- Has a running bit where she rates how unhinged each case is on a scale of 1-10
"""

PROMPT = """You are writing a script for "Dark Files" — a true crime podcast hosted by two best friends, Morgan and Taylor.

The show feels like eavesdropping on two funny, warm, slightly chaotic women who happen to be obsessed with true crime. It sounds NOTHING like a scripted podcast. It sounds like two real people talking.

{morgan_bio}

{taylor_bio}

Today's case: {case}

Write a FULL episode script. The script must feel completely natural — interruptions, laughter, tangents, personal stories. NOT a document. A CONVERSATION.

Format: Use only MORGAN: and TAYLOR: labels. Write everything else as natural dialogue.

---

MORGAN: [Cold open — the most shocking single sentence from today's case. No greeting yet. Just drop us in.]
TAYLOR: [Her gut reaction — one line, completely unfiltered]

[--- INTRO BANTER SECTION — 3-4 minutes of real conversation before the case ---]

MORGAN: Okay hi everyone, welcome back to Dark Files. I'm Morgan.
TAYLOR: I'm Taylor, and I have already heard what today's case is and I need everyone to know I was not okay about it.
MORGAN: [Brief funny/warm response to Taylor's reaction — then pivot to asking about Taylor's week. Reference something specific like Jake, her wine habit, something she mentioned last episode]
TAYLOR: [A genuine personal story about her week — funny, specific, relatable. 3-5 sentences. Can reference Jake, her general chaos, something mundane that went wrong]
MORGAN: [React to Taylor's story naturally — laugh, commiserate, share a related quick thing about her own week. Reference Biscuit, hiking, her iced coffee addiction, or something current]
TAYLOR: [Short reaction + transition toward getting into the episode — something like "okay but I feel like we need to get into this because I've been thinking about it all day"]
MORGAN: [Agree, set up why THIS case, why TODAY — maybe reference how she found it, how long she's been wanting to cover it. Build genuine anticipation.]
TAYLOR: I'm ready. I think. No I'm not ready but let's go.

[--- THE CASE — Told conversationally, not like a report ---]

MORGAN: [Set the scene — place, time, who the victim was. Specific vivid details. Speak to the listener like you're telling a story to a friend over coffee. 5-6 sentences.]
TAYLOR: [React to a specific detail — ask a natural follow-up question or express shock at something specific]
MORGAN: [Answer + continue the timeline — what led up to the crime, what was normal about this person's life before. 5-6 sentences. Include a detail that will become significant later.]
TAYLOR: [Pick up on a detail that feels off — "wait hold on, so you're telling me..." 1-2 sentences]
MORGAN: [Exactly right, and here's why that matters — build the tension. What happened. Be specific. 5-6 sentences. Include a moment that makes Taylor react.]
TAYLOR: [Genuine shocked or horrified reaction — can be dark humor or genuine horror. Rate the case on the unhinged scale if appropriate. 2 sentences.]
MORGAN: [The investigation — who looked, what they found, what was suspicious, who the suspects were. 5-6 sentences. Include a detail that made investigators question everything.]
TAYLOR: [Ask the question every listener is screaming at their phone. "But WHY would they..." or "Okay but did anyone check..." 1-2 sentences]
MORGAN: [Answer it — this is where you drop the most disturbing reveal. Take your time. 4-5 sentences. Let the weight of it land.]
TAYLOR: [Sit with it for a second. React authentically. Maybe make a dark joke, then pull back. 2 sentences.]
MORGAN: [Where it stands today — solved, cold case, or recently reopened. Be honest about what we don't know. 4-5 sentences.]
TAYLOR: [Final reaction — something that will stick with the listener. Reference something from earlier that hits differently now. 2 sentences.]

[--- OUTRO — Warm, personal, feels like hanging up the phone with a friend ---]

MORGAN: [Wrap up the case with genuine emotion — honor the victim if relevant. Tip line or cold case resources if applicable. 3 sentences.]
TAYLOR: [Add something — a final thought, a dark observation, or something human about the victim. 1-2 sentences.]
MORGAN: Okay. That was a lot. Taylor, rate it.
TAYLOR: [Give a genuine unhinged rating on the 1-10 scale with a brief reason — funny but real. "That's a solid 9 out of 10 on the unhinged scale because..." 1-2 sentences]
MORGAN: [Agree or debate the rating briefly — feel free to bicker about it for one exchange]
TAYLOR: [Concede or hold firm — then pivot to signing off]
MORGAN: Okay everyone — thank you so much for listening to Dark Files. New episode drops [day of week]. Don't forget to subscribe, leave a review, it genuinely helps us more than you know. And as always —
TAYLOR: Stay curious, stay safe, and maybe don't go hiking alone.
MORGAN: [One last Biscuit mention or personal sign-off — warm and specific]

---

CRITICAL RULES — READ THESE OR THE SCRIPT IS TRASH:

1. NATURAL SPEECH ONLY. Real people say: "okay so like", "wait wait wait", "no no no", "I literally", "you know what I mean?", "I'm not even kidding", "honestly", "I mean", "right?", "okay but here's the thing", sentence fragments, run-on thoughts. USE THESE.

2. CONTRACTIONS ALWAYS. Never "do not" — always "don't". Never "it is" — always "it's". Never "I am" — always "I'm". No exceptions.

3. MORGAN'S STORYTELLING sounds like she's telling her best friend something insane she read — not like a Wikipedia article. She goes "okay so picture this" and "and you're gonna think I'm making this up but" and trails off dramatically.

4. TAYLOR reacts like a real person watching a horror movie with her friend. "Okay STOP." "No absolutely not." "Wait I'm sorry — she did WHAT?" Short, punchy, real.

5. FILLER WORDS are your friend. "Like", "um", "so", "I mean", "honestly", "literally", "basically" — scatter them naturally. Not every sentence. But enough that it sounds human.

6. INTERRUPTIONS. Taylor can cut Morgan off mid-sentence. Morgan can say "exactly, exactly" while Taylor's still talking. Real conversation overlaps.

7. HUMOR must land. At least two moments where something is genuinely funny — dark humor is fine, that's the show's brand.

8. EMOTIONAL RANGE. Morgan's voice drops when she talks about victims. Taylor gets quiet when something really hits. Not every line is at the same energy level.

9. THE COLD OPEN LINE must be the single most jaw-dropping sentence of the episode. Not an intro — a hook.

10. Total word count: 1600-2200 words. This is a 20-25 minute episode.
"""

REPLENISH_PROMPT = """Generate 30 new true crime podcast episode topics for a show called Dark Files.

Each must be a real documented case — murder, disappearance, cold case, heist, or crime.
Prioritize: underreported cases, international cases, historical crimes, cases with bizarre twists.
Avoid: OJ Simpson, Ted Bundy, Jeffrey Dahmer (overexposed).

Reply with ONLY a numbered list. One sentence per case.
1. [Case description]
...

Generate 30 now:"""

def call_ollama(prompt, tokens=3000):
    return _ai_generate(prompt, model="sonnet", max_tokens=tokens)


def parse_script(raw, case):
    data = {
        "case": case,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "title": "", "description": "", "slug": "",
        "dialogue": []
    }

    current_speaker = None
    current_lines = []

    def flush():
        if current_speaker and current_lines:
            text = ' '.join(' '.join(current_lines).split()).strip()
            if text and len(text) > 3:
                data["dialogue"].append({"speaker": current_speaker, "text": text})

    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.startswith("MORGAN:"):
            flush(); current_speaker = "MORGAN"; current_lines = [s[7:].strip()]
        elif s.startswith("TAYLOR:"):
            flush(); current_speaker = "TAYLOR"; current_lines = [s[7:].strip()]
        elif s.startswith("TITLE:"):
            flush(); current_speaker = None; current_lines = []
            data["title"] = s[6:].strip()
        elif s.startswith("DESCRIPTION:"):
            data["description"] = s[12:].strip()
        elif current_speaker:
            if not s.startswith('[---') and not s.startswith('---'):
                current_lines.append(s)
    flush()

    # Auto-generate title from case if model didn't provide one
    if not data["title"]:
        words = case.split()[:8]
        data["title"] = ' '.join(words).rstrip('.,')

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

def replenish_cases(data):
    print("Generating new cases...")
    raw = call_ollama(REPLENISH_PROMPT)
    new = []
    for line in raw.strip().split('\n'):
        line = re.sub(r'^\d+[\.\)]\s*', '', line.strip()).strip()
        if len(line) > 30 and line not in data["cases"]:
            new.append(line)
    data["cases"].extend(new)
    save_cases(data)
    print(f"Added {len(new)} new cases.")

def main():
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_cases()

    unused = [c for c in data["cases"] if c not in data["used"]]
    if len(unused) < 10:
        replenish_cases(data)
        data = load_cases()

    case = get_next_case(data)
    if not case:
        print("No cases available.")
        return

    ep_num = len(data["used"]) + 1
    print(f"Generating EP{ep_num:03d}: {case[:60]}...")

    raw = call_ollama(PROMPT.format(
        case=case,
        morgan_bio=MORGAN_BIO,
        taylor_bio=TAYLOR_BIO
    ))
    script = parse_script(raw, case)
    script["ep_num"] = ep_num

    fname = f"ep{ep_num:03d}-{script['slug']}.json"
    (SCRIPTS_DIR / fname).write_text(json.dumps(script, indent=2))

    data["used"].append(case)
    save_cases(data)

    print(f"Saved: {fname}")
    print(f"Title: {script['title']}")
    print(f"Dialogue lines: {len(script['dialogue'])}")

if __name__ == "__main__":
    main()
