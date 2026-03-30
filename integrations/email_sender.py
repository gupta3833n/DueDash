"""
Email Reminder Integration for DueDash
Sends compliance reminder emails via SMTP (Gmail / Outlook / custom).

Setup:
1. Configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in config.py or env vars
2. For Gmail: use App Password (not your Gmail password)
   → Google Account → Security → 2FA → App Passwords → Create
3. Set ALERT_EMAIL to the recipient address
"""

from __future__ import annotations

import smtplib
import ssl
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Tuple


STATUS_LABELS = {
    "overdue":   "🔴 OVERDUE",
    "burning":   "🔥 Burning Now",
    "this_week": "⚠️ Due This Week",
    "upcoming":  "📅 Due in Next 30 Days",
    "future":    "📋 Upcoming",
}

URGENCY_ORDER = ["overdue", "burning", "this_week", "upcoming"]


def _build_html(items: List[Dict], entity_type: str, state: str, fy: str,
                recipient_name: str = "Team") -> str:
    """Build an HTML email body."""
    from utils.helpers import format_date, days_label

    # Group by status
    grouped: Dict[str, List[Dict]] = {s: [] for s in URGENCY_ORDER}
    for item in items:
        s = item.get("status", "future")
        if s in grouped:
            grouped[s].append(item)

    has_urgent = any(grouped[s] for s in ["overdue", "burning", "this_week"])

    rows_html = ""
    for status in URGENCY_ORDER:
        for item in grouped[status]:
            dd      = item.get("due_date")
            due_str = format_date(dd) if dd else "—"
            days    = item.get("days_remaining", "")
            days_str = days_label(days) if isinstance(days, int) else ""
            badge_color = {
                "overdue":   "#E53E3E",
                "burning":   "#DD6B20",
                "this_week": "#D69E2E",
                "upcoming":  "#276749",
            }.get(status, "#2B6CB0")
            rows_html += f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;">{item.get('category','')}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;font-weight:600;">{item.get('name','')}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;">{item.get('period','')}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;">{due_str}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;color:{badge_color};font-weight:700;">{days_str}</td>
            </tr>"""

    if not rows_html:
        rows_html = "<tr><td colspan='5' style='padding:16px;text-align:center;color:#718096;'>No urgent items found.</td></tr>"

    subject_prefix = "⚠️ ACTION REQUIRED" if has_urgent else "📅 Compliance Update"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:Arial,sans-serif;color:#2D3748;">
  <div style="max-width:700px;margin:32px auto;background:#FFFFFF;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#2563AB,#4A90D9);padding:28px 32px;">
      <h1 style="margin:0;color:#FFFFFF;font-size:24px;letter-spacing:-0.5px;">DueDash</h1>
      <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">Smart Compliance Calendar</p>
    </div>
    <!-- Body -->
    <div style="padding:28px 32px;">
      <p style="font-size:16px;margin:0 0 8px;">Dear {recipient_name},</p>
      <p style="font-size:15px;color:#4A5568;margin:0 0 24px;">
        Here is your compliance reminder for <strong>{entity_type}</strong> | <strong>{state}</strong> | <strong>FY {fy}</strong>.
      </p>

      <!-- Stats -->
      <div style="display:flex;gap:12px;margin-bottom:24px;">
        {"".join([
            f'<div style="flex:1;background:#FFF5F5;border:1px solid #FEB2B2;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-size:22px;font-weight:800;color:#E53E3E;">{len(grouped["overdue"])}</div>'
            f'<div style="font-size:12px;color:#E53E3E;margin-top:4px;">OVERDUE</div></div>'
        ] if grouped["overdue"] else [])}
        {"".join([
            f'<div style="flex:1;background:#FFFAF0;border:1px solid #FBD38D;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-size:22px;font-weight:800;color:#DD6B20;">{len(grouped["burning"])}</div>'
            f'<div style="font-size:12px;color:#DD6B20;margin-top:4px;">BURNING NOW</div></div>'
        ] if grouped["burning"] else [])}
        {"".join([
            f'<div style="flex:1;background:#FFFFF0;border:1px solid #FAF089;border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-size:22px;font-weight:800;color:#D69E2E;">{len(grouped["this_week"])}</div>'
            f'<div style="font-size:12px;color:#D69E2E;margin-top:4px;">THIS WEEK</div></div>'
        ] if grouped["this_week"] else [])}
        <div style="flex:1;background:#F0FFF4;border:1px solid #9AE6B4;border-radius:8px;padding:14px;text-align:center;">
          <div style="font-size:22px;font-weight:800;color:#276749;">{len(grouped["upcoming"])}</div>
          <div style="font-size:12px;color:#276749;margin-top:4px;">NEXT 30 DAYS</div>
        </div>
      </div>

      <!-- Table -->
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#EBF8FF;">
            <th style="padding:10px 12px;text-align:left;font-size:12px;color:#2B6CB0;text-transform:uppercase;letter-spacing:0.5px;">Category</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;color:#2B6CB0;text-transform:uppercase;letter-spacing:0.5px;">Compliance</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;color:#2B6CB0;text-transform:uppercase;letter-spacing:0.5px;">Period</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;color:#2B6CB0;text-transform:uppercase;letter-spacing:0.5px;">Due Date</th>
            <th style="padding:10px 12px;text-align:left;font-size:12px;color:#2B6CB0;text-transform:uppercase;letter-spacing:0.5px;">Status</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <!-- Footer -->
    <div style="background:#F8FAFC;padding:20px 32px;border-top:1px solid #E2E8F0;">
      <p style="margin:0;font-size:12px;color:#718096;">
        This is an automated reminder from <strong>DueDash</strong> — Smart Compliance Calendar for Indian Businesses.<br>
        Please consult your CA for specific advice on due dates and penalties.
      </p>
    </div>
  </div>
</body>
</html>"""


class EmailSender:
    """SMTP email sender for DueDash reminders."""

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host     = host
        self.port     = port
        self.user     = user
        self.password = password

    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def test_connection(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "SMTP credentials not configured."
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=10) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.login(self.user, self.password)
            return True, "SMTP connection successful."
        except Exception as e:
            return False, f"SMTP connection failed: {e}"

    def send_reminder(
        self,
        to_email: str,
        items: List[Dict],
        entity_type: str,
        state: str,
        fy: str,
        recipient_name: str = "Team",
        days_filter: List[str] = None,
    ) -> Tuple[bool, str]:
        """Send compliance reminder email. Returns (success, message)."""
        if not self.is_configured():
            return False, "SMTP credentials not configured."
        if not to_email:
            return False, "Recipient email not configured."

        # Filter to urgent items only (unless custom filter)
        if days_filter is None:
            days_filter = ["overdue", "burning", "this_week", "upcoming"]
        filtered = [i for i in items if i.get("status") in days_filter]

        if not filtered:
            return True, "No urgent compliance items — email not sent."

        html_body = _build_html(filtered, entity_type, state, fy, recipient_name)

        overdue_count = sum(1 for i in filtered if i.get("status") == "overdue")
        burning_count = sum(1 for i in filtered if i.get("status") == "burning")
        if overdue_count:
            subject = f"⚠️ DueDash: {overdue_count} Overdue Compliance(s) | FY {fy} | {entity_type}"
        elif burning_count:
            subject = f"🔥 DueDash: {burning_count} Compliance(s) Due in 3 Days | FY {fy}"
        else:
            subject = f"📅 DueDash: Compliance Reminders | FY {fy} | {entity_type}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"DueDash <{self.user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.login(self.user, self.password)
                srv.sendmail(self.user, to_email, msg.as_string())
            return True, f"Reminder sent to {to_email} ({len(filtered)} compliance items)."
        except Exception as e:
            return False, f"Email send failed: {e}"


def get_sender() -> EmailSender:
    """Factory — reads from config."""
    from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    return EmailSender(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
