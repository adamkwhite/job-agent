"""
RLS Job Board Scraper

Scrapes leadership/management jobs from the Rands Leadership Slack job board.
Uses a structured JSON API — no HTML parsing or Firecrawl needed.

Usage:
    PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/rls_scraper.py
    PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/rls_scraper.py --min-score 50
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.db_retry import print_profile_score_summary, score_single_job, store_single_job
from utils.multi_scorer import get_multi_scorer

API_URL = "https://worker-production-a172.up.railway.app/api/jobs"


class RLSJobBoardScraper(object):  # noqa: UP004 (explicit object for SonarLint S1722 compatibility)
    """Scraper for Rands Leadership Slack job board"""

    def __init__(self, profile: str | None = None) -> None:
        self.profile = profile
        self.database = JobDatabase()
        self.multi_scorer = get_multi_scorer()

    def scrape_rls_jobs(self, min_score: int = 47) -> dict[str, Any]:
        """
        Fetch and store jobs from the RLS Job Board API.

        Args:
            min_score: Minimum score to highlight as qualifying (default 47)

        Returns:
            Stats dictionary
        """
        print("\n" + "=" * 80)
        print("RLS JOB BOARD SCRAPER - RANDS LEADERSHIP SLACK")
        print("=" * 80)
        print(f"API: {API_URL}")
        print(f"Min score: {min_score}")
        print("=" * 80 + "\n")

        stats: dict[str, Any] = {
            "jobs_found": 0,
            "jobs_stored": 0,
            "jobs_scored": 0,
            "profile_scores": {},
        }

        try:
            response = requests.get(API_URL, timeout=30)
            response.raise_for_status()
            jobs = response.json()
        except requests.RequestException as e:
            print(f"✗ Failed to fetch RLS jobs: {e}")
            stats["error"] = str(e)
            return stats

        stats["jobs_found"] = len(jobs)
        print(f"✓ Fetched {len(jobs)} jobs from API\n")

        for job in jobs:
            job_dict = self._build_job_dict(job)
            job_id = store_single_job(self.database, job_dict["title"], job_dict, stats)
            if job_id is None:
                continue
            score_single_job(
                self.multi_scorer, job_dict["title"], job_dict, job_id, stats, min_score
            )

        return stats

    @staticmethod
    def _build_job_dict(job: dict[str, Any]) -> dict[str, Any]:
        """Map RLS API fields to our job schema"""
        location = job.get("location", "")
        remote_status = job.get("remote_status", "")
        if remote_status and remote_status.lower() != "onsite":
            location = f"{location} ({remote_status})" if location else remote_status

        experience = job.get("experience_level", "")
        job_function = job.get("job_function", "")
        is_mgmt = job.get("is_management", False)
        description_parts = [
            f"Experience: {experience}" if experience else "",
            f"Function: {job_function}" if job_function else "",
            "Management role" if is_mgmt else "",
            job.get("company_description", ""),
        ]
        description = " | ".join(p for p in description_parts if p)

        return {
            "title": job.get("role_title", ""),
            "company": job.get("company", ""),
            "location": location,
            "link": job.get("url", ""),
            "source": "rls_job_board",
            "posted_date": job.get("extracted_at", ""),
            "description": description,
            "salary": job.get("salary_range", ""),
            "job_type": job.get("role_type", "Full-time"),
        }

    @staticmethod
    def print_summary(stats: dict[str, Any]) -> None:
        """Print scraper summary"""
        print("\n" + "=" * 80)
        print("RLS JOB BOARD - SUMMARY")
        print("=" * 80)
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Jobs stored: {stats['jobs_stored']}")
        print(f"Jobs scored: {stats.get('jobs_scored', 0)}")
        print()
        print_profile_score_summary(stats)
        print("=" * 80 + "\n")


def main() -> None:
    """Run RLS Job Board scraper"""
    parser = argparse.ArgumentParser(description="Scrape RLS Job Board (Rands Leadership Slack)")
    parser.add_argument("--profile", type=str, help="Profile to score for (optional)")
    parser.add_argument(
        "--min-score", type=int, default=47, help="Min score to highlight (default 47)"
    )
    args = parser.parse_args()

    scraper = RLSJobBoardScraper(profile=args.profile)
    stats = scraper.scrape_rls_jobs(min_score=args.min_score)
    scraper.print_summary(stats)


if __name__ == "__main__":
    main()
