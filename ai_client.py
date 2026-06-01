#!/usr/bin/env python3
"""
AI client — uses Claude API if credits available, falls back to Ollama (free).
Free mode: llama3.1:8b via Ollama — good quality, runs locally on M4 Max.
Paid mode: Claude Sonnet — best quality, ~$4/month.
"""
import os
import requests
from pathlib import Path

KEY_FILE    = Path(__file__).parent / ".api_key"
OLLAMA_URL  = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"

def _ollama_available():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(OLLAMA_MODEL.split(":")[0] in m for m in models)
    except:
        return False

def _claude_credits():
    """Returns True if Claude API key exists and has credits."""
    key = KEY_FILE.read_text().strip() if KEY_FILE.exists() else ""
    if not key:
        return False, ""
    return True, key

def generate(prompt, model="sonnet", max_tokens=3000):
    """
    Generate text. Tries Claude API first, falls back to Ollama automatically.
    model param is ignored in free mode — always uses llama3.1:8b.
    """
    has_key, key = _claude_credits()

    # Try Claude API first
    if has_key:
        try:
            import anthropic
            model_id = "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            if "credit" in str(e).lower() or "balance" in str(e).lower():
                pass  # Fall through to Ollama
            else:
                raise

    # Free fallback: Ollama
    if not _ollama_available():
        # Start Ollama if not running
        import subprocess
        subprocess.Popen(["ollama", "serve"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        time.sleep(6)

    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": max_tokens}
        },
        timeout=300
    )
    resp.raise_for_status()
    return resp.json()["response"]
