"""
Company Monitoring Scraper - Refactored Version
Scrapes monitored companies' career pages for leadership roles
Integrates with unified weekly scraper
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.job_filter_pipeline import JobFilterPipeline
from agents.profile_scorer import ProfileScorer
from api.company_service import CompanyService
from database import JobDatabase
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from scrapers.firecrawl_career_scraper import FirecrawlCareerScraper
from utils.profile_manager import get_profile_manager

# Auto-disable threshold: companies with this many consecutive failures will be auto-disabled
AUTO_DISABLE_THRESHOLD = 5


class CompanyScraper:
    """
    Scrapes monitored companies for leadership roles
    Uses Firecrawl API for JavaScript-heavy career pages
    """

    def __init__(
        self,
        profile: str | None = None,
        enable_llm_extraction: bool = False,
        enable_pagination: bool = True,
    ):
        # Store profile for multi-profile support
        self.profile = profile

        # Load profile configuration for filtering
        pm = get_profile_manager()
        profile_obj = pm.get_profile(profile) if profile else None
        profile_config = profile_obj.scoring if profile_obj else {}

        # Initialize components
        self.company_service = CompanyService()
        self.firecrawl_scraper = FirecrawlCareerScraper(
            enable_llm_extraction=enable_llm_extraction,
            enable_pagination=enable_pagination,
        )
        self.job_filter = JobFilter()
        self.filter_pipeline = JobFilterPipeline(profile_config) if profile_config else None
        self.scorer = (
            ProfileScorer(profile_obj) if profile_obj else ProfileScorer(pm.get_profile("wes"))
        )
        self.database = JobDatabase(profile=profile)
        self.notifier = JobNotifier()

        # Initialize failure logging
        self.failure_log_path = Path("logs/scraper_failures.log")
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.failure_log = open(self.failure_log_path, "a", encoding="utf-8")  # noqa: SIM115
        self.failures: list[dict[str, Any]] = []  # Track for summary

    def __del__(self):
        """Ensure failure log is closed on cleanup"""
        self._close_failure_log()

    def _log_failure(self, company_name: str, url: str, failure_count: int, reason: str) -> None:
        """
        Log scraping failure to dedicated file and memory

        Args:
            company_name: Name of company that failed
            url: Career page URL that failed
            failure_count: Current consecutive failure count
            reason: Reason for failure (e.g., "0 jobs extracted", "Exception: ...")
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "company": company_name,
            "url": url,
            "failure_count": failure_count,
            "reason": reason,
        }

        # Write to file immediately (real-time logging)
        self.failure_log.write(
            f"{timestamp} | {company_name} | {url} | "
            f"{failure_count}/{AUTO_DISABLE_THRESHOLD} | {reason}\n"
        )
        self.failure_log.flush()  # Ensure immediate write

        # Track for summary
        self.failures.append(log_entry)

    def _close_failure_log(self) -> None:
        """Close the failure log file"""
        if hasattr(self, "failure_log") and not self.failure_log.closed:
            self.failure_log.close()

    def _print_failure_summary(self) -> None:
        """Print summary of all failures that occurred during scraping"""
        if not self.failures:
            return

        print("\n" + "=" * 80)
        print(f"FAILURE SUMMARY - {len(self.failures)} companies failed")
        print("=" * 80)

        for failure in self.failures:
            status = (
                "🚫 AUTO-DISABLED"
                if failure["failure_count"] >= AUTO_DISABLE_THRESHOLD
                else f"⚠️  {failure['failure_count']}/{AUTO_DISABLE_THRESHOLD}"
            )
            print(f"\n{status} {failure['company']}")
            print(f"  URL: {failure['url']}")
            print(f"  Reason: {failure['reason']}")
            print(f"  Time: {failure['timestamp']}")

        print(f"\n📝 Full log: {self.failure_log_path}")
        print("=" * 80)

    def scrape_all_companies(
        self,
        min_score: int = 50,
        company_filter: str | None = None,
        notify_threshold: int = 80,
        skip_recent_hours: int | None = None,
    ) -> dict[str, Any]:
        """
        Scrape all monitored companies

        Args:
            min_score: Minimum score to store (default: 50 for D+ grade)
            company_filter: Filter companies by notes (e.g., "From Wes")
            notify_threshold: Score threshold for notifications (default: 80 for A grade)
            skip_recent_hours: Skip companies checked within this many hours (None = scrape all)

        Returns:
            Stats dictionary with scraping results
        """
        print("=" * 80)
        print(f"COMPANY MONITORING SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"Minimum score: {min_score}")
        print(f"Notification threshold: {notify_threshold}")
        if skip_recent_hours:
            print(f"Skip if checked within: {skip_recent_hours} hours")
        print()

        stats: dict[str, Any] = {
            "companies_checked": 0,
            "companies_skipped": 0,
            "jobs_scraped": 0,
            "leadership_jobs": 0,
            "jobs_hard_filtered": 0,
            "jobs_context_filtered": 0,
            "jobs_above_threshold": 0,
            "jobs_stored": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
            "scraping_errors": 0,
            "companies_auto_disabled": 0,
            "failed_extractions": [],  # Companies where both regex and LLM failed
        }

        # Get active companies
        all_companies = self.company_service.get_all_companies(active_only=True)

        # Filter companies if requested
        if company_filter:
            companies = [c for c in all_companies if company_filter in (c.get("notes") or "")]
            print(f"Filtered to {len(companies)} companies matching '{company_filter}'")
        else:
            companies = all_companies

        # Filter out recently checked companies if requested
        if skip_recent_hours is not None:
            from datetime import timedelta

            cutoff_time = (datetime.now() - timedelta(hours=skip_recent_hours)).isoformat()
            filtered_companies = []
            for company in companies:
                last_checked = company.get("last_checked")
                if not last_checked or last_checked < cutoff_time:
                    filtered_companies.append(company)
                else:
                    stats["companies_skipped"] += 1

            print(
                f"Skipping {stats['companies_skipped']} companies checked in last {skip_recent_hours} hours"
            )
            companies = filtered_companies

        print(f"Scraping {len(companies)} companies\n")

        # Scrape each company
        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] {company['name']}")
            print(f"  URL: {company['careers_url']}")

            stats["companies_checked"] += 1

            try:
                # Scrape jobs from career page using Firecrawl
                jobs = self.firecrawl_scraper.scrape_jobs(
                    careers_url=company["careers_url"],
                    company_name=company["name"],
                )

                stats["jobs_scraped"] += len(jobs)

                # Track companies where both regex AND LLM extraction failed
                if not jobs and self.firecrawl_scraper.enable_llm_extraction:
                    stats["failed_extractions"].append(
                        {"name": company["name"], "url": company["careers_url"]}
                    )
                    print("  ⚠ Both regex and LLM extraction returned 0 jobs - flagged for review")

                # Process and store the jobs
                if jobs:
                    job_stats = self.process_scraped_jobs(
                        company_name=company["name"],
                        jobs=jobs,
                        min_score=min_score,
                        notify_threshold=notify_threshold,
                    )

                    # Aggregate stats
                    stats["leadership_jobs"] += job_stats["leadership_jobs"]
                    stats["jobs_hard_filtered"] += job_stats["jobs_hard_filtered"]
                    stats["jobs_context_filtered"] += job_stats["jobs_context_filtered"]
                    stats["jobs_above_threshold"] += job_stats["jobs_above_threshold"]
                    stats["jobs_stored"] += job_stats["jobs_stored"]
                    stats["notifications_sent"] += job_stats["notifications_sent"]
                    stats["duplicates_skipped"] += job_stats["duplicates_skipped"]

                    # Reset failure counter on successful scrape (>0 jobs found)
                    self.company_service.reset_company_failures(company["id"])
                else:
                    # Increment failure counter and check for auto-disable
                    failure_count = self.company_service.increment_company_failures(
                        company["id"], "0 jobs extracted"
                    )
                    print(
                        f"  ⚠ No jobs extracted (failure {failure_count}/{AUTO_DISABLE_THRESHOLD})"
                    )

                    # Log failure to dedicated file
                    self._log_failure(
                        company_name=company["name"],
                        url=company["careers_url"],
                        failure_count=failure_count,
                        reason="0 jobs extracted",
                    )

                    if failure_count >= AUTO_DISABLE_THRESHOLD:
                        # Auto-disable company after 5 consecutive failures
                        self.company_service.disable_company(company["id"])
                        stats["companies_auto_disabled"] += 1
                        print(
                            f"  🚫 Auto-disabled {company['name']} after {AUTO_DISABLE_THRESHOLD} consecutive failures"
                        )

                # Update last checked timestamp
                self.company_service.update_last_checked(company["id"])

            except Exception as e:
                print(f"  ✗ Error scraping {company['name']}: {e}")
                stats["scraping_errors"] += 1

                # Log exception failure (get current failure count from database)
                current_failure_count = company.get("consecutive_failures", 0) + 1
                self._log_failure(
                    company_name=company["name"],
                    url=company["careers_url"],
                    failure_count=current_failure_count,
                    reason=f"Exception: {str(e)}",
                )

                continue

        # Print failure summary and close log
        self._print_failure_summary()
        self._close_failure_log()

        return stats

    def process_scraped_jobs(
        self,
        company_name: str,
        jobs: list[tuple[OpportunityData, str]],
        min_score: int = 50,
        notify_threshold: int = 80,
    ) -> dict[str, Any]:
        """
        Process jobs scraped from a company

        Args:
            company_name: Name of the company
            jobs: List of tuples (OpportunityData, extraction_method)
            min_score: Minimum score to store
            notify_threshold: Score threshold for notifications

        Returns:
            Stats dictionary
        """
        stats = self._init_job_stats()
        print(f"\nProcessing {len(jobs)} jobs from {company_name}")

        for job, extraction_method in jobs:
            stats["jobs_processed"] += 1

            # Filter non-leadership roles
            if not self.job_filter.is_leadership_role(job.title or ""):
                continue

            stats["leadership_jobs"] += 1

            # Prepare job dictionary
            job_dict = self._prepare_job_dict(job)

            # Scoring (filtering now happens per-profile in multi_scorer)
            score, grade, breakdown, _ = self.scorer.score_job(job_dict)

            # Context filters (after scoring, uses current profile's context)
            if self.filter_pipeline:
                should_keep, filter_reason = self.filter_pipeline.apply_context_filters(
                    job_dict, score, breakdown
                )
                if not should_keep:
                    self._handle_context_filtered_job(
                        job,
                        job_dict,
                        score,
                        grade,
                        breakdown,
                        filter_reason,
                        stats,
                    )
                    continue

            # Check minimum score threshold
            if score < min_score:
                print(f"  ⊘ Skipped (below threshold): {job.title}")
                print(f"    Score: {grade} ({score}/115) - Min: {min_score}")
                continue

            stats["jobs_above_threshold"] += 1

            # Prepare for storage
            job_dict.update(
                {
                    "source": "company_monitoring",
                    "type": "direct_job",
                    "received_at": job.received_at,
                    "fit_score": score,
                    "fit_grade": grade,
                    "score_breakdown": json.dumps(breakdown),
                    "keywords_matched": json.dumps([]),
                    "source_email": "",
                    "extraction_method": extraction_method,
                }
            )

            # Store in database
            job_id = self.database.add_job(job_dict)

            if job_id:
                # New job
                self._handle_new_job(
                    job,
                    job_dict,
                    job_id,
                    score,
                    grade,
                    breakdown,
                    extraction_method,
                    notify_threshold,
                    stats,
                )
            else:
                # Duplicate job
                self._handle_duplicate_job(job, job_dict, stats)

        return stats

    # ==================== Extracted Helper Methods ====================

    def _init_job_stats(self) -> dict[str, Any]:
        """Initialize job processing statistics dictionary"""
        return {
            "jobs_processed": 0,
            "leadership_jobs": 0,
            "jobs_hard_filtered": 0,
            "jobs_context_filtered": 0,
            "jobs_above_threshold": 0,
            "jobs_stored": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
        }

    def _prepare_job_dict(self, job: OpportunityData) -> dict[str, str]:
        """Convert OpportunityData to dictionary for processing"""
        return {
            "title": job.title or "",
            "company": job.company or "",
            "location": job.location or "",
            "link": job.link or "",
        }

    def _handle_hard_filtered_job(
        self, job: OpportunityData, job_dict: dict, filter_reason: str, stats: dict
    ) -> None:
        """Handle job that failed hard filters"""
        stats["jobs_hard_filtered"] += 1
        print(f"  ⊘ Hard filtered: {job.title}")
        print(f"    Reason: {filter_reason}")

        # Store filtered job in database
        job_dict.update(
            {
                "source": "company_monitoring",
                "type": "direct_job",
                "received_at": job.received_at,
                "filter_reason": filter_reason,
                "filtered_at": datetime.now().isoformat(),
                "keywords_matched": json.dumps([]),
                "source_email": "",
            }
        )
        self.database.add_job(job_dict)

    def _handle_context_filtered_job(
        self,
        job: OpportunityData,
        job_dict: dict,
        score: int,
        grade: str,
        breakdown: dict,
        filter_reason: str,
        stats: dict,
    ) -> None:
        """Handle job that failed context filters"""
        stats["jobs_context_filtered"] += 1
        print(f"  ⊘ Context filtered: {job.title}")
        print(f"    Reason: {filter_reason}")

        # Store with score but mark as filtered
        job_dict.update(
            {
                "source": "company_monitoring",
                "type": "direct_job",
                "received_at": job.received_at,
                "fit_score": score,
                "fit_grade": grade,
                "score_breakdown": json.dumps(breakdown),
                "filter_reason": filter_reason,
                "filtered_at": datetime.now().isoformat(),
                "keywords_matched": json.dumps([]),
                "source_email": "",
            }
        )

        job_id = self.database.add_job(job_dict)
        if job_id:
            # New filtered job - score for all profiles
            self._run_multi_profile_scoring(job_dict, job_id)
        else:
            # Duplicate filtered job - score for all profiles
            job_hash = self.database.generate_job_hash(
                job_dict["title"], job_dict["company"], job_dict["link"]
            )
            existing_job_id = self.database.get_job_id_by_hash(job_hash)
            if existing_job_id:
                self._run_multi_profile_scoring(job_dict, existing_job_id)

    def _handle_new_job(
        self,
        job: OpportunityData,
        job_dict: dict,
        job_id: int,
        score: int,
        grade: str,
        breakdown: dict,
        extraction_method: str,
        notify_threshold: int,
        stats: dict,
    ) -> None:
        """Handle storage and processing of a new job"""
        stats["jobs_stored"] += 1

        # Display job information
        self._display_new_job_info(job, score, grade, breakdown, extraction_method)

        # Multi-profile scoring (includes current profile)
        self._run_multi_profile_scoring(job_dict, job_id)

        # Send notification if above threshold
        self._send_notification_if_needed(
            job, job_dict, job_id, score, grade, notify_threshold, stats
        )

    def _display_new_job_info(
        self, job: OpportunityData, score: int, grade: str, breakdown: dict, extraction_method: str
    ) -> None:
        """Display information about a newly stored job"""
        breakdown_str = f"Seniority={breakdown.get('seniority', 0)}, Domain={breakdown.get('domain', 0)}, Role={breakdown.get('role_type', 0)}"
        method_label = "🤖 LLM" if extraction_method == "llm" else "📝 Regex"

        print(f"\n✓ New Job Stored [{method_label}]:")
        print(f"  Title: {job.title}")
        print(f"  Company: {job.company}")
        print(f"  Location: {job.location or 'N/A'}")
        print(f"  Link: {job.link}")
        print(f"  ✓ Scored: {grade} ({score}/115)")
        print(f"    Breakdown: {breakdown_str}")

    def _run_multi_profile_scoring(self, job_dict: dict, job_id: int) -> None:
        """Run multi-profile scoring for a job"""
        try:
            from utils.multi_scorer import get_multi_scorer

            multi_scorer = get_multi_scorer()
            profile_scores = multi_scorer.score_job_for_all(job_dict, job_id)
            print("  ✓ Multi-profile scores:")
            for pid, (s, g) in profile_scores.items():
                print(f"    {pid}: {s}/{g}")
        except Exception as mp_error:
            print(f"  ⚠ Multi-profile scoring failed: {mp_error}")

    def _send_notification_if_needed(
        self,
        job: OpportunityData,
        job_dict: dict,
        job_id: int,
        score: int,
        grade: str,
        notify_threshold: int,
        stats: dict,
    ) -> None:
        """Send notification if job score meets threshold"""
        if score >= notify_threshold:
            try:
                notification_job = job_dict.copy()
                notification_job["title"] = f"[{grade} {score}] {job.title}"

                notification_results = self.notifier.notify_job(notification_job)

                if notification_results.get("email") or notification_results.get("sms"):
                    stats["notifications_sent"] += 1
                    self.database.mark_notified(job_id)
                    print("  ✓ Notification sent")

            except Exception as e:
                print(f"  ✗ Notification failed: {e}")
        else:
            print(f"  ⊘ Notification skipped: Low score ({grade} {score}/115)")

    def _handle_duplicate_job(
        self,
        job: OpportunityData,
        job_dict: dict,
        stats: dict,
    ) -> None:
        """Handle processing of a duplicate job"""
        stats["duplicates_skipped"] += 1
        print(f"\n- Duplicate: {job.title} at {job.company}")

        # Get existing job ID
        job_hash = self.database.generate_job_hash(
            job_dict["title"], job_dict["company"], job_dict["link"]
        )
        existing_job_id = self.database.get_job_id_by_hash(job_hash)

        if existing_job_id:
            # Score for all profiles using multi-scorer
            try:
                from utils.multi_scorer import get_multi_scorer

                multi_scorer = get_multi_scorer()
                profile_scores = multi_scorer.score_job_for_all(job_dict, existing_job_id)
                if profile_scores:
                    print("  ✓ Multi-profile scores:")
                    for pid, (s, g) in profile_scores.items():
                        print(f"    {pid}: {s}/{g}")
            except Exception as e:
                print(f"  ⚠ Multi-profile scoring failed: {e}")


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Company monitoring scraper")
    parser.add_argument(
        "--profile",
        type=str,
        choices=["wes", "adam", "eli", "mario"],
        help="Profile to use for scoring (wes, adam, eli, mario)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum score to store (default: 50 for D+ grade)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter companies by notes (e.g., 'From Wes', 'Priority robotics')",
    )

    args = parser.parse_args()

    scraper = CompanyScraper(profile=args.profile)
    stats = scraper.scrape_all_companies(min_score=args.min_score, company_filter=args.filter)

    print("\n" + "=" * 80)
    print("COMPANY SCRAPER SUMMARY")
    print("=" * 80)
    print(f"Companies checked: {stats['companies_checked']}")
    print(f"Jobs scraped: {stats['jobs_scraped']}")
    print(f"Leadership jobs: {stats['leadership_jobs']}")
    print(f"Jobs hard filtered: {stats['jobs_hard_filtered']}")
    print(f"Jobs context filtered: {stats['jobs_context_filtered']}")
    print(f"Jobs stored: {stats['jobs_stored']}")
    print(f"Notifications sent: {stats['notifications_sent']}")
    if stats.get("companies_auto_disabled", 0) > 0:
        print(f"🚫 Companies auto-disabled: {stats['companies_auto_disabled']}")

    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
