"""
Migrate companies from robotics sheet to company monitoring database (Issue #131)

This script:
1. Downloads robotics/deeptech Google Sheet
2. Extracts unique companies with career page URLs
3. Deduplicates against existing companies
4. Adds companies to monitoring database in batches

Usage:
    python scripts/migrate_robotics_companies.py [--dry-run] [--min-jobs N] [--batch-size N]
"""

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.company_service import CompanyService


def derive_career_page_url(job_url: str) -> str | None:
    """
    Derive company career page URL from a job posting URL

    Handles various ATS platforms:
    - Greenhouse: greenhouse.io/company/jobs/123 → greenhouse.io/company/jobs
    - Workday: myworkdayjobs.com/company/job/123 → myworkdayjobs.com/company
    - Lever: jobs.lever.co/company/uuid → jobs.lever.co/company
    - Generic: company.com/careers/job/123 → company.com/careers

    Returns:
        Career page URL or None if URL format is unknown
    """
    try:
        parsed = urlparse(job_url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Greenhouse ATS
        if "greenhouse.io" in domain or "grnh.se" in domain:
            # Extract company name from path
            # Format: /company/jobs/123 or /company/123
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                company_name = parts[0]
                return f"https://{domain}/{company_name}/jobs"

        # Workday ATS
        if "myworkdayjobs.com" in domain:
            # Format: company.wd1.myworkdayjobs.com/CompanyName/job/...
            # Career page: company.wd1.myworkdayjobs.com/CompanyName
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                company_name = parts[0]
                return f"https://{domain}/{company_name}"

        # Lever ATS
        if "lever.co" in domain:
            # Format: jobs.lever.co/company/uuid
            # Career page: jobs.lever.co/company
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                company_name = parts[0]
                return f"https://{domain}/{company_name}"

        # Ashby HQ ATS
        if "ashbyhq.com" in domain:
            # Format: jobs.ashbyhq.com/company/uuid
            # Career page: jobs.ashbyhq.com/company
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                company_name = parts[0]
                return f"https://{domain}/{company_name}"

        # Generic /careers, /jobs patterns
        if "/careers" in path:
            # Find /careers in path and truncate there
            careers_index = path.find("/careers")
            base_path = path[: careers_index + len("/careers")]
            return f"https://{domain}{base_path}"

        if "/jobs" in path:
            # Find /jobs in path and truncate there
            jobs_index = path.find("/jobs")
            base_path = path[: jobs_index + len("/jobs")]
            return f"https://{domain}{base_path}"

        # If no pattern matches, return None
        return None

    except Exception:
        return None


def fetch_robotics_sheet() -> list[dict]:
    """
    Fetch and parse robotics/deeptech Google Sheet

    Returns:
        List of row dictionaries with job data
    """
    sheet_id = "1i1OQti71WbiE9kFANDc5Pt-IknCM3UB2dD61gujPywk"
    gid = "0"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    print("📥 Fetching robotics sheet from Google...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Parse CSV
    csv_data = response.text
    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)

    print(f"✓ Fetched {len(rows)} jobs from sheet\n")
    return rows


def extract_unique_companies(rows: list[dict], min_jobs: int = 1) -> list[dict]:
    """
    Extract unique companies from sheet rows

    Args:
        rows: List of row dictionaries from sheet
        min_jobs: Minimum number of jobs required to include company

    Returns:
        List of company dictionaries with name, career_url, job_count
    """
    company_data: dict = defaultdict(lambda: {"job_urls": set(), "job_count": 0})

    for row in rows:
        company = row.get("Company", "").strip()
        job_url = row.get("Job_Url", "").strip()

        if not company or not job_url:
            continue

        company_data[company]["job_urls"].add(job_url)
        company_data[company]["job_count"] += 1

    print(f"📊 Found {len(company_data)} unique companies in sheet")

    # Derive career page URLs
    companies = []
    companies_without_career_url = []

    for company_name, data in company_data.items():
        if data["job_count"] < min_jobs:
            continue

        # Try to derive career page from job URLs
        career_url = None
        for job_url in data["job_urls"]:
            derived_url = derive_career_page_url(job_url)
            if derived_url:
                career_url = derived_url
                break

        if career_url:
            companies.append(
                {
                    "name": company_name,
                    "careers_url": career_url,
                    "job_count": data["job_count"],
                    "notes": f"From robotics sheet ({data['job_count']} jobs)",
                    "source": "robotics_sheet_migration",
                }
            )
        else:
            companies_without_career_url.append((company_name, data["job_count"]))

    # Sort by job count (descending)
    companies.sort(key=lambda x: x["job_count"], reverse=True)

    print(f"✓ Derived career URLs for {len(companies)} companies")
    print(f"⚠ Could not derive URLs for {len(companies_without_career_url)} companies\n")

    if companies_without_career_url:
        print("Companies without derived URLs (top 10):")
        for name, count in sorted(companies_without_career_url, key=lambda x: x[1], reverse=True)[
            :10
        ]:
            print(f"  - {name} ({count} jobs)")
        print()

    return companies


def main():
    parser = argparse.ArgumentParser(
        description="Migrate companies from robotics sheet to monitoring database"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview companies without adding to database"
    )
    parser.add_argument(
        "--min-jobs", type=int, default=1, help="Minimum jobs per company to migrate (default: 1)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Batch size for adding companies"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("ROBOTICS SHEET COMPANY MIGRATION (Issue #131)")
    print("=" * 80)
    print(f"Minimum jobs per company: {args.min_jobs}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Fetch sheet data
    rows = fetch_robotics_sheet()

    # Extract unique companies
    companies = extract_unique_companies(rows, min_jobs=args.min_jobs)

    if not companies:
        print("❌ No companies found to migrate")
        return

    print("📋 Top 20 companies by job count:")
    for i, company in enumerate(companies[:20], 1):
        print(f"  {i}. {company['name']} - {company['job_count']} jobs")
        print(f"     URL: {company['careers_url']}")
    print()

    if args.dry_run:
        print(f"✓ Dry run complete. Would add {len(companies)} companies to database")
        print("\nTo migrate, run without --dry-run flag:")
        print(f"  python {sys.argv[0]} --min-jobs {args.min_jobs}")
        return

    # Add companies to database
    company_service = CompanyService()
    print(f"💾 Adding {len(companies)} companies to database...")

    result = company_service.add_companies_batch(companies, similarity_threshold=90.0)

    print("\n" + "=" * 80)
    print("MIGRATION RESULTS")
    print("=" * 80)
    print(f"✓ Added: {result['added']}")
    print(f"⊘ Skipped (duplicates): {result['skipped_duplicates']}")
    print(f"✗ Errors: {result['errors']}")

    if result["details"]:
        print("\nDetails:")
        for detail in result["details"][:20]:  # Show first 20
            status = "✓" if detail["status"] == "added" else "⊘"
            print(f"  {status} {detail['company']}")
            if detail["status"] != "added":
                print(f"     Reason: {detail.get('reason', 'Unknown')}")

    print("\n" + "=" * 80)
    print(f"Migration complete! Added {result['added']} new companies to monitoring.")
    print("=" * 80)


if __name__ == "__main__":
    main()
