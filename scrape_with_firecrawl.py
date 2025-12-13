#!/usr/bin/env python3
"""
Temporary script to scrape companies with Firecrawl MCP
This script is designed to be run from within Claude Code session
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from jobs.scrape_companies_with_firecrawl import CompanyScraperWithFirecrawl


def main():
    scraper = CompanyScraperWithFirecrawl()

    # Get companies
    companies = scraper.company_service.get_companies(active_only=True, filter_source="From Wes")

    print(f"Found {len(companies)} companies to scrape\n")

    stats = {"total": len(companies), "scraped": 0, "jobs_found": 0, "errors": 0}

    # Will be populated by Claude Code calling Firecrawl MCP
    results = []

    return companies, stats, results


if __name__ == "__main__":
    companies, stats, results = main()
    print(f"\nReady to scrape {len(companies)} companies")
    print("Waiting for Claude Code to call Firecrawl MCP...")
