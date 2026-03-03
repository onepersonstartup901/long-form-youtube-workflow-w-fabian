#!/usr/bin/env python3
"""
YouTube Video Uploader.

Uploads videos to YouTube with metadata, thumbnails, and scheduling
using the YouTube Data API v3.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]

YOUTUBE_CATEGORIES = {
    "film": "1",
    "autos": "2",
    "music": "10",
    "pets": "15",
    "sports": "17",
    "gaming": "20",
    "comedy": "23",
    "entertainment": "24",
    "news": "25",
    "howto": "26",
    "education": "27",
    "science": "28",
    "nonprofits": "29",
}


def get_youtube_credentials():
    """Get OAuth2 credentials for YouTube API."""
    creds = None
    token_path = "data/youtube_token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def upload_video(
    video_path: str,
    metadata: dict,
    thumbnail_path: str = None,
    schedule: str = None,
    visibility: str = "private",
    playlist_id: str = None,
) -> dict:
    """
    Upload a video to YouTube.

    Args:
        video_path: Path to video file
        metadata: Metadata dict (from generate_metadata.py)
        thumbnail_path: Path to thumbnail image
        schedule: ISO 8601 publish time (for scheduled videos)
        visibility: public / unlisted / private
        playlist_id: Optional playlist to add to

    Returns:
        Upload result dict with video_id and url
    """
    creds = get_youtube_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # Pick first title option
    title = metadata.get("titles", ["Untitled"])[0] if isinstance(metadata.get("titles"), list) else metadata.get("title", "Untitled")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    category = metadata.get("category", "howto")
    category_id = YOUTUBE_CATEGORIES.get(category.lower(), "27")  # Default to education

    # Build request body
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags[:50],  # YouTube limit
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False,
        },
    }

    if schedule and visibility == "private":
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = schedule

    # Upload video
    print(f"Uploading: {video_path}")
    print(f"Title: {title}")
    print(f"Visibility: {visibility}")

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Upload complete! Video ID: {video_id}")
    print(f"URL: {video_url}")

    # Upload thumbnail
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"Setting thumbnail: {thumbnail_path}")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()
        print("Thumbnail set.")

    # Add to playlist
    if playlist_id:
        print(f"Adding to playlist: {playlist_id}")
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                },
            },
        ).execute()
        print("Added to playlist.")

    result = {
        "video_id": video_id,
        "url": video_url,
        "title": title,
        "visibility": visibility,
        "uploaded_at": datetime.now().isoformat(),
        "schedule": schedule,
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--metadata", required=True, help="Path to metadata JSON")
    parser.add_argument("--thumbnail", help="Path to thumbnail image")
    parser.add_argument("--schedule", help="ISO 8601 publish time")
    parser.add_argument("--visibility", default="private",
                        choices=["public", "unlisted", "private"])
    parser.add_argument("--playlist", help="Playlist ID to add to")

    args = parser.parse_args()

    # Load metadata
    with open(args.metadata, "r") as f:
        metadata = json.load(f)

    # Upload
    result = upload_video(
        args.video,
        metadata,
        args.thumbnail,
        args.schedule,
        args.visibility,
        args.playlist,
    )

    # Save result
    os.makedirs(".tmp/uploads", exist_ok=True)
    slug = result["title"].lower().replace(" ", "_")[:40]
    result_path = f".tmp/uploads/{slug}_result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nUpload result saved to {result_path}")

    # Append to content log
    os.makedirs("data", exist_ok=True)
    log_path = "data/content_log.json"
    log = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log = json.load(f)
    log.append(result)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Content log updated: {log_path}")


if __name__ == "__main__":
    main()
