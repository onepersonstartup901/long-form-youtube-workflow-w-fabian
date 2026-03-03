# Video Assembly

Programmatically assemble narration, visuals, and captions into a rendered video using Remotion.

## Execution Script

`execution/assemble_video.py`

---

## Quick Start

```bash
# Assemble and render video
python3 execution/assemble_video.py \
  --video-id 20260303_ai_tools \
  --tmp-dir .tmp/20260303_ai_tools/

# Draft render (720p, faster)
python3 execution/assemble_video.py \
  --video-id 20260303_ai_tools \
  --tmp-dir .tmp/20260303_ai_tools/ \
  --draft

# Custom settings
python3 execution/assemble_video.py \
  --video-id 20260303_ai_tools \
  --tmp-dir .tmp/20260303_ai_tools/ \
  --title "Custom Title" \
  --channel "My Channel"
```

---

## What It Does

1. **Loads pipeline data** — `parsed_script.json`, `word_timestamps.json`, `visuals_manifest.json`, `captions.json`
2. **Copies assets** — Visual files → Remotion `public/{video_id}/` for `staticFile()` access
3. **Calculates timings** — Maps word timestamps to block durations, converts to frame counts at 30fps
4. **Builds segments** — Intro (3s) → narration blocks → outro (5s), with animation cycling
5. **Writes props JSON** — Full `AssemblyProps` object for Remotion composition
6. **Renders video** — `npx remotion render FullVideo` with props

---

## Remotion Project Structure

```
execution/remotion_video/
  src/
    Root.tsx              # Registers FullVideo composition
    FullVideo.tsx         # Main: Audio + Sequence per segment
    components/
      NarrationSegment    # Visual (KenBurns/video) + section title + captions
      AnimatedCaption     # Word-by-word animated text overlay
      KenBurns            # Pan/zoom on static images
      IntroSequence       # Animated title card
      OutroSequence       # Subscribe CTA
      TransitionSlide     # Fade between segments
    types.ts              # TypeScript interfaces
    theme.ts              # Brand styling (colors, fonts, sizes)
```

---

## Segment Types

| Type | Duration | Content |
|------|----------|---------|
| `intro` | 3 seconds (90 frames) | Title card with channel branding |
| `narration` | Variable (from timestamps) | Visual + narration + animated captions |
| `transition` | 0.5s (15 frames) | Fade between sections |
| `outro` | 5 seconds (150 frames) | Subscribe CTA + channel name |

---

## Visual Animations

Static images get Ken Burns effects to avoid a slideshow feel:

| Animation | Effect | Description |
|-----------|--------|-------------|
| `ken_burns_in` | 1x → 1.15x | Slow zoom in |
| `ken_burns_out` | 1.15x → 1x | Slow zoom out |
| `pan_left` | Right → center | Slow pan left |
| `pan_right` | Left → center | Slow pan right |
| `static` | No motion | Fallback |

Animations cycle automatically across blocks. Video files play at native speed.

---

## Render Settings

| Setting | Draft | Production |
|---------|-------|------------|
| Resolution | 1280x720 | 1920x1080 |
| FPS | 30 | 30 |
| Codec | H.264 | H.264 |
| Concurrency | 50% | 50% |
| CRF | — | 18 |

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Assembled video | MP4 | `.tmp/{vid}/assembled.mp4` |
| Debug props | JSON | `.tmp/{vid}/assembly_props.json` |

---

## Required Inputs

All must exist in `.tmp/{vid}/` before assembly:

| File | From Stage |
|------|------------|
| `parsed_script.json` | Scripting (parse_script.py) |
| `narration.mp3` | Voice Generation |
| `word_timestamps.json` | Voice Generation |
| `visuals_manifest.json` | Visual Gathering |
| `visuals/*.mp4` or `*.png` | Visual Gathering |
| `captions.json` | Caption Generation |

---

## Remotion Dependencies

```bash
cd execution/remotion_video && npm install
```

Required: Node.js 18+, npm. Remotion handles Chrome/Chromium for rendering.

---

## Troubleshooting

### Render fails with "composition not found"
- Run from project root, not from remotion_video/
- Check that `src/Root.tsx` registers `FullVideo`

### Assets not loading
- Verify files are copied to `execution/remotion_video/public/{video_id}/`
- Check paths in props JSON match actual file locations

### Slow render
- Use `--draft` for 720p preview
- Reduce concurrency if running out of memory
- Close other Chrome instances
