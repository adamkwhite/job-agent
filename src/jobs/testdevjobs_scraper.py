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
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from scrapers.testdevjobs_scraper import TestDevJob, TestDevJobsScraper
from utils.multi_scorer import get_multi_scorer

load_dotenv()

_T = TypeVar("_T")


class TestDevJobsWeeklyScraper(object):  # noqa: UP004 (explicit object for SonarLint S1722 compatibility)
    """Weekly scraper for TestDevJobs remote jobs"""

    def __init__(self, profile: str | None = None) -> None:
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

    @staticmethod
    def _retry_db_operation(
        operation: Callable[[], _T], max_retries: int = 3, initial_delay: float = 0.1
    ) -> _T:
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
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exc = e
                error_msg = str(e).lower()

                # Only retry on database lock errors
                if (
                    "database is locked" in error_msg or "locked" in error_msg
                ) and attempt < max_retries - 1:
                    time.sleep(delay)
                    # Exponential backoff
                    delay *= 2
                    continue

                # For other errors, raise immediately
                raise

        # All retries exhausted
        assert last_exc is not None
        raise last_exc

    def scrape_testdevjobs(
        self,
        min_score: int = 47,
        locations: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Scrape TestDevJobs remote jobs using Firecrawl API

        Args:
            min_score: Minimum score to store/notify (default 47)
            locations: List of locations to scrape (default: Canada, US, Europe, Worldwide)

        Returns:
            Stats dictionary
        """
        # Default to key locations for broad coverage
        if locations is None:
            locations = [
                "remote-canada",
                "remote-united-states",
                "remote-europe",
                "remote-worldwide",
            ]

        print("\n" + "=" * 80)
        print("TESTDEVJOBS SCRAPER - MULTI-LOCATION")
        print("=" * 80)
        print(f"Locations: {', '.join(locations)}")
        print(f"Min score: {min_score}")
        print("=" * 80 + "\n")

        stats = {
            "pages_scraped": 0,
            "jobs_found": 0,
            "jobs_stored": 0,
            "jobs_scored": 0,
            "notifications_sent": 0,
            "profile_scores": {},
        }

        # Scrape each location
        for i, location in enumerate(locations, 1):
            url = f"https://testdevjobs.com/location/{location}/"

            print(f"\n📄 Location {i}/{len(locations)}: {location}")
            print(f"   🔄 Fetching: {url}")

            try:
                # Scrape page with Firecrawl
                document = self.firecrawl.scrape(url, formats=["markdown"])
                markdown = document.markdown if document.markdown else ""

                if not markdown:
                    print("   ⚠️  No content returned from Firecrawl")
                    continue

                print(f"   ✓ Fetched {len(markdown)} characters")
                stats["pages_scraped"] += 1  # type: ignore[operator]

                # Parse and store jobs from this location
                stats = self.parse_page_and_store(
                    markdown=markdown,
                    min_score=min_score,
                    stats=stats,
                )

            except Exception as e:
                print(f"   ✗ Error scraping {location}: {e}")
                continue

        return stats

    @staticmethod
    def _build_job_dict(job: TestDevJob) -> dict[str, Any]:
        """Build a job dictionary from a TestDevJob object"""
        tech_keywords = ", ".join(job.tech_tags) if job.tech_tags else ""
        return {
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

    def _store_single_job(
        self, job_title: str, job_dict: dict[str, Any], stats: dict[str, Any]
    ) -> int | None:
        """
        Store a single job in the database.

        Returns job_id if stored successfully, None if duplicate or error.
        Updates stats["jobs_stored"] on success.
        """
        try:
            job_id = self._retry_db_operation(lambda: self.database.add_job(job_dict))
            if job_id is None:
                print(f"   ⊙ Duplicate: {job_title} (already in database)")
                return None
            stats["jobs_stored"] += 1
            return job_id
        except Exception as e:
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                print(f"   ⊙ Duplicate: {job_title} (already in database)")
            else:
                print(f"   ✗ Error storing job: {e}")
            return None

    def _score_single_job(
        self,
        job_title: str,
        job_dict: dict[str, Any],
        job_id: int,
        stats: dict[str, Any],
        min_score: int,
    ) -> None:
        """
        Score a single job for all profiles.

        Updates stats["jobs_scored"] and stats["profile_scores"] on success.
        """
        try:
            profile_scores = self._retry_db_operation(
                lambda: self.multi_scorer.score_job_for_all(job_dict, job_id)
            )
            stats["jobs_scored"] += 1

            if not profile_scores:
                print(f"   ⊘ {job_title[:50]}")
                print("     All profiles filtered this job")
                return

            for profile_id, (score, grade) in profile_scores.items():
                if profile_id not in stats["profile_scores"]:
                    stats["profile_scores"][profile_id] = []
                stats["profile_scores"][profile_id].append((score, grade))

            scores_str = ", ".join(f"{pid}:{s}/{g}" for pid, (s, g) in profile_scores.items())
            print(f"   ✓ {job_title[:50]}")
            print(f"     Scores: {scores_str}")

            max_score = max(score for score, _ in profile_scores.values())
            if max_score >= min_score:
                print(f"     🎯 QUALIFYING JOB (max score: {max_score})")

        except Exception as e:
            print(f"   ✗ Error scoring job: {e}")

    def parse_page_and_store(
        self,
        markdown: str,
        min_score: int = 47,
        stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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

        jobs = self.testdev_scraper.parse_jobs_from_page(markdown)
        page_jobs_count = len(jobs)
        stats["jobs_found"] += page_jobs_count  # type: ignore[operator]
        print(f"   ✓ Found {page_jobs_count} jobs")

        for job in jobs:
            job_dict = self._build_job_dict(job)
            job_id = self._store_single_job(job.title, job_dict, stats)
            if job_id is None:
                continue
            self._score_single_job(job.title, job_dict, job_id, stats, min_score)

        return stats

    @staticmethod
    def print_summary(stats: dict[str, Any]) -> None:
        """Print scraper summary"""
        print("\n" + "=" * 80)
        print("TESTDEVJOBS SCRAPER - SUMMARY")
        print("=" * 80)
        print(f"Pages scraped: {stats.get('pages_scraped', 0)}")
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


def main() -> None:
    """Run TestDevJobs scraper"""
    parser = argparse.ArgumentParser(description="Scrape TestDevJobs remote jobs")
    parser.add_argument("--profile", type=str, help="Profile to score for (optional)")
    parser.add_argument("--min-score", type=int, default=47, help="Min score to store (default 47)")
    parser.add_argument(
        "--locations",
        type=str,
        nargs="+",
        help="Locations to scrape (default: Canada, US, Europe, Worldwide)",
    )

    args = parser.parse_args()

    scraper = TestDevJobsWeeklyScraper(profile=args.profile)

    # Run scraper
    stats = scraper.scrape_testdevjobs(min_score=args.min_score, locations=args.locations)

    scraper.print_summary(stats)


if __name__ == "__main__":
    main()
