"""Tests for Profile Configuration Validator"""

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.config_validator import check_required_keys
from src.utils.profile_manager import Profile


def create_test_profile(profile_id="test", name="Test", email="test@test.com", scoring=None):
    if scoring is None:
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
    return Profile(
        id=profile_id,
        name=name,
        email=email,
        enabled=True,
        email_username="test@test.com",
        email_app_password_env="TEST_PWD",
        scoring=scoring,
        digest_min_grade="C",
        digest_min_score=63,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="A",
        notifications_min_score=90,
    )


class TestCheckRequiredKeys:
    def test_valid_profile_passes(self):
        check_required_keys(create_test_profile())

    def test_missing_email_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*email"):
            check_required_keys(create_test_profile(email=""))


class TestProfileScorerIntegration:
    def test_profile_scorer_validates_on_init(self):
        scorer = ProfileScorer(create_test_profile())
        assert scorer.profile is not None
