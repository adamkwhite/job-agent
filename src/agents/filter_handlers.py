"""
Filter Handlers using Chain of Responsibility Pattern

Each handler checks one specific hard filter criterion and either:
- Blocks the job (returns False + reason)
- Passes to next handler in chain

This design makes filters:
- Independently testable
- Easy to add/remove/reorder
- Single responsibility compliant
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from utils.profile_manager import Profile

# Type alias for filter results
FilterReason = str


class FilterHandler(ABC):
    """Base class for hard filter handlers using Chain of Responsibility pattern"""

    def __init__(self, profile: Union[dict, "Profile"]):
        """
        Initialize filter handler.

        Args:
            profile: User profile containing filter configuration (dict or Profile object)
        """
        self.profile = profile

        # Handle both dict and Profile object formats
        if isinstance(profile, dict):
            # Dict format (used in tests and legacy code)
            self.hard_filters = profile.get("hard_filter_keywords", {})
            self.context_filters = profile.get("context_filters", {})
        else:
            # Profile object format (used with ProfileManager)
            self.hard_filters = profile.scoring.get("hard_filter_keywords", {})
            self.context_filters = profile.scoring.get("context_filters", {})

        self.next_handler: FilterHandler | None = None

    def set_next(self, handler: "FilterHandler") -> "FilterHandler":
        """
        Set next handler in chain.

        Args:
            handler: Next filter handler to execute

        Returns:
            The handler that was set (for chaining)
        """
        self.next_handler = handler
        return handler

    def handle(self, job: dict) -> tuple[bool, FilterReason | None]:
        """
        Execute this filter, then delegate to next handler if needed.

        Args:
            job: Job dict with at least 'title' field

        Returns:
            (should_continue, filter_reason):
                - (True, None) = passed all filters
                - (False, reason) = blocked by this or downstream filter
        """
        # Check this filter's condition
        should_block, reason = self.check(job)

        if should_block:
            return (False, reason)

        # Pass to next handler in chain
        if self.next_handler:
            return self.next_handler.handle(job)

        # End of chain, job passed all filters
        return (True, None)

    @abstractmethod
    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        """
        Check if this filter should block the job.

        Args:
            job: Job dict with at least 'title' field

        Returns:
            (True, reason) if job should be blocked
            (False, None) if job passes this filter
        """
        pass


# ============================================================================
# Concrete Filter Handlers (11 handlers)
# ============================================================================


class JuniorPositionFilter(FilterHandler):
    """FR1.1: Block junior positions"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        if "junior" in title:
            return (True, "hard_filter_junior")
        return (False, None)


class InternshipFilter(FilterHandler):
    """FR1.2: Block intern/internship positions"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        if "intern" in title or "internship" in title:
            return (True, "hard_filter_intern")
        return (False, None)


class CoordinatorFilter(FilterHandler):
    """FR1.3: Block coordinator (unless senior coordinator if configured)"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        if "coordinator" not in title:
            return (False, None)

        # Check profile exception for senior coordinators
        exceptions = self.hard_filters.get("exceptions", {})
        if exceptions.get("senior_coordinator_allowed", True) and "senior coordinator" in title:
            return (False, None)  # Allow senior coordinator

        return (True, "hard_filter_coordinator")


class AssociateFilter(FilterHandler):
    """FR1.4: Block 'Associate' unless Director/VP/Principal/Chief"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        if "associate" not in title:
            return (False, None)

        # Check whitelist: allow if senior title present
        associate_exceptions = self.context_filters.get(
            "associate_with_senior", ["director", "vp", "principal", "chief"]
        )
        if any(exception in title for exception in associate_exceptions):
            return (False, None)  # Allow if whitelisted senior title

        return (True, "hard_filter_associate_low_seniority")


class HRRoleFilter(FilterHandler):
    """FR1.5: Block HR/People Operations roles (except C-level like CPO)"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        hr_keywords = self.hard_filters.get("role_type_blocks", [])

        for keyword in hr_keywords:
            if keyword in title:
                # Exception: Chief People Officer is C-level
                exceptions = self.hard_filters.get("exceptions", {})
                c_level_overrides = exceptions.get("c_level_override", ["chief people officer"])
                if any(override in title for override in c_level_overrides):
                    return (False, None)  # Allow C-level override

                return (True, "hard_filter_hr_role")

        return (False, None)


class FinanceRoleFilter(FilterHandler):
    """FR1.6: Block Finance roles"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        finance_keywords = [
            "financ",  # Catches finance/financial
            "accounting",
            "controller",
            "treasurer",
            "cfo",
        ]

        for keyword in finance_keywords:
            if keyword in title:
                return (True, "hard_filter_finance_role")

        return (False, None)


class LegalRoleFilter(FilterHandler):
    """FR1.7: Block Legal roles"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        legal_keywords = ["legal", "counsel", "compliance"]

        for keyword in legal_keywords:
            if keyword in title:
                return (True, "hard_filter_legal_role")

        return (False, None)


class MarketingRoleFilter(FilterHandler):
    """FR1.8a: Block ALL marketing roles (no exceptions)"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()

        # Check department blocks config
        marketing_keywords = self.hard_filters.get("department_blocks", [])
        if (
            "marketing" in marketing_keywords or any("marketing" in kw for kw in marketing_keywords)
        ) and "marketing" in title:
            return (True, "hard_filter_marketing_role")

        # Additional specific marketing role blocks
        sales_marketing_blocks = self.hard_filters.get(
            "sales_marketing_blocks",
            ["sales manager", "marketing manager", "business development"],
        )
        for keyword in sales_marketing_blocks:
            if "marketing" in keyword and keyword in title:
                return (True, "hard_filter_marketing_role")

        return (False, None)


class SalesRoleFilter(FilterHandler):
    """FR1.8b: Block Sales (unless Director+ seniority)"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        sales_keywords = ["sales manager", "business development", "sales"]

        # Check if it's a sales role (not marketing)
        for keyword in sales_keywords:
            if keyword in title and "marketing" not in title:
                # Allow if Director+ level
                senior_keywords = ["director", "vp", "vice president", "chief", "head of"]
                if not any(senior in title for senior in senior_keywords):
                    return (True, "hard_filter_sales_marketing")

        return (False, None)


class AdministrativeRoleFilter(FilterHandler):
    """FR1.9: Block Administrative roles"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        admin_keywords = ["administrative", "office manager", "executive assistant", "receptionist"]

        for keyword in admin_keywords:
            if keyword in title:
                return (True, "hard_filter_administrative")

        return (False, None)


class RetailRoleFilter(FilterHandler):
    """FR1.10: Block Retail roles"""

    def check(self, job: dict) -> tuple[bool, FilterReason | None]:
        title = job.get("title", "").lower()
        retail_keywords = ["retail", "store operations", "store manager"]

        for keyword in retail_keywords:
            if keyword in title:
                return (True, "hard_filter_retail")

        return (False, None)
