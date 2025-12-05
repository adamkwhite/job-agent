#!/usr/bin/env python3
"""
Add 20 priority robotics companies to the monitoring database.
Uses fuzzy matching to prevent duplicates.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.company_service import CompanyService

# 20 priority robotics companies
ROBOTICS_COMPANIES = [
    {
        "name": "Gecko Robotics",
        "careers_url": "https://www.geckorobotics.com/careers/",
        "notes": "Priority robotics company - Infrastructure robotics",
    },
    {
        "name": "Boston Dynamics",
        "careers_url": "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
        "notes": "Priority robotics company - Humanoid and quadruped robots",
    },
    {
        "name": "Robust AI",
        "careers_url": "https://jobs.lever.co/robust-ai",
        "notes": "Priority robotics company - Warehouse robotics",
    },
    {
        "name": "Chef Robotics",
        "careers_url": "https://jobs.lever.co/ChefRobotics",
        "notes": "Priority robotics company - Food service robotics",
    },
    {
        "name": "Skydio",
        "careers_url": "https://www.skydio.com/careers",
        "notes": "Priority robotics company - Autonomous drones",
    },
    {
        "name": "Sanctuary AI",
        "careers_url": "https://jobs.lever.co/sanctuary",
        "notes": "Priority robotics company - Humanoid robots",
    },
    {
        "name": "Agility Robotics",
        "careers_url": "https://www.agilityrobotics.com/about/careers",
        "notes": "Priority robotics company - Bipedal robots",
    },
    {
        "name": "Figure",
        "careers_url": "https://job-boards.greenhouse.io/figureai",
        "notes": "Priority robotics company - Humanoid robots for manufacturing",
    },
    {
        "name": "1X Technologies",
        "careers_url": "https://www.1x.tech/careers",
        "notes": "Priority robotics company - Humanoid robots",
    },
    {
        "name": "Skild AI",
        "careers_url": "https://job-boards.greenhouse.io/skildai-careers",
        "notes": "Priority robotics company - General-purpose robotics AI",
    },
    {
        "name": "Dexterity",
        "careers_url": "https://jobs.lever.co/dexterity",
        "notes": "Priority robotics company - Warehouse picking robots",
    },
    {
        "name": "Veo",
        "careers_url": "https://jobs.lever.co/veo",
        "notes": "Priority robotics company - Autonomous forklifts",
    },
    {
        "name": "Covariant",
        "careers_url": "https://covariant.ai/careers/",
        "notes": "Priority robotics company - AI for warehouse robotics",
    },
    {
        "name": "Nuro",
        "careers_url": "https://nuro.ai/careers/",
        "notes": "Priority robotics company - Autonomous delivery vehicles",
    },
    {
        "name": "RightHand Robotics",
        "careers_url": "https://righthandrobotics.com/careers",
        "notes": "Priority robotics company - Warehouse picking robots",
    },
    {
        "name": "Nimble Robotics",
        "careers_url": "https://jobs.lever.co/NimbleAI",
        "notes": "Priority robotics company - Warehouse fulfillment",
    },
    {
        "name": "Miso Robotics",
        "careers_url": "https://misorobotics.com/careers/",
        "notes": "Priority robotics company - Food service robotics",
    },
    {
        "name": "Apptronik",
        "careers_url": "https://apptronik.com/careers",
        "notes": "Priority robotics company - Humanoid robots",
    },
    {
        "name": "Bright Machines",
        "careers_url": "https://www.brightmachines.com/careers",
        "notes": "Priority robotics company - Manufacturing automation",
    },
    {
        "name": "Machina Labs",
        "careers_url": "https://machinalabs.ai/careers",
        "notes": "Priority robotics company - Robotic metal forming",
    },
]


def main():
    """Add robotics companies to database with fuzzy matching."""
    service = CompanyService()

    print("=" * 80)
    print("ADD ROBOTICS COMPANIES TO DATABASE")
    print("=" * 80)
    print(f"Companies to add: {len(ROBOTICS_COMPANIES)}")
    print("Fuzzy matching threshold: 90%")
    print()

    # Add companies in batch (handles fuzzy matching and duplicates)
    stats = service.add_companies_batch(
        companies=ROBOTICS_COMPANIES,
        similarity_threshold=90.0,  # 90% similarity threshold
    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Added: {stats['added']}")
    print(f"⊘ Skipped (duplicates): {stats['skipped_duplicates']}")
    print(f"✗ Errors: {stats['errors']}")
    print("=" * 80)

    if stats["added"] > 0:
        print("\nRobotics companies have been added to the database!")
        print("You can now use the company_scraper.py to scrape these companies:")
        print("  PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/company_scraper.py")


if __name__ == "__main__":
    main()
