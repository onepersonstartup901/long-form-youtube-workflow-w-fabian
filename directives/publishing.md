# Publishing & Upload

Upload finished videos to YouTube with metadata, scheduling, and post-publish optimization.

## Execution Script

`execution/youtube_upload.py`

---

## Quick Start

```bash
# Upload with metadata
python3 execution/youtube_upload.py \
  --video .tmp/exports/final_video.mp4 \
  --metadata .tmp/metadata/video_slug.json \
  --thumbnail .tmp/thumbnails/thumbnail.png

# Schedule for later
python3 execution/youtube_upload.py \
  --video .tmp/exports/final_video.mp4 \
  --metadata .tmp/metadata/video_slug.json \
  --schedule "2026-03-10T14:00:00Z"

# Upload as unlisted (for review)
python3 execution/youtube_upload.py \
  --video .tmp/exports/final_video.mp4 \
  --metadata .tmp/metadata/video_slug.json \
  --visibility unlisted
```

---

## What It Does

1. **Authenticates** with YouTube Data API v3 (OAuth2)
2. **Uploads** the video file with resumable upload
3. **Sets metadata** — title, description, tags, category, language
4. **Uploads thumbnail** — Custom thumbnail image
5. **Schedules** — Set publish time or publish immediately
6. **Adds to playlist** — If specified
7. **Sets end screen** — Configures end screen elements
8. **Logs result** — Records video ID, URL, upload status

---

## Pre-Upload Checklist

- [ ] Video exported in correct format (H.264, 1080p+)
- [ ] Metadata JSON generated (`generate_metadata.py`)
- [ ] Thumbnail image ready (1280x720, <2MB)
- [ ] Description includes timestamps
- [ ] Tags populated (30-50)
- [ ] Category selected
- [ ] Cards/end screens planned

---

## Publishing Strategy

### Best Upload Times (General)
| Day | Best Time (UTC) | Notes |
|-----|----------------|-------|
| Tuesday | 14:00-16:00 | Strong for educational |
| Thursday | 14:00-16:00 | High engagement day |
| Saturday | 09:00-11:00 | Weekend viewers |

*Adjust based on your audience's timezone and analytics.*

### Visibility Options
| Setting | Use case |
|---------|----------|
| `public` | Standard publish, immediately visible |
| `unlisted` | For review before going public |
| `private` | Internal only, draft review |
| `scheduled` | Set publish time in advance |

---

## Post-Publish Actions

1. **First 30 minutes**: Share to social media, communities, newsletter
2. **First hour**: Reply to every comment
3. **First 24 hours**: Monitor analytics (CTR, AVD, impressions)
4. **Day 2-3**: Add cards if promoting related content
5. **Week 1**: Evaluate performance, update description if needed

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Upload result | JSON | `.tmp/uploads/{slug}_result.json` |
| Video URL | String | Logged to console |
| Content log | Appended | `data/content_log.json` |

---

## YouTube API Quotas

- **Daily quota**: 10,000 units
- **Upload cost**: ~1,600 units per video
- **Metadata update**: ~50 units
- **Practical limit**: ~6 uploads per day

---

## Edge Cases

- **Upload fails mid-way**: Script uses resumable upload, will retry automatically
- **Quota exceeded**: Wait until midnight Pacific time for reset
- **Thumbnail rejected**: Must be JPG/PNG, under 2MB, 1280x720 minimum
- **Duplicate title**: YouTube allows it, but avoid for SEO clarity
