#!/usr/bin/env python3
"""
Telegram Bot for Pipeline Approvals and Notifications.

Provides approval gates, pipeline status, and notifications
via Telegram bot interface.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_APPROVER_CHAT_ID") or os.getenv("TELEGRAM_GROUP_ID")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text: str, chat_id: str = None, parse_mode: str = "Markdown") -> dict:
    """Send a message via Telegram bot."""
    cid = chat_id or CHAT_ID
    if not BOT_TOKEN or not cid:
        print("Warning: TELEGRAM_BOT_TOKEN or chat ID not configured")
        return {}

    resp = httpx.post(
        f"{API_BASE}/sendMessage",
        json={
            "chat_id": cid,
            "text": text,
            "parse_mode": parse_mode,
        },
        timeout=10,
    )
    return resp.json()


def send_document(file_path: str, caption: str = "", chat_id: str = None) -> dict:
    """Send a file via Telegram bot."""
    cid = chat_id or CHAT_ID
    if not BOT_TOKEN or not cid:
        return {}

    with open(file_path, "rb") as f:
        resp = httpx.post(
            f"{API_BASE}/sendDocument",
            data={"chat_id": cid, "caption": caption},
            files={"document": f},
            timeout=30,
        )
    return resp.json()


def send_video(file_path: str, caption: str = "", chat_id: str = None) -> dict:
    """Send a video via Telegram bot (max 50MB)."""
    cid = chat_id or CHAT_ID
    if not BOT_TOKEN or not cid:
        return {}

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 50:
        return send_message(
            f"Video too large for Telegram ({size_mb:.0f}MB). "
            f"File: `{file_path}`",
            cid,
        )

    with open(file_path, "rb") as f:
        resp = httpx.post(
            f"{API_BASE}/sendVideo",
            data={"chat_id": cid, "caption": caption},
            files={"video": f},
            timeout=120,
        )
    return resp.json()


def notify_stage(video_id: str, stage: str, message: str = ""):
    """Send a pipeline stage notification."""
    text = f"*Pipeline Update*\n`{video_id}`: {stage}"
    if message:
        text += f"\n{message}"
    send_message(text)


def notify_gate1(video_id: str):
    """Send Gate 1 notification with script preview."""
    video_dir = TMP_DIR / video_id
    state_path = video_dir / "state.json"
    script_path = video_dir / "script.md"

    if not state_path.exists():
        print(f"State file not found for {video_id}")
        return

    with open(state_path) as f:
        state = json.load(f)

    topic = state.get("topic", "Unknown")

    # Read script preview
    preview = ""
    if script_path.exists():
        with open(script_path) as f:
            content = f.read()
        preview = content[:2000]
        if len(content) > 2000:
            preview += "\n..."

    text = (
        f"*Script Ready for Review*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Video:* `{video_id}`\n"
        f"*Topic:* {topic}\n\n"
        f"*Script Preview:*\n"
        f"```\n{preview[:1500]}\n```\n\n"
        f"To approve: create `{video_dir}/gate_response.json` with:\n"
        f'`{{"decision": "approved"}}`\n\n'
        f"To reject:\n"
        f'`{{"decision": "rejected", "reason": "your feedback"}}`'
    )

    send_message(text)

    # Also send full script as document
    if script_path.exists():
        send_document(str(script_path), caption=f"Full script: {topic}")


def notify_gate2(video_id: str):
    """Send Gate 2 notification with final video."""
    video_dir = TMP_DIR / video_id
    state_path = video_dir / "state.json"
    final_path = video_dir / "final.mp4"

    if not state_path.exists():
        return

    with open(state_path) as f:
        state = json.load(f)

    topic = state.get("topic", "Unknown")

    if final_path.exists():
        size_mb = os.path.getsize(final_path) / (1024 * 1024)

        # Get duration
        import subprocess
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(final_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.stdout.strip() else 0

        text = (
            f"*Video Ready for Review*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*Video:* `{video_id}`\n"
            f"*Topic:* {topic}\n"
            f"*Duration:* {duration/60:.1f} min\n"
            f"*Size:* {size_mb:.0f} MB\n\n"
            f"To approve: create `{video_dir}/gate_response.json` with:\n"
            f'`{{"decision": "approved"}}`'
        )

        send_message(text)

        # Try to send video directly
        send_video(str(final_path), caption=f"Final video: {topic}")
    else:
        send_message(f"*Gate 2:* Video file not found for `{video_id}`")


def send_status():
    """Send pipeline status summary."""
    videos = []
    if TMP_DIR.exists():
        for d in sorted(TMP_DIR.iterdir()):
            state_file = d / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    videos.append(json.load(f))

    if not videos:
        send_message("*Pipeline Status:* No videos in pipeline.")
        return

    active = [v for v in videos if v.get("status") not in ("published", "failed")]
    pending = [v for v in active if "gate" in v.get("status", "")]
    published = [v for v in videos if v.get("status") == "published"]
    failed = [v for v in videos if v.get("status") == "failed"]

    lines = ["*Pipeline Status*\n━━━━━━━━━━━━━━━━━━━━━━━━"]

    if active:
        lines.append(f"\n*Active ({len(active)}):*")
        for v in active:
            lines.append(f"  `{v['video_id']}`: {v['status']}")

    if pending:
        lines.append(f"\n*Awaiting Approval ({len(pending)}):*")
        for v in pending:
            lines.append(f"  `{v['video_id']}`: {v['status']}")

    if published:
        lines.append(f"\n*Published: {len(published)}*")

    if failed:
        lines.append(f"\n*Failed: {len(failed)}*")
        for v in failed:
            lines.append(f"  `{v['video_id']}`: {v.get('error', '?')}")

    send_message("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Telegram pipeline bot")
    parser.add_argument("--notify-gate1", metavar="VIDEO_ID",
                        help="Send Gate 1 (script review) notification")
    parser.add_argument("--notify-gate2", metavar="VIDEO_ID",
                        help="Send Gate 2 (video review) notification")
    parser.add_argument("--notify-stage", nargs=2, metavar=("VIDEO_ID", "STAGE"),
                        help="Send stage transition notification")
    parser.add_argument("--status", action="store_true",
                        help="Send pipeline status summary")
    parser.add_argument("--message", help="Send a custom message")

    args = parser.parse_args()

    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    if not CHAT_ID:
        print("Error: TELEGRAM_APPROVER_CHAT_ID or TELEGRAM_GROUP_ID not set",
              file=sys.stderr)
        sys.exit(1)

    if args.notify_gate1:
        notify_gate1(args.notify_gate1)
    elif args.notify_gate2:
        notify_gate2(args.notify_gate2)
    elif args.notify_stage:
        notify_stage(args.notify_stage[0], args.notify_stage[1])
    elif args.status:
        send_status()
    elif args.message:
        send_message(args.message)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
