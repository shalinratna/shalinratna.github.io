#!/usr/bin/env python3
import json
import re
import requests
import sys
from datetime import datetime
from pathlib import Path

SITE_NAME = "AI Money Tools"
SITE_URL = "https://shalinratna.github.io"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434"
ARTICLES_PER_RUN = 3

PROMPT = """Write an expert, SEO-optimized article about: {topic}

Use this EXACT format (markers must appear exactly as written):

TITLE: [55-65 chars. Lead with the primary keyword. Make it specific and benefit-driven.]
META: [150-158 chars. Include keyword + clear benefit + mild urgency. No clickbait.]
SLUG: [lowercase-hyphens-only-no-special-chars-max-60-chars]
TAGS: [6-8 tags: mix of broad + long-tail keywords, comma separated]

CONTENT:
## [Keyword-rich H2: restate topic as a question or promise]

[Opening paragraph: lead with a surprising stat or relatable problem. 2-3 sentences max.]

[Second paragraph: promise exactly what this article delivers and why it matters right now.]

> **Key Takeaways**
> - [Specific benefit 1 with number or result]
> - [Specific benefit 2 with number or result]
> - [Specific benefit 3 with number or result]

## [H2: First major concept — name the specific tool or method]

[200-250 words. Open with what it is and why it works. Include a numbered step-by-step process or a real example. Name specific tools like ChatGPT, Claude, Copilot, Mint, YNAB, etc. End with one concrete result the reader can expect.]

## [H2: Second concept — go deeper, add comparison or data]

[200-250 words. Include a markdown table comparing 2-3 options OR a numbered list of exact steps. Be specific with numbers, percentages, timeframes.]

## [H2: Third concept — common mistakes or pro tips]

[200-250 words. List 4-5 specific mistakes or tips as bullet points with brief explanations. Be direct.]

## [H2: Fourth concept — advanced tactic or tool combo]

[200-250 words. One specific advanced technique most people miss. Include exact prompts, settings, or tool combinations where relevant.]

## [H2: Step-by-step action plan]

[150-200 words. Numbered list of exactly 5-7 steps the reader can start TODAY. Each step is one sentence, specific and actionable.]

## Frequently Asked Questions

**[Question 1 about the topic — something people actually Google]**
[2-3 sentence answer. Direct and specific.]

**[Question 2 about the topic]**
[2-3 sentence answer.]

**[Question 3 about the topic]**
[2-3 sentence answer.]

## Final Verdict

[100-150 words. Summarize the single most important thing to do first. Include a specific next step. End with encouragement.]

Rules:
- Total length: 1500-2000 words
- Conversational but authoritative tone
- Every claim needs a specific number, tool name, or example — no vague statements
- Never say "in conclusion" or "in summary"
- Bold the most important phrase in each section
- Include at least one markdown table somewhere in the article
"""

def call_ollama(topic):
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": PROMPT.format(topic=topic),
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 2800}
            },
            timeout=300
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def parse_response(raw, topic):
    title = topic
    meta = ""
    slug = ""
    tags = []
    content = ""

    lines = raw.strip().split('\n')
    content_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("TITLE:"):
            title = stripped[6:].strip()
        elif stripped.startswith("META:"):
            meta = stripped[5:].strip()
        elif stripped.startswith("SLUG:"):
            slug = stripped[5:].strip()
            slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
            slug = re.sub(r'-+', '-', slug).strip('-')
        elif stripped.startswith("TAGS:"):
            raw_tags = stripped[5:].strip()
            tags = [t.strip() for t in raw_tags.split(',')]
        elif stripped == "CONTENT:":
            content_start = i + 1
            break

    content = '\n'.join(lines[content_start:]).strip()

    if not slug and title:
        slug = re.sub(r'[^a-z0-9\s-]', '', title.lower())
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')[:60]

    return {
        "title": title,
        "meta": meta,
        "slug": slug,
        "tags": tags,
        "content": content,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

def save_article(article):
    articles_dir = Path("articles")
    articles_dir.mkdir(exist_ok=True)
    filename = f"{article['date']}-{article['slug']}.md"
    filepath = articles_dir / filename

    fm = f"""---
title: "{article['title'].replace('"', "'")}"
description: "{article['meta'].replace('"', "'")}"
slug: "{article['slug']}"
date: "{article['date']}"
tags: {json.dumps(article['tags'])}
---

{article['content']}
"""
    filepath.write_text(fm, encoding='utf-8')
    return filepath

def load_topics():
    with open("topics.json") as f:
        return json.load(f)

def save_topics(data):
    with open("topics.json", "w") as f:
        json.dump(data, f, indent=2)

def main():
    data = load_topics()
    pending = [t for t in data["topics"] if t not in data["used"]]

    if not pending:
        print("All topics used. Add more to topics.json")
        sys.exit(0)

    count = min(ARTICLES_PER_RUN, len(pending))
    print(f"Generating {count} articles...")

    for i in range(count):
        topic = pending[i]
        print(f"\n[{i+1}/{count}] {topic}")

        raw = call_ollama(topic)
        if not raw:
            print("Skipping — Ollama failed")
            continue

        article = parse_response(raw, topic)
        path = save_article(article)
        data["used"].append(topic)
        save_topics(data)
        print(f"Saved: {path.name}")

    print(f"\nDone. {count} articles generated.")

if __name__ == "__main__":
    main()
