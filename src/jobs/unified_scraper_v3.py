"""
Unified Job Scraper V3 - Single workflow for all sources

Flow:
1. Ingest: Collect company URLs from all sources (emails, CSV, browser extension)
2. Scrape: Get jobs from career pages using Firecrawl
3. Score: Basic scoring, then enhanced scoring for promising jobs (70+)
4. Notify: Real-time alerts for excellent jobs (80+)
5. Digest: Weekly summary of all new jobs
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.job_scorer import JobScorer
from database import JobDatabase
from extractors.email_company_extractor import EmailCompanyExtractor
from imap_client import IMAPEmailClient
from models.company import Company
from notifier import JobNotifier


class UnifiedJobScraper:
    """
    Unified scraper coordinating all job sources

    All sources flow through the same pipeline:
    - Extract company URLs
    - Scrape career pages
    - Score jobs
    - Send notifications
    - Store in database
    """

    def __init__(self):
        self.database = JobDatabase()
        self.scorer = JobScorer()
        self.notifier = JobNotifier()
        self.email_extractor = EmailCompanyExtractor()
        self.imap_client = None

    def run(
        self,
        scrape_emails: bool = True,
        scrape_csv: bool = True,
        scrape_browser_extension: bool = True,
        email_limit: int = 100,
        notify_threshold: int = 80,
        enhanced_scoring_threshold: int = 70,
    ) -> dict:
        """
        Run unified scraper across all sources

        Args:
            scrape_emails: Process emails for company URLs
            scrape_csv: Process CSV company list
            scrape_browser_extension: Process browser extension companies
            email_limit: Max emails to process
            notify_threshold: Score threshold for real-time notifications (default: 80)
            enhanced_scoring_threshold: Score to trigger full JD fetch (default: 70)

        Returns:
            Statistics dictionary
        """
        print("=" * 80)
        print("UNIFIED JOB SCRAPER V3")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(
            f"Sources: Email={scrape_emails}, CSV={scrape_csv}, Browser={scrape_browser_extension}"
        )
        print(f"Notify threshold: {notify_threshold}+")
        print(f"Enhanced scoring threshold: {enhanced_scoring_threshold}+")
        print("=" * 80 + "\n")

        stats = {
            "companies_found": 0,
            "companies_scraped": 0,
            "jobs_found": 0,
            "jobs_stored": 0,
            "jobs_enhanced_scoring": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

        # STEP 1: INGEST - Collect all career page URLs
        companies = []

        if scrape_emails:
            print("\n[STEP 1.1] Ingesting companies from emails...")
            email_companies = self._ingest_from_emails(limit=email_limit)
            companies.extend(email_companies)
            print(f"  ✓ Found {len(email_companies)} companies from emails")

        if scrape_csv:
            print("\n[STEP 1.2] Ingesting companies from CSV...")
            csv_companies = self._ingest_from_csv()
            companies.extend(csv_companies)
            print(f"  ✓ Found {len(csv_companies)} companies from CSV")

        if scrape_browser_extension:
            print("\n[STEP 1.3] Ingesting companies from browser extension...")
            browser_companies = self._ingest_from_browser_extension()
            companies.extend(browser_companies)
            print(f"  ✓ Found {len(browser_companies)} companies from browser extension")

        stats["companies_found"] = len(companies)
        print(f"\n✓ Total companies to scrape: {len(companies)}\n")

        if not companies:
            print("⚠️  No companies found to scrape")
            return stats

        # STEP 2-6: Process each company
        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] Processing {company.name}")
            print(f"  Source: {company.source_details}")
            print(f"  URL: {company.careers_url}")

            try:
                company_stats = self._process_company(
                    company,
                    notify_threshold=notify_threshold,
                    enhanced_scoring_threshold=enhanced_scoring_threshold,
                )

                # Aggregate stats
                stats["companies_scraped"] += 1
                stats["jobs_found"] += company_stats["jobs_found"]
                stats["jobs_stored"] += company_stats["jobs_stored"]
                stats["jobs_enhanced_scoring"] += company_stats["jobs_enhanced_scoring"]
                stats["notifications_sent"] += company_stats["notifications_sent"]
                stats["duplicates_skipped"] += company_stats["duplicates_skipped"]

            except Exception as e:
                print(f"  ✗ Error processing {company.name}: {e}")
                stats["errors"] += 1
                continue

        # Print final summary
        self._print_summary(stats)

        return stats

    def _ingest_from_emails(self, limit: int = 100) -> list[Company]:
        """
        Extract company URLs from job alert emails

        Instead of parsing job details from emails, we just extract:
        - Company name
        - Career page URL

        Returns:
            List of Company objects
        """
        companies = []

        try:
            # Initialize IMAP client if needed
            if not self.imap_client:
                self.imap_client = IMAPEmailClient()

            # Fetch recent emails (read or unread)
            print(f"  → Fetching last {limit} emails...")
            emails = self.imap_client.fetch_recent_emails(limit=limit)
            print(f"  ✓ Retrieved {len(emails)} emails")

            # Extract companies from each email
            for email in emails:
                try:
                    email_companies = self.email_extractor.extract_companies(email)
                    companies.extend(email_companies)
                except Exception as e:
                    print(f"  ⚠️  Error extracting from email: {e}")
                    continue

            # Deduplicate by (name, url)
            seen = set()
            unique_companies = []
            for company in companies:
                key = (company.name.lower(), company.careers_url.lower())
                if key not in seen:
                    seen.add(key)
                    unique_companies.append(company)

            return unique_companies

        except Exception as e:
            print(f"  ✗ Error fetching emails: {e}")
            return []

    def _ingest_from_csv(self) -> list[Company]:
        """
        Load companies from CSV file

        Reads job_sources.csv and extracts company entries
        """
        import csv

        companies: list[Company] = []
        csv_path = Path(__file__).parent.parent.parent / "data" / "job_sources.csv"

        if not csv_path.exists():
            print(f"  ⚠️  CSV file not found: {csv_path}")
            return companies

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle different CSV formats
                row_type = row.get("Type", "").lower()
                company_name = row.get("Company", "") or row.get("name", "")
                careers_url = row.get("Job Site", "") or row.get("careers_url", "")

                # Skip if no company name or URL
                if not company_name or not careers_url:
                    continue

                # Skip recruiters, job boards - only companies
                if row_type in ["recruiter", "job board"]:
                    continue

                companies.append(
                    Company(
                        name=company_name.strip(),
                        careers_url=careers_url.strip(),
                        source="csv",
                        source_details=f"job_sources.csv ({row_type or 'company'})",
                        notes=row.get("notes", "") or row.get("Notes", ""),
                    )
                )

        return companies

    def _ingest_from_browser_extension(self) -> list[Company]:
        """
        Get companies added via browser extension

        Queries the companies table for recently added companies
        """
        # Browser extension integration placeholder
        # Will be implemented in future PR
        return []

    def _process_company(
        self, company: Company, notify_threshold: int = 80, enhanced_scoring_threshold: int = 70
    ) -> dict:
        """
        Process a single company: scrape, score, notify, store

        Args:
            company: Company to process
            notify_threshold: Score for real-time notifications
            enhanced_scoring_threshold: Score to trigger full JD fetch

        Returns:
            Statistics for this company
        """
        stats = {
            "jobs_found": 0,
            "jobs_stored": 0,
            "jobs_enhanced_scoring": 0,
            "notifications_sent": 0,
            "duplicates_skipped": 0,
        }

        # STEP 2: SCRAPE career page
        print("  → Scraping career page...")
        jobs = self._scrape_career_page(company.careers_url, company.name)
        stats["jobs_found"] = len(jobs)

        if not jobs:
            print("  ⚠️  No jobs found")
            return stats

        print(f"  ✓ Found {len(jobs)} jobs")

        # STEP 3-6: Process each job
        for job in jobs:
            # STEP 3: Basic scoring (with title, company, location only)
            score, grade, breakdown = self._score_job_basic(job)

            # STEP 4: Enhanced scoring for promising jobs
            if score >= enhanced_scoring_threshold:
                print(f"    → Fetching full JD for {job['title']} (scored {score})")
                full_jd = self._fetch_job_description(job["link"])
                if full_jd:
                    job["description"] = full_jd
                    score, grade, breakdown = self._score_job_full(job)
                    stats["jobs_enhanced_scoring"] += 1

            # Prepare job for storage
            job_dict = {
                "title": job["title"],
                "company": job["company"],
                "location": job.get("location", ""),
                "link": job["link"],
                "description": job.get("description", ""),
                "source": company.source,
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "fit_score": score,
                "fit_grade": grade,
                "score_breakdown": json.dumps(breakdown),
                "keywords_matched": json.dumps([]),
                "source_email": "",
            }

            # STEP 5: Store in database
            job_id = self.database.add_job(job_dict)

            if job_id:
                stats["jobs_stored"] += 1
                self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))

                print(f"    ✓ {job['title']}: {grade} ({score}/115)")

                # STEP 6: Real-time notification for excellent jobs
                if score >= notify_threshold:
                    try:
                        notification_job = job_dict.copy()
                        notification_job["title"] = f"[{grade} {score}] {job['title']}"

                        notification_results = self.notifier.notify_job(notification_job)

                        if notification_results.get("email") or notification_results.get("sms"):
                            stats["notifications_sent"] += 1
                            self.database.mark_notified(job_id)
                            print("      ✓ Notification sent (SMS + Email)")

                    except Exception as e:
                        print(f"      ✗ Notification failed: {e}")
            else:
                stats["duplicates_skipped"] += 1
                print(f"    - Duplicate: {job['title']}")

        return stats

    def _extract_jobs_from_markdown(
        self, markdown: str, company_name: str, _base_url: str
    ) -> list[dict]:
        """
        Extract job listings from Firecrawl markdown content

        Looks for patterns like:
        - [Job Title](url)
        - Job Title followed by location
        - Links containing job/apply/career

        Args:
            markdown: Markdown content from Firecrawl
            company_name: Company name
            base_url: Base URL for resolving relative links

        Returns:
            List of job dictionaries with: title, company, location, link
        """
        import re

        jobs = []

        # Pattern 1: Markdown links with job-related URLs
        # Example: [Director, Product Management - Platform](https://miovision.applytojob.com/apply/ICgkCMvoO0/...)
        # Fixed ReDoS: Use specific character classes to prevent catastrophic backtracking
        # Fixed: Removed duplicate . in character class (doesn't need escaping)
        job_link_pattern = re.compile(
            r"\[([\w\s,.()&/-]+)\]\((https?://[a-zA-Z0-9./?&=%-]+(?:job|apply|career|position|opening)[a-zA-Z0-9./?&=%-]*)\)",
            re.IGNORECASE,
        )

        matches = job_link_pattern.findall(markdown)

        for title, url in matches:
            title = title.strip()

            # Skip navigation/utility links
            skip_phrases = [
                "view job",
                "apply now",
                "learn more",
                "read more",
                "view current opportunities",
                "view openings",
                "skip to",
                "home page",
                "contact",
                "apply",
                "back to",
            ]
            if any(phrase in title.lower() for phrase in skip_phrases):
                continue

            # Skip anchor links
            if (
                url.endswith("#")
                or "#" in url
                and url.split("#")[1]
                and not url.split("#")[1].startswith("job")
            ):
                continue

            # Extract location from surrounding context
            location = ""
            # Look for the line after the title in markdown
            title_pos = markdown.find(f"[{title}]")
            if title_pos != -1:
                # Get next 300 chars after the link
                context_start = markdown.find(")", title_pos) + 1
                context = markdown[context_start : context_start + 300]

                # Look for location patterns on the next line(s)
                # Pattern: Remote, Hybrid, city names, state codes
                # Simplified to reduce regex complexity
                loc_match = re.search(
                    r"^\s*-?\s*(Remote|Hybrid|On-?site|[A-Z][a-z]+,\s*[A-Z]{2,})",
                    context,
                    re.MULTILINE,
                )
                if loc_match:
                    location = loc_match.group(1).strip()

            jobs.append(
                {
                    "title": title,
                    "company": company_name,
                    "location": location or "Not specified",
                    "link": url,
                }
            )

        return jobs

    def _scrape_career_page(self, careers_url: str, _company_name: str) -> list[dict]:
        """
        Scrape jobs from career page using Firecrawl MCP

        NOTE: This method is called by the scraper but cannot directly call
        Firecrawl MCP. Claude Code must intercept and call the MCP tool.

        Returns:
            List of job dictionaries with: title, company, location, link
        """
        # This is a marker for Claude Code to intercept
        print(f"    → Calling Firecrawl MCP for: {careers_url}")

        # Placeholder - in production, Claude Code will:
        # 1. Call mcp__firecrawl-mcp__firecrawl_scrape
        # 2. Get markdown content
        # 3. Call _extract_jobs_from_markdown
        # 4. Return job list
        return []

    def _score_job_basic(self, job: dict) -> tuple[int, str, dict]:
        """
        Score job with basic information (title, company, location)

        Returns:
            (score, grade, breakdown)
        """
        return self.scorer.score_job(job)

    def _score_job_full(self, job: dict) -> tuple[int, str, dict]:
        """
        Score job with full job description

        Returns:
            (score, grade, breakdown)
        """
        return self.scorer.score_job(job)

    def _fetch_job_description(self, job_url: str) -> str | None:
        """
        Fetch full job description from individual job page

        Uses Firecrawl to scrape the job page and extract description

        Returns:
            Job description text or None if failed
        """
        print("      ℹ️  Fetching JD requires Firecrawl MCP call")
        print(f"      → URL: {job_url}")

        # Placeholder - requires Claude Code to call Firecrawl
        return None

    def _print_summary(self, stats: dict) -> None:
        """Print final summary statistics"""
        print("\n" + "=" * 80)
        print("UNIFIED SCRAPER - SUMMARY")
        print("=" * 80)
        print(f"Companies found: {stats['companies_found']}")
        print(f"Companies scraped: {stats['companies_scraped']}")
        print(f"Jobs found: {stats['jobs_found']}")
        print(f"Jobs stored: {stats['jobs_stored']}")
        print(f"Jobs with enhanced scoring: {stats['jobs_enhanced_scoring']}")
        print(f"Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"Real-time notifications: {stats['notifications_sent']}")
        print(f"Errors: {stats['errors']}")
        print("=" * 80)


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Unified job scraper - all sources")

    # Source toggles
    parser.add_argument("--email-only", action="store_true", help="Only process emails")
    parser.add_argument("--csv-only", action="store_true", help="Only process CSV")
    parser.add_argument(
        "--browser-only", action="store_true", help="Only process browser extension"
    )

    # Options
    parser.add_argument("--email-limit", type=int, default=100, help="Max emails to process")
    parser.add_argument(
        "--notify-threshold", type=int, default=80, help="Score threshold for notifications"
    )
    parser.add_argument(
        "--enhanced-threshold",
        type=int,
        default=70,
        help="Score threshold for full JD fetch",
    )

    args = parser.parse_args()

    # Determine what to run
    if args.email_only:
        run_email, run_csv, run_browser = True, False, False
    elif args.csv_only:
        run_email, run_csv, run_browser = False, True, False
    elif args.browser_only:
        run_email, run_csv, run_browser = False, False, True
    else:
        # Run all sources by default
        run_email, run_csv, run_browser = True, True, True

    scraper = UnifiedJobScraper()
    stats = scraper.run(
        scrape_emails=run_email,
        scrape_csv=run_csv,
        scrape_browser_extension=run_browser,
        email_limit=args.email_limit,
        notify_threshold=args.notify_threshold,
        enhanced_scoring_threshold=args.enhanced_threshold,
    )

    # Output JSON for logging
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
