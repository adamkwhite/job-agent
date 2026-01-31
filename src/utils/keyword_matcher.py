"""
Centralized Keyword Matching Utility

Provides consistent keyword matching across job scoring system with support for:
- Word boundary matching (prevents "vp" matching "supervisor")
- Substring matching (for flexible counting)
- Case-insensitive matching
- Future: Fuzzy matching support
"""

import re
from typing import Literal

MatchMode = Literal["word_boundary", "substring"]


class KeywordMatcher:
    """
    Centralized keyword matching utility

    Supports two matching modes:
    - word_boundary: Uses regex \\b to match whole words only (prevents false positives)
    - substring: Simple case-insensitive substring matching

    Examples:
        >>> matcher = KeywordMatcher(["vp", "director", "chief"])
        >>> matcher.has_any("vp of engineering")  # True (word boundary)
        >>> matcher.has_any("supervisor role")  # False (no match)
        >>>
        >>> matcher = KeywordMatcher(["robot", "automation"])
        >>> matcher.count_matches("robotics automation company")  # 2
    """

    def __init__(self, keywords: list[str]):
        """
        Initialize matcher with list of keywords

        Args:
            keywords: List of keywords to match (will be lowercased)
        """
        self.keywords = [kw.lower() for kw in keywords]

    def matches(
        self, text: str, mode: MatchMode = "word_boundary", _threshold: float = 0.8
    ) -> list[str]:
        """
        Find keyword matches in text

        Args:
            text: Text to search in
            mode: Matching mode ("word_boundary" or "substring")
            _threshold: Fuzzy match threshold (0.0-1.0) - FUTURE: not yet implemented

        Returns:
            List of matched keywords from self.keywords
        """
        if not text:
            return []

        text_lower = text.lower()
        matched = []

        for keyword in self.keywords:
            if mode == "word_boundary":
                # Use regex word boundaries to match whole words only
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text_lower):
                    matched.append(keyword)
            elif mode == "substring":
                # Simple substring matching
                if keyword in text_lower:
                    matched.append(keyword)
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'word_boundary' or 'substring'")

        return matched

    def count_matches(self, text: str, mode: MatchMode = "word_boundary") -> int:
        """
        Count keyword matches in text

        Args:
            text: Text to search in
            mode: Matching mode ("word_boundary" or "substring")

        Returns:
            Number of matched keywords
        """
        return len(self.matches(text, mode=mode))

    def has_any(self, text: str, mode: MatchMode = "word_boundary") -> bool:
        """
        Check if any keyword matches in text

        Args:
            text: Text to search in
            mode: Matching mode ("word_boundary" or "substring")

        Returns:
            True if at least one keyword matches
        """
        if not text:
            return False

        text_lower = text.lower()

        for keyword in self.keywords:
            if mode == "word_boundary":
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text_lower):
                    return True
            elif mode == "substring":
                if keyword in text_lower:
                    return True
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'word_boundary' or 'substring'")

        return False

    def has_keyword(self, text: str, keyword: str, mode: MatchMode = "word_boundary") -> bool:
        """
        Check if a single keyword matches in text

        Convenience method for checking a single keyword without creating a new matcher.

        Args:
            text: Text to search in
            keyword: Single keyword to check
            mode: Matching mode ("word_boundary" or "substring")

        Returns:
            True if keyword matches
        """
        if not text or not keyword:
            return False

        text_lower = text.lower()
        keyword_lower = keyword.lower()

        if mode == "word_boundary":
            pattern = r"\b" + re.escape(keyword_lower) + r"\b"
            return bool(re.search(pattern, text_lower))
        elif mode == "substring":
            return keyword_lower in text_lower
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'word_boundary' or 'substring'")
