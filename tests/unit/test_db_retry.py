"""Tests for shared database utilities (retry, store, score)"""

from unittest.mock import MagicMock

import pytest

from utils.db_retry import retry_db_operation, score_single_job, store_single_job


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


class TestStoreSingleJob:
    """Tests for the shared store_single_job function"""

    def test_stores_successfully(self) -> None:
        db = MagicMock()
        db.add_job.return_value = 42
        stats: dict[str, int] = {"jobs_stored": 0}

        result = store_single_job(db, "Test Job Title", {"title": "Test"}, stats)

        assert result == 42
        assert stats["jobs_stored"] == 1

    def test_duplicate_returns_none(self) -> None:
        db = MagicMock()
        db.add_job.return_value = None
        stats: dict[str, int] = {"jobs_stored": 0}

        result = store_single_job(db, "Duplicate Job", {"title": "Dup"}, stats)

        assert result is None
        assert stats["jobs_stored"] == 0

    def test_unique_constraint_error(self) -> None:
        db = MagicMock()
        db.add_job.side_effect = Exception("UNIQUE constraint failed")
        stats: dict[str, int] = {"jobs_stored": 0}

        result = store_single_job(db, "Constraint Job", {}, stats)

        assert result is None
        assert stats["jobs_stored"] == 0

    def test_generic_db_error(self) -> None:
        db = MagicMock()
        db.add_job.side_effect = Exception("disk full")
        stats: dict[str, int] = {"jobs_stored": 0}

        result = store_single_job(db, "Error Job", {}, stats)

        assert result is None
        assert stats["jobs_stored"] == 0


class TestScoreSingleJob:
    """Tests for the shared score_single_job function"""

    def test_scores_and_records(self) -> None:
        scorer = MagicMock()
        scorer.score_job_for_all.return_value = {"adam": (80, "B"), "wes": (90, "A")}
        stats: dict[str, object] = {"jobs_scored": 0, "profile_scores": {}}

        score_single_job(scorer, "Great Job", {}, 1, stats, 47)

        assert stats["jobs_scored"] == 1
        scores = stats["profile_scores"]
        assert isinstance(scores, dict)
        assert len(scores["adam"]) == 1
        assert len(scores["wes"]) == 1

    def test_empty_profile_scores(self) -> None:
        """When all profiles filter a job, stats still increment."""
        scorer = MagicMock()
        scorer.score_job_for_all.return_value = {}
        stats: dict[str, object] = {"jobs_scored": 0, "profile_scores": {}}

        score_single_job(scorer, "Filtered Job", {}, 1, stats, 47)

        assert stats["jobs_scored"] == 1
        assert stats["profile_scores"] == {}

    def test_scoring_exception(self) -> None:
        """Scoring exceptions are caught and don't crash."""
        scorer = MagicMock()
        scorer.score_job_for_all.side_effect = RuntimeError("scorer broke")
        stats: dict[str, object] = {"jobs_scored": 0, "profile_scores": {}}

        score_single_job(scorer, "Bad Job", {}, 1, stats, 47)

        assert stats["jobs_scored"] == 0

    def test_qualifying_job_printed(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Jobs at or above min_score are flagged as qualifying."""
        scorer = MagicMock()
        scorer.score_job_for_all.return_value = {"adam": (85, "A")}
        stats: dict[str, object] = {"jobs_scored": 0, "profile_scores": {}}

        score_single_job(scorer, "Great Job", {}, 1, stats, 80)

        captured = capsys.readouterr()
        assert "QUALIFYING JOB" in captured.out

    def test_below_threshold_no_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Jobs below min_score are not flagged."""
        scorer = MagicMock()
        scorer.score_job_for_all.return_value = {"adam": (40, "D")}
        stats: dict[str, object] = {"jobs_scored": 0, "profile_scores": {}}

        score_single_job(scorer, "Meh Job", {}, 1, stats, 80)

        captured = capsys.readouterr()
        assert "QUALIFYING JOB" not in captured.out
