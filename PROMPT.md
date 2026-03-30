# PROMPT.md — DueDash

## Title
**DueDash — Smart Compliance Calendar & Auto-Reminder Platform**

## The Problem
Chartered Accountants and Indian businesses must manually track 100+ compliance deadlines across central regulations (Income Tax, GST, TDS/TCS, ROC/MCA, PF, ESI), state-specific regulations (Professional Tax, Labour Welfare Fund, Shops & Establishment), and industry-specific compliances. These deadlines vary by entity type, state, turnover, and industry. Missing even one deadline means penalties, interest, and legal exposure. Existing solutions are either expensive or too generic.

## What This App Does
1. **Select entity profile** — entity type (Company, LLP, Partnership, Proprietorship, Trust, etc.) + state + industry + GST turnover slab
2. **Auto-generates a full-year compliance calendar** — 100+ deadlines tailored to the entity's profile
3. **Dashboard with urgency levels** — Burning Now (0-3 days), This Week (4-7 days), Next 30 Days, Future
4. **State-specific compliances** — Professional Tax, Labour Welfare Fund, Shop & Establishment Act deadlines for all Indian states
5. **Industry-specific compliances** — IT/Software, Manufacturing, Banking/NBFC, Healthcare, Real Estate, Education, E-Commerce, Import/Export, and more
6. **Google Sheets sync** — push the entire calendar to a Google Sheet for team collaboration
7. **Auto-email reminders** — SMTP-based email alerts at 15, 7, 3, and 1 day before each deadline
8. **Export to Excel** — download the compliance calendar as a formatted .xlsx file
9. **Mark as done** — track completion status of each compliance item

### Demo Mode
The app works fully without any API keys or credentials. Google Sheets sync and email reminders are optional add-ons.

## Tech Stack
| Component | Technology |
|-----------|-----------|
| Frontend / Web App | Python + Streamlit |
| Compliance Engine | Custom Python engine with 100+ rules |
| State Data | JSON database (state_compliances.json) |
| Industry Data | JSON database (industry_compliances.json) |
| Charts & Visuals | Plotly |
| Google Sheets Integration | gspread + google-auth |
| Email Reminders | SMTP (smtplib) |
| Excel Export | XlsxWriter + openpyxl |
| Data Processing | pandas |

## AICA Modules Used
| Module | Application |
|--------|------------|
| Module 4 — Communication Automation | Auto-email reminders via SMTP, Google Sheets sync for collaboration |
| Module 6 — Python for AI | Core compliance engine, date logic, rule-based calendar generation |
| Module 7 — Full-Stack Web App + PWA | Streamlit web app with responsive design, installable as PWA |
| Module 8 — Android APK | Can be packaged as Android app via PWA wrapper |
| Module 9 — AI-Driven Workflows | Intelligent compliance rule engine that adapts calendar based on entity profile; Gemini API ready for future AI features |

## How to Recreate This From Scratch Using AI

### Step 1: Set up the project
```
mkdir DueDash && cd DueDash
pip install streamlit pandas openpyxl python-dateutil gspread google-auth google-auth-oauthlib plotly xlsxwriter
```

### Step 2: Prompt an AI assistant with this description
> "Build a Streamlit web app called DueDash — a Smart Compliance Calendar for Indian businesses. The user selects: entity type (Company, LLP, Partnership, Proprietorship, Trust, Society, HUF, AOP/BOI), state, industry, and GST turnover slab. The app generates a full-year compliance calendar with 100+ deadlines covering: Income Tax (advance tax, ITR, audit), GST (GSTR-1, GSTR-3B, annual return), TDS/TCS (monthly/quarterly returns, certificates), ROC/MCA (annual filing, DIR-3 KYC, DPT-3), PF and ESI (monthly returns), state-specific Professional Tax and Labour Welfare Fund (varies by state), and industry-specific compliances. Show a dashboard with urgency-based categorization: Burning Now (0-3 days), This Week (4-7 days), Next 30 Days, Future. Include Plotly charts for category breakdown and monthly distribution. Add Google Sheets sync via gspread, SMTP email reminders, and Excel export. Use a clean professional UI with Inter font."

### Step 3: Build the compliance database
Create two JSON files:
- `data/state_compliances.json` — Professional Tax, LWF, S&E Act deadlines for each Indian state
- `data/industry_compliances.json` — industry-specific compliances (IT, Manufacturing, Banking, Healthcare, etc.)

### Step 4: Build the compliance engine
Create `compliance_engine.py` with rule-based logic that generates deadlines based on entity type, state, industry, and turnover slab. Handle quarterly vs monthly frequencies, half-yearly deadlines, and annual filings.

### Step 5: Add integrations
- Google Sheets: Use gspread with service account credentials
- Email: Use smtplib with Gmail App Password
- Excel: Use XlsxWriter for formatted exports

### Step 6: Test and iterate
Run `streamlit run app.py`, verify all entity type + state + industry combinations generate correct calendars.

## File Structure
```
DueDash/
├── app.py                      # Main Streamlit application (UI + orchestration)
├── compliance_engine.py        # Core compliance calendar generation engine
├── config.py                   # Configuration (SMTP, Google Sheets, API keys)
├── requirements.txt            # Python dependencies
├── data/
│   ├── state_compliances.json  # State-specific compliance rules (all states)
│   └── industry_compliances.json # Industry-specific compliance rules
├── integrations/
│   ├── google_sheets.py        # Google Sheets sync integration
│   └── email_sender.py         # SMTP email reminder system
└── utils/
    └── helpers.py              # Date formatting, Excel export, utilities
```

---
*AICA (AI for CA) Level 2 Capstone Project — March 2026*
