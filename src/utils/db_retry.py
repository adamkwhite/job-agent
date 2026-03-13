"""Shared database retry utility for scraper modules."""

import time
from collections.abc import Callable


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
