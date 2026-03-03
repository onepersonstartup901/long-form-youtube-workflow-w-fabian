# Metadata & SEO

Generate optimized YouTube metadata — titles, descriptions, tags, and thumbnail concepts — to maximize discoverability and click-through rate.

## Execution Script

`execution/generate_metadata.py`

---

## Quick Start

```bash
# Generate metadata from a script/transcript
python3 execution/generate_metadata.py \
  --script .tmp/scripts/video_script.md \
  --niche "your niche"

# Generate from transcript (post-recording)
python3 execution/generate_metadata.py \
  --transcript .tmp/transcripts/video.txt

# Generate thumbnail concepts
python3 execution/generate_metadata.py \
  --thumbnail-concepts --title "Video Title"
```

---

## What It Does

1. **Title generation** — Creates 5-10 title options optimized for CTR and search
2. **Description writing** — SEO-rich description with timestamps, links, and keywords
3. **Tag generation** — 30-50 relevant tags ranked by search volume
4. **Thumbnail concepts** — 3-5 thumbnail ideas with text overlay, emotion, and composition notes
5. **Hashtags** — 3 hashtags for the title line

---

## Title Formula

Great YouTube titles follow patterns:

| Pattern | Example | When to use |
|---------|---------|-------------|
| How to [Result] | "How to Edit Videos 10x Faster" | Tutorial content |
| [Number] [Things] | "7 Mistakes Killing Your Videos" | List content |
| [Result] in [Timeframe] | "Learn Python in 30 Days" | Transformation |
| I [Did Thing] [Result] | "I Tried AI Editing for 30 Days" | Story/experiment |
| Why [Contrarian Take] | "Why Most YouTubers Fail" | Opinion/analysis |
| [Thing] is [Superlative] | "The Best Camera Under $500" | Review/comparison |

### Title Rules
- **Under 60 characters** (truncation in search)
- **Front-load the keyword** — Put the main search term early
- **Include a number** when possible (increases CTR by ~20%)
- **Create curiosity gap** — Don't give away the answer
- **Avoid clickbait** — Deliver on the promise

---

## Description Template

```
[1-2 sentence hook that expands on the title]

In this video, I [brief summary of what the viewer will learn/see].

⏰ Timestamps:
0:00 - Intro
0:30 - [Section 1]
2:15 - [Section 2]
...

🔗 Resources mentioned:
- [Resource 1](url)
- [Resource 2](url)

📱 Connect:
- [Social link 1]
- [Social link 2]

#hashtag1 #hashtag2 #hashtag3
```

---

## Tag Strategy

1. **Primary keyword** (exact match) — e.g., "how to edit youtube videos"
2. **Variations** — "youtube video editing", "edit videos for youtube"
3. **Long-tail** — "how to edit youtube videos for beginners 2026"
4. **Related topics** — "davinci resolve tutorial", "video editing tips"
5. **Channel brand** — Your channel name, series names
6. **Competitor tags** — Tags used by top-ranking videos on the same topic

---

## Thumbnail Best Practices

| Element | Guideline |
|---------|-----------|
| **Face** | Show emotion (surprise, excitement, concern) |
| **Text** | Max 4-6 words, large bold font, contrasting color |
| **Colors** | High contrast, avoid YouTube red (blends with UI) |
| **Composition** | Rule of thirds, face on one side, text on other |
| **Resolution** | 1280x720 minimum, 16:9 aspect ratio |
| **File size** | Under 2MB |

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Metadata package | JSON | `.tmp/metadata/{slug}.json` |
| Description (ready to paste) | Text | `.tmp/metadata/{slug}_description.txt` |
| Thumbnail concepts | Markdown | `.tmp/metadata/{slug}_thumbnails.md` |
