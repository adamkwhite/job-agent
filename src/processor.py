"""
Main job processing pipeline: IMAP → Parse → Filter → Store → Notify
"""
import imaplib
import email
import json
import sys
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from email_parser import JobEmailParser
from job_filter import JobFilter
from database import JobDatabase
from notifier import JobNotifier

from dotenv import load_dotenv
import os


class JobProcessor:
    """Main orchestrator for job alert processing"""

    def __init__(self):
        load_dotenv()

        self.parser = JobEmailParser()
        self.filter = JobFilter()
        self.database = JobDatabase()
        self.notifier = JobNotifier()

        # IMAP credentials
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.username = os.getenv('GMAIL_USERNAME')
        self.password = os.getenv('GMAIL_APP_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("Gmail credentials not configured. Please set GMAIL_USERNAME and GMAIL_APP_PASSWORD in .env")

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        print(f"Connecting to {self.imap_server}...")
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        return mail

    def fetch_unread_emails(self, limit: int = 50) -> List[email.message.Message]:
        """Fetch unread emails from inbox"""
        mail = self.connect_imap()
        mail.select('INBOX')

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')

        if status != 'OK':
            print("No unread emails found")
            return []

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} unread emails")

        # Limit number of emails to process
        email_ids = email_ids[:limit]

        emails = []
        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                emails.append(email_message)

            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")
                continue

        mail.close()
        mail.logout()

        return emails

    def process_emails(self, emails: List[email.message.Message]) -> Dict:
        """
        Process emails through the full pipeline

        Returns:
            Statistics dictionary
        """
        stats = {
            'emails_processed': 0,
            'jobs_found': 0,
            'jobs_passed_filter': 0,
            'jobs_stored': 0,
            'notifications_sent': 0,
            'errors': []
        }

        for email_message in emails:
            try:
                # Parse email to extract jobs
                jobs = self.parser.parse_email(email_message)
                stats['jobs_found'] += len(jobs)

                # Filter jobs
                included_jobs, excluded_jobs = self.filter.filter_jobs(jobs)
                stats['jobs_passed_filter'] += len(included_jobs)

                print(f"\n{'='*60}")
                print(f"Email: {email_message.get('Subject', 'No Subject')}")
                print(f"Found: {len(jobs)} jobs | Passed filter: {len(included_jobs)}")

                # Process included jobs
                for job in included_jobs:
                    # Store in database
                    job_id = self.database.add_job(job)

                    if job_id:
                        stats['jobs_stored'] += 1
                        print(f"\n✓ New Job: {job['title']} at {job['company']}")
                        print(f"  Keywords: {', '.join(job.get('keywords_matched', []))}")
                        print(f"  Link: {job['link']}")

                        # Send notification
                        try:
                            notification_results = self.notifier.notify_job(job)

                            if notification_results.get('email') or notification_results.get('sms'):
                                stats['notifications_sent'] += 1
                                self.database.mark_notified(job_id)
                                print(f"  ✓ Notified: SMS={notification_results.get('sms')}, Email={notification_results.get('email')}")
                        except Exception as e:
                            print(f"  ✗ Notification failed: {e}")
                            stats['errors'].append(f"Notification failed for job {job_id}: {e}")

                    else:
                        print(f"\n- Duplicate: {job['title']} at {job['company']}")

                # Log excluded jobs
                if excluded_jobs:
                    print(f"\nExcluded {len(excluded_jobs)} jobs:")
                    for job in excluded_jobs[:5]:  # Show first 5
                        reason = job.get('filter_result', {}).get('reason', 'Unknown')
                        print(f"  - {job.get('title', 'Unknown')}: {reason}")

                stats['emails_processed'] += 1

            except Exception as e:
                print(f"Error processing email: {e}")
                stats['errors'].append(str(e))
                continue

        return stats

    def run(self, fetch_emails: bool = True, limit: int = 50) -> Dict:
        """
        Main entry point - run the full pipeline

        Args:
            fetch_emails: If True, fetch from IMAP. If False, use provided test emails.
            limit: Maximum number of emails to process

        Returns:
            Processing statistics
        """
        print(f"\n{'='*60}")
        print("Job Alert Processor Starting")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        if fetch_emails:
            # Fetch unread emails from IMAP
            emails = self.fetch_unread_emails(limit=limit)
        else:
            print("No emails to process (test mode)")
            return {'emails_processed': 0}

        if not emails:
            print("No emails to process")
            return {'emails_processed': 0}

        # Process emails
        stats = self.process_emails(emails)

        # Print summary
        print(f"\n{'='*60}")
        print("Processing Complete")
        print(f"{'='*60}")
        print(f"Emails processed: {stats['emails_processed']}")
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Jobs passed filter: {stats['jobs_passed_filter']}")
        print(f"New jobs stored: {stats['jobs_stored']}")
        print(f"Notifications sent: {stats['notifications_sent']}")

        if stats['errors']:
            print(f"\nErrors: {len(stats['errors'])}")
            for error in stats['errors'][:5]:
                print(f"  - {error}")

        # Database stats
        db_stats = self.database.get_stats()
        print(f"\nDatabase Stats:")
        print(f"  Total jobs: {db_stats['total_jobs']}")
        print(f"  Notified: {db_stats['notified_jobs']}")
        print(f"  Pending: {db_stats['unnotified_jobs']}")

        return stats


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Process job alert emails')
    parser.add_argument('--test', action='store_true', help='Test mode (no IMAP fetch)')
    parser.add_argument('--limit', type=int, default=50, help='Max emails to process')

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
