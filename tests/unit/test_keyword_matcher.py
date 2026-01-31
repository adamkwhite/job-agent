"""
Unit tests for KeywordMatcher utility

Tests both word boundary and substring matching modes to ensure:
- Correct matching behavior
- Case insensitivity
- Word boundary prevention of false positives
- Substring matching flexibility
"""

import pytest

from src.utils.keyword_matcher import KeywordMatcher


class TestWordBoundaryMatching:
    """Test word boundary matching mode (default)"""

    def test_exact_word_match(self):
        """Word boundary matching matches whole words"""
        matcher = KeywordMatcher(["vp", "director", "chief"])

        assert matcher.has_any("vp of engineering") is True
        assert matcher.has_any("director of product") is True
        assert matcher.has_any("chief technology officer") is True

    def test_prevents_substring_false_positives(self):
        """Word boundary matching prevents false positives"""
        matcher = KeywordMatcher(["vp", "chief"])

        # "vp" should NOT match "supervisor"
        assert matcher.has_any("supervisor of engineering") is False

        # "chief" should NOT match "mischief"
        assert matcher.has_any("mischief maker") is False

    def test_matches_with_punctuation(self):
        """Word boundary matching handles punctuation"""
        matcher = KeywordMatcher(["vp", "director"])

        assert matcher.has_any("VP, Engineering") is True
        assert matcher.has_any("VP-Product") is True
        assert matcher.has_any("Director (Engineering)") is True

    def test_case_insensitive(self):
        """Word boundary matching is case insensitive"""
        matcher = KeywordMatcher(["robotics", "automation"])

        assert matcher.has_any("ROBOTICS Engineer") is True
        assert matcher.has_any("Automation Specialist") is True
        assert matcher.has_any("RoBoTiCs") is True

    def test_count_matches_word_boundary(self):
        """count_matches counts word boundary matches"""
        matcher = KeywordMatcher(["robotics", "automation", "hardware", "iot"])

        assert matcher.count_matches("robotics automation engineer") == 2
        assert matcher.count_matches("hardware iot startup") == 2
        assert matcher.count_matches("software engineering") == 0

    def test_matches_returns_matched_keywords(self):
        """matches() returns list of matched keywords"""
        matcher = KeywordMatcher(["robotics", "automation", "hardware"])

        matched = matcher.matches("robotics automation company")
        assert set(matched) == {"robotics", "automation"}

        matched = matcher.matches("hardware startup")
        assert matched == ["hardware"]

        matched = matcher.matches("software company")
        assert matched == []

    def test_empty_text(self):
        """Word boundary matching handles empty text"""
        matcher = KeywordMatcher(["vp", "director"])

        assert matcher.has_any("") is False
        assert matcher.count_matches("") == 0
        assert matcher.matches("") == []

    def test_empty_keywords(self):
        """Matcher handles empty keyword list"""
        matcher = KeywordMatcher([])

        assert matcher.has_any("vp of engineering") is False
        assert matcher.count_matches("director of product") == 0
        assert matcher.matches("chief engineer") == []


class TestSubstringMatching:
    """Test substring matching mode"""

    def test_substring_matches(self):
        """Substring mode matches partial words"""
        matcher = KeywordMatcher(["robot", "auto"])

        # Substring mode DOES match partials
        assert matcher.has_any("robotics engineer", mode="substring") is True
        assert matcher.has_any("automation specialist", mode="substring") is True

    def test_substring_vs_word_boundary(self):
        """Substring mode is more permissive than word boundary"""
        matcher = KeywordMatcher(["robot"])

        # Word boundary: "robot" does NOT match "robotics" (whole word only)
        assert matcher.has_any("robotics engineer", mode="word_boundary") is False

        # Substring: "robot" DOES match "robotics" (partial match)
        assert matcher.has_any("robotics engineer", mode="substring") is True

    def test_substring_count_matches(self):
        """count_matches works with substring mode"""
        matcher = KeywordMatcher(["robot", "auto", "hard"])

        # Matches "robot" in "robotics", "auto" in "automation", "hard" in "hardware"
        count = matcher.count_matches("robotics automation hardware", mode="substring")
        assert count == 3

    def test_substring_matches_returns_keywords(self):
        """matches() returns matched keywords in substring mode"""
        matcher = KeywordMatcher(["robot", "auto"])

        matched = matcher.matches("robotics automation", mode="substring")
        assert set(matched) == {"robot", "auto"}

    def test_substring_case_insensitive(self):
        """Substring matching is case insensitive"""
        matcher = KeywordMatcher(["robot", "auto"])

        assert matcher.has_any("ROBOTICS", mode="substring") is True
        assert matcher.has_any("AUTOMATION", mode="substring") is True


class TestHasKeywordMethod:
    """Test has_keyword() convenience method"""

    def test_has_keyword_word_boundary(self):
        """has_keyword() checks single keyword with word boundary"""
        matcher = KeywordMatcher([])  # Empty matcher, use has_keyword directly

        assert matcher.has_keyword("vp of engineering", "vp") is True
        assert matcher.has_keyword("supervisor role", "vp") is False

    def test_has_keyword_substring(self):
        """has_keyword() checks single keyword with substring"""
        matcher = KeywordMatcher([])

        assert matcher.has_keyword("robotics engineer", "robot", mode="substring") is True
        assert matcher.has_keyword("automation specialist", "auto", mode="substring") is True

    def test_has_keyword_case_insensitive(self):
        """has_keyword() is case insensitive"""
        matcher = KeywordMatcher([])

        assert matcher.has_keyword("VP of Engineering", "vp") is True
        assert matcher.has_keyword("ROBOTICS", "robotics") is True

    def test_has_keyword_empty_inputs(self):
        """has_keyword() handles empty inputs"""
        matcher = KeywordMatcher([])

        assert matcher.has_keyword("", "vp") is False
        assert matcher.has_keyword("vp of engineering", "") is False
        assert matcher.has_keyword("", "") is False


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_invalid_mode_raises_error(self):
        """Invalid mode raises ValueError"""
        matcher = KeywordMatcher(["vp"])

        with pytest.raises(ValueError, match="Invalid mode"):
            matcher.has_any("vp of engineering", mode="invalid")

        with pytest.raises(ValueError, match="Invalid mode"):
            matcher.count_matches("director", mode="fuzzy")

        with pytest.raises(ValueError, match="Invalid mode"):
            matcher.matches("chief", mode="regex")

    def test_special_regex_characters(self):
        """Handles keywords with special regex characters"""
        # Note: Word boundary mode doesn't work well with non-word chars like "++"
        # Use substring mode for these special cases
        matcher = KeywordMatcher(["c++", "r&d", ".net"])

        # Should escape special characters in substring mode
        assert matcher.has_any("c++ developer", mode="substring") is True
        assert matcher.has_any("r&d engineer", mode="substring") is True
        assert matcher.has_any(".net specialist", mode="substring") is True

    def test_multiword_keywords(self):
        """Handles multi-word keywords"""
        matcher = KeywordMatcher(["machine learning", "data science"])

        assert matcher.has_any("machine learning engineer") is True
        assert matcher.has_any("data science specialist") is True

    def test_none_text(self):
        """Handles None text gracefully"""
        matcher = KeywordMatcher(["vp", "director"])

        # Should handle None as empty
        assert matcher.has_any(None) is False
        assert matcher.count_matches(None) == 0
        assert matcher.matches(None) == []

    def test_keywords_lowercased_on_init(self):
        """Keywords are lowercased during initialization"""
        matcher = KeywordMatcher(["VP", "Director", "CHIEF"])

        # Should match regardless of case
        assert matcher.has_any("vp of engineering") is True
        assert matcher.has_any("Director of Product") is True
        assert matcher.has_any("CHIEF Technology Officer") is True


class TestPerformance:
    """Test performance characteristics"""

    def test_large_keyword_list(self):
        """Matcher handles large keyword lists efficiently"""
        # Create matcher with 100 keywords
        keywords = [f"keyword{i}" for i in range(100)]
        matcher = KeywordMatcher(keywords)

        # Should complete quickly (pytest will timeout if too slow)
        result = matcher.has_any("keyword50 in the middle")
        assert result is True

        count = matcher.count_matches("keyword10 keyword20 keyword99")
        assert count == 3

    def test_long_text(self):
        """Matcher handles long text efficiently"""
        matcher = KeywordMatcher(["robotics", "automation", "hardware"])

        # Create very long text
        long_text = "software " * 1000 + "robotics automation"

        # Should find matches even in long text
        assert matcher.has_any(long_text) is True
        assert matcher.count_matches(long_text) == 2
