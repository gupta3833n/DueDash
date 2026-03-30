"""
DueDash Configuration
Centralised config — override via environment variables or edit here directly.
"""

import os


def _get_secret(key: str, default: str = "") -> str:
    """Load a secret: Streamlit secrets → env var → default."""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    val = os.getenv(key, "")
    if val:
        return val
    return default


# ── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_FILE = _get_secret("GOOGLE_CREDENTIALS_FILE")   # path to service-account JSON
GOOGLE_SHEET_ID          = _get_secret("GOOGLE_SHEET_ID")          # spreadsheet ID from URL
GOOGLE_SHEET_NAME        = _get_secret("GOOGLE_SHEET_NAME", "Compliance Calendar")

# ── Email / SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST     = _get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(_get_secret("SMTP_PORT", "587"))
SMTP_USER     = _get_secret("SMTP_USER")
SMTP_PASSWORD = _get_secret("SMTP_PASSWORD")
ALERT_EMAIL   = _get_secret("ALERT_EMAIL")  # recipient for reminders
EMAIL_DAYS_BEFORE = [1, 3, 7, 15]             # days before due date to send alerts

# ── Gemini API (future AI features) ──────────────────────────────────────────
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")

# ── App ───────────────────────────────────────────────────────────────────────
APP_TITLE   = "DueDash"
APP_TAGLINE = "Smart Compliance Calendar for Indian Businesses"
DEFAULT_FY  = "2025-26"
SUPPORTED_FYS = ["2025-26", "2026-27"]

# Urgency thresholds (days)
BURNING_DAYS   = 3    # 0-3 days → Burning Now
THIS_WEEK_DAYS = 7    # 4-7 days → This Week
UPCOMING_DAYS  = 30   # 8-30 days → Next 30 Days
                      # 31+ days  → Future

# Colours (used in CSS injection)
COLORS = {
    "primary":    "#4A90D9",
    "primary_dk": "#2563AB",
    "bg":         "#F8FAFC",
    "card":       "#FFFFFF",
    "accent":     "#E8F0FE",
    "border":     "#E2E8F0",
    "text":       "#2D3748",
    "muted":      "#718096",

    # Status
    "overdue":    "#E53E3E",
    "overdue_bg": "#FFF5F5",
    "burning":    "#DD6B20",
    "burning_bg": "#FFFAF0",
    "this_week":  "#D69E2E",
    "this_week_bg": "#FFFFF0",
    "upcoming":   "#276749",
    "upcoming_bg": "#F0FFF4",
    "future":     "#2B6CB0",
    "future_bg":  "#EBF8FF",
    "done":       "#718096",
    "done_bg":    "#F7FAFC",
}

CATEGORY_COLORS = {
    "Income Tax":          "#4A90D9",
    "GST":                 "#7C3AED",
    "ROC / MCA":           "#EA580C",
    "TDS / TCS":           "#0D9488",
    "PF":                  "#9333EA",
    "ESI":                 "#16A34A",
    "Professional Tax":    "#CA8A04",
    "Labour Welfare Fund": "#0284C7",
    "Shop & Establishment":"#DB2777",
    "Industry-Specific":   "#059669",
}
