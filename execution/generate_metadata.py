#!/usr/bin/env python3
"""
YouTube Metadata Generator.

Generates optimized titles, descriptions, tags, and thumbnail concepts
for YouTube videos using Claude.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()


def generate_metadata(
    client: anthropic.Anthropic,
    script: str = None,
    transcript: str = None,
    title_hint: str = None,
    niche: str = "general",
) -> dict:
    """
    Generate complete YouTube metadata package.

    Args:
        client: Anthropic client
        script: Video script text
        transcript: Video transcript text
        title_hint: Optional title hint
        niche: Channel niche

    Returns:
        Metadata dict with titles, description, tags, thumbnails
    """
    content = script or transcript or title_hint
    if not content:
        raise ValueError("Provide --script, --transcript, or --title")

    content_type = "script" if script else ("transcript" if transcript else "title")

    prompt = f"""Analyze this video {content_type} and generate optimized YouTube metadata.

Content:
{content[:3000]}

Niche: {niche}

Generate:

1. **titles** (array of 5-10 options):
   - Under 60 characters each
   - Front-load the keyword
   - Include numbers where natural
   - Create curiosity gap
   - Mix patterns: How-to, List, Result+Timeframe, Story, Contrarian

2. **description** (string):
   - 1-2 sentence hook expanding on the title
   - Brief summary
   - Timestamps section (estimate from content structure)
   - Resources mentioned section
   - Social links placeholders

3. **tags** (array of 30-50):
   - Primary keyword (exact match)
   - Variations and long-tail
   - Related topics
   - Mix broad and specific

4. **hashtags** (array of 3):
   - For the title line

5. **thumbnail_concepts** (array of 3-5):
   - Each with: text_overlay, emotion, composition, color_scheme

6. **category**: Best YouTube category

Return as JSON only. No other text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def format_description(metadata: dict) -> str:
    """Format the description for direct paste into YouTube."""
    return metadata.get("description", "")


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube metadata")
    parser.add_argument("--script", help="Path to video script file")
    parser.add_argument("--transcript", help="Path to transcript file")
    parser.add_argument("--title", help="Video title hint")
    parser.add_argument("--niche", default="general", help="Channel niche")
    parser.add_argument("--thumbnail-concepts", action="store_true", help="Focus on thumbnail concepts")

    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    os.makedirs(".tmp/metadata", exist_ok=True)

    # Load content
    script = None
    transcript = None

    if args.script:
        with open(args.script, "r") as f:
            script = f.read()
    if args.transcript:
        with open(args.transcript, "r") as f:
            transcript = f.read()

    if not script and not transcript and not args.title:
        print("Error: Provide --script, --transcript, or --title", file=sys.stderr)
        sys.exit(1)

    print("Generating metadata...")
    metadata = generate_metadata(client, script, transcript, args.title, args.niche)

    # Save metadata JSON
    slug = (args.title or "video").lower().replace(" ", "_")[:40]
    meta_path = f".tmp/metadata/{slug}.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to {meta_path}")

    # Save description as pasteable text
    desc_path = f".tmp/metadata/{slug}_description.txt"
    with open(desc_path, "w") as f:
        f.write(format_description(metadata))
    print(f"Description saved to {desc_path}")

    # Print summary
    print(f"\nTitle options:")
    for i, title in enumerate(metadata.get("titles", [])):
        print(f"  {i+1}. {title}")

    print(f"\nTags: {len(metadata.get('tags', []))} generated")
    print(f"Hashtags: {', '.join(metadata.get('hashtags', []))}")

    if metadata.get("thumbnail_concepts"):
        print(f"\nThumbnail concepts:")
        for i, tc in enumerate(metadata["thumbnail_concepts"]):
            text = tc.get("text_overlay", "")
            emotion = tc.get("emotion", "")
            print(f"  {i+1}. \"{text}\" — {emotion}")


if __name__ == "__main__":
    main()
