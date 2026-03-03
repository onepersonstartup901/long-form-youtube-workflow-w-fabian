# Topic Discovery

Automatically discover trending tech/AI topics from free public sources, score them for video potential, and output a ranked list for the content pipeline.

## Execution Script

`execution/discover_topics.py`

---

## Quick Start

```bash
# Discover and rank topics from all sources
python3 execution/discover_topics.py

# Top 10 only
python3 execution/discover_topics.py --top 10

# Single source
python3 execution/discover_topics.py --source hn

# Save to custom path
python3 execution/discover_topics.py --output topics.json

# Exclude previously published topics
python3 execution/discover_topics.py --exclude-file published.json

# JSON output to stdout
python3 execution/discover_topics.py --json
```

---

## What It Does

1. **Fetches** candidate topics from multiple free sources (no API keys needed)
2. **Scores** each topic on recency, engagement, relevance, and novelty
3. **Deduplicates** similar topics via fuzzy title matching
4. **Ranks** topics by composite score and outputs a JSON file

---

## Sources

| Source | URL Pattern | What it returns |
|--------|------------|-----------------|
| Hacker News | `hacker-news.firebaseio.com/v0/topstories.json` | Top 40 stories with scores & comment counts |
| Reddit | `reddit.com/r/{sub}/hot.json` | Hot posts from r/technology, r/programming, r/artificial |
| arXiv | `export.arxiv.org/api/query?cat:cs.AI` | Recent AI/ML/NLP papers |

All sources are free and require no authentication for basic use.

### Source Keys

- `hn` — Hacker News
- `reddit` — Reddit (all tech subreddits)
- `arxiv` — arXiv papers

---

## Scoring Criteria

Each topic gets a score from 0 to 100 based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Relevance | 35% | Keyword match against Tech/AI niche terms |
| Recency | 25% | How recently the topic was posted (6h = 100, 7d+ = 10) |
| Engagement | 25% | Upvotes and comments, scaled per source |
| Novelty | 15% | Penalises topics similar to previously published videos |

### Relevance Keywords

The script matches against ~60 keywords covering: AI/ML, programming languages, developer tools, cloud platforms, databases, security, and web development. The keyword list is maintained in `RELEVANCE_KEYWORDS` inside the script.

---

## Inputs

| Input | Source | Required | Description |
|-------|--------|----------|-------------|
| `--source` | CLI | No | Restrict to single source (`hn`, `reddit`, `arxiv`) |
| `--top` | CLI | No | Limit output to top N topics |
| `--output` | CLI | No | Custom output path (default: `.tmp/discovery.json`) |
| `--exclude-file` | CLI | No | JSON file of published titles to penalise |
| `--json` | CLI | No | Print JSON to stdout |

### Exclude File Format

The exclude file can be either:
- A flat JSON array of title strings: `["Title 1", "Title 2"]`
- An array of objects with `title` keys: `[{"title": "Title 1"}, ...]`

---

## Outputs

| Output | Format | Location |
|--------|--------|----------|
| Discovery results | JSON | `.tmp/discovery.json` (default) or `--output` path |

### Output Schema

```json
{
  "discovered_at": "2026-03-03T10:00:00+00:00",
  "topics": [
    {
      "title": "Claude 4.5 Released with Enhanced Coding Abilities",
      "source": "hackernews",
      "source_url": "https://...",
      "score": 85.0,
      "engagement": {"upvotes": 450, "comments": 120},
      "keywords": ["AI", "Claude", "Coding"],
      "suggested_angle": "First look review and hands-on demo with comparison to alternatives",
      "discovered_at": "2026-03-03T09:30:00+00:00"
    }
  ]
}
```

---

## Pipeline Integration

This script is the **first step** in the video pipeline — it feeds into `topic_research.py` for deeper research and outline generation.

Typical workflow:
```
discover_topics.py  -->  review top topics  -->  topic_research.py --outline "chosen topic"  -->  pipeline_orchestrator.py --new "topic"
```

---

## Edge Cases & Learnings

- **Reddit rate limiting**: Uses a custom User-Agent (`YTLongform/1.0`). If rate-limited, the script continues with other sources.
- **arXiv has no engagement metrics**: Papers get a baseline engagement score of 40. They rank based on recency and relevance.
- **Fuzzy dedup threshold**: Set at 0.65 (SequenceMatcher ratio). Lower = more aggressive dedup. Tune if too many similar topics appear.
- **Source failures are non-fatal**: Each source is fetched independently. If one fails, the others still return results.
- **Product Hunt**: Skipped in MVP (requires auth). Can be added later as a source.
- **HTTP timeout**: 15 seconds per request. Increase `HTTP_TIMEOUT` if on slow connections.
- **arXiv paper titles**: Often long/academic. The "suggested angle" helps reframe them for YouTube audiences.

---

## Future Improvements

- [ ] Add Product Hunt when API key is available
- [ ] Add YouTube trending/search suggestions as a source
- [ ] Add Google Trends integration
- [ ] LLM-powered angle generation (use Anthropic API for smarter suggestions)
- [ ] Persistent topic database to track discovery over time
- [ ] Slack/Telegram notification of high-scoring topics
