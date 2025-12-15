"""
Unified Weekly Scraper
Combines all job sources: emails and company monitoring
Runs weekly to find new opportunities across all channels
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from jobs.company_scraper import CompanyScraper
from processor_v2 import JobProcessorV2

load_dotenv()


class WeeklyUnifiedScraper:
    """
    Unified weekly scraper combining all job sources:
    1. Email-based sources (LinkedIn, Supra, F6S, Artemis, Built In, etc.)
    2. Company monitoring (68 companies)
    """

    def __init__(self, profile: str | None = None):
        # Store profile for logging and sub-components
        self.profile = profile

        # Email processor (handles all email parsers)
        self.email_processor = JobProcessorV2(profile=profile)

        # Read LLM extraction config
        config_path = (
            Path(__file__).parent.parent.parent / "config" / "llm-extraction-settings.json"
        )
        llm_enabled = False
        if config_path.exists():
            with open(config_path) as f:
                llm_config = json.load(f)
                llm_enabled = llm_config.get("enabled", False)

        # Company monitoring scraper
        self.company_scraper = CompanyScraper(profile=profile, enable_llm_extraction=llm_enabled)

    def run_all(
        self,
        fetch_emails: bool = True,
        email_limit: int | None = None,
        scrape_companies: bool = True,
        companies_min_score: int = 50,
        company_filter: str | None = None,
        skip_recent_hours: int | None = None,
    ) -> dict:
        """
        Run all job processing sources

        Args:
            fetch_emails: Whether to fetch and process emails
            email_limit: Max emails to process (None = process all unread emails)
            scrape_companies: Whether to scrape monitored companies
            companies_min_score: Minimum score for company jobs (default: 50 for D+ grade)
            company_filter: Filter companies by notes (e.g., "From Wes")
            skip_recent_hours: Skip companies checked within this many hours (None = scrape all)

        Returns:
            Combined stats from all sources
        """
        print("=" * 80)
        print("UNIFIED WEEKLY SCRAPER - ALL JOB SOURCES")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"📧 Email processing: {fetch_emails}")
        print(f"🏢 Company monitoring: {scrape_companies}")
        print("=" * 80 + "\n")

        all_stats = {
            "email": {},
            "companies": {},
            "total_jobs_found": 0,
            "total_jobs_stored": 0,
            "total_notifications": 0,
        }

        # PART 1: Email-based sources
        if fetch_emails:
            print("\n" + "=" * 80)
            print("PART 1: EMAIL-BASED SOURCES")
            print("=" * 80 + "\n")

            email_stats = self.email_processor.run(fetch_emails=fetch_emails, limit=email_limit)

            all_stats["email"] = email_stats
            all_stats["total_jobs_found"] += email_stats.get("opportunities_found", 0)
            all_stats["total_jobs_stored"] += email_stats.get("jobs_stored", 0)
            all_stats["total_notifications"] += email_stats.get("notifications_sent", 0)

        # PART 2: Company monitoring
        if scrape_companies:
            print("\n" + "=" * 80)
            print("PART 2: COMPANY MONITORING (FIRECRAWL)")
            print("=" * 80 + "\n")

            company_stats = self._scrape_monitored_companies(
                min_score=companies_min_score,
                company_filter=company_filter,
                skip_recent_hours=skip_recent_hours,
            )

            all_stats["companies"] = company_stats
            all_stats["total_jobs_found"] += company_stats.get("jobs_scraped", 0)
            all_stats["total_jobs_stored"] += company_stats.get("jobs_stored", 0)
            all_stats["total_notifications"] += company_stats.get("notifications_sent", 0)

        # Final summary
        self._print_summary(all_stats, fetch_emails, scrape_companies)

        return all_stats

    def _scrape_monitored_companies(
        self,
        min_score: int = 50,
        company_filter: str | None = None,
        skip_recent_hours: int | None = None,
    ) -> dict:
        """
        Scrape all monitored companies using Firecrawl

        Args:
            min_score: Minimum score to store/notify
            company_filter: Filter companies by notes (e.g., "From Wes")
            skip_recent_hours: Skip companies checked within this many hours (None = scrape all)

        Returns:
            Stats dictionary
        """
        return self.company_scraper.scrape_all_companies(
            min_score=min_score,
            company_filter=company_filter,
            notify_threshold=80,
            skip_recent_hours=skip_recent_hours,
        )

    def _print_summary(
        self,
        all_stats: dict,
        ran_emails: bool,
        ran_companies: bool,
    ) -> None:
        """Print final summary"""
        print("\n" + "=" * 80)
        print("UNIFIED SCRAPER - FINAL SUMMARY")
        print("=" * 80)

        if ran_emails:
            email_stats = all_stats["email"]
            print("\n📧 Email Sources:")
            print(f"  Emails processed: {email_stats.get('emails_processed', 0)}")
            print(f"  Jobs found: {email_stats.get('opportunities_found', 0)}")
            print(f"  Jobs stored: {email_stats.get('jobs_stored', 0)}")
            print(f"  Notifications: {email_stats.get('notifications_sent', 0)}")

        if ran_companies:
            company_stats = all_stats["companies"]
            print("\n🏢 Company Monitoring:")
            print(f"  Companies checked: {company_stats.get('companies_checked', 0)}")
            print(f"  Jobs scraped: {company_stats.get('jobs_scraped', 0)}")
            print(f"  Leadership roles: {company_stats.get('leadership_jobs', 0)}")
            print(f"  Jobs stored: {company_stats.get('jobs_stored', 0)}")
            print(f"  Notifications: {company_stats.get('notifications_sent', 0)}")

            # Email failed extractions table (both regex and LLM returned 0)
            failed_extractions = company_stats.get("failed_extractions", [])
            if failed_extractions:
                print(
                    f"\n⚠️  {len(failed_extractions)} companies failed both extraction methods - emailing review list..."
                )
                self._email_failed_extractions(failed_extractions)

        print("\n📊 TOTALS:")
        print(f"  Jobs found: {all_stats['total_jobs_found']}")
        print(f"  Jobs stored: {all_stats['total_jobs_stored']}")
        print(f"  Notifications sent: {all_stats['total_notifications']}")

    def _email_failed_extractions(self, failed_companies: list[dict]) -> None:
        """Email list of companies where both regex and LLM extraction failed"""
        try:
            # Build HTML table
            html_rows = ""
            for company in failed_companies:
                html_rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{company["name"]}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="{company["url"]}">{company["url"]}</a>
                    </td>
                </tr>
                """

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>⚠️ Companies Needing Review - Extraction Failed</h2>
                <p>The following {len(failed_companies)} companies returned 0 jobs from both regex AND LLM extraction:</p>
                <p>This may indicate:</p>
                <ul>
                    <li>Broken career pages</li>
                    <li>Unusual job posting formats</li>
                    <li>Career pages requiring JavaScript or authentication</li>
                    <li>No current job openings</li>
                </ul>
                <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                    <thead>
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Company</th>
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Career Page URL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_rows}
                    </tbody>
                </table>
                <p style="margin-top: 20px; color: #666;">
                    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </p>
            </body>
            </html>
            """

            # Get email credentials
            gmail_user = os.getenv("ADAMWHITE_GMAIL_USERNAME")
            gmail_password = os.getenv("ADAMWHITE_GMAIL_APP_PASSWORD")

            if not gmail_user or not gmail_password:
                print("  ⚠ Email credentials not found - skipping email notification")
                return

            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = gmail_user
            msg["To"] = "adamkwhite@gmail.com"
            msg["Subject"] = (
                f"⚠️ {len(failed_companies)} Companies Failed Extraction - Review Needed"
            )

            msg.attach(MIMEText(html_body, "html"))

            # Send email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_password)
                server.send_message(msg)

            print("  ✓ Emailed review list to adamkwhite@gmail.com")

        except Exception as e:
            print(f"  ✗ Failed to send email: {e}")


def main():
    """CLI entry point"""
    import argparse

    from utils.profile_manager import get_profile_manager

    # Get available profile IDs dynamically
    profile_manager = get_profile_manager()
    available_profiles = profile_manager.get_profile_ids()

    parser = argparse.ArgumentParser(description="Unified weekly scraper - all job sources")

    # Profile selection
    parser.add_argument(
        "--profile",
        type=str,
        choices=available_profiles,
        help="Profile to use (determines email account and scoring)",
    )

    # Source toggles
    parser.add_argument("--email-only", action="store_true", help="Only process emails")
    parser.add_argument(
        "--companies-only", action="store_true", help="Only scrape monitored companies"
    )

    # Email options
    parser.add_argument(
        "--email-limit",
        type=int,
        default=None,
        help="Max emails to process (default: all unread emails)",
    )

    # Company options
    parser.add_argument(
        "--companies-min-score",
        type=int,
        default=50,
        help="Min score for company jobs (default: 50 for D+ grade)",
    )
    parser.add_argument(
        "--company-filter",
        type=str,
        help="Filter companies by notes (e.g., 'From Wes')",
    )
    parser.add_argument(
        "--skip-recent-hours",
        type=int,
        help="Skip companies checked within this many hours (saves API credits)",
    )

    args = parser.parse_args()

    # Determine what to run
    if args.email_only:
        run_emails = True
        run_companies = False
    elif args.companies_only:
        run_emails = False
        run_companies = True
    else:
        # Run all sources by default
        run_emails = True
        run_companies = True

    scraper = WeeklyUnifiedScraper(profile=args.profile)
    stats = scraper.run_all(
        fetch_emails=run_emails,
        email_limit=args.email_limit,
        scrape_companies=run_companies,
        companies_min_score=args.companies_min_score,
        company_filter=args.company_filter,
        skip_recent_hours=args.skip_recent_hours,
    )

    # Output JSON for logging
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
