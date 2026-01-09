"""
Job Filter Pipeline - Apply hard filters before scoring

Implements multi-stage filtering to prevent irrelevant jobs from reaching the digest:
- Stage 1: Hard filters (junior, HR, finance, etc.) - BEFORE scoring
- Stage 2: Context-aware filters (software engineering, contract) - AFTER scoring
- Stage 3: Stale job validation - BEFORE digest

This module implements Stage 1: Hard Filters (FR1 from PRD)
"""

from typing import Literal

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
        self.hard_filters = profile.get("hard_filter_keywords", {})
        self.context_filters = profile.get("context_filters", {})

    def apply_hard_filters(self, job: dict) -> tuple[bool, FilterReason | None]:
        """
        Stage 1: Apply hard filters BEFORE scoring.

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
        title = job.get("title", "").lower()

        # FR1.1: Block junior positions
        if "junior" in title:
            return (False, "hard_filter_junior")

        # FR1.2: Block intern/internship
        if "intern" in title or "internship" in title:
            return (False, "hard_filter_intern")

        # FR1.3: Block coordinator (unless "senior coordinator")
        if "coordinator" in title:
            exceptions = self.hard_filters.get("exceptions", {})
            if exceptions.get("senior_coordinator_allowed", True):
                if "senior coordinator" not in title:
                    return (False, "hard_filter_coordinator")
            else:
                return (False, "hard_filter_coordinator")

        # FR1.4: Block "Associate" unless Director/VP/Principal/Chief
        if "associate" in title:
            associate_exceptions = self.context_filters.get(
                "associate_with_senior", ["director", "vp", "principal", "chief"]
            )
            # Check if title contains any exception keywords
            if not any(exception in title for exception in associate_exceptions):
                return (False, "hard_filter_associate_low_seniority")

        # FR1.5: Block HR/People Operations roles (except CPO)
        hr_keywords = self.hard_filters.get("role_type_blocks", [])
        for keyword in hr_keywords:
            if keyword in title:
                # Exception: Chief People Officer is C-level
                exceptions = self.hard_filters.get("exceptions", {})
                c_level_overrides = exceptions.get("c_level_override", ["chief people officer"])
                if not any(override in title for override in c_level_overrides):
                    return (False, "hard_filter_hr_role")

        # FR1.6: Block Finance roles
        finance_keywords = [
            "financ",
            "accounting",
            "controller",
            "treasurer",
            "cfo",
        ]  # "financ" catches finance/financial
        for keyword in finance_keywords:
            if keyword in title:
                return (False, "hard_filter_finance_role")

        # FR1.7: Block Legal roles
        legal_keywords = ["legal", "counsel", "compliance"]
        for keyword in legal_keywords:
            if keyword in title:
                return (False, "hard_filter_legal_role")

        # FR1.8a: Block ALL marketing roles (no exceptions)
        marketing_keywords = self.hard_filters.get("department_blocks", [])
        if (
            "marketing" in marketing_keywords or any("marketing" in kw for kw in marketing_keywords)
        ) and "marketing" in title:
            return (False, "hard_filter_marketing_role")

        # Additional specific marketing role blocks
        sales_marketing_blocks = self.hard_filters.get(
            "sales_marketing_blocks",
            ["sales manager", "marketing manager", "business development"],
        )
        for keyword in sales_marketing_blocks:
            if "marketing" in keyword and keyword in title:
                return (False, "hard_filter_marketing_role")

        # FR1.8b: Block Sales (unless Director+ at hardware company)
        # Note: Hardware company check happens in context filters (after scoring)
        sales_keywords = ["sales manager", "business development", "sales"]

        # Check if it's a sales role (not marketing)
        for keyword in sales_keywords:
            if keyword in title and "marketing" not in title:
                # Allow if Director+ level
                senior_keywords = ["director", "vp", "vice president", "chief", "head of"]
                if not any(senior in title for senior in senior_keywords):
                    return (False, "hard_filter_sales_marketing")

        # FR1.9: Block Administrative roles
        admin_keywords = ["administrative", "office manager", "executive assistant", "receptionist"]
        for keyword in admin_keywords:
            if keyword in title:
                return (False, "hard_filter_administrative")

        # FR1.10: Block Retail roles
        retail_keywords = ["retail", "store operations", "store manager"]
        for keyword in retail_keywords:
            if keyword in title:
                return (False, "hard_filter_retail")

        # Passed all hard filters
        return (True, None)

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
