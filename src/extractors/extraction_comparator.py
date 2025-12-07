"""
Extraction Comparator - Compare regex vs LLM job extraction results
"""

import logging
from datetime import datetime
from typing import Any

from src.models import OpportunityData

logger = logging.getLogger(__name__)


class ExtractionComparator:
    """Compare extraction results from different methods (regex vs LLM)"""

    def compare(
        self,
        jobs_regex: list[tuple[OpportunityData, str]],
        jobs_llm: list[tuple[OpportunityData, str]],
        company_name: str,
    ) -> dict[str, Any]:
        """Compare regex and LLM extraction results

        Args:
            jobs_regex: List of (OpportunityData, extraction_method) tuples from regex
            jobs_llm: List of (OpportunityData, extraction_method) tuples from LLM
            company_name: Company name

        Returns:
            Dictionary of comparison metrics
        """
        # Extract just the OpportunityData objects
        regex_jobs = [job for job, _ in jobs_regex]
        llm_jobs = [job for job, _ in jobs_llm]

        # Calculate metrics
        regex_with_location = sum(1 for job in regex_jobs if job.location)
        llm_with_location = sum(1 for job in llm_jobs if job.location)

        # Calculate location extraction rates
        regex_location_rate = (regex_with_location / len(regex_jobs)) if regex_jobs else 0.0
        llm_location_rate = (llm_with_location / len(llm_jobs)) if llm_jobs else 0.0

        # Find overlapping jobs (same title and company)
        overlap = self._calculate_overlap(regex_jobs, llm_jobs)

        # Calculate unique jobs
        regex_unique = len(regex_jobs) - overlap
        llm_unique = len(llm_jobs) - overlap

        # Build metrics dictionary
        metrics = {
            "company_name": company_name,
            "scrape_date": datetime.now().isoformat(),
            # Regex metrics
            "regex_jobs_found": len(regex_jobs),
            "regex_leadership_jobs": len(regex_jobs),  # All regex jobs are leadership
            "regex_with_location": regex_with_location,
            "regex_location_rate": regex_location_rate,
            # LLM metrics
            "llm_jobs_found": len(llm_jobs),
            "llm_leadership_jobs": len(llm_jobs),  # All LLM jobs are leadership
            "llm_with_location": llm_with_location,
            "llm_location_rate": llm_location_rate,
            # LLM cost (will be set by caller if available)
            "llm_api_cost": 0.0,
            # Overlap metrics
            "overlap_count": overlap,
            "regex_unique": regex_unique,
            "llm_unique": llm_unique,
        }

        # Log comparison summary
        logger.info(
            f"Extraction comparison for {company_name}: "
            f"Regex={len(regex_jobs)} jobs ({regex_location_rate:.1%} location), "
            f"LLM={len(llm_jobs)} jobs ({llm_location_rate:.1%} location), "
            f"Overlap={overlap}, Regex-only={regex_unique}, LLM-only={llm_unique}"
        )

        return metrics

    def _calculate_overlap(
        self, jobs_a: list[OpportunityData], jobs_b: list[OpportunityData]
    ) -> int:
        """Calculate number of overlapping jobs between two lists

        Jobs are considered the same if they have matching normalized titles.

        Args:
            jobs_a: First list of jobs
            jobs_b: Second list of jobs

        Returns:
            Number of overlapping jobs
        """
        # Normalize titles for comparison (lowercase, strip whitespace)
        titles_a = {self._normalize_title(job.title) for job in jobs_a if job.title}
        titles_b = {self._normalize_title(job.title) for job in jobs_b if job.title}

        # Count intersection
        return len(titles_a & titles_b)

    def _normalize_title(self, title: str | None) -> str:
        """Normalize job title for comparison

        Args:
            title: Job title

        Returns:
            Normalized title (lowercase, stripped)
        """
        if not title:
            return ""

        # Lowercase and strip whitespace
        normalized = title.lower().strip()

        # Remove common variations
        normalized = normalized.replace("  ", " ")  # Double spaces
        normalized = normalized.replace("-", " ")  # Hyphens to spaces
        normalized = normalized.replace("(", "").replace(")", "")  # Parentheses

        return normalized

    def print_comparison_table(
        self, metrics: dict[str, Any], show_location_improvement: bool = True
    ) -> None:
        """Print formatted comparison table to console

        Args:
            metrics: Comparison metrics dictionary
            show_location_improvement: Whether to highlight location rate improvements
        """
        company = metrics["company_name"]

        print(f"\n{'=' * 80}")
        print(f"EXTRACTION COMPARISON: {company}")
        print(f"{'=' * 80}")

        # Summary table
        print(f"\n{'Method':<15} {'Jobs Found':<12} {'With Location':<15} {'Location Rate':<15}")
        print("-" * 80)

        regex_rate = metrics["regex_location_rate"]
        llm_rate = metrics["llm_location_rate"]

        print(
            f"{'Regex':<15} {metrics['regex_jobs_found']:<12} "
            f"{metrics['regex_with_location']:<15} {regex_rate:>12.1%}"
        )
        print(
            f"{'LLM':<15} {metrics['llm_jobs_found']:<12} "
            f"{metrics['llm_with_location']:<15} {llm_rate:>12.1%}"
        )

        # Improvement indicator
        if show_location_improvement and llm_rate > regex_rate:
            improvement = llm_rate - regex_rate
            print(f"\n{'':>43}✅ LLM improved location extraction by {improvement:.1%}")
        elif show_location_improvement and regex_rate > llm_rate:
            decline = regex_rate - llm_rate
            print(f"\n{'':>43}⚠️  LLM location rate declined by {decline:.1%}")

        # Overlap analysis
        print(f"\n{'Overlap Analysis':<30}")
        print("-" * 80)
        print(f"  Both methods:        {metrics['overlap_count']} jobs")
        print(f"  Regex only:          {metrics['regex_unique']} jobs")
        print(f"  LLM only:            {metrics['llm_unique']} jobs")

        # Cost if available
        if metrics.get("llm_api_cost", 0) > 0:
            print(f"\n{'LLM API Cost':<30} ${metrics['llm_api_cost']:.4f}")

        print(f"\n{'=' * 80}\n")
