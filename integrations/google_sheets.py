"""
Google Sheets Integration for DueDash
Reads/writes compliance calendar data to a Google Sheet.

Setup:
1. Create a Google Cloud project and enable Sheets + Drive APIs
2. Create a service account, download credentials JSON
3. Share your spreadsheet with the service account email
4. Set GOOGLE_CREDENTIALS_FILE and GOOGLE_SHEET_ID in config.py or env vars
"""

from __future__ import annotations

from datetime import date
from typing import List, Dict, Optional, Tuple
import os

# ── Lazy imports so app runs without these packages installed ─────────────────
def _try_import():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        return gspread, Credentials
    except ImportError:
        return None, None


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER_ROW = [
    "Category", "Sub-Category", "Compliance Name", "Description",
    "Due Date", "Period", "Days Remaining", "Status",
    "Form / Return", "Penalty", "Priority",
]


class GoogleSheetsIntegration:
    """Thin wrapper around gspread for DueDash."""

    def __init__(self, credentials_file: str, sheet_id: str, sheet_name: str = "Compliance Calendar"):
        self.credentials_file = credentials_file
        self.sheet_id         = sheet_id
        self.sheet_name       = sheet_name
        self._client          = None
        self._sheet           = None

    def is_configured(self) -> bool:
        return bool(self.credentials_file and self.sheet_id and
                    os.path.exists(self.credentials_file))

    def connect(self) -> Tuple[bool, str]:
        """Establish connection. Returns (success, message)."""
        gspread, Credentials = _try_import()
        if gspread is None:
            return False, "gspread / google-auth packages not installed. Run: pip install gspread google-auth"
        if not self.is_configured():
            return False, "Google credentials file or Sheet ID not configured."
        try:
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=SCOPES)
            self._client = gspread.authorize(creds)
            spreadsheet    = self._client.open_by_key(self.sheet_id)
            # Get or create worksheet
            try:
                self._sheet = spreadsheet.worksheet(self.sheet_name)
            except Exception:
                self._sheet = spreadsheet.add_worksheet(title=self.sheet_name, rows=500, cols=20)
            return True, "Connected to Google Sheets successfully."
        except Exception as e:
            return False, f"Connection failed: {e}"

    def write_calendar(self, items: List[Dict], entity_type: str, state: str, fy: str) -> Tuple[bool, str]:
        """Write compliance calendar to sheet. Returns (success, message)."""
        if self._sheet is None:
            ok, msg = self.connect()
            if not ok:
                return False, msg
        try:
            from utils.helpers import STATUS_LABELS, format_date
            rows = [HEADER_ROW]
            for item in items:
                dd = item.get("due_date")
                rows.append([
                    item.get("category", ""),
                    item.get("sub_category", ""),
                    item.get("name", ""),
                    item.get("description", ""),
                    format_date(dd) if dd else "",
                    item.get("period", ""),
                    str(item.get("days_remaining", "")),
                    STATUS_LABELS.get(item.get("status", ""), ""),
                    item.get("form_number", ""),
                    item.get("penalty", ""),
                    item.get("priority", "medium").capitalize(),
                ])
            self._sheet.clear()
            self._sheet.update(rows, "A1")
            # Bold header
            self._sheet.format("A1:K1", {"textFormat": {"bold": True}})
            return True, f"Successfully wrote {len(items)} items to Google Sheets."
        except Exception as e:
            return False, f"Write failed: {e}"

    def read_calendar(self) -> Tuple[Optional[List[Dict]], str]:
        """Read compliance data from sheet. Returns (data or None, message)."""
        if self._sheet is None:
            ok, msg = self.connect()
            if not ok:
                return None, msg
        try:
            records = self._sheet.get_all_records()
            return records, f"Read {len(records)} items from Google Sheets."
        except Exception as e:
            return None, f"Read failed: {e}"


def get_integration(credentials_file: str = "", sheet_id: str = "",
                    sheet_name: str = "Compliance Calendar") -> GoogleSheetsIntegration:
    """Factory — reads config if args not provided."""
    if not credentials_file:
        from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
        credentials_file = GOOGLE_CREDENTIALS_FILE
        sheet_id         = GOOGLE_SHEET_ID
        sheet_name       = GOOGLE_SHEET_NAME
    return GoogleSheetsIntegration(credentials_file, sheet_id, sheet_name)
