# Telegram Approvals & Notifications

Manage pipeline approval gates and receive status notifications via Telegram bot.

## Execution Script

`execution/telegram_bot.py`

---

## Quick Start

```bash
# Send Gate 1 notification (script review)
python3 execution/telegram_bot.py --notify-gate1 20260303_ai_tools

# Send Gate 2 notification (video review)
python3 execution/telegram_bot.py --notify-gate2 20260303_ai_tools

# Send pipeline status
python3 execution/telegram_bot.py --status

# Send custom message
python3 execution/telegram_bot.py --message "Pipeline maintenance in 10 minutes"
```

---

## Approval Gates

The pipeline has two human approval gates:

### Gate 1: Script Review (after scripting stage)

**What you receive:**
- Script preview (first 1500 characters) in Telegram message
- Full script as `.md` file attachment
- Video ID and topic

**To approve:**
```bash
echo '{"decision": "approved"}' > .tmp/{video_id}/gate_response.json
```

**To reject with feedback:**
```bash
echo '{"decision": "rejected", "reason": "Script too generic, add specific tool examples"}' > .tmp/{video_id}/gate_response.json
```

When rejected, the pipeline returns to the scripting stage with your feedback included as revision context.

### Gate 2: Final Video Review (after post-production)

**What you receive:**
- Video stats (duration, file size) in Telegram message
- Video file sent directly (if under 50MB)
- Video ID and topic

**To approve:**
```bash
echo '{"decision": "approved"}' > .tmp/{video_id}/gate_response.json
```

**To reject:**
```bash
echo '{"decision": "rejected", "reason": "Captions out of sync at 3:45"}' > .tmp/{video_id}/gate_response.json
```

When rejected, the pipeline returns to the assembly stage.

---

## Gate Response Format

```json
{
  "decision": "approved" | "rejected",
  "reason": "Optional feedback for rejections"
}
```

File location: `.tmp/{video_id}/gate_response.json`

The orchestrator polls for this file. Once found, it reads the decision and advances or reverts the pipeline.

---

## Notification Types

| Notification | Trigger | Content |
|-------------|---------|---------|
| Stage transition | Each pipeline stage | Video ID + stage name |
| Gate 1 (script) | Script ready | Preview + full script attachment |
| Gate 2 (video) | Video ready | Stats + video file |
| Pipeline status | On demand | All active/pending/published videos |
| Error alert | Stage failure | Error details + video ID |

---

## Pipeline Status Summary

The `--status` command sends a summary showing:
- **Active** videos with current stage
- **Awaiting Approval** videos at gates
- **Published** count
- **Failed** videos with error details

---

## Skipping Gates (Testing)

For development and testing, gates can be skipped:

```bash
# Run entire pipeline without approval gates
python3 execution/pipeline_orchestrator.py \
  --new "Test Topic" \
  --run-all --skip-gates
```

This auto-creates `gate_response.json` with `{"decision": "approved"}` at each gate.

---

## Bot Setup

1. Create bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
3. Set environment variables:

```
TELEGRAM_BOT_TOKEN=         # From BotFather
TELEGRAM_APPROVER_CHAT_ID=  # Your chat ID or group ID
```

The bot uses the Telegram HTTP API directly (via httpx), no polling/webhook server required.

---

## Edge Cases

- **Bot token missing**: Notifications are silently skipped (logged to console)
- **Video too large for Telegram**: Sends size info + file path instead of video
- **Multiple pending gates**: Each video has its own gate_response.json
- **Rapid approvals**: Orchestrator processes one stage at a time per video
