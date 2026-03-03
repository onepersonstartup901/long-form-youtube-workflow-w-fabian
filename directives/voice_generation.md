# Voice Generation

Generate natural-sounding narration from script text using ElevenLabs TTS, with word-level timestamps for caption sync.

## Execution Script

`execution/generate_voice.py`

---

## Quick Start

```bash
# Generate voice from parsed script
python3 execution/generate_voice.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/

# Use a specific voice
python3 execution/generate_voice.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/ \
  --voice-id "pNInz6obpgDQGcFmaJgB"

# Adjust voice parameters
python3 execution/generate_voice.py \
  .tmp/{vid}/parsed_script.json \
  -o .tmp/{vid}/ \
  --stability 0.6 --similarity-boost 0.8
```

---

## What It Does

1. **Loads parsed script** — Reads `parsed_script.json` (output of `parse_script.py`)
2. **Combines narration** — Joins all block narrations with sentence-break pauses
3. **Calls ElevenLabs API** — Single API call for natural pacing across the full script
4. **Extracts timestamps** — Character-level alignment → word-level timestamps
5. **Maps words to blocks** — Each word tagged with its source block index

---

## Voice Selection

| Voice | Style | Best For |
|-------|-------|----------|
| `pNInz6obpgDQGcFmaJgB` (Adam) | Deep, authoritative | Tech explainers |
| `ErXwobaYiN019PkySvjV` (Antoni) | Warm, engaging | Tutorials |
| `EXAVITQu4vr4xnSDxMaL` (Bella) | Clear, professional | News/updates |

Set via `ELEVENLABS_VOICE_ID` in `.env` or `--voice-id` flag.

---

## Voice Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `stability` | 0.5 | 0.0-1.0 | Higher = more consistent, lower = more expressive |
| `similarity_boost` | 0.75 | 0.0-1.0 | Higher = closer to original voice |
| `model` | `eleven_multilingual_v2` | — | Best quality model |

**Recommended for faceless content:** `stability=0.5, similarity_boost=0.75` — natural variation without being erratic.

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Narration audio | MP3 | `.tmp/{vid}/narration.mp3` |
| Word timestamps | JSON | `.tmp/{vid}/word_timestamps.json` |

### Word Timestamps Format

```json
[
  {"word": "Every", "start": 0.0, "end": 0.25, "block_index": 0},
  {"word": "few", "start": 0.25, "end": 0.42, "block_index": 0},
  ...
]
```

Each entry includes the `block_index` mapping the word back to its source script block.

---

## Cost Management

| Plan | Monthly | Characters | Per Video (~12 min) |
|------|---------|------------|---------------------|
| Starter | $5 | 30K | ~2 videos |
| Creator | $22 | 100K | ~6 videos |
| Scale | $99 | 500K | ~30 videos |
| Business | $330 | 2M | ~120 videos |

**For daily production:** Scale plan ($99/mo) gives ~30 videos/month at ~$3.30/video.

A 12-minute video uses approximately 15,000-18,000 characters.

---

## Edge Cases

- **API returns no timestamps**: Falls back to estimated timestamps based on audio duration and word count (uniform distribution)
- **Very long scripts (>20 min)**: May need to split into chunks; current implementation uses single API call
- **Special characters**: Stripped from narration before TTS to avoid pronunciation issues
- **Rate limits**: ElevenLabs allows ~100 requests/hour on Scale plan

---

## Environment Variables

```
ELEVENLABS_API_KEY=         # Required
ELEVENLABS_VOICE_ID=        # Optional (default: env or Adam voice)
```
