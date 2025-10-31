"""
Test script for Unified Workflow V3 with Firecrawl integration

This script demonstrates the complete workflow:
1. Load company from CSV
2. Scrape career page with Firecrawl
3. Extract jobs from markdown
4. Score jobs (basic + enhanced)
5. Store in database
6. Send notifications for high-scoring jobs

Usage:
    PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/test_unified_workflow.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from jobs.unified_scraper_v3 import UnifiedJobScraper


def test_miovision():
    """
    Test workflow with Miovision (has active job postings)
    """
    print("=" * 80)
    print("TESTING UNIFIED WORKFLOW V3 - MIOVISION")
    print("=" * 80)

    # Step 1: Create scraper instance
    scraper = UnifiedJobScraper()

    # Step 2: Simulate Firecrawl markdown (from real scrape)
    markdown = """[Skip To Job Description](https://miovision.applytojob.com/apply#job-description)

Thanks for visiting our Career Page. Please review our open positions and apply to the positions that match your qualifications.

## Current Openings

- #### Business Operations




#### [Atlassian Site Administrator (AI Focus)](https://miovision.applytojob.com/apply/JYgcYtl0gP/Atlassian-Site-Administrator-AI-Focus)

  - Remote
  - Business Operations
- #### [SnapLogic Administrator & Developer](https://miovision.applytojob.com/apply/3XC67oaFCY/SnapLogic-Administrator-Developer)

  - Remote
  - Business Operations
- #### Customer Experience




#### [Customer Success Manager - West USA](https://miovision.applytojob.com/apply/AOsAoNv7lm/Customer-Success-Manager-West-USA)

  - Remote
  - Customer Experience
- #### Product Management




#### [Director, Product Management - Platform](https://miovision.applytojob.com/apply/ICgkCMvoO0/Director-Product-Management-Platform)

  - Remote
  - Product Management
- #### [Senior Product Manager](https://miovision.applytojob.com/apply/dHkksszYZT/Senior-Product-Manager)

  - Remote
  - Product Management
- #### Sales




#### [Solutions Engineering Manager](https://miovision.applytojob.com/apply/uLegDG1eLz/Solutions-Engineering-Manager)

  - Remote
  - Sales
- #### Security




#### [Security Analyst](https://miovision.applytojob.com/apply/106Ky1Py9X/Security-Analyst)

  - Remote
  - Security"""

    # Step 3: Extract jobs from markdown
    print("\n[STEP 1] Extracting jobs from Firecrawl markdown...")
    jobs = scraper._extract_jobs_from_markdown(
        markdown, company_name="Miovision", base_url="https://miovision.applytojob.com"
    )
    print(f"  ✓ Extracted {len(jobs)} jobs\n")

    # Step 4: Score each job (basic scoring)
    print("[STEP 2] Scoring jobs (basic)...")
    scored_jobs = []
    for job in jobs:
        score, grade, breakdown = scraper._score_job_basic(job)
        job["fit_score"] = score
        job["fit_grade"] = grade
        job["score_breakdown"] = breakdown
        scored_jobs.append(job)
        print(f"  {grade} ({score:3d}/115) - {job['title']}")

    # Step 5: Show which jobs would trigger enhanced scoring (70+)
    print("\n[STEP 3] Enhanced scoring candidates (70+)...")
    enhanced_candidates = [j for j in scored_jobs if j["fit_score"] >= 70]
    print(f"  → {len(enhanced_candidates)} jobs qualify for enhanced scoring")
    for job in enhanced_candidates:
        print(f"    - {job['title']} ({job['fit_score']}/115)")
        print(f"      Would fetch JD from: {job['link']}")

    # Step 6: Show which jobs would trigger notifications (80+)
    print("\n[STEP 4] Notification candidates (80+)...")
    notification_candidates = [j for j in scored_jobs if j["fit_score"] >= 80]
    print(f"  → {len(notification_candidates)} jobs qualify for notifications")
    for job in notification_candidates:
        print(f"    - {job['title']} ({job['fit_score']}/115)")
        print("      Would send SMS + Email to Wesley")

    # Step 7: Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Jobs extracted: {len(jobs)}")
    print(f"Jobs scored: {len(scored_jobs)}")
    print(f"Enhanced scoring candidates (70+): {len(enhanced_candidates)}")
    print(f"Notification candidates (80+): {len(notification_candidates)}")
    print("Grade distribution:")
    for grade in ["A", "B", "C", "D", "F"]:
        count = len([j for j in scored_jobs if j["fit_grade"] == grade])
        if count > 0:
            print(f"  {grade}: {count}")
    print("=" * 80)

    return scored_jobs


def test_with_database_storage():
    """
    Test storing jobs in database (dry run)
    """
    print("\n" + "=" * 80)
    print("TESTING DATABASE STORAGE")
    print("=" * 80)

    scored_jobs = test_miovision()

    db = JobDatabase()

    print("\n[STEP 5] Storing jobs in database...")
    stored_count = 0
    duplicate_count = 0

    for job in scored_jobs:
        job_dict = {
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "link": job["link"],
            "description": "",
            "source": "csv",
            "type": "direct_job",
            "received_at": "2025-10-30T21:00:00",
            "fit_score": job["fit_score"],
            "fit_grade": job["fit_grade"],
            "score_breakdown": json.dumps(job["score_breakdown"]),
            "keywords_matched": json.dumps([]),
            "source_email": "",
        }

        job_id = db.add_job(job_dict)
        if job_id:
            stored_count += 1
            print(f"  ✓ Stored: {job['title']} (ID: {job_id})")
        else:
            duplicate_count += 1
            print(f"  - Duplicate: {job['title']}")

    print(f"\n  Stored: {stored_count}")
    print(f"  Duplicates: {duplicate_count}")


if __name__ == "__main__":
    # Run basic test
    scored_jobs = test_miovision()

    # Optionally test database storage
    print("\n\nWould you like to test database storage? (This will add jobs to jobs.db)")
    print("Run with --store flag to enable database storage")

    if "--store" in sys.argv:
        test_with_database_storage()
