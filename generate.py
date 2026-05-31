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

PROMPT = """Write a detailed, helpful article about: {topic}

Use this exact format:

TITLE: [Compelling title, 55-65 characters, includes main keyword]
META: [Meta description, 145-155 characters, includes keyword and benefit]
SLUG: [lowercase-url-slug-with-hyphens-only]
TAGS: [tag1, tag2, tag3, tag4]

CONTENT:
## Introduction
[2-3 engaging paragraphs that hook the reader and state the value clearly]

> **Quick Takeaways:** [3 bullet points summarizing the key benefits]

## [Section 1 Title]
[250-300 words with specific, actionable information]

## [Section 2 Title]
[250-300 words]

## [Section 3 Title]
[250-300 words with numbered list or comparison table where appropriate]

## [Section 4 Title]
[250-300 words]

## [Section 5 Title - Tips/Mistakes/Recommendations]
[200-250 words with bullet points]

## Final Thoughts
[150-200 word conclusion with clear next step for the reader]

Requirements:
- Write in a direct, conversational tone (no corporate fluff)
- Include specific tool names, numbers, and real examples
- Total length: 1400-1800 words
- Every section must provide concrete, actionable value
- Do not include affiliate disclaimers or sponsored content mentions
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
