#!/usr/bin/env python3
"""
Compare extraction methods across all cached Firecrawl markdown files

This script processes all cached markdown files and compares regex vs LLM extraction.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import JobDatabase
from extractors.extraction_comparator import ExtractionComparator
from scrapers.firecrawl_career_scraper import CompanyScraperWithFirecrawl


def main():
    """Compare extraction methods across all cached markdown files"""
    cache_dir = Path("data/firecrawl_cache")

    if not cache_dir.exists():
        print(f"❌ Cache directory not found: {cache_dir}")
        sys.exit(1)

    # Find all markdown files
    markdown_files = sorted(cache_dir.glob("*.md"))

    if not markdown_files:
        print(f"❌ No markdown files found in {cache_dir}")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print("COMPARING EXTRACTION METHODS")
    print(f"{'=' * 80}")
    print(f"Found {len(markdown_files)} cached markdown files\n")

    # Initialize components
    scraper = CompanyScraperWithFirecrawl()
    comparator = ExtractionComparator()
    database = JobDatabase()

    # Storage for all metrics
    all_metrics = []

    # Process each file
    for i, md_file in enumerate(markdown_files, 1):
        # Extract company name from filename (e.g., "boston_dynamics_20251130.md")
        company_name = md_file.stem.rsplit("_", 1)[0].replace("_", " ").title()

        print(f"\n[{i}/{len(markdown_files)}] Processing: {company_name}")
        print(f"File: {md_file.name}")

        # Read markdown content
        try:
            markdown_content = md_file.read_text()
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            continue

        # Extract jobs using both methods
        try:
            jobs_regex = scraper._extract_jobs_from_markdown(markdown_content, company_name)
            print(f"  Regex:  {len(jobs_regex)} jobs extracted")
        except Exception as e:
            print(f"  ❌ Regex extraction failed: {e}")
            jobs_regex = []

        try:
            # LLM extraction
            if scraper.llm_extractor and scraper.llm_extractor.budget_available():
                jobs_llm_raw = scraper.llm_extractor.extract_jobs(markdown_content, company_name)
                # Convert to tuple format
                jobs_llm = [(job, "llm") for job in jobs_llm_raw]
                print(f"  LLM:    {len(jobs_llm)} jobs extracted")
            else:
                jobs_llm = []
                print("  LLM:    Skipped (budget exceeded or disabled)")
        except Exception as e:
            print(f"  ❌ LLM extraction failed: {e}")
            jobs_llm = []

        # Compare results
        if jobs_regex or jobs_llm:
            metrics = comparator.compare(jobs_regex, jobs_llm, company_name)

            # Store in database
            try:
                database.store_extraction_metrics(metrics)
                print("  ✅ Metrics stored in database")
            except Exception as e:
                print(f"  ⚠️  Failed to store metrics: {e}")

            # Add to report
            all_metrics.append(metrics)

            # Print quick summary
            print(
                f"  Summary: Overlap={metrics['overlap_count']}, "
                f"Regex-only={metrics['regex_unique']}, "
                f"LLM-only={metrics['llm_unique']}"
            )

            # Print full comparison table
            comparator.print_comparison_table(metrics)
        else:
            print("  ⚠️  No jobs extracted by either method")

    # Generate summary report
    if all_metrics:
        print(f"\n{'=' * 80}")
        print("OVERALL SUMMARY")
        print(f"{'=' * 80}\n")

        total_regex_jobs = sum(m["regex_jobs_found"] for m in all_metrics)
        total_llm_jobs = sum(m["llm_jobs_found"] for m in all_metrics)
        total_overlap = sum(m["overlap_count"] for m in all_metrics)

        # Calculate average location rates
        regex_rates = [m["regex_location_rate"] for m in all_metrics if m["regex_jobs_found"] > 0]
        llm_rates = [m["llm_location_rate"] for m in all_metrics if m["llm_jobs_found"] > 0]

        avg_regex_rate = sum(regex_rates) / len(regex_rates) if regex_rates else 0
        avg_llm_rate = sum(llm_rates) / len(llm_rates) if llm_rates else 0

        print(f"Companies processed:        {len(all_metrics)}")
        print(f"Total regex jobs:           {total_regex_jobs}")
        print(f"Total LLM jobs:             {total_llm_jobs}")
        print(f"Total overlap:              {total_overlap}")
        print("\nAverage location rates:")
        print(f"  Regex:                    {avg_regex_rate:.1%}")
        print(f"  LLM:                      {avg_llm_rate:.1%}")

        if avg_llm_rate > avg_regex_rate:
            improvement = avg_llm_rate - avg_regex_rate
            print(f"  ✅ LLM improvement:        +{improvement:.1%}")
        else:
            decline = avg_regex_rate - avg_llm_rate
            print(f"  ⚠️  LLM vs Regex:          -{decline:.1%}")

        # Save detailed report
        report_date = datetime.now().strftime("%Y-%m-%d")
        report_path = Path(f"logs/extraction-metrics-{report_date}.json")
        report_path.parent.mkdir(exist_ok=True)

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "companies_processed": len(all_metrics),
            "summary": {
                "total_regex_jobs": total_regex_jobs,
                "total_llm_jobs": total_llm_jobs,
                "total_overlap": total_overlap,
                "avg_regex_location_rate": avg_regex_rate,
                "avg_llm_location_rate": avg_llm_rate,
            },
            "company_metrics": all_metrics,
        }

        report_path.write_text(json.dumps(report_data, indent=2))
        print(f"\n📊 Detailed report saved to: {report_path}")

    else:
        print("\n⚠️  No metrics collected")

    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    main()
