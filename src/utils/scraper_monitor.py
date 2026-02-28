"""
Scraper monitoring and alerting.

Analyzes stats from weekly_unified_scraper runs and sends failure alerts
via email when issues are detected.
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


class ScraperMonitor:
    """Analyzes scraper stats and sends failure alerts."""

    def __init__(self, alert_email: str = "adamkwhite@gmail.com") -> None:
        self.alert_email = alert_email
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def check_single_profile_stats(self, stats: dict[str, Any]) -> bool:
        """Check stats from run_all(). Returns True if healthy."""
        self._check_email_stats(stats.get("email", {}))
        self._check_company_stats(stats.get("companies", {}))
        self._check_source_stats(stats.get("ministry", {}), "Ministry of Testing")
        self._check_source_stats(stats.get("testdevjobs", {}), "TestDevJobs")
        return len(self.failures) == 0

    def check_all_inboxes_stats(self, stats: dict[str, Any]) -> bool:
        """Check stats from run_all_inboxes(). Returns True if healthy."""
        # Check top-level errors
        for error in stats.get("errors", []):
            self.failures.append(f"Top-level error: {error}")

        # Check per-inbox results
        self._check_inbox_failures(stats.get("profiles", {}))

        # Check shared resources
        self._check_company_stats(stats.get("companies", {}))
        self._check_source_stats(stats.get("ministry", {}), "Ministry of Testing")
        self._check_source_stats(stats.get("testdevjobs", {}), "TestDevJobs")

        return len(self.failures) == 0

    def send_alert(self, subject: str) -> bool:
        """Send alert email via SMTP. Returns True if sent successfully."""
        gmail_user = os.getenv("ADAMWHITE_GMAIL_USERNAME")
        gmail_password = os.getenv("ADAMWHITE_GMAIL_APP_PASSWORD")

        if not gmail_user or not gmail_password:
            print("  Warning: Email credentials not found - skipping alert email")
            return False

        html_body = self._build_alert_html()
        msg = MIMEMultipart("alternative")
        msg["From"] = gmail_user
        msg["To"] = self.alert_email
        msg["Subject"] = subject

        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_password)
                server.send_message(msg)
            print(f"  Alert email sent to {self.alert_email}")
            return True
        except Exception as e:
            print(f"  Failed to send alert email: {e}")
            return False

    def get_exit_code(self) -> int:
        """Return 0 if healthy, 1 if failures."""
        return 1 if self.failures else 0

    def _check_email_stats(self, email_stats: dict[str, Any]) -> None:
        """Check email processing stats for failures."""
        if not email_stats:
            return

        if "error" in email_stats:
            self.failures.append(f"Email processing error: {email_stats['error']}")
            return

        emails_processed = email_stats.get("emails_processed", 0)
        if emails_processed == 0:
            self.warnings.append("Email processing returned 0 emails")

    def _check_company_stats(self, company_stats: dict[str, Any]) -> None:
        """Check company scraping stats for failures."""
        if not company_stats:
            return

        if "error" in company_stats:
            self.failures.append(f"Company scraping error: {company_stats['error']}")
            return

        companies_checked = company_stats.get("companies_checked", 0)
        if companies_checked == 0:
            self.warnings.append("Company scraping checked 0 companies")

    def _check_source_stats(self, source_stats: dict[str, Any], source_name: str) -> None:
        """Check stats for a generic source (ministry, testdevjobs)."""
        if not source_stats:
            return

        if "error" in source_stats:
            self.failures.append(f"{source_name} error: {source_stats['error']}")

    def _check_inbox_failures(self, profiles: dict[str, Any]) -> None:
        """Check multi-inbox results for per-profile failures."""
        for profile_id, result in profiles.items():
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                self.failures.append(
                    f"Inbox failed for {result.get('name', profile_id)}: {error_msg}"
                )

    def _build_alert_html(self) -> str:
        """Build HTML email body for alert."""
        failure_rows = _build_table_rows(self.failures, "#f44336")
        warning_rows = _build_table_rows(self.warnings, "#ff9800")

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Weekly Scraper Alert</h2>
            <p>The weekly scraper encountered issues during its run.</p>

            {_build_section("Failures", failure_rows)}
            {_build_section("Warnings", warning_rows)}

            <p style="margin-top: 20px; color: #666;">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </body>
        </html>
        """


def _build_table_rows(items: list[str], color: str) -> str:
    """Build HTML table rows for a list of items."""
    rows = ""
    for item in items:
        rows += (
            f'<tr><td style="padding: 8px; border: 1px solid #ddd;'
            f' color: {color};">{item}</td></tr>\n'
        )
    return rows


def _build_section(title: str, rows: str) -> str:
    """Build an HTML section with a table if rows exist."""
    if not rows:
        return ""
    return f"""
        <h3>{title}</h3>
        <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
            <tbody>{rows}</tbody>
        </table>
    """
