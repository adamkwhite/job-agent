"""
Tests for profile onboarding script (Issue #346).

Tests the profile generation, validation, and message formatting
without requiring interactive input.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from onboard_profile import gather_profile_info, print_onboarding_message, save_profile


@pytest.fixture
def sample_profile():
    """A complete profile dict as gather_profile_info would return."""
    return {
        "id": "janesmith",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "enabled": True,
        "scoring": {
            "target_seniority": ["director", "vp", "head of"],
            "domain_keywords": ["saas", "cloud", "enterprise"],
            "role_types": {
                "engineering_leadership": [
                    "engineering",
                    "engineering manager",
                    "director engineering",
                    "vp engineering",
                    "head of engineering",
                ],
            },
            "company_stage": ["growth", "series b", "series c", "scale-up"],
            "avoid_keywords": [
                "junior",
                "associate",
                "intern",
                "coordinator",
                "fintech",
                "medtech",
            ],
            "location_preferences": {
                "remote_keywords": [
                    "remote",
                    "work from home",
                    "wfh",
                    "anywhere",
                    "distributed",
                ],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto", "barrie"],
                "preferred_regions": ["ontario", "canada"],
            },
            "filtering": {
                "aggression_level": "conservative",
                "software_engineering_avoid": [
                    "software engineer",
                    "software engineering",
                    "frontend",
                    "backend",
                    "full stack",
                ],
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        },
        "digest": {
            "min_grade": "B",
            "min_score": 70,
            "include_grades": ["A", "B"],
            "send_frequency": "weekly",
        },
        "notifications": {
            "enabled": False,
            "min_grade": "B",
            "min_score": 70,
        },
    }


class TestSaveProfile:
    """Test save_profile writes valid JSON."""

    def test_creates_json_file(self, tmp_path, sample_profile):
        """Should create a valid JSON file in the profiles directory."""
        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            path = save_profile(sample_profile)

        assert path.exists()
        assert path.suffix == ".json"

        with open(path) as f:
            loaded = json.load(f)

        assert loaded["id"] == "janesmith"
        assert loaded["name"] == "Jane Smith"
        assert loaded["scoring"]["target_seniority"] == ["director", "vp", "head of"]

    def test_overwrites_when_confirmed(self, tmp_path, sample_profile):
        """Should overwrite existing file when user confirms."""
        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            # Create first
            save_profile(sample_profile)

            # Overwrite with confirmation
            with patch("builtins.input", return_value="y"):
                path = save_profile(sample_profile)

        assert path.exists()

    def test_aborts_when_declined(self, tmp_path, sample_profile):
        """Should exit when user declines overwrite."""
        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            save_profile(sample_profile)

            with patch("builtins.input", return_value="n"), pytest.raises(SystemExit):
                save_profile(sample_profile)


class TestGatherProfileInfo:
    """Test gather_profile_info with mocked input."""

    def test_builds_complete_profile(self):
        """Should build a valid profile dict from user inputs."""
        inputs = iter(
            [
                "Jane Smith",  # name
                "janesmith",  # id
                "jane@example.com",  # email
                "director, vp",  # seniority
                "saas, cloud",  # domains
                "fintech",  # exclude
                "",  # eng roles (default)
                "",  # company stage (default)
                "toronto, barrie",  # cities
                "",  # regions (default)
                "",  # aggression (default)
                "",  # min grade (default)
                "",  # min score (default)
                "n",  # has inbox
            ]
        )
        with patch("builtins.input", lambda _: next(inputs)):
            profile = gather_profile_info()

        assert profile["id"] == "janesmith"
        assert profile["name"] == "Jane Smith"
        assert "director" in profile["scoring"]["target_seniority"]
        assert "saas" in profile["scoring"]["domain_keywords"]
        assert "fintech" in profile["scoring"]["avoid_keywords"]
        assert "email_credentials" not in profile

    def test_includes_inbox_when_configured(self):
        """Should add email_credentials when inbox is configured."""
        inputs = iter(
            [
                "Jane Smith",
                "janesmith",
                "jane@example.com",
                "director",
                "saas",
                "",  # no excludes
                "",  # eng roles default
                "",  # company stage default
                "toronto",
                "",  # regions default
                "",  # aggression default
                "",  # grade default
                "",  # score default
                "y",  # has inbox
                "jane.jobalerts@gmail.com",
                "",  # password env default
            ]
        )
        with patch("builtins.input", lambda _: next(inputs)):
            profile = gather_profile_info()

        assert "email_credentials" in profile
        assert profile["email_credentials"]["username"] == "jane.jobalerts@gmail.com"
        assert profile["email_credentials"]["app_password_env"] == "JANESMITH_GMAIL_APP_PASSWORD"


class TestOnboardingMessage:
    """Test the generated onboarding message."""

    def test_message_contains_profile_details(self, sample_profile, capsys):
        """Should include key profile info in the onboarding message."""
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Jane" in output
        assert "Director" in output
        assert "saas" in output
        assert "jane@example.com" in output
        assert "Toronto" in output
        assert "Fintech" in output  # excluded domain
        assert "Monday" in output

    def test_message_no_excluded_when_none(self, sample_profile, capsys):
        """Should omit excluded domains line when none are excluded."""
        # Remove domain excludes
        sample_profile["scoring"]["avoid_keywords"] = [
            "junior",
            "associate",
            "intern",
            "coordinator",
        ]
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Excluded domains" not in output
