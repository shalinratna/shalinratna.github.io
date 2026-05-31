#!/usr/bin/env python3
"""
Uploads a video to YouTube using the Data API v3.
Run setup_youtube_auth.py once first to get credentials.
"""
import json
import sys
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDS_FILE = Path("youtube/client_secrets.json")
TOKEN_FILE = Path("youtube/token.pickle")

def get_youtube_client():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path, script_path):
    with open(script_path) as f:
        script = json.load(f)

    youtube = get_youtube_client()

    title = script.get("title", "AI Money Tips")[:100]
    description = script.get("description", "")
    tags = script.get("tags", [])

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": f"{description}\n\n---\nLearn more at https://shalinratna.github.io",
                "tags": tags,
                "categoryId": "27",  # Education
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    )

    print(f"Uploading: {title}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%...")

    video_id = response["id"]
    print(f"Uploaded: https://youtube.com/watch?v={video_id}")

    # Track uploaded
    uploaded = Path("youtube/uploaded/log.json")
    log = json.loads(uploaded.read_text()) if uploaded.exists() else []
    log.append({"video_id": video_id, "title": title, "path": str(video_path)})
    uploaded.write_text(json.dumps(log, indent=2))

    return video_id

if __name__ == "__main__":
    if "--auth-only" in sys.argv:
        print("Authenticating with Google...")
        get_youtube_client()
        print("✓ Google account authorized! YouTube uploads are now fully automatic.")
        sys.exit(0)

    videos = sorted(Path("youtube/video").glob("*.mp4"))
    scripts = sorted(Path("youtube/scripts").glob("*.json"))
    if not videos or not scripts:
        print("No video or script found. Run make_video_v2.py first.")
        sys.exit(1)
    upload_video(videos[-1], scripts[-1])
