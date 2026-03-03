# Google Sheet Production Tracker

Keeps the Google Sheet in sync with the pipeline so you always have a live dashboard of every video's status, content calendar, and running costs.

## Execution Script

`execution/sheet_tracker.py`

---

## Setup

### 1. Create the Google Sheet

Create a new Google Sheet (or use an existing one). It needs three tabs with these exact names and header rows:

**Tab: Pipeline**
| video_id | topic | status | created_at | script_approved_at | video_approved_at | published_at | youtube_url | duration_mins | cost_total | cost_breakdown | error_log | notes |

**Tab: Content Calendar**
| publish_date | video_id | topic | niche | trending_score | status | source |

**Tab: Cost Tracker**
| date | video_id | category | amount | service |

> If a tab is missing when the script runs, it will be auto-created with the correct headers.

### 2. Set the environment variable

Add to `.env`:

```
PIPELINE_SHEET_ID=<your-sheet-id-here>
```

The Sheet ID is the long string in the URL between `/d/` and `/edit`:
```
https://docs.google.com/spreadsheets/d/THIS_PART_IS_THE_ID/edit
```

### 3. Ensure OAuth credentials exist

The tracker reuses the same `credentials.json` / `token.json` OAuth flow as the other Sheet scripts. If you can already run `read_sheet.py` or `append_to_sheet.py`, you're good.

---

## Usage

### Automatic (via pipeline orchestrator)

The pipeline orchestrator calls `sync_video_to_sheet()` automatically after every state change. No manual action required. If `PIPELINE_SHEET_ID` is not set, the sync is silently skipped.

### Manual CLI

```bash
# Sync a video's state to the Pipeline tab
python execution/sheet_tracker.py sync \
    --video-id 20260303_ai_code_editors \
    --state-json .tmp/20260303_ai_code_editors/state.json

# Log a cost entry
python execution/sheet_tracker.py log-cost \
    --video-id 20260303_ai_code_editors \
    --category tts \
    --amount 2.85 \
    --service ElevenLabs

# Read all Pipeline rows
python execution/sheet_tracker.py status

# Upsert a Content Calendar entry
python execution/sheet_tracker.py calendar \
    --video-id 20260303_ai_code_editors \
    --publish-date 2026-03-05 \
    --topic "AI Code Editors Compared" \
    --niche "tech/AI"
```

### From other Python scripts

```python
from sheet_tracker import sync_video_to_sheet, log_cost, update_calendar, get_pipeline_status

# After any state change
sync_video_to_sheet(video_id, state_dict)

# After a paid API call
log_cost(video_id, "tts", 2.85, "ElevenLabs")
log_cost(video_id, "claude", 0.42, "Anthropic")
log_cost(video_id, "images", 0.15, "Replicate")

# Read the full pipeline
rows = get_pipeline_status()

# Plan a publish date
update_calendar(video_id, "2026-03-05", "AI Code Editors", niche="tech/AI")
```

---

## Functions

| Function | Purpose | Tab |
|----------|---------|-----|
| `sync_video_to_sheet(video_id, state)` | Upsert video row | Pipeline |
| `log_cost(video_id, category, amount, service)` | Append cost entry | Cost Tracker |
| `get_pipeline_status()` | Read all rows | Pipeline |
| `update_calendar(video_id, publish_date, topic, ...)` | Upsert calendar row | Content Calendar |

---

## Error Handling

- If `PIPELINE_SHEET_ID` is not set, all functions return silently (no crash, no log).
- If the Sheet API call fails (auth error, network, quota), the error is logged but **never raised**. The pipeline continues running.
- Tab auto-creation: if a tab doesn't exist, it is created with the correct headers on first access.

---

## Cost Categories

| Category | Used for |
|----------|----------|
| `tts` | ElevenLabs voice generation |
| `claude` | Anthropic API (script, metadata, research) |
| `images` | Replicate / Flux AI image generation |
| `other` | Stock footage fees, misc |

---

## Lessons Learned

- Keep this section updated as issues arise.
- _No issues recorded yet._
