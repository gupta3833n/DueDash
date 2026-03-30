"""
DueDash — Smart Compliance Calendar & Auto-Reminder Platform
AICA Level 2 Capstone Project

Run:  streamlit run app.py
"""

from __future__ import annotations

import sys
import os
from datetime import date, datetime
from typing import List, Dict, Optional

import pandas as pd
import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from compliance_engine import (
    generate_calendar, get_urgency_counts,
    ENTITY_TYPES, STATES, INDUSTRIES, GST_TURNOVER_OPTIONS, STATUS_LABELS,
)
from utils.helpers import (
    format_date, days_label, export_to_excel, get_categories, compute_summary,
)
from config import (
    APP_TITLE, APP_TAGLINE, COLORS, CATEGORY_COLORS, SUPPORTED_FYS,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL,
    GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DueDash – Compliance Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    color: #2D3748;
}
.main { background: #F8FAFC; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
section[data-testid="stSidebar"] .block-container { padding: 1rem 1rem 2rem; }

/* ── Header ── */
.dd-header {
    background: linear-gradient(135deg, #2563AB 0%, #4A90D9 100%);
    border-radius: 14px;
    padding: 22px 28px;
    margin-bottom: 24px;
    color: white;
}
.dd-header h1 { margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -1px; color: white; }
.dd-header p  { margin: 4px 0 0; font-size: 0.95rem; opacity: 0.88; color: white; }

/* ── Demo banner ── */
.demo-banner {
    background: #EBF8FF;
    border: 1px solid #90CDF4;
    border-radius: 10px;
    padding: 10px 18px;
    margin-bottom: 16px;
    font-size: 0.88rem;
    color: #2B6CB0;
}

/* ── Stat cards ── */
.stats-grid { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 24px; }
.stat-card {
    flex: 1; min-width: 120px;
    background: #FFFFFF;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: transform .15s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-number { font-size: 2rem; font-weight: 800; line-height: 1; }
.stat-label  { font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
               letter-spacing: 0.5px; margin-top: 5px; }

/* ── Compliance card ── */
.comp-card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow .15s;
    border-left: 4px solid #4A90D9;
}
.comp-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.10); }
.comp-card.overdue   { border-left-color: #E53E3E; background: #FFFAFA; }
.comp-card.burning   { border-left-color: #DD6B20; background: #FFFCF7; }
.comp-card.this_week { border-left-color: #D69E2E; background: #FFFFFB; }
.comp-card.upcoming  { border-left-color: #276749; background: #FAFFF9; }
.comp-card.future    { border-left-color: #4A90D9; background: #FAFCFF; }

.card-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; }
.card-title { font-size: 1rem; font-weight: 700; color: #1A202C; margin: 0; }
.card-meta  { font-size: 0.8rem; color: #718096; margin-top: 4px; }
.card-desc  { font-size: 0.85rem; color: #4A5568; margin-top: 8px; line-height: 1.5; }
.card-footer { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; align-items: center; }

/* ── Badges ── */
.badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.badge-overdue   { background: #FFF5F5; color: #E53E3E; border: 1px solid #FEB2B2; }
.badge-burning   { background: #FFFAF0; color: #DD6B20; border: 1px solid #FBD38D; }
.badge-this_week { background: #FFFFF0; color: #D69E2E; border: 1px solid #FAF089; }
.badge-upcoming  { background: #F0FFF4; color: #276749; border: 1px solid #9AE6B4; }
.badge-future    { background: #EBF8FF; color: #2B6CB0; border: 1px solid #90CDF4; }
.badge-done      { background: #F7FAFC; color: #718096; border: 1px solid #CBD5E0; }

/* ── Category pill ── */
.cat-pill {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 999px;
    background: #EBF8FF;
    color: #2B6CB0;
}

/* ── Days chip ── */
.days-chip {
    font-size: 0.8rem;
    font-weight: 700;
    color: #718096;
}
.days-chip.overdue   { color: #E53E3E; }
.days-chip.burning   { color: #DD6B20; }
.days-chip.this_week { color: #D69E2E; }
.days-chip.upcoming  { color: #276749; }
.days-chip.future    { color: #2B6CB0; }

/* ── Sidebar labels ── */
.sb-section {
    font-size: 0.72rem;
    font-weight: 700;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 16px 0 6px;
}

/* ── Tables ── */
.dataframe { font-size: 0.85rem !important; }

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #A0AEC0;
}
.empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
.empty-state h3    { color: #718096; font-size: 1.1rem; }

/* ── Settings form ── */
.settings-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.settings-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #2D3748;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Calendar View ── */
.cal-container { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
.cal-month {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px;
    min-width: 280px;
    max-width: 340px;
    flex: 1;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    overflow: visible;
}
.cal-month-title {
    text-align: center;
    font-weight: 800;
    font-size: 1rem;
    color: #2563AB;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E8F0FE;
}
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
    overflow: visible;
}
.cal-dow {
    text-align: center;
    font-size: 0.68rem;
    font-weight: 700;
    color: #718096;
    padding: 4px 0;
    text-transform: uppercase;
}
.cal-day {
    text-align: center;
    padding: 6px 2px;
    border-radius: 6px;
    font-size: 0.78rem;
    color: #4A5568;
    position: relative;
    min-height: 36px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}
.cal-day.empty { background: transparent; }
.cal-day.today {
    border: 2px solid #4A90D9;
    font-weight: 800;
}
.cal-day.has-items {
    cursor: pointer;
    font-weight: 700;
    transition: transform .15s, box-shadow .15s;
}
.cal-day.has-items:hover {
    transform: scale(1.15);
    box-shadow: 0 3px 10px rgba(0,0,0,0.15);
    z-index: 10;
}
.cal-day.has-items.overdue   { background: #FFF5F5; color: #E53E3E; border: 1px solid #FEB2B2; }
.cal-day.has-items.burning   { background: #FFFAF0; color: #DD6B20; border: 1px solid #FBD38D; }
.cal-day.has-items.this_week { background: #FFFFF0; color: #D69E2E; border: 1px solid #FAF089; }
.cal-day.has-items.upcoming  { background: #F0FFF4; color: #276749; border: 1px solid #9AE6B4; }
.cal-day.has-items.future    { background: #EBF8FF; color: #2B6CB0; border: 1px solid #90CDF4; }
.cal-day-num { font-size: 0.82rem; line-height: 1; }
.cal-day-count {
    font-size: 0.6rem;
    background: currentColor;
    color: #FFFFFF;
    border-radius: 999px;
    padding: 1px 5px;
    margin-top: 2px;
    line-height: 1.3;
}
.cal-day.has-items.overdue .cal-day-count   { background: #E53E3E; }
.cal-day.has-items.burning .cal-day-count   { background: #DD6B20; }
.cal-day.has-items.this_week .cal-day-count { background: #D69E2E; }
.cal-day.has-items.upcoming .cal-day-count  { background: #276749; }
.cal-day.has-items.future .cal-day-count    { background: #2B6CB0; }

/* ── Calendar tooltip ── */
.cal-day.has-items .cal-tooltip {
    display: none;
    position: absolute;
    bottom: 110%;
    left: 50%;
    transform: translateX(-50%);
    background: #1A202C;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.72rem;
    font-weight: 500;
    white-space: nowrap;
    z-index: 100;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    text-align: left;
    min-width: 200px;
    max-width: 320px;
    white-space: normal;
    line-height: 1.5;
}
.cal-day.has-items .cal-tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: #1A202C;
}
.cal-day.has-items:hover .cal-tooltip { display: block; }

/* ── Calendar legend ── */
.cal-legend {
    display: flex; gap: 16px; flex-wrap: wrap;
    justify-content: center;
    margin: 16px 0;
    font-size: 0.78rem;
}
.cal-legend-item {
    display: flex; align-items: center; gap: 5px;
}
.cal-legend-dot {
    width: 12px; height: 12px; border-radius: 3px;
}

/* ── Email preview card ── */
.email-preview {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin: 12px 0;
}
.email-preview-header {
    background: linear-gradient(135deg, #2563AB, #4A90D9);
    padding: 14px 20px;
    color: white;
    font-weight: 700;
}
.email-preview-body {
    padding: 16px 20px;
    font-size: 0.85rem;
    color: #4A5568;
    max-height: 300px;
    overflow-y: auto;
}

/* ── Mobile responsive ── */
@media (max-width: 768px) {
    .stats-grid { gap: 8px; }
    .stat-card  { min-width: 80px; padding: 12px 10px; }
    .stat-number { font-size: 1.5rem; }
    .comp-card  { padding: 12px 14px; }
    .dd-header h1 { font-size: 1.5rem; }
    .card-top   { flex-direction: column; }
    .cal-month  { min-width: 100%; }
    .cal-day    { min-height: 28px; padding: 4px 1px; }
    .cal-day-num { font-size: 0.7rem; }
}

/* ── Streamlit overrides ── */
div[data-testid="stTabs"] > div > div > button {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stSelectbox label, .stRadio label, .stSlider label {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #4A5568 !important;
}
/* Allow tooltips to overflow Streamlit containers */
div[data-testid="stMarkdown"], div[data-testid="stHtml"] {
    overflow: visible !important;
}
div[data-testid="stMarkdown"] > div, div[data-testid="stHtml"] > div {
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ─────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "entity_type":    "Private Company",
        "state":          "Maharashtra",
        "industry":       "General",
        "fy":             "2025-26",
        "gst_label":      "Above Rs 5 Cr (Monthly Filing)",
        "search":         "",
        "category_filter": "All",
        "calendar":       None,
        "smtp_host":      SMTP_HOST,
        "smtp_port":      SMTP_PORT,
        "smtp_user":      SMTP_USER,
        "smtp_password":  SMTP_PASSWORD,
        "alert_email":    ALERT_EMAIL,
        "gsheets_creds":  GOOGLE_CREDENTIALS_FILE,
        "gsheets_id":     GOOGLE_SHEET_ID,
        "gsheets_name":   GOOGLE_SHEET_NAME,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── Helpers ───────────────────────────────────────────────────────────────────

CATEGORY_ICON = {
    "Income Tax":          "💰",
    "GST":                 "🧾",
    "ROC / MCA":           "🏢",
    "TDS / TCS":           "✂️",
    "PF":                  "🛡️",
    "ESI":                 "🏥",
    "Professional Tax":    "📋",
    "Labour Welfare Fund": "🤝",
    "Shop & Establishment":"🏪",
    "Industry-Specific":   "🏭",
}

STATUS_ICON = {
    "overdue":   "🔴",
    "burning":   "🔥",
    "this_week": "⚠️",
    "upcoming":  "📅",
    "future":    "🔵",
    "done":      "✅",
}

STATUS_BADGE_LABEL = {
    "overdue":   "Overdue",
    "burning":   "Burning Now",
    "this_week": "This Week",
    "upcoming":  "Next 30 Days",
    "future":    "Future",
    "done":      "Done",
}


def _is_demo() -> bool:
    return not (SMTP_USER or GOOGLE_CREDENTIALS_FILE)


def _load_calendar() -> List[Dict]:
    return generate_calendar(
        entity_type       = st.session_state.entity_type,
        state             = st.session_state.state,
        industry          = st.session_state.industry,
        fy                = st.session_state.fy,
        gst_turnover_label= st.session_state.gst_label,
    )


def _render_stat_card(number: int, label: str, color: str, bg: str = "#FFFFFF") -> str:
    return (
        f'<div class="stat-card" style="background:{bg};">'
        f'<div class="stat-number" style="color:{color};">{number}</div>'
        f'<div class="stat-label" style="color:{color};">{label}</div>'
        f'</div>'
    )


def _render_compliance_card(item: Dict) -> str:
    status    = item.get("status", "future")
    category  = item.get("category", "")
    cat_color = CATEGORY_COLORS.get(category, "#4A90D9")
    icon      = CATEGORY_ICON.get(category, "📋")
    days      = item.get("days_remaining", 0)
    due_str   = format_date(item["due_date"])
    days_str  = days_label(days)
    form      = item.get("form_number", "")
    period    = item.get("period", "")
    penalty   = item.get("penalty", "")
    priority  = item.get("priority", "medium")

    priority_html = ""
    if priority == "high":
        priority_html = '<span style="font-size:0.7rem;font-weight:700;color:#E53E3E;background:#FFF5F5;padding:2px 8px;border-radius:999px;border:1px solid #FEB2B2;">HIGH</span>'
    elif priority == "medium":
        priority_html = '<span style="font-size:0.7rem;font-weight:700;color:#D69E2E;background:#FFFFF0;padding:2px 8px;border-radius:999px;border:1px solid #FAF089;">MEDIUM</span>'

    form_html    = f'<span style="font-size:0.78rem;color:#4A90D9;background:#EBF8FF;padding:2px 8px;border-radius:6px;">{form}</span>' if form else ""
    period_html  = f'<span style="font-size:0.78rem;color:#718096;">📆 {period}</span>' if period else ""

    penalty_block = ""
    if penalty and status in ["overdue", "burning"]:
        penalty_block = f'<div style="margin-top:10px;padding:8px 12px;background:#FFF5F5;border-radius:8px;font-size:0.78rem;color:#C53030;"><strong>Penalty:</strong> {penalty}</div>'

    return (
        f'<div class="comp-card {status}">'
        f'<div class="card-top">'
        f'<div>'
        f'<div class="card-title">{icon} {item.get("name","")}</div>'
        f'<div class="card-meta">'
        f'<span class="cat-pill" style="background:{cat_color}22;color:{cat_color};">{category}</span>'
        f'&nbsp;&nbsp;📅 Due: <strong>{due_str}</strong>'
        f'</div></div>'
        f'<div style="text-align:right;">'
        f'<span class="badge badge-{status}">{STATUS_ICON.get(status,"")} {STATUS_BADGE_LABEL.get(status,"")}</span><br>'
        f'<span class="days-chip {status}" style="margin-top:4px;display:block;">{days_str}</span>'
        f'</div></div>'
        f'<div class="card-desc">{item.get("description","")}</div>'
        f'<div class="card-footer">{priority_html}{form_html}{period_html}</div>'
        f'{penalty_block}'
        f'</div>'
    )


def _render_empty(label: str) -> str:
    return (
        f'<div class="empty-state">'
        f'<div class="icon">🎉</div>'
        f'<h3>No {label} items</h3>'
        f'<p style="font-size:0.88rem;">Nothing to show here — you\'re on track!</p>'
        f'</div>'
    )


# ── Calendar View ─────────────────────────────────────────────────────────────

def _render_calendar_month(year: int, month: int, items: List[Dict], today: date) -> str:
    """Render a single month as an HTML calendar grid with hover tooltips."""
    import calendar as cal_mod
    c = cal_mod.Calendar(firstweekday=0)
    month_name = date(year, month, 1).strftime("%B %Y")

    month_items = [i for i in items if i["due_date"].month == month and i["due_date"].year == year]
    by_day: Dict[int, List[Dict]] = {}
    for item in month_items:
        by_day.setdefault(item["due_date"].day, []).append(item)

    cells = ""
    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        cells += f'<div class="cal-dow">{d}</div>'

    for week in c.monthdayscalendar(year, month):
        for day in week:
            if day == 0:
                cells += '<div class="cal-day empty"></div>'
                continue

            is_today = (year == today.year and month == today.month and day == today.day)
            today_cls = " today" if is_today else ""
            day_items = by_day.get(day, [])

            if not day_items:
                cells += f'<div class="cal-day{today_cls}"><span class="cal-day-num">{day}</span></div>'
            else:
                statuses = [i["status"] for i in day_items]
                for s in ["overdue", "burning", "this_week", "upcoming", "future"]:
                    if s in statuses:
                        cls = s
                        break
                else:
                    cls = "future"

                tooltip_lines = []
                for i in day_items[:6]:
                    cat_icon = CATEGORY_ICON.get(i.get("category", ""), "📋")
                    tooltip_lines.append(f"{cat_icon} {i['name']}")
                if len(day_items) > 6:
                    tooltip_lines.append(f"...+{len(day_items)-6} more")
                tooltip_html = "<br>".join(tooltip_lines)

                cells += (
                    f'<div class="cal-day has-items {cls}{today_cls}">'
                    f'<span class="cal-day-num">{day}</span>'
                    f'<span class="cal-day-count">{len(day_items)}</span>'
                    f'<div class="cal-tooltip">{tooltip_html}</div>'
                    f'</div>'
                )

    return (
        f'<div class="cal-month">'
        f'<div class="cal-month-title">{month_name}</div>'
        f'<div class="cal-grid">{cells}</div>'
        f'</div>'
    )


def _render_full_calendar(items: List[Dict], fy: str) -> str:
    """Render full FY calendar (Apr to Mar) + extended months for post-FY filings."""
    fy_year = int(fy.split("-")[0])
    today = date.today()

    # FY months Apr to Mar + extended to Dec of next year for post-FY filings
    months = []
    for m in range(4, 13):
        months.append((fy_year, m))
    for m in range(1, 13):
        months.append((fy_year + 1, m))

    # Only show months that have items or are within the FY
    month_has_items = set()
    for item in items:
        month_has_items.add((item["due_date"].year, item["due_date"].month))

    cal_html = ""
    for y, m in months:
        if (y, m) in month_has_items:
            cal_html += _render_calendar_month(y, m, items, today)

    legend = (
        '<div class="cal-legend">'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#E53E3E;"></div>Overdue</div>'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#DD6B20;"></div>Burning Now</div>'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#D69E2E;"></div>This Week</div>'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#276749;"></div>Next 30 Days</div>'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#2B6CB0;"></div>Future</div>'
        '<div class="cal-legend-item"><div class="cal-legend-dot" style="background:#4A90D9;border:2px solid #2563AB;"></div>Today</div>'
        '</div>'
    )

    return legend + f'<div class="cal-container">{cal_html}</div>'


# ── Charts ────────────────────────────────────────────────────────────────────

def _render_charts(items: List[Dict], counts: Dict[str, int]):
    """Render analytics charts using Plotly."""
    import plotly.graph_objects as go

    # ── 1. Status Distribution Donut ──────────────────────────────────────────
    status_data = {
        "Overdue":      counts.get("overdue", 0),
        "Burning Now":  counts.get("burning", 0),
        "This Week":    counts.get("this_week", 0),
        "Next 30 Days": counts.get("upcoming", 0),
        "Future":       counts.get("future", 0),
    }
    status_data = {k: v for k, v in status_data.items() if v > 0}

    fig_status = go.Figure(data=[go.Pie(
        labels=list(status_data.keys()),
        values=list(status_data.values()),
        hole=0.55,
        marker=dict(colors=["#E53E3E", "#DD6B20", "#D69E2E", "#276749", "#2B6CB0"]),
        textinfo="label+value",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>%{value} items<br>%{percent}<extra></extra>",
    )])
    fig_status.update_layout(
        title=dict(text="Compliance Status Distribution", font=dict(size=16, color="#2D3748")),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
        height=380,
        margin=dict(t=50, b=40, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
        annotations=[dict(
            text=f"<b>{counts.get('total', 0)}</b><br>Total",
            x=0.5, y=0.5, font_size=18, showarrow=False, font_color="#2D3748",
        )],
    )

    # ── 2. Category Breakdown Bar ─────────────────────────────────────────────
    cat_counts: Dict[str, int] = {}
    for item in items:
        cat = item.get("category", "Other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    cat_sorted = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    cat_names = [c[0] for c in cat_sorted]
    cat_vals  = [c[1] for c in cat_sorted]
    cat_colors_list = [CATEGORY_COLORS.get(c, "#4A90D9") for c in cat_names]

    fig_cat = go.Figure(data=[go.Bar(
        x=cat_vals, y=cat_names,
        orientation="h",
        marker=dict(color=cat_colors_list, cornerradius=6),
        text=cat_vals,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x} items<extra></extra>",
    )])
    fig_cat.update_layout(
        title=dict(text="Items by Compliance Category", font=dict(size=16, color="#2D3748")),
        height=max(300, len(cat_names) * 42 + 80),
        margin=dict(t=50, b=30, l=140, r=40),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", title=""),
        yaxis=dict(autorange="reversed", title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
    )

    # ── 3. Monthly Timeline ──────────────────────────────────────────────────
    month_data: Dict[str, Dict[str, int]] = {}
    for item in items:
        key = item["due_date"].strftime("%Y-%m")
        label = item["due_date"].strftime("%b %Y")
        if key not in month_data:
            month_data[key] = {"label": label, "overdue": 0, "burning": 0, "this_week": 0, "upcoming": 0, "future": 0}
        s = item.get("status", "future")
        if s in month_data[key]:
            month_data[key][s] += 1

    sorted_months = sorted(month_data.keys())
    m_labels = [month_data[k]["label"] for k in sorted_months]

    fig_timeline = go.Figure()
    for status_key, color, name in [
        ("overdue", "#E53E3E", "Overdue"),
        ("burning", "#DD6B20", "Burning"),
        ("this_week", "#D69E2E", "This Week"),
        ("upcoming", "#276749", "Next 30 Days"),
        ("future", "#2B6CB0", "Future"),
    ]:
        vals = [month_data[k].get(status_key, 0) for k in sorted_months]
        if sum(vals) > 0:
            fig_timeline.add_trace(go.Bar(
                x=m_labels, y=vals, name=name,
                marker_color=color,
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y}} items<extra></extra>",
            ))

    fig_timeline.update_layout(
        title=dict(text="Monthly Compliance Timeline", font=dict(size=16, color="#2D3748")),
        barmode="stack",
        height=380,
        margin=dict(t=50, b=40, l=40, r=20),
        xaxis=dict(title="", tickangle=-45),
        yaxis=dict(title="Items", showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
    )

    # ── 4. Priority Breakdown ─────────────────────────────────────────────────
    pri_counts = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        p = item.get("priority", "medium")
        if p in pri_counts:
            pri_counts[p] += 1

    fig_pri = go.Figure(data=[go.Pie(
        labels=["High", "Medium", "Low"],
        values=[pri_counts["high"], pri_counts["medium"], pri_counts["low"]],
        hole=0.5,
        marker=dict(colors=["#E53E3E", "#D69E2E", "#48BB78"]),
        textinfo="label+value",
        hovertemplate="<b>%{label}</b><br>%{value} items<extra></extra>",
    )])
    fig_pri.update_layout(
        title=dict(text="Priority Breakdown", font=dict(size=16, color="#2D3748")),
        height=350,
        margin=dict(t=50, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial"),
    )

    return fig_status, fig_cat, fig_timeline, fig_pri


# ── Email Preview Builder ────────────────────────────────────────────────────

def _build_email_preview_items(items: List[Dict]) -> str:
    """Build a compact HTML preview of what the email will contain."""
    urgent = [i for i in items if i.get("status") in ["overdue", "burning", "this_week", "upcoming"]]
    if not urgent:
        return '<div style="text-align:center;padding:20px;color:#718096;">No urgent items to include in reminder.</div>'

    rows = ""
    for item in urgent[:15]:
        status = item.get("status", "future")
        badge_color = {"overdue": "#E53E3E", "burning": "#DD6B20", "this_week": "#D69E2E", "upcoming": "#276749"}.get(status, "#718096")
        status_label = STATUS_BADGE_LABEL.get(status, "")
        dd = format_date(item["due_date"])
        rows += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #E2E8F0;font-size:0.82rem;">'
            f'<div><strong>{item.get("name","")}</strong><br><span style="color:#718096;">{item.get("category","")}</span></div>'
            f'<div style="text-align:right;"><span style="color:{badge_color};font-weight:700;">{status_label}</span><br><span style="color:#718096;">{dd}</span></div>'
            f'</div>'
        )
    if len(urgent) > 15:
        rows += f'<div style="text-align:center;padding:10px;color:#718096;font-size:0.82rem;">...and {len(urgent)-15} more items</div>'

    return (
        f'<div class="email-preview">'
        f'<div class="email-preview-header">📧 Email Preview — {len(urgent)} items will be included</div>'
        f'<div class="email-preview-body">{rows}</div>'
        f'</div>'
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 4px 16px;">
      <div style="font-size:1.6rem;font-weight:900;color:#2563AB;letter-spacing:-1px;">📅 DueDash</div>
      <div style="font-size:0.78rem;color:#718096;margin-top:2px;">Smart Compliance Calendar</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Profile</div>', unsafe_allow_html=True)

    entity = st.selectbox("Entity Type", ENTITY_TYPES, key="entity_type")
    state = st.selectbox("State", STATES, key="state")
    industry = st.selectbox("Industry", INDUSTRIES, key="industry")

    st.markdown('<div class="sb-section">Financial Year</div>', unsafe_allow_html=True)
    fy = st.radio("Select FY", SUPPORTED_FYS, key="fy")

    st.markdown('<div class="sb-section">GST Turnover</div>', unsafe_allow_html=True)
    gst_options = list(GST_TURNOVER_OPTIONS.keys())
    gst_label = st.selectbox("Annual Turnover", gst_options, key="gst_label")

    st.markdown("---")

    # Generate button
    if st.button("🔄 Generate Calendar", use_container_width=True, type="primary"):
        with st.spinner("Generating compliance calendar..."):
            st.session_state.calendar = _load_calendar()
        st.success(f"Generated {len(st.session_state.calendar)} compliance items.")

    # Auto-generate on first load
    if st.session_state.calendar is None:
        st.session_state.calendar = _load_calendar()

    st.markdown("---")

    # Export
    if st.session_state.calendar:
        excel_bytes = export_to_excel(
            st.session_state.calendar,
            st.session_state.entity_type,
            st.session_state.state,
            st.session_state.fy,
        )
        st.download_button(
            label="📥 Export to Excel",
            data=excel_bytes,
            file_name=f"DueDash_{st.session_state.entity_type.replace(' ','_')}_{st.session_state.fy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")

    # ── Quick Email Reminder ──────────────────────────────────────────────────
    st.markdown('<div class="sb-section">📧 Send Reminder</div>', unsafe_allow_html=True)
    sidebar_email = st.text_input("Recipient Email", value=st.session_state.alert_email, key="sidebar_email", placeholder="ca@firm.com")
    sidebar_recip = st.text_input("Recipient Name", value="Team", key="sidebar_recip")

    smtp_configured = bool(st.session_state.smtp_user and st.session_state.smtp_password)

    if st.button("📩 Send Email Reminder", use_container_width=True, type="primary"):
        if not smtp_configured:
            st.warning("Configure SMTP in Settings tab first.")
        elif not sidebar_email:
            st.warning("Enter a recipient email.")
        else:
            from integrations.email_sender import EmailSender
            sender = EmailSender(
                st.session_state.smtp_host,
                int(st.session_state.smtp_port),
                st.session_state.smtp_user,
                st.session_state.smtp_password,
            )
            cal = st.session_state.calendar or []
            ok, msg = sender.send_reminder(
                to_email=sidebar_email,
                items=cal,
                entity_type=st.session_state.entity_type,
                state=st.session_state.state,
                fy=st.session_state.fy,
                recipient_name=sidebar_recip,
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if not smtp_configured:
        st.caption("⚙️ Set up SMTP in the Settings tab to enable email reminders.")

    st.markdown("---")
    st.markdown('<div class="sb-section">Today</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.88rem;color:#4A5568;'>{date.today().strftime('%d %B %Y')}</div>", unsafe_allow_html=True)


# ── Main content ──────────────────────────────────────────────────────────────

# Header
st.markdown(f"""
<div class="dd-header">
  <h1>📅 DueDash</h1>
  <p>{APP_TAGLINE} &nbsp;·&nbsp; {st.session_state.entity_type} &nbsp;·&nbsp; {st.session_state.state} &nbsp;·&nbsp; FY {st.session_state.fy}</p>
</div>
""", unsafe_allow_html=True)

# Demo banner
if _is_demo():
    st.markdown("""
    <div class="demo-banner">
      🎯 <strong>Demo Mode</strong> — Running without any API keys. All compliance data is live.
      Configure Google Sheets / Email in the <em>Settings</em> tab to unlock sync & reminders.
    </div>
    """, unsafe_allow_html=True)

# ── Stats row ─────────────────────────────────────────────────────────────────
calendar = st.session_state.calendar or []
counts   = get_urgency_counts(calendar)

stats_cards = "".join([
    _render_stat_card(counts['total'],    'Total',        '#2563AB', '#EBF8FF'),
    _render_stat_card(counts['overdue'],  'Overdue',      '#E53E3E', '#FFF5F5'),
    _render_stat_card(counts['burning'],  'Burning Now',  '#DD6B20', '#FFFAF0'),
    _render_stat_card(counts['this_week'],'This Week',    '#D69E2E', '#FFFFF0'),
    _render_stat_card(counts['upcoming'], 'Next 30 Days', '#276749', '#F0FFF4'),
    _render_stat_card(counts['future'],   'Future',       '#2B6CB0', '#EBF8FF'),
])
st.markdown(f'<div class="stats-grid">{stats_cards}</div>', unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_all, tab_overdue, tab_burning, tab_week, tab_upcoming, tab_future, tab_calendar, tab_charts, tab_table, tab_email, tab_settings = st.tabs([
    f"📋 All ({counts['total']})",
    f"🔴 Overdue ({counts['overdue']})",
    f"🔥 Burning ({counts['burning']})",
    f"⚠️ This Week ({counts['this_week']})",
    f"📅 Next 30 Days ({counts['upcoming']})",
    f"🔵 Future ({counts['future']})",
    "📆 Calendar",
    "📊 Analytics",
    "📋 Table",
    "📧 Email",
    "⚙️ Settings",
])


def _render_tab(items: List[Dict], label: str, show_filters: bool = False):
    if not items:
        st.markdown(_render_empty(label), unsafe_allow_html=True)
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search compliance items", value="", key=f"search_{label}", placeholder="e.g. GSTR-1, TDS, PF...")
    with col2:
        cats = get_categories(items)
        cat_filter = st.selectbox("Category", cats, key=f"cat_{label}")

    # Apply filters
    filtered = items
    if search:
        q = search.lower()
        filtered = [i for i in filtered if q in i["name"].lower() or q in i.get("description","").lower() or q in i.get("category","").lower()]
    if cat_filter != "All":
        filtered = [i for i in filtered if i.get("category") == cat_filter]

    st.markdown(f"<p style='font-size:0.82rem;color:#718096;margin-bottom:12px;'>Showing <strong>{len(filtered)}</strong> of {len(items)} items</p>", unsafe_allow_html=True)

    # Render cards
    cards_html = "".join(_render_compliance_card(item) for item in filtered)
    if cards_html:
        st.markdown(cards_html, unsafe_allow_html=True)
    else:
        st.markdown(_render_empty("matching"), unsafe_allow_html=True)


# ── All Tab ───────────────────────────────────────────────────────────────────
with tab_all:
    _render_tab(calendar, "All")

# ── Overdue Tab ───────────────────────────────────────────────────────────────
with tab_overdue:
    overdue_items = [i for i in calendar if i["status"] == "overdue"]
    if overdue_items:
        st.markdown(f"""
        <div style="background:#FFF5F5;border:1px solid #FEB2B2;border-radius:10px;padding:12px 18px;margin-bottom:16px;">
          <strong style="color:#E53E3E;">⚠️ {len(overdue_items)} compliance item(s) are past their due date.</strong>
          Take immediate action to avoid penalties and prosecution.
        </div>
        """, unsafe_allow_html=True)
    _render_tab(overdue_items, "overdue")

# ── Burning Tab ───────────────────────────────────────────────────────────────
with tab_burning:
    burning_items = [i for i in calendar if i["status"] == "burning"]
    if burning_items:
        st.markdown(f"""
        <div style="background:#FFFAF0;border:1px solid #FBD38D;border-radius:10px;padding:12px 18px;margin-bottom:16px;">
          <strong style="color:#DD6B20;">🔥 {len(burning_items)} item(s) due in the next 3 days.</strong>
          Act today to avoid last-minute scramble.
        </div>
        """, unsafe_allow_html=True)
    _render_tab(burning_items, "Burning Now")

# ── This Week Tab ─────────────────────────────────────────────────────────────
with tab_week:
    week_items = [i for i in calendar if i["status"] == "this_week"]
    _render_tab(week_items, "This Week")

# ── Upcoming Tab ──────────────────────────────────────────────────────────────
with tab_upcoming:
    upcoming_items = [i for i in calendar if i["status"] == "upcoming"]
    _render_tab(upcoming_items, "Next 30 Days")

# ── Future Tab ────────────────────────────────────────────────────────────────
with tab_future:
    future_items = [i for i in calendar if i["status"] == "future"]
    _render_tab(future_items, "Future")

# ── Calendar Tab ──────────────────────────────────────────────────────────────
with tab_calendar:
    if not calendar:
        st.info("No data. Generate the calendar first.")
    else:
        st.markdown(
            '<p style="font-size:0.88rem;color:#718096;margin-bottom:8px;">'
            'Hover over colored dates to see compliance items due on that day. '
            'Click <strong>Generate Calendar</strong> after changing filters.</p>',
            unsafe_allow_html=True,
        )
        cal_html = _render_full_calendar(calendar, st.session_state.fy)
        st.markdown(cal_html, unsafe_allow_html=True)

        # Show items for a selected date
        st.markdown("---")
        st.subheader("Browse by Date")
        sel_date = st.date_input(
            "Select a date to see compliance items",
            value=date.today(),
            key="cal_date_pick",
        )
        date_items = [i for i in calendar if i["due_date"] == sel_date]
        if date_items:
            st.markdown(
                f'<p style="font-size:0.88rem;color:#4A5568;margin-bottom:10px;">'
                f'<strong>{len(date_items)}</strong> item(s) due on <strong>{format_date(sel_date)}</strong></p>',
                unsafe_allow_html=True,
            )
            cards_html = "".join(_render_compliance_card(item) for item in date_items)
            st.markdown(cards_html, unsafe_allow_html=True)
        else:
            st.markdown(
                f'<p style="font-size:0.88rem;color:#A0AEC0;">No compliance items due on {format_date(sel_date)}.</p>',
                unsafe_allow_html=True,
            )

# ── Analytics Tab ─────────────────────────────────────────────────────────────
with tab_charts:
    if not calendar:
        st.info("No data. Generate the calendar first.")
    else:
        fig_status, fig_cat, fig_timeline, fig_pri = _render_charts(calendar, counts)

        # Row 1: Status donut + Priority
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.plotly_chart(fig_status, use_container_width=True, key="chart_status")
        with col_ch2:
            st.plotly_chart(fig_pri, use_container_width=True, key="chart_pri")

        # Row 2: Timeline
        st.plotly_chart(fig_timeline, use_container_width=True, key="chart_timeline")

        # Row 3: Category
        st.plotly_chart(fig_cat, use_container_width=True, key="chart_cat")

        # Summary stats
        st.markdown("---")
        st.markdown(
            '<p style="font-size:0.82rem;color:#718096;text-align:center;">'
            f'Analytics for <strong>{st.session_state.entity_type}</strong> | '
            f'<strong>{st.session_state.state}</strong> | '
            f'<strong>FY {st.session_state.fy}</strong> | '
            f'{counts["total"]} total compliance items</p>',
            unsafe_allow_html=True,
        )

# ── Table View Tab ────────────────────────────────────────────────────────────
with tab_table:
    if not calendar:
        st.info("No data. Generate the calendar first.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            status_options = ["All"] + list(STATUS_BADGE_LABEL.values())
            status_filter  = st.selectbox("Filter by Status", status_options, key="table_status")
        with col2:
            all_cats = get_categories(calendar)
            cat_f    = st.selectbox("Filter by Category", all_cats, key="table_cat")
        with col3:
            search_t = st.text_input("Search", key="table_search", placeholder="name, form...")

        # Build display dataframe
        filtered = calendar
        if status_filter != "All":
            rev_map = {v: k for k, v in STATUS_BADGE_LABEL.items()}
            s_key   = rev_map.get(status_filter)
            if s_key:
                filtered = [i for i in filtered if i["status"] == s_key]
        if cat_f != "All":
            filtered = [i for i in filtered if i.get("category") == cat_f]
        if search_t:
            q = search_t.lower()
            filtered = [i for i in filtered if q in i["name"].lower() or q in i.get("form_number","").lower()]

        rows = []
        for item in filtered:
            days = item.get("days_remaining", 0)
            rows.append({
                "Category":   item.get("category", ""),
                "Name":       item.get("name", ""),
                "Due Date":   format_date(item["due_date"]),
                "Period":     item.get("period", ""),
                "Days":       days if isinstance(days, int) else "",
                "Status":     STATUS_BADGE_LABEL.get(item.get("status",""), ""),
                "Form":       item.get("form_number", ""),
                "Priority":   item.get("priority", "").capitalize(),
            })

        df = pd.DataFrame(rows)
        st.markdown(f"<p style='font-size:0.82rem;color:#718096;'>Showing {len(df)} items</p>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

        # Export from table view too
        excel_bytes = export_to_excel(
            filtered,
            st.session_state.entity_type,
            st.session_state.state,
            st.session_state.fy,
        )
        st.download_button(
            "📥 Download filtered data as Excel",
            data=excel_bytes,
            file_name=f"DueDash_filtered_{st.session_state.fy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ── Email Tab ─────────────────────────────────────────────────────────────────
with tab_email:
    st.markdown(
        '<p style="font-size:0.92rem;color:#2D3748;margin-bottom:16px;">'
        'Send beautifully formatted compliance reminder emails directly from DueDash. '
        'Configure your SMTP credentials below, then hit <strong>Send</strong>.</p>',
        unsafe_allow_html=True,
    )

    col_email_l, col_email_r = st.columns([1, 1])

    with col_email_l:
        st.markdown("**📧 Email Configuration**")
        em_host = st.text_input("SMTP Host", value=st.session_state.smtp_host, key="em_smtp_host", placeholder="smtp.gmail.com")
        em_port = st.number_input("SMTP Port", value=st.session_state.smtp_port, min_value=1, max_value=65535, key="em_smtp_port")
        em_user = st.text_input("SMTP Username / Email", value=st.session_state.smtp_user, key="em_smtp_user", placeholder="your@gmail.com")
        em_pass = st.text_input("App Password", value=st.session_state.smtp_password, type="password", key="em_smtp_pass", placeholder="16-character App Password")

        if st.button("💾 Save SMTP Config", use_container_width=True, key="em_save"):
            st.session_state.smtp_host = em_host
            st.session_state.smtp_port = em_port
            st.session_state.smtp_user = em_user
            st.session_state.smtp_password = em_pass
            st.success("SMTP config saved for this session!")

        if st.button("🔌 Test SMTP Connection", use_container_width=True, key="em_test"):
            if not em_user or not em_pass:
                st.warning("Enter SMTP credentials first.")
            else:
                from integrations.email_sender import EmailSender
                sender = EmailSender(em_host, int(em_port), em_user, em_pass)
                ok, msg = sender.test_connection()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        with st.expander("📖 Gmail Setup Guide"):
            st.markdown("""
**To use Gmail as SMTP:**
1. Enable **2-Factor Authentication** on your Google Account
2. Go to **Google Account** → **Security** → **App Passwords**
3. Create an App Password for "Mail"
4. Use that **16-character password** above (NOT your Gmail password)
5. SMTP Host: `smtp.gmail.com` | Port: `587`

**For Outlook / Office 365:**
- SMTP Host: `smtp.office365.com` | Port: `587`
- Use your Office 365 credentials
            """)

    with col_email_r:
        st.markdown("**📩 Send Reminder**")
        em_to   = st.text_input("Recipient Email", value=st.session_state.alert_email, key="em_to", placeholder="client@company.com")
        em_name = st.text_input("Recipient Name", value="Team", key="em_name")
        em_filter = st.multiselect(
            "Include items with status",
            ["Overdue", "Burning Now", "This Week", "Next 30 Days"],
            default=["Overdue", "Burning Now", "This Week", "Next 30 Days"],
            key="em_filter",
        )
        status_map = {"Overdue": "overdue", "Burning Now": "burning", "This Week": "this_week", "Next 30 Days": "upcoming"}
        selected_statuses = [status_map[s] for s in em_filter]

        # Email preview
        preview_items = [i for i in calendar if i.get("status") in selected_statuses]
        st.markdown(_build_email_preview_items(preview_items), unsafe_allow_html=True)

        if st.button("📩 Send Compliance Reminder", use_container_width=True, type="primary", key="em_send"):
            if not em_user or not em_pass:
                st.error("Configure and save SMTP credentials first (left panel).")
            elif not em_to:
                st.warning("Enter a recipient email address.")
            elif not preview_items:
                st.info("No items match the selected statuses. Nothing to send.")
            else:
                from integrations.email_sender import EmailSender
                sender = EmailSender(
                    st.session_state.smtp_host,
                    int(st.session_state.smtp_port),
                    st.session_state.smtp_user,
                    st.session_state.smtp_password,
                )
                ok, msg = sender.send_reminder(
                    to_email=em_to,
                    items=calendar,
                    entity_type=st.session_state.entity_type,
                    state=st.session_state.state,
                    fy=st.session_state.fy,
                    recipient_name=em_name,
                    days_filter=selected_statuses,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")

# ── Settings Tab ──────────────────────────────────────────────────────────────
with tab_settings:
    col_left, col_right = st.columns(2)

    with col_left:
        # ── Email Settings ────────────────────────────────────────────────────
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">📧 Email Reminder Settings</div>', unsafe_allow_html=True)
        st.caption("Configure SMTP to send automated compliance reminders.")

        smtp_host = st.text_input("SMTP Host", value=st.session_state.smtp_host, key="inp_smtp_host", placeholder="smtp.gmail.com")
        smtp_port = st.number_input("SMTP Port", value=st.session_state.smtp_port, min_value=1, max_value=65535, key="inp_smtp_port")
        smtp_user = st.text_input("SMTP Username / Email", value=st.session_state.smtp_user, key="inp_smtp_user", placeholder="your@gmail.com")
        smtp_pass = st.text_input("App Password", value=st.session_state.smtp_password, type="password", key="inp_smtp_pass", placeholder="App password (not Gmail password)")
        alert_to  = st.text_input("Send Reminders To", value=st.session_state.alert_email, key="inp_alert_email", placeholder="ca@example.com")
        recip_name = st.text_input("Recipient Name", value="Team", key="inp_recip_name")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Save Email Config", use_container_width=True):
                st.session_state.smtp_host     = smtp_host
                st.session_state.smtp_port     = smtp_port
                st.session_state.smtp_user     = smtp_user
                st.session_state.smtp_password = smtp_pass
                st.session_state.alert_email   = alert_to
                st.success("Email config saved!")
        with col_b:
            if st.button("🔌 Test Connection", use_container_width=True):
                if not smtp_user:
                    st.warning("Enter SMTP credentials first.")
                else:
                    from integrations.email_sender import EmailSender
                    sender = EmailSender(smtp_host, int(smtp_port), smtp_user, smtp_pass)
                    ok, msg = sender.test_connection()
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        if st.button("📩 Send Test Reminder Now", use_container_width=True, type="primary"):
            if not smtp_user or not alert_to:
                st.warning("Configure SMTP credentials and recipient email first.")
            else:
                from integrations.email_sender import EmailSender
                sender = EmailSender(smtp_host, int(smtp_port), smtp_user, smtp_pass)
                urgent = [i for i in calendar if i.get("status") in ["overdue", "burning", "this_week", "upcoming"]]
                ok, msg = sender.send_reminder(
                    to_email       = alert_to,
                    items          = urgent,
                    entity_type    = st.session_state.entity_type,
                    state          = st.session_state.state,
                    fy             = st.session_state.fy,
                    recipient_name = recip_name,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)

        # Gmail help
        with st.expander("📖 Gmail Setup Guide"):
            st.markdown("""
**To use Gmail as SMTP:**
1. Enable 2-Factor Authentication on your Google Account
2. Go to **Google Account → Security → App Passwords**
3. Create an App Password for "Mail"
4. Use that 16-character password above (not your Gmail password)
5. SMTP Host: `smtp.gmail.com`, Port: `587`

**For Outlook/Office 365:**
- SMTP Host: `smtp.office365.com`, Port: `587`
- Use your Office 365 credentials
            """)

    with col_right:
        # ── Google Sheets Settings ────────────────────────────────────────────
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">📊 Google Sheets Integration</div>', unsafe_allow_html=True)
        st.caption("Sync compliance calendar to a Google Sheet for team collaboration.")

        gs_creds = st.text_input("Service Account JSON Path", value=st.session_state.gsheets_creds, key="inp_gs_creds", placeholder="/path/to/service-account.json")
        gs_id    = st.text_input("Spreadsheet ID", value=st.session_state.gsheets_id, key="inp_gs_id", placeholder="Paste Sheet ID from URL")
        gs_name  = st.text_input("Sheet Name", value=st.session_state.gsheets_name, key="inp_gs_name")

        col_c, col_d = st.columns(2)
        with col_c:
            if st.button("💾 Save Sheets Config", use_container_width=True):
                st.session_state.gsheets_creds = gs_creds
                st.session_state.gsheets_id    = gs_id
                st.session_state.gsheets_name  = gs_name
                st.success("Sheets config saved!")
        with col_d:
            if st.button("🔌 Test Sheets", use_container_width=True):
                if not gs_creds or not gs_id:
                    st.warning("Enter credentials and Sheet ID first.")
                else:
                    from integrations.google_sheets import GoogleSheetsIntegration
                    gs = GoogleSheetsIntegration(gs_creds, gs_id, gs_name)
                    ok, msg = gs.connect()
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        if st.button("☁️ Sync Calendar to Sheets", use_container_width=True, type="primary"):
            if not gs_creds or not gs_id:
                st.warning("Configure Google Sheets credentials first.")
            else:
                from integrations.google_sheets import GoogleSheetsIntegration
                gs = GoogleSheetsIntegration(gs_creds, gs_id, gs_name)
                ok, msg = gs.write_calendar(
                    items       = calendar,
                    entity_type = st.session_state.entity_type,
                    state       = st.session_state.state,
                    fy          = st.session_state.fy,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📖 Google Sheets Setup Guide"):
            st.markdown("""
**To connect Google Sheets:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Sheets API** + **Drive API**
3. Create a **Service Account** → Download JSON credentials
4. Share your Google Sheet with the service account email
5. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/**SHEET_ID**/edit`
6. Paste the JSON file path and Sheet ID above
            """)

        # ── Penalty Reference ─────────────────────────────────────────────────
        st.markdown('<div class="settings-card" style="margin-top:16px;">', unsafe_allow_html=True)
        st.markdown('<div class="settings-title">⚖️ Quick Penalty Reference</div>', unsafe_allow_html=True)
        penalties = [
            ("Late ITR Filing",        "Rs 5,000 (Rs 1,000 if income < 5L) u/s 234F"),
            ("TDS Late Deposit",       "1%/month for late deduction, 1.5%/month for late deposit"),
            ("TDS Return Late",        "Rs 200/day u/s 234E (min = TDS amount)"),
            ("GSTR-1/3B Late",         "Rs 50/day (Rs 20 for nil). Max Rs 10,000"),
            ("GST Non-Payment",        "18% p.a. interest on unpaid tax"),
            ("ROC AOC-4 Late",         "Rs 1,000/day, max Rs 10 lakh"),
            ("PF Late Deposit",        "12% p.a. interest + 5-25% damages"),
            ("Tax Audit Default",      "0.5% of turnover, max Rs 1.5 lakh u/s 271B"),
        ]
        penalty_html = "".join([
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #E2E8F0;font-size:0.82rem;">'
            f'<span style="font-weight:600;color:#2D3748;">{k}</span>'
            f'<span style="color:#E53E3E;text-align:right;max-width:55%;">{v}</span></div>'
            for k, v in penalties
        ])
        st.markdown(penalty_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#A0AEC0;font-size:0.78rem;padding:8px 0 16px;">
  <strong style="color:#4A90D9;">DueDash</strong> &nbsp;·&nbsp; Smart Compliance Calendar for Indian Businesses &nbsp;·&nbsp;
  AICA Level 2 Capstone &nbsp;·&nbsp; FY {st.session_state.fy} &nbsp;·&nbsp;
  Data current as of AY 2026-27 &nbsp;·&nbsp;
  <em>Consult your CA for professional advice.</em>
</div>
""", unsafe_allow_html=True)
