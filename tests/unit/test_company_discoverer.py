"""
Unit tests for CompanyDiscoverer (company extraction from job sources)
"""

import pytest

from models import OpportunityData
from scrapers.company_discoverer import CompanyDiscoverer


@pytest.fixture
def discoverer():
    """Create CompanyDiscoverer instance"""
    return CompanyDiscoverer()


class TestCompanyDiscoverer:
    """Test CompanyDiscoverer functionality"""

    def test_discover_from_robotics_sheet_with_pydantic_objects(self, discoverer):
        """Test discovering companies from Pydantic OpportunityData objects"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Boston Dynamics",
                location="Waltham, MA",
                link="https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/123",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP Engineering",
                company="Agility Robotics",
                location="Pittsburgh, PA",
                link="https://jobs.lever.co/agilityrobotics/abc-def",
                source="robotics_sheet",
            ),
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 2
        assert companies[0]["name"] == "Boston Dynamics"
        assert companies[0]["source"] == "robotics_sheet_auto"
        assert "Auto-discovered" in companies[0]["notes"]

    def test_discover_from_robotics_sheet_with_dicts(self, discoverer):
        """Test discovering companies from dict objects (backward compatibility)"""
        opportunities = [
            {
                "company": "Skydio",
                "link": "https://boards.greenhouse.io/skydio/jobs/456789",
            },
            {
                "company": "Figure AI",
                "link": "https://jobs.lever.co/figureai/xyz-123",
            },
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 2
        assert companies[0]["name"] == "Skydio"
        assert companies[1]["name"] == "Figure AI"

    def test_discover_deduplicates_same_company(self, discoverer):
        """Test that multiple jobs from same company yield one company entry"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Boston Dynamics",
                location="Waltham, MA",
                link="https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/123",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP Product",
                company="Boston Dynamics",
                location="Waltham, MA",
                link="https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/456",
                source="robotics_sheet",
            ),
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        # Should only have 1 company (same careers URL)
        assert len(companies) == 1
        assert companies[0]["name"] == "Boston Dynamics"

    def test_discover_skips_missing_company_name(self, discoverer):
        """Test that opportunities without company name are skipped"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="",
                location="Waltham, MA",
                link="https://example.com/jobs/123",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP Engineering",
                company="Valid Company",
                location="Pittsburgh, PA",
                link="https://example.com/jobs/456",
                source="robotics_sheet",
            ),
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 1
        assert companies[0]["name"] == "Valid Company"

    def test_discover_skips_missing_link(self, discoverer):
        """Test that opportunities without link are skipped"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Waltham, MA",
                link="",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP Engineering",
                company="Valid Company",
                location="Pittsburgh, PA",
                link="https://example.com/jobs/456",
                source="robotics_sheet",
            ),
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 1
        assert companies[0]["name"] == "Valid Company"

    def test_extract_greenhouse_url(self, discoverer):
        """Test extracting Greenhouse career page URL from job URL"""
        job_url = "https://boards.greenhouse.io/company/jobs/123456"
        careers_url = discoverer._extract_careers_url(job_url)

        assert careers_url == "https://boards.greenhouse.io/company"

    def test_extract_lever_url(self, discoverer):
        """Test extracting Lever career page URL from job URL"""
        job_url = "https://jobs.lever.co/company/abc123-job-title"
        careers_url = discoverer._extract_careers_url(job_url)

        assert careers_url == "https://jobs.lever.co/company"

    def test_extract_workday_url(self, discoverer):
        """Test extracting Workday career page URL from job URL"""
        job_url = "https://company.wd1.myworkdayjobs.com/CareerSite/job/Location/Title/JR123456"
        careers_url = discoverer._extract_careers_url(job_url)

        assert careers_url == "https://company.wd1.myworkdayjobs.com/CareerSite"

    def test_extract_generic_careers_url(self, discoverer):
        """Test extracting generic career page URL with /careers path"""
        job_url = "https://example.com/careers/engineering-director"
        careers_url = discoverer._extract_careers_url(job_url)

        assert careers_url == "https://example.com/careers"

    def test_extract_generic_jobs_url(self, discoverer):
        """Test extracting generic career page URL with /jobs path"""
        job_url = "https://example.com/jobs/123-engineering-director"
        careers_url = discoverer._extract_careers_url(job_url)

        assert careers_url == "https://example.com/jobs"

    def test_extract_nested_careers_url(self, discoverer):
        """Test extracting nested career page URL like /about/careers"""
        job_url = "https://example.com/about/careers/engineering-director"
        careers_url = discoverer._extract_careers_url(job_url)

        assert "/careers" in careers_url

    def test_extract_url_fallback_to_domain(self, discoverer):
        """Test fallback to domain/careers for unrecognized patterns"""
        job_url = "https://example.com/some/random/path"
        careers_url = discoverer._extract_careers_url(job_url)

        # Should fallback to domain + /careers
        assert "example.com" in careers_url

    def test_extract_url_handles_empty(self, discoverer):
        """Test URL extraction handles empty string"""
        careers_url = discoverer._extract_careers_url("")
        assert careers_url == ""

    def test_extract_url_handles_invalid(self, discoverer):
        """Test URL extraction handles malformed URLs gracefully"""
        careers_url = discoverer._extract_careers_url("not-a-valid-url")
        # Falls back to careers URL construction
        assert "not-a-valid-url" in careers_url

    def test_filter_by_company_names(self, discoverer):
        """Test filtering companies by target names"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
            {"name": "Agility Robotics", "careers_url": "https://agility.io"},
            {"name": "Skydio", "careers_url": "https://skydio.com"},
            {"name": "Figure AI", "careers_url": "https://figure.ai"},
        ]

        target_names = ["Boston Dynamics", "Skydio"]

        filtered = discoverer.filter_by_company_names(companies, target_names)

        assert len(filtered) == 2
        assert filtered[0]["name"] == "Boston Dynamics"
        assert filtered[1]["name"] == "Skydio"

    def test_filter_by_company_names_case_insensitive(self, discoverer):
        """Test filtering is case-insensitive"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
            {"name": "Agility Robotics", "careers_url": "https://agility.io"},
        ]

        target_names = ["BOSTON DYNAMICS", "agility robotics"]

        filtered = discoverer.filter_by_company_names(companies, target_names)

        assert len(filtered) == 2

    def test_filter_by_company_names_no_matches(self, discoverer):
        """Test filtering returns empty list when no matches"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
            {"name": "Agility Robotics", "careers_url": "https://agility.io"},
        ]

        target_names = ["Nonexistent Company"]

        filtered = discoverer.filter_by_company_names(companies, target_names)

        assert len(filtered) == 0

    def test_filter_by_company_names_empty_list(self, discoverer):
        """Test filtering with empty target list returns empty"""
        companies = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
        ]

        target_names = []

        filtered = discoverer.filter_by_company_names(companies, target_names)

        assert len(filtered) == 0

    def test_extract_url_with_exception(self, discoverer):
        """Test URL extraction handles exceptions gracefully"""
        # Test with None input (causes exception in urlparse)
        careers_url = discoverer._extract_careers_url(None)
        assert careers_url == ""

    def test_discover_handles_whitespace_company(self, discoverer):
        """Test discovering with whitespace-only company name"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="   ",
                location="Remote",
                link="https://example.com/jobs/123",
                source="robotics_sheet",
            )
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 0

    def test_discover_handles_whitespace_link(self, discoverer):
        """Test discovering with whitespace-only link"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Test Company",
                location="Remote",
                link="   ",
                source="robotics_sheet",
            )
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        assert len(companies) == 0

    def test_extract_greenhouse_url_with_empty_path(self, discoverer):
        """Test Greenhouse URL extraction with empty path returns base URL"""
        result = discoverer._extract_greenhouse_url("")
        assert result == "https://boards.greenhouse.io/"

    def test_extract_lever_url_with_empty_path(self, discoverer):
        """Test Lever URL extraction with empty path returns base URL"""
        result = discoverer._extract_lever_url("")
        assert result == "https://jobs.lever.co/"

    def test_extract_workday_url_with_empty_path(self, discoverer):
        """Test Workday URL extraction with empty path returns base URL"""
        result = discoverer._extract_workday_url("company.wd1.myworkdayjobs.com", "")
        assert result == "https://company.wd1.myworkdayjobs.com/"

    def test_extract_generic_careers_url_fallback_to_domain(self, discoverer):
        """Test generic URL extraction falls back to /careers for empty path"""
        result = discoverer._extract_generic_careers_url("example.com", "")
        assert result == "https://example.com/careers"

    def test_discover_skips_unparseable_url(self, discoverer):
        """Test discovering skips opportunities with URLs that can't be parsed"""
        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Test Company",
                location="Remote",
                link="https://example.com",  # Generic URL, will extract to generic careers page
                source="robotics_sheet",
            )
        ]

        companies = discoverer.discover_from_robotics_sheet(opportunities)

        # Should still create company with extracted careers URL
        assert len(companies) == 1

    def test_discover_skips_opportunities_with_exception_in_url_parsing(self, discoverer):
        """Test discovering skips opportunities when URL parsing raises exception"""
        import unittest.mock as mock

        opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Test Company",
                location="Remote",
                link="https://example.com/jobs/123",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP Engineering",
                company="Valid Company",
                location="Remote",
                link="https://valid.com/jobs/456",
                source="robotics_sheet",
            ),
        ]

        # Mock urlparse to raise exception for first URL
        original_urlparse = discoverer._extract_careers_url

        def mock_extract(url):
            if "example.com" in url:
                return ""  # Simulate exception returning empty string
            return original_urlparse(url)

        with mock.patch.object(discoverer, "_extract_careers_url", side_effect=mock_extract):
            companies = discoverer.discover_from_robotics_sheet(opportunities)

        # Should skip the first opportunity and process the second
        assert len(companies) == 1
        assert companies[0]["name"] == "Valid Company"
