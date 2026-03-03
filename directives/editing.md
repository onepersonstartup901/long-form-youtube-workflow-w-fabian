# Video Editing Pipeline

End-to-end editing workflow from raw footage to export-ready video. Combines automated tools (VAD, audio enhancement) with manual editing guidance.

## Execution Scripts

- `execution/jump_cut_vad_singlepass.py` — Automated silence removal
- `execution/insert_3d_transition.py` — 3D transitions between segments
- `execution/enhance_audio.py` — Audio enhancement chain
- `execution/export_final.py` — Final export with encoding settings

---

## Editing Pipeline

### Phase 1: Rough Cut (Automated)

```bash
# 1. Remove silences and "cut cut" restarts
python3 execution/jump_cut_vad_singlepass.py \
  .tmp/raw/recording.mp4 \
  .tmp/edited/rough_cut.mp4 \
  --min-silence 0.5 --padding 100

# 2. Apply audio enhancement
python3 execution/enhance_audio.py \
  .tmp/edited/rough_cut.mp4 \
  .tmp/edited/rough_cut_enhanced.mp4
```

### Phase 2: Assembly Edit (Manual/Assisted)
- Import rough cut into editor (DaVinci Resolve, Premiere, CapCut)
- Add B-roll at marked `[B-ROLL]` points from script
- Add lower thirds, text overlays
- Add background music (low volume, -20dB under voice)

### Phase 3: Fine Cut
- Tighten pacing — cut any segments that drag
- Add transitions between major sections
- Color grade (or apply LUT)
- Add sound effects for emphasis

### Phase 4: Final Export

```bash
# Export with YouTube-optimized settings
python3 execution/export_final.py \
  .tmp/edited/final.mp4 \
  .tmp/exports/video_title.mp4 \
  --preset youtube_1080p
```

---

## Audio Enhancement Chain

Applied automatically by the enhance_audio script:

```
highpass=f=80            # Remove rumble below 80Hz
lowpass=f=12000          # Remove harsh highs
equalizer (200Hz, -1dB)  # Reduce muddiness
equalizer (3kHz, +2dB)   # Boost presence/clarity
acompressor (3:1)        # Gentle compression
loudnorm=I=-16           # YouTube loudness standard (-16 LUFS)
```

---

## Export Presets

| Preset | Resolution | Codec | Bitrate | Audio | Use Case |
|--------|-----------|-------|---------|-------|----------|
| `youtube_1080p` | 1920x1080 | H.264 | 10 Mbps | AAC 192k | Standard upload |
| `youtube_4k` | 3840x2160 | H.265 | 35 Mbps | AAC 320k | 4K upload |
| `draft` | 1280x720 | H.264 | 5 Mbps | AAC 128k | Quick review |

---

## File Flow

```
.tmp/raw/              → Raw recordings
.tmp/broll/            → B-roll clips
.tmp/edited/           → Work-in-progress edits
.tmp/exports/          → Final exported videos (ready to upload)
```

---

## Troubleshooting

### Cuts feel too aggressive
- Increase `--padding` to 150-200ms
- Increase `--min-silence` to 0.8s

### Audio levels inconsistent
- Run `enhance_audio.py` with loudnorm
- Check source recording levels

### Export file too large
- Use `youtube_1080p` preset (not 4K) unless 4K is necessary
- Check bitrate settings
