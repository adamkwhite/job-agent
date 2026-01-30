"""
Job Filter Pipeline - Apply hard filters before scoring

Implements multi-stage filtering to prevent irrelevant jobs from reaching the digest:
- Stage 1: Hard filters (junior, HR, finance, etc.) - BEFORE scoring
- Stage 2: Context-aware filters (software engineering, contract) - AFTER scoring
- Stage 3: Stale job validation - BEFORE digest

This module implements Stage 1: Hard Filters (FR1 from PRD)

Stage 1 uses Chain of Responsibility pattern for better testability and maintainability.
"""

from typing import Literal

from agents.filter_handlers import (
    AdministrativeRoleFilter,
    AssociateFilter,
    CoordinatorFilter,
    FilterHandler,
    FinanceRoleFilter,
    HRRoleFilter,
    InternshipFilter,
    JuniorPositionFilter,
    LegalRoleFilter,
    MarketingRoleFilter,
    RetailRoleFilter,
    SalesRoleFilter,
)

# All possible filter reasons for type safety
FilterReason = Literal[
    "hard_filter_junior",
    "hard_filter_intern",
    "hard_filter_coordinator",
    "hard_filter_associate_low_seniority",
    "hard_filter_hr_role",
    "hard_filter_finance_role",
    "hard_filter_legal_role",
    "hard_filter_sales_marketing",
    "hard_filter_marketing_role",
    "hard_filter_administrative",
    "hard_filter_retail",
    "context_filter_software_engineering",
    "context_filter_contract_low_seniority",
    "stale_job_age",
    "stale_no_longer_accepting_applications",
]


class JobFilterPipeline:
    """
    Apply filtering rules to jobs before and after scoring.

    Usage:
        profile = load_profile("wes")
        pipeline = JobFilterPipeline(profile)

        # Before scoring
        should_score, reason = pipeline.apply_hard_filters(job)
        if not should_score:
            print(f"Job blocked: {reason}")
            continue

        # ... scoring happens ...

        # After scoring
        should_keep, reason = pipeline.apply_context_filters(job, score)
    """

    def __init__(self, profile: dict):
        """
        Initialize filter pipeline with profile configuration.

        Args:
            profile: User profile dict containing:
                - hard_filter_keywords: Seniority/role/department blocks
                - context_filters: Associate exceptions, software engineering rules
        """
        self.profile = profile
        self.hard_filters = profile.get("hard_filter_keywords") or {}
        self.context_filters = profile.get("context_filters") or {}

    def _build_filter_chain(self) -> FilterHandler:
        """
        Construct chain of filter handlers in priority order.

        Returns:
            Head of the filter chain (first handler)
        """
        # Create handlers in priority order (handlers accept both dict and Profile)
        junior = JuniorPositionFilter(self.profile)
        intern = InternshipFilter(self.profile)
        coordinator = CoordinatorFilter(self.profile)
        associate = AssociateFilter(self.profile)
        hr = HRRoleFilter(self.profile)
        finance = FinanceRoleFilter(self.profile)
        legal = LegalRoleFilter(self.profile)
        marketing = MarketingRoleFilter(self.profile)
        sales = SalesRoleFilter(self.profile)
        admin = AdministrativeRoleFilter(self.profile)
        retail = RetailRoleFilter(self.profile)

        # Chain handlers together
        junior.set_next(intern).set_next(coordinator).set_next(associate).set_next(hr).set_next(
            finance
        ).set_next(legal).set_next(marketing).set_next(sales).set_next(admin).set_next(retail)

        return junior  # Return head of chain

    def apply_hard_filters(self, job: dict) -> tuple[bool, FilterReason | None]:
        """
        Stage 1: Apply hard filters BEFORE scoring using Chain of Responsibility pattern.

        These filters block jobs that are clearly not relevant regardless of scoring.
        Execution time: <10ms per job.

        Args:
            job: Job dict with at least 'title' field

        Returns:
            (should_continue, filter_reason):
                - (True, None) = passed filters, continue to scoring
                - (False, "reason") = blocked, don't score this job

        Examples:
            >>> pipeline.apply_hard_filters({"title": "Junior Engineer"})
            (False, "hard_filter_junior")

            >>> pipeline.apply_hard_filters({"title": "VP Engineering"})
            (True, None)
        """
        # Build filter chain and execute
        chain = self._build_filter_chain()
        return chain.handle(job)

    def apply_context_filters(
        self, job: dict, _score: int, score_breakdown: dict
    ) -> tuple[bool, FilterReason | None]:
        """
        Stage 2: Apply context-aware filters AFTER scoring.

        These filters use scoring information to make smarter decisions:
        - Software engineering with hardware/product context
        - Contract positions based on seniority score

        Args:
            job: Job dict with 'title' field
            score: Total job fit score (0-115)
            score_breakdown: Dict with category scores (e.g., {"seniority": 25})

        Returns:
            (should_keep, filter_reason):
                - (True, None) = passed filters, keep job
                - (False, "reason") = blocked after scoring

        Examples:
            >>> pipeline.apply_context_filters(
            ...     {"title": "Director of Software Engineering"},
            ...     85,
            ...     {"seniority": 25}
            ... )
            (False, "context_filter_software_engineering")
        """
        title = job.get("title", "").lower()

        # FR2.2: Software engineering context check
        # Block if: "software engineering" AND no hardware/product keywords
        if "software" in title and "engineering" in title:
            exceptions = self.context_filters.get(
                "software_engineering_exceptions", ["hardware", "product"]
            )
            if not any(exception in title for exception in exceptions):
                return (False, "context_filter_software_engineering")

        # FR2.3: Contract position handling
        contract_keywords = ["contract", "contractor", "temporary", "temp", "interim"]
        is_contract = any(keyword in title for keyword in contract_keywords)

        if is_contract:
            # Get minimum seniority score for contracts (default 25 = Director)
            min_seniority = self.context_filters.get("contract_min_seniority_score", 25)
            seniority_score = score_breakdown.get("seniority", 0)

            if seniority_score < min_seniority:
                return (False, "context_filter_contract_low_seniority")

        # Passed all context filters
        return (True, None)
