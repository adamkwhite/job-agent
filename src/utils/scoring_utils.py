"""
Shared scoring utilities used by both JobScorer and ProfileScorer

This module provides pure utility functions for scoring calculations.
It has no external dependencies (except stdlib and score_thresholds) and serves as the foundation layer.

Note: classify_and_score_company() has been moved to company_classifier.py to eliminate circular imports.
"""

import logging

from utils.score_thresholds import Grade
from utils.score_thresholds import calculate_grade as _calculate_grade

logger = logging.getLogger(__name__)


def calculate_grade(score: int) -> str:
    """
    Convert score to letter grade (out of 100 total)

    DEPRECATED: This function is kept for backwards compatibility.
    Use utils.score_thresholds.calculate_grade() directly instead.

    Thresholds (percentage of max):
    - A: 85%+ (85+)
    - B: 70%+ (70+)
    - C: 55%+ (55+)
    - D: 40%+ (40+)
    - F: <40% (<40)
    """
    return _calculate_grade(score)


# Grade thresholds for filtering
# DEPRECATED: Use Grade enum from score_thresholds module instead
GRADE_THRESHOLDS = {
    "A": Grade.A.value,
    "B": Grade.B.value,
    "C": Grade.C.value,
    "D": Grade.D.value,
    "F": Grade.F.value,
}


def score_meets_grade(score: int, min_grade: str) -> bool:
    """
    Check if a score meets or exceeds the minimum grade threshold

    DEPRECATED: This function is kept for backwards compatibility.
    Use utils.score_thresholds.score_meets_grade() directly instead.
    """
    threshold = GRADE_THRESHOLDS.get(min_grade, 0)
    return score >= threshold
