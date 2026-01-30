"""
Tests for ProfileManager and Profile classes
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.profile_manager import Profile, ProfileManager


@pytest.fixture
def sample_profile_data():
    """Sample profile data for testing"""
    return {
        "id": "test_user",
        "name": "Test User",
        "email": "test@example.com",
        "enabled": True,
        "email_credentials": {
            "username": "test.alerts@gmail.com",
            "app_password_env": "TEST_GMAIL_APP_PASSWORD",
        },
        "scoring": {
            "target_seniority": ["senior", "lead", "principal"],
            "domain_keywords": ["software", "backend", "python"],
            "role_types": {"engineering": ["software engineer", "developer"]},
            "company_stage": ["startup", "series a"],
            "avoid_keywords": ["junior", "intern"],
            "location_preferences": {
                "remote_keywords": ["remote", "wfh"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto", "ottawa"],
                "preferred_regions": ["ontario", "canada"],
            },
        },
        "digest": {
            "min_grade": "C",
            "min_score": 63,
            "include_grades": ["A", "B", "C"],
            "send_frequency": "weekly",
        },
        "notifications": {"enabled": True, "min_grade": "B", "min_score": 80},
    }


@pytest.fixture
def temp_profiles_dir(sample_profile_data):
    """Create a temporary profiles directory with test profiles"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test profile
        profile_path = Path(tmpdir) / "test_user.json"
        with open(profile_path, "w") as f:
            json.dump(sample_profile_data, f)

        # Write a disabled profile
        disabled_profile = sample_profile_data.copy()
        disabled_profile["id"] = "disabled_user"
        disabled_profile["enabled"] = False
        disabled_path = Path(tmpdir) / "disabled_user.json"
        with open(disabled_path, "w") as f:
            json.dump(disabled_profile, f)

        yield tmpdir


class TestProfile:
    """Test Profile dataclass"""

    def test_profile_creation(self, sample_profile_data):
        """Test creating a Profile from data"""
        data = sample_profile_data
        profile = Profile(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            enabled=data["enabled"],
            email_username=data["email_credentials"]["username"],
            email_app_password_env=data["email_credentials"]["app_password_env"],
            scoring=data["scoring"],
            digest_min_grade=data["digest"]["min_grade"],
            digest_min_score=data["digest"]["min_score"],
            digest_min_location_score=data["digest"].get("min_location_score", 0),
            digest_include_grades=data["digest"]["include_grades"],
            digest_frequency=data["digest"]["send_frequency"],
            notifications_enabled=data["notifications"]["enabled"],
            notifications_min_grade=data["notifications"]["min_grade"],
            notifications_min_score=data["notifications"]["min_score"],
        )

        assert profile.id == "test_user"
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.enabled is True

    def test_get_location_preferences(self, sample_profile_data):
        """Test getting location preferences"""
        data = sample_profile_data
        profile = Profile(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            enabled=data["enabled"],
            email_username="",
            email_app_password_env="",
            scoring=data["scoring"],
            digest_min_grade="C",
            digest_min_score=63,
            digest_min_location_score=0,
            digest_include_grades=["A", "B", "C"],
            digest_frequency="weekly",
            notifications_enabled=False,
            notifications_min_grade="A",
            notifications_min_score=90,
        )

        prefs = profile.get_location_preferences()
        assert "remote_keywords" in prefs
        assert "toronto" in prefs["preferred_cities"]

    def test_get_target_seniority(self, sample_profile_data):
        """Test getting target seniority levels"""
        data = sample_profile_data
        profile = Profile(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            enabled=data["enabled"],
            email_username="",
            email_app_password_env="",
            scoring=data["scoring"],
            digest_min_grade="C",
            digest_min_score=63,
            digest_min_location_score=0,
            digest_include_grades=["A", "B", "C"],
            digest_frequency="weekly",
            notifications_enabled=False,
            notifications_min_grade="A",
            notifications_min_score=90,
        )

        seniority = profile.get_target_seniority()
        assert "senior" in seniority
        assert "lead" in seniority

    def test_get_domain_keywords(self, sample_profile_data):
        """Test getting domain keywords"""
        data = sample_profile_data
        profile = Profile(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            enabled=data["enabled"],
            email_username="",
            email_app_password_env="",
            scoring=data["scoring"],
            digest_min_grade="C",
            digest_min_score=63,
            digest_min_location_score=0,
            digest_include_grades=["A", "B", "C"],
            digest_frequency="weekly",
            notifications_enabled=False,
            notifications_min_grade="A",
            notifications_min_score=90,
        )

        keywords = profile.get_domain_keywords()
        assert "software" in keywords
        assert "python" in keywords

    def test_get_avoid_keywords(self, sample_profile_data):
        """Test getting avoid keywords"""
        data = sample_profile_data
        profile = Profile(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            enabled=data["enabled"],
            email_username="",
            email_app_password_env="",
            scoring=data["scoring"],
            digest_min_grade="C",
            digest_min_score=63,
            digest_min_location_score=0,
            digest_include_grades=["A", "B", "C"],
            digest_frequency="weekly",
            notifications_enabled=False,
            notifications_min_grade="A",
            notifications_min_score=90,
        )

        avoid = profile.get_avoid_keywords()
        assert "junior" in avoid
        assert "intern" in avoid


class TestProfileManager:
    """Test ProfileManager class"""

    def test_load_profiles(self, temp_profiles_dir):
        """Test loading profiles from directory"""
        manager = ProfileManager(profiles_dir=temp_profiles_dir)

        assert len(manager.get_all_profiles()) == 2
        assert manager.profile_exists("test_user")
        assert manager.profile_exists("disabled_user")

    def test_get_profile(self, temp_profiles_dir):
        """Test getting a specific profile"""
        manager = ProfileManager(profiles_dir=temp_profiles_dir)

        profile = manager.get_profile("test_user")
        assert profile is not None
        assert profile.name == "Test User"

        # Non-existent profile
        assert manager.get_profile("nonexistent") is None

    def test_get_enabled_profiles(self, temp_profiles_dir):
        """Test getting only enabled profiles"""
        manager = ProfileManager(profiles_dir=temp_profiles_dir)

        enabled = manager.get_enabled_profiles()
        assert len(enabled) == 1
        assert enabled[0].id == "test_user"

    def test_get_profile_ids(self, temp_profiles_dir):
        """Test getting list of profile IDs"""
        manager = ProfileManager(profiles_dir=temp_profiles_dir)

        ids = manager.get_profile_ids()
        assert "test_user" in ids
        assert "disabled_user" in ids

    def test_reload_profiles(self, temp_profiles_dir):
        """Test reloading profiles"""
        manager = ProfileManager(profiles_dir=temp_profiles_dir)

        # Add a new profile file (with all required fields for Pydantic validation)
        new_profile = {
            "id": "new_user",
            "name": "New User",
            "email": "new@example.com",
            "enabled": True,
            "email_credentials": {
                "username": "new.alerts@gmail.com",
                "app_password_env": "NEW_GMAIL_APP_PASSWORD",
            },
            "scoring": {
                "target_seniority": ["senior", "lead"],
                "domain_keywords": ["software", "python"],
                "role_types": {"engineering": ["software engineer"]},
            },
            "digest": {
                "min_grade": "C",
                "min_score": 55,
                "include_grades": ["A", "B", "C"],
                "send_frequency": "weekly",
            },
            "notifications": {"enabled": True, "min_grade": "B", "min_score": 70},
        }
        new_path = Path(temp_profiles_dir) / "new_user.json"
        with open(new_path, "w") as f:
            json.dump(new_profile, f)

        # Reload and verify new profile is loaded
        manager.reload_profiles()
        assert manager.profile_exists("new_user")

    def test_nonexistent_directory(self, capsys):
        """Test handling of non-existent profiles directory"""
        manager = ProfileManager(profiles_dir="/nonexistent/path")

        assert len(manager.get_all_profiles()) == 0

        captured = capsys.readouterr()
        assert "not found" in captured.out
