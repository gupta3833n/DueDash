# DueDash
### Smart Compliance Calendar & Auto-Reminder Platform

**AICA (AI for CA) Level 2 Capstone Project**

---

## What it does

DueDash is an intelligent compliance calendar that auto-generates 100+ regulatory deadlines tailored to an Indian business's specific profile. It:

1. Takes entity type (Company, LLP, Partnership, etc.), state, industry, and GST turnover slab as inputs
2. Generates a full-year compliance calendar covering Income Tax, GST, TDS/TCS, ROC/MCA, PF, ESI, state-specific, and industry-specific deadlines
3. Displays an urgency-based dashboard — Burning Now, This Week, Next 30 Days, Future
4. Syncs to Google Sheets for team collaboration
5. Sends auto-email reminders at 15, 7, 3, and 1 day before each deadline
6. Exports the calendar as a formatted Excel file

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501` in your browser.

### 3. Use it (no API keys needed)

Select your entity type, state, and industry in the sidebar. The compliance calendar generates instantly. Google Sheets sync and email reminders are optional features.

---

## Optional: Google Sheets Sync

1. Create a Google Cloud service account and download the JSON credentials
2. Set environment variables:
   ```
   GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
   GOOGLE_SHEET_ID=your_spreadsheet_id
   ```
3. Share the Google Sheet with the service account email

## Optional: Email Reminders

Set environment variables for SMTP:
```
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=recipient@example.com
```

---

## Project Structure

```
DueDash/
├── app.py                      Main Streamlit application
├── compliance_engine.py        Core compliance calendar engine
├── config.py                   Configuration (SMTP, Sheets, API keys)
├── requirements.txt            Python dependencies
│
├── data/
│   ├── state_compliances.json  State-specific rules (all Indian states)
│   └── industry_compliances.json Industry-specific rules
│
├── integrations/
│   ├── google_sheets.py        Google Sheets sync
│   └── email_sender.py         SMTP email reminders
│
└── utils/
    └── helpers.py              Date formatting, Excel export, utilities
```

---

## Compliance Coverage

| Category | Examples |
|----------|---------|
| Income Tax | Advance Tax (quarterly), ITR filing, Tax Audit |
| GST | GSTR-1, GSTR-3B, Annual Return (GSTR-9) |
| TDS / TCS | Monthly/quarterly returns, certificates |
| ROC / MCA | Annual filing, DIR-3 KYC, DPT-3 |
| PF | Monthly ECR filing |
| ESI | Monthly contribution, half-yearly return |
| Professional Tax | State-wise deadlines (varies by state) |
| Labour Welfare Fund | State-wise half-yearly/annual |
| Shop & Establishment | State-wise renewal deadlines |
| Industry-Specific | IT/Software, Manufacturing, Banking, Healthcare, etc. |

---

## Urgency Levels

| Level | Days Remaining | Colour |
|-------|---------------|--------|
| Burning Now | 0–3 days | Orange/Red |
| This Week | 4–7 days | Yellow |
| Next 30 Days | 8–30 days | Green |
| Future | 31+ days | Blue |
| Overdue | Past due | Red |

---

## Tech Stack

- **Frontend:** Streamlit
- **Compliance Engine:** Custom Python rule engine
- **Charts:** Plotly
- **Google Sheets:** gspread + google-auth
- **Email:** smtplib (SMTP)
- **Excel Export:** XlsxWriter
- **Data:** pandas

---

*AICA Capstone Project — AI for CA | 2026*
