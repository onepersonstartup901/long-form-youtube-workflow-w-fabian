# Ideation & Topic Research

Research, validate, and outline longform YouTube video topics. The goal is to find high-potential topics that match the channel's niche, have search demand, and low-enough competition.

## Execution Script

`execution/topic_research.py`

---

## Quick Start

```bash
# Research a topic area
python3 execution/topic_research.py --niche "your niche" --count 10

# Validate a specific topic idea
python3 execution/topic_research.py --validate "How to build X from scratch"

# Generate content calendar
python3 execution/topic_research.py --calendar --weeks 4
```

---

## What It Does

1. **Keyword research** — Pulls search volume, competition, and trending data
2. **Competitor analysis** — Finds top-performing videos in the niche, analyzes titles/thumbnails/retention
3. **Topic scoring** — Ranks ideas by: search demand, competition gap, audience fit, evergreen potential
4. **Outline generation** — Creates a structured outline with hooks, segments, and CTAs
5. **Content calendar** — Maps topics to a publishing schedule

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Niche keywords | User | The channel's topic area |
| Competitor channels | User / scraped | Channels to analyze |
| Past performance | YouTube Analytics | What worked before |

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Topic ideas (ranked) | JSON | `.tmp/topics_{date}.json` |
| Content calendar | JSON | `data/content_calendar.json` |
| Outlines | Markdown | `.tmp/outlines/` |

---

## Topic Scoring Criteria

| Factor | Weight | How to assess |
|--------|--------|---------------|
| Search demand | 30% | YouTube search suggestions, Google Trends |
| Competition gap | 25% | Few quality videos on the topic |
| Audience fit | 20% | Matches channel positioning |
| Evergreen potential | 15% | Will it still be relevant in 6 months? |
| Personal expertise | 10% | Can you speak on this authentically? |

---

## Edge Cases

- **Trending but saturated** — Skip unless you have a unique angle
- **Low search but high shareability** — Worth it if the topic is provocative/novel
- **Seasonal topics** — Plan around timing (publish 2-4 weeks before peak)
