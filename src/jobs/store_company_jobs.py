"""
Store company monitoring jobs in database
Run this once to import the 14 leadership jobs from Wes's 26 companies
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.profile_scorer import ProfileScorer
from database import JobDatabase
from utils.profile_manager import get_profile_manager
from utils.score_thresholds import Grade

# Constants for repeated location strings
HAMILTON_ONTARIO_CANADA = "Hamilton, Ontario, Canada"


def main():
    """Store company jobs in database"""

    print("=" * 70)
    print("STORING COMPANY JOBS IN DATABASE")
    print("=" * 70)

    # The 14 leadership jobs from manual scraping
    company_jobs = [
        # Promise Robotics
        {
            "title": "Senior Robotics and Control Engineer",
            "company": "Promise Robotics",
            "location": "Calgary, AB",
            "link": "https://promiserobotics.com/careers/",
        },
        # Miovision (3 jobs)
        {
            "title": "Director, Product Management - Platform",
            "company": "Miovision",
            "location": "Remote",
            "link": "https://miovision.applytojob.com/apply/ICgkCMvoO0/Director-Product-Management-Platform",
        },
        {
            "title": "Senior Product Manager",
            "company": "Miovision",
            "location": "Remote",
            "link": "https://miovision.applytojob.com/apply/dHkksszYZT/Senior-Product-Manager",
        },
        {
            "title": "Solutions Engineering Manager",
            "company": "Miovision",
            "location": "Remote",
            "link": "https://miovision.applytojob.com/apply/uLegDG1eLz/Solutions-Engineering-Manager",
        },
        # Stryker (4 jobs)
        {
            "title": "Lead Human Resources Business Partner - Stryker Canada (HYBRID)",
            "company": "Stryker",
            "location": HAMILTON_ONTARIO_CANADA,
            "link": "https://careers.stryker.com/lead-human-resources-business-partner-stryker-canada-hybrid/job/0D47BC319BD9C53E8133246A8DAF7461",
        },
        {
            "title": "Senior Manager FP&A (8 month contract - Hybrid)",
            "company": "Stryker",
            "location": HAMILTON_ONTARIO_CANADA,
            "link": "https://careers.stryker.com/senior-manager-fp-a-8-month-contract-hybrid/job/1DB8E70AAFFD68FB70B97AA6750B9D1D",
        },
        {
            "title": "Associate Manager, Inventory Accounting (hybrid)",
            "company": "Stryker",
            "location": HAMILTON_ONTARIO_CANADA,
            "link": "https://careers.stryker.com/associate-manager-inventory-accounting-hybrid/job/0261D85E9C82947261D639DE67797D6A",
        },
        {
            "title": "Senior Product Manager - Patient Care - Hybrid",
            "company": "Stryker",
            "location": HAMILTON_ONTARIO_CANADA,
            "link": "https://careers.stryker.com/senior-product-manager-patient-care-hybrid/job/D621045890300D0E92DD5D3B2BFEE3D9",
        },
        # P&P Optica
        {
            "title": "Project Manager",
            "company": "P&P Optica",
            "location": "Waterloo, Ontario, Canada",
            "link": "https://ppo.applytojobs.ca/operations/42369",
        },
        # NDI (Northern Digital)
        {
            "title": "Global Director, Project Management Office",
            "company": "NDI (Northern Digital)",
            "location": "Waterloo, ON (Hybrid)",
            "link": "https://recruiting.ultipro.com/ROP1001ROPER/JobBoard/fe143739-d521-4f49-a596-553671cff63b/OpportunityDetail?opportunityId=b124b004-7beb-4e87-82d7-39bd90ee40b9",
        },
        # Baylis Medical Technologies
        {
            "title": "Equipment & Maintenance Manager",
            "company": "Baylis Medical Technologies",
            "location": "Mississauga, ON",
            "link": "https://recruiting.ultipro.ca/BAY5002BAYM/JobBoard/15d9dd2e-ab9a-4fd7-a9f6-b561f2b3f3c5/OpportunityDetail?opportunityId=d459e681-bd06-4a48-b3b9-10b2b24bec4e",
        },
        # Jazwares (2 jobs)
        {
            "title": "Senior Director, Global Project Management & Business Services",
            "company": "Jazwares",
            "location": "Plantation, FL (Hybrid)",
            "link": "https://recruiting.ultipro.com/JAZ1000JAZW/JobBoard/703a9474-9a06-41dc-a880-4948822e0ce9/OpportunityDetail?opportunityId=8aed7851-23a2-4b35-8470-2f01a931cba6",
        },
        {
            "title": "Dir, Business Data & Analytics",
            "company": "Jazwares",
            "location": "Plantation, FL (Hybrid)",
            "link": "https://recruiting.ultipro.com/JAZ1000JAZW/JobBoard/703a9474-9a06-41dc-a880-4948822e0ce9/OpportunityDetail?opportunityId=a25b7a6e-4192-48ad-9042-ed57645c9a6b",
        },
        # Sciex
        {
            "title": "Engineering Manager I",
            "company": "Sciex",
            "location": "Bangalore, India",
            "link": "https://jobs.danaher.com/global/en/job/R1297471/Engineering-Manager-I",
        },
    ]

    print(f"\nProcessing {len(company_jobs)} company jobs...")

    db = JobDatabase()
    wes_profile = get_profile_manager().get_profile("wes")
    scorer = ProfileScorer(wes_profile)

    stats = {
        "total": len(company_jobs),
        "stored": 0,
        "duplicates": 0,
        "by_grade": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
    }

    for i, job in enumerate(company_jobs, 1):
        print(f"\n[{i}/{len(company_jobs)}] {job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")

        # Score the job
        score, grade, breakdown, _classification_metadata = scorer.score_job(job)
        print(f"  Score: {score}/115 ({grade} grade)")

        # Prepare for storage
        job_dict = {
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "link": job["link"],
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
            "fit_score": score,
            "fit_grade": grade,
            "score_breakdown": json.dumps(breakdown),
            "keywords_matched": json.dumps([]),
            "source_email": "",
        }

        # Store in database
        job_id = db.add_job(job_dict)

        if job_id:
            stats["stored"] += 1
            stats["by_grade"][grade] += 1

            # Update score
            db.update_job_score(job_id, score, grade, json.dumps(breakdown))
            print(f"  ✓ Stored (ID: {job_id})")
        else:
            stats["duplicates"] += 1
            print("  - Duplicate (already in database)")

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Total jobs: {stats['total']}")
    print(f"Stored: {stats['stored']}")
    print(f"Duplicates: {stats['duplicates']}")
    print("\nBy Grade:")
    print(f"  A grade ({Grade.A.value}+): {stats['by_grade']['A']}")
    print(f"  B grade ({Grade.B.value}+): {stats['by_grade']['B']}")
    print(f"  C grade ({Grade.C.value}+): {stats['by_grade']['C']}")
    print(f"  D grade ({Grade.D.value}+): {stats['by_grade']['D']}")
    print(f"  F grade (<{Grade.D.value}): {stats['by_grade']['F']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
