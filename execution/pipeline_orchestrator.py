#!/usr/bin/env python3
"""
Pipeline Orchestrator.

State machine that advances videos through production stages.
Manages the full lifecycle from topic to published YouTube video.
"""

import os
import sys
import json
import subprocess
import argparse
import time
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
EXECUTION_DIR = Path(__file__).parent
TMP_DIR = PROJECT_ROOT / ".tmp"


STAGE_ORDER = [
    "research",
    "scripting",
    "gate1_pending",
    "voice",
    "visuals",
    "captions",
    "assembly",
    "post_production",
    "gate2_pending",
    "metadata",
    "uploading",
    "published",
]


def make_video_id(topic: str) -> str:
    """Generate video ID from topic and date."""
    date_str = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40].strip('_')
    return f"{date_str}_{slug}"


def get_video_dir(video_id: str) -> Path:
    """Get the working directory for a video."""
    d = TMP_DIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_state(video_id: str) -> dict:
    """Load video state from its state file."""
    state_path = get_video_dir(video_id) / "state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}


def save_state(video_id: str, state: dict):
    """Save video state."""
    state_path = get_video_dir(video_id) / "state.json"
    state["updated_at"] = datetime.now().isoformat()
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def run_python(script: str, args: list[str], cwd: str = None) -> tuple[bool, str]:
    """Run a Python execution script."""
    cmd = [sys.executable, str(EXECUTION_DIR / script)] + args
    print(f"  Running: {script} {' '.join(args[:4])}...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or str(PROJECT_ROOT),
        timeout=600,  # 10 min timeout
    )

    if result.returncode != 0:
        print(f"  FAILED: {result.stderr[:500]}")
        return False, result.stderr

    if result.stdout:
        # Print last few lines
        lines = result.stdout.strip().split("\n")
        for line in lines[-5:]:
            print(f"    {line}")

    return True, result.stdout


def stage_research(video_id: str, state: dict) -> bool:
    """Stage: Research topic and generate outline."""
    topic = state["topic"]
    video_dir = get_video_dir(video_id)
    outline_path = video_dir / "outline.md"

    success, output = run_python("topic_research.py", [
        "--outline", topic,
        "--niche", state.get("niche", "tech/AI"),
        "--style", "educational",
    ])

    if success:
        # topic_research.py saves to .tmp/outlines/, move to our dir
        slug = topic.lower().replace(" ", "_")[:40]
        src = TMP_DIR / "outlines" / f"{slug}.md"
        if src.exists():
            import shutil
            shutil.move(str(src), str(outline_path))
        elif not outline_path.exists():
            # Save output as outline
            with open(outline_path, "w") as f:
                f.write(output)

    return success


def stage_scripting(video_id: str, state: dict) -> bool:
    """Stage: Generate faceless narration script."""
    topic = state["topic"]
    video_dir = get_video_dir(video_id)

    outline_path = video_dir / "outline.md"
    outline_args = ["--outline", str(outline_path)] if outline_path.exists() else []

    success, output = run_python("generate_script.py", [
        "--topic", topic,
        "--style", "faceless",
        "--length", str(state.get("target_length", 12)),
    ] + outline_args)

    if success:
        # Move script to video directory
        slug = topic.lower().replace(" ", "_")[:40]
        src = TMP_DIR / "scripts" / f"{slug}_v1.md"
        script_path = video_dir / "script.md"
        if src.exists():
            import shutil
            shutil.move(str(src), str(script_path))

        # Parse the script
        if script_path.exists():
            ok, _ = run_python("parse_script.py", [
                str(script_path),
                "-o", str(video_dir / "parsed_script.json"),
                "--validate",
            ])
            return ok

    return success


def stage_voice(video_id: str, state: dict) -> bool:
    """Stage: Generate TTS narration."""
    video_dir = get_video_dir(video_id)
    parsed_path = video_dir / "parsed_script.json"

    if not parsed_path.exists():
        print("  Error: parsed_script.json not found")
        return False

    success, _ = run_python("generate_voice.py", [
        str(parsed_path),
        "-o", str(video_dir),
    ])

    return success


def stage_visuals(video_id: str, state: dict) -> bool:
    """Stage: Gather visual assets."""
    video_dir = get_video_dir(video_id)
    parsed_path = video_dir / "parsed_script.json"

    if not parsed_path.exists():
        print("  Error: parsed_script.json not found")
        return False

    args = [str(parsed_path), "-o", str(video_dir)]
    if state.get("skip_ai_images"):
        args.append("--skip-ai")

    success, _ = run_python("gather_visuals.py", args)
    return success


def stage_captions(video_id: str, state: dict) -> bool:
    """Stage: Generate captions."""
    video_dir = get_video_dir(video_id)
    timestamps_path = video_dir / "word_timestamps.json"
    parsed_path = video_dir / "parsed_script.json"

    if not timestamps_path.exists():
        print("  Error: word_timestamps.json not found")
        return False

    args = [
        str(timestamps_path),
        "-o", str(video_dir),
        "--script-json", str(parsed_path),
    ]

    success, _ = run_python("generate_captions.py", args)
    return success


def stage_assembly(video_id: str, state: dict) -> bool:
    """Stage: Assemble video with Remotion."""
    video_dir = get_video_dir(video_id)

    success, _ = run_python("assemble_video.py", [
        "--video-id", video_id,
        "--tmp-dir", str(video_dir),
        "--title", state.get("topic", ""),
        "--channel", state.get("channel_name", "AI Tech"),
    ] + (["--draft"] if state.get("draft") else []))

    return success


def stage_post_production(video_id: str, state: dict) -> bool:
    """Stage: Audio enhancement and final export."""
    video_dir = get_video_dir(video_id)
    assembled = video_dir / "assembled.mp4"
    final = video_dir / "final.mp4"

    if not assembled.exists():
        print("  Error: assembled.mp4 not found")
        return False

    # Apply audio enhancement
    success, _ = run_python("enhance_audio.py", [
        str(assembled),
        str(final),
        "--preset", "voice",
    ])

    return success


def stage_metadata(video_id: str, state: dict) -> bool:
    """Stage: Generate YouTube metadata."""
    video_dir = get_video_dir(video_id)
    script_path = video_dir / "script.md"

    args = ["--niche", state.get("niche", "tech/AI")]
    if script_path.exists():
        args.extend(["--script", str(script_path)])
    else:
        args.extend(["--title", state.get("topic", "")])

    success, _ = run_python("generate_metadata.py", args)

    if success:
        # Move metadata to video dir
        slug = state.get("topic", "video").lower().replace(" ", "_")[:40]
        meta_src = TMP_DIR / "metadata" / f"{slug}.json"
        if meta_src.exists():
            import shutil
            shutil.move(str(meta_src), str(video_dir / "metadata.json"))

    return success


def stage_uploading(video_id: str, state: dict) -> bool:
    """Stage: Upload to YouTube."""
    video_dir = get_video_dir(video_id)
    video_path = video_dir / "final.mp4"
    metadata_path = video_dir / "metadata.json"

    if not video_path.exists():
        print("  Error: final.mp4 not found")
        return False

    if not metadata_path.exists():
        print("  Error: metadata.json not found")
        return False

    args = [
        "--video", str(video_path),
        "--metadata", str(metadata_path),
        "--visibility", state.get("visibility", "private"),
    ]

    thumbnail_path = video_dir / "thumbnail.png"
    if thumbnail_path.exists():
        args.extend(["--thumbnail", str(thumbnail_path)])

    success, _ = run_python("youtube_upload.py", args)
    return success


# Stage handler mapping
STAGE_HANDLERS = {
    "research": stage_research,
    "scripting": stage_scripting,
    "voice": stage_voice,
    "visuals": stage_visuals,
    "captions": stage_captions,
    "assembly": stage_assembly,
    "post_production": stage_post_production,
    "metadata": stage_metadata,
    "uploading": stage_uploading,
}


def advance_video(video_id: str, skip_gates: bool = False) -> str:
    """
    Advance a video to its next stage.

    Returns:
        New status string
    """
    state = load_state(video_id)
    current = state.get("status", "research")

    print(f"\n{'='*50}")
    print(f"Video: {video_id}")
    print(f"Status: {current}")
    print(f"Topic: {state.get('topic', '?')}")

    # Handle gate stages
    if current in ("gate1_pending", "gate2_pending"):
        if skip_gates:
            print(f"  Skipping gate (--skip-gates)")
        else:
            # Check for gate response file
            video_dir = get_video_dir(video_id)
            gate_response = video_dir / "gate_response.json"

            if gate_response.exists():
                with open(gate_response) as f:
                    response = json.load(f)

                if response.get("decision") == "approved":
                    print(f"  Gate approved!")
                    gate_response.unlink()
                elif response.get("decision") == "rejected":
                    reason = response.get("reason", "No reason given")
                    print(f"  Gate rejected: {reason}")
                    # Roll back
                    rollback = "scripting" if current == "gate1_pending" else "assembly"
                    state["status"] = rollback
                    state["feedback"] = reason
                    save_state(video_id, state)
                    gate_response.unlink()
                    return rollback
                else:
                    print(f"  Waiting for gate approval...")
                    return current
            else:
                print(f"  Waiting for gate approval...")
                print(f"  (Use --skip-gates to bypass, or create {gate_response})")
                return current

    # Find next stage
    if current not in STAGE_ORDER:
        print(f"  Unknown stage: {current}")
        return current

    idx = STAGE_ORDER.index(current)

    # Execute current stage if it has a handler
    handler = STAGE_HANDLERS.get(current)
    if handler:
        print(f"  Executing: {current}")
        start = time.time()
        success = handler(video_id, state)
        elapsed = time.time() - start

        if not success:
            state["status"] = "failed"
            state["error"] = f"Failed at {current}"
            state["failed_at"] = datetime.now().isoformat()
            save_state(video_id, state)
            print(f"  FAILED at {current} ({elapsed:.1f}s)")
            return "failed"

        print(f"  Completed in {elapsed:.1f}s")

    # Move to next stage
    if idx + 1 < len(STAGE_ORDER):
        next_stage = STAGE_ORDER[idx + 1]
        state["status"] = next_stage
        state[f"{current}_completed_at"] = datetime.now().isoformat()
        save_state(video_id, state)
        print(f"  Advanced to: {next_stage}")
        return next_stage
    else:
        state["status"] = "published"
        state["published_at"] = datetime.now().isoformat()
        save_state(video_id, state)
        print(f"  PUBLISHED!")
        return "published"


def run_all(video_id: str, skip_gates: bool = False) -> str:
    """Run all stages sequentially until complete or blocked."""
    state = load_state(video_id)
    status = state.get("status", "research")

    while status not in ("published", "failed"):
        if status in ("gate1_pending", "gate2_pending") and not skip_gates:
            print(f"\nBlocked at {status}. Waiting for approval.")
            break

        new_status = advance_video(video_id, skip_gates)
        if new_status == status:
            break  # No progress
        status = new_status

    return status


def new_video(topic: str, niche: str = "tech/AI", length: int = 12) -> str:
    """Create a new video in the pipeline."""
    video_id = make_video_id(topic)
    video_dir = get_video_dir(video_id)

    state = {
        "video_id": video_id,
        "topic": topic,
        "niche": niche,
        "target_length": length,
        "status": "research",
        "created_at": datetime.now().isoformat(),
        "channel_name": "AI Tech",
        "visibility": "private",
    }

    save_state(video_id, state)
    print(f"Created video: {video_id}")
    print(f"  Topic: {topic}")
    print(f"  Directory: {video_dir}")

    return video_id


def list_videos() -> list[dict]:
    """List all videos in the pipeline."""
    videos = []
    if TMP_DIR.exists():
        for d in sorted(TMP_DIR.iterdir()):
            state_file = d / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                videos.append(state)

    return videos


def main():
    parser = argparse.ArgumentParser(description="YouTube Video Pipeline Orchestrator")
    parser.add_argument("--new", metavar="TOPIC", help="Create new video from topic")
    parser.add_argument("--video", metavar="ID", help="Video ID to operate on")
    parser.add_argument("--advance", action="store_true", help="Advance video one stage")
    parser.add_argument("--run-all", action="store_true", help="Run all stages")
    parser.add_argument("--skip-gates", action="store_true",
                        help="Skip approval gates (for testing)")
    parser.add_argument("--list", action="store_true", help="List all videos")
    parser.add_argument("--retry", action="store_true", help="Retry failed stage")
    parser.add_argument("--niche", default="tech/AI", help="Content niche")
    parser.add_argument("--length", type=int, default=12, help="Target length in minutes")

    args = parser.parse_args()

    if args.list:
        videos = list_videos()
        if not videos:
            print("No videos in pipeline.")
            return
        print(f"\n{'ID':<35} {'Status':<20} {'Topic':<40}")
        print("-" * 95)
        for v in videos:
            vid = v.get("video_id", "?")
            status = v.get("status", "?")
            topic = v.get("topic", "?")[:40]
            print(f"{vid:<35} {status:<20} {topic}")
        return

    if args.new:
        video_id = new_video(args.new, args.niche, args.length)
        if args.run_all:
            run_all(video_id, args.skip_gates)
        return

    if args.video:
        if args.retry:
            state = load_state(args.video)
            if state.get("status") == "failed":
                # Find the last completed stage and resume from the failed one
                error = state.get("error", "")
                failed_stage = error.replace("Failed at ", "")
                if failed_stage in STAGE_ORDER:
                    state["status"] = failed_stage
                    save_state(args.video, state)
                    print(f"Retrying from: {failed_stage}")
                else:
                    print(f"Cannot determine failed stage from error: {error}")
                    return

        if args.run_all:
            run_all(args.video, args.skip_gates)
        elif args.advance:
            advance_video(args.video, args.skip_gates)
        else:
            state = load_state(args.video)
            print(json.dumps(state, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
