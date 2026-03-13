"""Tests for shared database retry utility"""

import pytest

from utils.db_retry import retry_db_operation


class TestRetryDbOperation:
    """Tests for database retry logic"""

    def test_succeeds_first_try(self) -> None:
        result = retry_db_operation(lambda: 42)
        assert result == 42

    def test_retries_on_lock_error(self) -> None:
        call_count = 0

        def flaky_op() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("database is locked")
            return 99

        result = retry_db_operation(flaky_op, initial_delay=0.001)
        assert result == 99
        assert call_count == 3

    def test_raises_non_lock_errors(self) -> None:
        with pytest.raises(ValueError, match="bad data"):
            retry_db_operation(lambda: (_ for _ in ()).throw(ValueError("bad data")))

    def test_raises_lock_error_after_max_retries(self) -> None:
        """All retries exhausted on persistent lock errors."""
        with pytest.raises(Exception, match="database is locked"):
            retry_db_operation(
                lambda: (_ for _ in ()).throw(Exception("database is locked")),
                max_retries=2,
                initial_delay=0.001,
            )
