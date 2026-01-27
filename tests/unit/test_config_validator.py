"""Tests for Profile Configuration Validator"""

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.config_validator import check_required_keys, validate_profile_config
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

    def test_missing_id_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*id"):
            check_required_keys(create_test_profile(profile_id=""))

    def test_missing_name_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*name"):
            check_required_keys(create_test_profile(name=""))

    def test_missing_email_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*email"):
            check_required_keys(create_test_profile(email=""))

    def test_missing_scoring_raises_error(self):
        profile = create_test_profile()
        profile.scoring = None
        with pytest.raises(ValueError, match="missing required keys.*scoring"):
            check_required_keys(profile)

    def test_missing_target_seniority_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*scoring.target_seniority"):
            check_required_keys(create_test_profile(scoring={"domain_keywords": ["robotics"]}))

    def test_legacy_seniority_levels_accepted(self):
        # Test that seniority_levels (legacy format) is accepted instead of target_seniority
        scoring = {"seniority_levels": ["vp"], "domain_keywords": ["robotics"]}
        check_required_keys(create_test_profile(scoring=scoring))

    def test_missing_domain_keywords_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*scoring.domain_keywords"):
            check_required_keys(create_test_profile(scoring={"target_seniority": ["vp"]}))

    def test_empty_domain_keywords_list_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*scoring.domain_keywords"):
            check_required_keys(
                create_test_profile(scoring={"target_seniority": ["vp"], "domain_keywords": []})
            )

    def test_empty_domain_keywords_dict_raises_error(self):
        with pytest.raises(ValueError, match="missing required keys.*scoring.domain_keywords"):
            check_required_keys(
                create_test_profile(scoring={"target_seniority": ["vp"], "domain_keywords": {}})
            )

    def test_multiple_missing_keys_listed_in_error(self):
        profile = create_test_profile(profile_id="", email="")
        with pytest.raises(ValueError, match="id.*email"):
            check_required_keys(profile)


class TestValidateProfileConfig:
    def test_valid_profile_no_warnings(self):
        scoring = {
            "target_seniority": ["vp"],
            "domain_keywords": ["robotics"],
            "hard_filter_keywords": {"include": ["vp"]},
            "context_filters": [],
            "role_types": {"engineering": 20},
            "location_preferences": {"remote": 15},
        }
        profile = create_test_profile(scoring=scoring)
        warnings = validate_profile_config(profile)
        assert len(warnings) == 0

    def test_missing_scoring_returns_empty_list(self):
        profile = create_test_profile()
        profile.scoring = None
        warnings = validate_profile_config(profile)
        assert warnings == []

    def test_missing_hard_filter_keywords_warns(self):
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
        profile = create_test_profile(scoring=scoring)
        warnings = validate_profile_config(profile)
        assert any("hard_filter_keywords" in w for w in warnings)

    def test_missing_context_filters_warns(self):
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
        profile = create_test_profile(scoring=scoring)
        warnings = validate_profile_config(profile)
        assert any("context_filters" in w for w in warnings)

    def test_missing_digest_min_grade_warns(self):
        profile = create_test_profile()
        profile.digest_min_grade = None
        warnings = validate_profile_config(profile)
        assert any("digest.min_grade" in w for w in warnings)

    def test_missing_role_types_warns(self):
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
        profile = create_test_profile(scoring=scoring)
        warnings = validate_profile_config(profile)
        assert any("role_types" in w for w in warnings)

    def test_missing_location_preferences_warns(self):
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
        profile = create_test_profile(scoring=scoring)
        warnings = validate_profile_config(profile)
        assert any("location_preferences" in w for w in warnings)

    def test_all_missing_optional_keys_generate_warnings(self):
        scoring = {"target_seniority": ["vp"], "domain_keywords": ["robotics"]}
        profile = create_test_profile(scoring=scoring)
        profile.digest_min_grade = None
        warnings = validate_profile_config(profile)
        # Should have 5 warnings for missing optional keys
        assert len(warnings) == 5


class TestProfileScorerIntegration:
    def test_profile_scorer_validates_on_init(self):
        scorer = ProfileScorer(create_test_profile())
        assert scorer.profile is not None
