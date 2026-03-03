# YouTube Longform Video Pipeline

Automated pipeline that produces daily 8-15 minute faceless YouTube videos in the Tech/AI niche.

## Architecture

```
Layer 1 (Directives): This file + stage-specific SOPs in directives/
Layer 2 (Orchestration): AI reads directives, calls execution scripts
Layer 3 (Execution): Python scripts in execution/ + Remotion rendering
```

## Pipeline Stages

```
[1] Research         → outline.md
[2] Scripting        → script.md, parsed_script.json
    ── GATE 1: Script approval via Telegram ──
[3] Voice Generation → narration.mp3, word_timestamps.json
[4] Visual Gathering → visuals/, visuals_manifest.json
[5] Caption Gen      → captions.srt, captions.json
[6] Video Assembly   → assembled.mp4 (Remotion render)
[7] Post-Production  → final.mp4 (audio enhanced)
    ── GATE 2: Video review via Telegram ──
[8] Metadata Gen     → metadata.json
[9] YouTube Upload   → published
```

## Quick Start

### Create and run a video end-to-end (with gate skipping for testing):
```bash
python execution/pipeline_orchestrator.py \
    --new "5 AI Tools That Will Replace Your Entire Tech Stack" \
    --run-all --skip-gates
```

### Step by step:
```bash
# Create a new video
python execution/pipeline_orchestrator.py --new "Your Topic Here"

# Advance one stage
python execution/pipeline_orchestrator.py --video 20260303_your_topic --advance

# List all videos
python execution/pipeline_orchestrator.py --list
```

### Individual scripts:
```bash
# Research + outline
python execution/topic_research.py --outline "Your Topic" --niche "tech/AI"

# Generate faceless script
python execution/generate_script.py --topic "Your Topic" --style faceless --length 12

# Parse script
python execution/parse_script.py .tmp/{vid}/script.md -o .tmp/{vid}/parsed_script.json

# Generate voice
python execution/generate_voice.py .tmp/{vid}/parsed_script.json -o .tmp/{vid}/

# Gather visuals
python execution/gather_visuals.py .tmp/{vid}/parsed_script.json -o .tmp/{vid}/

# Generate captions
python execution/generate_captions.py .tmp/{vid}/word_timestamps.json -o .tmp/{vid}/

# Assemble video
python execution/assemble_video.py --video-id {vid} --tmp-dir .tmp/{vid}/

# Audio enhancement
python execution/enhance_audio.py .tmp/{vid}/assembled.mp4 .tmp/{vid}/final.mp4

# Generate metadata
python execution/generate_metadata.py --script .tmp/{vid}/script.md --niche "tech/AI"

# Upload to YouTube
python execution/youtube_upload.py --video .tmp/{vid}/final.mp4 --metadata .tmp/{vid}/metadata.json
```

## Approval Gates

Gates use Telegram bot notifications + JSON response files.

### Approve a gate:
```bash
echo '{"decision": "approved"}' > .tmp/{video_id}/gate_response.json
```

### Reject with feedback:
```bash
echo '{"decision": "rejected", "reason": "Script too generic, add more specific examples"}' > .tmp/{video_id}/gate_response.json
```

### Telegram bot commands:
```bash
# Send gate notification
python execution/telegram_bot.py --notify-gate1 {video_id}
python execution/telegram_bot.py --notify-gate2 {video_id}

# Send status
python execution/telegram_bot.py --status
```

## Video ID Convention

`{YYYYMMDD}_{slug}` — e.g., `20260303_ai_code_editors`

All intermediate files live in `.tmp/{video_id}/`.

## Cost Per Video (~$3.50-4.00)

| Component | Cost |
|-----------|------|
| ElevenLabs TTS | ~$3.00 |
| Claude API (script) | ~$0.30-0.50 |
| Flux AI images | ~$0.10-0.20 |
| Stock footage (Pexels/Pixabay) | Free |
| YouTube API | Free |

## Environment Variables Required

```
ANTHROPIC_API_KEY          # Script generation
ELEVENLABS_API_KEY         # Voice generation
ELEVENLABS_VOICE_ID        # ElevenLabs voice
PEXELS_API_KEY             # Stock footage
PIXABAY_API_KEY            # Stock footage (backup)
REPLICATE_API_TOKEN        # AI image generation (Flux)
TELEGRAM_BOT_TOKEN         # Notifications
TELEGRAM_APPROVER_CHAT_ID  # Approval messages
PIPELINE_SHEET_ID          # Google Sheet production tracker (optional)
```

## Google Sheet Tracker

The pipeline automatically syncs every state change to a Google Sheet when `PIPELINE_SHEET_ID` is set. See `directives/sheet_tracker.md` for setup instructions.

Three tabs: **Pipeline** (video status dashboard), **Content Calendar** (publish planning), **Cost Tracker** (per-video spend). If the env var is not set, tracking is silently skipped.

## Dependencies

### Python
```bash
pip install anthropic elevenlabs httpx python-dotenv replicate Pillow
pip install google-api-python-client google-auth-oauthlib
```

### System
```bash
brew install ffmpeg
```

### Remotion
```bash
cd execution/remotion_video && npm install
```

## Script Format (Faceless)

Scripts use structured VISUAL+NARRATION blocks:

```markdown
# Video Title

## HOOK (0:00 - 0:30)

---
VISUAL_TYPE: stock_footage
VISUAL_QUERY: "developer typing code"
NARRATION: "Opening hook sentence."
---
VISUAL_TYPE: ai_generated
VISUAL_PROMPT: "Futuristic code editor, cinematic"
NARRATION: "Second hook sentence."
CAPTION_EMPHASIS: ["key phrase"]
---
```

Each `---` block becomes a Remotion segment with matched visual + narration + captions.
