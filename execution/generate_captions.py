#!/usr/bin/env python3
"""
Caption Generator.

Produces SRT subtitle files and Remotion-compatible caption JSON
from word-level timestamps.
"""

import json
import argparse
import sys
import os


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def group_words(
    word_timestamps: list[dict],
    max_words: int = 4,
    max_duration: float = 3.0,
) -> list[dict]:
    """
    Group words into caption groups for display.

    Args:
        word_timestamps: List of {word, start, end, ...} dicts
        max_words: Maximum words per caption group
        max_duration: Maximum duration per group in seconds

    Returns:
        List of caption groups with start, end, words, text
    """
    groups = []
    current_words = []
    group_start = None

    for wt in word_timestamps:
        word = wt["word"].strip()
        if not word:
            continue

        if group_start is None:
            group_start = wt["start"]

        current_words.append(wt)

        # Check if we should close this group
        duration = wt["end"] - group_start
        at_limit = len(current_words) >= max_words or duration >= max_duration

        # Also break on sentence-ending punctuation
        ends_sentence = word.rstrip().endswith((".","!","?",":"))

        if at_limit or ends_sentence:
            groups.append({
                "start": group_start,
                "end": wt["end"],
                "words": [w["word"] for w in current_words],
                "text": " ".join(w["word"] for w in current_words),
                "word_timings": [
                    {"word": w["word"], "start": w["start"], "end": w["end"]}
                    for w in current_words
                ],
            })
            current_words = []
            group_start = None

    # Flush remaining words
    if current_words:
        groups.append({
            "start": group_start,
            "end": current_words[-1]["end"],
            "words": [w["word"] for w in current_words],
            "text": " ".join(w["word"] for w in current_words),
            "word_timings": [
                {"word": w["word"], "start": w["start"], "end": w["end"]}
                for w in current_words
            ],
        })

    return groups


def generate_srt(groups: list[dict]) -> str:
    """Generate SRT subtitle content from caption groups."""
    lines = []
    for i, group in enumerate(groups, 1):
        start = format_srt_time(group["start"])
        end = format_srt_time(group["end"])
        text = group["text"]
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def generate_remotion_captions(
    groups: list[dict],
    fps: int = 30,
    emphasis_words: list[str] = None,
) -> list[dict]:
    """
    Generate Remotion-compatible caption data.

    Each group becomes a Remotion caption entry with frame-based timing.

    Args:
        groups: Caption groups from group_words()
        fps: Video frame rate
        emphasis_words: Words to highlight (from CAPTION_EMPHASIS)

    Returns:
        List of caption entries for Remotion props
    """
    emphasis_set = set(w.lower() for w in (emphasis_words or []))

    captions = []
    for group in groups:
        start_frame = int(group["start"] * fps)
        end_frame = int(group["end"] * fps)

        words = []
        for wt in group["word_timings"]:
            word_start = int(wt["start"] * fps)
            word_end = int(wt["end"] * fps)
            is_highlight = wt["word"].lower().strip(".,!?;:") in emphasis_set

            words.append({
                "word": wt["word"],
                "startFrame": word_start,
                "endFrame": word_end,
                "highlight": is_highlight,
            })

        captions.append({
            "startFrame": start_frame,
            "endFrame": end_frame,
            "text": group["text"],
            "words": words,
        })

    return captions


def generate_captions(
    word_timestamps: list[dict],
    output_dir: str,
    max_words_per_group: int = 4,
    fps: int = 30,
    emphasis_words: list[str] = None,
) -> tuple[str, str]:
    """
    Generate both SRT and Remotion caption files.

    Args:
        word_timestamps: Word-level timestamps from TTS
        output_dir: Output directory
        max_words_per_group: Words per caption line
        fps: Video frame rate
        emphasis_words: Words to highlight

    Returns:
        Tuple of (srt_path, captions_json_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Group words
    groups = group_words(word_timestamps, max_words=max_words_per_group)
    print(f"  Created {len(groups)} caption groups from {len(word_timestamps)} words")

    # Generate SRT
    srt_content = generate_srt(groups)
    srt_path = os.path.join(output_dir, "captions.srt")
    with open(srt_path, "w") as f:
        f.write(srt_content)
    print(f"  SRT: {srt_path}")

    # Generate Remotion JSON
    remotion_captions = generate_remotion_captions(groups, fps, emphasis_words)
    captions_json_path = os.path.join(output_dir, "captions.json")
    with open(captions_json_path, "w") as f:
        json.dump(remotion_captions, f, indent=2)
    print(f"  Remotion JSON: {captions_json_path}")

    return srt_path, captions_json_path


def main():
    parser = argparse.ArgumentParser(description="Generate captions from word timestamps")
    parser.add_argument("timestamps_json", help="Path to word_timestamps.json")
    parser.add_argument("--output-dir", "-o", default=".tmp/captions",
                        help="Output directory")
    parser.add_argument("--max-words", type=int, default=4,
                        help="Max words per caption group (default: 4)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Video frame rate (default: 30)")
    parser.add_argument("--emphasis", nargs="*",
                        help="Words to highlight in captions")
    parser.add_argument("--script-json",
                        help="Path to parsed script JSON (for CAPTION_EMPHASIS)")

    args = parser.parse_args()

    # Load timestamps
    with open(args.timestamps_json, "r") as f:
        word_timestamps = json.load(f)

    # Collect emphasis words
    emphasis_words = list(args.emphasis or [])

    # Also collect from script blocks if provided
    if args.script_json:
        with open(args.script_json, "r") as f:
            parsed = json.load(f)
        for block in parsed.get("blocks", []):
            emp = block.get("caption_emphasis", [])
            if isinstance(emp, list):
                emphasis_words.extend(emp)

    print(f"Generating captions...")
    print(f"  Words: {len(word_timestamps)}")
    if emphasis_words:
        print(f"  Emphasis: {emphasis_words}")

    srt_path, json_path = generate_captions(
        word_timestamps=word_timestamps,
        output_dir=args.output_dir,
        max_words_per_group=args.max_words,
        fps=args.fps,
        emphasis_words=emphasis_words,
    )

    print(f"\nDone.")


if __name__ == "__main__":
    main()
