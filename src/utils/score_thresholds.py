"""
Centralized grade threshold definitions using enum for type safety.

This module provides a single source of truth for all score-to-grade conversions
throughout the codebase. Use the Grade enum to avoid magic numbers.

Usage:
    from utils.score_thresholds import Grade, calculate_grade, score_meets_grade

    # Check if score meets B grade
    if score >= Grade.B.value:
        send_notification()

    # Calculate grade from score
    grade = calculate_grade(85)  # Returns "A"

    # Check if score meets minimum grade
    if score_meets_grade(72, "B"):
        include_in_digest()
"""

from enum import Enum


class Grade(Enum):
    """
    Letter grade thresholds for job scoring (0-110 point scale).

    These values represent the minimum score required for each grade.
    The base scoring system is 0-100 with up to +10 bonus points possible.

    Grade Ranges:
    - A: 85-110 (Perfect match)
    - B: 70-84 (Excellent match)
    - C: 55-69 (Good match)
    - D: 40-54 (Lower match)
    - F: 0-39 (Minimal match)

    Notification Policy:
    - A/B grades (70+): Immediate SMS/email notifications + weekly digest
    - C: grade (55-69): Weekly digest only
    - D/F grades (<55): Not included in notifications or digests
    """

    A = 85
    B = 70
    C = 55
    D = 40
    F = 0


def calculate_grade(score: int) -> str:
    """
    Convert numeric score to letter grade.

    Args:
        score: Numeric score (typically 0-110, but handles any integer)

    Returns:
        Letter grade as string ("A", "B", "C", "D", or "F")

    Examples:
        >>> calculate_grade(85)
        'A'
        >>> calculate_grade(84)
        'B'
        >>> calculate_grade(39)
        'F'
    """
    if score >= Grade.A.value:
        return "A"
    elif score >= Grade.B.value:
        return "B"
    elif score >= Grade.C.value:
        return "C"
    elif score >= Grade.D.value:
        return "D"
    else:
        return "F"


def score_meets_grade(score: int, min_grade: str) -> bool:
    """
    Check if a score meets or exceeds a minimum grade threshold.

    Args:
        score: Numeric score to check
        min_grade: Minimum grade required (e.g., "B", "C")

    Returns:
        True if score meets or exceeds the grade threshold

    Examples:
        >>> score_meets_grade(72, "B")
        True
        >>> score_meets_grade(68, "B")
        False
        >>> score_meets_grade(55, "C")
        True

    Raises:
        KeyError: If min_grade is not a valid grade letter
    """
    return score >= Grade[min_grade].value


def get_grade_threshold(grade: str) -> int:
    """
    Get the numeric threshold for a specific grade.

    Args:
        grade: Grade letter (e.g., "A", "B", "C")

    Returns:
        Minimum score required for that grade

    Examples:
        >>> get_grade_threshold("B")
        70
        >>> get_grade_threshold("A")
        85

    Raises:
        KeyError: If grade is not a valid grade letter
    """
    return Grade[grade].value
