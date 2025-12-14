"""
Company Monitoring Scraper
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
from agents.job_scorer import JobScorer
from api.company_service import CompanyService
from database import JobDatabase
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from scrapers.firecrawl_career_scraper import FirecrawlCareerScraper
from utils.profile_manager import get_profile_manager


class CompanyScraper:
    """
    Scrapes monitored companies for leadership roles
    Designed to work with Firecrawl MCP for JavaScript-heavy career pages
    """

    def __init__(self, profile: str | None = None, enable_llm_extraction: bool = False):
        # Store profile for multi-profile support
        self.profile = profile

        # Load profile configuration for filtering
        pm = get_profile_manager()
        profile_obj = pm.get_profile(profile) if profile else None
        profile_config = profile_obj.scoring if profile_obj else {}

        # Initialize components
        self.company_service = CompanyService()
        self.firecrawl_scraper = FirecrawlCareerScraper(enable_llm_extraction=enable_llm_extraction)
        self.job_filter = JobFilter()
        self.filter_pipeline = JobFilterPipeline(profile_config) if profile_config else None
        self.scorer = JobScorer()
        self.database = JobDatabase(profile=profile)
        self.notifier = JobNotifier()

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
            notify_threshold: Score threshold for notifications (default: 80 for A/B grade)
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

                # Update last checked timestamp
                self.company_service.update_last_checked(company["id"])

            except Exception as e:
                print(f"  ✗ Error scraping {company['name']}: {e}")
                stats["scraping_errors"] += 1
                continue

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
        stats: dict[str, Any] = {
            "jobs_processed": 0,
            "leadership_jobs": 0,
            "jobs_hard_filtered": 0,
            "jobs_context_filtered": 0,
            "jobs_above_threshold": 0,
            "jobs_stored": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
        }

        print(f"\nProcessing {len(jobs)} jobs from {company_name}")

        for job, extraction_method in jobs:
            stats["jobs_processed"] += 1

            # Check if leadership role
            if not self.job_filter.is_leadership_role(job.title or ""):
                continue

            stats["leadership_jobs"] += 1

            # Prepare job dictionary
            job_dict = {
                "title": job.title or "",
                "company": job.company or "",
                "location": job.location or "",
                "link": job.link or "",
            }

            # Stage 1: Hard filters (before scoring)
            if self.filter_pipeline:
                should_score, filter_reason = self.filter_pipeline.apply_hard_filters(job_dict)
                if not should_score:
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
                    continue

            # Stage 2: Scoring
            score, grade, breakdown, _classification_metadata = self.scorer.score_job(job_dict)

            # Stage 3: Context filters (after scoring)
            if self.filter_pipeline:
                should_keep, filter_reason = self.filter_pipeline.apply_context_filters(
                    job_dict, score, breakdown
                )
                if not should_keep:
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
                        self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))
                    else:
                        # Duplicate filtered job - still score for current profile
                        job_hash = self.database.generate_job_hash(
                            job_dict["title"], job_dict["company"], job_dict["link"]
                        )
                        existing_job_id = self.database.get_job_id_by_hash(job_hash)
                        if existing_job_id:
                            self.database.upsert_job_score(
                                job_id=existing_job_id,
                                profile_id=self.profile,
                                score=score,
                                grade=grade,
                                breakdown=json.dumps(breakdown),
                                classification_metadata=json.dumps(_classification_metadata)
                                if _classification_metadata
                                else None,
                            )
                    continue

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
                    "extraction_method": extraction_method,  # Store extraction method
                }
            )

            # Store in database
            job_id = self.database.add_job(job_dict)

            if job_id:
                stats["jobs_stored"] += 1

                # Update score
                self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))

                # Format breakdown for display
                breakdown_str = f"Seniority={breakdown.get('seniority', 0)}, Domain={breakdown.get('domain', 0)}, Role={breakdown.get('role_type', 0)}"

                method_label = "🤖 LLM" if extraction_method == "llm" else "📝 Regex"
                print(f"\n✓ New Job Stored [{method_label}]:")
                print(f"  Title: {job.title}")
                print(f"  Company: {job.company}")
                print(f"  Location: {job.location or 'N/A'}")
                print(f"  Link: {job.link}")
                print(f"  ✓ Scored: {grade} ({score}/115)")
                print(f"    Breakdown: {breakdown_str}")

                # Multi-profile scoring
                try:
                    from utils.multi_scorer import get_multi_scorer

                    multi_scorer = get_multi_scorer()
                    profile_scores = multi_scorer.score_job_for_all(job_dict, job_id)
                    print("  ✓ Multi-profile scores:")
                    for pid, (s, g) in profile_scores.items():
                        print(f"    {pid}: {s}/{g}")
                except Exception as mp_error:
                    print(f"  ⚠ Multi-profile scoring failed: {mp_error}")

                # Send notification if above threshold
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
            else:
                # Duplicate job - still score for current profile
                stats["duplicates_skipped"] += 1
                print(f"\n- Duplicate: {job.title} at {job.company}")

                # Get existing job ID and score for current profile
                job_hash = self.database.generate_job_hash(job.title, job.company, job.link)
                existing_job_id = self.database.get_job_id_by_hash(job_hash)

                if existing_job_id:
                    # Score this duplicate for current profile
                    self.database.upsert_job_score(
                        job_id=existing_job_id,
                        profile_id=self.profile,
                        score=score,
                        grade=grade,
                        breakdown=json.dumps(breakdown),
                        classification_metadata=json.dumps(_classification_metadata)
                        if _classification_metadata
                        else None,
                    )
                    print(f"  ✓ Scored for {self.profile}: {grade} ({score}/115)")

                    # Also try multi-profile scoring for duplicates
                    try:
                        from utils.multi_scorer import get_multi_scorer

                        multi_scorer = get_multi_scorer()
                        profile_scores = multi_scorer.score_job_for_all(job_dict, existing_job_id)
                        if profile_scores:
                            print("  ✓ Multi-profile scores:")
                            for pid, (s, g) in profile_scores.items():
                                if pid != self.profile:  # Don't repeat current profile
                                    print(f"    {pid}: {s}/{g}")
                    except Exception:
                        pass  # Multi-profile scoring is optional

        return stats


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Company monitoring scraper")
    parser.add_argument(
        "--profile",
        type=str,
        choices=["wes", "adam", "eli"],
        help="Profile to use for scoring (wes, adam, eli)",
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

    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
