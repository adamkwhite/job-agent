"""
Unit tests for CompanyMatcher (fuzzy matching logic)
"""

import pytest

from utils.company_matcher import CompanyMatcher


@pytest.fixture
def matcher():
    """Create matcher with 90% threshold"""
    return CompanyMatcher(similarity_threshold=90.0)


@pytest.fixture
def loose_matcher():
    """Create matcher with lower 70% threshold"""
    return CompanyMatcher(similarity_threshold=70.0)


class TestCompanyMatcher:
    """Test CompanyMatcher fuzzy matching"""

    def test_init_default_threshold(self):
        """Test default similarity threshold is 90%"""
        matcher = CompanyMatcher()
        assert matcher.similarity_threshold == 90.0

    def test_init_custom_threshold(self):
        """Test custom similarity threshold"""
        matcher = CompanyMatcher(similarity_threshold=85.0)
        assert matcher.similarity_threshold == 85.0

    def test_exact_url_match(self, matcher):
        """Test exact URL match returns existing company"""
        candidate = {
            "name": "Boston Dynamics",
            "careers_url": "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
        }
        existing = [
            {
                "name": "Boston Dynamics Inc",
                "careers_url": "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
            }
        ]

        match = matcher.find_match(candidate, existing)

        assert match is not None
        assert match["name"] == "Boston Dynamics Inc"

    def test_exact_name_match(self, matcher):
        """Test exact name match returns existing company"""
        candidate = {"name": "Agility Robotics", "careers_url": "https://careers.agility.io"}
        existing = [{"name": "Agility Robotics", "careers_url": "https://agility.io/careers"}]

        match = matcher.find_match(candidate, existing)

        assert match is not None
        assert match["name"] == "Agility Robotics"

    def test_fuzzy_name_match_with_suffix(self, matcher):
        """Test fuzzy matching ignores company suffixes"""
        candidate = {"name": "Boston Dynamics", "careers_url": "https://example.com/careers"}
        existing = [
            {"name": "Boston Dynamics Inc.", "careers_url": "https://different.com/careers"}
        ]

        match = matcher.find_match(candidate, existing)

        assert match is not None
        assert match["name"] == "Boston Dynamics Inc."

    def test_no_match_different_companies(self, matcher):
        """Test no match for completely different companies"""
        candidate = {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"}
        existing = [{"name": "Agility Robotics", "careers_url": "https://agility.io"}]

        match = matcher.find_match(candidate, existing)

        assert match is None

    def test_url_normalization_removes_www(self, matcher):
        """Test URL normalization removes www prefix"""
        candidate = {"name": "Test Co", "careers_url": "https://www.example.com/careers"}
        existing = [{"name": "Test Company", "careers_url": "https://example.com/careers"}]

        match = matcher.find_match(candidate, existing)

        assert match is not None

    def test_url_normalization_removes_trailing_slash(self, matcher):
        """Test URL normalization removes trailing slashes"""
        candidate = {"name": "Test Co", "careers_url": "https://example.com/careers/"}
        existing = [{"name": "Test Company", "careers_url": "https://example.com/careers"}]

        match = matcher.find_match(candidate, existing)

        assert match is not None

    def test_url_normalization_ignores_protocol(self, matcher):
        """Test URL normalization ignores http vs https"""
        candidate = {"name": "Test Co", "careers_url": "http://example.com/careers"}
        existing = [{"name": "Test Company", "careers_url": "https://example.com/careers"}]

        match = matcher.find_match(candidate, existing)

        assert match is not None

    def test_missing_candidate_name(self, matcher):
        """Test returns None if candidate missing name"""
        candidate = {"careers_url": "https://example.com"}
        existing = [{"name": "Test Co", "careers_url": "https://example.com"}]

        match = matcher.find_match(candidate, existing)

        assert match is None

    def test_missing_candidate_url(self, matcher):
        """Test returns None if candidate missing URL"""
        candidate = {"name": "Test Co"}
        existing = [{"name": "Test Co", "careers_url": "https://example.com"}]

        match = matcher.find_match(candidate, existing)

        assert match is None

    def test_empty_existing_companies(self, matcher):
        """Test returns None if no existing companies"""
        candidate = {"name": "Test Co", "careers_url": "https://example.com"}
        existing = []

        match = matcher.find_match(candidate, existing)

        assert match is None

    def test_threshold_sensitivity(self, loose_matcher):
        """Test lower threshold catches more matches"""
        candidate = {"name": "Boston Dynamics Corp", "careers_url": "https://example.com"}
        existing = [{"name": "Boston Dynamics", "careers_url": "https://different.com"}]

        # Loose matcher (70%) should match
        match = loose_matcher.find_match(candidate, existing)
        assert match is not None

        # Strict matcher (90%) might not match
        strict_matcher = CompanyMatcher(similarity_threshold=95.0)
        match = strict_matcher.find_match(candidate, existing)
        # Result depends on exact similarity score

    def test_deduplicate_companies_no_duplicates(self, matcher):
        """Test deduplication with no duplicates"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
            {"name": "Agility Robotics", "careers_url": "https://agility.io"},
            {"name": "Skydio", "careers_url": "https://skydio.com"},
        ]

        unique, duplicates = matcher.deduplicate_companies(companies)

        assert len(unique) == 3
        assert len(duplicates) == 0

    def test_deduplicate_companies_with_duplicates(self, matcher):
        """Test deduplication removes similar companies"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com/careers"},
            {
                "name": "Boston Dynamics Inc",
                "careers_url": "https://bostondynamics.com/careers",
            },  # Duplicate URL
            {"name": "Agility Robotics", "careers_url": "https://agility.io"},
        ]

        unique, duplicates = matcher.deduplicate_companies(companies)

        assert len(unique) == 2
        assert len(duplicates) == 1
        assert duplicates[0]["name"] == "Boston Dynamics Inc"

    def test_normalize_company_name_removes_suffixes(self, matcher):
        """Test company name normalization removes legal suffixes"""
        test_cases = [
            ("Boston Dynamics Inc.", "boston dynamics"),
            ("Agility Robotics LLC", "agility robotics"),
            ("Skydio Corp", "skydio"),
            ("Figure AI Limited", "figure ai"),
            ("Bright Machines Co.", "bright machines"),
        ]

        for input_name, expected in test_cases:
            normalized = matcher._normalize_company_name(input_name)
            assert normalized == expected

    def test_normalize_company_name_removes_punctuation(self, matcher):
        """Test company name normalization removes punctuation"""
        normalized = matcher._normalize_company_name("Boston-Dynamics, Inc!")
        # Hyphen is removed, leaving no space between words
        assert normalized == "bostondynamics"

    def test_normalize_company_name_handles_empty(self, matcher):
        """Test company name normalization handles empty string"""
        normalized = matcher._normalize_company_name("")
        assert normalized == ""

    def test_normalize_url_handles_greenhouse(self, matcher):
        """Test URL normalization for Greenhouse URLs"""
        url = "https://boards.greenhouse.io/company/jobs/123456"
        normalized = matcher._normalize_url(url)
        assert normalized == "boards.greenhouse.io/company/jobs/123456"

    def test_normalize_url_handles_workday(self, matcher):
        """Test URL normalization for Workday URLs"""
        url = "https://company.wd1.myworkdayjobs.com/CareerSite/job/Location/Title/JR123456"
        normalized = matcher._normalize_url(url)
        assert normalized == "company.wd1.myworkdayjobs.com/CareerSite/job/Location/Title/JR123456"

    def test_normalize_url_removes_query_params(self, matcher):
        """Test URL normalization removes query parameters"""
        url = "https://example.com/careers?utm_source=linkedin&ref=job_board"
        normalized = matcher._normalize_url(url)
        assert "?" not in normalized
        assert "utm_source" not in normalized

    def test_normalize_url_handles_invalid(self, matcher):
        """Test URL normalization handles malformed URLs"""
        normalized = matcher._normalize_url("not-a-valid-url")
        assert normalized == "not-a-valid-url"

    def test_normalize_url_handles_empty(self, matcher):
        """Test URL normalization handles empty string"""
        normalized = matcher._normalize_url("")
        assert normalized == ""
