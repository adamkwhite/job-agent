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
from jobs.ministry_scraper import MinistryScraper
from processor_v2 import JobProcessorV2

load_dotenv()


class WeeklyUnifiedScraper:
    """
    Unified weekly scraper combining all job sources:
    1. Email-based sources (LinkedIn, Supra, F6S, Artemis, Built In, etc.)
    2. Company monitoring (68 companies)
    3. Ministry of Testing (QA/testing job board)
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

        # Company monitoring scraper (with pagination enabled by default)
        self.company_scraper = CompanyScraper(
            profile=profile, enable_llm_extraction=llm_enabled, enable_pagination=True
        )

        # Ministry of Testing scraper
        self.ministry_scraper = MinistryScraper(profile=profile)

    def run_all(
        self,
        fetch_emails: bool = True,
        email_limit: int | None = None,
        scrape_companies: bool = True,
        companies_min_score: int = 50,
        company_filter: str | None = None,
        skip_recent_hours: int | None = None,
        scrape_ministry: bool = True,
        _ministry_max_pages: int = 3,
        _ministry_min_score: int = 47,
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
            scrape_ministry: Whether to scrape Ministry of Testing
            ministry_max_pages: Max pages to scrape from Ministry (default: 3)
            ministry_min_score: Minimum score for Ministry jobs (default: 47 for Mario)

        Returns:
            Combined stats from all sources
        """
        print("=" * 80)
        print("UNIFIED WEEKLY SCRAPER - ALL JOB SOURCES")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"📧 Email processing: {fetch_emails}")
        print(f"🏢 Company monitoring: {scrape_companies}")
        print(f"🧪 Ministry of Testing: {scrape_ministry}")
        print("=" * 80 + "\n")

        all_stats = {
            "email": {},
            "companies": {},
            "ministry": {},
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

        # PART 3: Ministry of Testing
        if scrape_ministry:
            print("\n" + "=" * 80)
            print("PART 3: MINISTRY OF TESTING (QA/TESTING JOBS)")
            print("=" * 80 + "\n")

            try:
                ministry_stats = self.ministry_scraper.scrape_ministry_jobs(
                    max_pages=_ministry_max_pages,
                    min_score=_ministry_min_score,
                )
                all_stats["ministry"] = ministry_stats

                # Update totals
                all_stats["total_jobs_found"] += ministry_stats.get("jobs_found", 0)
                all_stats["total_jobs_stored"] += ministry_stats.get("jobs_stored", 0)

            except Exception as e:
                print(f"✗ Ministry scraper error: {e}")
                all_stats["ministry"] = {
                    "pages_scraped": 0,
                    "jobs_found": 0,
                    "jobs_stored": 0,
                    "jobs_scored": 0,
                    "profile_scores": {},
                    "error": str(e),
                }

        # Final summary
        self._print_summary(all_stats, fetch_emails, scrape_companies, scrape_ministry)

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
        ran_ministry: bool = False,
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

        if ran_ministry:
            ministry_stats = all_stats["ministry"]
            print("\n🧪 Ministry of Testing:")
            print(f"  Pages scraped: {ministry_stats.get('pages_scraped', 0)}")
            print(f"  Jobs found: {ministry_stats.get('jobs_found', 0)}")
            print(f"  Jobs stored: {ministry_stats.get('jobs_stored', 0)}")
            print(f"  Jobs scored: {ministry_stats.get('jobs_scored', 0)}")

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


def run_all_inboxes(
    run_emails: bool = True,
    run_companies: bool = True,
    email_limit: int | None = None,
    companies_min_score: int = 50,
    company_filter: str | None = None,
    skip_recent_hours: int | None = None,
) -> dict:
    """
    Run unified scraper across ALL profiles with configured email inboxes.

    Flow:
    1. Get enabled profiles with email_credentials (check profile.email_username)
    2. For EACH profile: scrape emails only (companies/ministry disabled)
    3. After all emails: run companies + ministry ONCE (shared resources)
    4. Aggregate and return combined stats

    Args:
        run_emails: Whether to process email sources
        run_companies: Whether to scrape companies and ministry
        email_limit: Max emails per inbox (None = all unread)
        companies_min_score: Minimum score for company jobs
        company_filter: Filter companies by notes
        skip_recent_hours: Skip recently-checked companies

    Returns:
        Aggregated stats from all inboxes and shared sources
    """
    from utils.profile_manager import get_profile_manager

    print("=" * 80)
    print("MULTI-INBOX MODE - PROCESSING ALL CONFIGURED EMAIL ACCOUNTS")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Get profiles with email credentials
    manager = get_profile_manager()
    profiles_with_email = [
        p for p in manager.get_enabled_profiles() if p.email_username and p.email_app_password
    ]

    if not profiles_with_email:
        print("\n✗ No profiles with email credentials found!")
        print("  Ensure profiles have 'email_credentials' configured in JSON")
        return {
            "profiles": {},
            "email_totals": {},
            "companies": {},
            "ministry": {},
            "grand_totals": {},
            "errors": ["No profiles with email credentials"],
        }

    print(f"\n📬 Found {len(profiles_with_email)} inboxes to process:")
    for p in profiles_with_email:
        print(f"  • {p.name} ({p.id}) - {p.email_username}")
    print("=" * 80 + "\n")

    # Initialize aggregated stats
    aggregated_stats: dict[str, dict | list] = {
        "profiles": {},
        "email_totals": {},
        "companies": {},
        "ministry": {},
        "grand_totals": {},
        "errors": [],
    }

    # PART 1: Process all email inboxes
    if run_emails:
        profile_results = _process_all_inboxes(profiles_with_email, email_limit=email_limit)
        aggregated_stats["profiles"] = profile_results
        aggregated_stats["email_totals"] = _aggregate_email_stats(profile_results)

    # PART 2: Scrape companies ONCE (shared resource)
    if run_companies:
        company_stats = _scrape_shared_companies(
            min_score=companies_min_score,
            company_filter=company_filter,
            skip_recent_hours=skip_recent_hours,
        )
        aggregated_stats["companies"] = company_stats

        # PART 3: Scrape Ministry ONCE (shared resource)
        ministry_stats = _scrape_shared_ministry()
        aggregated_stats["ministry"] = ministry_stats

    # Calculate grand totals
    aggregated_stats["grand_totals"] = _calculate_grand_totals(aggregated_stats)

    # Print summary
    _print_all_inboxes_summary(aggregated_stats, run_emails, run_companies)

    return aggregated_stats


def _process_all_inboxes(profiles: list, email_limit: int | None = None) -> dict:
    """
    Process email inbox for each profile sequentially.

    Args:
        profiles: List of Profile objects with email credentials
        email_limit: Max emails per inbox

    Returns:
        Dict mapping profile_id -> {name, email_stats, status, error}
    """
    results = {}

    for i, profile in enumerate(profiles, 1):
        print("\n" + "=" * 80)
        print(f"INBOX {i}/{len(profiles)}: {profile.name} ({profile.email_username})")
        print("=" * 80 + "\n")

        try:
            scraper = WeeklyUnifiedScraper(profile=profile.id)
            profile_stats = scraper.run_all(
                fetch_emails=True,
                email_limit=email_limit,
                scrape_companies=False,
                scrape_ministry=False,
            )

            results[profile.id] = {
                "name": profile.name,
                "email_stats": profile_stats["email"],
                "status": "success",
            }

            print(f"\n✓ Completed inbox for {profile.name}")

        except Exception as e:
            print(f"\n✗ Error processing inbox for {profile.name}: {e}")
            results[profile.id] = {"name": profile.name, "status": "error", "error": str(e)}

    return results


def _aggregate_email_stats(profile_results: dict) -> dict:
    """
    Aggregate email stats across all profiles.

    Args:
        profile_results: Dict from _process_all_inboxes()

    Returns:
        Aggregated totals
    """
    totals = {
        "total_emails_processed": 0,
        "total_jobs_found": 0,
        "total_jobs_stored": 0,
        "total_notifications": 0,
        "successful_profiles": 0,
        "failed_profiles": 0,
    }

    for _profile_id, result in profile_results.items():
        if result["status"] == "success":
            email_stats = result["email_stats"]
            totals["total_emails_processed"] += email_stats.get("emails_processed", 0)
            totals["total_jobs_found"] += email_stats.get("opportunities_found", 0)
            totals["total_jobs_stored"] += email_stats.get("jobs_stored", 0)
            totals["total_notifications"] += email_stats.get("notifications_sent", 0)
            totals["successful_profiles"] += 1
        else:
            totals["failed_profiles"] += 1

    return totals


def _scrape_shared_companies(
    min_score: int = 50,
    company_filter: str | None = None,
    skip_recent_hours: int | None = None,
) -> dict:
    """
    Scrape monitored companies ONCE (shared across all profiles).

    Returns:
        Company scraping stats (or error dict)
    """
    print("\n" + "=" * 80)
    print("SHARED RESOURCE: COMPANY MONITORING (ALL PROFILES)")
    print("=" * 80 + "\n")

    try:
        # Use None profile since companies are shared
        scraper = WeeklyUnifiedScraper(profile=None)
        company_stats = scraper._scrape_monitored_companies(
            min_score=min_score,
            company_filter=company_filter,
            skip_recent_hours=skip_recent_hours,
        )
        print("\n✓ Company monitoring completed")
        return company_stats

    except Exception as e:
        print(f"\n✗ Company scraping error: {e}")
        return {"companies_checked": 0, "jobs_scraped": 0, "jobs_stored": 0, "error": str(e)}


def _scrape_shared_ministry() -> dict:
    """
    Scrape Ministry of Testing ONCE (shared across all profiles).

    Returns:
        Ministry scraping stats (or error dict)
    """
    print("\n" + "=" * 80)
    print("SHARED RESOURCE: MINISTRY OF TESTING (ALL PROFILES)")
    print("=" * 80 + "\n")

    try:
        scraper = WeeklyUnifiedScraper(profile=None)
        ministry_stats = scraper.ministry_scraper.scrape_ministry_jobs(
            max_pages=3,
            min_score=47,
        )
        print("\n✓ Ministry of Testing scraping completed")
        return ministry_stats

    except Exception as e:
        print(f"\n✗ Ministry scraping error: {e}")
        return {"pages_scraped": 0, "jobs_found": 0, "jobs_stored": 0, "error": str(e)}


def _calculate_grand_totals(aggregated_stats: dict) -> dict:
    """
    Calculate grand totals across all sources.

    Args:
        aggregated_stats: Full stats dict from run_all_inboxes()

    Returns:
        Grand totals dict
    """
    email_totals = aggregated_stats.get("email_totals", {})
    company_stats = aggregated_stats.get("companies", {})
    ministry_stats = aggregated_stats.get("ministry", {})

    return {
        "total_jobs_found": (
            email_totals.get("total_jobs_found", 0)
            + company_stats.get("jobs_scraped", 0)
            + ministry_stats.get("jobs_found", 0)
        ),
        "total_jobs_stored": (
            email_totals.get("total_jobs_stored", 0)
            + company_stats.get("jobs_stored", 0)
            + ministry_stats.get("jobs_stored", 0)
        ),
        "total_notifications": (
            email_totals.get("total_notifications", 0) + company_stats.get("notifications_sent", 0)
        ),
    }


def _print_all_inboxes_summary(
    aggregated_stats: dict, ran_emails: bool, ran_companies: bool
) -> None:
    """
    Print comprehensive summary for all-inboxes mode.

    Args:
        aggregated_stats: Full stats from run_all_inboxes()
        ran_emails: Whether email processing ran
        ran_companies: Whether company/ministry scraping ran
    """
    print("\n" + "=" * 80)
    print("MULTI-INBOX MODE - FINAL SUMMARY")
    print("=" * 80)

    # Per-profile email results
    if ran_emails:
        print("\n📬 EMAIL PROCESSING BY INBOX:")
        profile_results = aggregated_stats.get("profiles", {})

        for _profile_id, result in profile_results.items():
            status_icon = "✓" if result["status"] == "success" else "✗"
            print(f"\n  {status_icon} {result['name']}:")

            if result["status"] == "success":
                email_stats = result["email_stats"]
                print(f"    Emails processed: {email_stats.get('emails_processed', 0)}")
                print(f"    Jobs found: {email_stats.get('opportunities_found', 0)}")
                print(f"    Jobs stored: {email_stats.get('jobs_stored', 0)}")
                print(f"    Notifications: {email_stats.get('notifications_sent', 0)}")
            else:
                print(f"    ERROR: {result.get('error', 'Unknown error')}")

        # Email totals
        email_totals = aggregated_stats.get("email_totals", {})
        print("\n  📊 EMAIL TOTALS (ALL INBOXES):")
        print(f"    Total emails processed: {email_totals.get('total_emails_processed', 0)}")
        print(f"    Total jobs found: {email_totals.get('total_jobs_found', 0)}")
        print(f"    Total jobs stored: {email_totals.get('total_jobs_stored', 0)}")
        print(f"    Total notifications: {email_totals.get('total_notifications', 0)}")
        print(f"    Successful inboxes: {email_totals.get('successful_profiles', 0)}")
        print(f"    Failed inboxes: {email_totals.get('failed_profiles', 0)}")

    # Company monitoring results
    if ran_companies:
        company_stats = aggregated_stats.get("companies", {})
        print("\n🏢 COMPANY MONITORING:")
        if "error" in company_stats:
            print(f"  ✗ ERROR: {company_stats['error']}")
        else:
            print(f"  Companies checked: {company_stats.get('companies_checked', 0)}")
            print(f"  Jobs scraped: {company_stats.get('jobs_scraped', 0)}")
            print(f"  Jobs stored: {company_stats.get('jobs_stored', 0)}")
            print(f"  Notifications: {company_stats.get('notifications_sent', 0)}")

        # Ministry results
        ministry_stats = aggregated_stats.get("ministry", {})
        print("\n🧪 MINISTRY OF TESTING:")
        if "error" in ministry_stats:
            print(f"  ✗ ERROR: {ministry_stats['error']}")
        else:
            print(f"  Pages scraped: {ministry_stats.get('pages_scraped', 0)}")
            print(f"  Jobs found: {ministry_stats.get('jobs_found', 0)}")
            print(f"  Jobs stored: {ministry_stats.get('jobs_stored', 0)}")

    # Grand totals
    grand_totals = aggregated_stats.get("grand_totals", {})
    print("\n📊 GRAND TOTALS (ALL SOURCES):")
    print(f"  Total jobs found: {grand_totals.get('total_jobs_found', 0)}")
    print(f"  Total jobs stored: {grand_totals.get('total_jobs_stored', 0)}")
    print(f"  Total notifications: {grand_totals.get('total_notifications', 0)}")

    # Errors summary
    errors = aggregated_stats.get("errors", [])
    if errors:
        print("\n⚠️  ERRORS:")
        for error in errors:
            print(f"  • {error}")

    print("\n" + "=" * 80)


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
    parser.add_argument(
        "--all-inboxes",
        action="store_true",
        help="Process ALL configured inboxes sequentially (wes, adam, etc.)",
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

    # Validate mutually exclusive flags
    if args.all_inboxes and args.profile:
        parser.error("Cannot specify both --all-inboxes and --profile")

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

    # Route to appropriate handler
    if args.all_inboxes:
        # Multi-inbox mode: process ALL configured email accounts
        stats = run_all_inboxes(
            run_emails=run_emails,
            run_companies=run_companies,
            email_limit=args.email_limit,
            companies_min_score=args.companies_min_score,
            company_filter=args.company_filter,
            skip_recent_hours=args.skip_recent_hours,
        )
    else:
        # Single profile mode
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
