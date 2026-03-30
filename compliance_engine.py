"""
DueDash Compliance Engine
Generates a full compliance calendar for FY 2025-26 / 2026-27 based on
entity type, state, industry and GST turnover.

All due dates follow Indian statutory requirements:
- Income Tax Act 1961
- GST Acts (CGST/SGST) 2017
- Companies Act 2013
- PF Act / ESI Act
- State PT Acts
- State LWF Acts
"""

from __future__ import annotations

import calendar
import json
import os
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

ENTITY_TYPES = [
    "Private Company",
    "LLP",
    "Partnership",
    "Proprietorship",
    "Individual",
    "Trust",
    "Society",
]

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu & Kashmir", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal",
]

INDUSTRIES = [
    "General",
    "Manufacturing",
    "IT / ITES",
    "Healthcare",
    "Construction / Real Estate",
    "Trading / Import-Export",
    "FMCG / Food Processing",
    "Financial Services",
]

GST_TURNOVER_OPTIONS = {
    "Not Registered for GST": 0,
    "Up to Rs 1.5 Cr (Quarterly QRMP)": 0.5,
    "Rs 1.5 Cr – Rs 5 Cr (Quarterly QRMP)": 3.0,
    "Above Rs 5 Cr (Monthly Filing)": 10.0,
}

STATUS_LABELS = {
    "overdue":   "Overdue",
    "burning":   "Burning Now",
    "this_week": "This Week",
    "upcoming":  "Next 30 Days",
    "future":    "Future",
    "done":      "Done",
}

# QRMP Category I states (22nd due date for GSTR-3B quarterly)
QRMP_CAT1_STATES = {
    "Andhra Pradesh", "Chhattisgarh", "Gujarat", "Karnataka", "Kerala",
    "Goa", "Maharashtra", "Madhya Pradesh", "Tamil Nadu", "Telangana",
    "Lakshadweep", "Daman and Diu", "Dadra & Nagar Haveli",
}


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_state_data() -> Dict:
    path = os.path.join(DATA_DIR, "state_compliances.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_industry_data() -> Dict:
    path = os.path.join(DATA_DIR, "industry_compliances.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Date utilities ────────────────────────────────────────────────────────────

def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _safe_date(year: int, month: int, day: int) -> date:
    """Clamp day to last day of month to handle Feb 28/29 etc."""
    day = min(day, _last_day(year, month))
    return date(year, month, day)


def _month_name(month: int) -> str:
    return date(2000, month, 1).strftime("%b")


def _fy_months(fy_year: int) -> List[Tuple[int, int]]:
    """Return (year, month) tuples for Apr–Mar of the FY."""
    months = []
    for m in range(4, 13):
        months.append((fy_year, m))
    for m in range(1, 4):
        months.append((fy_year + 1, m))
    return months


def _compute_status(due: date, today: date) -> str:
    delta = (due - today).days
    if delta < 0:
        return "overdue"
    elif delta <= 3:
        return "burning"
    elif delta <= 7:
        return "this_week"
    elif delta <= 30:
        return "upcoming"
    else:
        return "future"


def _item(
    *,
    id: str,
    category: str,
    sub_category: str,
    name: str,
    description: str,
    due_date: date,
    period: str = "",
    form_number: str = "",
    penalty: str = "",
    priority: str = "medium",
    applicable_entities: Optional[List[str]] = None,
) -> Dict:
    return {
        "id":                   id,
        "category":             category,
        "sub_category":         sub_category,
        "name":                 name,
        "description":          description,
        "due_date":             due_date,
        "period":               period,
        "form_number":          form_number,
        "penalty":              penalty,
        "priority":             priority,
        "applicable_entities":  applicable_entities or ENTITY_TYPES,
        "status":               "future",  # computed later
        "days_remaining":       0,         # computed later
    }


# ── Income Tax ────────────────────────────────────────────────────────────────

def _advance_tax(fy_year: int, entity_type: str) -> List[Dict]:
    """Advance Tax installments for the FY."""
    items = []
    if entity_type == "Individual" and False:  # future: add salary-only exclusion
        return []
    quarters = [
        (date(fy_year, 6, 15),     "Q1 (15% of estimated tax)",   1),
        (date(fy_year, 9, 15),     "Q2 (cumulative 45%)",          2),
        (date(fy_year, 12, 15),    "Q3 (cumulative 75%)",          3),
        (date(fy_year + 1, 3, 15), "Q4 (100% – full payment)",     4),
    ]
    for due, note, q in quarters:
        items.append(_item(
            id=f"adv_tax_q{q}_{fy_year}",
            category="Income Tax",
            sub_category="Advance Tax",
            name=f"Advance Tax – Installment {q}",
            description=f"{note}. Sec 208/211 – mandatory if estimated tax liability ≥ Rs 10,000.",
            due_date=due,
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="Challan ITNS 280",
            penalty="Interest u/s 234B & 234C @ 1% per month on shortfall",
            priority="high",
            applicable_entities=["Private Company", "LLP", "Partnership", "Proprietorship", "Individual", "Trust", "Society"],
        ))
    return items


def _itr_items(fy_year: int, entity_type: str) -> List[Dict]:
    """ITR filing due dates (filed after FY ends)."""
    ay_year = fy_year + 1
    items   = []

    if entity_type == "Private Company":
        items.append(_item(
            id=f"itr_company_{fy_year}",
            category="Income Tax",
            sub_category="ITR Filing",
            name=f"ITR-6: Company Income Tax Return (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="Annual Income Tax Return for companies u/s 139(1). Tax audit mandatory if turnover > Rs 1 Cr.",
            due_date=date(ay_year, 10, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="ITR-6",
            penalty="Late filing fee u/s 234F: Rs 5,000 (Rs 1,000 if income < Rs 5L). Interest u/s 234A.",
            priority="high",
            applicable_entities=["Private Company"],
        ))
    elif entity_type == "LLP":
        items.append(_item(
            id=f"itr_llp_{fy_year}",
            category="Income Tax",
            sub_category="ITR Filing",
            name=f"ITR-5: LLP Income Tax Return (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="ITR for LLP/firm u/s 139(1). Audit u/s 44AB if turnover > Rs 1 Cr.",
            due_date=date(ay_year, 10, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="ITR-5",
            penalty="Late filing fee u/s 234F: Rs 5,000. Interest u/s 234A.",
            priority="high",
            applicable_entities=["LLP"],
        ))
    elif entity_type == "Partnership":
        items.append(_item(
            id=f"itr_partnership_{fy_year}",
            category="Income Tax",
            sub_category="ITR Filing",
            name=f"ITR-5: Partnership Firm IT Return (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="ITR-5 for partnership firms. Audit if turnover > Rs 1 Cr (business) or Rs 50L (profession).",
            due_date=date(ay_year, 10, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="ITR-5",
            penalty="Late filing fee u/s 234F. Interest u/s 234A.",
            priority="high",
            applicable_entities=["Partnership"],
        ))
    elif entity_type in ["Proprietorship", "Individual"]:
        # Non-audit: 31 Jul; Audit: 31 Oct
        items.append(_item(
            id=f"itr_individual_{fy_year}",
            category="Income Tax",
            sub_category="ITR Filing",
            name=f"ITR-3/4: Business Income Tax Return (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="ITR-3/4 for individual/proprietor with business income. Non-audit due 31 Jul; audit cases 31 Oct.",
            due_date=date(ay_year, 7, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="ITR-3 / ITR-4 (Sugam)",
            penalty="Late filing fee u/s 234F: Rs 5,000 (Rs 1,000 if income < Rs 5L).",
            priority="high",
            applicable_entities=["Proprietorship", "Individual"],
        ))
        if entity_type == "Proprietorship":
            items.append(_item(
                id=f"itr_proprietorship_audit_{fy_year}",
                category="Income Tax",
                sub_category="ITR Filing",
                name=f"ITR-3: Proprietorship (Audit Case) – AY {ay_year}-{str(ay_year+1)[-2:]}",
                description="If turnover > Rs 1 Cr, audit u/s 44AB is mandatory. ITR due 31 Oct.",
                due_date=date(ay_year, 10, 31),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="ITR-3",
                penalty="Penalty u/s 271B: 0.5% of turnover (max Rs 1.5 lakh) for non-audit.",
                priority="medium",
                applicable_entities=["Proprietorship"],
            ))
    elif entity_type in ["Trust", "Society"]:
        items.append(_item(
            id=f"itr_trust_{fy_year}",
            category="Income Tax",
            sub_category="ITR Filing",
            name=f"ITR-7: Trust/Society IT Return (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="ITR-7 for trusts, societies and institutions claiming exemption u/s 11, 12, 12A.",
            due_date=date(ay_year, 10, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="ITR-7",
            penalty="Loss of exemption; late fee u/s 234F.",
            priority="high",
            applicable_entities=["Trust", "Society"],
        ))

    # Tax Audit Report (3CA/3CB/3CD)
    audit_entities = ["Private Company", "LLP", "Partnership", "Proprietorship"]
    if entity_type in audit_entities:
        items.append(_item(
            id=f"tax_audit_{fy_year}",
            category="Income Tax",
            sub_category="Tax Audit",
            name=f"Tax Audit Report – Form 3CA/3CB/3CD (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="CA-certified audit report mandatory if turnover > Rs 1 Cr (business) or Rs 50L (profession). Upload on Income Tax portal.",
            due_date=date(ay_year, 9, 30),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="Form 3CA/3CB + Form 3CD",
            penalty="Penalty u/s 271B: 0.5% of gross turnover, minimum Rs 500, maximum Rs 1,50,000.",
            priority="high",
            applicable_entities=audit_entities,
        ))

    # Transfer Pricing Audit (Form 3CEB)
    if entity_type in ["Private Company", "LLP"]:
        items.append(_item(
            id=f"tp_audit_{fy_year}",
            category="Income Tax",
            sub_category="Transfer Pricing",
            name=f"Transfer Pricing Audit Report – Form 3CEB (AY {ay_year}-{str(ay_year+1)[-2:]})",
            description="Mandatory for entities with international/specified domestic transactions above threshold.",
            due_date=date(ay_year, 10, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="Form 3CEB",
            penalty="Rs 1,00,000 per international transaction not reported.",
            priority="medium",
            applicable_entities=["Private Company", "LLP"],
        ))

    return items


# ── TDS / TCS ──────────────────────────────────────────────────────────────────

def _tds_deposit(fy_year: int, entity_type: str) -> List[Dict]:
    """Monthly TDS/TCS deposit items (7th of next month; 30 Apr for March)."""
    items       = []
    depositors  = ["Private Company", "LLP", "Partnership", "Proprietorship"]
    if entity_type not in depositors:
        return []

    for year, month in _fy_months(fy_year):
        # Deposit due in following month
        dep_month = month + 1 if month < 12 else 1
        dep_year  = year if month < 12 else year + 1

        if month == 3:  # March TDS → 30 April
            due = date(dep_year, 4, 30)
        else:
            due = _safe_date(dep_year, dep_month, 7)

        period_str = f"{_month_name(month)} {year}"
        items.append(_item(
            id=f"tds_dep_{year}_{month:02d}",
            category="TDS / TCS",
            sub_category="TDS Deposit",
            name=f"TDS / TCS Deposit – {period_str}",
            description=f"Monthly deposit of Tax Deducted/Collected at Source for {period_str}. Government deductors: same day.",
            due_date=due,
            period=period_str,
            form_number="Challan ITNS 281",
            penalty="Interest u/s 201(1A): 1%/month for late deduction, 1.5%/month for late deposit.",
            priority="high",
            applicable_entities=depositors,
        ))
    return items


def _tds_returns(fy_year: int, entity_type: str) -> List[Dict]:
    """Quarterly TDS/TCS Returns."""
    depositors = ["Private Company", "LLP", "Partnership", "Proprietorship"]
    if entity_type not in depositors:
        return []
    quarters = [
        ("Q1", f"Apr–Jun {fy_year}",         date(fy_year, 7, 31)),
        ("Q2", f"Jul–Sep {fy_year}",         date(fy_year, 10, 31)),
        ("Q3", f"Oct–Dec {fy_year}",         date(fy_year + 1, 1, 31)),
        ("Q4", f"Jan–Mar {fy_year + 1}",     date(fy_year + 1, 5, 31)),
    ]
    items = []
    for q, period, due in quarters:
        items.append(_item(
            id=f"tds_return_{q}_{fy_year}",
            category="TDS / TCS",
            sub_category="TDS Return",
            name=f"TDS Return ({q}) – {period}",
            description=f"Quarterly TDS/TCS Statement for {period}. Form 24Q (salaries), 26Q (non-salaries), 27Q (NRI payments), 27EQ (TCS).",
            due_date=due,
            period=period,
            form_number="Form 24Q / 26Q / 27Q / 27EQ",
            penalty="Rs 200/day u/s 234E (minimum: TDS amount). Rs 10,000–1,00,000 u/s 271H.",
            priority="high",
            applicable_entities=depositors,
        ))
    return items


# ── GST ───────────────────────────────────────────────────────────────────────

def _gst_gstr1_monthly(fy_year: int) -> List[Dict]:
    """GSTR-1 Monthly (turnover > 5 Cr or opted monthly)."""
    items = []
    for year, month in _fy_months(fy_year):
        dep_m = month + 1 if month < 12 else 1
        dep_y = year if month < 12 else year + 1
        due   = _safe_date(dep_y, dep_m, 11)
        period_str = f"{_month_name(month)} {year}"
        items.append(_item(
            id=f"gstr1_m_{year}_{month:02d}",
            category="GST",
            sub_category="GSTR-1 (Monthly)",
            name=f"GSTR-1 – {period_str}",
            description=f"Monthly outward supplies return for {period_str}. Includes B2B, B2C, CDN, export invoices.",
            due_date=due,
            period=period_str,
            form_number="GSTR-1",
            penalty="Late fee: Rs 50/day (Rs 20/day for nil return). Max Rs 10,000.",
            priority="high",
        ))
    return items


def _gst_gstr1_quarterly(fy_year: int) -> List[Dict]:
    """GSTR-1 Quarterly under QRMP (turnover ≤ 5 Cr)."""
    quarters = [
        ("Q1", f"Apr–Jun {fy_year}",       date(fy_year, 7, 31)),
        ("Q2", f"Jul–Sep {fy_year}",       date(fy_year, 10, 31)),
        ("Q3", f"Oct–Dec {fy_year}",       date(fy_year + 1, 1, 31)),
        ("Q4", f"Jan–Mar {fy_year + 1}",   date(fy_year + 1, 4, 30)),
    ]
    items = []
    for q, period, due in quarters:
        items.append(_item(
            id=f"gstr1_q_{q}_{fy_year}",
            category="GST",
            sub_category="GSTR-1 (Quarterly QRMP)",
            name=f"GSTR-1 ({q}) – {period}",
            description=f"Quarterly GSTR-1 for QRMP taxpayers. Period: {period}. IFF optional for B2B in months 1 & 2 of quarter.",
            due_date=due,
            period=period,
            form_number="GSTR-1 / IFF",
            penalty="Late fee: Rs 50/day. Max Rs 10,000.",
            priority="high",
        ))
    return items


def _gst_gstr3b_monthly(fy_year: int) -> List[Dict]:
    """GSTR-3B Monthly (turnover > 5 Cr)."""
    items = []
    for year, month in _fy_months(fy_year):
        dep_m = month + 1 if month < 12 else 1
        dep_y = year if month < 12 else year + 1
        due   = _safe_date(dep_y, dep_m, 20)
        period_str = f"{_month_name(month)} {year}"
        items.append(_item(
            id=f"gstr3b_m_{year}_{month:02d}",
            category="GST",
            sub_category="GSTR-3B (Monthly)",
            name=f"GSTR-3B – {period_str}",
            description=f"Monthly summary return & tax payment for {period_str}. Declare outward/inward supplies, pay GST liability.",
            due_date=due,
            period=period_str,
            form_number="GSTR-3B",
            penalty="Late fee: Rs 50/day (Rs 20 for nil). Interest @ 18% p.a. on unpaid tax.",
            priority="high",
        ))
    return items


def _gst_gstr3b_quarterly(fy_year: int, state: str) -> List[Dict]:
    """GSTR-3B Quarterly under QRMP (22nd/24th based on state category)."""
    due_day = 22 if state in QRMP_CAT1_STATES else 24
    quarters = [
        ("Q1", f"Apr–Jun {fy_year}",       (fy_year, 7)),
        ("Q2", f"Jul–Sep {fy_year}",       (fy_year, 10)),
        ("Q3", f"Oct–Dec {fy_year}",       (fy_year + 1, 1)),
        ("Q4", f"Jan–Mar {fy_year + 1}",   (fy_year + 1, 4)),
    ]
    items = []
    for q, period, (y, m) in quarters:
        due = _safe_date(y, m, due_day)
        items.append(_item(
            id=f"gstr3b_q_{q}_{fy_year}",
            category="GST",
            sub_category="GSTR-3B (Quarterly QRMP)",
            name=f"GSTR-3B ({q}) – {period}",
            description=f"Quarterly GSTR-3B for QRMP taxpayers ({state}: due {due_day}th). Pay tax via PMT-06 in months 1 & 2.",
            due_date=due,
            period=period,
            form_number="GSTR-3B / PMT-06",
            penalty="Late fee: Rs 50/day. Interest @ 18% p.a. on tax due.",
            priority="high",
        ))
    return items


def _gst_annual(fy_year: int, entity_type: str) -> List[Dict]:
    """GSTR-9 and GSTR-9C (Annual GST Return)."""
    ay_year = fy_year + 1
    items   = []
    entities_9 = ["Private Company", "LLP", "Partnership", "Proprietorship", "Trust", "Society"]
    if entity_type in entities_9:
        items.append(_item(
            id=f"gstr9_{fy_year}",
            category="GST",
            sub_category="GSTR-9 (Annual)",
            name=f"GSTR-9: Annual GST Return (FY {fy_year}-{str(fy_year+1)[-2:]})",
            description=f"Annual consolidated return of all supplies/purchases for FY {fy_year}-{str(fy_year+1)[-2:]}. Mandatory if turnover > Rs 2 Cr.",
            due_date=date(ay_year, 12, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="GSTR-9",
            penalty="Rs 200/day (Rs 100 CGST + Rs 100 SGST). Max 0.25% of turnover.",
            priority="high",
            applicable_entities=entities_9,
        ))
        items.append(_item(
            id=f"gstr9c_{fy_year}",
            category="GST",
            sub_category="GSTR-9C (Reconciliation)",
            name=f"GSTR-9C: Reconciliation Statement (FY {fy_year}-{str(fy_year+1)[-2:]})",
            description="CA-certified reconciliation of GSTR-9 with audited financials. Mandatory if turnover > Rs 5 Cr.",
            due_date=date(ay_year, 12, 31),
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="GSTR-9C",
            penalty="Same as GSTR-9 (Rs 200/day, max 0.25% of turnover).",
            priority="medium",
            applicable_entities=["Private Company", "LLP", "Partnership"],
        ))
    return items


# ── ROC / MCA ─────────────────────────────────────────────────────────────────

def _roc_items(fy_year: int, entity_type: str) -> List[Dict]:
    """ROC/MCA compliances for Companies and LLPs."""
    if entity_type not in ["Private Company", "LLP"]:
        return []
    items   = []
    ay_year = fy_year + 1  # AGM held after FY ends

    if entity_type == "Private Company":
        items += [
            _item(
                id=f"agm_{fy_year}",
                category="ROC / MCA",
                sub_category="Annual General Meeting",
                name=f"AGM – Annual General Meeting (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Mandatory AGM within 6 months of financial year end (i.e., by 30 Sep). Adopt accounts, appoint auditor, declare dividend.",
                due_date=date(ay_year, 9, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="—",
                penalty="Rs 1 lakh + Rs 5,000/day on company & officers.",
                priority="high",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"aoc4_{fy_year}",
                category="ROC / MCA",
                sub_category="Financial Statements",
                name=f"AOC-4: Financial Statements Filing (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="File Balance Sheet, P&L, Auditor's Report with ROC within 30 days of AGM (i.e., by 30 Oct typically).",
                due_date=date(ay_year, 10, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="AOC-4 / AOC-4 CFS",
                penalty="Rs 1,000/day (max Rs 10 lakh) u/s 137.",
                priority="high",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"mgt7_{fy_year}",
                category="ROC / MCA",
                sub_category="Annual Return",
                name=f"MGT-7: Annual Return (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Annual Return with details of shareholders, directors, registered office. Due within 60 days of AGM (by 29 Nov).",
                due_date=date(ay_year, 11, 29),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="MGT-7 / MGT-7A (for small/OPC)",
                penalty="Rs 50,000 + Rs 100/day for company; Rs 5,000 + Rs 50/day for officers.",
                priority="high",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"adt1_{fy_year}",
                category="ROC / MCA",
                sub_category="Auditor Appointment",
                name=f"ADT-1: Auditor Appointment (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Inform ROC of auditor appointment/reappointment within 15 days of AGM (by 15 Oct).",
                due_date=date(ay_year, 10, 15),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="ADT-1",
                penalty="Rs 300/day default fee.",
                priority="medium",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"dir3_kyc_{fy_year}",
                category="ROC / MCA",
                sub_category="Director KYC",
                name=f"DIR-3 KYC: Director KYC (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Annual KYC of all directors holding DIN. File by 30 Sep every year. Web-based DIR-3 KYC for no-change cases.",
                due_date=date(ay_year, 9, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="DIR-3 KYC / DIR-3 KYC-Web",
                penalty="Rs 5,000 penalty for deactivated DIN reactivation.",
                priority="high",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"dpt3_{fy_year}",
                category="ROC / MCA",
                sub_category="Deposits",
                name=f"DPT-3: Return of Deposits / Particulars of Loans",
                description="Annual return of deposits/outstanding loans not treated as deposits. Due 30 June every year.",
                due_date=date(ay_year, 6, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="DPT-3",
                penalty="Rs 5,000 + Rs 500/day of default.",
                priority="medium",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"msme1_h1_{fy_year}",
                category="ROC / MCA",
                sub_category="MSME",
                name=f"MSME-1: Half-Yearly Return (Apr–Sep {fy_year})",
                description="Half-yearly return of outstanding dues to MSME suppliers exceeding 45 days.",
                due_date=date(fy_year, 10, 31),
                period=f"Apr–Sep {fy_year}",
                form_number="MSME-1",
                penalty="Rs 25,000 to Rs 3,00,000. Officers: Rs 25,000 per default.",
                priority="medium",
                applicable_entities=["Private Company"],
            ),
            _item(
                id=f"msme1_h2_{fy_year}",
                category="ROC / MCA",
                sub_category="MSME",
                name=f"MSME-1: Half-Yearly Return (Oct {fy_year}–Mar {fy_year+1})",
                description="Half-yearly return of outstanding dues to MSME suppliers exceeding 45 days.",
                due_date=date(fy_year + 1, 4, 30),
                period=f"Oct {fy_year}–Mar {fy_year+1}",
                form_number="MSME-1",
                penalty="Rs 25,000 to Rs 3,00,000.",
                priority="medium",
                applicable_entities=["Private Company"],
            ),
        ]

    elif entity_type == "LLP":
        items += [
            _item(
                id=f"llp11_{fy_year}",
                category="ROC / MCA",
                sub_category="Annual Return",
                name=f"LLP-11: Annual Return (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Annual return of LLP with details of partners, business, registered office. Due 30 May every year.",
                due_date=date(ay_year, 5, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="LLP-11",
                penalty="Rs 100/day of default.",
                priority="high",
                applicable_entities=["LLP"],
            ),
            _item(
                id=f"llp8_{fy_year}",
                category="ROC / MCA",
                sub_category="Financial Statements",
                name=f"LLP-8: Statement of Account & Solvency (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Annual financial statements + solvency declaration. Due 30 October every year.",
                due_date=date(ay_year, 10, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="Form-8",
                penalty="Rs 100/day of default.",
                priority="high",
                applicable_entities=["LLP"],
            ),
            _item(
                id=f"dir3_kyc_llp_{fy_year}",
                category="ROC / MCA",
                sub_category="Director KYC",
                name=f"DIR-3 KYC: Designated Partner KYC (FY {fy_year}-{str(fy_year+1)[-2:]})",
                description="Annual KYC of all Designated Partners holding DIN. Due 30 Sep.",
                due_date=date(ay_year, 9, 30),
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="DIR-3 KYC",
                penalty="Rs 5,000 penalty for DIN deactivation.",
                priority="high",
                applicable_entities=["LLP"],
            ),
        ]

    return items


# ── PF / ESI ──────────────────────────────────────────────────────────────────

def _pf_items(fy_year: int, entity_type: str) -> List[Dict]:
    """PF monthly deposits + annual return."""
    excl = ["Individual", "Trust", "Society"]
    if entity_type in excl:
        return []
    items = []
    for year, month in _fy_months(fy_year):
        dep_m = month + 1 if month < 12 else 1
        dep_y = year if month < 12 else year + 1
        due   = _safe_date(dep_y, dep_m, 15)
        period_str = f"{_month_name(month)} {year}"
        items.append(_item(
            id=f"pf_dep_{year}_{month:02d}",
            category="PF",
            sub_category="PF Deposit",
            name=f"EPF/EPS Deposit – {period_str}",
            description=f"Monthly Provident Fund contribution deposit (employee 12% + employer 12%) for {period_str}. Mandatory if ≥ 20 employees (or voluntary).",
            due_date=due,
            period=period_str,
            form_number="ECR (Electronic Challan cum Return)",
            penalty="Interest @ 12% p.a. + damages 5%–25% of arrears.",
            priority="high",
        ))
    # Annual return
    items.append(_item(
        id=f"pf_annual_{fy_year}",
        category="PF",
        sub_category="PF Annual Return",
        name=f"EPF Annual Return (FY {fy_year}-{str(fy_year+1)[-2:]})",
        description="Annual PF return filing on EPFO portal. (Electronic filing via ECR has largely replaced physical returns.)",
        due_date=date(fy_year + 1, 4, 30),
        period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
        form_number="Annual Return (Form 3A/6A)",
        penalty="Rs 5,000 per return.",
        priority="medium",
    ))
    return items


def _esi_items(fy_year: int, entity_type: str) -> List[Dict]:
    """ESI monthly deposits + half-yearly returns."""
    excl = ["Individual", "Trust", "Society"]
    if entity_type in excl:
        return []
    items = []
    for year, month in _fy_months(fy_year):
        dep_m = month + 1 if month < 12 else 1
        dep_y = year if month < 12 else year + 1
        due   = _safe_date(dep_y, dep_m, 15)
        period_str = f"{_month_name(month)} {year}"
        items.append(_item(
            id=f"esi_dep_{year}_{month:02d}",
            category="ESI",
            sub_category="ESI Deposit",
            name=f"ESIC Contribution Deposit – {period_str}",
            description=f"Monthly ESI contribution (employee 0.75% + employer 3.25% of wages) for {period_str}. Mandatory if ≥ 10 employees.",
            due_date=due,
            period=period_str,
            form_number="ESIC Challan (Online)",
            penalty="12% interest p.a. + damages up to 25% of arrears.",
            priority="high",
        ))
    # Half-yearly returns
    items += [
        _item(
            id=f"esi_return_h1_{fy_year}",
            category="ESI",
            sub_category="ESI Return",
            name=f"ESIC Half-Yearly Return (Apr–Sep {fy_year})",
            description=f"Half-yearly ESI return for Apr–Sep {fy_year}. File on ESIC portal.",
            due_date=date(fy_year, 11, 11),
            period=f"Apr–Sep {fy_year}",
            form_number="Form 6 (Online ESIC portal)",
            penalty="Rs 5,000 per return.",
            priority="medium",
        ),
        _item(
            id=f"esi_return_h2_{fy_year}",
            category="ESI",
            sub_category="ESI Return",
            name=f"ESIC Half-Yearly Return (Oct {fy_year}–Mar {fy_year+1})",
            description=f"Half-yearly ESI return for Oct {fy_year}–Mar {fy_year+1}. File on ESIC portal.",
            due_date=date(fy_year + 1, 5, 11),
            period=f"Oct {fy_year}–Mar {fy_year+1}",
            form_number="Form 6 (Online ESIC portal)",
            penalty="Rs 5,000 per return.",
            priority="medium",
        ),
    ]
    return items


# ── Professional Tax ──────────────────────────────────────────────────────────

def _pt_items(fy_year: int, state: str) -> List[Dict]:
    """State Professional Tax items."""
    state_data = _load_state_data()
    pt_data    = state_data.get("professional_tax", {}).get(state)
    if not pt_data or not pt_data.get("applicable"):
        return []

    items   = []
    freq    = pt_data.get("payment_frequency", "monthly")
    due_day = pt_data.get("payment_due_day", 15)

    if freq == "monthly":
        for year, month in _fy_months(fy_year):
            # Due date = due_day of the same month (most states)
            due = _safe_date(year, month, due_day)
            period_str = f"{_month_name(month)} {year}"
            items.append(_item(
                id=f"pt_dep_{state[:3]}_{year}_{month:02d}",
                category="Professional Tax",
                sub_category=f"PT – {state}",
                name=f"Professional Tax Deposit – {period_str}",
                description=f"Monthly PT deduction from employee salary and deposit for {period_str}. {state} max: Rs {pt_data.get('max_annual',2500):,}/year.",
                due_date=due,
                period=period_str,
                form_number="State PT Challan",
                penalty="Interest + penalty as per state PT Act.",
                priority="medium",
            ))

    elif freq == "quarterly":
        due_months = pt_data.get("payment_due_months", [9, 12, 3, 6])
        for dm in due_months:
            dy = fy_year + 1 if dm < 4 else fy_year
            due = _safe_date(dy, dm, due_day)
            if date(fy_year, 4, 1) <= due <= date(fy_year + 1, 3, 31) or \
               due > date(fy_year + 1, 3, 31):
                period_str = f"Quarter ending {_month_name(dm)} {dy}"
                items.append(_item(
                    id=f"pt_q_{state[:3]}_{dy}_{dm:02d}",
                    category="Professional Tax",
                    sub_category=f"PT – {state}",
                    name=f"Professional Tax Deposit ({period_str})",
                    description=f"Quarterly PT payment for {period_str}. {state}.",
                    due_date=due,
                    period=period_str,
                    form_number="State PT Challan",
                    penalty="Interest + penalty as per state PT Act.",
                    priority="medium",
                ))

    elif freq == "half_yearly":
        due_months = pt_data.get("payment_due_months", [9, 3])
        for dm in due_months:
            dy = fy_year + 1 if dm < 4 else fy_year
            due = _safe_date(dy, dm, due_day)
            period_str = f"Half-year ending {_month_name(dm)} {dy}"
            items.append(_item(
                id=f"pt_h_{state[:3]}_{dy}_{dm:02d}",
                category="Professional Tax",
                sub_category=f"PT – {state}",
                name=f"Professional Tax Deposit ({period_str})",
                description=f"Half-yearly PT payment for {period_str}. {state}.",
                due_date=due,
                period=period_str,
                form_number="State PT Challan",
                penalty="Interest + penalty as per state PT Act.",
                priority="medium",
            ))

    # Annual PT Return
    ret_month = pt_data.get("return_due_month")
    ret_day   = pt_data.get("return_due_day")
    if ret_month and ret_day:
        ret_year = fy_year + 1 if ret_month < 4 else fy_year
        due = _safe_date(ret_year, ret_month, ret_day)
        items.append(_item(
            id=f"pt_return_{state[:3]}_{fy_year}",
            category="Professional Tax",
            sub_category=f"PT Return – {state}",
            name=f"Professional Tax Annual Return – {state}",
            description=f"Annual PT return filing with {state} Labour/Tax authority.",
            due_date=due,
            period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
            form_number="State PT Return Form",
            penalty="Penalty as per state PT Act.",
            priority="medium",
        ))

    return items


# ── Labour Welfare Fund ───────────────────────────────────────────────────────

def _lwf_items(fy_year: int, state: str) -> List[Dict]:
    """Labour Welfare Fund items."""
    state_data = _load_state_data()
    lwf_data   = state_data.get("labour_welfare_fund", {}).get(state)
    if not lwf_data or not lwf_data.get("applicable"):
        return []

    items    = []
    freq     = lwf_data.get("frequency")
    emp_cont = lwf_data.get("employer_contribution", 0)
    emp_cont_str = f"Employer: Rs {emp_cont}/month/employee"

    if freq == "half_yearly":
        due_months = lwf_data.get("due_months", [6, 12])
        due_day    = lwf_data.get("due_day", 15)
        for dm in due_months:
            dy = fy_year + 1 if dm < 4 else fy_year
            due = _safe_date(dy, dm, due_day)
            period_str = f"Half-year {_month_name(dm)} {dy}"
            items.append(_item(
                id=f"lwf_{state[:3]}_{dy}_{dm:02d}",
                category="Labour Welfare Fund",
                sub_category=f"LWF – {state}",
                name=f"Labour Welfare Fund – {state} ({period_str})",
                description=f"{emp_cont_str}. {lwf_data.get('notes','')}",
                due_date=due,
                period=period_str,
                form_number="LWF Challan",
                penalty="Interest + penalty as per state LWF Act.",
                priority="low",
            ))

    elif freq == "annual":
        due_month = lwf_data.get("due_month")
        due_day   = lwf_data.get("due_day", 31)
        if due_month:
            dy  = fy_year + 1 if due_month < 4 else fy_year
            due = _safe_date(dy, due_month, due_day)
            items.append(_item(
                id=f"lwf_{state[:3]}_{fy_year}_annual",
                category="Labour Welfare Fund",
                sub_category=f"LWF – {state}",
                name=f"Labour Welfare Fund – {state} (Annual)",
                description=f"Annual LWF contribution. {emp_cont_str}. {lwf_data.get('notes','')}",
                due_date=due,
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number="LWF Challan",
                penalty="Interest + penalty as per state LWF Act.",
                priority="low",
            ))

    return items


# ── Shop & Establishment ──────────────────────────────────────────────────────

def _se_items(fy_year: int, state: str, entity_type: str) -> List[Dict]:
    """Shop & Establishment Act renewal."""
    excl = ["Individual"]
    if entity_type in excl:
        return []
    state_data = _load_state_data()
    se_states  = state_data.get("shop_establishment", {}).get("states", {})
    se         = se_states.get(state)
    if not se:
        return []
    if se.get("renewal") == "lifetime":
        return []  # no recurring compliance

    r_month = se.get("renewal_month", 12)
    r_day   = se.get("renewal_day", 31)
    r_year  = fy_year + 1 if r_month < 4 else fy_year
    due     = _safe_date(r_year, r_month, r_day)

    return [_item(
        id=f"se_renewal_{state[:3]}_{fy_year}",
        category="Shop & Establishment",
        sub_category=f"S&E – {state}",
        name=f"Shop & Establishment Act Renewal – {state}",
        description=f"Annual renewal of registration under {state} Shops and Establishments Act. Authority: {se.get('authority','')}.",
        due_date=due,
        period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
        form_number="State S&E Renewal Form",
        penalty="Fine up to Rs 10,000 for operating without valid registration.",
        priority="medium",
    )]


# ── Industry-Specific ─────────────────────────────────────────────────────────

def _industry_items(fy_year: int, industry: str, entity_type: str) -> List[Dict]:
    """Industry-specific compliance items from JSON data."""
    if industry == "General":
        return []
    industry_data = _load_industry_data()
    sector        = industry_data.get(industry, {})
    templates     = sector.get("compliances", [])
    items         = []

    for tmpl in templates:
        freq = tmpl.get("frequency", "annual")

        if freq == "annual":
            m   = tmpl.get("due_month", 3)
            d   = tmpl.get("due_day", 31)
            y   = fy_year + 1 if m < 4 else fy_year
            due = _safe_date(y, m, d)
            items.append(_item(
                id=f"{tmpl['id']}_{fy_year}",
                category=tmpl.get("category", "Industry-Specific"),
                sub_category=tmpl.get("sub_category", industry),
                name=tmpl["name"],
                description=tmpl.get("description", ""),
                due_date=due,
                period=f"FY {fy_year}-{str(fy_year+1)[-2:]}",
                form_number=tmpl.get("form_number", ""),
                penalty=tmpl.get("penalty", ""),
                priority=tmpl.get("priority", "medium"),
            ))

        elif freq == "quarterly":
            due_months = tmpl.get("due_months", [7, 10, 1, 4])
            due_day    = tmpl.get("due_day", 30)
            for i, dm in enumerate(due_months, 1):
                dy  = fy_year + 1 if dm < 4 else fy_year
                due = _safe_date(dy, dm, due_day)
                items.append(_item(
                    id=f"{tmpl['id']}_q{i}_{fy_year}",
                    category=tmpl.get("category", "Industry-Specific"),
                    sub_category=tmpl.get("sub_category", industry),
                    name=f"{tmpl['name']} – Q{i}",
                    description=tmpl.get("description", ""),
                    due_date=due,
                    period=f"Quarter {i} – {fy_year}-{str(fy_year+1)[-2:]}",
                    form_number=tmpl.get("form_number", ""),
                    penalty=tmpl.get("penalty", ""),
                    priority=tmpl.get("priority", "medium"),
                ))

        elif freq == "half_yearly":
            due_months = tmpl.get("due_months", [5, 11])
            due_day    = tmpl.get("due_day", 31)
            for i, dm in enumerate(due_months, 1):
                dy  = fy_year + 1 if dm < 4 else fy_year
                due = _safe_date(dy, dm, due_day)
                items.append(_item(
                    id=f"{tmpl['id']}_h{i}_{fy_year}",
                    category=tmpl.get("category", "Industry-Specific"),
                    sub_category=tmpl.get("sub_category", industry),
                    name=f"{tmpl['name']} – H{i}",
                    description=tmpl.get("description", ""),
                    due_date=due,
                    period=f"Half-year {i} – {fy_year}-{str(fy_year+1)[-2:]}",
                    form_number=tmpl.get("form_number", ""),
                    penalty=tmpl.get("penalty", ""),
                    priority=tmpl.get("priority", "medium"),
                ))

    return items


# ── Main engine ───────────────────────────────────────────────────────────────

def generate_calendar(
    entity_type: str,
    state: str,
    industry: str = "General",
    fy: str = "2025-26",
    gst_turnover_label: str = "Above Rs 5 Cr (Monthly Filing)",
    today_override: Optional[date] = None,
) -> List[Dict]:
    """
    Generate full compliance calendar.

    Returns list of compliance dicts sorted by due date, each with:
    id, category, sub_category, name, description, due_date, period,
    form_number, penalty, priority, status, days_remaining.
    """
    fy_year = int(fy.split("-")[0])  # e.g. 2025
    today   = today_override or date.today()

    gst_turnover = GST_TURNOVER_OPTIONS.get(gst_turnover_label, 0)
    has_gst      = gst_turnover > 0
    monthly_gst  = gst_turnover > 5.0
    qrmp         = has_gst and not monthly_gst

    items: List[Dict] = []

    # ── Income Tax ────────────────────────────────────────────────────────────
    items += _advance_tax(fy_year, entity_type)
    items += _itr_items(fy_year, entity_type)

    # ── TDS / TCS ─────────────────────────────────────────────────────────────
    items += _tds_deposit(fy_year, entity_type)
    items += _tds_returns(fy_year, entity_type)

    # ── GST ───────────────────────────────────────────────────────────────────
    if has_gst:
        if monthly_gst:
            items += _gst_gstr1_monthly(fy_year)
            items += _gst_gstr3b_monthly(fy_year)
        else:
            items += _gst_gstr1_quarterly(fy_year)
            items += _gst_gstr3b_quarterly(fy_year, state)
        items += _gst_annual(fy_year, entity_type)

    # ── ROC / MCA ─────────────────────────────────────────────────────────────
    items += _roc_items(fy_year, entity_type)

    # ── PF / ESI ──────────────────────────────────────────────────────────────
    items += _pf_items(fy_year, entity_type)
    items += _esi_items(fy_year, entity_type)

    # ── State-specific ────────────────────────────────────────────────────────
    items += _pt_items(fy_year, state)
    items += _lwf_items(fy_year, state)
    items += _se_items(fy_year, state, entity_type)

    # ── Industry-specific ─────────────────────────────────────────────────────
    items += _industry_items(fy_year, industry, entity_type)

    # ── Compute status & days_remaining ───────────────────────────────────────
    for item in items:
        dd                   = item["due_date"]
        item["days_remaining"] = (dd - today).days
        item["status"]         = _compute_status(dd, today)

    # Sort by due date
    items.sort(key=lambda x: x["due_date"])
    return items


def get_urgency_counts(items: List[Dict]) -> Dict[str, int]:
    counts = {"total": len(items), "overdue": 0, "burning": 0, "this_week": 0, "upcoming": 0, "future": 0, "done": 0}
    for item in items:
        s = item.get("status", "future")
        if s in counts:
            counts[s] += 1
    return counts
