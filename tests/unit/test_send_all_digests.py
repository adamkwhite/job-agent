"""
Unit tests for URL validation deduplication in send_all_digests (Issue #310)

Tests the extracted _validate_and_filter_jobs helper, the new
_prevalidate_jobs_for_all_profiles function, and the pre_validated_jobs
bypass in send_digest_to_profile.
"""

from unittest.mock import MagicMock, patch

from src.send_profile_digest import (
    _prevalidate_jobs_for_all_profiles,
    _simplify_flagged_status,
    _simplify_invalid_status,
    _update_db_validation_statuses,
    _validate_and_filter_jobs,
    send_all_digests,
    send_digest_to_profile,
)

# ── Fixtures ─────────────────────────────────────────────────────────


def _make_job(
    company="Acme",
    title="Engineer",
    link="https://example.com/job1",
    score=80,
    grade="B",
    job_hash="hash1",
    **kwargs,
):
    """Helper to build a job dict with sensible defaults."""
    job = {
        "id": kwargs.get("id", 1),
        "company": company,
        "title": title,
        "link": link,
        "fit_score": score,
        "fit_grade": grade,
        "job_hash": job_hash,
        "location": kwargs.get("location", "Remote"),
        "score_breakdown": kwargs.get("score_breakdown", "{}"),
        "received_at": kwargs.get("received_at", "2026-02-20T10:00:00"),
    }
    job.update(kwargs)
    return job


def _make_profile(profile_id="wes", name="Wes", enabled=True):
    """Helper to build a mock Profile."""
    p = MagicMock()
    p.id = profile_id
    p.name = name
    p.enabled = enabled
    p.email = f"{profile_id}@example.com"
    p.email_username = f"{profile_id}@example.com"
    p.email_app_password = "fake-password"
    p.digest_min_grade = "C"
    p.digest_min_location_score = 0
    p.scoring = {}
    p.get_target_seniority.return_value = ["senior"]
    p.get_domain_keywords.return_value = ["robotics"]
    return p


# ── _simplify_invalid_status ─────────────────────────────────────────


class TestSimplifyInvalidStatus:
    def test_stale_prefix(self):
        assert _simplify_invalid_status("stale_no_longer_accepting") == "stale"

    def test_404(self):
        assert _simplify_invalid_status("404_not_found") == "404"

    def test_connection_error(self):
        assert _simplify_invalid_status("connection_error") == "connection_error"

    def test_invalid_response(self):
        assert _simplify_invalid_status("invalid_response") == "invalid_response"

    def test_passthrough(self):
        assert _simplify_invalid_status("timeout") == "timeout"


# ── _simplify_flagged_status ─────────────────────────────────────────


class TestSimplifyFlaggedStatus:
    def test_rate_limited(self):
        assert _simplify_flagged_status("rate_limited_assumed_valid") == "rate_limited"

    def test_linkedin_prefix(self):
        assert _simplify_flagged_status("linkedin_unverifiable") == "linkedin"

    def test_generic_prefix(self):
        assert _simplify_flagged_status("generic_career_page") == "generic_page"

    def test_passthrough(self):
        assert _simplify_flagged_status("needs_review") == "needs_review"


# ── _update_db_validation_statuses ───────────────────────────────────


class TestUpdateDbValidationStatuses:
    def test_updates_all_categories(self):
        db = MagicMock()
        valid = [_make_job(job_hash="v1")]
        flagged = [_make_job(job_hash="f1", validation_reason="linkedin_unverifiable")]
        invalid = [_make_job(job_hash="i1", validation_reason="404_not_found")]

        _update_db_validation_statuses(db, valid, flagged, invalid)

        db.update_url_validation.assert_any_call("i1", "404")
        db.update_url_validation.assert_any_call("v1", "valid")
        db.update_url_validation.assert_any_call("f1", "linkedin")
        assert db.update_url_validation.call_count == 3

    def test_skips_jobs_without_hash(self):
        db = MagicMock()
        valid = [_make_job(job_hash=None)]
        _update_db_validation_statuses(db, valid, [], [])
        db.update_url_validation.assert_not_called()


# ── _validate_and_filter_jobs ────────────────────────────────────────


class TestValidateAndFilterJobs:
    @patch("src.send_profile_digest.JobValidator")
    def test_empty_input_returns_empty(self, mock_validator_cls):
        db = MagicMock()
        result = _validate_and_filter_jobs([], db)
        assert result == []
        mock_validator_cls.assert_not_called()

    def test_valid_jobs_pass_through(self):
        db = MagicMock()
        jobs = [_make_job(link="https://example.com/job1")]

        validator = MagicMock()
        validator.filter_valid_jobs.return_value = (jobs, [], [])
        validator.validate_for_digest.return_value = (True, None)

        result = _validate_and_filter_jobs(jobs, db, validator)
        assert len(result) == 1
        assert result[0]["company"] == "Acme"

    def test_invalid_jobs_excluded(self):
        db = MagicMock()
        valid_job = _make_job(link="https://example.com/good", job_hash="good")
        invalid_job = _make_job(
            link="https://example.com/bad", job_hash="bad", validation_reason="404_not_found"
        )

        validator = MagicMock()
        validator.filter_valid_jobs.return_value = ([valid_job], [], [invalid_job])
        validator.validate_for_digest.return_value = (True, None)

        result = _validate_and_filter_jobs([valid_job, invalid_job], db, validator)
        assert len(result) == 1
        # Invalid job should have been persisted as 404
        db.update_url_validation.assert_any_call("bad", "404")

    def test_stale_jobs_excluded_in_second_pass(self):
        db = MagicMock()
        fresh = _make_job(link="https://example.com/fresh", job_hash="fresh")
        stale = _make_job(link="https://example.com/stale", job_hash="stale")

        validator = MagicMock()
        validator.filter_valid_jobs.return_value = ([fresh, stale], [], [])
        # First call fresh, second call stale
        validator.validate_for_digest.side_effect = [
            (True, None),
            (False, "stale_job_age"),
        ]

        result = _validate_and_filter_jobs([fresh, stale], db, validator)
        assert len(result) == 1
        assert result[0]["job_hash"] == "fresh"
        db.update_url_validation.assert_any_call("stale", "stale_job_age")

    def test_creates_validator_when_none_provided(self):
        db = MagicMock()
        jobs = [_make_job()]

        with patch("src.send_profile_digest.JobValidator") as mock_validator_cls:
            mock_instance = MagicMock()
            mock_instance.filter_valid_jobs.return_value = (jobs, [], [])
            mock_instance.validate_for_digest.return_value = (True, None)
            mock_validator_cls.return_value = mock_instance

            result = _validate_and_filter_jobs(jobs, db)
            mock_validator_cls.assert_called_once_with(timeout=5)
            assert len(result) == 1

    def test_reuses_provided_validator(self):
        db = MagicMock()
        jobs = [_make_job()]
        validator = MagicMock()
        validator.filter_valid_jobs.return_value = (jobs, [], [])
        validator.validate_for_digest.return_value = (True, None)

        _validate_and_filter_jobs(jobs, db, validator)
        validator.filter_valid_jobs.assert_called_once()


# ── _prevalidate_jobs_for_all_profiles ───────────────────────────────


class TestPrevalidateJobsForAllProfiles:
    def test_shared_url_validated_once(self):
        """Same URL appearing in two profiles should only be HTTP-checked once."""
        db = MagicMock()
        shared_link = "https://example.com/shared-job"
        job_wes = _make_job(link=shared_link, job_hash="h1", id=1)
        job_adam = _make_job(link=shared_link, job_hash="h1", id=1)

        db.get_jobs_for_profile_digest.side_effect = [[job_wes], [job_adam]]

        profiles = [_make_profile("wes"), _make_profile("adam")]

        with patch("src.send_profile_digest._validate_and_filter_jobs") as mock_vf:
            mock_vf.return_value = [_make_job(link=shared_link)]

            result = _prevalidate_jobs_for_all_profiles(profiles, db)

            # _validate_and_filter_jobs called once with 1 unique job
            mock_vf.assert_called_once()
            unique_jobs = mock_vf.call_args[0][0]
            assert len(unique_jobs) == 1

        assert "wes" in result
        assert "adam" in result

    def test_invalid_url_excluded_from_all_profiles(self):
        db = MagicMock()
        good = _make_job(link="https://example.com/good", job_hash="g")
        bad = _make_job(link="https://example.com/bad", job_hash="b")

        db.get_jobs_for_profile_digest.side_effect = [
            [good, bad],  # wes
            [bad],  # adam
        ]

        profiles = [_make_profile("wes"), _make_profile("adam")]

        with patch("src.send_profile_digest._validate_and_filter_jobs") as mock_vf:
            # Only the good job survives validation
            mock_vf.return_value = [_make_job(link="https://example.com/good")]

            result = _prevalidate_jobs_for_all_profiles(profiles, db)

        assert len(result["wes"]) == 1
        assert result["wes"][0]["link"] == "https://example.com/good"
        assert len(result["adam"]) == 0  # bad link excluded

    def test_returns_shallow_copies(self):
        """Per-profile lists should be independent (shallow copies)."""
        db = MagicMock()
        shared = _make_job(link="https://example.com/shared")
        db.get_jobs_for_profile_digest.side_effect = [[shared], [shared]]

        profiles = [_make_profile("wes"), _make_profile("adam")]

        with patch("src.send_profile_digest._validate_and_filter_jobs") as mock_vf:
            mock_vf.return_value = [_make_job(link="https://example.com/shared")]
            result = _prevalidate_jobs_for_all_profiles(profiles, db)

        # Mutating one profile's list shouldn't affect the other
        result["wes"][0]["title"] = "MUTATED"
        assert result["adam"][0]["title"] != "MUTATED"

    def test_force_resend_passes_through(self):
        db = MagicMock()
        db.get_jobs_for_profile_digest.return_value = []
        profiles = [_make_profile("wes")]

        with patch("src.send_profile_digest._validate_and_filter_jobs") as mock_vf:
            mock_vf.return_value = []
            _prevalidate_jobs_for_all_profiles(profiles, db, force_resend=True)

        db.get_jobs_for_profile_digest.assert_called_once_with(
            profile_id="wes",
            min_grade="F",
            min_location_score=0,
            limit=100,
            max_age_days=7,
        )

    def test_empty_profiles_returns_empty(self):
        db = MagicMock()
        with patch("src.send_profile_digest._validate_and_filter_jobs") as mock_vf:
            mock_vf.return_value = []
            result = _prevalidate_jobs_for_all_profiles([], db)
        assert result == {}


# ── send_digest_to_profile with pre_validated_jobs ───────────────────


class TestSendDigestToProfilePreValidated:
    @patch("src.send_profile_digest.get_profile_manager")
    @patch("src.send_profile_digest.JobDatabase")
    def test_skips_validation_when_pre_validated(self, mock_db_cls, mock_manager):
        """When pre_validated_jobs is provided, JobValidator should not be used."""
        profile = _make_profile("wes", "Wes")
        mock_manager.return_value.get_profile.return_value = profile

        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        jobs = [_make_job(score=80, grade="B")]

        with (
            patch("src.send_profile_digest.JobValidator") as mock_validator_cls,
            patch("src.send_profile_digest.JobFilterPipeline") as mock_filter_cls,
        ):
            mock_filter_cls.return_value.apply_hard_filters.return_value = (True, None)

            send_digest_to_profile("wes", dry_run=True, pre_validated_jobs=jobs)

            # Validator should NOT be instantiated
            mock_validator_cls.assert_not_called()

    @patch("src.send_profile_digest.get_profile_manager")
    @patch("src.send_profile_digest.JobDatabase")
    def test_still_applies_hard_filters(self, mock_db_cls, mock_manager):
        """Hard filters must still run even with pre-validated jobs."""
        profile = _make_profile("wes", "Wes")
        mock_manager.return_value.get_profile.return_value = profile
        mock_db_cls.return_value = MagicMock()

        blocked_job = _make_job(title="Software Engineer", score=80, grade="B")

        with patch("src.send_profile_digest.JobFilterPipeline") as mock_filter_cls:
            mock_filter_cls.return_value.apply_hard_filters.return_value = (False, "software_role")

            result = send_digest_to_profile("wes", dry_run=True, pre_validated_jobs=[blocked_job])

            mock_filter_cls.return_value.apply_hard_filters.assert_called_once()
            assert result is False  # No jobs after filtering

    @patch("src.send_profile_digest.get_profile_manager")
    @patch("src.send_profile_digest.JobDatabase")
    def test_empty_pre_validated_returns_false(self, mock_db_cls, mock_manager):
        profile = _make_profile("wes", "Wes")
        mock_manager.return_value.get_profile.return_value = profile
        mock_db_cls.return_value = MagicMock()

        result = send_digest_to_profile("wes", dry_run=True, pre_validated_jobs=[])
        assert result is False


# ── send_all_digests integration ─────────────────────────────────────


class TestSendAllDigestsIntegration:
    @patch("src.send_profile_digest.send_digest_to_profile")
    @patch("src.send_profile_digest._prevalidate_jobs_for_all_profiles")
    @patch("src.send_profile_digest.JobDatabase")
    @patch("src.send_profile_digest.get_profile_manager")
    def test_calls_prevalidate_then_per_profile(
        self, mock_manager, mock_db_cls, mock_prevalidate, mock_send
    ):
        profiles = [_make_profile("wes"), _make_profile("adam")]
        mock_manager.return_value.get_enabled_profiles.return_value = profiles

        wes_jobs = [_make_job(company="WesJob")]
        adam_jobs = [_make_job(company="AdamJob")]
        mock_prevalidate.return_value = {"wes": wes_jobs, "adam": adam_jobs}
        mock_send.return_value = True

        results = send_all_digests(dry_run=True)

        mock_prevalidate.assert_called_once()
        assert mock_send.call_count == 2

        # Verify pre_validated_jobs kwarg was passed
        for c in mock_send.call_args_list:
            assert "pre_validated_jobs" in c.kwargs

        assert results == {"wes": True, "adam": True}

    @patch("src.send_profile_digest.send_digest_to_profile")
    @patch("src.send_profile_digest._prevalidate_jobs_for_all_profiles")
    @patch("src.send_profile_digest.JobDatabase")
    @patch("src.send_profile_digest.get_profile_manager")
    def test_missing_profile_in_prevalidated_passes_none(
        self, mock_manager, mock_db_cls, mock_prevalidate, mock_send
    ):
        """If prevalidation has no entry for a profile, None is passed."""
        profiles = [_make_profile("wes")]
        mock_manager.return_value.get_enabled_profiles.return_value = profiles
        mock_prevalidate.return_value = {}  # empty
        mock_send.return_value = False

        send_all_digests()

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["pre_validated_jobs"] is None
