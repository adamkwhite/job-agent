"""
Job filtering module for keyword-based job matching
"""

import json
import re


class JobFilter:
    """Filter jobs based on include/exclude keywords"""

    def __init__(self, config_path: str = "config/filter-keywords.json"):
        with open(config_path) as f:
            self.config = json.load(f)

        self.include_keywords = [kw.lower() for kw in self.config.get("include_keywords", [])]
        self.exclude_keywords = [kw.lower() for kw in self.config.get("exclude_keywords", [])]
        self.company_include = [kw.lower() for kw in self.config.get("company_include", [])]
        self.company_exclude = [kw.lower() for kw in self.config.get("company_exclude", [])]

    def filter_job(self, job: dict) -> tuple[bool, list[str], str]:
        """
        Filter a job based on keywords

        Args:
            job: Job dictionary with title, company, description, etc.

        Returns:
            Tuple of (should_include, matched_keywords, reason)
        """
        # Combine searchable fields
        searchable_text = self._get_searchable_text(job)

        # Check exclude keywords first (high priority)
        exclude_matches = self._find_matches(searchable_text, self.exclude_keywords)
        if exclude_matches:
            return False, exclude_matches, f"Excluded due to keywords: {', '.join(exclude_matches)}"

        # Check company exclusions
        company = job.get("company", "").lower()
        company_exclude_matches = self._find_matches(company, self.company_exclude)
        if company_exclude_matches:
            return (
                False,
                company_exclude_matches,
                f"Excluded due to company keywords: {', '.join(company_exclude_matches)}",
            )

        # Check include keywords
        include_matches = self._find_matches(searchable_text, self.include_keywords)

        if not include_matches:
            return False, [], "No matching include keywords found"

        # Check company include keywords (bonus points, not required)
        company_include_matches = self._find_matches(company, self.company_include)

        all_matches = include_matches + company_include_matches

        return True, all_matches, f"Matched keywords: {', '.join(all_matches)}"

    def filter_jobs(self, jobs: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filter a list of jobs

        Args:
            jobs: List of job dictionaries

        Returns:
            Tuple of (included_jobs, excluded_jobs)
        """
        included = []
        excluded = []

        for job in jobs:
            should_include, matched_keywords, reason = self.filter_job(job)

            # Add filtering metadata
            job["filter_result"] = {
                "included": should_include,
                "keywords_matched": matched_keywords,
                "reason": reason,
            }

            if should_include:
                job["keywords_matched"] = matched_keywords
                included.append(job)
            else:
                excluded.append(job)

        return included, excluded

    def _get_searchable_text(self, job: dict) -> str:
        """Combine all searchable job fields into one string"""
        fields = [
            job.get("title", ""),
            job.get("company", ""),
            job.get("description", ""),
            job.get("location", ""),
            job.get("job_type", ""),
        ]

        return " ".join(fields).lower()

    def _find_matches(self, text: str, keywords: list[str]) -> list[str]:
        """Find all matching keywords in text"""
        matches = []

        for keyword in keywords:
            # Use word boundary matching for more accurate results
            # This prevents "pm" from matching "development" etc.
            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, text, re.IGNORECASE):
                matches.append(keyword)

        return matches

    def is_leadership_role(self, title: str) -> bool:
        """Check if job title is a leadership role"""
        leadership_keywords = [
            "director",
            "vp",
            "vice president",
            "head of",
            "chief",
            "manager",
            "lead",
            "principal",
            "senior manager",
        ]
        title_lower = (title or "").lower()
        return any(kw in title_lower for kw in leadership_keywords)

    def get_stats(self) -> dict:
        """Get filter configuration stats"""
        return {
            "include_keywords_count": len(self.include_keywords),
            "exclude_keywords_count": len(self.exclude_keywords),
            "company_include_count": len(self.company_include),
            "company_exclude_count": len(self.company_exclude),
            "include_keywords": self.include_keywords,
            "exclude_keywords": self.exclude_keywords,
        }


class SmartJobRanker:
    """
    Optional: Rank jobs based on keyword matches and other criteria
    Useful for V2 when you want to prioritize notifications
    """

    def __init__(self, config_path: str = "config/filter-keywords.json"):
        self.filter = JobFilter(config_path)

    def rank_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        Rank jobs by relevance score

        Scoring criteria:
        - Number of matching keywords (higher = better)
        - Company include matches (bonus points)
        - Job type preference (full-time > contract > part-time)
        - Location preference (local > remote > other)
        """
        scored_jobs = []

        for job in jobs:
            score = 0

            # Base score from keyword matches
            matched_keywords = job.get("keywords_matched", [])
            score += len(matched_keywords) * 10

            # Company bonus
            company = job.get("company", "").lower()
            company_matches = self.filter._find_matches(company, self.filter.company_include)
            score += len(company_matches) * 20

            # Job type bonus
            job_type = job.get("job_type", "").lower()
            if "full-time" in job_type or "full time" in job_type:
                score += 15
            elif "contract" in job_type:
                score += 10

            # Remote bonus
            if "remote" in job.get("location", "").lower():
                score += 10

            job["relevance_score"] = score
            scored_jobs.append(job)

        # Sort by score (highest first)
        scored_jobs.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored_jobs


if __name__ == "__main__":
    # Test the filter
    job_filter = JobFilter()
    print("Job filter initialized successfully")
    print("Stats:", job_filter.get_stats())
