#!/usr/bin/env python3
"""
Process robotics companies via Firecrawl scraping.
Re-scrapes 20 priority robotics companies and processes jobs.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.company_scraper import CompanyScraper
from scrapers.firecrawl_career_scraper import FirecrawlCareerScraper

# 20 priority robotics companies from weekly scraper output
ROBOTICS_COMPANIES = [
    ("Gecko Robotics", "https://www.geckorobotics.com/careers/"),
    ("Boston Dynamics", "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"),
    ("Robust AI", "https://jobs.lever.co/robust-ai"),
    ("Chef Robotics", "https://jobs.lever.co/ChefRobotics"),
    ("Skydio", "https://www.skydio.com/careers"),
    ("Sanctuary AI", "https://jobs.lever.co/sanctuary"),
    ("Agility Robotics", "https://www.agilityrobotics.com/about/careers"),
    ("Figure", "https://job-boards.greenhouse.io/figureai"),
    ("1X Technologies", "https://www.1x.tech/careers"),
    ("Skild AI", "https://job-boards.greenhouse.io/skildai-careers"),
    ("Dexterity", "https://jobs.lever.co/dexterity"),
    ("Veo", "https://jobs.lever.co/veo"),
    ("Covariant", "https://covariant.ai/careers/"),
    ("Nuro", "https://nuro.ai/careers/"),
    ("RightHand Robotics", "https://righthandrobotics.com/careers"),
    ("Nimble Robotics", "https://jobs.lever.co/NimbleAI"),
    ("Miso Robotics", "https://misorobotics.com/careers/"),
    ("Apptronik", "https://apptronik.com/careers"),
    ("Bright Machines", "https://www.brightmachines.com/careers/"),
    ("Machina Labs", "https://machinalabs.ai/careers"),
]


def scrape_robotics_companies(profile: str | None = None, min_score: int = 50) -> dict:
    """
    Scrape all robotics companies using Firecrawl.

    Args:
        profile: Profile to use for scoring (wes, adam, eli)
        min_score: Minimum score to store jobs

    Returns:
        Stats dictionary
    """
    scraper = CompanyScraper(profile=profile)
    firecrawl_scraper = FirecrawlCareerScraper()

    stats = {
        "companies_scraped": 0,
        "jobs_found": 0,
        "leadership_jobs": 0,
        "jobs_stored": 0,
        "jobs_above_threshold": 0,
        "notifications_sent": 0,
        "duplicates_skipped": 0,
        "scraping_errors": 0,
    }

    print("=== ROBOTICS COMPANIES FIRECRAWL SCRAPER ===")
    print(f"Profile: {profile or 'default'}")
    print(f"Min score: {min_score}")
    print(f"Companies: {len(ROBOTICS_COMPANIES)}\n")

    for i, (company_name, careers_url) in enumerate(ROBOTICS_COMPANIES, 1):
        print(f"\n[{i}/{len(ROBOTICS_COMPANIES)}] {company_name}")
        print(f"  URL: {careers_url}")

        stats["companies_scraped"] += 1

        try:
            # Scrape jobs from career page
            jobs = firecrawl_scraper.scrape_jobs(
                careers_url=careers_url,
                company_name=company_name,
            )

            stats["jobs_found"] += len(jobs)

            # Process and store the jobs
            if jobs:
                job_stats = scraper.process_scraped_jobs(
                    company_name=company_name,
                    jobs=jobs,
                    min_score=min_score,
                    notify_threshold=80,
                )

                stats["leadership_jobs"] += job_stats["leadership_jobs"]
                stats["jobs_above_threshold"] += job_stats["jobs_above_threshold"]
                stats["jobs_stored"] += job_stats["jobs_stored"]
                stats["notifications_sent"] += job_stats["notifications_sent"]
                stats["duplicates_skipped"] += job_stats["duplicates_skipped"]

        except Exception as e:
            print(f"  ✗ Error scraping {company_name}: {e}")
            stats["scraping_errors"] += 1
            continue

    return stats


def main():
    """Main processing function."""
    parser = argparse.ArgumentParser(description="Scrape robotics companies via Firecrawl")
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
        help="Minimum score to store jobs (default: 50 for D+ grade)",
    )

    args = parser.parse_args()

    # Run the scraping
    stats = scrape_robotics_companies(profile=args.profile, min_score=args.min_score)

    # Print summary
    print(f"\n{'=' * 80}")
    print("ROBOTICS FIRECRAWL SCRAPER SUMMARY")
    print(f"{'=' * 80}")
    print(f"Companies scraped: {stats['companies_scraped']}")
    print(f"Jobs found: {stats['jobs_found']}")
    print(f"Leadership jobs: {stats['leadership_jobs']}")
    print(f"Jobs above threshold: {stats['jobs_above_threshold']}")
    print(f"Jobs stored: {stats['jobs_stored']}")
    print(f"Notifications sent: {stats['notifications_sent']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"Scraping errors: {stats['scraping_errors']}")
    print(f"{'=' * 80}\n")

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
