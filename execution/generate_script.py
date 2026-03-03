#!/usr/bin/env python3
"""
Video Script Generator for YouTube Longform Content.

Generates structured scripts from topics/outlines using Claude.
Supports full scripts, bullet outlines, and hybrid formats.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()


SCRIPT_SYSTEM_PROMPT = """You are an expert YouTube scriptwriter. You write scripts that:
- Sound natural when spoken aloud (write for the ear, not the eye)
- Use short, punchy sentences
- Include retention hooks every 3-5 minutes
- Mark B-roll opportunities with [B-ROLL: description]
- Mark intentional pauses with [BEAT]
- Use conversational markers ("Look,", "Here's the thing,", "So,")
- Include specific examples, numbers, and stories
- Follow the Hook → Context → Content → CTA structure"""


def generate_script(
    client: anthropic.Anthropic,
    topic: str,
    outline: str = None,
    style: str = "hybrid",
    length: int = 15,
) -> str:
    """
    Generate a video script using Claude.

    Args:
        client: Anthropic client
        topic: Video topic/title
        outline: Optional outline to work from
        style: full / bullet / hybrid
        length: Target video length in minutes

    Returns:
        Script as markdown string
    """
    outline_section = f"\n\nExisting outline to expand:\n{outline}" if outline else ""

    style_instruction = {
        "full": "Write a word-for-word script. Every line should be speakable.",
        "bullet": "Write a bullet-point outline with key talking points. Leave room for improvisation.",
        "hybrid": "Write the hook and CTA as full script. Write the main content as detailed bullet points with key phrases to hit.",
        "faceless": "Write a structured faceless narration script. Use the VISUAL+NARRATION block format described below.",
    }

    if style == "faceless":
        prompt = f"""Write a faceless YouTube narration script in structured VISUAL+NARRATION block format.

Topic: {topic}
Target length: {length} minutes (~{length * 150} words)
{outline_section}

OUTPUT FORMAT (follow exactly):

# {{Video Title}}

## HOOK (0:00 - 0:30)

---
VISUAL_TYPE: stock_footage
VISUAL_QUERY: "descriptive search query for stock video"
NARRATION: "Opening hook sentence that grabs attention."
---
VISUAL_TYPE: ai_generated
VISUAL_PROMPT: "Detailed image generation prompt, cinematic style"
NARRATION: "Second hook sentence building curiosity."
CAPTION_EMPHASIS: ["key phrase"]
---

## SEGMENT 1: {{Segment Title}} (0:30 - 3:00)

---
VISUAL_TYPE: stock_footage
VISUAL_QUERY: "relevant stock video search query"
NARRATION: "Clear, conversational narration sentence."
---

(continue pattern for all segments...)

## CTA & OUTRO (last 30 seconds)

---
VISUAL_TYPE: ai_generated
VISUAL_PROMPT: "Stylized outro graphic, subscribe button, dark theme"
NARRATION: "If you found this valuable, hit subscribe and drop a comment below."
---

RULES:
- Every segment MUST use the --- delimited block format above
- VISUAL_TYPE must be either "stock_footage" or "ai_generated"
- For stock_footage: include VISUAL_QUERY with a descriptive search term
- For ai_generated: include VISUAL_PROMPT with a detailed image prompt
- NARRATION must be natural, conversational, and complete sentences
- Optional: CAPTION_EMPHASIS: ["word1", "word2"] for words to highlight in captions
- Aim for 15-25 blocks total for a {length}-minute video
- Each NARRATION should be 1-3 sentences (5-15 seconds when spoken)
- Alternate between stock_footage and ai_generated for visual variety
- Include retention hooks between major segments
- Write for the ear, not the eye — short punchy sentences"""
    else:
        prompt = f"""Write a YouTube video script.

Topic: {topic}
Target length: {length} minutes (~{length * 150} words)
Format: {style} ({style_instruction[style]})
{outline_section}

Structure:
1. HOOK (0:00-0:30)
   - Pattern interrupt (something unexpected)
   - Promise (what they'll learn)
   - Proof (why you're credible)

2. CONTEXT (0:30-2:00)
   - Why this matters
   - Who this is for

3. MAIN CONTENT (2:00-{length-2}:00)
   - 3-7 segments, each with a clear point
   - Include [B-ROLL: description] markers
   - Add retention hooks between segments
   - Include [BEAT] for dramatic pauses

4. CTA & OUTRO (last 2 min)
   - 2-3 key takeaways
   - Subscribe/comment prompt
   - Tease next video

Add approximate timestamps throughout."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4000,
        system=SCRIPT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def generate_teleprompter(script: str) -> str:
    """
    Convert a script to teleprompter format.
    Strips markdown, B-ROLL markers, and formatting.
    Keeps only speakable text in large, clear lines.
    """
    lines = []
    for line in script.split("\n"):
        line = line.strip()
        # Skip markdown headers, B-ROLL markers, timestamps
        if line.startswith("#") or line.startswith("[B-ROLL") or line.startswith("---"):
            continue
        if line.startswith("[BEAT]"):
            lines.append("")
            lines.append("... (pause) ...")
            lines.append("")
            continue
        if line.startswith("- "):
            line = line[2:]
        if line.startswith("**") and line.endswith("**"):
            line = line[2:-2]
        if line:
            lines.append(line)

    return "\n\n".join(lines)


def refine_script(client: anthropic.Anthropic, script: str, feedback: str = None) -> str:
    """
    Refine an existing script.

    Args:
        client: Anthropic client
        script: Existing script text
        feedback: Optional specific feedback

    Returns:
        Refined script
    """
    feedback_section = f"\n\nSpecific feedback to address:\n{feedback}" if feedback else ""

    prompt = f"""Refine this YouTube script. Make it:
- More conversational and natural-sounding
- Tighter (remove filler, redundancy)
- Better paced (add/adjust retention hooks)
- More specific (replace vague statements with examples)
{feedback_section}

Current script:
{script}

Return the complete refined script."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4000,
        system=SCRIPT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube video scripts")
    parser.add_argument("--topic", help="Video topic/title")
    parser.add_argument("--outline", help="Path to outline file")
    parser.add_argument("--style", default="hybrid", choices=["full", "bullet", "hybrid", "faceless"])
    parser.add_argument("--length", type=int, default=15, help="Target length in minutes (default: 15)")
    parser.add_argument("--refine", help="Path to existing script to refine")
    parser.add_argument("--feedback", help="Specific feedback for refinement")
    parser.add_argument("--teleprompter", action="store_true", help="Also generate teleprompter version")

    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    os.makedirs(".tmp/scripts", exist_ok=True)

    if args.refine:
        with open(args.refine, "r") as f:
            script = f.read()
        print(f"Refining script: {args.refine}")
        refined = refine_script(client, script, args.feedback)

        # Save with incremented version
        base = args.refine.rsplit("_v", 1)
        if len(base) == 2:
            version = int(base[1].replace(".md", "")) + 1
            output_path = f"{base[0]}_v{version}.md"
        else:
            output_path = args.refine.replace(".md", "_v2.md")

        with open(output_path, "w") as f:
            f.write(refined)
        print(f"Refined script saved to {output_path}")
        return

    if not args.topic:
        print("Error: --topic is required", file=sys.stderr)
        sys.exit(1)

    # Load outline if provided
    outline = None
    if args.outline:
        with open(args.outline, "r") as f:
            outline = f.read()

    print(f"Generating {args.style} script for: {args.topic}")
    print(f"Target length: {args.length} minutes")

    script = generate_script(client, args.topic, outline, args.style, args.length)

    # Save script
    slug = args.topic.lower().replace(" ", "_")[:40]
    script_path = f".tmp/scripts/{slug}_v1.md"
    with open(script_path, "w") as f:
        f.write(script)
    print(f"Script saved to {script_path}")

    # Generate teleprompter version if requested
    if args.teleprompter:
        teleprompter = generate_teleprompter(script)
        tp_path = f".tmp/scripts/{slug}_teleprompter.txt"
        with open(tp_path, "w") as f:
            f.write(teleprompter)
        print(f"Teleprompter version saved to {tp_path}")

    # Print script
    print("\n" + "=" * 60)
    print(script)


if __name__ == "__main__":
    main()
