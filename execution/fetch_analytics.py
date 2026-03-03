#!/usr/bin/env python3
"""
YouTube Analytics Fetcher.

Fetches video performance data from YouTube Analytics API
and generates performance reports.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_youtube_credentials():
    """Get OAuth2 credentials for YouTube Analytics API."""
    creds = None
    token_path = "data/youtube_token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def fetch_video_stats(youtube, video_id: str) -> dict:
    """Fetch stats for a single video."""
    response = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=video_id,
    ).execute()

    if not response.get("items"):
        return None

    item = response["items"][0]
    stats = item["statistics"]

    return {
        "video_id": video_id,
        "title": item["snippet"]["title"],
        "published_at": item["snippet"]["publishedAt"],
        "duration": item["contentDetails"]["duration"],
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "fetched_at": datetime.now().isoformat(),
    }


def fetch_recent_videos(youtube, days: int = 30) -> list[dict]:
    """Fetch stats for videos published in the last N days."""
    after = (datetime.now() - timedelta(days=days)).isoformat() + "Z"

    response = youtube.search().list(
        part="id,snippet",
        forMine=True,
        type="video",
        order="date",
        publishedAfter=after,
        maxResults=50,
    ).execute()

    video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

    if not video_ids:
        print("No videos found in the specified period.")
        return []

    # Fetch detailed stats for each
    results = []
    for vid in video_ids:
        stats = fetch_video_stats(youtube, vid)
        if stats:
            results.append(stats)

    return results


def generate_report(videos: list[dict]) -> str:
    """Generate a markdown performance report."""
    if not videos:
        return "# Performance Report\n\nNo videos to analyze."

    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    total_comments = sum(v["comments"] for v in videos)
    avg_views = total_views / len(videos)

    report = f"""# YouTube Performance Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Summary
- **Videos analyzed**: {len(videos)}
- **Total views**: {total_views:,}
- **Average views/video**: {avg_views:,.0f}
- **Total likes**: {total_likes:,}
- **Total comments**: {total_comments:,}

## Video Performance

| # | Title | Views | Likes | Comments | Published |
|---|-------|-------|-------|----------|-----------|
"""

    # Sort by views descending
    for i, v in enumerate(sorted(videos, key=lambda x: x["views"], reverse=True)):
        pub_date = v["published_at"][:10]
        report += f"| {i+1} | {v['title'][:40]} | {v['views']:,} | {v['likes']:,} | {v['comments']:,} | {pub_date} |\n"

    # Top performer analysis
    if videos:
        top = max(videos, key=lambda x: x["views"])
        bottom = min(videos, key=lambda x: x["views"])

        report += f"""
## Insights

### Top Performer
- **{top['title']}** — {top['views']:,} views, {top['likes']:,} likes
- What worked? Analyze title, thumbnail, topic, and timing.

### Lowest Performer
- **{bottom['title']}** — {bottom['views']:,} views, {bottom['likes']:,} likes
- What to improve? Check CTR, retention, and topic fit.

## Action Items
- [ ] Review top performer — replicate what worked
- [ ] Review bottom performer — identify what to avoid
- [ ] Update content calendar based on insights
- [ ] A/B test thumbnail styles on next upload
"""

    return report


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube analytics")
    parser.add_argument("--days", type=int, default=30, help="Fetch videos from last N days")
    parser.add_argument("--video-id", help="Fetch stats for specific video")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--output", help="Output path for report")

    args = parser.parse_args()

    creds = get_youtube_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    os.makedirs(".tmp/analytics", exist_ok=True)
    os.makedirs(".tmp/reports", exist_ok=True)

    if args.video_id:
        print(f"Fetching stats for video: {args.video_id}")
        stats = fetch_video_stats(youtube, args.video_id)
        if stats:
            output_path = f".tmp/analytics/{args.video_id}.json"
            with open(output_path, "w") as f:
                json.dump(stats, f, indent=2)
            print(f"Stats saved to {output_path}")
            print(json.dumps(stats, indent=2))
        else:
            print("Video not found.")
        return

    print(f"Fetching videos from last {args.days} days...")
    videos = fetch_recent_videos(youtube, args.days)
    print(f"Found {len(videos)} videos")

    # Save raw data
    timestamp = datetime.now().strftime("%Y%m%d")
    data_path = f"data/analytics_snapshots/{timestamp}.json"
    os.makedirs("data/analytics_snapshots", exist_ok=True)
    with open(data_path, "w") as f:
        json.dump(videos, f, indent=2)
    print(f"Analytics snapshot saved to {data_path}")

    # Generate report
    if args.report:
        report = generate_report(videos)
        output_path = args.output or f".tmp/reports/{timestamp}.md"
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report saved to {output_path}")
        print(report)
    else:
        for v in videos:
            print(f"  {v['views']:>8,} views | {v['title'][:50]}")


if __name__ == "__main__":
    main()
