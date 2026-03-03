#!/usr/bin/env python3
"""
Topic Discovery Engine for YouTube Longform Content Pipeline.

Discovers trending tech/AI topics from multiple free sources:
  - Hacker News (top stories API)
  - Reddit (r/technology, r/programming, r/artificial)
  - arXiv (recent AI/ML papers)

Scores, deduplicates, and ranks topics for video production.
No API keys required for any source.
"""

import os
import sys
import json
import re
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from xml.etree import ElementTree

import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(PROJECT_ROOT, ".tmp")
DEFAULT_OUTPUT = os.path.join(TMP_DIR, "discovery.json")

RELEVANCE_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
    "llm", "large language model", "gpt", "claude", "gemini", "chatbot",
    "neural network", "transformer", "diffusion", "generative",
    "coding", "programming", "developer", "software", "engineering",
    "python", "javascript", "typescript", "rust", "go",
    "api", "framework", "library", "open source", "github",
    "automation", "devops", "cloud", "aws", "gcp", "azure",
    "startup", "saas", "developer tools", "ide", "code editor",
    "cursor", "copilot", "vscode", "terminal",
    "agent", "agentic", "rag", "retrieval", "vector", "embedding",
    "fine-tuning", "training", "inference", "gpu", "nvidia", "cuda",
    "robotics", "computer vision", "nlp", "speech", "multimodal",
    "data science", "data engineering", "analytics",
    "cybersecurity", "security", "privacy", "encryption",
    "web development", "frontend", "backend", "fullstack",
    "docker", "kubernetes", "microservices", "serverless",
    "database", "sql", "nosql", "postgres", "redis",
    "tech", "technology", "tutorial", "guide", "how to",
]

REDDIT_SUBREDDITS = ["technology", "programming", "artificial"]
REDDIT_USER_AGENT = "YTLongform/1.0 (topic-discovery)"

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

ARXIV_API_URL = "http://export.arxiv.org/api/query"

# How many items to fetch per source (before filtering)
HN_FETCH_COUNT = 40
REDDIT_FETCH_COUNT = 25
ARXIV_FETCH_COUNT = 25

# Timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 15.0

# Fuzzy match threshold for deduplication (0-1, higher = stricter)
DEDUP_THRESHOLD = 0.65


# ---------------------------------------------------------------------------
# Source Fetchers
# ---------------------------------------------------------------------------

async def fetch_hackernews(client: httpx.AsyncClient) -> list[dict]:
    """Fetch top stories from Hacker News."""
    topics = []
    try:
        resp = await client.get(HN_TOP_STORIES_URL, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        story_ids = resp.json()[:HN_FETCH_COUNT]

        # Fetch story details concurrently (in batches of 10)
        for batch_start in range(0, len(story_ids), 10):
            batch = story_ids[batch_start:batch_start + 10]
            tasks = [
                client.get(HN_ITEM_URL.format(id=sid), timeout=HTTP_TIMEOUT)
                for sid in batch
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for r in responses:
                if isinstance(r, Exception):
                    continue
                try:
                    r.raise_for_status()
                    item = r.json()
                except Exception:
                    continue

                if not item or item.get("type") != "story":
                    continue

                title = item.get("title", "").strip()
                if not title:
                    continue

                posted_at = datetime.fromtimestamp(
                    item.get("time", 0), tz=timezone.utc
                ).isoformat()

                topics.append({
                    "title": title,
                    "source": "hackernews",
                    "source_url": item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
                    "engagement": {
                        "upvotes": item.get("score", 0),
                        "comments": item.get("descendants", 0),
                    },
                    "posted_at": posted_at,
                    "raw_score": item.get("score", 0),
                })

        print(f"  [HN] Fetched {len(topics)} stories")
    except Exception as e:
        print(f"  [HN] Error: {e}", file=sys.stderr)

    return topics


async def fetch_reddit(client: httpx.AsyncClient) -> list[dict]:
    """Fetch hot posts from tech subreddits."""
    topics = []
    headers = {"User-Agent": REDDIT_USER_AGENT}

    for sub in REDDIT_SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={REDDIT_FETCH_COUNT}"
            resp = await client.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            posts = data.get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                title = d.get("title", "").strip()
                if not title:
                    continue
                # Skip stickied / meta posts
                if d.get("stickied"):
                    continue

                posted_at = datetime.fromtimestamp(
                    d.get("created_utc", 0), tz=timezone.utc
                ).isoformat()

                topics.append({
                    "title": title,
                    "source": f"reddit/r/{sub}",
                    "source_url": f"https://www.reddit.com{d.get('permalink', '')}",
                    "engagement": {
                        "upvotes": d.get("ups", 0),
                        "comments": d.get("num_comments", 0),
                    },
                    "posted_at": posted_at,
                    "raw_score": d.get("ups", 0),
                })

            print(f"  [Reddit] r/{sub}: {len(posts)} posts")
        except Exception as e:
            print(f"  [Reddit] r/{sub} error: {e}", file=sys.stderr)

    print(f"  [Reddit] Total: {len(topics)} posts")
    return topics


async def fetch_arxiv(client: httpx.AsyncClient) -> list[dict]:
    """Fetch recent AI/ML papers from arXiv."""
    topics = []
    try:
        params = {
            "search_query": "cat:cs.AI OR cat:cs.LG OR cat:cs.CL",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(ARXIV_FETCH_COUNT),
        }
        resp = await client.get(ARXIV_API_URL, params=params, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()

        # Parse Atom XML
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ElementTree.fromstring(resp.text)
        entries = root.findall("atom:entry", ns)

        for entry in entries:
            title_el = entry.find("atom:title", ns)
            title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
            if not title:
                continue

            summary_el = entry.find("atom:summary", ns)
            summary = summary_el.text.strip().replace("\n", " ")[:200] if summary_el is not None else ""

            published_el = entry.find("atom:published", ns)
            posted_at = published_el.text if published_el is not None else ""

            link_el = entry.find("atom:id", ns)
            source_url = link_el.text if link_el is not None else ""

            topics.append({
                "title": title,
                "source": "arxiv",
                "source_url": source_url,
                "engagement": {
                    "upvotes": 0,  # arXiv has no upvote system
                    "comments": 0,
                },
                "posted_at": posted_at,
                "raw_score": 0,
                "summary": summary,
            })

        print(f"  [arXiv] Fetched {len(topics)} papers")
    except Exception as e:
        print(f"  [arXiv] Error: {e}", file=sys.stderr)

    return topics


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_recency_score(posted_at: str) -> float:
    """Score 0-100 based on how recent the item is. Full marks < 6h, zero > 7d."""
    try:
        if posted_at.endswith("Z"):
            posted_at = posted_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(posted_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return 30  # default for unparseable dates

    if age_hours < 6:
        return 100
    elif age_hours < 12:
        return 85
    elif age_hours < 24:
        return 70
    elif age_hours < 48:
        return 55
    elif age_hours < 72:
        return 40
    elif age_hours < 168:  # 7 days
        return 25
    else:
        return 10


def compute_engagement_score(engagement: dict, source: str) -> float:
    """Score 0-100 based on upvotes and comments. Scaled per source."""
    upvotes = engagement.get("upvotes", 0)
    comments = engagement.get("comments", 0)

    if source == "hackernews":
        # HN top stories: 100+ is decent, 500+ is great
        up_score = min(upvotes / 500 * 100, 100)
        cm_score = min(comments / 200 * 100, 100)
    elif source.startswith("reddit"):
        # Reddit: 500+ is decent, 5000+ is great
        up_score = min(upvotes / 5000 * 100, 100)
        cm_score = min(comments / 500 * 100, 100)
    elif source == "arxiv":
        # arXiv has no engagement metrics; give a baseline
        return 40
    else:
        up_score = min(upvotes / 100 * 100, 100)
        cm_score = min(comments / 50 * 100, 100)

    return round(up_score * 0.6 + cm_score * 0.4, 1)


def compute_relevance_score(title: str, summary: str = "") -> float:
    """Score 0-100 based on keyword match against Tech/AI niche."""
    text = (title + " " + summary).lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)

    if matches == 0:
        return 5
    elif matches == 1:
        return 30
    elif matches == 2:
        return 55
    elif matches <= 4:
        return 75
    else:
        return min(80 + matches * 2, 100)


def compute_novelty_score(title: str, published_titles: list[str]) -> float:
    """Score 0-100 where 100 = completely novel (no similar published videos)."""
    if not published_titles:
        return 100

    title_lower = title.lower()
    max_similarity = 0.0
    for pub in published_titles:
        ratio = SequenceMatcher(None, title_lower, pub.lower()).ratio()
        if ratio > max_similarity:
            max_similarity = ratio

    # High similarity -> low novelty
    if max_similarity > 0.8:
        return 5
    elif max_similarity > 0.6:
        return 30
    elif max_similarity > 0.4:
        return 60
    else:
        return 100


def score_topic(topic: dict, published_titles: list[str] | None = None) -> float:
    """
    Compute a weighted overall score for a topic.

    Weights:
      - Recency:    25%
      - Engagement: 25%
      - Relevance:  35%
      - Novelty:    15%

    Returns a score 0-100.
    """
    recency = compute_recency_score(topic.get("posted_at", ""))
    engagement = compute_engagement_score(
        topic.get("engagement", {}), topic.get("source", "")
    )
    relevance = compute_relevance_score(
        topic.get("title", ""), topic.get("summary", "")
    )
    novelty = compute_novelty_score(
        topic.get("title", ""), published_titles or []
    )

    weighted = (
        recency * 0.25
        + engagement * 0.25
        + relevance * 0.35
        + novelty * 0.15
    )
    return round(weighted, 1)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate_topics(topics: list[dict]) -> list[dict]:
    """Remove near-duplicate topics using fuzzy title matching."""
    if not topics:
        return topics

    unique = []
    for topic in topics:
        title_lower = topic["title"].lower()
        is_dup = False
        for kept in unique:
            ratio = SequenceMatcher(
                None, title_lower, kept["title"].lower()
            ).ratio()
            if ratio >= DEDUP_THRESHOLD:
                # Keep the one with higher score
                if topic.get("score", 0) > kept.get("score", 0):
                    unique.remove(kept)
                    unique.append(topic)
                is_dup = True
                break
        if not is_dup:
            unique.append(topic)

    return unique


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords(title: str, summary: str = "") -> list[str]:
    """Extract matching keywords from title/summary."""
    text = (title + " " + summary).lower()
    found = []
    for kw in RELEVANCE_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)
    # Capitalise nicely
    return [kw.title() if len(kw) > 2 else kw.upper() for kw in found[:8]]


# ---------------------------------------------------------------------------
# Suggested angle generation
# ---------------------------------------------------------------------------

def suggest_angle(topic: dict) -> str:
    """Generate a suggested video angle based on the topic source and title."""
    title = topic.get("title", "")
    source = topic.get("source", "")

    title_lower = title.lower()

    if source == "arxiv":
        return "Explain the paper's key findings in plain English with visual demonstrations"
    if any(w in title_lower for w in ["release", "launch", "announce", "introduce", "new"]):
        return "First look review and hands-on demo with comparison to alternatives"
    if any(w in title_lower for w in ["vs", "compare", "better", "best"]):
        return "Deep-dive comparison with benchmarks and real-world use cases"
    if any(w in title_lower for w in ["how to", "tutorial", "guide", "build", "create"]):
        return "Step-by-step tutorial with practical code examples"
    if any(w in title_lower for w in ["why", "problem", "issue", "fail", "broken"]):
        return "Problem analysis with solutions and expert commentary"
    if any(w in title_lower for w in ["future", "predict", "trend", "2026", "2027"]):
        return "Trend analysis with predictions and implications for developers"
    if any(w in title_lower for w in ["tool", "app", "product", "platform"]):
        return "Product review with demo, pros/cons, and who it's best for"

    return "Explainer video covering what it is, why it matters, and how to get started"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def discover_topics_async(
    sources: list[str] | None = None,
    published_titles: list[str] | None = None,
) -> list[dict]:
    """
    Fetch topics from all sources, score, deduplicate, and rank them.

    Args:
        sources: List of sources to fetch from. None = all.
                 Valid values: "hn", "reddit", "arxiv"
        published_titles: Previously published video titles to penalise.

    Returns:
        Ranked list of topic dicts.
    """
    all_sources = sources or ["hn", "reddit", "arxiv"]
    all_topics: list[dict] = []

    print("Discovering topics...")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = []
        if "hn" in all_sources:
            tasks.append(("hn", fetch_hackernews(client)))
        if "reddit" in all_sources:
            tasks.append(("reddit", fetch_reddit(client)))
        if "arxiv" in all_sources:
            tasks.append(("arxiv", fetch_arxiv(client)))

        results = await asyncio.gather(
            *[t[1] for t in tasks], return_exceptions=True
        )

        for (name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"  [{name}] Failed: {result}", file=sys.stderr)
            elif isinstance(result, list):
                all_topics.extend(result)

    print(f"\nRaw topics collected: {len(all_topics)}")

    # Score all topics
    for topic in all_topics:
        topic["score"] = score_topic(topic, published_titles)
        topic["keywords"] = extract_keywords(
            topic.get("title", ""), topic.get("summary", "")
        )
        topic["suggested_angle"] = suggest_angle(topic)

    # Sort by score descending
    all_topics.sort(key=lambda t: t["score"], reverse=True)

    # Deduplicate
    all_topics = deduplicate_topics(all_topics)

    # Re-sort after dedup (since replacements may shift order)
    all_topics.sort(key=lambda t: t["score"], reverse=True)

    print(f"After deduplication: {len(all_topics)} topics")

    return all_topics


def discover_topics(
    sources: list[str] | None = None,
    published_titles: list[str] | None = None,
) -> list[dict]:
    """Synchronous wrapper for the async discovery pipeline."""
    return asyncio.run(discover_topics_async(sources, published_titles))


def load_exclude_titles(path: str) -> list[str]:
    """Load previously published titles from a JSON file."""
    if not os.path.exists(path):
        print(f"Warning: exclude file not found: {path}", file=sys.stderr)
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        # Support both flat list of strings and list of dicts with 'title' key
        if isinstance(data, list):
            if data and isinstance(data[0], str):
                return data
            return [item.get("title", "") for item in data if isinstance(item, dict)]
        return []
    except Exception as e:
        print(f"Warning: failed to parse exclude file: {e}", file=sys.stderr)
        return []


def format_output(topics: list[dict]) -> dict:
    """Format topics into the standard discovery output format."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    formatted_topics = []
    for t in topics:
        formatted_topics.append({
            "title": t["title"],
            "source": t["source"],
            "source_url": t.get("source_url", ""),
            "score": t["score"],
            "engagement": t.get("engagement", {"upvotes": 0, "comments": 0}),
            "keywords": t.get("keywords", []),
            "suggested_angle": t.get("suggested_angle", ""),
            "discovered_at": t.get("posted_at", now),
        })

    return {
        "discovered_at": now,
        "topics": formatted_topics,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Discover trending tech/AI topics for YouTube longform videos"
    )
    parser.add_argument(
        "--top", type=int, default=0,
        help="Return only top N topics (default: all)"
    )
    parser.add_argument(
        "--source", choices=["hn", "reddit", "arxiv"],
        help="Fetch from a single source only"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output file path (default: .tmp/discovery.json)"
    )
    parser.add_argument(
        "--exclude-file", type=str, default=None,
        help="JSON file of previously published titles to skip"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print JSON output to stdout instead of formatted table"
    )

    args = parser.parse_args()

    # Determine sources
    sources = [args.source] if args.source else None

    # Load exclusions
    published_titles = []
    if args.exclude_file:
        published_titles = load_exclude_titles(args.exclude_file)
        print(f"Loaded {len(published_titles)} published titles to exclude")

    # Run discovery
    topics = discover_topics(sources=sources, published_titles=published_titles)

    # Limit if requested
    if args.top > 0:
        topics = topics[:args.top]

    # Format output
    output = format_output(topics)

    # Determine output path
    output_path = args.output
    if output_path is None:
        output_path = DEFAULT_OUTPUT

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Write to file
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {len(output['topics'])} topics to {output_path}")

    # Print results
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"\n{'='*70}")
        print(f"  DISCOVERED TOPICS  ({output['discovered_at']})")
        print(f"{'='*70}")
        for i, t in enumerate(output["topics"], 1):
            src_label = t["source"]
            up = t["engagement"]["upvotes"]
            cm = t["engagement"]["comments"]
            print(f"\n  {i:>2}. [{t['score']:>5.1f}] {t['title']}")
            print(f"      Source: {src_label}  |  Upvotes: {up}  |  Comments: {cm}")
            if t["keywords"]:
                print(f"      Keywords: {', '.join(t['keywords'])}")
            print(f"      Angle: {t['suggested_angle']}")
        print(f"\n{'='*70}")


if __name__ == "__main__":
    main()
