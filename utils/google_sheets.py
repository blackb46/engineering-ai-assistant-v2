"""
google_sheets.py
================
City of Brentwood Engineering AI Assistant - V2
Google Sheets integration for flagged response logging.

PURPOSE:
    When an engineer clicks "👎 Needs Improvement", the flagged response
    is sent to a Google Sheet so administrators can review it outside the
    app — in a familiar spreadsheet interface they already know how to use.

    V2 ADDITIONS over V1:
    - Discrepancy flag column (more_restrictive / conflict / none)
    - Abstained column (did the system decline to answer?)
    - Sheet auto-header initialization (creates header row if sheet is empty)
    - test_connection() returns structured dict instead of tuple

V1 COMPATIBILITY:
    log_flagged_response(question, ai_response, user_feedback) still works
    exactly as before. The new columns just get empty values on V1-style calls.

GOOGLE SHEET COLUMN LAYOUT (V2):
    A: Timestamp
    B: Question
    C: AI Response
    D: User Feedback
    E: Discrepancy Flag      ← NEW in V2
    F: Abstained             ← NEW in V2
    G: Status

HOW AUTH WORKS:
    Uses the same gcp_service_account credentials already in Streamlit
    secrets for drive_loader.py. No new credentials needed.

REQUIRED STREAMLIT SECRETS:
    [gcp_service_account]   ← already present
    GOOGLE_SHEET_ID = "..." ← already present from V1

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

from datetime import datetime
from typing import Optional

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Google API scopes needed for Sheets read/write
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# V2 column header row — written to row 1 if the sheet is empty
SHEET_HEADERS = [
    "Timestamp",
    "Question",
    "AI Response",
    "User Feedback",
    "Discrepancy Flag",   # V2
    "Abstained",          # V2
    "Status",
]

# Maximum characters to store per cell (Google Sheets limit: 50,000)
MAX_CELL_CHARS = 5000


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get_worksheet() -> Optional[gspread.Worksheet]:
    """
    Connect to the Google Sheet and return the first worksheet.

    Uses the same gcp_service_account credentials as drive_loader.py
    and google_sheets.py V1 — no new setup required.

    RETURNS:
        gspread.Worksheet if connection succeeds, None if it fails.
    """
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SHEETS_SCOPES,
        )
        client      = gspread.authorize(credentials)
        sheet_id    = st.secrets["GOOGLE_SHEET_ID"]
        spreadsheet = client.open_by_key(sheet_id)
        return spreadsheet.sheet1

    except Exception as e:
        print(f"google_sheets._get_worksheet error: {e}")
        return None


def _ensure_headers(worksheet: gspread.Worksheet):
    """
    Write the V2 header row if the sheet is empty or has no headers.

    Safe to call on every write — checks first row before writing.
    Handles the case where a V1 sheet already has headers by leaving
    them alone (V1 headers are a subset of V2 headers).

    ARGS:
        worksheet: The connected gspread worksheet.
    """
    try:
        first_row = worksheet.row_values(1)
        if not first_row:
            # Sheet is empty — write the V2 header row
            worksheet.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"google_sheets._ensure_headers error: {e}")


def _truncate(text: str, max_chars: int = MAX_CELL_CHARS) -> str:
    """
    Truncate a string to fit within Google Sheets cell limits.

    ARGS:
        text:      The string to truncate.
        max_chars: Maximum character count (default 5000).

    RETURNS:
        Truncated string with "... [truncated]" suffix if shortened.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def log_flagged_response(
    question:         str,
    ai_response:      str,
    user_feedback:    str  = "",
    # V2 additions — optional so V1 callers still work unchanged
    discrepancy_flag: Optional[str]  = None,
    abstained:        bool = False,
) -> bool:
    """
    Append a flagged response to the Google Sheet review queue.

    Called when an engineer submits the "👎 Needs Improvement" feedback form.

    V1 CALL (still works):
        log_flagged_response(question, ai_response, user_feedback)

    V2 CALL (full context):
        log_flagged_response(
            question, ai_response, user_feedback,
            discrepancy_flag="more_restrictive",
            abstained=False,
        )

    ARGS:
        question:         The engineer's original question.
        ai_response:      The AI answer that was flagged.
        user_feedback:    Engineer's explanation of what was wrong (optional).
        discrepancy_flag: 'more_restrictive' | 'conflict' | None
        abstained:        True if the system declined to answer.

    RETURNS:
        True if the row was written successfully, False if it failed.
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        print("google_sheets.log_flagged_response: could not connect to sheet")
        return False

    try:
        _ensure_headers(worksheet)

        timestamp     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        disc_display  = discrepancy_flag if discrepancy_flag else "none"
        abst_display  = "Yes" if abstained else "No"

        new_row = [
            timestamp,
            _truncate(question),
            _truncate(ai_response),
            user_feedback if user_feedback else "(No feedback provided)",
            disc_display,    # V2
            abst_display,    # V2
            "Open",          # default review status
        ]

        worksheet.append_row(new_row, value_input_option="USER_ENTERED")
        print(f"✅ Flagged response logged to Google Sheet at {timestamp}")
        return True

    except Exception as e:
        print(f"google_sheets.log_flagged_response error: {e}")
        return False


def test_connection() -> dict:
    """
    Test the Google Sheets connection and return a status dict.

    Used by the Admin panel to verify Sheets integration is working.

    V1 returned a (bool, str) tuple. V2 returns a dict for richer
    status display, but the first element is still a bool so old
    callers using `success, msg = test_connection()` still work via
    dict unpacking workaround (see note below).

    RETURNS:
        dict with keys:
            success (bool):   True if connected
            message (str):    Human-readable status
            sheet_title (str): Spreadsheet name if connected
            row_count (int):  Number of data rows (excluding header)
    """
    worksheet = _get_worksheet()

    if worksheet is None:
        return {
            "success":     False,
            "message":     "Could not connect to Google Sheet. "
                           "Check gcp_service_account and GOOGLE_SHEET_ID secrets.",
            "sheet_title": "",
            "row_count":   0,
        }

    try:
        headers   = worksheet.row_values(1)
        all_rows  = worksheet.get_all_values()
        row_count = max(0, len(all_rows) - 1)  # subtract header row

        if headers:
            return {
                "success":     True,
                "message":     f"Connected. Headers: {headers}",
                "sheet_title": worksheet.spreadsheet.title,
                "row_count":   row_count,
            }
        else:
            return {
                "success":     True,
                "message":     "Connected but sheet is empty. Headers will be "
                               "written automatically on first flagged response.",
                "sheet_title": worksheet.spreadsheet.title,
                "row_count":   0,
            }

    except Exception as e:
        return {
            "success":     False,
            "message":     f"Connection error: {str(e)}",
            "sheet_title": "",
            "row_count":   0,
        }
