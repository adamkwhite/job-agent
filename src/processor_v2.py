"""
Job processing pipeline V2 - with pluggable parsers and enrichment
IMAP → Parse (registry) → Enrich → Filter → Store → Notify
"""

import email
import imaplib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

# New architecture imports
import os

from dotenv import load_dotenv

from agents.job_scorer import JobScorer
from database import JobDatabase
from enrichment.enrichment_pipeline import EnrichmentPipeline
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from parsers.artemis_parser import ArtemisParser
from parsers.f6s_parser import F6SParser
from parsers.linkedin_parser import LinkedInParser
from parsers.parser_registry import ParserRegistry
from parsers.supra_parser import SupraParser


class JobProcessorV2:
    """Main orchestrator for job alert processing with pluggable parsers"""

    def __init__(self):
        load_dotenv()

        # Initialize components
        self.parser_registry = ParserRegistry()
        self.enrichment = EnrichmentPipeline()
        self.filter = JobFilter()
        self.database = JobDatabase()
        self.notifier = JobNotifier()
        self.scorer = JobScorer()

        # Register parsers
        self._register_parsers()

        # IMAP credentials
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.username = os.getenv("GMAIL_USERNAME")
        self.password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.username or not self.password:
            raise ValueError(
                "Gmail credentials not configured. Please set GMAIL_USERNAME and GMAIL_APP_PASSWORD in .env"
            )

    def _register_parsers(self):
        """Register all available parsers"""
        self.parser_registry.register(LinkedInParser())
        self.parser_registry.register(F6SParser())
        self.parser_registry.register(SupraParser())
        self.parser_registry.register(ArtemisParser())

        print(f"Registered parsers: {', '.join(self.parser_registry.get_enabled_parsers())}")

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        print(f"Connecting to {self.imap_server}...")
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        return mail

    def fetch_unread_emails(self, limit: int = 50) -> list[email.message.Message]:
        """Fetch unread emails from inbox"""
        mail = self.connect_imap()
        mail.select("INBOX")

        status, messages = mail.search(None, "UNSEEN")

        if status != "OK":
            print("No unread emails found")
            return []

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} unread emails")

        email_ids = email_ids[:limit]

        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if (
                    status != "OK"
                    or not msg_data
                    or not isinstance(msg_data, list)
                    or len(msg_data) == 0
                ):
                    continue

                first_msg = msg_data[0]
                if not isinstance(first_msg, tuple) or len(first_msg) < 2:
                    continue
                raw_email = first_msg[1]
                if not isinstance(raw_email, bytes):
                    continue
                email_message = email.message_from_bytes(raw_email)
                emails.append(email_message)

            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")
                continue

        mail.close()
        mail.logout()

        return emails

    def process_emails(self, emails: list[email.message.Message]) -> dict[str, int | list[str]]:
        """Process emails through the full pipeline"""
        stats: dict[str, int | list[str]] = {
            "emails_processed": 0,
            "opportunities_found": 0,
            "opportunities_enriched": 0,
            "jobs_passed_filter": 0,
            "jobs_stored": 0,
            "jobs_scored": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        for email_message in emails:
            try:
                subject = email_message.get("Subject", "No Subject")
                print(f"\n{'=' * 70}")
                print(f"Email: {subject}")
                print(f"{'=' * 70}")

                # Step 1: Parse email using appropriate parser
                parse_result = self.parser_registry.parse_email(email_message)

                if not parse_result.success:
                    print(f"  ✗ Parsing failed: {parse_result.error}")
                    errors_list = stats["errors"]
                    assert isinstance(errors_list, list)
                    errors_list.append(f"Parse error: {parse_result.error}")
                    continue

                opportunities = parse_result.opportunities
                stats["opportunities_found"] = cast(int, stats["opportunities_found"]) + len(
                    opportunities
                )

                print(f"  Parser: {parse_result.parser_name}")
                print(f"  Opportunities found: {len(opportunities)}")

                # Step 2: Enrich opportunities that need research (funding leads)
                enriched_opportunities = self.enrichment.enrich_opportunities(opportunities)
                stats["opportunities_enriched"] = cast(int, stats["opportunities_enriched"]) + len(
                    [o for o in enriched_opportunities if o.research_attempted]
                )

                # Step 3: Filter opportunities
                included_opps, excluded_opps = self.filter.filter_jobs(
                    [self._opportunity_to_dict(o) for o in enriched_opportunities]
                )

                stats["jobs_passed_filter"] = cast(int, stats["jobs_passed_filter"]) + len(
                    included_opps
                )

                print("\nFiltering Results:")
                print(f"  ✓ Passed: {len(included_opps)}")
                print(f"  ✗ Excluded: {len(excluded_opps)}")

                # Step 4: Store, score, and notify
                for job_dict in included_opps:
                    job_id = self.database.add_job(job_dict)

                    if job_id:
                        stats["jobs_stored"] = cast(int, stats["jobs_stored"]) + 1
                        print("\n✓ New Job Stored:")
                        print(f"  Title: {job_dict['title']}")
                        print(f"  Company: {job_dict['company']}")
                        print(f"  Keywords: {', '.join(job_dict.get('keywords_matched', []))}")
                        print(f"  Link: {job_dict['link']}")

                        # Step 4.5: Score the job
                        try:
                            score, grade, breakdown = self.scorer.score_job(job_dict)

                            # Update database with score
                            self.database.update_job_score(
                                job_id, score, grade, json.dumps(breakdown)
                            )

                            stats["jobs_scored"] = cast(int, stats["jobs_scored"]) + 1
                            print(f"  ✓ Scored: {grade} ({score}/100)")
                            print(
                                f"    Breakdown: Seniority={breakdown['seniority']}, Domain={breakdown['domain']}, Role={breakdown['role_type']}"
                            )

                        except Exception as e:
                            print(f"  ✗ Scoring failed: {e}")
                            errors_list = stats["errors"]
                            assert isinstance(errors_list, list)
                            errors_list.append(f"Scoring failed for job {job_id}: {e}")

                        # Send notification ONLY for A/B grade jobs (70+)
                        if score >= 70:  # A or B grade
                            try:
                                # Add score to notification title for priority
                                notification_job = job_dict.copy()
                                notification_job["title"] = f"[{grade} {score}] {job_dict['title']}"

                                notification_results = self.notifier.notify_job(notification_job)

                                if notification_results.get("email") or notification_results.get(
                                    "sms"
                                ):
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
                            print(f"  ⊘ Notification skipped: Low score ({grade} {score}/100)")

                    else:
                        print(f"\n- Duplicate: {job_dict['title']} at {job_dict['company']}")

                stats["emails_processed"] = cast(int, stats["emails_processed"]) + 1

            except Exception as e:
                print(f"Error processing email: {e}")
                errors_list = stats["errors"]
                assert isinstance(errors_list, list)
                errors_list.append(str(e))
                continue

        return stats

    def _opportunity_to_dict(self, opp: OpportunityData) -> dict:
        """Convert OpportunityData to dict for compatibility with existing code"""
        return {
            "title": opp.title or "Job Opportunity",
            "company": opp.company,
            "location": opp.location or opp.company_location or "",
            "link": opp.link or opp.career_page_url or "",
            "description": opp.description or "",
            "salary": opp.salary or "",
            "job_type": opp.job_type or "",
            "posted_date": opp.posted_date or "",
            "source": opp.source,
            "source_email": opp.source_email or "",
            "received_at": opp.received_at,
            "keywords_matched": opp.keywords_matched or [],
            "raw_email_content": opp.raw_content or "",
        }

    def run(self, fetch_emails: bool = True, limit: int = 50) -> dict:
        """Main entry point - run the full pipeline"""
        print(f"\n{'=' * 70}")
        print("Job Alert Processor V2 Starting")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        if fetch_emails:
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
        print(f"\n{'=' * 70}")
        print("Processing Complete")
        print(f"{'=' * 70}")
        print(f"Emails processed: {stats['emails_processed']}")
        print(f"Opportunities found: {stats['opportunities_found']}")
        print(f"Opportunities enriched: {stats['opportunities_enriched']}")
        print(f"Jobs passed filter: {stats['jobs_passed_filter']}")
        print(f"New jobs stored: {stats['jobs_stored']}")
        print(f"Jobs scored: {stats['jobs_scored']}")
        print(f"Notifications sent: {stats['notifications_sent']}")

        errors_list_final = stats["errors"]
        if errors_list_final:
            assert isinstance(errors_list_final, list)
            print(f"\nErrors: {len(errors_list_final)}")
            for error in errors_list_final[:5]:
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

    parser = argparse.ArgumentParser(description="Process job alert emails (V2)")
    parser.add_argument("--test", action="store_true", help="Test mode (no IMAP fetch)")
    parser.add_argument("--limit", type=int, default=50, help="Max emails to process")

    args = parser.parse_args()

    try:
        processor = JobProcessorV2()
        stats = processor.run(fetch_emails=not args.test, limit=args.limit)

        # Return stats as JSON for n8n
        print("\n" + json.dumps(stats, indent=2))

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
