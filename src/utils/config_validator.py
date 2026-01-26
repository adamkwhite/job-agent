"""
Configuration Validation for Profile JSON Files

Validates that profile JSON files contain all required keys and warns about
missing optional keys. This helps catch configuration errors early.

Required keys (raise ValueError if missing):
- id: Profile identifier
- name: User's full name
- email: User's email address
- scoring.target_seniority: List of target seniority levels
- scoring.domain_keywords: List of domain keywords for scoring

Optional keys (log warning if missing):
- hard_filter_keywords: Keywords for filtering jobs
- context_filters: Context-specific filtering rules
- digest.min_grade: Minimum grade for digest inclusion
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def check_required_keys(profile: Any) -> None:
    """
    Validate that profile has all required configuration keys.

    Raises:
        ValueError: If any required key is missing with clear error message
    """
    missing_keys: list[str] = []

    # Check top-level required keys (use getattr to handle mocks)
    if not getattr(profile, "id", None):
        missing_keys.append("id")
    if not getattr(profile, "name", None):
        missing_keys.append("name")
    if not getattr(profile, "email", None):
        missing_keys.append("email")

    # Check required scoring keys
    scoring = getattr(profile, "scoring", None)
    if not scoring:
        missing_keys.append("scoring")
    else:
        # Check for target_seniority OR seniority_levels (legacy format)
        has_target_seniority = bool(scoring.get("target_seniority"))
        has_seniority_levels = bool(scoring.get("seniority_levels"))
        if not (has_target_seniority or has_seniority_levels):
            missing_keys.append("scoring.target_seniority")

        # Check for domain_keywords (required)
        domain_kw = scoring.get("domain_keywords")
        # Accept both list format and dict format
        if not domain_kw or (isinstance(domain_kw, (list, dict)) and len(domain_kw) == 0):
            missing_keys.append("scoring.domain_keywords")

    if missing_keys:
        raise ValueError(f"Profile configuration missing required keys: {', '.join(missing_keys)}")


def validate_profile_config(profile: Any) -> list[str]:
    """
    Validate profile configuration and return list of warnings.

    Checks for optional keys that are commonly used but may be missing.
    Does not raise exceptions, only returns warnings.

    Args:
        profile: Profile object to validate

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings: list[str] = []

    # Check optional scoring configuration (use getattr to handle mocks)
    scoring = getattr(profile, "scoring", None)
    if not scoring:
        # Already caught by check_required_keys, skip optional checks
        return warnings

    profile_id = getattr(profile, "id", "unknown")

    # Check for hard_filter_keywords
    if "hard_filter_keywords" not in scoring:
        warnings.append(
            f"Profile '{profile_id}' missing optional key 'scoring.hard_filter_keywords' - "
            "no keyword-based job filtering will be applied"
        )

    # Check for context_filters
    if "context_filters" not in scoring:
        warnings.append(
            f"Profile '{profile_id}' missing optional key 'scoring.context_filters' - "
            "no context-based filtering rules will be applied"
        )

    # Check for digest settings
    digest_min_grade = getattr(profile, "digest_min_grade", None)
    if not digest_min_grade:
        warnings.append(f"Profile '{profile_id}' missing digest.min_grade - defaulting to 'C'")

    # Check for role_types
    if "role_types" not in scoring:
        warnings.append(
            f"Profile '{profile_id}' missing optional key 'scoring.role_types' - "
            "role type scoring will use defaults"
        )

    # Check for location_preferences
    if "location_preferences" not in scoring:
        warnings.append(
            f"Profile '{profile_id}' missing optional key 'scoring.location_preferences' - "
            "location scoring will be limited"
        )

    return warnings
