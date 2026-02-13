"""
TestDevJobs Weekly Scraper

Scrapes QA/testing jobs from TestDevJobs.com remote jobs board.
Primary beneficiary: Mario (QA/testing profile).

Usage:
    PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/testdevjobs_scraper.py
    PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/testdevjobs_scraper.py --profile mario
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from scrapers.testdevjobs_scraper import TestDevJobsScraper
from utils.multi_scorer import get_multi_scorer

load_dotenv()


class TestDevJobsWeeklyScraper:
    """Weekly scraper for TestDevJobs remote jobs"""

    def __init__(self, profile: str | None = None):
        """
        Initialize scraper

        Args:
            profile: Optional profile to score jobs for (default: all profiles)
        """
        self.profile = profile
        self.database = JobDatabase()
        self.multi_scorer = get_multi_scorer()
        self.testdev_scraper = TestDevJobsScraper()

        # Initialize Firecrawl API client
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        self.firecrawl = FirecrawlApp(api_key=api_key)

    def _retry_db_operation(self, operation, max_retries=3, initial_delay=0.1):
        """
        Retry database operations with exponential backoff
        Handles 'database is locked' errors gracefully

        Args:
            operation: Callable that performs the database operation
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 0.1)

        Returns:
            Result from the operation

        Raises:
            Exception if all retries fail
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Only retry on database lock errors
                if (
                    "database is locked" in error_msg or "locked" in error_msg
                ) and attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue

                # For other errors, raise immediately
                raise

        # All retries exhausted
        raise last_exception

    def scrape_testdevjobs(
        self,
        min_score: int = 47,
    ) -> dict:
        """
        Scrape TestDevJobs remote jobs using Firecrawl API

        Args:
            min_score: Minimum score to store/notify (default 47)

        Returns:
            Stats dictionary
        """
        print("\n" + "=" * 80)
        print("TESTDEVJOBS SCRAPER")
        print("=" * 80)
        print("URL: https://testdevjobs.com/remote-jobs")
        print(f"Min score: {min_score}")
        print("=" * 80 + "\n")

        stats = {
            "jobs_found": 0,
            "jobs_stored": 0,
            "jobs_scored": 0,
            "notifications_sent": 0,
            "profile_scores": {},
        }

        url = "https://testdevjobs.com/remote-jobs"

        print(f"📄 Fetching: {url}")
        print("   🔄 Fetching with Firecrawl API...")

        try:
            # Scrape page with Firecrawl
            document = self.firecrawl.scrape(url, formats=["markdown"])
            markdown = document.markdown if document.markdown else ""

            if not markdown:
                print("   ⚠️  No content returned from Firecrawl")
                return stats

            print(f"   ✓ Fetched {len(markdown)} characters")

            # Parse and store jobs
            stats = self.parse_page_and_store(
                markdown=markdown,
                min_score=min_score,
                stats=stats,
            )

        except Exception as e:
            print(f"   ✗ Error scraping TestDevJobs: {e}")
            return stats

        return stats

    def parse_page_and_store(
        self,
        markdown: str,
        min_score: int = 47,
        stats: dict | None = None,
    ) -> dict:
        """
        Parse a scraped TestDevJobs page and store qualifying jobs

        Args:
            markdown: Page markdown from Firecrawl
            min_score: Minimum score to store (default 47)
            stats: Stats dict to update (optional)

        Returns:
            Updated stats dictionary
        """
        if stats is None:
            stats = {
                "jobs_found": 0,
                "jobs_stored": 0,
                "jobs_scored": 0,
                "profile_scores": {},
            }

        # Parse jobs from markdown
        jobs = self.testdev_scraper.parse_jobs_from_page(markdown)

        stats["jobs_found"] = len(jobs)
        print(f"   ✓ Found {len(jobs)} jobs")

        # Store and score each job
        for job in jobs:
            # Build tech keywords string from tags
            tech_keywords = ", ".join(job.tech_tags) if job.tech_tags else ""

            job_dict = {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "link": job.link,
                "source": "testdevjobs",
                "posted_date": job.posted_date,
                "description": f"{job.remote_status} | {tech_keywords}",
                "salary": job.salary,
                "job_type": job.job_type,
            }

            # Store job (add_job handles duplicates via UNIQUE constraint on job_hash)
            try:
                job_id = self._retry_db_operation(lambda j=job_dict: self.database.add_job(j))

                # Check if job_id is None (duplicate job)
                if job_id is None:
                    print(f"   ⊙ Duplicate: {job.title} (already in database)")
                    continue

                stats["jobs_stored"] += 1
            except Exception as e:
                # Likely a duplicate (UNIQUE constraint on job_hash)
                error_msg = str(e).lower()
                if "unique" in error_msg or "duplicate" in error_msg:
                    print(f"   ⊙ Duplicate: {job.title} (already in database)")
                    continue
                else:
                    print(f"   ✗ Error storing job: {e}")
                    continue

            # Score for all profiles
            try:
                profile_scores = self._retry_db_operation(
                    lambda j=job_dict, jid=job_id: self.multi_scorer.score_job_for_all(j, jid)
                )
                stats["jobs_scored"] += 1

                # Handle empty profile_scores (all profiles filtered the job)
                if not profile_scores:
                    print(f"   ⊘ {job.title[:50]}")
                    print("     All profiles filtered this job")
                    continue

                # Track scores per profile
                for profile_id, (score, grade) in profile_scores.items():
                    if profile_id not in stats["profile_scores"]:
                        stats["profile_scores"][profile_id] = []
                    stats["profile_scores"][profile_id].append((score, grade))

                # Print scores
                scores_str = ", ".join(f"{pid}:{s}/{g}" for pid, (s, g) in profile_scores.items())
                print(f"   ✓ {job.title[:50]}")
                print(f"     Scores: {scores_str}")

                # Check if meets min score for any profile
                max_score = max(score for score, _ in profile_scores.values())
                if max_score >= min_score:
                    print(f"     🎯 QUALIFYING JOB (max score: {max_score})")

            except Exception as e:
                print(f"   ✗ Error scoring job: {e}")

        return stats

    def print_summary(self, stats: dict):
        """Print scraper summary"""
        print("\n" + "=" * 80)
        print("TESTDEVJOBS SCRAPER - SUMMARY")
        print("=" * 80)
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Jobs stored: {stats['jobs_stored']}")
        print(f"Jobs scored: {stats['jobs_scored']}")
        print()

        if stats.get("profile_scores"):
            print("Scores by profile:")
            for profile_id, scores in stats["profile_scores"].items():
                if not scores:
                    continue

                # Count by grade
                grade_counts: dict[str, int] = {}
                for _score, grade in scores:
                    grade_counts[grade] = grade_counts.get(grade, 0) + 1

                total = len(scores)
                avg_score = sum(s for s, _ in scores) / total if total > 0 else 0

                print(f"  {profile_id}:")
                print(f"    Total: {total} jobs")
                print(f"    Avg score: {avg_score:.1f}")
                print(
                    f"    Grades: {', '.join(f'{g}={c}' for g, c in sorted(grade_counts.items()))}"
                )

        print("=" * 80 + "\n")


def main():
    """Run TestDevJobs scraper"""
    parser = argparse.ArgumentParser(description="Scrape TestDevJobs remote jobs")
    parser.add_argument("--profile", type=str, help="Profile to score for (optional)")
    parser.add_argument("--min-score", type=int, default=47, help="Min score to store (default 47)")

    args = parser.parse_args()

    scraper = TestDevJobsWeeklyScraper(profile=args.profile)

    # Run scraper
    stats = scraper.scrape_testdevjobs(min_score=args.min_score)

    scraper.print_summary(stats)


if __name__ == "__main__":
    main()
