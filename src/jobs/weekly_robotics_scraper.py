"""
Weekly Robotics/Deeptech Job Scraper
Run weekly to check for new high-scoring robotics jobs
Can be scheduled via cron or run manually
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.job_scorer import JobScorer
from database import JobDatabase
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier
from scrapers.robotics_deeptech_scraper import RoboticsDeeptechScraper


class WeeklyRoboticsJobChecker:
    """Weekly check for new robotics/deeptech opportunities"""

    def __init__(self, profile: str | None = None):
        self.scraper = RoboticsDeeptechScraper()
        self.scorer = JobScorer()
        self.filter = JobFilter()
        self.database = JobDatabase(profile=profile)
        self.notifier = JobNotifier()
        self.profile = profile

    def process_firecrawl_markdown(self, markdown_path: str, company: str) -> list[OpportunityData]:
        """
        Process Firecrawl markdown output and extract job listings.

        Args:
            markdown_path: Path to saved Firecrawl markdown file
            company: Company name for attribution

        Returns:
            List of OpportunityData extracted from markdown
        """
        jobs = []

        try:
            with open(markdown_path) as f:
                content = f.read()

            # Leadership keywords for filtering
            leadership_keywords = [
                "director",
                "vp",
                "vice president",
                "head of",
                "chief",
                "executive",
                "principal",
                "staff",
                "senior manager",
                "lead",
            ]

            # Pattern 1: Look for job titles in headings
            # Match patterns like "## Director of Engineering" or "### VP of Product"
            heading_pattern = r"^#+\s+(.+)$"
            headings = re.findall(heading_pattern, content, re.MULTILINE)

            # Pattern 2: URL pattern for job links
            # Match various ATS patterns
            url_pattern = r"https?://[^\s)]+(?:job|career|position)[^\s)]*"

            # Extract jobs from headings that look like job titles
            for heading in headings:
                # Check if heading looks like a job title (contains leadership keyword)
                if any(kw in heading.lower() for kw in leadership_keywords):
                    # Try to find associated URL nearby in content
                    # This is a simple heuristic - look for URLs within 500 chars after heading
                    heading_pos = content.find(heading)
                    if heading_pos != -1:
                        nearby_content = content[heading_pos : heading_pos + 500]
                        nearby_urls = re.findall(url_pattern, nearby_content, re.IGNORECASE)
                        job_url = (
                            nearby_urls[0]
                            if nearby_urls
                            else f"https://{company.lower().replace(' ', '')}.com/careers"
                        )

                        job = OpportunityData(
                            source="robotics_deeptech_sheet",
                            source_email="",
                            type="direct_job",
                            company=company,
                            title=heading.strip(),
                            location="",
                            link=job_url,
                            description=f"Discovered via Firecrawl scraping of {company} career page",
                            job_type="",
                            needs_research=False,
                            research_notes=f"Scraped from generic career page on {datetime.now().strftime('%Y-%m-%d')}",
                        )
                        jobs.append(job)

            # Pattern 3: Look for structured job listings (table format, lists, etc.)
            # This is a fallback if headings don't work well
            # Match bullet points or numbered lists that look like job titles
            list_pattern = r"^[\*\-\d\.]+\s+(.+)$"
            list_items = re.findall(list_pattern, content, re.MULTILINE)

            for item in list_items:
                if any(kw in item.lower() for kw in leadership_keywords):
                    # Skip if we already have this title from headings
                    if any(job.title.lower() == item.lower() for job in jobs):
                        continue

                    # Find associated URL
                    item_pos = content.find(item)
                    if item_pos != -1:
                        nearby_content = content[item_pos : item_pos + 500]
                        nearby_urls = re.findall(url_pattern, nearby_content, re.IGNORECASE)
                        job_url = (
                            nearby_urls[0]
                            if nearby_urls
                            else f"https://{company.lower().replace(' ', '')}.com/careers"
                        )

                        job = OpportunityData(
                            source="robotics_deeptech_sheet",
                            source_email="",
                            type="direct_job",
                            company=company,
                            title=item.strip(),
                            location="",
                            link=job_url,
                            description=f"Discovered via Firecrawl scraping of {company} career page",
                            job_type="",
                            needs_research=False,
                            research_notes=f"Scraped from generic career page on {datetime.now().strftime('%Y-%m-%d')}",
                        )
                        jobs.append(job)

            print(f"  ✓ Extracted {len(jobs)} leadership jobs from {company} markdown")
            return jobs

        except FileNotFoundError:
            print(f"  ✗ Markdown file not found: {markdown_path}")
            return []
        except Exception as e:
            print(f"  ✗ Error processing markdown for {company}: {e}")
            return []

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
            "generic_pages_found": 0,
            "firecrawl_credits_used": 0,
        }

        # Phase 1: Scrape jobs from Google Sheet
        print("PHASE 1: Scraping robotics/deeptech job board...")
        print("-" * 80)

        # Use Firecrawl fallback method to get both direct jobs and generic pages
        sheet_jobs, generic_pages = self.scraper.scrape_with_firecrawl_fallback()

        # Apply leadership filter if requested
        if leadership_only:
            leadership_keywords = self.scraper.leadership_keywords
            jobs = [
                job
                for job in sheet_jobs
                if any(kw in job.title.lower() for kw in leadership_keywords)
            ]
            print(f"  Filtered for leadership roles: {len(jobs)} of {len(sheet_jobs)} jobs")
        else:
            jobs = sheet_jobs

        stats["jobs_scraped"] = len(jobs)
        stats["generic_pages_found"] = len(generic_pages)
        print(f"  ✓ Scraped {len(jobs)} direct jobs from sheet")
        print(f"  ✓ Found {len(generic_pages)} generic career pages from priority companies\n")

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

        # Phase 2: Firecrawl Generic Career Pages
        if generic_pages:
            print("\n" + "=" * 80)
            print("PHASE 2: Scraping Generic Career Pages via Firecrawl")
            print("=" * 80)

            # Load config for budget tracking
            config = self.scraper.priority_config
            max_companies = config.get("max_companies_per_run", 10)
            weekly_budget = config.get("credit_budget_weekly", 50)
            cache_enabled = config.get("markdown_cache_enabled", True)
            cache_dir = Path(config.get("markdown_cache_dir", "data/firecrawl_cache"))

            print(f"Budget: {weekly_budget} credits/week")
            print(f"Max companies: {max_companies}")
            print(f"Markdown cache: {'Enabled' if cache_enabled else 'Disabled'}")
            print(f"Cache directory: {cache_dir}\n")

            # Limit to max companies
            companies_to_scrape = list(generic_pages.items())[:max_companies]
            estimated_credits = len(companies_to_scrape)
            stats["firecrawl_credits_used"] = estimated_credits

            # Check budget
            if estimated_credits > weekly_budget:
                print(
                    f"⚠️  WARNING: Estimated {estimated_credits} credits exceeds weekly budget of {weekly_budget}"
                )
                print(f"   Limiting to first {weekly_budget} companies to stay within budget\n")
                companies_to_scrape = companies_to_scrape[:weekly_budget]
                stats["firecrawl_credits_used"] = len(companies_to_scrape)

            print("📋 MANUAL FIRECRAWL COMMANDS (Copy & Execute in Claude Code):")
            print("=" * 80)
            print("Please execute these Firecrawl MCP commands manually:")
            print()

            for i, (company, page_info) in enumerate(companies_to_scrape, 1):
                url = page_info["url"]

                # Generate cache file path
                timestamp = datetime.now().strftime("%Y%m%d")
                cache_file = cache_dir / f"{company.lower().replace(' ', '_')}_{timestamp}.md"

                print(f"[{i}/{len(companies_to_scrape)}] {company}")
                print(f"   URL: {url}")
                print()
                print("   Command:")
                print("   ```python")
                print("   mcp__firecrawl-mcp__firecrawl_scrape(")
                print(f'       url="{url}",')
                print('       formats=["markdown"],')
                print("       onlyMainContent=True")
                print("   )")
                print("   ```")
                print()
                print(f"   Save markdown output to: {cache_file}")
                print()
                print("-" * 80)
                print()

            # Instructions for processing results
            print("\n📝 AFTER RUNNING COMMANDS:")
            print("=" * 80)
            print("1. Save each Firecrawl markdown output to the cache file shown above")
            print("2. Run the markdown processor:")
            print()
            print('   python -c "')
            print("   from src.jobs.weekly_robotics_scraper import WeeklyRoboticsJobChecker")
            print("   checker = WeeklyRoboticsJobChecker()")
            for company, _ in companies_to_scrape:
                timestamp = datetime.now().strftime("%Y%m%d")
                cache_file = cache_dir / f"{company.lower().replace(' ', '_')}_{timestamp}.md"
                print(f'   checker.process_firecrawl_markdown("{cache_file}", "{company}")')
            print('   "')
            print()
            print("3. Results will be automatically scored, stored, and notifications sent")
            print("=" * 80)

        # Summary
        print("\n" + "=" * 80)
        print("WEEKLY SCRAPER COMPLETE")
        print("=" * 80)
        print(f"Jobs scraped: {stats['jobs_scraped']}")
        print(f"Generic career pages: {stats['generic_pages_found']}")
        print(f"Passed filter: {stats['jobs_passed_filter']}")
        print(f"High-scoring (B+): {stats['jobs_above_threshold']}")
        print(f"  - A grade: {stats['jobs_a_grade']}")
        print(f"  - B grade: {stats['jobs_b_grade']}")
        print(f"New jobs stored: {stats['jobs_stored']}")
        print(f"Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"Notifications sent: {stats['notifications_sent']}")
        if stats["firecrawl_credits_used"] > 0:
            print("\nFirecrawl Usage:")
            print(f"  Credits used (estimated): {stats['firecrawl_credits_used']}")
            print(
                f"  Budget remaining: {self.scraper.priority_config.get('credit_budget_weekly', 50) - stats['firecrawl_credits_used']}"
            )

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
