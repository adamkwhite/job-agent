"""
Job processing pipeline V2 - with pluggable parsers and enrichment
IMAP → Parse (registry) → Enrich → Filter → Store → Notify
"""

import email
import json
import sys
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

from agents.job_filter_pipeline import JobFilterPipeline
from agents.profile_scorer import ProfileScorer
from database import JobDatabase
from enrichment.enrichment_pipeline import EnrichmentPipeline
from imap_client import IMAPEmailClient
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from parsers.artemis_parser import ArtemisParser
from parsers.builtin_parser import BuiltInParser
from parsers.f6s_parser import F6SParser
from parsers.indeed_parser import IndeedParser
from parsers.jobbank_wrapper import JobBankParser
from parsers.linkedin_parser import LinkedInParser
from parsers.parser_registry import ParserRegistry
from parsers.recruiter_wrapper import RecruiterParser
from parsers.supra_parser import SupraParser
from parsers.welcometothejungle_parser import WelcomeToTheJungleParser
from parsers.wellfound_parser import WellfoundParser
from parsers.workintech_wrapper import WorkInTechParser
from utils.job_validator import JobValidator
from utils.multi_scorer import get_multi_scorer
from utils.profile_manager import get_profile_manager
from utils.score_thresholds import Grade


def decode_email_subject(subject: str) -> str:
    """
    Decode MIME encoded email subject to readable text.

    Handles RFC 2047 encoded-word syntax for non-ASCII characters:
    - =?UTF-8?B?...?= (Base64 encoding)
    - =?UTF-8?Q?...?= (Quoted-printable encoding)

    Args:
        subject: Raw email subject (may contain encoded words)

    Returns:
        Decoded, human-readable subject line

    Example:
        >>> decode_email_subject("=?UTF-8?B?VGVjaOKAmXM=?=")
        "Tech's"
    """
    try:
        decoded_parts = decode_header(subject)
        return "".join(
            part.decode(encoding or "utf-8") if isinstance(part, bytes) else part
            for part, encoding in decoded_parts
        )
    except Exception:
        # If decoding fails, return original
        return subject


class JobProcessorV2:
    """Main orchestrator for job alert processing with pluggable parsers"""

    def __init__(self, profile: str | None = None):
        # Store profile for multi-profile support (defaults to 'wes' for backwards compatibility)
        self.profile = profile or "wes"

        # Initialize components
        self.parser_registry = ParserRegistry()
        self.enrichment = EnrichmentPipeline()
        self.filter = JobFilter()
        self.database = JobDatabase(profile=profile)
        self.notifier = JobNotifier()

        # Use ProfileScorer for the selected profile
        pm = get_profile_manager()
        profile_obj = pm.get_profile(self.profile)
        self.scorer = ProfileScorer(profile_obj)

        # Initialize filter pipeline with profile config
        self.filter_pipeline = JobFilterPipeline(profile_obj.scoring) if profile_obj else None

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
        self.parser_registry.register(WelcomeToTheJungleParser())
        self.parser_registry.register(WellfoundParser())
        self.parser_registry.register(IndeedParser())

        print(f"Registered parsers: {', '.join(self.parser_registry.get_enabled_parsers())}")

    def _increment_stat(self, stats: dict[str, int | list[str]], key: str, amount: int = 1) -> None:
        """Helper to increment a stat counter with type safety"""
        stats[key] = cast(int, stats[key]) + amount

    def _append_error(self, stats: dict[str, int | list[str]], error: str) -> None:
        """Helper to append error to stats with type safety"""
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        errors_list.append(error)

    def fetch_unread_emails(self, limit: int | None = None) -> list[email.message.Message]:
        """Fetch unread emails from inbox

        Args:
            limit: Maximum number of emails to fetch (None = fetch all)
        """
        return self.imap_client.fetch_unread_emails(limit)

    def process_emails(self, emails: list[email.message.Message]) -> dict[str, int | list[str]]:
        """Process emails through the full pipeline"""
        stats: dict[str, int | list[str]] = {
            "emails_processed": 0,
            "opportunities_found": 0,
            "opportunities_enriched": 0,
            "jobs_passed_filter": 0,
            "jobs_hard_filtered": 0,
            "jobs_context_filtered": 0,
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
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
            decoded_subject = decode_email_subject(subject)
            print(f"\n{'=' * 70}")
            print(f"Email: {decoded_subject}")
            print(f"{'=' * 70}")

            # Step 1: Parse email
            parse_result = self.parser_registry.parse_email(email_message)
            if not parse_result.success:
                self._handle_parse_error(parse_result.error, stats)
                return

            # Step 2: Enrich and filter
            included_opps = self._enrich_and_filter_opportunities(parse_result, stats)

            # Step 2.5: Validate job URLs
            valid_jobs = self._validate_job_urls(included_opps, stats)

            # Step 3: Process each job
            for job_dict in valid_jobs:
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

    def _validate_job_urls(self, jobs: list[dict], stats: dict[str, int | list[str]]) -> list[dict]:
        """
        Validate job URLs to filter out stale/invalid jobs before storing.

        Args:
            jobs: List of job dictionaries after keyword filtering
            stats: Statistics dictionary to update

        Returns:
            List of valid + flagged jobs (excludes invalid/stale jobs)
        """
        if not jobs:
            return []

        print("\n🔍 Validating job URLs...")
        validator = JobValidator(timeout=5, check_content=True)
        valid_jobs, flagged_jobs, invalid_jobs = validator.filter_valid_jobs(
            jobs,
            show_progress=False,  # Don't spam progress for each job
        )

        # Update statistics
        self._increment_stat(stats, "jobs_validated", len(jobs))
        self._increment_stat(stats, "jobs_valid", len(valid_jobs))
        self._increment_stat(stats, "jobs_flagged", len(flagged_jobs))
        self._increment_stat(stats, "jobs_invalid", len(invalid_jobs))

        # Log validation results
        print(f"  ✓ Valid: {len(valid_jobs)}")
        if flagged_jobs:
            print(f"  ⚠ Flagged: {len(flagged_jobs)} (included, needs review)")
            for job in flagged_jobs:
                reason = job.get("validation_reason", "unknown")
                print(
                    f"    - {job.get('company', 'Unknown')} - {job.get('title', '')[:40]}... ({reason})"
                )

        if invalid_jobs:
            print(f"  ⛔ Invalid: {len(invalid_jobs)} (filtered out)")
            for job in invalid_jobs:
                reason = job.get("validation_reason", "unknown")
                print(
                    f"    - {job.get('company', 'Unknown')} - {job.get('title', '')[:40]}... ({reason})"
                )

        # Mark flagged jobs with needs_review flag
        for job in flagged_jobs:
            job["needs_review"] = True

        # Return valid + flagged jobs (exclude invalid)
        return valid_jobs + flagged_jobs

    def _store_and_process_job(self, job_dict: dict, stats: dict[str, int | list[str]]) -> None:
        """Store a job and process it (score + notify)"""
        # Stage 1: Hard filters (before storage and scoring)
        if self.filter_pipeline:
            should_score, filter_reason = self.filter_pipeline.apply_hard_filters(job_dict)
            if not should_score:
                self._increment_stat(stats, "jobs_hard_filtered")
                print(f"\n⊘ Hard filtered: {job_dict['title']}")
                print(f"  Reason: {filter_reason}")

                # Store filtered job with filter_reason
                job_dict["filter_reason"] = filter_reason
                job_dict["filtered_at"] = datetime.now().isoformat()
                self.database.add_job(job_dict)
                return

        # Store the job
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

        # Stage 2: Score the job
        score, grade, breakdown = self._score_and_update_job(job_id, job_dict, stats)

        # Stage 3: Context filters (after scoring)
        if score is not None and grade is not None and breakdown is not None:
            if self.filter_pipeline:
                should_keep, filter_reason = self.filter_pipeline.apply_context_filters(
                    job_dict, score, breakdown
                )
                if not should_keep:
                    self._increment_stat(stats, "jobs_context_filtered")
                    print(f"  ⊘ Context filtered: {job_dict['title']}")
                    print(f"    Reason: {filter_reason}")

                    # Update job with filter_reason
                    self.database.mark_job_filtered(job_id, filter_reason)
                    return

            # Notify if qualified
            self._notify_if_qualified(job_id, job_dict, score, grade, stats)

    def _score_and_update_job(
        self, job_id: int, job_dict: dict, stats: dict[str, int | list[str]]
    ) -> tuple[int | None, str | None, dict | None]:
        """Score a job and update database for the selected profile"""
        try:
            # Score for the selected profile
            score, grade, breakdown, _classification_metadata = self.scorer.score_job(job_dict)
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

            return score, grade, breakdown

        except Exception as e:
            print(f"  ✗ Scoring failed: {e}")
            self._append_error(stats, f"Scoring failed for job {job_id}: {e}")
            return None, None, None

    def _notify_if_qualified(
        self,
        job_id: int,
        job_dict: dict,
        score: int,
        grade: str,
        stats: dict[str, int | list[str]],
    ) -> None:
        """Send notification if job meets score threshold (B+ grade)"""
        if score < Grade.B.value:
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

    def run(self, fetch_emails: bool = True, limit: int | None = None) -> dict:
        """Main entry point - run the full pipeline

        Args:
            fetch_emails: Whether to fetch emails from IMAP
            limit: Maximum number of emails to fetch (None = fetch all)
        """
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
    parser.add_argument(
        "--limit", type=int, default=None, help="Max emails to process (default: all unread)"
    )

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
