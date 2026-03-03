#!/usr/bin/env python3
"""
Google Sheet Production Tracker.

Wrapper module that syncs pipeline state to a Google Sheet with three tabs:
  - Pipeline:         One row per video, upserted on every state change
  - Content Calendar: Planned publish dates and topics
  - Cost Tracker:     Append-only log of per-video costs

The Sheet ID is read from env var PIPELINE_SHEET_ID.
If the var is not set, every function silently returns without error
so the rest of the pipeline keeps working.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google Sheets auth (mirrors pattern from read_sheet.py / append_to_sheet.py)
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Tab names (must match the Google Sheet)
TAB_PIPELINE = "Pipeline"
TAB_CALENDAR = "Content Calendar"
TAB_COSTS = "Cost Tracker"

# Expected headers for each tab.
# The Sheet must have these as row 1 in the respective tabs.
PIPELINE_HEADERS = [
    "video_id",
    "topic",
    "status",
    "created_at",
    "script_approved_at",
    "video_approved_at",
    "published_at",
    "youtube_url",
    "duration_mins",
    "cost_total",
    "cost_breakdown",
    "error_log",
    "notes",
]

CALENDAR_HEADERS = [
    "publish_date",
    "video_id",
    "topic",
    "niche",
    "trending_score",
    "status",
    "source",
]

COST_HEADERS = [
    "date",
    "video_id",
    "category",
    "amount",
    "service",
]


def _get_sheet_id() -> str | None:
    """Return the PIPELINE_SHEET_ID env var, or None if not configured."""
    sheet_id = os.getenv("PIPELINE_SHEET_ID", "").strip()
    return sheet_id if sheet_id else None


def _get_credentials():
    """
    Get OAuth2 credentials for Google Sheets API.
    Mirrors the auth flow used by append_to_sheet.py.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = None

    if os.path.exists("token.json"):
        try:
            with open("token.json", "r") as token:
                token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            logger.warning("Error loading token: %s", e)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def _get_spreadsheet():
    """Return a gspread Spreadsheet object, or None if unavailable."""
    import gspread

    sheet_id = _get_sheet_id()
    if not sheet_id:
        return None

    creds = _get_credentials()
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)


def _ensure_tab(spreadsheet, tab_name: str, headers: list[str]):
    """
    Return the worksheet for *tab_name*, creating it with *headers* if it
    does not exist yet.
    """
    try:
        ws = spreadsheet.worksheet(tab_name)
    except Exception:
        # Tab doesn't exist -- create it
        ws = spreadsheet.add_worksheet(title=tab_name, rows=500, cols=len(headers))
        ws.update(values=[headers], range_name="A1")
        logger.info("Created new tab '%s' with headers", tab_name)
    return ws


def _find_row_by_video_id(worksheet, video_id: str) -> int | None:
    """
    Return the 1-based row number where *video_id* appears in column A,
    or None if not found.
    """
    try:
        cell = worksheet.find(video_id, in_column=1)
        return cell.row if cell else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_video_to_sheet(video_id: str, state: dict) -> bool:
    """
    Upsert a row in the Pipeline tab.

    Reads relevant fields from *state* and writes them to the Sheet.
    If a row for *video_id* already exists it is updated in-place;
    otherwise a new row is appended.

    Returns True on success, False on any error (errors are logged, never raised).
    """
    if not _get_sheet_id():
        return True  # Silently skip -- no Sheet configured

    try:
        spreadsheet = _get_spreadsheet()
        if spreadsheet is None:
            return True

        ws = _ensure_tab(spreadsheet, TAB_PIPELINE, PIPELINE_HEADERS)

        # Build the row from state, matching PIPELINE_HEADERS order
        row = [
            state.get("video_id", video_id),
            state.get("topic", ""),
            state.get("status", ""),
            state.get("created_at", ""),
            state.get("gate1_pending_completed_at", state.get("script_approved_at", "")),
            state.get("gate2_pending_completed_at", state.get("video_approved_at", "")),
            state.get("published_at", ""),
            state.get("youtube_url", ""),
            state.get("duration_mins", ""),
            state.get("cost_total", ""),
            state.get("cost_breakdown", ""),
            state.get("error", state.get("error_log", "")),
            state.get("notes", ""),
        ]

        # Convert any non-string values to strings for the Sheet
        row = [str(v) if v is not None else "" for v in row]

        existing_row = _find_row_by_video_id(ws, video_id)
        if existing_row:
            # Update existing row
            end_col = chr(ord("A") + len(row) - 1)
            ws.update(
                values=[row],
                range_name=f"A{existing_row}:{end_col}{existing_row}",
                value_input_option="RAW",
            )
            logger.info("Updated Pipeline row %d for %s", existing_row, video_id)
        else:
            # Append new row
            ws.append_row(row, value_input_option="RAW")
            logger.info("Appended Pipeline row for %s", video_id)

        return True

    except Exception as e:
        logger.error("sync_video_to_sheet failed for %s: %s", video_id, e)
        return False


def log_cost(video_id: str, category: str, amount: float, service: str) -> bool:
    """
    Append a cost entry to the Cost Tracker tab.

    Args:
        video_id: The video identifier (e.g. 20260303_ai_code_editors)
        category: Cost category -- one of tts, claude, images, other
        amount:   Dollar amount
        service:  Service name (e.g. ElevenLabs, Anthropic, Replicate)

    Returns True on success, False on error.
    """
    if not _get_sheet_id():
        return True

    try:
        spreadsheet = _get_spreadsheet()
        if spreadsheet is None:
            return True

        ws = _ensure_tab(spreadsheet, TAB_COSTS, COST_HEADERS)

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            video_id,
            category,
            str(round(amount, 4)),
            service,
        ]

        ws.append_row(row, value_input_option="RAW")
        logger.info("Logged cost: %s %s $%s (%s)", video_id, category, amount, service)
        return True

    except Exception as e:
        logger.error("log_cost failed for %s: %s", video_id, e)
        return False


def get_pipeline_status() -> list[dict] | None:
    """
    Read all rows from the Pipeline tab and return them as a list of dicts
    keyed by the header names.

    Returns None if the Sheet is not configured or on error.
    """
    if not _get_sheet_id():
        return None

    try:
        spreadsheet = _get_spreadsheet()
        if spreadsheet is None:
            return None

        ws = _ensure_tab(spreadsheet, TAB_PIPELINE, PIPELINE_HEADERS)
        records = ws.get_all_records()
        logger.info("Read %d rows from Pipeline tab", len(records))
        return records

    except Exception as e:
        logger.error("get_pipeline_status failed: %s", e)
        return None


def update_calendar(
    video_id: str,
    publish_date: str,
    topic: str,
    niche: str = "",
    trending_score: str = "",
    status: str = "planned",
    source: str = "",
) -> bool:
    """
    Upsert a row in the Content Calendar tab.

    If a row with matching *video_id* already exists it is updated;
    otherwise a new row is appended.

    Returns True on success, False on error.
    """
    if not _get_sheet_id():
        return True

    try:
        spreadsheet = _get_spreadsheet()
        if spreadsheet is None:
            return True

        ws = _ensure_tab(spreadsheet, TAB_CALENDAR, CALENDAR_HEADERS)

        row = [
            publish_date,
            video_id,
            topic,
            niche,
            str(trending_score),
            status,
            source,
        ]

        existing_row = _find_row_by_video_id(ws, video_id)
        # video_id is column B (index 1) in the Calendar tab, so search col 2
        try:
            cell = ws.find(video_id, in_column=2)
            existing_row = cell.row if cell else None
        except Exception:
            existing_row = None

        if existing_row:
            end_col = chr(ord("A") + len(row) - 1)
            ws.update(
                values=[row],
                range_name=f"A{existing_row}:{end_col}{existing_row}",
                value_input_option="RAW",
            )
            logger.info("Updated Calendar row %d for %s", existing_row, video_id)
        else:
            ws.append_row(row, value_input_option="RAW")
            logger.info("Appended Calendar row for %s", video_id)

        return True

    except Exception as e:
        logger.error("update_calendar failed for %s: %s", video_id, e)
        return False


# ---------------------------------------------------------------------------
# CLI entry point (for testing / manual use)
# ---------------------------------------------------------------------------


def main():
    """Simple CLI for manual testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Google Sheet Pipeline Tracker")
    sub = parser.add_subparsers(dest="command")

    # sync
    sync_p = sub.add_parser("sync", help="Sync a video state to the Pipeline tab")
    sync_p.add_argument("--video-id", required=True)
    sync_p.add_argument("--state-json", required=True, help="Path to state.json")

    # log-cost
    cost_p = sub.add_parser("log-cost", help="Log a cost entry")
    cost_p.add_argument("--video-id", required=True)
    cost_p.add_argument("--category", required=True, choices=["tts", "claude", "images", "other"])
    cost_p.add_argument("--amount", required=True, type=float)
    cost_p.add_argument("--service", required=True)

    # status
    sub.add_parser("status", help="Print all Pipeline rows")

    # calendar
    cal_p = sub.add_parser("calendar", help="Upsert a Content Calendar row")
    cal_p.add_argument("--video-id", required=True)
    cal_p.add_argument("--publish-date", required=True)
    cal_p.add_argument("--topic", required=True)
    cal_p.add_argument("--niche", default="")
    cal_p.add_argument("--status", default="planned")

    args = parser.parse_args()

    if args.command == "sync":
        with open(args.state_json) as f:
            state = json.load(f)
        ok = sync_video_to_sheet(args.video_id, state)
        print("OK" if ok else "FAILED")

    elif args.command == "log-cost":
        ok = log_cost(args.video_id, args.category, args.amount, args.service)
        print("OK" if ok else "FAILED")

    elif args.command == "status":
        rows = get_pipeline_status()
        if rows is None:
            print("Sheet not configured (PIPELINE_SHEET_ID not set).")
        elif not rows:
            print("No rows in Pipeline tab.")
        else:
            print(json.dumps(rows, indent=2))

    elif args.command == "calendar":
        ok = update_calendar(
            args.video_id, args.publish_date, args.topic,
            niche=args.niche, status=args.status,
        )
        print("OK" if ok else "FAILED")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
