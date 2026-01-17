"""
Unit tests for Ministry of Testing scraper
Tests for company extraction and job parsing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scrapers.ministry_of_testing_scraper import MinistryOfTestingScraper


class TestCompanyExtraction:
    """Test company name extraction from job title and location"""

    def test_extract_company_from_city_location(self):
        """Should NOT extract city names as company names"""
        scraper = MinistryOfTestingScraper()

        # Test case 1: "Toronto, Ontario" should NOT return "Toronto" as company
        company = scraper._extract_company(
            title="Quality Assurance (QA) Analyst", location="Toronto, Ontario"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

        # Test case 2: "Austin, TX (Remote)" should NOT return "Austin" as company
        company = scraper._extract_company(
            title="Senior Software Quality Assurance Engineer", location="Austin, TX (Remote)"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

        # Test case 3: "San Francisco, CA" should NOT return "San Francisco"
        company = scraper._extract_company(
            title="QA Automation Engineer", location="San Francisco, CA"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

    def test_extract_company_from_title_with_hyphen(self):
        """Should extract company from 'Company - Title' format"""
        scraper = MinistryOfTestingScraper()

        company = scraper._extract_company(
            title="Acme Corp - Senior QA Engineer", location="Remote"
        )
        assert company == "Acme Corp", f"Expected 'Acme Corp' but got '{company}'"

    def test_extract_company_unknown_fallback(self):
        """Should return 'Unknown Company' when no company found"""
        scraper = MinistryOfTestingScraper()

        company = scraper._extract_company(title="QA Engineer", location="United States")
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"


class TestJobParsing:
    """Test parsing jobs from markdown"""

    def test_parse_qa_jobs_from_markdown(self):
        """Should parse QA jobs with correct title, location, and links"""
        scraper = MinistryOfTestingScraper()

        markdown = """
[Quality Assurance (QA) Analyst](https://www.ministryoftesting.com/jobs/qa-analyst)

Toronto, Ontario

16 Jan

[Senior QA Engineer](https://www.ministryoftesting.com/jobs/senior-qa-engineer)

Remote

15 Jan
"""

        jobs = scraper.parse_jobs_from_page(markdown, target_locations=["Canada", "Remote"])

        # Should find 2 jobs
        assert len(jobs) == 2, f"Expected 2 jobs but got {len(jobs)}"

        # Check first job
        job1 = jobs[0]
        assert job1.title == "Quality Assurance (QA) Analyst"
        assert job1.location == "Toronto, Ontario"
        assert job1.link == "https://www.ministryoftesting.com/jobs/qa-analyst"
        assert job1.company != "Toronto", "Company should NOT be 'Toronto'"

        # Check second job
        job2 = jobs[1]
        assert job2.title == "Senior QA Engineer"
        assert job2.location == "Remote"
        assert job2.link == "https://www.ministryoftesting.com/jobs/senior-qa-engineer"

    def test_location_filtering(self):
        """Should filter jobs by target locations"""
        scraper = MinistryOfTestingScraper()

        markdown = """
[QA Engineer](https://www.ministryoftesting.com/jobs/qa-1)

Toronto, Ontario

16 Jan

[Test Engineer](https://www.ministryoftesting.com/jobs/test-1)

London, United Kingdom

15 Jan

[QA Analyst](https://www.ministryoftesting.com/jobs/qa-2)

Remote

14 Jan
"""

        # Filter for Canada and Remote only
        jobs = scraper.parse_jobs_from_page(markdown, target_locations=["Canada", "Remote"])

        # Should only get 2 jobs (Toronto + Remote, not London)
        assert len(jobs) == 2, f"Expected 2 jobs but got {len(jobs)}"

        locations = [job.location for job in jobs]
        assert "Toronto, Ontario" in locations
        assert "Remote" in locations
        assert "London, United Kingdom" not in locations
