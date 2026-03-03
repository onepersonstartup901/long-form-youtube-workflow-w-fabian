#!/usr/bin/env python3
"""
Video Assembly.

Builds Remotion props JSON from parsed script, voice timestamps, visuals manifest,
and captions, then triggers Remotion render to produce the final video.
"""

import os
import sys
import json
import subprocess
import argparse
import shutil
import time
from pathlib import Path

# Path to Remotion project
REMOTION_DIR = Path(__file__).parent / "remotion_video"


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError(f"ffprobe failed: {result.stderr[:200]}")
        return float(result.stdout.strip())
    except FileNotFoundError:
        print("  Error: ffprobe not found. Install ffmpeg.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"  Error getting audio duration: {e}", file=sys.stderr)
        sys.exit(1)


def build_assembly_props(
    video_id: str,
    tmp_dir: str,
    title: str = "",
    channel_name: str = "AI Tech",
    fps: int = 30,
) -> dict:
    """
    Build Remotion assembly props from pipeline intermediate files.

    Expects these files in tmp_dir:
      - narration.mp3 (from generate_voice.py)
      - word_timestamps.json (from generate_voice.py)
      - visuals_manifest.json (from gather_visuals.py)
      - captions.json (from generate_captions.py)
      - parsed_script.json (from parse_script.py)

    Returns:
        Assembly props dict ready for Remotion
    """
    # Load all intermediate files
    parsed_path = os.path.join(tmp_dir, "parsed_script.json")
    audio_path = os.path.join(tmp_dir, "narration.mp3")
    timestamps_path = os.path.join(tmp_dir, "word_timestamps.json")
    manifest_path = os.path.join(tmp_dir, "visuals_manifest.json")
    captions_path = os.path.join(tmp_dir, "captions.json")

    with open(parsed_path) as f:
        parsed = json.load(f)
    with open(timestamps_path) as f:
        word_timestamps = json.load(f)
    with open(manifest_path) as f:
        visuals_manifest = json.load(f)
    with open(captions_path) as f:
        remotion_captions = json.load(f)

    # Get audio duration
    audio_duration = get_audio_duration(audio_path)
    total_frames = int(audio_duration * fps)

    # Copy assets into Remotion public directory for staticFile()
    public_dir = REMOTION_DIR / "public" / video_id
    public_dir.mkdir(parents=True, exist_ok=True)

    # Copy narration audio
    audio_dest = f"{video_id}/narration.mp3"
    shutil.copy2(audio_path, public_dir / "narration.mp3")

    # Copy visual assets
    visuals_dir = public_dir / "visuals"
    visuals_dir.mkdir(exist_ok=True)

    for entry in visuals_manifest:
        if entry.get("file_path") and os.path.exists(entry["file_path"]):
            filename = os.path.basename(entry["file_path"])
            dest = visuals_dir / filename
            shutil.copy2(entry["file_path"], dest)
            entry["remotion_src"] = f"{video_id}/visuals/{filename}"

    # Build segments from parsed script blocks
    blocks = parsed.get("blocks", [])
    segments = []

    # Intro segment (3 seconds)
    intro_frames = 3 * fps
    segments.append({
        "type": "intro",
        "startFrame": 0,
        "durationInFrames": intro_frames,
        "title": title or parsed.get("title", "Untitled"),
    })

    # Build narration segments from blocks
    # Each block maps to a visual + its portion of captions
    current_frame = intro_frames

    # Calculate timing per block from word timestamps
    block_timings = _calculate_block_timings(word_timestamps, blocks, fps)

    animations = ["ken_burns_in", "ken_burns_out", "pan_left", "pan_right", "static"]

    prev_section = None
    for i, block in enumerate(blocks):
        block_idx = block.get("index", i)
        timing = block_timings.get(block_idx, {})

        start_time = timing.get("start", 0)
        end_time = timing.get("end", start_time + 5)
        duration_frames = int((end_time - start_time) * fps)

        if duration_frames <= 0:
            continue

        # Find visual for this block
        visual_entry = next(
            (v for v in visuals_manifest if v.get("block_index") == block_idx),
            None,
        )

        visual_src = ""
        visual_type = "image"
        if visual_entry and visual_entry.get("remotion_src"):
            visual_src = visual_entry["remotion_src"]
            visual_type = visual_entry.get("file_type", "image")

        # Get captions for this block's time range
        block_start_frame = int(start_time * fps)
        block_end_frame = int(end_time * fps)
        block_captions = [
            c for c in remotion_captions
            if c["startFrame"] >= block_start_frame and c["endFrame"] <= block_end_frame
        ]

        # Adjust caption frames relative to segment start
        adjusted_captions = []
        for cap in block_captions:
            adjusted = {
                **cap,
                "startFrame": cap["startFrame"] - block_start_frame,
                "endFrame": cap["endFrame"] - block_start_frame,
                "words": [
                    {
                        **w,
                        "startFrame": w["startFrame"] - block_start_frame,
                        "endFrame": w["endFrame"] - block_start_frame,
                    }
                    for w in cap.get("words", [])
                ],
            }
            adjusted_captions.append(adjusted)

        # Check for section change
        section_name = block.get("section_name", "")
        section_title = None
        if section_name and section_name != prev_section:
            section_title = section_name.split("(")[0].strip()
            prev_section = section_name

        segment = {
            "type": "narration",
            "startFrame": current_frame,
            "durationInFrames": duration_frames,
            "visual": {
                "type": visual_type,
                "src": visual_src,
                "animation": animations[i % len(animations)],
            },
            "captions": adjusted_captions,
        }

        if section_title:
            segment["sectionTitle"] = section_title

        segments.append(segment)
        current_frame += duration_frames

    # Outro segment (5 seconds)
    outro_frames = 5 * fps
    segments.append({
        "type": "outro",
        "startFrame": current_frame,
        "durationInFrames": outro_frames,
        "channelName": channel_name,
        "cta": "Subscribe & Hit the Bell",
    })

    total_frames = current_frame + outro_frames

    # Default style
    style = {
        "backgroundColor": "#0a0a0a",
        "captionFont": "Inter, system-ui, sans-serif",
        "captionColor": "#ffffff",
        "captionHighlightColor": "#00ff88",
        "captionPosition": "bottom",
        "captionMaxWords": 4,
        "accentColor": "#3b82f6",
        "captionFontSize": 52,
        "captionStrokeColor": "#000000",
        "captionStrokeWidth": 4,
    }

    props = {
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "totalDurationInFrames": total_frames,
        "audioSrc": audio_dest,
        "segments": segments,
        "style": style,
    }

    return props


def _calculate_block_timings(
    word_timestamps: list[dict], blocks: list[dict], fps: int
) -> dict:
    """Calculate start/end times for each block from word timestamps."""
    timings = {}

    # Group words by block_index
    block_words: dict[int, list[dict]] = {}
    for wt in word_timestamps:
        bi = wt.get("block_index", 0)
        block_words.setdefault(bi, []).append(wt)

    for block in blocks:
        idx = block.get("index", 0)
        words = block_words.get(idx, [])

        if words:
            timings[idx] = {
                "start": words[0]["start"],
                "end": words[-1]["end"],
            }
        else:
            # Estimate from narration word count
            narration = block.get("narration", "")
            word_count = len(narration.split())
            duration = max(2.0, word_count / 2.5)  # ~150 wpm

            prev_end = 0
            if timings:
                prev_end = max(t["end"] for t in timings.values())

            timings[idx] = {
                "start": prev_end,
                "end": prev_end + duration,
            }

    return timings


def render_video(
    props: dict,
    output_path: str,
    draft: bool = False,
    concurrency: int = 4,
) -> bool:
    """
    Render video using Remotion.

    Args:
        props: Assembly props dict
        output_path: Output video file path
        draft: If True, render at lower quality for preview
        concurrency: Number of concurrent rendering threads

    Returns:
        True if render succeeded
    """
    # Write props to video-scoped temp file (prevents race conditions)
    props_path = REMOTION_DIR / f"props_{os.path.basename(output_path).replace('.mp4','')}.json"
    with open(props_path, "w") as f:
        json.dump(props, f)

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "FullVideo",
        os.path.abspath(output_path),
        "--props", str(props_path),
        "--concurrency", str(concurrency),
        "--log", "error",
    ]

    if draft:
        cmd.extend(["--quality", "50", "--scale", "0.5"])
    else:
        cmd.extend([
            "--codec", "h264",
            "--audio-bitrate", "192K",
            "--video-bitrate", "10M",
        ])

    print(f"Rendering video...")
    print(f"  Output: {output_path}")
    print(f"  Duration: {props['totalDurationInFrames'] / props['fps']:.1f}s")
    print(f"  {'Draft mode' if draft else 'Full quality'}")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Render failed: {result.stderr[:1000]}")
        return False

    elapsed = time.time() - start_time
    print(f"  Rendered in {elapsed:.1f}s")

    # Clean up props file
    if props_path.exists():
        props_path.unlink()

    return True


def assemble_video(
    video_id: str,
    tmp_dir: str,
    output_path: str = None,
    draft: bool = False,
    title: str = "",
    channel_name: str = "AI Tech",
) -> str:
    """
    Full assembly pipeline: build props + render.

    Args:
        video_id: Video identifier
        tmp_dir: Directory with intermediate files
        output_path: Override output path
        draft: Render in draft quality
        title: Video title
        channel_name: Channel name for outro

    Returns:
        Path to rendered video
    """
    if not output_path:
        output_path = os.path.join(tmp_dir, "assembled.mp4")

    print(f"Assembling video: {video_id}")
    print(f"  Source: {tmp_dir}")

    # Build props
    props = build_assembly_props(video_id, tmp_dir, title, channel_name)

    # Save props for debugging
    props_debug_path = os.path.join(tmp_dir, "assembly_props.json")
    with open(props_debug_path, "w") as f:
        json.dump(props, f, indent=2)
    print(f"  Props saved to {props_debug_path}")
    print(f"  Segments: {len(props['segments'])}")
    print(f"  Total frames: {props['totalDurationInFrames']}")

    # Render
    success = render_video(props, output_path, draft=draft)

    if success:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Output: {output_path} ({size_mb:.1f} MB)")
        return output_path
    else:
        print("  Assembly failed!")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Assemble video from pipeline outputs")
    parser.add_argument("--video-id", required=True, help="Video identifier")
    parser.add_argument("--tmp-dir", required=True, help="Directory with intermediate files")
    parser.add_argument("--output", "-o", help="Output video path")
    parser.add_argument("--draft", action="store_true", help="Render draft quality")
    parser.add_argument("--title", default="", help="Video title")
    parser.add_argument("--channel", default="AI Tech", help="Channel name")

    args = parser.parse_args()

    result = assemble_video(
        video_id=args.video_id,
        tmp_dir=args.tmp_dir,
        output_path=args.output,
        draft=args.draft,
        title=args.title,
        channel_name=args.channel,
    )

    if result:
        print(f"\nDone: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
