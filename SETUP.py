#!/usr/bin/env python3
"""
One-time setup wizard for Money Brain automation.
Run this once: python3 SETUP.py
"""
import json
import subprocess
import sys
from pathlib import Path

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
CHECK = f"{GREEN}✓{RESET}"
ARROW = f"{BLUE}→{RESET}"

def clear(): print("\n" * 2)

def header(text):
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  {text}{RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")

def done(text): print(f"  {CHECK} {GREEN}{text}{RESET}")
def info(text): print(f"  {ARROW} {text}")
def warn(text): print(f"  {YELLOW}⚠  {text}{RESET}")

def ask(prompt, secret=False):
    try:
        import getpass
        if secret:
            return getpass.getpass(f"  {BOLD}{prompt}:{RESET} ").strip()
        return input(f"  {BOLD}{prompt}:{RESET} ").strip()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)

def step_pexels():
    header("STEP 1 of 3 — Pexels API Key (Free Stock Footage)")
    key_file = Path("youtube/pexels_key.txt")

    if key_file.exists() and key_file.read_text().strip():
        done("Pexels already configured!")
        return

    print("  This gives your videos REAL stock footage instead of solid backgrounds.")
    print()
    info("Safari is open at pexels.com/api")
    print()
    print(f"  {BOLD}Do this:{RESET}")
    print("  1. Click  'Your API Key'  or  'Get Started'")
    print("  2. Sign up or log in with Google (free)")
    print("  3. Copy the API key shown on the page")
    print()

    key = ask("Paste your Pexels API key here")
    if key:
        key_file.write_text(key)
        done(f"Pexels API key saved!")
    else:
        warn("Skipped — videos will use solid color backgrounds")

def step_youtube_channel():
    header("STEP 2 of 3 — Create 'Money Brain' YouTube Channel")
    channel_file = Path("youtube/channel_id.txt")

    if channel_file.exists() and channel_file.read_text().strip():
        done("YouTube channel already configured!")
        return

    print("  This is where your videos will be published automatically.")
    print()
    info("Safari is open at youtube.com/create_channel")
    print()
    print(f"  {BOLD}Do this:{RESET}")
    print("  1. Sign in with your Google account if needed")
    print("  2. Choose  'Use a custom name'")
    print("  3. Name it:  Money Brain")
    print("  4. Click Create")
    print("  5. After creating, go to: youtube.com/account_advanced")
    print("  6. Copy your  Channel ID  (starts with UC...)")
    print()

    channel_id = ask("Paste your YouTube Channel ID (starts with UC)")
    if channel_id:
        channel_file.write_text(channel_id.strip())
        done(f"Channel ID saved: {channel_id[:20]}...")
    else:
        warn("Skipped — upload will be enabled when you add this later")

def step_youtube_oauth():
    header("STEP 3 of 3 — YouTube Upload Credentials")
    creds_file = Path("youtube/client_secrets.json")

    if creds_file.exists():
        done("YouTube OAuth already configured!")
        return

    print("  This lets your Mac upload videos to YouTube automatically.")
    print()
    info("Safari is open at console.cloud.google.com")
    print()
    print(f"  {BOLD}Do this (copy these steps exactly):{RESET}")
    print()
    print("  1. Name the project:  MoneyBrain  → click  CREATE")
    print("  2. Wait for it to create, then in the top search bar type:")
    print("       YouTube Data API v3")
    print("  3. Click the result → click  ENABLE")
    print("  4. Click  'CREATE CREDENTIALS'  in the top right")
    print("  5. Choose:  OAuth client ID")
    print("  6. If it asks about consent screen → External → fill in:")
    print("       App name: Money Brain")
    print("       Your email for support")
    print("       → Save and Continue → Save and Continue → Back to Dashboard")
    print("  7. Back in credentials: Application type →  Desktop app")
    print("       Name: Money Brain  → CREATE")
    print("  8. Click  DOWNLOAD JSON  → file downloads to your Downloads folder")
    print()

    input(f"  {BOLD}Press Enter when you've downloaded the JSON file...{RESET} ")
    print()

    # Find the downloaded file
    downloads = Path.home() / "Downloads"
    json_files = sorted(downloads.glob("client_secret*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

    if json_files:
        src = json_files[0]
        creds_file.parent.mkdir(exist_ok=True)
        creds_file.write_text(src.read_text())
        done(f"Found and saved: {src.name}")

        # Trigger OAuth flow
        print()
        print(f"  {BOLD}One more click — authorizing your Google account...{RESET}")
        info("A browser window will open. Log in and click Allow.")
        print()
        input("  Press Enter to open the authorization window... ")
        result = subprocess.run([sys.executable, "youtube/upload_youtube.py", "--auth-only"],
                              capture_output=False)
    else:
        warn("Couldn't find downloaded JSON file.")
        path = ask("Paste the full path to the downloaded JSON file")
        if path and Path(path).exists():
            creds_file.write_text(Path(path).read_text())
            done("Credentials saved!")

def final_summary():
    header("SETUP COMPLETE 🎉")

    pexels = Path("youtube/pexels_key.txt").exists()
    channel = Path("youtube/channel_id.txt").exists()
    creds = Path("youtube/client_secrets.json").exists()
    token = Path("youtube/token.pickle").exists()

    print(f"  {'✓' if pexels else '✗'} Pexels stock footage: {'ENABLED' if pexels else 'skipped'}")
    print(f"  {'✓' if channel else '✗'} YouTube channel: {'CONFIGURED' if channel else 'skipped'}")
    print(f"  {'✓' if creds else '✗'} YouTube upload: {'READY' if (creds and token) else 'credentials saved' if creds else 'skipped'}")
    print()

    if pexels and creds and token:
        print(f"  {GREEN}{BOLD}Everything is live. Your Mac will:{RESET}")
        print(f"  • Generate + publish 3 SEO articles every night at 3am")
        print(f"  • Generate + upload 1 Money Brain YouTube video every night at 4am")
        print(f"  • Auto-cut 60s short for TikTok/Reels from every video")
        print()
        print(f"  {BOLD}You do nothing. Ever.{RESET}")
    else:
        print(f"  {YELLOW}Run this again anytime to finish remaining steps.{RESET}")
        print(f"  python3 SETUP.py")
    print()

if __name__ == "__main__":
    print(f"\n{BOLD}  Money Brain — Passive Income Setup Wizard{RESET}")
    print(f"  This will take about 10 minutes total.\n")

    step_pexels()
    step_youtube_channel()
    step_youtube_oauth()
    final_summary()
