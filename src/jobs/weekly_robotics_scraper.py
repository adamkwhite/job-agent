"""
Weekly Robotics/Deeptech Job Scraper
Run weekly to check for new high-scoring robotics jobs
Can be scheduled via cron or run manually
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.job_scorer import JobScorer
from database import JobDatabase
from job_filter import JobFilter
from notifier import JobNotifier
from scrapers.robotics_deeptech_scraper import RoboticsDeeptechScraper


class WeeklyRoboticsJobChecker:
    """Weekly check for new robotics/deeptech opportunities"""

    def __init__(self):
        self.scraper = RoboticsDeeptechScraper()
        self.scorer = JobScorer()
        self.filter = JobFilter()
        self.database = JobDatabase()
        self.notifier = JobNotifier()

    def run(self, min_score: int = 70, leadership_only: bool = True) -> dict:
        """
        Run weekly scraper job

        Args:
            min_score: Minimum score to store/notify (default: 70 for B+ grade)
            leadership_only: Only scrape leadership roles (default: True)

        Returns:
            Stats dictionary
        """
        print("=" * 80)
        print(f"WEEKLY ROBOTICS JOB SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"Minimum score: {min_score}")
        print(f"Leadership only: {leadership_only}\n")

        stats = {
            "jobs_scraped": 0,
            "jobs_passed_filter": 0,
            "jobs_above_threshold": 0,
            "jobs_stored": 0,
            "jobs_a_grade": 0,
            "jobs_b_grade": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
        }

        # Step 1: Scrape jobs
        print("Step 1: Scraping robotics/deeptech job board...")
        jobs = self.scraper.get_leadership_jobs_only() if leadership_only else self.scraper.scrape()

        stats["jobs_scraped"] = len(jobs)
        print(f"  ✓ Scraped {len(jobs)} jobs\n")

        # Step 2: Convert to dicts and filter
        print("Step 2: Filtering for PM/Engineering roles...")
        jobs_as_dicts = []
        for job in jobs:
            jobs_as_dicts.append(
                {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location or "",
                    "link": job.link,
                    "description": job.description or "",
                    "salary": job.salary or "",
                    "job_type": job.job_type or "",
                    "source": "robotics_deeptech_sheet",
                    "source_email": "",
                    "received_at": job.received_at,
                    "keywords_matched": [],
                }
            )

        included, excluded = self.filter.filter_jobs(jobs_as_dicts)
        stats["jobs_passed_filter"] = len(included)
        print(f"  ✓ Passed filter: {len(included)}")
        print(f"  ✗ Excluded: {len(excluded)}\n")

        # Step 3: Score and filter by threshold
        print(f"Step 3: Scoring jobs (threshold: {min_score}+)...")
        high_scoring_jobs = []

        for job_dict in included:
            score, grade, breakdown = self.scorer.score_job(job_dict)

            if score >= min_score:
                stats["jobs_above_threshold"] += 1

                if grade == "A":
                    stats["jobs_a_grade"] += 1
                elif grade == "B":
                    stats["jobs_b_grade"] += 1

                job_dict["fit_score"] = score
                job_dict["fit_grade"] = grade
                job_dict["score_breakdown"] = json.dumps(breakdown)

                high_scoring_jobs.append(job_dict)

        print(f"  ✓ High-scoring jobs: {len(high_scoring_jobs)}")
        print(f"    - A grade: {stats['jobs_a_grade']}")
        print(f"    - B grade: {stats['jobs_b_grade']}\n")

        # Step 4: Store and notify
        print("Step 4: Storing and notifying...")

        for job_dict in high_scoring_jobs:
            # Store in database
            job_id = self.database.add_job(job_dict)

            if job_id:
                stats["jobs_stored"] += 1

                # Update score in database
                self.database.update_job_score(
                    job_id,
                    job_dict["fit_score"],
                    job_dict["fit_grade"],
                    job_dict["score_breakdown"],
                )

                print(f"\n  ✓ New Job: {job_dict['title']}")
                print(f"    Company: {job_dict['company']}")
                print(f"    Score: {job_dict['fit_grade']} ({job_dict['fit_score']}/100)")

                # Send notification for A/B grade jobs
                try:
                    # Add score to notification
                    notification_job = job_dict.copy()
                    notification_job["title"] = (
                        f"[{job_dict['fit_grade']} {job_dict['fit_score']}] {job_dict['title']}"
                    )

                    notification_results = self.notifier.notify_job(notification_job)

                    if notification_results.get("email") or notification_results.get("sms"):
                        stats["notifications_sent"] += 1
                        self.database.mark_notified(job_id)
                        print(
                            f"    ✓ Notified: SMS={notification_results.get('sms')}, Email={notification_results.get('email')}"
                        )

                except Exception as e:
                    print(f"    ✗ Notification failed: {e}")
            else:
                stats["duplicates_skipped"] += 1
                print(f"\n  - Duplicate: {job_dict['title']} at {job_dict['company']}")

        # Summary
        print("\n" + "=" * 80)
        print("WEEKLY SCRAPER COMPLETE")
        print("=" * 80)
        print(f"Jobs scraped: {stats['jobs_scraped']}")
        print(f"Passed filter: {stats['jobs_passed_filter']}")
        print(f"High-scoring (B+): {stats['jobs_above_threshold']}")
        print(f"  - A grade: {stats['jobs_a_grade']}")
        print(f"  - B grade: {stats['jobs_b_grade']}")
        print(f"New jobs stored: {stats['jobs_stored']}")
        print(f"Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"Notifications sent: {stats['notifications_sent']}")

        return stats


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Weekly robotics/deeptech job scraper")
    parser.add_argument(
        "--min-score", type=int, default=70, help="Minimum score to store/notify (default: 70)"
    )
    parser.add_argument(
        "--all-roles", action="store_true", help="Include IC roles (default: leadership only)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without storing/notifying")

    args = parser.parse_args()

    checker = WeeklyRoboticsJobChecker()

    if args.dry_run:
        print("DRY RUN MODE - No storage or notifications\n")
        # TODO: Implement dry run logic

    stats = checker.run(min_score=args.min_score, leadership_only=not args.all_roles)

    # Output JSON for logging/monitoring
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
