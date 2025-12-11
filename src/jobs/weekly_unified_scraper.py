"""
Unified Weekly Scraper
Combines all job sources: emails, robotics sheet, and company monitoring
Runs weekly to find new opportunities across all channels
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.company_scraper import CompanyScraper
from jobs.weekly_robotics_scraper import WeeklyRoboticsJobChecker
from processor_v2 import JobProcessorV2


class WeeklyUnifiedScraper:
    """
    Unified weekly scraper combining all job sources:
    1. Email-based sources (LinkedIn, Supra, F6S, Artemis, Built In, etc.)
    2. Robotics/Deeptech Google Sheet
    3. Company monitoring (Wes's 26+ companies)
    """

    def __init__(self, profile: str | None = None, enable_llm_extraction: bool = False):
        # Store profile for logging and sub-components
        self.profile = profile

        # Email processor (handles all email parsers)
        self.email_processor = JobProcessorV2(profile=profile)

        # Robotics sheet scraper
        self.robotics_checker = WeeklyRoboticsJobChecker(profile=profile)

        # Company monitoring scraper
        self.company_scraper = CompanyScraper(
            profile=profile, enable_llm_extraction=enable_llm_extraction
        )

    def run_all(
        self,
        fetch_emails: bool = True,
        email_limit: int = 50,
        scrape_robotics: bool = True,
        robotics_min_score: int = 70,
        scrape_companies: bool = True,
        companies_min_score: int = 50,
        company_filter: str | None = None,
    ) -> dict:
        """
        Run all job processing sources

        Args:
            fetch_emails: Whether to fetch and process emails
            email_limit: Max emails to process
            scrape_robotics: Whether to scrape robotics sheet
            robotics_min_score: Minimum score for robotics jobs
            scrape_companies: Whether to scrape monitored companies
            companies_min_score: Minimum score for company jobs (default: 50 for D+ grade)
            company_filter: Filter companies by notes (e.g., "From Wes")

        Returns:
            Combined stats from all sources
        """
        print("=" * 80)
        print("UNIFIED WEEKLY SCRAPER - ALL JOB SOURCES")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"📧 Email processing: {fetch_emails}")
        print(f"🤖 Robotics scraping: {scrape_robotics}")
        print(f"🏢 Company monitoring: {scrape_companies}")
        print("=" * 80 + "\n")

        all_stats = {
            "email": {},
            "robotics": {},
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

        # PART 2: Robotics/Deeptech sheet
        if scrape_robotics:
            print("\n" + "=" * 80)
            print("PART 2: ROBOTICS/DEEPTECH WEB SCRAPING")
            print("=" * 80 + "\n")

            robotics_stats = self.robotics_checker.run(
                min_score=robotics_min_score, leadership_only=True
            )

            all_stats["robotics"] = robotics_stats
            all_stats["total_jobs_found"] += robotics_stats.get("jobs_scraped", 0)
            all_stats["total_jobs_stored"] += robotics_stats.get("jobs_stored", 0)
            all_stats["total_notifications"] += robotics_stats.get("notifications_sent", 0)

        # PART 3: Company monitoring
        if scrape_companies:
            print("\n" + "=" * 80)
            print("PART 3: COMPANY MONITORING (FIRECRAWL)")
            print("=" * 80 + "\n")

            company_stats = self._scrape_monitored_companies(
                min_score=companies_min_score, company_filter=company_filter
            )

            all_stats["companies"] = company_stats
            all_stats["total_jobs_found"] += company_stats.get("jobs_scraped", 0)
            all_stats["total_jobs_stored"] += company_stats.get("jobs_stored", 0)
            all_stats["total_notifications"] += company_stats.get("notifications_sent", 0)

        # Final summary
        self._print_summary(all_stats, fetch_emails, scrape_robotics, scrape_companies)

        return all_stats

    def _scrape_monitored_companies(
        self, min_score: int = 50, company_filter: str | None = None
    ) -> dict:
        """
        Scrape all monitored companies using Firecrawl

        Args:
            min_score: Minimum score to store/notify
            company_filter: Filter companies by notes (e.g., "From Wes")

        Returns:
            Stats dictionary
        """
        return self.company_scraper.scrape_all_companies(
            min_score=min_score, company_filter=company_filter, notify_threshold=80
        )

    def _print_summary(
        self,
        all_stats: dict,
        ran_emails: bool,
        ran_robotics: bool,
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

        if ran_robotics:
            robotics_stats = all_stats["robotics"]
            print("\n🤖 Robotics Sheet:")
            print(f"  Jobs scraped: {robotics_stats.get('jobs_scraped', 0)}")
            print(f"  High-scoring (B+): {robotics_stats.get('jobs_above_threshold', 0)}")
            print(f"  Jobs stored: {robotics_stats.get('jobs_stored', 0)}")
            print(f"  Notifications: {robotics_stats.get('notifications_sent', 0)}")

        if ran_companies:
            company_stats = all_stats["companies"]
            print("\n🏢 Company Monitoring:")
            print(f"  Companies checked: {company_stats.get('companies_checked', 0)}")
            print(f"  Jobs scraped: {company_stats.get('jobs_scraped', 0)}")
            print(f"  Leadership roles: {company_stats.get('leadership_jobs', 0)}")
            print(f"  Jobs stored: {company_stats.get('jobs_stored', 0)}")
            print(f"  Notifications: {company_stats.get('notifications_sent', 0)}")

        print("\n📊 TOTALS:")
        print(f"  Jobs found: {all_stats['total_jobs_found']}")
        print(f"  Jobs stored: {all_stats['total_jobs_stored']}")
        print(f"  Notifications sent: {all_stats['total_notifications']}")


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
    parser.add_argument("--robotics-only", action="store_true", help="Only scrape robotics sheet")
    parser.add_argument(
        "--companies-only", action="store_true", help="Only scrape monitored companies"
    )

    # Email options
    parser.add_argument("--email-limit", type=int, default=50, help="Max emails to process")

    # Robotics options
    parser.add_argument(
        "--robotics-min-score", type=int, default=70, help="Min score for robotics jobs"
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
        "--llm-extraction",
        action="store_true",
        help="Enable LLM extraction in parallel with regex for company monitoring (requires OpenRouter API key)",
    )

    args = parser.parse_args()

    # Determine what to run
    if args.email_only:
        run_emails = True
        run_robotics = False
        run_companies = False
    elif args.robotics_only:
        run_emails = False
        run_robotics = True
        run_companies = False
    elif args.companies_only:
        run_emails = False
        run_robotics = False
        run_companies = True
    else:
        # Run all sources by default
        run_emails = True
        run_robotics = True
        run_companies = True

    scraper = WeeklyUnifiedScraper(profile=args.profile, enable_llm_extraction=args.llm_extraction)
    stats = scraper.run_all(
        fetch_emails=run_emails,
        email_limit=args.email_limit,
        scrape_robotics=run_robotics,
        robotics_min_score=args.robotics_min_score,
        scrape_companies=run_companies,
        companies_min_score=args.companies_min_score,
        company_filter=args.company_filter,
    )

    # Output JSON for logging
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
