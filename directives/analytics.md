# Analytics & Feedback Loop

Track video performance, extract insights, and feed learnings back into the content pipeline for continuous improvement.

## Execution Script

`execution/fetch_analytics.py`

---

## Quick Start

```bash
# Fetch analytics for recent videos
python3 execution/fetch_analytics.py --days 30

# Analyze a specific video
python3 execution/fetch_analytics.py --video-id "dQw4w9WgXcQ"

# Generate performance report
python3 execution/fetch_analytics.py --report --output .tmp/reports/monthly.md
```

---

## Key Metrics

### Primary (Growth)
| Metric | Target | Why it matters |
|--------|--------|----------------|
| **CTR** (Click-Through Rate) | >5% | Are people clicking your thumbnails? |
| **AVD** (Average View Duration) | >50% of video | Are people watching? |
| **Impressions** | Growing month-over-month | Is YouTube showing your content? |

### Secondary (Engagement)
| Metric | Target | Why it matters |
|--------|--------|----------------|
| **Likes/Dislikes ratio** | >95% likes | Audience sentiment |
| **Comments** | Growing | Community engagement |
| **Subscribers gained** | Positive per video | Converting viewers |
| **Shares** | Any | Organic distribution |

### Diagnostic
| Metric | What it tells you |
|--------|-------------------|
| **Traffic sources** | Where viewers find you (search vs browse vs suggested) |
| **Audience retention curve** | Where viewers drop off |
| **End screen CTR** | Are viewers clicking to next video? |
| **Returning viewers %** | Are you building an audience? |

---

## Feedback Loop

After every video:

1. **Collect data** (after 7 days of data accumulation)
2. **Compare to averages** — Is this video above or below your baseline?
3. **Identify patterns**:
   - High CTR + Low AVD = Clickbait title, content didn't deliver
   - Low CTR + High AVD = Great content, bad packaging
   - High everything = Double down on this format/topic
   - Low everything = Pivot away from this type of content
4. **Update ideation** — Feed insights back into topic research
5. **Log learnings** — Update `data/content_learnings.md`

---

## Reporting Schedule

| Report | Frequency | What to review |
|--------|-----------|----------------|
| Video check-in | 48 hours post-publish | CTR, early retention |
| Video report | 7 days post-publish | Full metrics snapshot |
| Monthly report | End of month | Trends, top/bottom performers |
| Quarterly review | End of quarter | Strategy adjustments |

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Video analytics | JSON | `.tmp/analytics/{video_id}.json` |
| Performance report | Markdown | `.tmp/reports/{period}.md` |
| Content learnings | Markdown (append) | `data/content_learnings.md` |
| Metrics snapshot | JSON | `data/analytics_snapshots/` |
