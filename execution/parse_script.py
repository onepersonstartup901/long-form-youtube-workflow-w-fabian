#!/usr/bin/env python3
"""
Faceless Script Parser.

Parses structured VISUAL+NARRATION block format scripts into
a list of segment dictionaries for downstream pipeline consumption.
"""

import re
import json
import argparse
import sys


def parse_script(script_text: str) -> dict:
    """
    Parse a structured faceless narration script.

    Args:
        script_text: Raw script text in VISUAL+NARRATION block format

    Returns:
        Dict with title, sections, and flat segments list
    """
    lines = script_text.strip().split("\n")

    # Extract title from first H1
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Extract sections (H2 headers)
    sections = []
    current_section = None

    for line in lines:
        if line.startswith("## "):
            section_text = line[3:].strip()
            current_section = {
                "name": section_text,
                "blocks": [],
            }
            sections.append(current_section)

    # Parse blocks between --- delimiters
    # Each --- is a block boundary: save current block and start a new one
    blocks = []
    in_block = False
    current_block = {}
    current_section_idx = -1

    for line in lines:
        stripped = line.strip()

        # Track which section we're in
        if stripped.startswith("## "):
            current_section_idx += 1
            continue

        if stripped == "---":
            if current_block:
                current_block["section_index"] = max(0, current_section_idx)
                if 0 <= current_section_idx < len(sections):
                    current_block["section_name"] = sections[current_section_idx]["name"]
                blocks.append(current_block)
            current_block = {}
            in_block = True
            continue

        if in_block and stripped:
            # Parse key: value pairs
            match = re.match(r'^(\w+):\s*(.+)$', stripped)
            if match:
                key = match.group(1).lower()
                value = match.group(2).strip()

                # Remove surrounding quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Parse JSON arrays (for CAPTION_EMPHASIS)
                if value.startswith("["):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass

                current_block[key] = value

    # Number blocks sequentially
    for i, block in enumerate(blocks):
        block["index"] = i

    return {
        "title": title,
        "sections": [s["name"] for s in sections],
        "blocks": blocks,
        "block_count": len(blocks),
    }


def validate_script(parsed: dict) -> list[str]:
    """
    Validate a parsed script for completeness.

    Returns:
        List of warning strings (empty = valid)
    """
    warnings = []

    if not parsed["title"]:
        warnings.append("Missing title (no # heading found)")

    if parsed["block_count"] == 0:
        warnings.append("No VISUAL+NARRATION blocks found")
        return warnings

    for i, block in enumerate(parsed["blocks"]):
        if "narration" not in block:
            warnings.append(f"Block {i}: missing NARRATION")
        if "visual_type" not in block:
            warnings.append(f"Block {i}: missing VISUAL_TYPE")
        elif block["visual_type"] == "stock_footage" and "visual_query" not in block:
            warnings.append(f"Block {i}: stock_footage missing VISUAL_QUERY")
        elif block["visual_type"] == "ai_generated" and "visual_prompt" not in block:
            warnings.append(f"Block {i}: ai_generated missing VISUAL_PROMPT")

    if parsed["block_count"] < 10:
        warnings.append(f"Only {parsed['block_count']} blocks — may be too short for 8+ min video")

    return warnings


def estimate_duration(parsed: dict, wpm: int = 150) -> float:
    """
    Estimate video duration from narration word count.

    Args:
        parsed: Parsed script dict
        wpm: Words per minute (default 150 for narration)

    Returns:
        Estimated duration in seconds
    """
    total_words = 0
    for block in parsed["blocks"]:
        narration = block.get("narration", "")
        total_words += len(narration.split())

    return (total_words / wpm) * 60


def main():
    parser = argparse.ArgumentParser(description="Parse faceless narration scripts")
    parser.add_argument("script", help="Path to script file")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--validate", action="store_true", help="Validate script completeness")
    parser.add_argument("--narration-only", action="store_true",
                        help="Output only narration text (for TTS)")

    args = parser.parse_args()

    with open(args.script, "r") as f:
        script_text = f.read()

    parsed = parse_script(script_text)

    if args.narration_only:
        for block in parsed["blocks"]:
            narration = block.get("narration", "")
            if narration:
                print(narration)
                print()
        return

    # Always write output if -o specified (even with --validate)
    if args.output:
        output = json.dumps(parsed, indent=2)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Parsed script saved to {args.output}")

    if args.validate:
        warnings = validate_script(parsed)
        duration = estimate_duration(parsed)
        print(f"Title: {parsed['title']}")
        print(f"Sections: {len(parsed['sections'])}")
        print(f"Blocks: {parsed['block_count']}")
        print(f"Estimated duration: {duration:.0f}s ({duration/60:.1f} min)")
        if warnings:
            print(f"\nWarnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("\nScript is valid.")
        return

    if not args.output:
        print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()
