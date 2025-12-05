"""
Unit tests for profile digest email formatting helpers

Tests the formatting helper functions in send_profile_digest.py that format
profile data for email digest footers.
Addresses Issue #103 - Generic scoring explanations in digest emails.
"""

from unittest.mock import MagicMock

from src.send_profile_digest import (
    _format_domain_list,
    _format_location_prefs,
    _format_role_types,
    _format_seniority_list,
)


class TestFormatSeniorityList:
    """Test _format_seniority_list() helper"""

    def test_format_short_list(self):
        """Test formatting with list shorter than max"""
        profile = MagicMock()
        profile.get_target_seniority.return_value = ["vp", "director", "head of"]

        result = _format_seniority_list(profile, max_items=7)
        assert result == "Vp, Director, Head Of"

    def test_format_long_list_with_truncation(self):
        """Test formatting with list longer than max (adds ...)"""
        profile = MagicMock()
        profile.get_target_seniority.return_value = [
            "vp",
            "director",
            "head of",
            "executive",
            "chief",
            "cto",
            "cpo",
            "principal",
        ]

        result = _format_seniority_list(profile, max_items=5)
        assert result == "Vp, Director, Head Of, Executive, Chief..."
        assert "Principal" not in result

    def test_format_empty_list(self):
        """Test formatting with empty seniority list"""
        profile = MagicMock()
        profile.get_target_seniority.return_value = []

        result = _format_seniority_list(profile, max_items=7)
        assert result == ""

    def test_format_single_item(self):
        """Test formatting with single item"""
        profile = MagicMock()
        profile.get_target_seniority.return_value = ["director"]

        result = _format_seniority_list(profile, max_items=7)
        assert result == "Director"

    def test_format_title_case_conversion(self):
        """Test that items are converted to title case"""
        profile = MagicMock()
        profile.get_target_seniority.return_value = ["vice president", "chief technology officer"]

        result = _format_seniority_list(profile, max_items=7)
        assert result == "Vice President, Chief Technology Officer"


class TestFormatDomainList:
    """Test _format_domain_list() helper"""

    def test_format_short_domain_list(self):
        """Test formatting with list shorter than max"""
        profile = MagicMock()
        profile.get_domain_keywords.return_value = ["robotics", "automation", "IoT"]

        result = _format_domain_list(profile, max_items=10)
        assert result == "Robotics, Automation, Iot"

    def test_format_long_domain_list_with_truncation(self):
        """Test formatting with list longer than max (adds ...)"""
        profile = MagicMock()
        profile.get_domain_keywords.return_value = [
            "robotics",
            "automation",
            "hardware",
            "embedded",
            "IoT",
            "mechatronics",
            "manufacturing",
            "machine learning",
            "computer vision",
            "perception",
            "control systems",
        ]

        result = _format_domain_list(profile, max_items=7)
        assert result.endswith("...")
        assert result.count(",") == 6  # 7 items = 6 commas

    def test_format_empty_domain_list(self):
        """Test formatting with empty domain list"""
        profile = MagicMock()
        profile.get_domain_keywords.return_value = []

        result = _format_domain_list(profile, max_items=10)
        assert result == ""

    def test_format_domains_with_spaces(self):
        """Test formatting domains with spaces (title case applied)"""
        profile = MagicMock()
        profile.get_domain_keywords.return_value = [
            "machine learning",
            "computer vision",
            "deep tech",
        ]

        result = _format_domain_list(profile, max_items=10)
        assert result == "Machine Learning, Computer Vision, Deep Tech"


class TestFormatRoleTypes:
    """Test _format_role_types() helper"""

    def test_format_multiple_role_types(self):
        """Test formatting multiple role types with priority order"""
        profile = MagicMock()
        profile.scoring = {
            "role_types": {
                "engineering_leadership": {"keywords": ["vp engineering"], "points": 20},
                "product_leadership": {"keywords": ["vp product"], "points": 15},
            }
        }

        result = _format_role_types(profile)
        assert result == "Engineering Leadership > Product Leadership"

    def test_format_single_role_type(self):
        """Test formatting single role type"""
        profile = MagicMock()
        profile.scoring = {
            "role_types": {"engineering_leadership": {"keywords": ["vp engineering"], "points": 20}}
        }

        result = _format_role_types(profile)
        assert result == "Engineering Leadership"

    def test_format_empty_role_types(self):
        """Test formatting with no role types defined"""
        profile = MagicMock()
        profile.scoring = {"role_types": {}}

        result = _format_role_types(profile)
        assert result == "Not specified"

    def test_format_missing_role_types_key(self):
        """Test formatting when role_types key is missing"""
        profile = MagicMock()
        profile.scoring = {}

        result = _format_role_types(profile)
        assert result == "Not specified"

    def test_format_underscores_to_spaces(self):
        """Test that underscores are converted to spaces"""
        profile = MagicMock()
        profile.scoring = {
            "role_types": {
                "technical_leadership": {"keywords": [], "points": 20},
                "strategic_leadership": {"keywords": [], "points": 15},
            }
        }

        result = _format_role_types(profile)
        assert "Technical Leadership" in result
        assert "Strategic Leadership" in result
        assert "_" not in result


class TestFormatLocationPrefs:
    """Test _format_location_prefs() helper"""

    def test_format_remote_with_cities_and_regions(self):
        """Test formatting remote with preferred cities and regions"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": ["remote", "work from home"],
                "hybrid_keywords": [],
                "preferred_cities": ["Toronto", "Waterloo", "Burlington", "Ottawa"],
                "preferred_regions": ["Ontario", "Canada"],
            }
        }

        result = _format_location_prefs(profile)
        assert result == "Remote (Toronto, Waterloo, Burlington, Ontario, Canada)"

    def test_format_remote_without_locations(self):
        """Test formatting remote without specific locations"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": [],
                "preferred_cities": [],
                "preferred_regions": [],
            }
        }

        result = _format_location_prefs(profile)
        assert result == "Remote"

    def test_format_hybrid_only(self):
        """Test formatting hybrid preference only"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": [],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            }
        }

        result = _format_location_prefs(profile)
        assert result == "Hybrid"

    def test_format_remote_and_hybrid(self):
        """Test formatting both remote and hybrid"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["Toronto"],
                "preferred_regions": [],
            }
        }

        result = _format_location_prefs(profile)
        assert result == "Remote (Toronto), Hybrid"

    def test_format_truncates_long_lists(self):
        """Test that long city/region lists are truncated"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": [],
                "preferred_cities": ["Toronto", "Waterloo", "Burlington", "Ottawa", "Kitchener"],
                "preferred_regions": ["Ontario", "Canada", "USA"],
            }
        }

        result = _format_location_prefs(profile)
        # Should only show first 3 cities + 2 regions = 5 total
        assert result.count(",") <= 5  # At most 5 commas for 6 items (remote + 5 locations)

    def test_format_empty_preferences(self):
        """Test formatting with no location preferences"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": [],
                "hybrid_keywords": [],
                "preferred_cities": [],
                "preferred_regions": [],
            }
        }

        result = _format_location_prefs(profile)
        assert result == "Not specified"

    def test_format_missing_location_key(self):
        """Test formatting when location_preferences key is missing"""
        profile = MagicMock()
        profile.scoring = {}

        result = _format_location_prefs(profile)
        assert result == "Not specified"

    def test_format_title_cases_locations(self):
        """Test that city/region names are title-cased"""
        profile = MagicMock()
        profile.scoring = {
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": [],
                "preferred_cities": ["toronto", "waterloo"],
                "preferred_regions": ["ontario"],
            }
        }

        result = _format_location_prefs(profile)
        assert "Toronto" in result
        assert "Waterloo" in result
        assert "Ontario" in result
        assert "toronto" not in result  # Should not have lowercase
