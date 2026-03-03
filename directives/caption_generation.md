# Caption Generation

Generate word-by-word animated captions for Remotion rendering and standard SRT subtitle files from word timestamps.

## Execution Script

`execution/generate_captions.py`

---

## Quick Start

```bash
# Generate captions from word timestamps
python3 execution/generate_captions.py \
  .tmp/{vid}/word_timestamps.json \
  -o .tmp/{vid}/

# Custom grouping
python3 execution/generate_captions.py \
  .tmp/{vid}/word_timestamps.json \
  -o .tmp/{vid}/ \
  --max-words 3 --max-duration 2.5

# With emphasis words from parsed script
python3 execution/generate_captions.py \
  .tmp/{vid}/word_timestamps.json \
  -o .tmp/{vid}/ \
  --parsed-script .tmp/{vid}/parsed_script.json
```

---

## What It Does

1. **Groups words** — Combines word timestamps into readable caption groups (max 4 words, max 3s per group)
2. **Breaks on punctuation** — Sentence-ending punctuation (. ! ?) forces a group break
3. **Generates SRT** — Standard subtitle file for YouTube upload (auto-captions backup)
4. **Generates Remotion JSON** — Frame-based timing with per-word highlight flags for animated rendering

---

## Caption Styles

The Remotion `AnimatedCaption` component renders word-by-word animated captions:

- **Active word**: Scaled up (1.2x), highlighted in accent color (`#00ff88`)
- **Inactive words**: Normal size, white text
- **Background**: Semi-transparent dark bar behind text
- **Position**: Bottom-center of video frame
- **Font**: Inter Bold, 52px (configured in `theme.ts`)

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| SRT subtitles | SRT | `.tmp/{vid}/captions.srt` |
| Remotion captions | JSON | `.tmp/{vid}/captions.json` |

### SRT Format

```srt
1
00:00:00,000 --> 00:00:01,200
Every few years a

2
00:00:01,200 --> 00:00:02,800
technology comes along that
```

### Remotion JSON Format

```json
[
  {
    "text": "Every few years a",
    "startFrame": 0,
    "endFrame": 36,
    "words": [
      {"word": "Every", "startFrame": 0, "endFrame": 8, "highlight": false},
      {"word": "few", "startFrame": 8, "endFrame": 14, "highlight": false},
      {"word": "years", "startFrame": 14, "endFrame": 22, "highlight": false},
      {"word": "a", "startFrame": 22, "endFrame": 36, "highlight": false}
    ]
  }
]
```

---

## Grouping Rules

| Rule | Default | Description |
|------|---------|-------------|
| Max words per group | 4 | Keeps captions readable |
| Max duration | 3.0s | Prevents stale captions |
| Punctuation break | Enabled | `. ! ?` force new group |
| FPS | 30 | Frame calculation base |

---

## Emphasis / Highlighting

Words listed in `CAPTION_EMPHASIS` fields of the parsed script get `"highlight": true` in the Remotion JSON. The `AnimatedCaption` component renders these in the accent color for visual emphasis.

Example: If script block has `CAPTION_EMPHASIS: ["AI code editors"]`, the words "AI", "code", and "editors" will be highlighted when they appear as the active word.

---

## Edge Cases

- **Single-word groups**: Allowed; common for emphasized words after punctuation
- **Very long words**: Counted as one word regardless of length
- **Missing timestamps**: Words without timing data are skipped
- **Overlapping groups**: End of one group = start of next (no gaps)
