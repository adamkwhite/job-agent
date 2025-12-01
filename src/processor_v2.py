"""
Job processing pipeline V2 - with pluggable parsers and enrichment
IMAP → Parse (registry) → Enrich → Filter → Store → Notify
"""

import email
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

from agents.job_scorer import JobScorer
from database import JobDatabase
from enrichment.enrichment_pipeline import EnrichmentPipeline
from imap_client import IMAPEmailClient
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from parsers.artemis_parser import ArtemisParser
from parsers.builtin_parser import BuiltInParser
from parsers.f6s_parser import F6SParser
from parsers.jobbank_wrapper import JobBankParser
from parsers.linkedin_parser import LinkedInParser
from parsers.parser_registry import ParserRegistry
from parsers.recruiter_wrapper import RecruiterParser
from parsers.supra_parser import SupraParser
from parsers.workintech_wrapper import WorkInTechParser
from utils.multi_scorer import get_multi_scorer


class JobProcessorV2:
    """Main orchestrator for job alert processing with pluggable parsers"""

    def __init__(self, profile: str | None = None):
        # Store profile for multi-profile support
        self.profile = profile

        # Initialize components
        self.parser_registry = ParserRegistry()
        self.enrichment = EnrichmentPipeline()
        self.filter = JobFilter()
        self.database = JobDatabase(profile=profile)
        self.notifier = JobNotifier()
        self.scorer = JobScorer()
        self.imap_client = IMAPEmailClient(profile=profile)

        # Register parsers
        self._register_parsers()

    def _register_parsers(self):
        """Register all available parsers"""
        self.parser_registry.register(LinkedInParser())
        self.parser_registry.register(F6SParser())
        self.parser_registry.register(SupraParser())
        self.parser_registry.register(ArtemisParser())
        self.parser_registry.register(BuiltInParser())
        self.parser_registry.register(JobBankParser())
        self.parser_registry.register(RecruiterParser())
        self.parser_registry.register(WorkInTechParser())

        print(f"Registered parsers: {', '.join(self.parser_registry.get_enabled_parsers())}")

    def _increment_stat(self, stats: dict[str, int | list[str]], key: str, amount: int = 1) -> None:
        """Helper to increment a stat counter with type safety"""
        stats[key] = cast(int, stats[key]) + amount

    def _append_error(self, stats: dict[str, int | list[str]], error: str) -> None:
        """Helper to append error to stats with type safety"""
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        errors_list.append(error)

    def fetch_unread_emails(self, limit: int = 50) -> list[email.message.Message]:
        """Fetch unread emails from inbox"""
        return self.imap_client.fetch_unread_emails(limit)

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
            self._process_single_email(email_message, stats)

        return stats

    def _process_single_email(
        self, email_message: email.message.Message, stats: dict[str, int | list[str]]
    ) -> None:
        """Process a single email through parse -> enrich -> filter -> store pipeline"""
        try:
            subject = email_message.get("Subject", "No Subject")
            print(f"\n{'=' * 70}")
            print(f"Email: {subject}")
            print(f"{'=' * 70}")

            # Step 1: Parse email
            parse_result = self.parser_registry.parse_email(email_message)
            if not parse_result.success:
                self._handle_parse_error(parse_result.error, stats)
                return

            # Step 2: Enrich and filter
            included_opps = self._enrich_and_filter_opportunities(parse_result, stats)

            # Step 3: Process each job
            for job_dict in included_opps:
                self._store_and_process_job(job_dict, stats)

            self._increment_stat(stats, "emails_processed")

        except Exception as e:
            print(f"Error processing email: {e}")
            self._append_error(stats, str(e))

    def _handle_parse_error(self, error: str | None, stats: dict[str, int | list[str]]) -> None:
        """Handle parsing errors"""
        print(f"  ✗ Parsing failed: {error}")
        self._append_error(stats, f"Parse error: {error}")

    def _enrich_and_filter_opportunities(
        self, parse_result, stats: dict[str, int | list[str]]
    ) -> list[dict]:
        """Enrich opportunities and filter them"""
        opportunities = parse_result.opportunities
        self._increment_stat(stats, "opportunities_found", len(opportunities))

        print(f"  Parser: {parse_result.parser_name}")
        print(f"  Opportunities found: {len(opportunities)}")

        # Enrich opportunities
        enriched_opportunities = self.enrichment.enrich_opportunities(opportunities)
        enriched_count = len([o for o in enriched_opportunities if o.research_attempted])
        self._increment_stat(stats, "opportunities_enriched", enriched_count)

        # Filter opportunities
        included_opps, excluded_opps = self.filter.filter_jobs(
            [self._opportunity_to_dict(o) for o in enriched_opportunities]
        )

        self._increment_stat(stats, "jobs_passed_filter", len(included_opps))

        print("\nFiltering Results:")
        print(f"  ✓ Passed: {len(included_opps)}")
        print(f"  ✗ Excluded: {len(excluded_opps)}")

        return included_opps

    def _store_and_process_job(self, job_dict: dict, stats: dict[str, int | list[str]]) -> None:
        """Store a job and process it (score + notify)"""
        job_id = self.database.add_job(job_dict)

        if not job_id:
            print(f"\n- Duplicate: {job_dict['title']} at {job_dict['company']}")
            return

        self._increment_stat(stats, "jobs_stored")
        print("\n✓ New Job Stored:")
        print(f"  Title: {job_dict['title']}")
        print(f"  Company: {job_dict['company']}")
        print(f"  Keywords: {', '.join(job_dict.get('keywords_matched', []))}")
        print(f"  Link: {job_dict['link']}")

        # Score and notify
        score, grade = self._score_and_update_job(job_id, job_dict, stats)
        if score is not None and grade is not None:
            self._notify_if_qualified(job_id, job_dict, score, grade, stats)

    def _score_and_update_job(
        self, job_id: int, job_dict: dict, stats: dict[str, int | list[str]]
    ) -> tuple[int | None, str | None]:
        """Score a job and update database (for Wes - primary user)"""
        try:
            # Score for primary user (Wes - legacy behavior)
            score, grade, breakdown = self.scorer.score_job(job_dict)
            self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))

            self._increment_stat(stats, "jobs_scored")
            print(f"  ✓ Scored: {grade} ({score}/115)")
            print(
                f"    Breakdown: Seniority={breakdown['seniority']}, Domain={breakdown['domain']}, Role={breakdown['role_type']}"
            )

            # Also score for all profiles (multi-person support)
            try:
                multi_scorer = get_multi_scorer()
                profile_scores = multi_scorer.score_job_for_all(job_dict, job_id)
                profile_summary = ", ".join(
                    f"{pid}:{s}/{g}" for pid, (s, g) in profile_scores.items()
                )
                print(f"  ✓ Multi-profile scores: {profile_summary}")
            except Exception as mp_error:
                print(f"  ⚠ Multi-profile scoring failed: {mp_error}")

            return score, grade

        except Exception as e:
            print(f"  ✗ Scoring failed: {e}")
            self._append_error(stats, f"Scoring failed for job {job_id}: {e}")
            return None, None

    def _notify_if_qualified(
        self,
        job_id: int,
        job_dict: dict,
        score: int,
        grade: str,
        stats: dict[str, int | list[str]],
    ) -> None:
        """Send notification if job meets score threshold (70+)"""
        if score < 70:
            print(f"  ⊘ Notification skipped: Low score ({grade} {score}/100)")
            return

        try:
            notification_job = job_dict.copy()
            notification_job["title"] = f"[{grade} {score}] {job_dict['title']}"

            notification_results = self.notifier.notify_job(notification_job)

            if notification_results.get("email") or notification_results.get("sms"):
                self._increment_stat(stats, "notifications_sent")
                self.database.mark_notified(job_id)
                print(
                    f"  ✓ Notified: SMS={notification_results.get('sms')}, Email={notification_results.get('email')}"
                )
        except Exception as e:
            print(f"  ✗ Notification failed: {e}")
            self._append_error(stats, f"Notification failed for job {job_id}: {e}")

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
