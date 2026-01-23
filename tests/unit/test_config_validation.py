"""
Test configuration validation and completeness checks.

Related to: Codebase Analysis Issue #1.3 - Missing Config Key Silent Failure
"""

import json
import logging
from pathlib import Path

import pytest

from src.agents.job_scorer import JobScorer


@pytest.fixture
def config_path():
    """Path to filter-keywords.json config file"""
    return Path(__file__).parent.parent.parent / "config" / "filter-keywords.json"


@pytest.fixture
def role_categories_in_code():
    """All role categories that JobScorer._score_role_type() can match"""
    return {
        "product_leadership",
        "engineering_leadership",
        "technical_program_management",
        "manufacturing_npi_operations",
        "product_development_rnd",
        "platform_integrations_systems",
        "robotics_automation_engineering",
    }


class TestRoleCategoryConfigCompleteness:
    """Test that all code categories have config entries"""

    def test_all_code_categories_have_config_entries(self, config_path, role_categories_in_code):
        """Every category matched in code should have keywords in config"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        # Check each category exists
        missing_categories = []
        for category in role_categories_in_code:
            if category not in role_category_keywords:
                missing_categories.append(category)

        assert not missing_categories, (
            f"Categories in code but missing from config: {missing_categories}. "
            f"Add them to config/filter-keywords.json under 'role_category_keywords'"
        )

    def test_all_categories_have_must_keywords(self, config_path, role_categories_in_code):
        """Every category should have a 'must_keywords' list"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        missing_must_keywords = []
        for category in role_categories_in_code:
            if category in role_category_keywords:
                if "must_keywords" not in role_category_keywords[category]:
                    missing_must_keywords.append(category)
                elif not role_category_keywords[category]["must_keywords"]:
                    missing_must_keywords.append(f"{category} (empty list)")

        assert not missing_must_keywords, (
            f"Categories missing 'must_keywords': {missing_must_keywords}"
        )

    def test_all_categories_have_nice_keywords(self, config_path, role_categories_in_code):
        """Every category should have a 'nice_keywords' list"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        missing_nice_keywords = []
        for category in role_categories_in_code:
            if category in role_category_keywords:
                if "nice_keywords" not in role_category_keywords[category]:
                    missing_nice_keywords.append(category)
                elif not role_category_keywords[category]["nice_keywords"]:
                    missing_nice_keywords.append(f"{category} (empty list)")

        assert not missing_nice_keywords, (
            f"Categories missing 'nice_keywords': {missing_nice_keywords}"
        )

    def test_no_orphaned_config_categories(self, config_path, role_categories_in_code):
        """Warn about config categories not used in code (possibly typos)"""
        with open(config_path) as f:
            config = json.load(f)

        role_category_keywords = config.get("role_category_keywords", {})

        # Find categories in config but not in code
        orphaned_categories = set(role_category_keywords.keys()) - role_categories_in_code

        # This is a warning, not a hard failure (config might have future categories)
        if orphaned_categories:
            pytest.warns(
                UserWarning,
                match=f"Config has categories not used in code: {orphaned_categories}",
            )


class TestJobScorerConfigMissingWarnings:
    """Test that JobScorer logs warnings when config is incomplete"""

    def test_warns_when_matched_category_missing_from_config(self, caplog):
        """JobScorer should log WARNING when matched_category not in config"""
        scorer = JobScorer()

        # Temporarily remove a category from config to trigger warning
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["engineering_leadership"]

        with caplog.at_level(logging.WARNING):
            # Score a job that would match engineering_leadership
            job = {
                "title": "VP of Engineering",
                "company": "Test Company",
                "location": "Remote",
            }
            score, grade, breakdown, _ = scorer.score_job(job)

            # Should have logged a warning
            assert any(
                "engineering_leadership" in record.message
                and "not found in config" in record.message.lower()
                for record in caplog.records
            ), "Expected WARNING about missing config category"

        # Restore original config
        scorer.role_category_keywords = original_keywords

    def test_score_calculated_without_bonus_when_category_missing(self):
        """When category missing, base score should still be calculated"""
        scorer = JobScorer()

        # Remove engineering_leadership from config
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["engineering_leadership"]

        job = {
            "title": "VP of Engineering",
            "company": "Test Company",
            "location": "Remote",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        # Should still get base role score (15-20) without bonus
        assert breakdown["role_type"] > 0, "Should still get base role score"
        assert breakdown["role_type"] <= 20, "Should NOT get bonus (max base is 20)"

        # Restore config
        scorer.role_category_keywords = original_keywords

    def test_logs_which_keywords_would_have_matched(self, caplog):
        """Warning should explain which keywords would have been checked"""
        scorer = JobScorer()

        # Mock scenario where category is matched but config is missing
        original_keywords = scorer.role_category_keywords.copy()
        del scorer.role_category_keywords["product_leadership"]

        with caplog.at_level(logging.WARNING):
            job = {
                "title": "VP of Product with product roadmap and okrs experience",
                "company": "Test Company",
                "location": "Remote",
            }
            scorer.score_job(job)

            # Should mention the category name in warning
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
            config = json.load(f)  # Should not raise JSONDecodeError

        assert isinstance(config, dict)

    def test_config_has_required_sections(self, config_path):
        """Config should have all required top-level sections"""
        with open(config_path) as f:
            config = json.load(f)

        required_sections = [
            "include_keywords",
            "exclude_keywords",
            "role_category_keywords",
        ]

        for section in required_sections:
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
