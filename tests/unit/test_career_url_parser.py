"""
Unit tests for CareerURLParser

Tests URL parsing patterns for major ATS platforms and edge cases.
Target: 80%+ code coverage
"""

import pytest

from src.utils.career_url_parser import CareerURLParser


class TestCareerURLParser:
    """Test suite for CareerURLParser class"""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for tests"""
        return CareerURLParser()

    # Workday Tests
    def test_workday_basic(self, parser):
        """Test basic Workday URL parsing"""
        job_url = "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/Senior-Engineer/JR123456"
        expected = "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
        assert parser.parse(job_url) == expected

    def test_workday_different_subdomain(self, parser):
        """Test Workday with different subdomain (wd2, wd3, etc.)"""
        job_url = "https://figureai.wd12.myworkdayjobs.com/Figure/job/Sunnyvale-CA/Robotics-Engineer/JR987654"
        expected = "https://figureai.wd12.myworkdayjobs.com/Figure"
        assert parser.parse(job_url) == expected

    def test_workday_without_location(self, parser):
        """Test Workday URL without location segment"""
        job_url = "https://company.wd5.myworkdayjobs.com/CompanyJobs/job/JR111111"
        expected = "https://company.wd5.myworkdayjobs.com/CompanyJobs"
        assert parser.parse(job_url) == expected

    # Greenhouse Tests
    def test_greenhouse_job_boards(self, parser):
        """Test Greenhouse job-boards.greenhouse.io pattern"""
        job_url = "https://job-boards.greenhouse.io/figureai/jobs/4123456"
        expected = "https://job-boards.greenhouse.io/figureai"
        assert parser.parse(job_url) == expected

    def test_greenhouse_boards(self, parser):
        """Test Greenhouse boards.greenhouse.io pattern"""
        job_url = "https://boards.greenhouse.io/anthropic/jobs/4987654"
        expected = "https://boards.greenhouse.io/anthropic"
        assert parser.parse(job_url) == expected

    def test_greenhouse_with_details_path(self, parser):
        """Test Greenhouse URL with additional path segments"""
        job_url = "https://job-boards.greenhouse.io/company/jobs/4123456/application"
        expected = "https://job-boards.greenhouse.io/company"
        assert parser.parse(job_url) == expected

    # Lever Tests
    def test_lever_basic(self, parser):
        """Test basic Lever URL parsing"""
        job_url = "https://jobs.lever.co/kuka/abc-123-xyz"
        expected = "https://jobs.lever.co/kuka"
        assert parser.parse(job_url) == expected

    def test_lever_with_query_params(self, parser):
        """Test Lever URL with query parameters"""
        job_url = "https://jobs.lever.co/company/job-id-here?source=linkedin"
        expected = "https://jobs.lever.co/company"
        assert parser.parse(job_url) == expected

    def test_lever_with_fragment(self, parser):
        """Test Lever URL with fragment (#)"""
        job_url = "https://jobs.lever.co/company/job-id#apply"
        expected = "https://jobs.lever.co/company"
        assert parser.parse(job_url) == expected

    # Ashby Tests
    def test_ashby_basic(self, parser):
        """Test basic Ashby URL parsing"""
        job_url = "https://jobs.ashbyhq.com/company/abc-123-xyz"
        expected = "https://jobs.ashbyhq.com/company"
        assert parser.parse(job_url) == expected

    # SmartRecruiters Tests
    def test_smartrecruiters_basic(self, parser):
        """Test basic SmartRecruiters URL parsing"""
        job_url = "https://jobs.smartrecruiters.com/Company/123456789"
        expected = "https://jobs.smartrecruiters.com/Company"
        assert parser.parse(job_url) == expected

    def test_smartrecruiters_with_company_spaces(self, parser):
        """Test SmartRecruiters with company name containing encoded spaces"""
        job_url = "https://jobs.smartrecruiters.com/CompanyName/987654321"
        expected = "https://jobs.smartrecruiters.com/CompanyName"
        assert parser.parse(job_url) == expected

    # Generic Fallback Tests
    def test_generic_jobs_path(self, parser):
        """Test generic /jobs/ID pattern fallback"""
        job_url = "https://company.com/jobs/12345"
        # Should return base URL + /jobs
        result = parser.parse(job_url)
        assert result == "https://company.com/jobs"

    def test_generic_careers_path(self, parser):
        """Test generic /careers/ID pattern fallback"""
        job_url = "https://company.com/careers/senior-engineer-12345"
        # Should return base URL + /jobs (standardized)
        result = parser.parse(job_url)
        assert result in ["https://company.com/jobs", "https://company.com"]

    def test_generic_posting_path(self, parser):
        """Test generic /posting/ID pattern fallback"""
        job_url = "https://company.com/posting/123456"
        result = parser.parse(job_url)
        assert result == "https://company.com/jobs"

    # Edge Cases
    def test_empty_url(self, parser):
        """Test empty URL returns None"""
        assert parser.parse("") is None

    def test_none_url(self, parser):
        """Test None URL returns None"""
        assert parser.parse(None) is None

    def test_invalid_url(self, parser):
        """Test invalid URL format"""
        result = parser.parse("not-a-url")
        # Should either return None or attempt generic fallback
        assert result is None or result.startswith("http")

    def test_url_with_trailing_slash(self, parser):
        """Test URL with trailing slash is normalized"""
        job_url = "https://jobs.lever.co/company/job-id/"
        expected = "https://jobs.lever.co/company"
        assert parser.parse(job_url) == expected

    def test_url_case_insensitive(self, parser):
        """Test URL parsing is case-insensitive"""
        job_url = "https://JOBS.LEVER.CO/Company/job-id"
        expected = "https://JOBS.LEVER.CO/Company"
        result = parser.parse(job_url)
        assert result.lower() == expected.lower()

    # Batch Processing Tests
    def test_parse_batch_multiple_urls(self, parser):
        """Test batch parsing of multiple URLs"""
        job_urls = [
            "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/12345",
            "https://job-boards.greenhouse.io/figureai/jobs/4123456",
            "https://jobs.lever.co/kuka/abc-123",
        ]

        results = parser.parse_batch(job_urls)

        assert len(results) == 3
        assert (
            results[job_urls[0]] == "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
        )
        assert results[job_urls[1]] == "https://job-boards.greenhouse.io/figureai"
        assert results[job_urls[2]] == "https://jobs.lever.co/kuka"

    def test_parse_batch_with_failures(self, parser):
        """Test batch parsing handles failures gracefully"""
        job_urls = [
            "https://jobs.lever.co/company/job-id",
            "",  # Should return None
            "invalid-url",  # Should return None or fallback
        ]

        results = parser.parse_batch(job_urls)

        assert len(results) == 3
        assert results[job_urls[0]] == "https://jobs.lever.co/company"
        assert results[job_urls[1]] is None

    # Real-World Examples from Robotics Companies
    def test_real_world_boston_dynamics(self, parser):
        """Test real Boston Dynamics Workday URL"""
        job_url = "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-Office/Staff-Software-Engineer_R5678"
        expected = "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
        assert parser.parse(job_url) == expected

    def test_real_world_figure(self, parser):
        """Test real Figure.ai Greenhouse URL"""
        job_url = "https://job-boards.greenhouse.io/figureai/jobs/4404444008"
        expected = "https://job-boards.greenhouse.io/figureai"
        assert parser.parse(job_url) == expected

    def test_real_world_sanctuary(self, parser):
        """Test real Sanctuary AI Lever URL"""
        job_url = "https://jobs.lever.co/sanctuaryai/abc-def-123"
        expected = "https://jobs.lever.co/sanctuaryai"
        assert parser.parse(job_url) == expected

    # URL Validation Tests (optional feature)
    def test_is_valid_url_http(self, parser):
        """Test URL validation for HTTP URL"""
        assert parser._is_valid_url("http://example.com") is True

    def test_is_valid_url_https(self, parser):
        """Test URL validation for HTTPS URL"""
        assert parser._is_valid_url("https://example.com") is True

    def test_is_valid_url_no_scheme(self, parser):
        """Test URL validation fails without scheme"""
        assert parser._is_valid_url("example.com") is False

    def test_is_valid_url_invalid_scheme(self, parser):
        """Test URL validation fails with invalid scheme"""
        assert parser._is_valid_url("ftp://example.com") is False

    def test_is_valid_url_empty(self, parser):
        """Test URL validation fails for empty string"""
        assert parser._is_valid_url("") is False


class TestCareerURLParserPatterns:
    """Test specific pattern recognition capabilities"""

    @pytest.fixture
    def parser(self):
        return CareerURLParser()

    def test_pattern_priority_workday_over_generic(self, parser):
        """Test that Workday pattern takes priority over generic fallback"""
        job_url = "https://company.wd1.myworkdayjobs.com/CompanyJobs/job/Location/Title/JR123"
        result = parser.parse(job_url)
        # Should match Workday pattern, not fall back to generic
        assert "myworkdayjobs.com/CompanyJobs" in result
        assert result.endswith("/CompanyJobs")

    def test_pattern_recognition_greenhouse_variants(self, parser):
        """Test that both Greenhouse URL variants are recognized"""
        urls = [
            "https://job-boards.greenhouse.io/company/jobs/123",
            "https://boards.greenhouse.io/company/jobs/123",
        ]
        for url in urls:
            result = parser.parse(url)
            assert "greenhouse.io/company" in result

    def test_generic_fallback_last_resort(self, parser):
        """Test that generic fallback is used when no patterns match"""
        job_url = "https://unknown-ats.com/openings/12345"
        result = parser.parse(job_url)
        # Should use generic fallback
        assert result is not None
        assert "unknown-ats.com" in result
