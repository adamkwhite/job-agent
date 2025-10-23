"""
Robotics & Deeptech Google Sheets Scraper
Scrapes job listings from public Google Sheets job board
"""
import sys
from pathlib import Path
import csv
import io
import requests
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import OpportunityData


class RoboticsDeeptechScraper:
    """Scrape robotics/deeptech jobs from Google Sheets"""

    def __init__(self):
        self.name = "robotics_deeptech"
        # Google Sheets CSV export URL
        self.sheet_id = "1i1OQti71WbiE9kFANDc5Pt-IknCM3UB2dD61gujPywk"
        self.gid = "0"
        self.base_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid={self.gid}"

        # Leadership keywords for filtering
        self.leadership_keywords = [
            'director', 'vp', 'vice president', 'head of', 'chief',
            'executive', 'principal', 'staff', 'senior manager', 'lead'
        ]

    def scrape(self) -> List[OpportunityData]:
        """Scrape jobs from Google Sheets"""
        print(f"Fetching robotics/deeptech jobs from Google Sheets...")

        try:
            response = requests.get(self.base_url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            # Parse CSV
            csv_data = response.text
            reader = csv.DictReader(io.StringIO(csv_data))

            opportunities = []

            for row in reader:
                # Extract fields
                title = row.get('Job_Title', '').strip()
                company = row.get('Company', '').strip()
                description = row.get('Description', '').strip()
                department = row.get('Department', '').strip()
                experience_level = row.get('Experience_Level', '').strip()
                city = row.get('City', '').strip()
                country = row.get('Country', '').strip()
                job_url = row.get('Job_Url', '').strip()
                status = row.get('Status', '').strip()

                # Skip if missing critical fields
                if not title or not company or not job_url:
                    continue

                # Filter for leadership roles (optional - can be removed to get all jobs)
                # Uncomment to filter for leadership only:
                # is_leadership = any(kw in title.lower() for kw in self.leadership_keywords)
                # if not is_leadership:
                #     continue

                # Filter for NEW/Recent jobs (optional)
                # Uncomment to only get fresh jobs:
                # if status.lower() not in ['new', 'recent']:
                #     continue

                # Build location string
                location_parts = []
                if city:
                    location_parts.append(city)
                if country:
                    location_parts.append(country)
                location = ', '.join(location_parts) if location_parts else ''

                # Build enhanced description with metadata
                desc_parts = []
                if description:
                    desc_parts.append(description)
                if department:
                    desc_parts.append(f"Department: {department}")
                if experience_level:
                    desc_parts.append(f"Level: {experience_level}")
                if status:
                    desc_parts.append(f"Status: {status}")

                enhanced_description = ' | '.join(desc_parts)

                # Create opportunity
                opportunity = OpportunityData(
                    source="robotics_deeptech_sheet",
                    source_email="",
                    type="direct_job",
                    company=company,
                    title=title,
                    location=location,
                    link=job_url,
                    description=enhanced_description,
                    job_type=department or '',
                    needs_research=False,
                    research_notes=f"Status: {status}, Level: {experience_level}"  # Store extra metadata here
                )

                opportunities.append(opportunity)

            print(f"✓ Found {len(opportunities)} jobs from robotics/deeptech sheet")
            return opportunities

        except Exception as e:
            print(f"✗ Error scraping Google Sheets: {e}")
            return []

    def get_leadership_jobs_only(self) -> List[OpportunityData]:
        """Scrape and filter for leadership roles only"""
        all_jobs = self.scrape()

        leadership_jobs = [
            job for job in all_jobs
            if any(kw in job.title.lower() for kw in self.leadership_keywords)
        ]

        print(f"✓ Filtered to {len(leadership_jobs)} leadership roles")
        return leadership_jobs

    def get_fresh_jobs_only(self) -> List[OpportunityData]:
        """Scrape and filter for NEW/Recent jobs only"""
        all_jobs = self.scrape()

        fresh_jobs = [
            job for job in all_jobs
            if job.research_notes and any(status in job.research_notes.lower() for status in ['status: new', 'status: recent'])
        ]

        print(f"✓ Filtered to {len(fresh_jobs)} fresh jobs (NEW/Recent)")
        return fresh_jobs


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape robotics/deeptech Google Sheets job board')
    parser.add_argument('--leadership-only', action='store_true', help='Only return leadership roles')
    parser.add_argument('--fresh-only', action='store_true', help='Only return NEW/Recent jobs')
    parser.add_argument('--limit', type=int, default=20, help='Max jobs to display')

    args = parser.parse_args()

    scraper = RoboticsDeeptechScraper()

    # Get jobs based on filters
    if args.leadership_only:
        jobs = scraper.get_leadership_jobs_only()
    elif args.fresh_only:
        jobs = scraper.get_fresh_jobs_only()
    else:
        jobs = scraper.scrape()

    # Display results
    print(f"\n{'='*80}")
    print(f"ROBOTICS/DEEPTECH JOBS - Showing first {min(len(jobs), args.limit)} of {len(jobs)}")
    print(f"{'='*80}\n")

    for i, job in enumerate(jobs[:args.limit], 1):
        print(f"{i}. {job.title}")
        print(f"   Company: {job.company}")
        print(f"   Department: {job.job_type or 'N/A'}")
        print(f"   Metadata: {job.research_notes or 'N/A'}")
        print(f"   Location: {job.location or 'Not specified'}")
        print(f"   Link: {job.link}\n")

    if len(jobs) > args.limit:
        print(f"... and {len(jobs) - args.limit} more jobs\n")

    # Summary by status (extract from research_notes)
    from collections import Counter
    statuses = []
    for job in jobs:
        if job.research_notes and 'Status:' in job.research_notes:
            # Extract status from "Status: NEW, Level: Mid"
            status_part = job.research_notes.split(',')[0].replace('Status:', '').strip()
            statuses.append(status_part)
        else:
            statuses.append('Unknown')

    status_counts = Counter(statuses)
    print("\nStatus Distribution:")
    for status, count in status_counts.most_common():
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
