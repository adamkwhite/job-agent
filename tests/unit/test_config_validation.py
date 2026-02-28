"""
Test configuration validation and completeness checks.

Related to: Codebase Analysis Issue #1.3 - Missing Config Key Silent Failure
"""

import json
import logging
from pathlib import Path

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.profile_manager import get_profile_manager


@pytest.fixture
def config_path():
    """Path to filter-keywords.json config file"""
    return Path(__file__).parent.parent.parent / "config" / "filter-keywords.json"


@pytest.fixture
def role_categories_in_config(config_path):
    """All role categories defined in filter-keywords.json"""
    with open(config_path) as f:
        config = json.load(f)
    return set(config.get("role_category_keywords", {}).keys())


@pytest.fixture
def wes_profile():
    """Load Wes profile"""
    return get_profile_manager().get_profile("wes")


@pytest.fixture
def scorer(wes_profile):
    """Create ProfileScorer with Wes's profile"""
    return ProfileScorer(wes_profile)


class TestRoleCategoryConfigCompleteness:
    """Test that config categories have proper structure"""

    def test_all_categories_have_must_keywords(self, config_path, role_categories_in_config):
        """Every category should have a 'must_keywords' list"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        missing_must_keywords = []
        for category in role_categories_in_config:
            if category in role_category_keywords:
                if "must_keywords" not in role_category_keywords[category]:
                    missing_must_keywords.append(category)
                elif not role_category_keywords[category]["must_keywords"]:
                    missing_must_keywords.append(f"{category} (empty list)")

        assert not missing_must_keywords, (
            f"Categories missing 'must_keywords': {missing_must_keywords}"
        )

    def test_all_categories_have_nice_keywords(self, config_path, role_categories_in_config):
        """Every category should have a 'nice_keywords' list"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        missing_nice_keywords = []
        for category in role_categories_in_config:
            if category in role_category_keywords:
                if "nice_keywords" not in role_category_keywords[category]:
                    missing_nice_keywords.append(category)
                elif not role_category_keywords[category]["nice_keywords"]:
                    missing_nice_keywords.append(f"{category} (empty list)")

        assert not missing_nice_keywords, (
            f"Categories missing 'nice_keywords': {missing_nice_keywords}"
        )


class TestScorerConfigMissingWarnings:
    """Test that scorer logs warnings when config is incomplete"""

    def test_warns_when_matched_category_missing_from_config(self, scorer, caplog):
        """Scorer should log WARNING when matched_category not in config"""
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["engineering_leadership"]

        with caplog.at_level(logging.WARNING):
            job = {
                "title": "VP of Engineering",
                "company": "Test Company",
                "location": "Remote",
            }
            scorer.score_job(job)

            assert any(
                "engineering_leadership" in record.message
                and "not found in config" in record.message.lower()
                for record in caplog.records
            ), "Expected WARNING about missing config category"

        scorer.role_category_keywords = original_keywords

    def test_score_calculated_without_bonus_when_category_missing(self, scorer):
        """When category missing, base score should still be calculated"""
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["engineering_leadership"]

        job = {"title": "VP of Engineering", "company": "Test Company", "location": "Remote"}
        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should still get base role score"
        assert breakdown["role_type"] <= 20, "Should NOT get bonus (max base is 20)"

        scorer.role_category_keywords = original_keywords

    def test_logs_which_keywords_would_have_matched(self, scorer, caplog):
        """Warning should explain which keywords would have been checked"""
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["product_leadership"]

        with caplog.at_level(logging.WARNING):
            # Use "Product Manager" which matches the product_leadership
            # role_type keywords in Wes's profile, triggering the
            # _calculate_keyword_bonus warning about missing config category
            job = {
                "title": "VP of Product Management with roadmap and okrs experience",
                "company": "Test Company",
                "location": "Remote",
            }
            scorer.score_job(job)

            warning_messages = [
                record.message for record in caplog.records if record.levelno >= logging.WARNING
            ]
            assert any("product_leadership" in msg for msg in warning_messages), (
                "Warning should mention missing category name"
            )

        scorer.role_category_keywords = original_keywords


class TestConfigFileStructure:
    """Test config file structure and format"""

    def test_config_file_is_valid_json(self, config_path):
        """Config file should be valid JSON"""
        with open(config_path) as f:
            config = json.load(f)
        assert isinstance(config, dict)

    def test_config_has_required_sections(self, config_path):
        """Config should have all required top-level sections"""
        with open(config_path) as f:
            config = json.load(f)

        for section in ["include_keywords", "exclude_keywords", "role_category_keywords"]:
            assert section in config, f"Config missing required section: {section}"

    def test_role_category_keywords_structure(self, config_path):
        """Each role category should have consistent structure"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        for category, keywords in role_category_keywords.items():
            assert isinstance(keywords, dict), f"Category {category} should be a dict"
            assert "must_keywords" in keywords, f"Category {category} missing must_keywords"
            assert "nice_keywords" in keywords, f"Category {category} missing nice_keywords"
            assert isinstance(keywords["must_keywords"], list), (
                f"{category}.must_keywords should be a list"
            )
            assert isinstance(keywords["nice_keywords"], list), (
                f"{category}.nice_keywords should be a list"
            )
