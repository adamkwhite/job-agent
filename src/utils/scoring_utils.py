"""
Shared scoring utilities used by both JobScorer and ProfileScorer
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.company_classifier import CompanyClassifier

logger = logging.getLogger(__name__)


def classify_and_score_company(
    company_classifier: "CompanyClassifier",
    company_name: str,
    job_title: str,
    domain_keywords: list[str],
    role_types: dict,
    filtering_config: dict,
) -> tuple[int, dict]:
    """
    Classify company and apply filtering/boost adjustments.

    This function encapsulates the CompanyClassifier integration logic
    shared by both JobScorer and ProfileScorer.

    Args:
        company_classifier: CompanyClassifier instance
        company_name: Display name of company (original case)
        job_title: Job title to analyze
        domain_keywords: Profile domain keywords for classification
        role_types: Profile role types for filtering logic
        filtering_config: Profile filtering configuration dict

    Returns:
        tuple of (score_adjustment, classification_metadata)
        - score_adjustment: int (negative for penalty, positive for boost, 0 for none)
        - classification_metadata: dict with classification details
    """
    # Import here to avoid circular dependency
    from utils.company_classifier import should_filter_job

    # Classify company domain (software/hardware/both/unknown)
    company_classification = company_classifier.classify_company(
        company_name=company_name,
        job_title=job_title,
        domain_keywords=domain_keywords,
    )

    # Store classification metadata for transparency
    classification_metadata = {
        "company_type": company_classification.type,
        "confidence": company_classification.confidence,
        "signals": company_classification.signals,
        "source": company_classification.source,
    }

    logger.debug(
        f"Company classification for '{company_name}': "
        f"type={company_classification.type}, confidence={company_classification.confidence:.2f}"
    )

    # Get filtering config values (with defaults)
    aggression_level = filtering_config.get("aggression_level", "moderate")
    software_penalty = filtering_config.get("software_company_penalty", -20)
    hardware_boost = filtering_config.get("hardware_company_boost", 10)

    # Build profile dict for should_filter_job
    profile_dict = {
        "role_types": role_types,
        "filtering": filtering_config,
    }

    # Check if job should be filtered
    should_filter, filter_reason = should_filter_job(
        job_title=job_title,
        company_name=company_name,
        company_classification=company_classification,
        profile=profile_dict,
        aggression_level=aggression_level,
    )

    # Apply filtering penalty or boost
    score_adjustment = 0
    if should_filter:
        score_adjustment = software_penalty
        classification_metadata["filtered"] = True
        classification_metadata["filter_reason"] = filter_reason
        logger.info(
            f"Applying software role filter to '{job_title}' at '{company_name}': "
            f"{software_penalty} points (reason: {filter_reason})"
        )
    elif company_classification.type == "hardware":
        # Hardware company boost for engineering roles
        score_adjustment = hardware_boost
        classification_metadata["filtered"] = False
        classification_metadata["filter_reason"] = filter_reason
        classification_metadata["hardware_boost_applied"] = True
        logger.info(
            f"Applying hardware company boost to '{job_title}' at '{company_name}': "
            f"+{hardware_boost} points"
        )
    else:
        classification_metadata["filtered"] = False
        classification_metadata["filter_reason"] = filter_reason
        logger.debug(
            f"No filtering adjustment for '{job_title}' at '{company_name}' "
            f"(reason: {filter_reason})"
        )

    return score_adjustment, classification_metadata


def calculate_grade(score: int) -> str:
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


# Grade thresholds for filtering
GRADE_THRESHOLDS = {
    "A": 98,
    "B": 80,
    "C": 63,
    "D": 46,
    "F": 0,
}


def score_meets_grade(score: int, min_grade: str) -> bool:
    """Check if a score meets or exceeds the minimum grade threshold"""
    threshold = GRADE_THRESHOLDS.get(min_grade, 0)
    return score >= threshold
