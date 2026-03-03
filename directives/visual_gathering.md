# Visual Gathering

Source visual assets for each script block — stock footage/photos from Pexels/Pixabay and AI-generated images via Flux.

## Execution Script

`execution/gather_visuals.py`

---

## Quick Start

```bash
# Gather visuals for a parsed script
python3 execution/gather_visuals.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/

# Skip AI image generation (stock only)
python3 execution/gather_visuals.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/ \
  --skip-ai

# Prefer photos over video
python3 execution/gather_visuals.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/ \
  --no-prefer-video
```

---

## What It Does

1. **Reads parsed script** — Each block has `VISUAL_TYPE` and query/prompt
2. **For `stock_footage` blocks:**
   - Searches Pexels videos first (free API)
   - Falls back to Pixabay videos
   - Falls back to Pexels/Pixabay photos
   - Downloads best match to `visuals/` directory
3. **For `ai_generated` blocks:**
   - Sends prompt to Flux-schnell via Replicate API
   - Downloads generated image to `visuals/` directory
4. **Builds manifest** — JSON mapping each block to its visual file

---

## Visual Sources

| Source | Type | Cost | API Key |
|--------|------|------|---------|
| Pexels | Video + Photo | Free | `PEXELS_API_KEY` |
| Pixabay | Video + Photo | Free | `PIXABAY_API_KEY` |
| Flux-schnell (Replicate) | AI Images | ~$0.02/image | `REPLICATE_API_TOKEN` |

### Search Priority (stock_footage blocks)

```
1. Pexels videos → best match by query
2. Pixabay videos → fallback
3. Pexels photos → fallback
4. Pixabay photos → fallback
5. Placeholder (solid color) → last resort
```

---

## AI Image Generation

Used for `ai_generated` blocks. The `VISUAL_PROMPT` from the script is sent directly to Flux-schnell.

**Good prompts for tech content:**
- "Futuristic holographic code editor interface, neon blue glow, dark background, cinematic"
- "Neural network visualization, glowing nodes and connections, abstract data flow"
- "Robot hand typing on keyboard, macro shot, dramatic lighting"

**Tips:**
- Include "cinematic" or "professional photography" for higher quality
- Specify lighting: "dramatic lighting", "soft studio light", "neon glow"
- Add composition: "macro shot", "wide angle", "aerial view"

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Visual files | MP4/JPG/PNG | `.tmp/{vid}/visuals/` |
| Visuals manifest | JSON | `.tmp/{vid}/visuals_manifest.json` |

### Manifest Format

```json
[
  {
    "block_index": 0,
    "visual_type": "stock_footage",
    "source": "pexels",
    "file": "visuals/block_000.mp4",
    "query": "developer typing code",
    "url": "https://www.pexels.com/video/..."
  },
  {
    "block_index": 1,
    "visual_type": "ai_generated",
    "source": "replicate_flux",
    "file": "visuals/block_001.png",
    "prompt": "Futuristic code editor, cinematic"
  }
]
```

---

## Cost Per Video

| Item | Count | Unit Cost | Total |
|------|-------|-----------|-------|
| Pexels API calls | ~30-50 | Free | $0.00 |
| Pixabay API calls | ~10-20 | Free | $0.00 |
| Flux AI images | ~5-10 | $0.02 | $0.10-0.20 |
| **Total** | | | **$0.10-0.20** |

---

## Edge Cases

- **No results for query**: Tries simplified query (fewer words), then falls back to photos
- **Download fails**: Retries once, then marks block as missing in manifest
- **API rate limits**: 0.5s delay between API calls; Pexels allows 200 req/hr, Pixabay 100 req/hr
- **Large video files**: Downloads up to 1080p; skips 4K to save space
- **Replicate timeout**: Flux-schnell typically returns in 2-5 seconds; 30s timeout configured

---

## Environment Variables

```
PEXELS_API_KEY=            # Required for stock footage
PIXABAY_API_KEY=           # Optional fallback
REPLICATE_API_TOKEN=       # Required for AI images
```
