"""
Hybrid Job Scraper - Discovery + Scraping Workflow

Combines Google Sheets discovery with direct company scraping:
1. Discover companies from robotics/deeptech sheet
2. Fuzzy match against existing companies (90% threshold)
3. Batch import new companies to monitoring system
4. Scrape each company's career page via Firecrawl
5. Extract, score, and store real job URLs

This solves Issue #31: Jobs not found at links (generic career page URLs)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.profile_scorer import ProfileScorer
from api.company_service import CompanyService
from database import JobDatabase
from job_filter import JobFilter
from notifier import JobNotifier
from scrapers.company_discoverer import CompanyDiscoverer
from scrapers.firecrawl_career_scraper import FirecrawlCareerScraper
from scrapers.robotics_deeptech_scraper import RoboticsDeeptechScraper
from utils.profile_manager import get_profile_manager


class HybridJobScraper:
    """
    Orchestrates hybrid job discovery and scraping workflow

    Flow:
    - Robotics Sheet → Discover Companies → Fuzzy Match → Batch Import → Scrape → Store Jobs
    """

    def __init__(
        self,
        similarity_threshold: float = 90.0,
        min_score: int = 50,
        notify_threshold: int = 80,
    ):
        """
        Initialize hybrid scraper

        Args:
            similarity_threshold: Fuzzy matching threshold (0-100, default 90)
            min_score: Minimum score to store jobs (default 50 for D+ grade)
            notify_threshold: Score threshold for notifications (default 80 for A grade)
        """
        self.similarity_threshold = similarity_threshold
        self.min_score = min_score
        self.notify_threshold = notify_threshold

        # Initialize components
        self.company_service = CompanyService()
        self.company_discoverer = CompanyDiscoverer()
        self.firecrawl_scraper = FirecrawlCareerScraper()
        self.robotics_scraper = RoboticsDeeptechScraper()
        self.job_filter = JobFilter()
        wes_profile = get_profile_manager().get_profile("wes")
        self.scorer = ProfileScorer(wes_profile)
        self.database = JobDatabase()
        self.notifier = JobNotifier()

    def run_hybrid_scrape(
        self,
        poc_companies: list[str] | None = None,
        skip_scraping: bool = False,
    ) -> dict:
        """
        Run full hybrid scraping workflow

        Args:
            poc_companies: List of company names for POC (e.g., ["Boston Dynamics", "Skydio"])
            skip_scraping: If True, only do discovery/import, skip scraping

        Returns:
            Stats dictionary with results
        """
        stats = {
            "companies_discovered": 0,
            "companies_added": 0,
            "companies_skipped": 0,
            "companies_scraped": 0,
            "jobs_found": 0,
            "leadership_jobs": 0,
            "jobs_stored": 0,
            "duplicates_skipped": 0,
            "notifications_sent": 0,
        }

        print("\n" + "=" * 80)
        print("HYBRID JOB SCRAPER - Discovery + Scraping")
        print("=" * 80)
        print(f"Similarity threshold: {self.similarity_threshold}%")
        print(f"Min score to store: {self.min_score} (D+ grade)")
        print(f"Notify threshold: {self.notify_threshold} (B grade)")
        if poc_companies:
            print(f"POC Mode: {len(poc_companies)} companies")
        print("=" * 80 + "\n")

        # Step 1: Discover companies from robotics sheet
        print("Step 1: Discovering companies from robotics sheet...")
        opportunities = self.robotics_scraper.scrape()
        discovered_companies = self.company_discoverer.discover_from_robotics_sheet(opportunities)

        stats["companies_discovered"] = len(discovered_companies)
        print(f"✓ Discovered {len(discovered_companies)} unique companies\n")

        # Filter to POC companies if specified
        if poc_companies:
            discovered_companies = self.company_discoverer.filter_by_company_names(
                discovered_companies, poc_companies
            )
            print(f"✓ Filtered to {len(discovered_companies)} POC companies\n")

        # Step 2: Batch import with fuzzy matching
        print(
            f"Step 2: Batch importing companies (fuzzy threshold: {self.similarity_threshold}%)..."
        )
        import_stats = self.company_service.add_companies_batch(
            companies=discovered_companies,
            similarity_threshold=self.similarity_threshold,
        )

        stats["companies_added"] = import_stats["added"]
        stats["companies_skipped"] = import_stats["skipped_duplicates"]

        print("\n✓ Batch import complete:")
        print(f"  Added: {import_stats['added']}")
        print(f"  Skipped (duplicates): {import_stats['skipped_duplicates']}")
        print(f"  Errors: {import_stats['errors']}\n")

        if skip_scraping:
            print("✓ Skipping scraping phase (discovery/import only)\n")
            return stats

        # Step 3: Scrape newly added companies
        if import_stats["added"] > 0:
            print(f"Step 3: Scraping {import_stats['added']} newly added companies...")

            # Get list of newly added companies from details
            newly_added = [
                detail for detail in import_stats["details"] if detail["status"] == "added"
            ]

            for i, company_detail in enumerate(newly_added, 1):
                company_name = company_detail["company"]
                careers_url = company_detail["url"]

                print(f"\n[{i}/{len(newly_added)}] Scraping {company_name}...")
                print(f"  URL: {careers_url}")

                # Scrape jobs from company
                scrape_stats = self._scrape_company(
                    company_name=company_name,
                    careers_url=careers_url,
                )

                # Update overall stats
                stats["companies_scraped"] += 1
                stats["jobs_found"] += scrape_stats["jobs_found"]
                stats["leadership_jobs"] += scrape_stats["leadership_jobs"]
                stats["jobs_stored"] += scrape_stats["jobs_stored"]
                stats["duplicates_skipped"] += scrape_stats["duplicates_skipped"]
                stats["notifications_sent"] += scrape_stats["notifications_sent"]

        # Print final summary
        print("\n" + "=" * 80)
        print("HYBRID SCRAPE COMPLETE")
        print("=" * 80)
        print(f"Companies discovered: {stats['companies_discovered']}")
        print(f"Companies added: {stats['companies_added']}")
        print(f"Companies skipped (duplicates): {stats['companies_skipped']}")
        print(f"Companies scraped: {stats['companies_scraped']}")
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Leadership jobs: {stats['leadership_jobs']}")
        print(f"Jobs stored: {stats['jobs_stored']}")
        print(f"Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"Notifications sent: {stats['notifications_sent']}")
        print("=" * 80 + "\n")

        return stats

    def _is_leadership_role(self, title: str) -> bool:
        """Check if job title is a leadership role"""
        leadership_keywords = [
            "director",
            "vp",
            "vice president",
            "head of",
            "chief",
            "manager",
            "lead",
            "principal",
            "senior manager",
        ]
        title_lower = (title or "").lower()
        return any(kw in title_lower for kw in leadership_keywords)

    def _prepare_job_for_storage(self, job, score: int, grade: str, breakdown: dict) -> dict:
        """Prepare job dictionary with metadata for storage"""
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location or "",
            "link": job.link,
            "source": "hybrid_scraper",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
            "fit_score": score,
            "fit_grade": grade,
            "score_breakdown": json.dumps(breakdown),
            "keywords_matched": json.dumps([]),
            "source_email": "",
        }
        return job_dict

    def _send_notification_if_needed(
        self, job_dict: dict, job_id: int, score: int, grade: str
    ) -> bool:
        """Send notification for high-scoring jobs. Returns True if sent successfully"""
        if score < self.notify_threshold:
            return False

        try:
            notification_job = job_dict.copy()
            notification_job["title"] = f"[{grade} {score}] {job_dict['title']}"

            notification_results = self.notifier.notify_job(notification_job)

            if notification_results.get("email") or notification_results.get("sms"):
                self.database.mark_notified(job_id)
                print("    ✓ Notification sent")
                return True
        except Exception as e:
            print(f"    ✗ Notification failed: {e}")

        return False

    def _scrape_company(self, company_name: str, careers_url: str) -> dict:
        """
        Scrape a single company's career page

        Args:
            company_name: Name of company
            careers_url: Career page URL

        Returns:
            Stats dictionary
        """
        stats = {
            "jobs_found": 0,
            "leadership_jobs": 0,
            "jobs_stored": 0,
            "duplicates_skipped": 0,
            "notifications_sent": 0,
        }

        # Scrape with Firecrawl
        jobs = self.firecrawl_scraper.scrape_jobs(careers_url, company_name)
        stats["jobs_found"] = len(jobs)

        if not jobs:
            print("  ⊘ No jobs found")
            return stats

        for job in jobs:
            # Filter for leadership roles
            if not self._is_leadership_role(job.title):
                continue

            stats["leadership_jobs"] += 1

            # Score the job
            job_dict = {
                "title": job.title,
                "company": job.company,
                "location": job.location or "",
                "link": job.link,
            }
            score, grade, breakdown, _classification_metadata = self.scorer.score_job(job_dict)

            if score < self.min_score:
                continue

            # Prepare and store job
            job_dict = self._prepare_job_for_storage(job, score, grade, breakdown)
            job_id = self.database.add_job(job_dict)

            if job_id:
                stats["jobs_stored"] += 1
                self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))

                print(f"  ✓ {job.title}")
                print(f"    Score: {grade} ({score}/115)")
                print(f"    Location: {job.location}")
                print(f"    Link: {job.link}")

                # Send notification if needed
                if self._send_notification_if_needed(job_dict, job_id, score, grade):
                    stats["notifications_sent"] += 1
            else:
                stats["duplicates_skipped"] += 1
                print(f"  - Duplicate: {job.title}")

        return stats


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Hybrid job scraper - discover companies and scrape career pages"
    )
    parser.add_argument(
        "--poc",
        action="store_true",
        help="Run POC with 5 test companies only",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=90.0,
        help="Fuzzy matching threshold (0-100, default: 90)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum score to store (default: 50 for D+ grade)",
    )
    parser.add_argument(
        "--notify-threshold",
        type=int,
        default=80,
        help="Score threshold for notifications (default: 80 for A grade)",
    )
    parser.add_argument(
        "--discovery-only",
        action="store_true",
        help="Only discover and import companies, skip scraping",
    )

    args = parser.parse_args()

    # POC companies for testing
    poc_companies = None
    if args.poc:
        poc_companies = [
            "Boston Dynamics",
            "Agility Robotics",
            "Skydio",
            "Figure AI",
            "Bright Machines",
        ]

    # Run hybrid scraper
    scraper = HybridJobScraper(
        similarity_threshold=args.similarity_threshold,
        min_score=args.min_score,
        notify_threshold=args.notify_threshold,
    )

    scraper.run_hybrid_scrape(
        poc_companies=poc_companies,
        skip_scraping=args.discovery_only,
    )

    # Exit with success
    sys.exit(0)


if __name__ == "__main__":
    main()
