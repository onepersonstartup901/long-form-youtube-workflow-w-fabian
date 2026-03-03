# Recording

Guidelines and workflow for recording longform video content. Covers setup, recording flow, and integration with the editing pipeline.

## Related Tools

- `execution/jump_cut_vad_singlepass.py` — Silence removal (post-recording)
- `directives/jump_cut_vad.md` — Full VAD editing documentation

---

## Pre-Recording Checklist

### Equipment
- [ ] Camera charged and set to correct resolution/FPS
- [ ] Microphone connected and levels checked (-12dB to -6dB peaks)
- [ ] Lighting setup (key, fill, back)
- [ ] Teleprompter loaded with script (if using)
- [ ] B-roll equipment ready (screen recorder, second camera)

### Environment
- [ ] Quiet room, no echo
- [ ] Background clean and on-brand
- [ ] Phone on silent, notifications off
- [ ] "Recording in progress" sign up (if shared space)

### Files
- [ ] Script/outline accessible
- [ ] Shot list printed or on second screen
- [ ] Storage has enough space (estimate: 1GB per 10 min at 1080p)

---

## Recording Flow

### 1. Slate
Start each recording session with a quick slate:
- Say the video title
- Clap once (for audio sync if multi-cam)
- This helps identify files later

### 2. Record in Segments
- Follow the script structure (hook, context, segments, CTA)
- **Mistakes**: Say "cut cut" clearly, pause 2 seconds, redo from the last clean sentence
  - The VAD editor will automatically detect and remove the mistake segment
- **Natural pauses**: Don't worry about them — the VAD editor cuts silences > 0.5s
- **Energy check**: Every 10 minutes, reset energy. Stand up, take a breath, sit back down.

### 3. B-Roll Capture
- Record screen demos, product shots, or cutaway footage separately
- Name files clearly: `broll_screenrecording_section3.mp4`
- Store in `.tmp/broll/`

### 4. Wrap
- Review the last 30 seconds to make sure recording was clean
- Back up raw files immediately
- Note any issues (audio problems, lighting changes, mistakes to watch for)

---

## Recording Settings

### Recommended
| Setting | Value | Why |
|---------|-------|-----|
| Resolution | 1080p or 4K | 1080p is fine for talking head, 4K for B-roll |
| FPS | 30 | Standard for YouTube longform |
| Audio | 48kHz, 16-bit | Professional standard |
| Format | MP4 (H.264/H.265) | Universal compatibility |
| Bitrate | 20-50 Mbps | High enough for clean VAD processing |

### File Naming
```
raw_{date}_{slug}_take{n}.mp4
```
Example: `raw_20260303_how_to_build_saas_take1.mp4`

---

## Post-Recording

1. **Move raw files** to `.tmp/raw/`
2. **Run jump cut editor** to remove silences:
   ```bash
   python3 execution/jump_cut_vad_singlepass.py \
     .tmp/raw/raw_file.mp4 \
     .tmp/edited/edited_file.mp4 \
     --min-silence 0.5 --padding 100
   ```
3. **Review edited output** — check for awkward cuts, fix parameters if needed
4. **Proceed to full editing** (transitions, B-roll, audio enhancement)

---

## Edge Cases

- **Multiple takes**: Use the "cut cut" restart method. Don't stop/start recording unless necessary.
- **Audio issues mid-recording**: Stop, fix, re-record from the last section header.
- **Lost energy**: Take a 5-minute break. Don't push through — viewers can tell.
- **Teleprompter reading sounds robotic**: Switch to bullet outline, speak from memory.
