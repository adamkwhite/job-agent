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
from utils.db_retry import retry_db_operation
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
            job_id = self._store_single_job(job_dict["title"], job_dict, stats)
            if job_id is None:
                continue
            self._score_single_job(job_dict["title"], job_dict, job_id, stats, min_score)

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

    def _store_single_job(
        self, job_title: str, job_dict: dict[str, Any], stats: dict[str, Any]
    ) -> int | None:
        """Store a single job. Returns job_id or None if duplicate."""
        try:
            job_id: int | None = retry_db_operation(lambda: self.database.add_job(job_dict))
            if job_id is None:
                print(f"   ⊙ Duplicate: {job_title[:60]}")
                return None
            stats["jobs_stored"] += 1
            return job_id
        except Exception as e:
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                print(f"   ⊙ Duplicate: {job_title[:60]}")
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
        """Score a single job for all profiles."""
        try:
            profile_scores: dict[str, tuple[int, str]] = retry_db_operation(
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

        if stats.get("profile_scores"):
            print("Scores by profile:")
            for profile_id, scores in stats["profile_scores"].items():
                if not scores:
                    continue
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
