"""
Tests for profile onboarding script (Issue #346, #349).

Tests the profile generation, validation, message formatting,
and PromptKit dependency injection.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import from scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from onboard_profile import (
    PromptKit,
    _gather_digest_info,
    _gather_scoring_info,
    gather_profile_info,
    print_onboarding_message,
    save_profile,
)


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


def _mock_kit(responses: list[str]) -> PromptKit:
    """Create a PromptKit that returns predetermined responses in order."""
    call_count = {"idx": 0}

    def mock_prompt(_label: str, default: str = "") -> str:
        idx = call_count["idx"]
        call_count["idx"] += 1
        if idx < len(responses):
            return responses[idx] if responses[idx] else default
        return default

    def mock_prompt_list(label: str, default: str = "") -> list[str]:
        raw = mock_prompt(label, default)
        if not raw:
            return []
        return [item.strip().lower() for item in raw.split(",") if item.strip()]

    def mock_prompt_yes_no(label: str, default: bool = False) -> bool:
        raw = mock_prompt(label)
        if not raw:
            return default
        return raw.lower().startswith("y")

    return PromptKit(
        prompt=mock_prompt,
        prompt_list=mock_prompt_list,
        prompt_yes_no=mock_prompt_yes_no,
        print_fn=MagicMock(),
    )


# ── PromptKit ──────────────────────────────────────────────────────


class TestPromptKit:
    def test_default_kit_has_callables(self):
        kit = PromptKit()
        assert callable(kit.prompt)
        assert callable(kit.prompt_list)
        assert callable(kit.prompt_yes_no)
        assert callable(kit.print_fn)

    def test_custom_prompt_override(self):
        custom_prompt = MagicMock(return_value="test")
        kit = PromptKit(prompt=custom_prompt)
        result = kit.prompt("label")
        custom_prompt.assert_called_once_with("label")
        assert result == "test"


# ── _gather_scoring_info with PromptKit ────────────────────────────


class TestGatherScoringInfoWithKit:
    def test_returns_expected_structure(self):
        responses = [
            "senior, staff",  # target seniority
            "saas, cloud",  # domain keywords
            "fintech",  # exclude domains
            "",  # eng roles (use default)
            "",  # company stage (use default)
            "toronto, ottawa",  # preferred cities
            "",  # preferred regions (default)
            "moderate",  # aggression level
        ]
        kit = _mock_kit(responses)
        result = _gather_scoring_info(kit)

        assert result["target_seniority"] == ["senior", "staff"]
        assert result["domain_keywords"] == ["saas", "cloud"]
        assert "fintech" in result["avoid_keywords"]
        assert result["filtering"]["aggression_level"] == "moderate"
        assert result["location_preferences"]["preferred_cities"] == ["toronto", "ottawa"]

    def test_defaults_when_empty(self):
        responses = [""] * 8
        kit = _mock_kit(responses)
        result = _gather_scoring_info(kit)

        assert "role_types" in result
        assert result["filtering"]["aggression_level"] == "conservative"


# ── _gather_digest_info with PromptKit ─────────────────────────────


class TestGatherDigestInfoWithKit:
    def test_returns_digest_and_notifications(self):
        responses = ["B", "70", "daily"]
        kit = _mock_kit(responses)
        digest, notifications = _gather_digest_info(kit)

        assert digest["min_grade"] == "B"
        assert digest["min_score"] == 70
        assert digest["send_frequency"] == "daily"
        assert digest["include_grades"] == ["A", "B"]
        assert notifications["enabled"] is False

    def test_defaults(self):
        responses = ["", "", ""]
        kit = _mock_kit(responses)
        digest, _ = _gather_digest_info(kit)

        assert digest["min_grade"] == "B"
        assert digest["min_score"] == 70
        assert digest["send_frequency"] == "daily"


# ── gather_profile_info with PromptKit ─────────────────────────────


class TestGatherProfileInfoWithKit:
    def test_full_profile_without_inbox(self):
        responses = [
            "John Doe",
            "john",
            "john@example.com",
            # scoring (8)
            "senior, lead",
            "saas",
            "",
            "",
            "",
            "toronto",
            "",
            "conservative",
            # digest (3)
            "C",
            "55",
            "daily",
            # inbox
            "no",
        ]
        kit = _mock_kit(responses)
        profile = gather_profile_info(kit)

        assert profile["id"] == "john"
        assert profile["name"] == "John Doe"
        assert profile["email"] == "john@example.com"
        assert profile["enabled"] is True
        assert profile["scoring"]["target_seniority"] == ["senior", "lead"]
        assert profile["digest"]["send_frequency"] == "daily"
        assert "email_credentials" not in profile

    def test_profile_with_inbox(self):
        responses = [
            "Jane Smith",
            "jane",
            "jane@example.com",
            # scoring (8)
            "director, vp",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            # digest (3)
            "",
            "",
            "",
            # inbox
            "yes",
            "jane.jobalerts@gmail.com",
            "JANE_GMAIL_APP_PASSWORD",
        ]
        kit = _mock_kit(responses)
        profile = gather_profile_info(kit)

        assert "email_credentials" in profile
        assert profile["email_credentials"]["username"] == "jane.jobalerts@gmail.com"


# ── save_profile with PromptKit ────────────────────────────────────


class TestSaveProfile:
    def test_creates_json_file(self, tmp_path, sample_profile):
        kit = _mock_kit([])
        kit.print_fn = MagicMock()

        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            path = save_profile(sample_profile, kit)

        assert path is not None
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["name"] == "Jane Smith"

    def test_returns_none_on_overwrite_decline(self, tmp_path, sample_profile):
        (tmp_path / "janesmith.json").write_text("{}")
        kit = _mock_kit(["no"])
        kit.print_fn = MagicMock()

        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            result = save_profile(sample_profile, kit)

        assert result is None

    def test_overwrites_on_confirm(self, tmp_path, sample_profile):
        (tmp_path / "janesmith.json").write_text("{}")
        kit = _mock_kit(["yes"])
        kit.print_fn = MagicMock()

        with patch("onboard_profile.PROFILES_DIR", tmp_path):
            result = save_profile(sample_profile, kit)

        assert result is not None
        loaded = json.loads((tmp_path / "janesmith.json").read_text())
        assert loaded["name"] == "Jane Smith"


# ── Legacy CLI tests (backward compatibility) ─────────────────────


class TestGatherProfileInfoLegacy:
    def test_builds_complete_profile_with_input(self):
        inputs = iter(
            [
                "Jane Smith",
                "janesmith",
                "jane@example.com",
                "director, vp",
                "saas, cloud",
                "fintech",
                "",
                "",
                "toronto, barrie",
                "",
                "",
                "",
                "",
                "",  # digest defaults (now includes frequency)
                "n",  # no inbox
            ]
        )
        with patch("builtins.input", lambda _: next(inputs)):
            profile = gather_profile_info()

        assert profile["id"] == "janesmith"
        assert "director" in profile["scoring"]["target_seniority"]
        assert "email_credentials" not in profile

    def test_includes_inbox_when_configured(self):
        inputs = iter(
            [
                "Jane Smith",
                "janesmith",
                "jane@example.com",
                "director",
                "saas",
                "",
                "",
                "",
                "toronto",
                "",
                "",
                "",
                "",
                "",  # digest defaults
                "y",  # has inbox
                "jane.jobalerts@gmail.com",
                "",
            ]
        )
        with patch("builtins.input", lambda _: next(inputs)):
            profile = gather_profile_info()

        assert "email_credentials" in profile
        assert profile["email_credentials"]["username"] == "jane.jobalerts@gmail.com"


# ── Onboarding message ────────────────────────────────────────────


class TestOnboardingMessage:
    def test_message_contains_profile_details(self, sample_profile, capsys):
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Jane" in output
        assert "Director" in output
        assert "jane@example.com" in output
        assert "Toronto" in output
        assert "Fintech" in output

    def test_daily_frequency_in_message(self, sample_profile, capsys):
        sample_profile["digest"]["send_frequency"] = "daily"
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Daily" in output

    def test_weekly_frequency_in_message(self, sample_profile, capsys):
        sample_profile["digest"]["send_frequency"] = "weekly"
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Weekly" in output

    def test_no_excluded_when_none(self, sample_profile, capsys):
        sample_profile["scoring"]["avoid_keywords"] = [
            "junior",
            "associate",
            "intern",
            "coordinator",
        ]
        print_onboarding_message(sample_profile)
        output = capsys.readouterr().out

        assert "Excluded domains" not in output
