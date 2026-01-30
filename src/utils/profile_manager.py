"""
Profile Management System
Manages user profiles for multi-person job scoring

Profiles are stored as JSON files in the profiles/ directory.
Each profile contains:
- User identity (name, email)
- Email credentials (for IMAP access)
- Scoring preferences (keywords, seniority, domains)
- Digest settings (frequency, min grade)
- Notification preferences

Profiles are validated using Pydantic models for type safety and data integrity.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.pydantic_models import ProfileConfig


@dataclass
class Profile:
    """User profile data class"""

    id: str
    name: str
    email: str
    enabled: bool

    # Email credentials
    email_username: str
    email_app_password_env: str

    # Scoring configuration
    scoring: dict

    # Digest settings
    digest_min_grade: str
    digest_min_score: int
    digest_min_location_score: int
    digest_include_grades: list[str]
    digest_frequency: str

    # Notification settings
    notifications_enabled: bool
    notifications_min_grade: str
    notifications_min_score: int

    @property
    def email_app_password(self) -> str | None:
        """Get app password from environment variable"""
        return os.getenv(self.email_app_password_env)

    def get_location_preferences(self) -> dict:
        """Get location preferences from scoring config"""
        return self.scoring.get("location_preferences", {})

    def get_target_seniority(self) -> list[str]:
        """Get target seniority levels"""
        return self.scoring.get("target_seniority", [])

    def get_domain_keywords(self) -> list[str]:
        """Get domain keywords"""
        return self.scoring.get("domain_keywords", [])

    def get_avoid_keywords(self) -> list[str]:
        """Get keywords to avoid"""
        return self.scoring.get("avoid_keywords", [])


class ProfileManager:
    """Manages user profiles from JSON files"""

    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self._profiles: dict[str, Profile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """Load all profile JSON files"""
        if not self.profiles_dir.exists():
            print(f"Warning: Profiles directory not found: {self.profiles_dir}")
            return

        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                profile = self._load_profile_file(profile_file)
                if profile:
                    self._profiles[profile.id] = profile
            except Exception as e:
                print(f"Error loading profile {profile_file}: {e}")

    def _load_profile_file(self, path: Path) -> Profile | None:
        """
        Load a single profile from JSON file with Pydantic validation.

        Raises:
            ValidationError: If profile configuration is invalid
            ValueError: If profile fails validation with user-friendly message
        """
        with open(path) as f:
            data = json.load(f)

        # Validate profile data with Pydantic
        try:
            validated_config = ProfileConfig(**data)
        except ValidationError as e:
            # Convert Pydantic ValidationError to user-friendly message
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"  - {field}: {message}")

            raise ValueError(
                f"Invalid profile configuration in {path.name}:\n" + "\n".join(error_messages)
            ) from e

        # Extract nested fields from validated config
        email_creds = validated_config.email_credentials
        digest = validated_config.digest
        notifications = validated_config.notifications

        return Profile(
            id=validated_config.id,
            name=validated_config.name,
            email=validated_config.email,
            enabled=validated_config.enabled,
            email_username=email_creds.username if email_creds else "",
            email_app_password_env=email_creds.app_password_env if email_creds else "",
            scoring=validated_config.scoring.model_dump(),
            digest_min_grade=digest.min_grade,
            digest_min_score=digest.min_score,
            digest_min_location_score=digest.min_location_score,
            digest_include_grades=digest.include_grades,
            digest_frequency=digest.send_frequency,
            notifications_enabled=notifications.enabled,
            notifications_min_grade=notifications.min_grade,
            notifications_min_score=notifications.min_score,
        )

    def get_profile(self, profile_id: str) -> Profile | None:
        """Get profile by ID"""
        return self._profiles.get(profile_id)

    def get_all_profiles(self) -> list[Profile]:
        """Get all loaded profiles"""
        return list(self._profiles.values())

    def get_enabled_profiles(self) -> list[Profile]:
        """Get all enabled profiles"""
        return [p for p in self._profiles.values() if p.enabled]

    def profile_exists(self, profile_id: str) -> bool:
        """Check if profile exists"""
        return profile_id in self._profiles

    def reload_profiles(self):
        """Reload all profiles from disk"""
        self._profiles.clear()
        self._load_profiles()

    def get_profile_ids(self) -> list[str]:
        """Get list of all profile IDs"""
        return list(self._profiles.keys())


# Singleton instance for convenience
_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """Get or create ProfileManager singleton"""
    global _manager
    if _manager is None:
        _manager = ProfileManager()
    return _manager


if __name__ == "__main__":
    # Test loading profiles
    manager = ProfileManager()

    print(f"Loaded {len(manager.get_all_profiles())} profiles:")
    for profile in manager.get_all_profiles():
        print(f"\n  {profile.id}: {profile.name}")
        print(f"    Email: {profile.email}")
        print(f"    Enabled: {profile.enabled}")
        print(f"    Digest min grade: {profile.digest_min_grade}")
        print(f"    Target seniority: {profile.get_target_seniority()[:3]}...")
        print(f"    Domain keywords: {profile.get_domain_keywords()[:3]}...")
