#!/usr/bin/env python3
"""
Process cached Firecrawl markdown files to extract and score jobs.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import JobDatabase
from jobs.weekly_robotics_scraper import WeeklyRoboticsJobChecker
from utils.multi_scorer import get_multi_scorer


def main():
    """Process all cached Firecrawl markdown files."""
    checker = WeeklyRoboticsJobChecker()
    scorer = get_multi_scorer()
    db = JobDatabase()

    # Define companies and their cache files
    companies = [
        ("Gecko Robotics", "gecko_robotics_20251130.md"),
        ("Boston Dynamics", "boston_dynamics_20251130.md"),
        ("Robust AI", "robust_ai_20251130.md"),
        ("Chef Robotics", "chef_robotics_20251130.md"),
        ("Skydio", "skydio_20251130.md"),
        ("Sanctuary AI", "sanctuary_ai_20251130.md"),
        ("Agility Robotics", "agility_robotics_20251130.md"),
        ("Figure", "figure_20251130.md"),
        ("1X Technologies", "1x_technologies_20251130.md"),
        ("Skild AI", "skild_ai_20251130.md"),
        ("Dexterity", "dexterity_20251130.md"),
        ("Veo", "veo_20251130.md"),
        ("Covariant", "covariant_20251130.md"),
        ("Nuro", "nuro_20251130.md"),
        ("RightHand Robotics", "righthand_robotics_20251130.md"),
        ("Nimble Robotics", "nimble_robotics_20251130.md"),
        ("Miso Robotics", "miso_robotics_20251130.md"),
        ("Apptronik", "apptronik_20251130.md"),
        ("Bright Machines", "bright_machines_20251130.md"),
        ("Machina Labs", "machina_labs_20251130.md"),
        # New companies (Google, AV, Anthropic)
        ("Wing", "wing_20251130.md"),
        ("Intrinsic", "intrinsic_20251130.md"),
        ("Aptiv", "aptiv_20251130.md"),
        ("Mobileye", "mobileye_20251130.md"),
        ("Gatik", "gatik_20251130.md"),
        ("May Mobility", "may_mobility_20251130.md"),
        ("Anthropic", "anthropic_20251130.md"),
    ]

    cache_dir = Path("data/firecrawl_cache")
    total_jobs_found = 0
    total_jobs_stored = 0
    total_high_scoring = 0
    min_score = 50  # Store D+ grade and above

    print(f"\nProcessing {len(companies)} cached Firecrawl markdown files...")
    print(f"Min score for storage: {min_score} (D+ grade)")
    print("=" * 80)

    for company_name, cache_file in companies:
        filepath = cache_dir / cache_file

        if not filepath.exists():
            print(f"\n❌ {company_name}: Cache file not found - {filepath}")
            continue

        print(f"\n📄 {company_name}")
        print(f"   File: {cache_file}")

        try:
            # Extract jobs from markdown
            jobs = checker.process_firecrawl_markdown(str(filepath), company_name)
            total_jobs_found += len(jobs)

            if not jobs:
                print("   No leadership jobs found")
                continue

            # Score and store each job
            stored_count = 0
            high_score_count = 0

            for job in jobs:
                # Convert OpportunityData to dict
                job_dict = {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "link": job.link,
                    "description": job.description,
                    "source": job.source,
                    "source_email": job.source_email,
                    "job_type": job.job_type,
                    "keywords_matched": [],
                }

                # Add job to database (returns None if duplicate)
                job_id = db.add_job(job_dict)

                if job_id is None:
                    # Job already exists (duplicate)
                    continue

                # Score job for all profiles
                score_results = scorer.score_new_job(job_dict, job_id)

                # Get max score across all profiles
                max_score = max(score for score, grade in score_results.values())

                # Count if meets minimum score
                if max_score >= min_score:
                    stored_count += 1

                    if max_score >= 80:  # B+ grade
                        high_score_count += 1
                        print(f"   ⭐ {job.title} - Score: {max_score} (A/B grade)")

            total_jobs_stored += stored_count
            total_high_scoring += high_score_count

            print(f"   Jobs extracted: {len(jobs)}")
            print(f"   Jobs stored (≥{min_score}): {stored_count}")
            print(f"   High-scoring (≥80): {high_score_count}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Companies processed: {len(companies)}")
    print(f"  Total jobs extracted: {total_jobs_found}")
    print(f"  Total jobs stored (≥{min_score}): {total_jobs_stored}")
    print(f"  High-scoring jobs (≥80): {total_high_scoring}")
    print("=" * 80)


if __name__ == "__main__":
    main()
