# End-to-End Integration Test Guide

Step-by-step instructions to run the full pipeline from a topic to a rendered video.

---

## Prerequisites

### 1. System Dependencies

```bash
# ffmpeg (required for audio duration detection + post-production)
brew install ffmpeg

# Node.js 18+ (required for Remotion rendering)
node --version  # should be >= 18

# Python 3.11+ (3.14 has known issues with replicate package)
python3 --version
```

### 2. Install Python Dependencies

```bash
cd "/Users/ai-sandpit/Desktop/Command HUB/Projects/Youtube Longform Worflow"

# Install all required packages
pip install anthropic elevenlabs httpx python-dotenv
```

### 3. Install Remotion Dependencies

```bash
cd execution/remotion_video
npm install
cd ../..
```

### 4. API Keys Setup

Add these to your `.env` file in the project root:

```env
# === REQUIRED for pipeline ===

# Anthropic (script generation + metadata)
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs (voice generation)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...          # Find at: https://elevenlabs.io/voice-lab

# === REQUIRED for visuals (at least one) ===

# Pexels (free stock footage — recommended, get key at https://www.pexels.com/api/)
PEXELS_API_KEY=...

# Pixabay (free stock footage — backup, get key at https://pixabay.com/api/docs/)
PIXABAY_API_KEY=...

# === OPTIONAL ===

# Replicate (AI-generated images via Flux — $0.02/image)
REPLICATE_API_TOKEN=...

# Telegram (approval notifications — not needed for --skip-gates testing)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_APPROVER_CHAT_ID=...

# Google Sheets (production tracker — Phase 2)
PIPELINE_SHEET_ID=...
```

**Minimum keys needed for a test run:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, and at least one of `PEXELS_API_KEY` or `PIXABAY_API_KEY`.

---

## Quick Test (Full Pipeline, Skip Gates)

This runs all stages end-to-end, skipping human approval gates:

```bash
python execution/pipeline_orchestrator.py \
  --new "5 AI Tools Replacing Your Tech Stack in 2026" \
  --run-all \
  --skip-gates
```

**Expected output:**
```
Created video: 20260303_5_ai_tools_replacing_your_tech_stack_in
  Topic: 5 AI Tools Replacing Your Tech Stack in 2026
  Directory: .tmp/20260303_5_ai_tools_replacing_your_tech_stack_in

  Executing: research
  ...
  Executing: scripting
  ...
  Executing: voice
  ...
  Executing: visuals
  ...
  Executing: captions
  ...
  Executing: assembly
  ...
  PUBLISHED!
```

**Expected cost:** ~$3.50-4.00 (ElevenLabs TTS ~$3, Claude API ~$0.50, images ~$0.20)

**Expected time:** 15-25 minutes depending on API response times and render speed.

---

## Stage-by-Stage Test

If you want to verify each stage individually:

### Stage 1: Research

```bash
# Create a new video
python execution/pipeline_orchestrator.py --new "AI Code Editors Compared"

# Check it was created
python execution/pipeline_orchestrator.py --list

# Advance one stage (research)
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:** Check `.tmp/20260303_ai_code_editors_compared/research.md` exists.

### Stage 2: Scripting

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:** Check `.tmp/20260303_ai_code_editors_compared/script.md` exists and contains `VISUAL_TYPE:` + `NARRATION:` blocks.

### Stage 3: Gate 1 (Script Approval)

Without `--skip-gates`, the pipeline pauses here. To approve:

```bash
# Check status (should say gate1_pending)
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared

# Option A: Skip the gate
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance --skip-gates

# Option B: Manual approval
echo '{"decision": "approved"}' > .tmp/20260303_ai_code_editors_compared/gate_response.json
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance

# Option C: Reject with feedback (loops back to scripting)
echo '{"decision": "rejected", "reason": "Make it more engaging"}' > .tmp/20260303_ai_code_editors_compared/gate_response.json
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

### Stage 4: Voice Generation

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:**
- `.tmp/20260303_ai_code_editors_compared/narration.mp3` — play it, should sound natural
- `.tmp/20260303_ai_code_editors_compared/word_timestamps.json` — word-level timing data

### Stage 5: Visual Gathering

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:** `.tmp/20260303_ai_code_editors_compared/visuals/` directory should contain downloaded images/videos.

### Stage 6: Caption Generation

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:**
- `.tmp/20260303_ai_code_editors_compared/captions.srt` — standard subtitle file
- `.tmp/20260303_ai_code_editors_compared/captions_remotion.json` — Remotion caption data with frame numbers

### Stage 7: Assembly (Remotion Render)

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:** `.tmp/20260303_ai_code_editors_compared/assembled.mp4` — should be a playable video.

**This is the longest stage** (5-15 min depending on video length and CPU).

### Stage 8: Post-Production

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance
```

**Verify:** `.tmp/20260303_ai_code_editors_compared/final.mp4` — enhanced audio, normalized loudness.

### Stage 9: Gate 2 (Video Approval)

Same approval mechanism as Gate 1. Use `--skip-gates` or create `gate_response.json`.

### Stage 10: Metadata Generation

```bash
python execution/pipeline_orchestrator.py --video 20260303_ai_code_editors_compared --advance --skip-gates
```

**Verify:** `.tmp/20260303_ai_code_editors_compared/metadata.json` — YouTube title, description, tags.

---

## Running Individual Scripts

You can also test scripts standalone:

```bash
# Parse a script
python execution/parse_script.py .tmp/{video_id}/script.md --validate -o .tmp/{video_id}/parsed_script.json

# Generate voice (needs ELEVENLABS keys)
python execution/generate_voice.py .tmp/{video_id}/parsed_script.json -o .tmp/{video_id}/

# Gather visuals (needs PEXELS or PIXABAY key)
python execution/gather_visuals.py .tmp/{video_id}/parsed_script.json -o .tmp/{video_id}/visuals/

# Generate captions
python execution/generate_captions.py .tmp/{video_id}/word_timestamps.json -o .tmp/{video_id}/

# Assemble video (needs Remotion deps installed)
python execution/assemble_video.py .tmp/{video_id}/ -o .tmp/{video_id}/assembled.mp4
```

---

## Troubleshooting

### "ELEVENLABS_API_KEY not set"
Add your ElevenLabs API key to `.env`. Get one at https://elevenlabs.io/

### "ffprobe not found"
Install ffmpeg: `brew install ffmpeg`

### "Cannot find module 'remotion'"
Run `cd execution/remotion_video && npm install`

### Remotion render fails with "staticFile: file not found"
Visual assets weren't downloaded properly. Check `.tmp/{video_id}/visuals/` has actual files and that `visuals_manifest.json` paths match.

### Voice generation costs too much
Use `eleven_turbo_v2_5` model instead of `eleven_multilingual_v2` for cheaper (~50% cost reduction, slightly lower quality). Set via `--model` flag.

### Pipeline stuck at "failed"
```bash
# Check what failed
python execution/pipeline_orchestrator.py --video {video_id}

# Retry from the failed stage
python execution/pipeline_orchestrator.py --video {video_id} --retry --run-all --skip-gates
```

### Want to start over
```bash
# Delete the video directory and recreate
rm -rf .tmp/{video_id}
python execution/pipeline_orchestrator.py --new "Your Topic" --run-all --skip-gates
```

---

## Verification Checklist

After a successful run, verify:

- [ ] `.tmp/{video_id}/state.json` shows `"status": "published"`
- [ ] `.tmp/{video_id}/final.mp4` is playable and 8-15 minutes
- [ ] Narration sounds natural (not robotic)
- [ ] Visuals change every 5-10 seconds (not static slideshow)
- [ ] Captions are synced with narration (no drift)
- [ ] `.tmp/{video_id}/captions.srt` can be imported into any video player
- [ ] Ken Burns / pan effects are visible on images
- [ ] Transitions between sections are smooth
- [ ] Audio is normalized (no sudden volume jumps)
