"""
DueDash Helper Utilities
Excel export, date formatting, summary stats, filtering.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import pandas as pd


# ── Date helpers ──────────────────────────────────────────────────────────────

def format_date(d: date) -> str:
    """Return '15 Jun 2025' style string."""
    if not hasattr(d, "strftime"):
        return str(d)
    return d.strftime("%d %b %Y").lstrip("0")


def days_label(days: int) -> str:
    """Human-friendly days-remaining label."""
    if days < 0:
        return f"{abs(days)} day{'s' if abs(days) != 1 else ''} overdue"
    if days == 0:
        return "Due TODAY"
    if days == 1:
        return "Due TOMORROW"
    return f"{days} days remaining"


def fy_label(fy: str) -> str:
    """'2025-26' → 'FY 2025-26'"""
    return f"FY {fy}"


# ── Summary statistics ────────────────────────────────────────────────────────

def compute_summary(items: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "total":    len(items),
        "overdue":  0,
        "burning":  0,
        "this_week": 0,
        "upcoming": 0,
        "future":   0,
        "done":     0,
    }
    for item in items:
        status = item.get("status", "future")
        if status in counts:
            counts[status] += 1
    return counts


# ── Filtering ─────────────────────────────────────────────────────────────────

def filter_items(
    items: List[Dict],
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict]:
    result = items
    if status_filter and status_filter != "all":
        result = [i for i in result if i.get("status") == status_filter]
    if category_filter and category_filter != "All":
        result = [i for i in result if i.get("category") == category_filter]
    if search:
        q = search.lower()
        result = [
            i for i in result
            if q in i.get("name", "").lower()
            or q in i.get("description", "").lower()
            or q in i.get("category", "").lower()
        ]
    return result


# ── Excel export ──────────────────────────────────────────────────────────────

STATUS_ORDER = {"overdue": 0, "burning": 1, "this_week": 2, "upcoming": 3, "future": 4, "done": 5}

STATUS_LABELS = {
    "overdue":   "Overdue",
    "burning":   "Burning Now",
    "this_week": "This Week",
    "upcoming":  "Next 30 Days",
    "future":    "Future",
    "done":      "Done",
}

CATEGORY_COLORS_HEX = {
    "Income Tax":          "4A90D9",
    "GST":                 "7C3AED",
    "ROC / MCA":           "EA580C",
    "TDS / TCS":           "0D9488",
    "PF":                  "9333EA",
    "ESI":                 "16A34A",
    "Professional Tax":    "CA8A04",
    "Labour Welfare Fund": "0284C7",
    "Shop & Establishment":"DB2777",
    "Industry-Specific":   "059669",
}

STATUS_BG = {
    "overdue":   "FFCCCC",
    "burning":   "FFE0B2",
    "this_week": "FFF9C4",
    "upcoming":  "C8E6C9",
    "future":    "BBDEFB",
    "done":      "ECEFF1",
}


def export_to_excel(items: List[Dict], entity_type: str, state: str, fy: str) -> bytes:
    """Return a styled Excel workbook as bytes."""
    rows = []
    for item in items:
        dd = item.get("due_date")
        due_str = format_date(dd) if dd else ""
        days = item.get("days_remaining", "")
        rows.append({
            "Category":        item.get("category", ""),
            "Sub-Category":    item.get("sub_category", ""),
            "Compliance Name": item.get("name", ""),
            "Description":     item.get("description", ""),
            "Due Date":        due_str,
            "Period":          item.get("period", ""),
            "Days Remaining":  days if isinstance(days, int) else "",
            "Status":          STATUS_LABELS.get(item.get("status", ""), ""),
            "Form / Return":   item.get("form_number", ""),
            "Penalty":         item.get("penalty", ""),
            "Priority":        item.get("priority", "medium").capitalize(),
        })

    df = pd.DataFrame(rows)
    df["_sort"] = df["Status"].map({v: k for k, v in STATUS_LABELS.items()}).map(STATUS_ORDER).fillna(99)
    df = df.sort_values("_sort").drop(columns=["_sort"])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheet_name = "Compliance Calendar"
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        wb  = writer.book
        ws  = writer.sheets[sheet_name]

        # Header format
        hdr_fmt = wb.add_format({
            "bold": True, "font_color": "FFFFFF", "bg_color": "2563AB",
            "border": 1, "text_wrap": True, "valign": "vcenter", "align": "center",
        })

        col_widths = [14, 18, 36, 50, 14, 22, 14, 14, 16, 40, 10]
        for col_num, (col_name, width) in enumerate(zip(df.columns, col_widths)):
            ws.write(0, col_num, col_name, hdr_fmt)
            ws.set_column(col_num, col_num, width)

        ws.set_row(0, 22)

        # Status colour formats
        status_fmts = {
            s: wb.add_format({"bg_color": bg, "border": 1, "text_wrap": True, "valign": "vcenter"})
            for s, bg in STATUS_BG.items()
        }
        default_fmt = wb.add_format({"border": 1, "text_wrap": True, "valign": "vcenter"})

        # Data rows
        status_col = list(df.columns).index("Status")
        for row_num, row_data in enumerate(df.itertuples(index=False), start=1):
            label = row_data[status_col]
            rev_map = {v: k for k, v in STATUS_LABELS.items()}
            status_key = rev_map.get(label, "future")
            row_fmt = status_fmts.get(status_key, default_fmt)
            ws.set_row(row_num, 18, row_fmt)

        # Auto filter + freeze header
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)
        ws.freeze_panes(1, 0)

        # Summary sheet
        summary_data = {
            "Metric": ["Entity Type", "State", "Financial Year", "Total Items",
                       "Overdue", "Burning Now (0-3 days)", "This Week (4-7 days)",
                       "Next 30 Days", "Future", "Report Generated"],
            "Value": [
                entity_type, state, f"FY {fy}", len(items),
                sum(1 for i in items if i.get("status") == "overdue"),
                sum(1 for i in items if i.get("status") == "burning"),
                sum(1 for i in items if i.get("status") == "this_week"),
                sum(1 for i in items if i.get("status") == "upcoming"),
                sum(1 for i in items if i.get("status") == "future"),
                datetime.now().strftime("%d %b %Y %H:%M"),
            ],
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, index=False, sheet_name="Summary")

        ws2 = writer.sheets["Summary"]
        s_hdr = wb.add_format({"bold": True, "bg_color": "2563AB", "font_color": "FFFFFF", "border": 1})
        s_val = wb.add_format({"border": 1})
        ws2.set_column(0, 0, 30)
        ws2.set_column(1, 1, 35)
        for col_num, col_name in enumerate(df_summary.columns):
            ws2.write(0, col_num, col_name, s_hdr)
        for row_num, row_data in enumerate(df_summary.itertuples(index=False), start=1):
            for col_num, val in enumerate(row_data):
                ws2.write(row_num, col_num, str(val), s_val)

    return output.getvalue()


# ── Category list ─────────────────────────────────────────────────────────────

def get_categories(items: List[Dict]) -> List[str]:
    return ["All"] + sorted({i.get("category", "") for i in items if i.get("category")})
