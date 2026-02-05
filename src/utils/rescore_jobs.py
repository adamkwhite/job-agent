"""
Re-score existing jobs without re-scraping

mypy: ignore-errors

Allows updating scores for jobs when:
- Profile configurations change (target seniority, keywords, etc.)
- Scoring algorithm updates
- Backfilling scores for new profiles
- Selective re-scoring by company, date range, or grade

Usage:
    python src/utils/rescore_jobs.py --mode recent --days 7 --profiles wes
    python src/utils/rescore_jobs.py --mode date-range --start-date 2024-01-01 --end-date 2024-01-31
    python src/utils/rescore_jobs.py --mode company --company Tesla
    python src/utils/rescore_jobs.py --mode backfill --profile mario --max-jobs 500
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.multi_scorer import get_multi_scorer


class JobRescorer:
    """Re-score existing jobs without re-scraping"""

    def __init__(self, db_path: str | None = None):
        """Initialize rescorer

        Args:
            db_path: Optional database path (defaults to production)
        """
        self.db = JobDatabase(db_path=db_path)
        self.multi_scorer = get_multi_scorer()

    def rescore_recent_jobs(
        self,
        days: int = 7,
        profiles: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Re-score jobs from the last N days

        Args:
            days: Number of days to look back
            profiles: List of profile IDs (None = all profiles)
            dry_run: If True, preview changes without updating database

        Returns:
            dict: Statistics about the re-scoring operation
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        return self.rescore_by_date_range(
            start_date=start_date,
            end_date=end_date,
            profiles=profiles,
            dry_run=dry_run,
        )

    def rescore_by_date_range(
        self,
        start_date: str,
        end_date: str,
        profiles: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Re-score jobs within a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            profiles: List of profile IDs (None = all profiles)
            dry_run: If True, preview changes without updating database

        Returns:
            dict: Statistics about the re-scoring operation
        """
        print(f"\n{'=' * 70}")
        print(f"RE-SCORING JOBS: {start_date} to {end_date}")
        print(f"{'=' * 70}\n")

        if dry_run:
            print("⚠️  DRY RUN MODE - No database changes will be made\n")

        # Get jobs in date range
        jobs = self._get_jobs_by_date_range(start_date, end_date)

        if not jobs:
            print("No jobs found in date range")
            return {"jobs_processed": 0, "errors": 0, "significant_changes": []}

        print(f"Found {len(jobs)} jobs in date range")

        return self._rescore_jobs(jobs, profiles, dry_run)

    def rescore_by_company(
        self,
        company_name: str,
        profiles: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Re-score all jobs from a specific company

        Args:
            company_name: Company name to filter by
            profiles: List of profile IDs (None = all profiles)
            dry_run: If True, preview changes without updating database

        Returns:
            dict: Statistics about the re-scoring operation
        """
        print(f"\n{'=' * 70}")
        print(f"RE-SCORING JOBS: Company '{company_name}'")
        print(f"{'=' * 70}\n")

        if dry_run:
            print("⚠️  DRY RUN MODE - No database changes will be made\n")

        # Get jobs for company
        jobs = self._get_jobs_by_company(company_name)

        if not jobs:
            print(f"No jobs found for company: {company_name}")
            return {"jobs_processed": 0, "errors": 0, "significant_changes": []}

        print(f"Found {len(jobs)} jobs for {company_name}")

        return self._rescore_jobs(jobs, profiles, dry_run)

    def backfill_profile(
        self,
        profile_id: str,
        max_jobs: int | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Backfill scores for a new profile

        Args:
            profile_id: Profile ID to backfill scores for
            max_jobs: Maximum number of jobs to score (None = all)
            dry_run: If True, preview changes without updating database

        Returns:
            dict: Statistics about the backfill operation
        """
        print(f"\n{'=' * 70}")
        print(f"BACKFILL SCORES: Profile '{profile_id}'")
        print(f"{'=' * 70}\n")

        if dry_run:
            print("⚠️  DRY RUN MODE - No database changes will be made\n")

        # Get jobs missing scores for this profile
        jobs = self._get_jobs_missing_profile_scores(profile_id, max_jobs)

        if not jobs:
            print(f"No jobs need backfilling for profile: {profile_id}")
            return {"jobs_processed": 0, "errors": 0, "significant_changes": []}

        print(f"Found {len(jobs)} jobs to backfill for {profile_id}")

        return self._rescore_jobs(jobs, [profile_id], dry_run)

    def _get_jobs_by_date_range(self, start_date: str, end_date: str) -> list[dict]:
        """Get jobs within date range"""
        import sqlite3

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, company, location, link, description,
                   salary, job_type, posted_date
            FROM jobs
            WHERE received_at >= ? AND received_at <= ?
            ORDER BY received_at DESC
        """,
            (start_date, end_date + " 23:59:59"),
        )

        jobs = []
        for row in cursor.fetchall():
            jobs.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "location": row[3],
                    "link": row[4],
                    "description": row[5],
                    "salary": row[6],
                    "job_type": row[7],
                    "posted_date": row[8],
                }
            )

        conn.close()
        return jobs

    def _get_jobs_by_company(self, company_name: str) -> list[dict]:
        """Get jobs for a specific company"""
        import sqlite3

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, company, location, link, description,
                   salary, job_type, posted_date
            FROM jobs
            WHERE company LIKE ?
            ORDER BY received_at DESC
        """,
            (f"%{company_name}%",),
        )

        jobs = []
        for row in cursor.fetchall():
            jobs.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "location": row[3],
                    "link": row[4],
                    "description": row[5],
                    "salary": row[6],
                    "job_type": row[7],
                    "posted_date": row[8],
                }
            )

        conn.close()
        return jobs

    def _get_jobs_missing_profile_scores(
        self, profile_id: str, max_jobs: int | None = None
    ) -> list[dict]:
        """Get jobs that don't have scores for a profile"""
        import sqlite3

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        limit_clause = f"LIMIT {max_jobs}" if max_jobs else ""

        cursor.execute(
            f"""
            SELECT j.id, j.title, j.company, j.location, j.link, j.description,
                   j.salary, j.job_type, j.posted_date
            FROM jobs j
            LEFT JOIN job_scores js ON j.id = js.job_id AND js.profile_id = ?
            WHERE js.job_id IS NULL
            ORDER BY j.received_at DESC
            {limit_clause}
        """,
            (profile_id,),
        )

        jobs = []
        for row in cursor.fetchall():
            jobs.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "company": row[2],
                    "location": row[3],
                    "link": row[4],
                    "description": row[5],
                    "salary": row[6],
                    "job_type": row[7],
                    "posted_date": row[8],
                }
            )

        conn.close()
        return jobs

    def _get_existing_scores(self, job_id: int, profile_id: str) -> dict | None:
        """Get existing score for a job-profile pair"""
        try:
            return self.db.get_job_score(job_id, profile_id)
        except Exception:
            return None

    def _rescore_jobs(
        self, jobs: list[dict], profiles: list[str] | None, dry_run: bool
    ) -> dict[str, Any]:
        """Re-score a list of jobs

        Args:
            jobs: List of job dicts
            profiles: List of profile IDs (None = all profiles)
            dry_run: If True, don't update database

        Returns:
            dict: Statistics about the operation
        """
        stats = {
            "jobs_processed": 0,
            "profiles_scored": 0,
            "errors": 0,
            "significant_changes": [],
        }

        profile_changes = defaultdict(list)

        for job in jobs:
            try:
                job_id = job["id"]

                # Get existing scores for comparison
                existing_scores = {}
                if profiles:
                    for profile_id in profiles:
                        existing = self._get_existing_scores(job_id, profile_id)
                        if existing:
                            existing_scores[profile_id] = existing["fit_score"]

                # Score job for all profiles
                if dry_run:
                    # In dry run, just show what would happen
                    print(f"  Would rescore: {job['title']} at {job['company']}")
                else:
                    profile_scores = self.multi_scorer.score_job_for_all(job, job_id)

                    if profile_scores:
                        for profile_id, (score, _grade) in profile_scores.items():
                            # Skip if not in target profiles list
                            if profiles and profile_id not in profiles:
                                continue

                            stats["profiles_scored"] += 1

                            # Track significant changes (Δ ≥ 10 points)
                            old_score = existing_scores.get(profile_id)
                            if old_score is not None:
                                delta = abs(score - old_score)
                                if delta >= 10:
                                    stats["significant_changes"].append(
                                        {
                                            "job_id": job_id,
                                            "title": job["title"],
                                            "company": job["company"],
                                            "profile": profile_id,
                                            "old_score": old_score,
                                            "new_score": score,
                                            "delta": delta,
                                        }
                                    )
                                    profile_changes[profile_id].append(
                                        (job["title"], old_score, score, delta)
                                    )

                stats["jobs_processed"] += 1

            except Exception as e:
                print(f"  ❌ Error scoring {job.get('title', 'Unknown')}: {e}")
                stats["errors"] += 1

        # Print summary
        print(f"\n{'=' * 70}")
        print("RE-SCORING SUMMARY")
        print(f"{'=' * 70}\n")
        print(f"Jobs processed: {stats['jobs_processed']}")
        print(f"Profile scores updated: {stats['profiles_scored']}")
        print(f"Errors: {stats['errors']}")
        print(f"Significant changes (Δ ≥ 10): {len(stats['significant_changes'])}")

        if stats["significant_changes"]:
            print(f"\n{'=' * 70}")
            print("TOP SCORE CHANGES")
            print(f"{'=' * 70}\n")

            # Show top 10 changes by delta
            top_changes = sorted(
                stats["significant_changes"], key=lambda x: x["delta"], reverse=True
            )[:10]

            for change in top_changes:
                delta_sign = "+" if change["new_score"] > change["old_score"] else ""
                print(f"{change['profile']}: {change['title']} at {change['company']}")
                print(
                    f"  {change['old_score']} → {change['new_score']} ({delta_sign}{change['new_score'] - change['old_score']})"
                )

        return stats


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Re-score existing jobs without re-scraping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-score last 7 days for all profiles
  python src/utils/rescore_jobs.py --mode recent --days 7

  # Re-score date range for specific profile
  python src/utils/rescore_jobs.py --mode date-range --start-date 2024-01-01 --end-date 2024-01-31 --profiles wes

  # Re-score all Tesla jobs
  python src/utils/rescore_jobs.py --mode company --company Tesla

  # Backfill scores for new profile
  python src/utils/rescore_jobs.py --mode backfill --profile mario --max-jobs 500

  # Dry run to preview changes
  python src/utils/rescore_jobs.py --mode recent --days 7 --dry-run
        """,
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=["recent", "date-range", "company", "backfill"],
        help="Re-scoring mode",
    )
    parser.add_argument("--days", type=int, help="Days to look back (for recent mode)")
    parser.add_argument("--start-date", help="Start date YYYY-MM-DD (for date-range)")
    parser.add_argument("--end-date", help="End date YYYY-MM-DD (for date-range)")
    parser.add_argument("--company", help="Company name (for company mode)")
    parser.add_argument("--profile", help="Profile ID (for backfill mode)")
    parser.add_argument(
        "--profiles",
        nargs="+",
        help="List of profile IDs to score (default: all)",
    )
    parser.add_argument("--max-jobs", type=int, help="Max jobs to process (for backfill)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.mode == "recent" and not args.days:
        parser.error("--days required for recent mode")
    if args.mode == "date-range" and (not args.start_date or not args.end_date):
        parser.error("--start-date and --end-date required for date-range mode")
    if args.mode == "company" and not args.company:
        parser.error("--company required for company mode")
    if args.mode == "backfill" and not args.profile:
        parser.error("--profile required for backfill mode")

    # Create rescorer
    rescorer = JobRescorer()

    # Execute based on mode
    if args.mode == "recent":
        stats = rescorer.rescore_recent_jobs(
            days=args.days,
            profiles=args.profiles,
            dry_run=args.dry_run,
        )
    elif args.mode == "date-range":
        stats = rescorer.rescore_by_date_range(
            start_date=args.start_date,
            end_date=args.end_date,
            profiles=args.profiles,
            dry_run=args.dry_run,
        )
    elif args.mode == "company":
        stats = rescorer.rescore_by_company(
            company_name=args.company,
            profiles=args.profiles,
            dry_run=args.dry_run,
        )
    elif args.mode == "backfill":
        stats = rescorer.backfill_profile(
            profile_id=args.profile,
            max_jobs=args.max_jobs,
            dry_run=args.dry_run,
        )

    # Exit code based on errors
    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
