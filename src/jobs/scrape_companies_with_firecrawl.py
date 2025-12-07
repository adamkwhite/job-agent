"""
Weekly Company Scraper with Firecrawl Integration
This script coordinates company scraping by:
1. Getting list of companies to scrape
2. For each company, Claude Code calls Firecrawl MCP tool
3. Processing and storing results

This script is meant to be run BY Claude Code, not standalone.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.job_scorer import JobScorer
from api.company_service import CompanyService
from database import JobDatabase
from extractors.llm_extractor import LLMExtractor
from job_filter import JobFilter
from models import OpportunityData
from notifier import JobNotifier

logger = logging.getLogger(__name__)


class CompanyScraperWithFirecrawl:
    """
    Coordinates company scraping workflow with Firecrawl MCP

    Usage:
        1. Run this script to get list of companies
        2. Script outputs company URLs for Firecrawl scraping
        3. Claude Code calls mcp__firecrawl-mcp__firecrawl_scrape for each
        4. Script processes results and stores in database
    """

    def __init__(self, enable_llm_extraction: bool = False):
        self.company_service = CompanyService()
        self.job_filter = JobFilter()
        self.scorer = JobScorer()
        self.database = JobDatabase()
        self.notifier = JobNotifier()
        self.enable_llm_extraction = enable_llm_extraction
        self.llm_extractor = None

        if enable_llm_extraction:
            try:
                self.llm_extractor = LLMExtractor()
                logger.info("LLM extraction enabled")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize LLM extractor: {e}. Continuing with regex only."
                )
                self.enable_llm_extraction = False

    def get_companies_to_scrape(self, company_filter: str | None = None) -> list[dict]:
        """Get list of companies that need scraping"""
        all_companies = self.company_service.get_all_companies(active_only=True)

        # Filter companies if requested
        if company_filter:
            companies = [c for c in all_companies if company_filter in (c.get("notes") or "")]
        else:
            companies = all_companies

        return companies

    def process_company_markdown(
        self,
        company_name: str,
        markdown_content: str,
        min_score: int = 50,
        notify_threshold: int = 80,
    ) -> dict:
        """
        Process markdown content from Firecrawl for a company

        Args:
            company_name: Name of the company
            careers_url: Career page URL
            markdown_content: Markdown scraped by Firecrawl
            min_score: Minimum score to store
            notify_threshold: Score threshold for notifications

        Returns:
            Stats dictionary
        """
        stats = {
            "jobs_found": 0,
            "leadership_jobs": 0,
            "jobs_above_threshold": 0,
            "jobs_stored": 0,
            "duplicates_skipped": 0,
            "notifications_sent": 0,
        }

        print(f"\nProcessing {company_name}")

        # Extract jobs using regex (primary method)
        regex_jobs = self._extract_jobs_from_markdown(markdown_content, company_name)
        stats["jobs_found"] = len(regex_jobs)
        print(f"  Regex extraction: {len(regex_jobs)} jobs found")

        # Store regex results for processing
        jobs_to_process = [(job, "regex") for job in regex_jobs]

        # Run LLM extraction if enabled and budget available
        if self.enable_llm_extraction and self.llm_extractor:
            if self.llm_extractor.budget_available():
                try:
                    logger.info(f"Running LLM extraction for {company_name}")
                    llm_jobs = self.llm_extractor.extract_jobs(markdown_content, company_name)
                    print(f"  LLM extraction: {len(llm_jobs)} jobs found")

                    # Add LLM results for separate storage
                    jobs_to_process.extend([(job, "llm") for job in llm_jobs])
                except Exception as e:
                    logger.error(f"LLM extraction failed for {company_name}: {e}")
                    print(f"  ✗ LLM extraction failed: {e}")
            else:
                logger.warning(f"LLM budget exceeded, skipping LLM extraction for {company_name}")
                print("  ⚠ LLM budget exceeded, using regex only")

        if not jobs_to_process:
            return stats

        # Process each job
        # Leadership keywords to filter for
        leadership_keywords = [
            "director",
            "vp",
            "vice president",
            "head of",
            "chief",
            "manager",
            "lead",
            "principal",
            "senior manager",
        ]

        for job, extraction_method in jobs_to_process:
            # Check if leadership role
            title_lower = (job.title or "").lower()
            if not any(kw in title_lower for kw in leadership_keywords):
                continue

            stats["leadership_jobs"] += 1

            # Score the job
            job_dict = {
                "title": job.title,
                "company": job.company,
                "location": job.location or "",
                "link": job.link,
            }

            score, grade, breakdown = self.scorer.score_job(job_dict)

            if score < min_score:
                continue

            stats["jobs_above_threshold"] += 1

            # Prepare for storage with extraction method
            job_dict.update(
                {
                    "source": "company_monitoring",
                    "type": "direct_job",
                    "received_at": datetime.now().isoformat(),
                    "fit_score": score,
                    "fit_grade": grade,
                    "score_breakdown": json.dumps(breakdown),
                    "keywords_matched": json.dumps([]),
                    "source_email": "",
                    "extraction_method": extraction_method,  # Store how job was extracted
                }
            )

            # Store in database
            job_id = self.database.add_job(job_dict)

            if job_id:
                stats["jobs_stored"] += 1
                self.database.update_job_score(job_id, score, grade, json.dumps(breakdown))

                method_label = "🤖 LLM" if extraction_method == "llm" else "📝 Regex"
                print(f"  ✓ [{method_label}] {job.title}")
                print(f"    Score: {grade} ({score}/115)")
                print(f"    Location: {job.location}")

                # Send notification if above threshold
                if score >= notify_threshold:
                    try:
                        notification_job = job_dict.copy()
                        notification_job["title"] = f"[{grade} {score}] {job.title}"

                        notification_results = self.notifier.notify_job(notification_job)

                        if notification_results.get("email") or notification_results.get("sms"):
                            stats["notifications_sent"] += 1
                            self.database.mark_notified(job_id)
                            print("    ✓ Notification sent")

                    except Exception as e:
                        print(f"    ✗ Notification failed: {e}")
            else:
                stats["duplicates_skipped"] += 1
                print(f"  - Duplicate: {job.title}")

        return stats

    def _extract_jobs_from_markdown(
        self, markdown: str, company_name: str
    ) -> list[OpportunityData]:
        """
        Extract job listings from markdown content

        Args:
            markdown: Markdown content from Firecrawl
            company_name: Company name

        Returns:
            List of OpportunityData objects
        """
        import re

        jobs = []

        # Pattern 1: Job title as header, followed by location, then link
        # Example:
        # ## Vision Engineer
        # Cambridge, ON, Canada
        # [View Job](https://url)
        # Use {1,3} instead of + to prevent ReDoS
        pattern1 = re.compile(
            r"##\s+([^\n]+)\n{1,3}([^\n]+)\n{1,3}\[(?:View Job|Apply|Learn More)\]\(([^\)]+)\)",
            re.MULTILINE,
        )

        matches = pattern1.findall(markdown)
        for title, location, link in matches:
            title = title.strip()
            location = location.strip()

            # Filter out common non-job titles
            if self._is_likely_job_title(title):
                jobs.append(
                    OpportunityData(
                        type="direct_job",
                        title=title,
                        company=company_name,
                        location=location,
                        link=link,
                        source="company_monitoring",
                        received_at=datetime.now().isoformat(),
                    )
                )

        # Pattern 2: Markdown links with job titles (fallback)
        # Example: [Senior Engineer](https://careers.company.com/job/123)
        if not jobs:
            pattern2 = re.compile(r"\[([\w\s,\-\(\)/&]+?)\]\((https?://[^\)]+)\)", re.MULTILINE)

            matches = pattern2.findall(markdown)
            for title, link in matches:
                title = title.strip()

                # Filter out common non-job links
                if self._is_likely_job_title(title):
                    # Try to find location near this job
                    title_idx = markdown.find(f"[{title}]")
                    if title_idx != -1:
                        # Look backwards for location
                        context_before = markdown[max(0, title_idx - 200) : title_idx]
                        location_match = re.search(
                            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2,}(?:,\s*\w+)?)",
                            context_before,
                        )
                        location = location_match.group(1) if location_match else ""
                    else:
                        location = ""

                    jobs.append(
                        OpportunityData(
                            type="direct_job",
                            title=title,
                            company=company_name,
                            location=location,
                            link=link,
                            source="company_monitoring",
                            received_at=datetime.now().isoformat(),
                        )
                    )

        return jobs

    def _is_likely_job_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        import re

        # Filter out common non-job text
        exclude_patterns = [
            r"^(view|learn|see|click|apply|read|about|home|contact)",
            r"(page|site|website|logo|icon|menu|navigation)",
            r"^(current|openings?|jobs?|careers?|opportunities)$",
            r"^(department|location|type|filter|search|sort)",
            r"^(privacy|terms|policy|cookie)",
        ]

        text_lower = text.lower()

        for pattern in exclude_patterns:
            if re.search(pattern, text_lower):
                return False

        # Check if it contains job-related keywords
        job_keywords = [
            "engineer",
            "developer",
            "manager",
            "director",
            "lead",
            "architect",
            "designer",
            "analyst",
            "scientist",
            "specialist",
            "coordinator",
            "technician",
            "administrator",
            "officer",
            "associate",
            "consultant",
            "vp",
            "vice president",
            "head of",
            "chief",
        ]

        return any(keyword in text_lower for keyword in job_keywords)


def print_scraping_plan(companies: list[dict]) -> None:
    """Print scraping plan for Claude Code to execute"""
    print("\n" + "=" * 80)
    print("COMPANY SCRAPING PLAN - FOR CLAUDE CODE EXECUTION")
    print("=" * 80)
    print(f"\n{len(companies)} companies need scraping:\n")

    for i, company in enumerate(companies, 1):
        print(f"{i}. {company['name']}")
        print(f"   URL: {company['careers_url']}")
        print("   MCP Tool: mcp__firecrawl-mcp__firecrawl_scrape")
        print(f'   Args: url="{company["careers_url"]}", formats=["markdown"]')
        print()

    print("=" * 80)
    print("WORKFLOW:")
    print("1. Claude Code calls Firecrawl MCP tool for each company")
    print("2. Extracts markdown content from response")
    print("3. Calls process_company_markdown() for each result")
    print("4. Script stores jobs and sends notifications")
    print("=" * 80 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Company scraper with Firecrawl integration")
    parser.add_argument(
        "--company-filter",
        type=str,
        default="From Wes",
        help="Filter companies by notes (default: 'From Wes')",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Only print scraping plan, don't scrape",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum score to store (default: 50)",
    )
    parser.add_argument(
        "--llm-extraction",
        action="store_true",
        help="Enable LLM extraction in parallel with regex (requires OpenRouter API key)",
    )

    args = parser.parse_args()

    scraper = CompanyScraperWithFirecrawl(enable_llm_extraction=args.llm_extraction)

    # Get companies to scrape
    companies = scraper.get_companies_to_scrape(company_filter=args.company_filter)

    if not companies:
        print("No companies found matching filter")
        return

    # Print scraping plan
    print_scraping_plan(companies)

    if args.plan_only:
        print("✓ Plan printed. Use --execute to run scraping.")
        return

    print("\n⚠️  This script requires Claude Code to execute Firecrawl MCP calls")
    print("Run with --plan-only to see the execution plan\n")


if __name__ == "__main__":
    main()
