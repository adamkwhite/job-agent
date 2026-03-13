"""Shared database utilities for scraper modules.

Provides retry logic and common store/score operations used across
multiple job scrapers (RLS, TestDevJobs, etc.).
"""

import time
from collections.abc import Callable
from typing import Any, Protocol


class _JobStore(Protocol):
    """Protocol for objects that can store jobs (e.g., JobDatabase)."""

    def add_job(self, job_dict: dict[str, Any]) -> int | None: ...


class _MultiScorer(Protocol):
    """Protocol for objects that can score jobs for all profiles."""

    def score_job_for_all(
        self, job_dict: dict[str, Any], job_id: int
    ) -> dict[str, tuple[int, str]]: ...


def retry_db_operation[T](
    operation: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 0.1,
) -> T:
    """Retry database operations with exponential backoff for lock errors.

    Args:
        operation: Callable that performs the database operation
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 0.1)

    Returns:
        Result from the operation

    Raises:
        Exception: Re-raises the last exception if all retries are exhausted,
            or immediately for non-lock errors.
    """
    delay = initial_delay
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            last_exc = e
            error_msg = str(e).lower()
            if (
                "database is locked" in error_msg or "locked" in error_msg
            ) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise

    # pragma: no cover — loop always raises or returns before reaching here
    assert last_exc is not None  # noqa: S101
    raise last_exc


def store_single_job(
    database: _JobStore,
    job_title: str,
    job_dict: dict[str, Any],
    stats: dict[str, Any],
) -> int | None:
    """Store a single job in the database with retry and dedup handling.

    Returns job_id if stored successfully, None if duplicate or error.
    Updates stats["jobs_stored"] on success.
    """
    try:
        job_id: int | None = retry_db_operation(lambda: database.add_job(job_dict))
        if job_id is None:
            print(f"   ⊙ Duplicate: {job_title[:60]}")
            return None
        stats["jobs_stored"] += 1
        return job_id
    except Exception as e:
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            print(f"   ⊙ Duplicate: {job_title[:60]}")
        else:
            print(f"   ✗ Error storing job: {e}")
        return None


def score_single_job(
    multi_scorer: _MultiScorer,
    job_title: str,
    job_dict: dict[str, Any],
    job_id: int,
    stats: dict[str, Any],
    min_score: int,
) -> None:
    """Score a single job for all profiles with retry.

    Updates stats["jobs_scored"] and stats["profile_scores"] on success.
    """
    try:
        profile_scores: dict[str, tuple[int, str]] = retry_db_operation(
            lambda: multi_scorer.score_job_for_all(job_dict, job_id)
        )
        stats["jobs_scored"] += 1

        if not profile_scores:
            print(f"   ⊘ {job_title[:50]}")
            print("     All profiles filtered this job")
            return

        for profile_id, (score, grade) in profile_scores.items():
            if profile_id not in stats["profile_scores"]:
                stats["profile_scores"][profile_id] = []
            stats["profile_scores"][profile_id].append((score, grade))

        scores_str = ", ".join(f"{pid}:{s}/{g}" for pid, (s, g) in profile_scores.items())
        print(f"   ✓ {job_title[:50]}")
        print(f"     Scores: {scores_str}")

        max_score = max(score for score, _ in profile_scores.values())
        if max_score >= min_score:
            print(f"     🎯 QUALIFYING JOB (max score: {max_score})")

    except Exception as e:
        print(f"   ✗ Error scoring job: {e}")


def print_profile_score_summary(
    stats: dict[str, object],
) -> None:
    """Print per-profile scoring breakdown from stats["profile_scores"].

    Shared by RLS, Ministry, TestDevJobs scrapers.
    """
    profile_scores = stats.get("profile_scores")
    if not profile_scores or not isinstance(profile_scores, dict):
        return

    print("Scores by profile:")
    for profile_id, scores in profile_scores.items():
        if not scores:
            continue
        grade_counts: dict[str, int] = {}
        for _score, grade in scores:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        total = len(scores)
        avg_score = sum(s for s, _ in scores) / total if total > 0 else 0
        print(f"  {profile_id}:")
        print(f"    Total: {total} jobs")
        print(f"    Avg score: {avg_score:.1f}")
        print(f"    Grades: {', '.join(f'{g}={c}' for g, c in sorted(grade_counts.items()))}")
