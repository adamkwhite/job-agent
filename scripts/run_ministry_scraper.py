#!/usr/bin/env python3
"""
Ministry of Testing Scraper - Automated Runner

This script runs the Ministry of Testing scraper with Firecrawl MCP integration.
It's designed to be run from Claude Code which will automatically make the
Firecrawl MCP tool calls.

Usage:
    PYTHONPATH=$PWD job-agent-venv/bin/python scripts/run_ministry_scraper.py
    PYTHONPATH=$PWD job-agent-venv/bin/python scripts/run_ministry_scraper.py --max-pages 2

Options:
    --max-pages N       Maximum pages to scrape (default: 3)
    --locations L1 L2   Target locations (default: Canada Remote United States)
    --min-score N       Minimum score to store (default: 47)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jobs.ministry_scraper import MinistryScraper


def run_scraper_with_firecrawl(
    max_pages: int = 3,
    target_locations: list[str] | None = None,
    min_score: int = 47,
):
    """
    Run Ministry of Testing scraper with Firecrawl MCP calls

    This function will request Claude Code to make Firecrawl MCP calls
    for each page, then parse and store the results.

    Args:
        max_pages: Maximum pages to scrape
        target_locations: Target locations to filter
        min_score: Minimum score threshold
    """
    if target_locations is None:
        target_locations = ["Canada", "Remote", "United States", "Toronto"]

    scraper = MinistryScraper()

    print("\n" + "=" * 80)
    print("MINISTRY OF TESTING SCRAPER - AUTOMATED RUN")
    print("=" * 80)
    print(f"Target locations: {', '.join(target_locations)}")
    print(f"Max pages: {max_pages}")
    print(f"Min score: {min_score}")
    print("=" * 80 + "\n")

    stats = {
        "pages_scraped": 0,
        "jobs_found": 0,
        "jobs_stored": 0,
        "jobs_scored": 0,
        "profile_scores": {},
    }

    # Request Firecrawl scrapes for each page
    print("🔄 Requesting Firecrawl MCP to scrape Ministry of Testing pages...")
    print()
    print("Claude Code will now:")
    print("1. Call mcp__firecrawl-mcp__firecrawl_scrape for each page")
    print("2. Pass markdown results to scraper.parse_page_and_store()")
    print("3. Store and score jobs in database")
    print()
    print("Starting scrape...")
    print()

    # Pages to scrape
    urls = []
    for page_num in range(1, max_pages + 1):
        url = (
            f"https://www.ministryoftesting.com/jobs?page={page_num}"
            if page_num > 1
            else "https://www.ministryoftesting.com/jobs"
        )
        urls.append((page_num, url))

    # Return the scraper and URLs so Claude Code can make the MCP calls
    return scraper, urls, stats, target_locations, min_score


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Ministry of Testing scraper with Firecrawl")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Maximum pages to scrape (default: 3, ~75 jobs)",
    )
    parser.add_argument(
        "--locations",
        type=str,
        nargs="+",
        default=["Canada", "Remote", "United States"],
        help="Target locations (default: Canada Remote United States)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=47,
        help="Minimum score to store jobs (default: 47 for Mario's C-grade threshold)",
    )

    args = parser.parse_args()

    print("\n✨ Ministry of Testing Scraper Ready")
    print()
    print("This script is designed to be run from Claude Code.")
    print("Claude Code will make Firecrawl MCP calls automatically.")
    print()
    print("If you're running this manually, you'll need to:")
    print("1. Call mcp__firecrawl-mcp__firecrawl_scrape for each URL")
    print("2. Pass the markdown result to scraper.parse_page_and_store()")
    print()
    print("Or better yet: Ask Claude Code to run this script!")
    print()

    # Prepare scraper (actual scraping happens via MCP calls made by Claude Code)
    scraper, urls, stats, target_locations, min_score = run_scraper_with_firecrawl(
        max_pages=args.max_pages,
        target_locations=args.locations,
        min_score=args.min_score,
    )

    print(f"📋 Ready to scrape {len(urls)} pages:")
    for page_num, url in urls:
        print(f"   Page {page_num}: {url}")

    print()
    print("🤖 Waiting for Claude Code to make Firecrawl MCP calls...")
    print()

    return scraper, urls, stats, target_locations, min_score


if __name__ == "__main__":
    main()
