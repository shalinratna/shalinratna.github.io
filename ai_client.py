#!/usr/bin/env python3
"""
Single AI client for all content generation.
Uses Claude API (Haiku for speed/cost, Sonnet for quality).
~$3-5/month total for all pipelines.

Get your API key: console.anthropic.com → API Keys → Create Key
Save it: echo "sk-ant-..." > /Users/shalin/Documents/Projects/ai-income/.api_key
"""
import os
from pathlib import Path

KEY_FILE = Path(__file__).parent / ".api_key"

def get_key():
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    return os.environ.get("ANTHROPIC_API_KEY", "")

def generate(prompt, model="haiku", max_tokens=3000):
    """
    model: "haiku" (fast, cheap, ~$0.001/call) or "sonnet" (best quality, ~$0.01/call)
    """
    import anthropic
    key = get_key()
    if not key:
        raise RuntimeError(
            "No API key. Get one at console.anthropic.com → save to .api_key file"
        )

    model_id = "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"
    client = anthropic.Anthropic(api_key=key)

    msg = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
