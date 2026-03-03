#!/usr/bin/env python3
"""
YouTube Video Uploader.

Uploads videos to YouTube with metadata, thumbnails, and scheduling
using the YouTube Data API v3. Supports resumable uploads for large files,
OAuth2 authentication with token caching, and metadata generation from
pipeline state.

Usage:
    # Upload with explicit metadata
    python execution/youtube_upload.py \\
        --video-id 20260303_ai_tools \\
        --title "5 AI Tools That Will Replace Your Entire Tech Stack" \\
        --description "In this video..." \\
        --tags "ai,tools,tech" \\
        --privacy private \\
        --thumbnail .tmp/20260303_ai_tools/thumbnail.png \\
        --category 28

    # Upload from metadata.json
    python execution/youtube_upload.py \\
        --video-id 20260303_ai_tools \\
        --from-metadata

    # Generate metadata.json from pipeline state (does not upload)
    python execution/youtube_upload.py \\
        --video-id 20260303_ai_tools \\
        --generate-metadata
"""

import os
import sys
import json
import re
import argparse
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"

# ---------------------------------------------------------------------------
# YouTube constants
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

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

# Reverse mapping: category id -> name (for display)
CATEGORY_ID_TO_NAME = {v: k for k, v in YOUTUBE_CATEGORIES.items()}

# Default chunk size: 10 MB for resumable uploads
CHUNK_SIZE = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_video_dir(video_id: str) -> Path:
    """Return the .tmp/{video_id} working directory."""
    return TMP_DIR / video_id


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower())[:40].strip("_")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def get_youtube_credentials():
    """
    Obtain OAuth2 credentials for the YouTube Data API.

    Token search order:
      1. youtube_token.json in project root
      2. data/youtube_token.json (legacy location)

    Client secrets search order:
      1. YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET env vars
      2. credentials.json in project root (shared with Sheets OAuth)
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None

    # Possible token locations (prefer project-root, fall back to data/)
    token_paths = [
        PROJECT_ROOT / "youtube_token.json",
        PROJECT_ROOT / "data" / "youtube_token.json",
    ]

    token_path = None
    for tp in token_paths:
        if tp.exists():
            token_path = tp
            break

    # If no existing token found, we will save to the first location
    if token_path is None:
        token_path = token_paths[0]

    # Try loading cached token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            print(f"Warning: Could not load cached token ({e}), will re-authenticate.")

    # Refresh or run full OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired YouTube token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed ({e}), running full OAuth flow...")
                creds = None

        if not creds:
            # Build client config from env vars or credentials.json
            client_id = os.getenv("YOUTUBE_CLIENT_ID")
            client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

            if client_id and client_secret:
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                # Fall back to credentials.json
                creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
                creds_path = PROJECT_ROOT / creds_file
                if not creds_path.exists():
                    print(f"Error: No credentials found.", file=sys.stderr)
                    print(f"  Set YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET in .env", file=sys.stderr)
                    print(f"  Or place credentials.json in {PROJECT_ROOT}", file=sys.stderr)
                    sys.exit(1)
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)

            print("Opening browser for YouTube OAuth consent...")
            creds = flow.run_local_server(port=0)

        # Save token for reuse
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        print(f"YouTube token saved to {token_path}")

    return creds


# ---------------------------------------------------------------------------
# Metadata generation from pipeline state
# ---------------------------------------------------------------------------


def generate_metadata_from_state(video_id: str) -> dict:
    """
    Generate a metadata.json from the video's state.json and script.

    Reads:
      - .tmp/{video_id}/state.json  (topic, niche, etc.)
      - .tmp/{video_id}/script.md   (narration script)
      - .tmp/{video_id}/parsed_script.json (structured sections with timestamps)

    Returns:
      A metadata dict ready for YouTube upload.
    """
    video_dir = get_video_dir(video_id)
    state_path = video_dir / "state.json"
    script_path = video_dir / "script.md"
    parsed_path = video_dir / "parsed_script.json"

    if not state_path.exists():
        print(f"Error: state.json not found at {state_path}", file=sys.stderr)
        sys.exit(1)

    with open(state_path) as f:
        state = json.load(f)

    topic = state.get("topic", "Untitled Video")
    niche = state.get("niche", "tech/AI")

    # --- Title ---
    title = _generate_title(topic, state)

    # --- Description ---
    description = _generate_description(topic, state, script_path, parsed_path)

    # --- Tags ---
    tags = _generate_tags(topic, niche, state)

    # --- Category ---
    category = state.get("category", "28")
    if category in YOUTUBE_CATEGORIES:
        category = YOUTUBE_CATEGORIES[category]
    # Ensure it is a string category ID
    if not category.isdigit():
        category = "28"  # Default: Science & Technology

    # --- Thumbnail ---
    thumbnail = None
    for name in ("thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg"):
        if (video_dir / name).exists():
            thumbnail = name
            break

    # --- Privacy ---
    privacy = state.get("visibility", "private")
    if privacy not in ("public", "unlisted", "private"):
        privacy = "private"

    metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "category": category,
        "privacy": privacy,
    }
    if thumbnail:
        metadata["thumbnail"] = thumbnail

    return metadata


def _generate_title(topic: str, state: dict) -> str:
    """Extract or generate a video title from topic and state."""
    # If state already has an explicit title, use it
    if state.get("title"):
        return state["title"]

    # If there are generated titles from the metadata stage, pick the first
    if state.get("titles") and isinstance(state["titles"], list):
        return state["titles"][0]

    # Otherwise, capitalize the topic
    title = topic.strip()
    # Ensure under 100 chars (YouTube max)
    if len(title) > 100:
        title = title[:97] + "..."
    return title


def _generate_description(
    topic: str,
    state: dict,
    script_path: Path,
    parsed_path: Path,
) -> str:
    """Build a YouTube description with hook, timestamps, and tags."""
    lines = []

    # Hook / summary line
    hook = state.get("hook", "")
    if hook:
        lines.append(hook)
        lines.append("")
    else:
        lines.append(f"Everything you need to know about {topic}.")
        lines.append("")

    # Brief summary from script intro
    if script_path.exists():
        with open(script_path) as f:
            script_text = f.read()
        # Extract first paragraph (after any frontmatter / heading)
        paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        if paragraphs:
            summary = paragraphs[0][:500]
            lines.append(summary)
            lines.append("")

    # Timestamps from parsed script
    timestamps = _extract_timestamps(parsed_path)
    if timestamps:
        lines.append("--- Timestamps ---")
        for ts in timestamps:
            lines.append(f"{ts['time']} - {ts['label']}")
        lines.append("")

    # Tags as hashtags at the bottom
    niche = state.get("niche", "")
    if niche:
        niche_tag = "#" + re.sub(r"[^a-zA-Z0-9]", "", niche)
        lines.append(f"#YouTube {niche_tag}")

    return "\n".join(lines)


def _extract_timestamps(parsed_path: Path) -> list[dict]:
    """
    Extract chapter timestamps from parsed_script.json.

    Returns a list of dicts: [{"time": "0:00", "label": "Intro"}, ...]
    """
    if not parsed_path.exists():
        return []

    try:
        with open(parsed_path) as f:
            parsed = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []

    timestamps = []
    sections = parsed.get("sections", parsed.get("segments", []))

    for section in sections:
        start = section.get("start_time", section.get("start", None))
        label = section.get("title", section.get("heading", section.get("label", "")))

        if start is not None and label:
            # Format seconds as M:SS or H:MM:SS
            total_seconds = int(float(start))
            if total_seconds >= 3600:
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                time_str = f"{h}:{m:02d}:{s:02d}"
            else:
                m = total_seconds // 60
                s = total_seconds % 60
                time_str = f"{m}:{s:02d}"
            timestamps.append({"time": time_str, "label": label})

    # Always ensure 0:00 entry exists
    if timestamps and timestamps[0]["time"] != "0:00":
        timestamps.insert(0, {"time": "0:00", "label": "Intro"})

    return timestamps


def _generate_tags(topic: str, niche: str, state: dict) -> list[str]:
    """Auto-generate relevant tags from topic, niche, and state."""
    tags = []

    # Primary keyword: full topic
    tags.append(topic.lower().strip())

    # Break topic into individual words/phrases
    words = re.findall(r"[a-zA-Z0-9]+", topic.lower())
    for word in words:
        if len(word) > 2 and word not in tags:
            tags.append(word)

    # Two-word combinations from the topic
    for i in range(len(words) - 1):
        combo = f"{words[i]} {words[i+1]}"
        if combo not in tags:
            tags.append(combo)

    # Niche-based tags
    if niche:
        niche_lower = niche.lower()
        if niche_lower not in tags:
            tags.append(niche_lower)
        niche_parts = re.findall(r"[a-zA-Z0-9]+", niche_lower)
        for part in niche_parts:
            if len(part) > 2 and part not in tags:
                tags.append(part)

    # From state metadata if available
    if state.get("tags") and isinstance(state["tags"], list):
        for t in state["tags"]:
            if t.lower() not in tags:
                tags.append(t.lower())

    # Common YouTube suffixes
    suffixes = ["tutorial", "explained", "guide", "2026", "for beginners"]
    for suffix in suffixes:
        tag = f"{words[0] if words else topic.lower()} {suffix}"
        if tag not in tags:
            tags.append(tag)

    # YouTube allows max 500 characters total for tags, and max 30 tags
    # Trim to 30 and ensure total char count is reasonable
    tags = tags[:30]
    total_chars = sum(len(t) for t in tags)
    while total_chars > 480 and tags:
        tags.pop()
        total_chars = sum(len(t) for t in tags)

    return tags


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def upload_video(
    video_path: str,
    metadata: dict,
    thumbnail_path: str = None,
    schedule: str = None,
    playlist_id: str = None,
) -> dict:
    """
    Upload a video to YouTube with metadata and optional thumbnail.

    Args:
        video_path:     Absolute or relative path to the MP4 file.
        metadata:       Dict with title, description, tags, category, privacy.
        thumbnail_path: Path to a thumbnail image (JPG/PNG, 1280x720, <2 MB).
        schedule:       ISO 8601 publish time (for scheduled videos).
        playlist_id:    Optional playlist to add the video to.

    Returns:
        Result dict: {video_id, url, title, visibility, uploaded_at, schedule}
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    creds = get_youtube_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # Resolve metadata fields
    title = metadata.get("title", "Untitled")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    privacy = metadata.get("privacy", "private")

    # Category: accept name or ID
    category_raw = metadata.get("category", "28")
    if isinstance(category_raw, str) and category_raw.lower() in YOUTUBE_CATEGORIES:
        category_id = YOUTUBE_CATEGORIES[category_raw.lower()]
    elif isinstance(category_raw, str) and category_raw.isdigit():
        category_id = category_raw
    else:
        category_id = "28"

    # Build request body
    body = {
        "snippet": {
            "title": title[:100],  # YouTube title max 100 chars
            "description": description[:5000],  # YouTube description max 5000 chars
            "tags": tags[:50],  # YouTube allows max 50 tags
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if schedule and privacy == "private":
        body["status"]["publishAt"] = schedule

    # Print upload plan
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    cat_name = CATEGORY_ID_TO_NAME.get(category_id, category_id)
    print(f"\n{'='*60}")
    print(f"  YOUTUBE UPLOAD")
    print(f"{'='*60}")
    print(f"  File:       {video_path}")
    print(f"  Size:       {file_size_mb:.1f} MB")
    print(f"  Title:      {title}")
    print(f"  Category:   {cat_name} ({category_id})")
    print(f"  Tags:       {len(tags)} tags")
    print(f"  Privacy:    {privacy}")
    if schedule:
        print(f"  Scheduled:  {schedule}")
    print(f"{'='*60}\n")

    # Resumable upload
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=CHUNK_SIZE,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    print("Uploading video...")
    response = None
    retries = 0
    max_retries = 5

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                uploaded_mb = status.resumable_progress / (1024 * 1024)
                print(f"  Progress: {pct}% ({uploaded_mb:.1f} MB / {file_size_mb:.1f} MB)")
            retries = 0  # Reset on success
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < max_retries:
                retries += 1
                wait = 2 ** retries
                print(f"  Server error ({e.resp.status}), retrying in {wait}s... (attempt {retries}/{max_retries})")
                time.sleep(wait)
            else:
                raise

    yt_video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={yt_video_id}"
    print(f"\nUpload complete!")
    print(f"  Video ID: {yt_video_id}")
    print(f"  URL:      {video_url}")

    # --- Thumbnail ---
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"\nSetting thumbnail: {thumbnail_path}")
        try:
            youtube.thumbnails().set(
                videoId=yt_video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()
            print("  Thumbnail set successfully.")
        except HttpError as e:
            # Thumbnail upload requires a verified account; warn but don't fail
            print(f"  Warning: Thumbnail upload failed: {e}", file=sys.stderr)
            print(f"  (Your YouTube account may need to be verified for custom thumbnails)")

    # --- Playlist ---
    if playlist_id:
        print(f"\nAdding to playlist: {playlist_id}")
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": yt_video_id,
                        },
                    },
                },
            ).execute()
            print("  Added to playlist.")
        except HttpError as e:
            print(f"  Warning: Playlist add failed: {e}", file=sys.stderr)

    result = {
        "video_id": yt_video_id,
        "url": video_url,
        "title": title,
        "visibility": privacy,
        "uploaded_at": datetime.now().isoformat(),
        "schedule": schedule,
    }

    return result


# ---------------------------------------------------------------------------
# Result persistence
# ---------------------------------------------------------------------------


def save_upload_result(video_id: str, result: dict):
    """Save upload result to .tmp/{video_id}/upload_result.json and data/content_log.json."""
    # Per-video result
    video_dir = get_video_dir(video_id)
    video_dir.mkdir(parents=True, exist_ok=True)
    result_path = video_dir / "upload_result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nUpload result saved to {result_path}")

    # Also save to global uploads dir (legacy compat)
    uploads_dir = TMP_DIR / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(result.get("title", "video"))
    legacy_path = uploads_dir / f"{slug}_result.json"
    with open(legacy_path, "w") as f:
        json.dump(result, f, indent=2)

    # Append to content log
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "content_log.json"
    log = []
    if log_path.exists():
        try:
            with open(log_path) as f:
                log = json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    log.append(result)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Content log updated: {log_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Upload videos to YouTube with metadata, thumbnails, and scheduling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload with explicit metadata
  python execution/youtube_upload.py \\
      --video-id 20260303_ai_tools \\
      --title "5 AI Tools" --tags "ai,tools" --privacy private

  # Upload from metadata.json
  python execution/youtube_upload.py \\
      --video-id 20260303_ai_tools --from-metadata

  # Generate metadata only (no upload)
  python execution/youtube_upload.py \\
      --video-id 20260303_ai_tools --generate-metadata
        """,
    )

    parser.add_argument(
        "--video-id",
        required=True,
        help="Pipeline video ID (directory name under .tmp/)",
    )

    # --- Metadata source (mutually exclusive) ---
    meta_group = parser.add_mutually_exclusive_group()
    meta_group.add_argument(
        "--from-metadata",
        action="store_true",
        help="Read all metadata from .tmp/{video_id}/metadata.json",
    )
    meta_group.add_argument(
        "--generate-metadata",
        action="store_true",
        help="Generate metadata.json from state.json and script (no upload)",
    )

    # --- Explicit metadata overrides ---
    parser.add_argument("--title", help="Video title (max 100 chars)")
    parser.add_argument("--description", help="Video description")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="private",
        help="Privacy status (default: private)",
    )
    parser.add_argument("--thumbnail", help="Path to thumbnail image")
    parser.add_argument(
        "--category",
        default="28",
        help="YouTube category ID or name (default: 28 = Science & Technology)",
    )
    parser.add_argument("--schedule", help="ISO 8601 publish time for scheduled publish")
    parser.add_argument("--playlist", help="Playlist ID to add the video to")

    # Legacy compat: accept --video and --metadata directly
    parser.add_argument("--video", help="(Legacy) Direct path to video file")
    parser.add_argument("--metadata", help="(Legacy) Direct path to metadata JSON file")
    parser.add_argument("--visibility", choices=["public", "unlisted", "private"],
                        help="(Legacy) Alias for --privacy")

    args = parser.parse_args()

    video_id = args.video_id
    video_dir = get_video_dir(video_id)

    # ------------------------------------------------------------------
    # Mode: Generate metadata only
    # ------------------------------------------------------------------
    if args.generate_metadata:
        print(f"Generating metadata for {video_id}...")
        metadata = generate_metadata_from_state(video_id)
        meta_path = video_dir / "metadata.json"
        video_dir.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata written to {meta_path}")
        print(f"  Title:    {metadata['title']}")
        print(f"  Tags:     {len(metadata['tags'])} tags")
        print(f"  Category: {metadata['category']}")
        print(f"  Privacy:  {metadata['privacy']}")
        return

    # ------------------------------------------------------------------
    # Resolve video file path
    # ------------------------------------------------------------------
    if args.video:
        video_path = Path(args.video)
    else:
        # Look in standard pipeline locations
        candidates = [
            video_dir / "final.mp4",
            video_dir / "assembled.mp4",
        ]
        video_path = None
        for c in candidates:
            if c.exists():
                video_path = c
                break
        if video_path is None:
            print(f"Error: No video file found for {video_id}.", file=sys.stderr)
            print(f"  Looked in: {', '.join(str(c) for c in candidates)}", file=sys.stderr)
            print(f"  Use --video to specify a path directly.", file=sys.stderr)
            sys.exit(1)

    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Resolve metadata
    # ------------------------------------------------------------------
    if args.metadata:
        # Legacy mode: read from explicit metadata file
        with open(args.metadata) as f:
            metadata = json.load(f)
        # Apply visibility override
        if args.visibility:
            metadata["privacy"] = args.visibility
        elif "privacy" not in metadata:
            metadata["privacy"] = args.privacy

    elif args.from_metadata:
        # Read from .tmp/{video_id}/metadata.json
        meta_path = video_dir / "metadata.json"
        if not meta_path.exists():
            print(f"Error: metadata.json not found at {meta_path}", file=sys.stderr)
            print(f"  Run with --generate-metadata first, or provide metadata via CLI args.", file=sys.stderr)
            sys.exit(1)
        with open(meta_path) as f:
            metadata = json.load(f)

    else:
        # Build metadata from CLI arguments
        if not args.title:
            # Try to get title from state.json
            state_path = video_dir / "state.json"
            if state_path.exists():
                with open(state_path) as f:
                    state = json.load(f)
                title = state.get("topic", "Untitled Video")
            else:
                print("Error: --title is required (or use --from-metadata).", file=sys.stderr)
                sys.exit(1)
        else:
            title = args.title

        tags = []
        if args.tags:
            tags = [t.strip() for t in args.tags.split(",") if t.strip()]

        metadata = {
            "title": title,
            "description": args.description or "",
            "tags": tags,
            "category": args.category,
            "privacy": args.privacy,
        }

    # Apply CLI overrides on top of loaded metadata
    if args.title:
        metadata["title"] = args.title
    if args.description:
        metadata["description"] = args.description
    if args.tags:
        metadata["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.category and args.category != "28":
        metadata["category"] = args.category
    if args.privacy and args.privacy != "private":
        metadata["privacy"] = args.privacy
    if args.visibility:
        metadata["privacy"] = args.visibility

    # ------------------------------------------------------------------
    # Resolve thumbnail
    # ------------------------------------------------------------------
    thumbnail_path = None
    if args.thumbnail:
        thumbnail_path = args.thumbnail
    elif metadata.get("thumbnail"):
        # Thumbnail name relative to video dir
        thumb = video_dir / metadata["thumbnail"]
        if thumb.exists():
            thumbnail_path = str(thumb)
    else:
        # Auto-detect in video dir
        for name in ("thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg"):
            thumb = video_dir / name
            if thumb.exists():
                thumbnail_path = str(thumb)
                break

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    result = upload_video(
        video_path=str(video_path),
        metadata=metadata,
        thumbnail_path=thumbnail_path,
        schedule=args.schedule,
        playlist_id=args.playlist,
    )

    # Add pipeline video_id to result
    result["pipeline_video_id"] = video_id

    # Save results
    save_upload_result(video_id, result)

    # Update state.json if it exists
    state_path = video_dir / "state.json"
    if state_path.exists():
        try:
            with open(state_path) as f:
                state = json.load(f)
            state["youtube_video_id"] = result["video_id"]
            state["youtube_url"] = result["url"]
            state["uploaded_at"] = result["uploaded_at"]
            state["status"] = "published" if metadata.get("privacy") == "public" else "uploaded"
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)
            print(f"State updated: {state_path}")
        except (json.JSONDecodeError, ValueError, OSError) as e:
            print(f"Warning: Could not update state.json: {e}", file=sys.stderr)

    print(f"\nDone! Video URL: {result['url']}")


if __name__ == "__main__":
    main()
