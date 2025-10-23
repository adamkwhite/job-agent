"""
Master Job Processor
Runs both email processing AND web scraping in one command
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from processor_v2 import JobProcessorV2
from jobs.weekly_robotics_scraper import WeeklyRoboticsJobChecker


class MasterJobProcessor:
    """Master processor that runs all job sources"""

    def __init__(self):
        self.email_processor = JobProcessorV2()
        self.robotics_checker = WeeklyRoboticsJobChecker()

    def run_all(self,
                fetch_emails: bool = True,
                email_limit: int = 50,
                scrape_robotics: bool = True,
                robotics_min_score: int = 70) -> dict:
        """
        Run all job processing sources

        Args:
            fetch_emails: Whether to fetch and process emails
            email_limit: Max emails to process
            scrape_robotics: Whether to scrape robotics sheet
            robotics_min_score: Minimum score for robotics jobs

        Returns:
            Combined stats from all sources
        """
        print("="*80)
        print("MASTER JOB PROCESSOR - ALL SOURCES")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        print(f"Email processing: {fetch_emails}")
        print(f"Robotics scraping: {scrape_robotics}")
        print("="*80 + "\n")

        all_stats = {
            'email': {},
            'robotics': {},
            'total_jobs_stored': 0,
            'total_notifications': 0
        }

        # Step 1: Process emails (LinkedIn, Supra, F6S, Artemis)
        if fetch_emails:
            print("\n" + "="*80)
            print("PART 1: EMAIL-BASED SOURCES")
            print("="*80 + "\n")

            email_stats = self.email_processor.run(
                fetch_emails=fetch_emails,
                limit=email_limit
            )

            all_stats['email'] = email_stats
            all_stats['total_jobs_stored'] += email_stats.get('jobs_stored', 0)
            all_stats['total_notifications'] += email_stats.get('notifications_sent', 0)

        # Step 2: Scrape robotics sheet
        if scrape_robotics:
            print("\n" + "="*80)
            print("PART 2: ROBOTICS/DEEPTECH WEB SCRAPING")
            print("="*80 + "\n")

            robotics_stats = self.robotics_checker.run(
                min_score=robotics_min_score,
                leadership_only=True
            )

            all_stats['robotics'] = robotics_stats
            all_stats['total_jobs_stored'] += robotics_stats.get('jobs_stored', 0)
            all_stats['total_notifications'] += robotics_stats.get('notifications_sent', 0)

        # Final summary
        print("\n" + "="*80)
        print("MASTER PROCESSOR - FINAL SUMMARY")
        print("="*80)

        if fetch_emails:
            print(f"\n📧 Email Sources:")
            print(f"  Emails processed: {all_stats['email'].get('emails_processed', 0)}")
            print(f"  Jobs stored: {all_stats['email'].get('jobs_stored', 0)}")
            print(f"  Jobs scored: {all_stats['email'].get('jobs_scored', 0)}")
            print(f"  Notifications: {all_stats['email'].get('notifications_sent', 0)}")

        if scrape_robotics:
            print(f"\n🤖 Robotics Sheet:")
            print(f"  Jobs scraped: {all_stats['robotics'].get('jobs_scraped', 0)}")
            print(f"  High-scoring (B+): {all_stats['robotics'].get('jobs_above_threshold', 0)}")
            print(f"  Jobs stored: {all_stats['robotics'].get('jobs_stored', 0)}")
            print(f"  Notifications: {all_stats['robotics'].get('notifications_sent', 0)}")

        print(f"\n📊 TOTALS:")
        print(f"  Jobs stored: {all_stats['total_jobs_stored']}")
        print(f"  Notifications sent: {all_stats['total_notifications']}")

        return all_stats


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Master job processor - all sources')
    parser.add_argument('--email-only', action='store_true', help='Only process emails')
    parser.add_argument('--robotics-only', action='store_true', help='Only scrape robotics sheet')
    parser.add_argument('--email-limit', type=int, default=50, help='Max emails to process')
    parser.add_argument('--robotics-min-score', type=int, default=70, help='Min score for robotics jobs')

    args = parser.parse_args()

    # Determine what to run
    run_emails = not args.robotics_only
    run_robotics = not args.email_only

    processor = MasterJobProcessor()
    stats = processor.run_all(
        fetch_emails=run_emails,
        email_limit=args.email_limit,
        scrape_robotics=run_robotics,
        robotics_min_score=args.robotics_min_score
    )

    # Output JSON for logging
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
