"""
Main job processing pipeline: IMAP → Parse → Filter → Store → Notify
"""

import email
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from database import JobDatabase
from email_parser import JobEmailParser
from imap_client import IMAPEmailClient
from job_filter import JobFilter
from notifier import JobNotifier


class JobProcessor:
    """Main orchestrator for job alert processing"""

    def __init__(self):
        self.parser = JobEmailParser()
        self.filter = JobFilter()
        self.database = JobDatabase()
        self.notifier = JobNotifier()
        self.imap_client = IMAPEmailClient()

    def fetch_unread_emails(self, limit: int = 50) -> list[email.message.Message]:
        """Fetch unread emails from inbox"""
        return self.imap_client.fetch_unread_emails(limit)

    def process_emails(self, emails: list[email.message.Message]) -> dict:
        """
        Process emails through the full pipeline

        Returns:
            Statistics dictionary
        """
        stats: dict[str, int | list[str]] = {
            "emails_processed": 0,
            "jobs_found": 0,
            "jobs_passed_filter": 0,
            "jobs_stored": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        for email_message in emails:
            try:
                # Parse email to extract jobs
                jobs = self.parser.parse_email(email_message)
                stats["jobs_found"] = cast(int, stats["jobs_found"]) + len(jobs)

                # Filter jobs
                included_jobs, excluded_jobs = self.filter.filter_jobs(jobs)
                stats["jobs_passed_filter"] = cast(int, stats["jobs_passed_filter"]) + len(
                    included_jobs
                )

                print(f"\n{'=' * 60}")
                print(f"Email: {email_message.get('Subject', 'No Subject')}")
                print(f"Found: {len(jobs)} jobs | Passed filter: {len(included_jobs)}")

                # Process included jobs
                for job in included_jobs:
                    # Store in database
                    job_id = self.database.add_job(job)

                    if job_id:
                        stats["jobs_stored"] = cast(int, stats["jobs_stored"]) + 1
                        print(f"\n✓ New Job: {job['title']} at {job['company']}")
                        print(f"  Keywords: {', '.join(job.get('keywords_matched', []))}")
                        print(f"  Link: {job['link']}")

                        # Send notification
                        try:
                            notification_results = self.notifier.notify_job(job)

                            if notification_results.get("email") or notification_results.get("sms"):
                                stats["notifications_sent"] = (
                                    cast(int, stats["notifications_sent"]) + 1
                                )
                                self.database.mark_notified(job_id)
                                print(
                                    f"  ✓ Notified: SMS={notification_results.get('sms')}, Email={notification_results.get('email')}"
                                )
                        except Exception as e:
                            print(f"  ✗ Notification failed: {e}")
                            errors_list = stats["errors"]
                            assert isinstance(errors_list, list)
                            errors_list.append(f"Notification failed for job {job_id}: {e}")

                    else:
                        print(f"\n- Duplicate: {job['title']} at {job['company']}")

                # Log excluded jobs
                if excluded_jobs:
                    print(f"\nExcluded {len(excluded_jobs)} jobs:")
                    for job in excluded_jobs[:5]:  # Show first 5
                        reason = job.get("filter_result", {}).get("reason", "Unknown")
                        print(f"  - {job.get('title', 'Unknown')}: {reason}")

                stats["emails_processed"] = cast(int, stats["emails_processed"]) + 1

            except Exception as e:
                print(f"Error processing email: {e}")
                errors_list = stats["errors"]
                assert isinstance(errors_list, list)
                errors_list.append(str(e))
                continue

        return stats

    def run(self, fetch_emails: bool = True, limit: int = 50) -> dict:
        """
        Main entry point - run the full pipeline

        Args:
            fetch_emails: If True, fetch from IMAP. If False, use provided test emails.
            limit: Maximum number of emails to process

        Returns:
            Processing statistics
        """
        print(f"\n{'=' * 60}")
        print("Job Alert Processor Starting")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        if fetch_emails:
            # Fetch unread emails from IMAP
            emails = self.fetch_unread_emails(limit=limit)
        else:
            print("No emails to process (test mode)")
            return {"emails_processed": 0}

        if not emails:
            print("No emails to process")
            return {"emails_processed": 0}

        # Process emails
        stats = self.process_emails(emails)

        # Print summary
        print(f"\n{'=' * 60}")
        print("Processing Complete")
        print(f"{'=' * 60}")
        print(f"Emails processed: {stats['emails_processed']}")
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Jobs passed filter: {stats['jobs_passed_filter']}")
        print(f"New jobs stored: {stats['jobs_stored']}")
        print(f"Notifications sent: {stats['notifications_sent']}")

        if stats["errors"]:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats["errors"][:5]:
                print(f"  - {error}")

        # Database stats
        db_stats = self.database.get_stats()
        print("\nDatabase Stats:")
        print(f"  Total jobs: {db_stats['total_jobs']}")
        print(f"  Notified: {db_stats['notified_jobs']}")
        print(f"  Pending: {db_stats['unnotified_jobs']}")

        return stats


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Process job alert emails")
    parser.add_argument("--test", action="store_true", help="Test mode (no IMAP fetch)")
    parser.add_argument("--limit", type=int, default=50, help="Max emails to process")

    args = parser.parse_args()

    try:
        processor = JobProcessor()
        stats = processor.run(fetch_emails=not args.test, limit=args.limit)

        # Return stats as JSON for n8n
        print("\n" + json.dumps(stats, indent=2))

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
