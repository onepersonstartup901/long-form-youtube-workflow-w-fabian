#!/usr/bin/env python3
"""
Topic Research & Ideation for YouTube Longform Content.

Researches topics, scores them, and generates structured outlines.
Uses Anthropic API for analysis and outline generation.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()


def score_topic(topic: dict) -> float:
    """
    Score a topic idea based on weighted criteria.

    Args:
        topic: Dict with keys: search_demand, competition_gap,
               audience_fit, evergreen, expertise (each 0-10)

    Returns:
        Weighted score 0-100
    """
    weights = {
        "search_demand": 0.30,
        "competition_gap": 0.25,
        "audience_fit": 0.20,
        "evergreen": 0.15,
        "expertise": 0.10,
    }

    score = 0
    for key, weight in weights.items():
        score += topic.get(key, 5) * weight * 10

    return round(score, 1)


def generate_outline(client: anthropic.Anthropic, topic: str, niche: str, style: str = "educational") -> str:
    """
    Generate a structured video outline using Claude.

    Args:
        client: Anthropic client
        topic: Video topic/title
        niche: Channel niche
        style: Video style (educational, conversational, storytelling)

    Returns:
        Markdown outline string
    """
    prompt = f"""Generate a structured outline for a longform YouTube video.

Topic: {topic}
Niche: {niche}
Style: {style}
Target length: 15-20 minutes

Structure the outline as:
1. Hook (0:00-0:30) - Pattern interrupt + promise + proof
2. Context (0:30-2:00) - Why this matters, who it's for
3. Main Content (3-7 key segments with talking points)
4. CTA & Outro - Recap, call to action, end screen

For each segment include:
- Key points to cover
- [B-ROLL: description] markers where visuals should go
- Retention hooks between segments
- Approximate timestamps

Output as clean Markdown."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def research_topics(client: anthropic.Anthropic, niche: str, count: int = 10) -> list[dict]:
    """
    Generate and score topic ideas for a niche.

    Args:
        client: Anthropic client
        niche: Channel niche/topic area
        count: Number of ideas to generate

    Returns:
        List of scored topic dicts
    """
    prompt = f"""Generate {count} YouTube longform video topic ideas for the niche: "{niche}"

For each topic, provide:
- title: A compelling video title (under 60 chars)
- description: 1-sentence summary
- search_demand: Score 0-10 (how much are people searching for this?)
- competition_gap: Score 0-10 (how underserved is this topic?)
- audience_fit: Score 0-10 (how well does it match the niche?)
- evergreen: Score 0-10 (will this be relevant in 6+ months?)
- expertise: Score 0-10 (how easy is it to speak authentically on this?)
- angle: What unique angle makes this video stand out?

Return as a JSON array. Only output the JSON, no other text."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = message.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    topics = json.loads(text)

    # Add scores
    for topic in topics:
        topic["score"] = score_topic(topic)

    # Sort by score descending
    topics.sort(key=lambda t: t["score"], reverse=True)

    return topics


def generate_calendar(topics: list[dict], weeks: int = 4, videos_per_week: int = 1) -> list[dict]:
    """
    Map top topics to a content calendar.

    Args:
        topics: Scored topic list
        weeks: Number of weeks to plan
        videos_per_week: Videos per week

    Returns:
        Calendar entries
    """
    total_videos = weeks * videos_per_week
    selected = topics[:total_videos]

    calendar = []
    from datetime import timedelta

    start_date = datetime.now()
    for i, topic in enumerate(selected):
        week_num = i // videos_per_week
        publish_date = start_date + timedelta(weeks=week_num, days=1)  # Tuesdays

        calendar.append({
            "week": week_num + 1,
            "publish_date": publish_date.strftime("%Y-%m-%d"),
            "title": topic["title"],
            "score": topic["score"],
            "status": "planned",
        })

    return calendar


def main():
    parser = argparse.ArgumentParser(description="YouTube topic research and ideation")
    parser.add_argument("--niche", help="Channel niche/topic area")
    parser.add_argument("--count", type=int, default=10, help="Number of topic ideas (default: 10)")
    parser.add_argument("--validate", help="Validate a specific topic idea")
    parser.add_argument("--outline", help="Generate outline for a topic")
    parser.add_argument("--calendar", action="store_true", help="Generate content calendar from topics")
    parser.add_argument("--weeks", type=int, default=4, help="Weeks for calendar (default: 4)")
    parser.add_argument("--style", default="educational", choices=["educational", "conversational", "storytelling"])

    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    os.makedirs(".tmp/outlines", exist_ok=True)

    if args.outline:
        niche = args.niche or "general"
        print(f"Generating outline for: {args.outline}")
        outline = generate_outline(client, args.outline, niche, args.style)

        slug = args.outline.lower().replace(" ", "_")[:40]
        output_path = f".tmp/outlines/{slug}.md"
        with open(output_path, "w") as f:
            f.write(outline)

        print(f"Outline saved to {output_path}")
        print(outline)
        return

    if not args.niche:
        print("Error: --niche is required for topic research", file=sys.stderr)
        sys.exit(1)

    # Research topics
    print(f"Researching {args.count} topics for niche: {args.niche}")
    topics = research_topics(client, args.niche, args.count)

    # Save topics
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topics_path = f".tmp/topics_{timestamp}.json"
    with open(topics_path, "w") as f:
        json.dump(topics, f, indent=2)

    print(f"\nTop topics (saved to {topics_path}):")
    for i, t in enumerate(topics):
        print(f"  {i+1}. [{t['score']}] {t['title']}")
        print(f"     {t.get('angle', '')}")

    # Generate calendar if requested
    if args.calendar:
        calendar = generate_calendar(topics, args.weeks)
        calendar_path = "data/content_calendar.json"
        os.makedirs("data", exist_ok=True)
        with open(calendar_path, "w") as f:
            json.dump(calendar, f, indent=2)
        print(f"\nContent calendar saved to {calendar_path}")
        for entry in calendar:
            print(f"  Week {entry['week']} ({entry['publish_date']}): {entry['title']}")


if __name__ == "__main__":
    main()
