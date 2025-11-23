"""
Shared scoring utilities used by both JobScorer and ProfileScorer
"""


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
