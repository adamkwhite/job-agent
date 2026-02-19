"""
Enrichment pipeline orchestrator
Coordinates career page discovery and job scraping
"""

import json

from enrichment.career_page_finder import CareerPageFinder, ManualCareerPageCollector
from enrichment.career_page_scraper import CareerPageScraper
from job_filter import JobFilter
from models import EnrichmentResult, OpportunityData


class EnrichmentPipeline:
    """Orchestrates the enrichment process for funding leads"""

    def __init__(self, config_path: str = "config/parsers.json"):
        self.finder = CareerPageFinder()
        self.scraper = CareerPageScraper()
        self.manual_collector = ManualCareerPageCollector()
        self.job_filter = JobFilter()

        # Load config
        with open(config_path) as f:
            self.config = json.load(f)

    def enrich_opportunity(self, opportunity: OpportunityData) -> EnrichmentResult:
        """
        Enrich a funding lead by finding and scraping career page

        Args:
            opportunity: Funding lead opportunity

        Returns:
            EnrichmentResult with found jobs
        """
        if not opportunity.needs_research:
            return EnrichmentResult(success=False, error="Opportunity doesn't need research")

        # Check if opportunity meets funding criteria
        from parsers.f6s_parser import F6SParser

        parser = F6SParser()

        if not parser.should_process_company(opportunity, self.config):
            print(f"\nSkipping {opportunity.company}: Doesn't meet funding criteria")
            print(
                f"  Stage: {opportunity.funding_stage}, Amount: ${opportunity.funding_amount_usd:,.0f}"
                if opportunity.funding_amount_usd
                else "  Stage: Unknown"
            )
            return EnrichmentResult(success=False, error="Doesn't meet funding criteria")

        print(f"\n{'=' * 70}")
        print(f"Enriching: {opportunity.company}")
        print(f"  Funding: {opportunity.funding_stage} - {opportunity.funding_amount}")
        print(f"  Industries: {', '.join(opportunity.industry_tags or [])}")
        print(f"{'=' * 70}")

        # Step 1: Find career page URL
        career_url = self.finder.find_career_page(opportunity)

        if not career_url:
            # Add to manual review
            self.manual_collector.add_for_manual_review(opportunity)

            opportunity.research_attempted = True
            opportunity.research_notes = (
                "Could not find career page automatically - added to manual review"
            )

            return EnrichmentResult(
                success=False,
                method_used="manual_required",
                error="Career page not found - needs manual entry",
            )

        # Update opportunity with career page URL
        opportunity.career_page_url = career_url
        opportunity.research_attempted = True

        # Step 2: Scrape jobs from career page
        jobs = self.scraper.scrape_jobs(career_url, opportunity.company, opportunity)

        if not jobs:
            opportunity.research_notes = f"Career page found but no jobs extracted: {career_url}"
            return EnrichmentResult(
                success=False,
                career_page_url=career_url,
                method_used="pattern" if "/careers" in career_url else "unknown",
                error="No jobs found on career page",
            )

        # Step 3: Filter jobs for PM roles
        print(f"\nFiltering {len(jobs)} jobs for Product Manager roles...")
        # Convert OpportunityData to dicts for existing filter
        jobs_as_dicts = [self._opportunity_to_dict(job) for job in jobs]
        pm_jobs_dicts, _ = self.job_filter.filter_jobs(jobs_as_dicts)

        # Convert back to OpportunityData with filter results
        pm_jobs = []
        for i, job_dict in enumerate(pm_jobs_dicts):
            job = jobs[i] if i < len(jobs) else jobs[0]
            job.keywords_matched = job_dict.get("keywords_matched", [])
            job.filter_passed = True
            pm_jobs.append(job)

        non_pm_jobs = pm_jobs_dicts  # Keep as dicts for logging

        print(f"  ✓ {len(pm_jobs)} Product Manager jobs found")
        print(f"  ✗ {len(non_pm_jobs)} jobs excluded")

        # Show PM jobs found
        for job in pm_jobs:
            print(f"\n  → {job.title}")
            print(f"    Keywords: {', '.join(job.keywords_matched or [])}")

        opportunity.research_notes = (
            f"Found {len(pm_jobs)} PM jobs out of {len(jobs)} total on {career_url}"
        )

        return EnrichmentResult(
            success=True, career_page_url=career_url, jobs_found=pm_jobs, method_used="pattern"
        )

    def _opportunity_to_dict(self, opp: OpportunityData) -> dict:
        """Convert OpportunityData to dict for filtering"""
        return {
            "title": opp.title or "Job Opportunity",
            "company": opp.company,
            "location": opp.location or opp.company_location or "",
            "description": opp.description or "",
            "salary": opp.salary or "",
            "job_type": opp.job_type or "",
        }

    def enrich_opportunities(self, opportunities: list[OpportunityData]) -> list[OpportunityData]:
        """
        Enrich multiple opportunities

        Args:
            opportunities: List of opportunities

        Returns:
            List of all opportunities (original + enriched jobs)
        """
        all_opportunities = []

        for opp in opportunities:
            if opp.needs_research:
                result = self.enrich_opportunity(opp)

                if result.success and result.jobs_found:
                    # Add the enriched jobs
                    all_opportunities.extend(result.jobs_found)
                else:
                    # Keep original opportunity with research notes
                    all_opportunities.append(opp)
            else:
                # Direct job, no enrichment needed
                all_opportunities.append(opp)

        return all_opportunities
