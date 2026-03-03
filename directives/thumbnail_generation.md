# Thumbnail Generation

Generate eye-catching 1280x720 YouTube thumbnails with bold text overlays. Supports AI-generated cinematic backgrounds (Flux via Replicate) and a zero-cost template fallback using Pillow.

## Execution Script

`execution/generate_thumbnail.py`

---

## Quick Start

```bash
# Template mode (no API key needed)
python3 execution/generate_thumbnail.py \
  --video-id 20260303_ai_tools \
  --title "5 AI Tools That Will Replace Your Entire Tech Stack" \
  --mode template \
  --output .tmp/20260303_ai_tools/thumbnail.png

# AI mode (requires REPLICATE_API_TOKEN)
python3 execution/generate_thumbnail.py \
  --video-id 20260303_ai_tools \
  --title "5 AI Tools That Will Replace Your Entire Tech Stack" \
  --mode ai \
  --output .tmp/20260303_ai_tools/thumbnail.png

# Default output path (.tmp/{video_id}/thumbnail.png)
python3 execution/generate_thumbnail.py \
  --video-id 20260303_ai_tools \
  --title "5 AI Tools That Will Replace Your Entire Tech Stack" \
  --mode template
```

---

## What It Does

1. **Parses the title** -- Extracts the most impactful keywords (strips filler words, keeps max 5 words, uppercases)
2. **Generates background** -- Either via AI (Flux) or gradient template
3. **Adds overlay** -- Semi-transparent gradient for text readability
4. **Renders text** -- Large bold white text with dark stroke, auto-sized and word-wrapped to fit
5. **Saves PNG** -- 1280x720, YouTube-standard thumbnail

---

## Modes

### Mode 1: AI-Generated (`--mode ai`)

Uses Flux Schnell via Replicate to generate a cinematic background image from the video title.

**Pipeline:**
1. Builds an image prompt from the title (cinematic style, dramatic lighting, no text)
2. Calls `black-forest-labs/flux-schnell` on Replicate
3. Downloads and resizes the generated image to 1280x720
4. Adds gradient overlay for text readability
5. Renders bold title keywords with stroke

**Cost:** ~$0.02 per thumbnail

**Fallback:** If Replicate fails or `REPLICATE_API_TOKEN` is not set, automatically falls back to template mode.

### Mode 2: Template-Based (`--mode template`)

Creates a visually appealing thumbnail using only Pillow -- no API calls, zero cost.

**Pipeline:**
1. Creates a multi-stop gradient background (dark blue to purple to dark red)
2. Adds a subtle radial glow in the center
3. Adds geometric accent elements (diagonal lines, horizontal rules, accent rectangles)
4. Renders bold title keywords with stroke
5. Adds a semi-transparent branding bar at the bottom

---

## Text Rendering

- **Font selection:** Searches system fonts in order of preference: Impact, Arial Bold, Arial Black, Futura, DejaVu Sans Bold, Liberation Sans Bold
- **Auto-sizing:** Tries font sizes from 96px down to 48px to find optimal fit
- **Word wrapping:** Wraps text to max 85% of image width, max 3 lines
- **Stroke:** Dark outline (4px+) around white text for readability on any background
- **Keyword extraction:** Strips filler words ("the", "and", "with", etc.), keeps top 5 impactful words, uppercased

---

## CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--video-id` | Yes | -- | Unique video identifier |
| `--title` | Yes | -- | Video title or topic |
| `--mode` | No | `template` | `ai` or `template` |
| `--output` | No | `.tmp/{video_id}/thumbnail.png` | Output file path |

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Thumbnail image | PNG (1280x720) | `--output` or `.tmp/{video_id}/thumbnail.png` |
| AI background (temp) | PNG | `.tmp/{video_id}/thumbnail_bg.png` (AI mode only) |

---

## Environment Variables

```
REPLICATE_API_TOKEN=       # Required for AI mode only
```

---

## Cost Per Thumbnail

| Mode | API Calls | Cost |
|------|-----------|------|
| Template | 0 | $0.00 |
| AI | 1 Replicate call | ~$0.02 |

---

## Edge Cases

- **Missing REPLICATE_API_TOKEN in AI mode**: Automatically falls back to template mode with a warning
- **Replicate API failure**: Falls back to template mode
- **No system bold font found**: Uses Pillow's built-in default font at a larger size
- **Very long titles**: Keyword extraction limits to 5 words; text auto-sizes down to 48px; wraps to max 3 lines
- **Very short titles (1-2 words)**: Uses full title instead of keyword extraction
- **Output directory doesn't exist**: Created automatically
- **Missing Pillow dependency**: Script will fail with ImportError -- install with `pip install Pillow`

---

## Quality Guidelines for Thumbnails

Good YouTube thumbnails follow these principles:

1. **Contrast**: White text on dark backgrounds, or dark text on bright backgrounds
2. **Minimal text**: 3-5 words maximum -- the thumbnail is a billboard, not a paragraph
3. **Large text**: Must be readable at 200x112px (mobile search results)
4. **Color pop**: Vibrant accent colors draw the eye in a sea of thumbnails
5. **Consistency**: Same general style across channel videos for brand recognition
6. **No clutter**: Clean composition with clear focal point

**AI mode tips for better backgrounds:**
- The prompt automatically includes "no text, no letters" to avoid AI-generated text artifacts
- Cinematic and dramatic lighting keywords produce more engaging backgrounds
- The gradient overlay ensures text is always readable regardless of the generated image

---

## Dependencies

```
Pillow>=10.0     # Image processing and text rendering
replicate>=0.25  # AI image generation (optional, only for AI mode)
httpx>=0.27      # Downloading generated images (optional, only for AI mode)
python-dotenv    # Environment variable loading
```

---

## Integration with Pipeline

This script is called during the pipeline's post-production phase, after metadata generation. The typical flow:

```
generate_metadata.py  -->  generates thumbnail concepts
generate_thumbnail.py -->  produces actual thumbnail image
youtube_upload.py     -->  uploads video with thumbnail
```

The metadata script may suggest thumbnail text/concepts which can be passed as `--title` to this script.
