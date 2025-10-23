"""
Job Scoring Agent
Evaluates job opportunities against candidate profile
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase


class JobScorer:
    """Score jobs against Wesley van Ooyen's profile"""

    def __init__(self):
        self.db = JobDatabase()

        # Wesley's profile criteria
        self.profile = {
            "target_seniority": ["vp", "director", "head of", "executive", "chief", "cto", "cpo"],
            "domain_keywords": [
                "robotics",
                "automation",
                "iot",
                "hardware",
                "medtech",
                "medical device",
                "mechatronics",
                "embedded",
                "firmware",
                "mechanical",
                "physical product",
                "manufacturing",
                "supply chain",
                "dfm",
                "dfa",
                "industrial",
            ],
            "role_types": {
                "engineering_leadership": ["engineering", "r&d", "technical", "hardware"],
                "product_leadership": ["product", "cpo", "chief product"],
                "dual_role": ["product engineering", "technical product", "hardware product"],
            },
            "company_stage": ["series a", "series b", "series c", "growth", "scale-up", "funded"],
            "avoid_keywords": ["junior", "associate", "intern", "coordinator"],
            "location_preferences": {
                "remote_keywords": ["remote", "work from home", "wfh", "anywhere", "distributed"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [
                    "toronto",
                    "waterloo",
                    "burlington",
                    "oakville",
                    "hamilton",
                    "mississauga",
                    "kitchener",
                    "guelph",
                ],
                "preferred_regions": ["ontario", "canada", "greater toronto area", "gta"],
            },
        }

    def score_job(self, job: dict) -> tuple[int, str, dict]:
        """
        Score a job from 0-115 with grade and breakdown

        Returns:
            (score, grade, breakdown_dict)
        """
        title = job["title"].lower()
        company = job["company"].lower()
        location = (job["location"] or "").lower()

        breakdown = {}

        # 1. Seniority Match (0-30 points)
        seniority_score = self._score_seniority(title)
        breakdown["seniority"] = seniority_score

        # 2. Domain Match (0-25 points)
        domain_score = self._score_domain(title, company)
        breakdown["domain"] = domain_score

        # 3. Role Type Match (0-20 points)
        role_score = self._score_role_type(title)
        breakdown["role_type"] = role_score

        # 4. Location Match (0-15 points) - NEW!
        location_score = self._score_location(location)
        breakdown["location"] = location_score

        # 5. Company Stage Match (0-15 points) - Limited info available
        stage_score = self._score_company_stage(company)
        breakdown["company_stage"] = stage_score

        # 6. Technical Keywords (0-10 points)
        tech_score = self._score_technical_keywords(title, company)
        breakdown["technical"] = tech_score

        # Total score (max 115)
        total_score = sum(breakdown.values())

        # Grade
        grade = self._calculate_grade(total_score)

        return total_score, grade, breakdown

    def _score_seniority(self, title: str) -> int:
        """Score based on seniority level (0-30)"""
        # VP/C-level: 30 points
        if any(
            keyword in title
            for keyword in ["vp ", "vice president", "chief", "cto", "cpo", "head of"]
        ):
            return 30

        # Director/Executive: 25 points
        if any(keyword in title for keyword in ["director", "executive director"]):
            return 25

        # Senior Manager/Principal: 15 points
        if any(keyword in title for keyword in ["senior manager", "principal", "staff"]):
            return 15

        # Manager/Lead: 10 points
        if any(keyword in title for keyword in ["manager", "lead", "leadership"]):
            return 10

        # IC roles: 0 points
        return 0

    def _score_domain(self, title: str, company: str) -> int:
        """Score based on domain match (0-25)"""
        text = f"{title} {company}"

        # Hardware/Robotics/Automation: 25 points
        hardware_keywords = [
            "robotics",
            "automation",
            "hardware",
            "iot",
            "mechatronics",
            "embedded",
        ]
        if any(kw in text for kw in hardware_keywords):
            return 25

        # MedTech: 20 points
        medtech_keywords = ["medtech", "medical device", "healthcare", "pharma"]
        if any(kw in text for kw in medtech_keywords):
            return 20

        # Physical product: 15 points
        physical_keywords = ["manufacturing", "supply chain", "industrial", "mechanical"]
        if any(kw in text for kw in physical_keywords):
            return 15

        # Generic engineering: 10 points
        if "engineering" in text:
            return 10

        return 5  # Default for product roles

    def _score_role_type(self, title: str) -> int:
        """Score based on role type (0-20)"""
        # Engineering leadership: 20 points
        if "engineering" in title and any(
            kw in title for kw in ["vp", "director", "head", "chief", "executive"]
        ):
            return 20

        # Product + Engineering: 18 points
        if "product" in title and "engineering" in title:
            return 18

        # Hardware Product: 15 points
        if "product" in title and any(kw in title for kw in ["hardware", "technical", "platform"]):
            return 15

        # Engineering Manager: 12 points
        if "engineering" in title and "manager" in title:
            return 12

        # Product leadership: 10 points
        if "product" in title and any(kw in title for kw in ["vp", "director", "head", "chief"]):
            return 10

        # Generic PM: 5 points
        if "product" in title or "program" in title:
            return 5

        return 0

    def _score_company_stage(self, company: str) -> int:
        """Score based on company stage (0-15) - Limited info"""
        # Note: We don't have much company data, so this is basic
        # Could be enhanced with company research later
        return 10  # Default neutral score

    def _score_location(self, location: str) -> int:
        """
        Score based on location match (0-15 points)

        Scoring:
        - Remote: 15 points (hard requirement met)
        - Hybrid + Ontario: 15 points (hard requirement met)
        - Preferred Ontario cities: 12 points (acceptable if hybrid)
        - Broader Canada: 8 points (possible)
        - US/Other: 0 points (not acceptable unless remote)
        """
        if not location:
            return 0

        location_lower = location.lower()
        prefs = self.profile["location_preferences"]

        # Check for remote (15 points - perfect match)
        if any(kw in location_lower for kw in prefs["remote_keywords"]):
            return 15

        # Check for hybrid (need to also check if in Ontario)
        is_hybrid = any(kw in location_lower for kw in prefs["hybrid_keywords"])

        # Check for preferred cities (Toronto, Waterloo, Burlington, etc.)
        in_preferred_city = any(city in location_lower for city in prefs["preferred_cities"])

        # Check for preferred regions (Ontario, Canada)
        in_preferred_region = any(region in location_lower for region in prefs["preferred_regions"])

        # Scoring logic
        if is_hybrid and (in_preferred_city or in_preferred_region):
            return 15  # Hybrid in Ontario - perfect
        elif in_preferred_city:
            return 12  # Preferred city (might be on-site, but acceptable location)
        elif in_preferred_region:
            return 8  # Broader Canada/Ontario
        else:
            return 0  # Not in preferred locations

    def _score_technical_keywords(self, title: str, company: str) -> int:
        """Score based on technical keyword matches (0-10)"""
        text = f"{title} {company}"
        score = 0

        # Strong technical matches (2 points each, max 10)
        tech_keywords = [
            "robotics",
            "automation",
            "iot",
            "hardware",
            "embedded",
            "firmware",
            "mechanical",
            "mechatronics",
            "manufacturing",
            "supply chain",
            "dfm",
            "industrial",
            "ml",
            "ai",
        ]

        for keyword in tech_keywords:
            if keyword in text:
                score += 2
                if score >= 10:
                    break

        return min(score, 10)

    def _calculate_grade(self, score: int) -> str:
        """
        Convert score to letter grade (out of 115 total)

        Thresholds (percentage of max):
        - A: 85%+ (98+)
        - B: 70%+ (80+)
        - C: 55%+ (63+)
        - D: 40%+ (46+)
        - F: <40% (<46)
        """
        if score >= 98:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 63:
            return "C"
        elif score >= 46:
            return "D"
        else:
            return "F"

    def score_all_jobs(self, limit: int = 100):
        """Score all recent jobs and update database"""
        jobs = self.db.get_recent_jobs(limit=limit)

        scored_jobs = []

        for job in jobs:
            score, grade, breakdown = self.score_job(job)

            # Update job with score
            job_id = job["id"]
            self.db.update_job_score(job_id, score, grade, json.dumps(breakdown))

            scored_jobs.append(
                {
                    "id": job_id,
                    "title": job["title"],
                    "company": job["company"],
                    "score": score,
                    "grade": grade,
                    "breakdown": breakdown,
                }
            )

        # Sort by score
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)

        return scored_jobs


def main():
    """CLI entry point"""
    scorer = JobScorer()

    print("Scoring jobs against Wesley van Ooyen's profile...\n")

    scored_jobs = scorer.score_all_jobs()

    print(f"✓ Scored {len(scored_jobs)} jobs\n")
    print("=" * 80)
    print(f"{'GRADE':<8} {'SCORE':<8} {'TITLE':<40} {'COMPANY':<20}")
    print("=" * 80)

    for job in scored_jobs[:20]:  # Show top 20
        title = job["title"][:37] + "..." if len(job["title"]) > 40 else job["title"]
        company = job["company"][:17] + "..." if len(job["company"]) > 20 else job["company"]

        print(f"{job['grade']:<8} {job['score']:<8} {title:<40} {company:<20}")

    print("=" * 80)

    # Grade distribution
    grade_counts = {}
    for job in scored_jobs:
        grade = job["grade"]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    print("\nGrade Distribution:")
    for grade in ["A", "B", "C", "D", "F"]:
        count = grade_counts.get(grade, 0)
        print(f"  {grade}: {count} jobs")

    print("\nTop 5 matches:")
    for i, job in enumerate(scored_jobs[:5], 1):
        print(f"\n{i}. {job['title']} at {job['company']}")
        print(f"   Score: {job['score']}/100 (Grade {job['grade']})")
        print(f"   Breakdown: {job['breakdown']}")


if __name__ == "__main__":
    main()
