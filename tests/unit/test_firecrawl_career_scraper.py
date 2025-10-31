"""
Tests for FirecrawlCareerScraper

Tests markdown job extraction from career pages scraped by Firecrawl:
- Pattern 1: Linked jobs with locations (Greenhouse/Lever style)
- Pattern 2: Header-based job listings
- Job title filtering and validation
"""

from src.scrapers.firecrawl_career_scraper import FirecrawlCareerScraper


class TestFirecrawlCareerScraperInit:
    """Test FirecrawlCareerScraper initialization"""

    def test_init(self):
        """Test scraper initializes with correct name"""
        scraper = FirecrawlCareerScraper()
        assert scraper.name == "firecrawl_career_scraper"


class TestJobTitleValidation:
    """Test job title validation logic"""

    def test_is_likely_job_title_with_valid_titles(self):
        """Test valid job titles are recognized"""
        scraper = FirecrawlCareerScraper()

        valid_titles = [
            "Senior Software Engineer",
            "Product Manager",
            "Director of Engineering",
            "Data Scientist",
            "UX Designer",
            "Technical Lead",
            "System Architect",
            "Business Analyst",
        ]

        for title in valid_titles:
            assert scraper._is_likely_job_title(title), f"Failed for: {title}"

    def test_is_likely_job_title_filters_navigation(self):
        """Test navigation/UI text is filtered out"""
        scraper = FirecrawlCareerScraper()

        invalid_texts = [
            "View all jobs",
            "Learn more",
            "Click here",
            "Apply now",
            "Home",
            "Contact us",
        ]

        for text in invalid_texts:
            assert not scraper._is_likely_job_title(text), f"Failed for: {text}"

    def test_is_likely_job_title_filters_generic_words(self):
        """Test generic career page words are filtered"""
        scraper = FirecrawlCareerScraper()

        invalid_texts = [
            "Jobs",
            "Careers",
            "Openings",
            "Opportunities",
            "Department",
            "Location",
            "Filter",
        ]

        for text in invalid_texts:
            assert not scraper._is_likely_job_title(text), f"Failed for: {text}"

    def test_is_likely_job_title_filters_page_elements(self):
        """Test page element text is filtered"""
        scraper = FirecrawlCareerScraper()

        invalid_texts = ["Logo", "Navigation menu", "Website header", "Page footer"]

        for text in invalid_texts:
            assert not scraper._is_likely_job_title(text), f"Failed for: {text}"


class TestMarkdownJobExtraction:
    """Test job extraction from markdown"""

    def test_extract_jobs_pattern1_greenhouse_style(self):
        """Test extracting jobs with Greenhouse/Lever style links"""
        scraper = FirecrawlCareerScraper()

        markdown = """
# Careers

We're hiring!

[Senior Software Engineer

Toronto, Canada](https://boards.greenhouse.io/company/jobs/123)

[Product Manager

Remote](https://boards.greenhouse.io/company/jobs/456)
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "Company Inc"
        )

        assert len(jobs) == 2

        assert jobs[0].title == "Senior Software Engineer"
        assert jobs[0].location == "Toronto, Canada"
        assert "greenhouse.io" in jobs[0].link
        assert jobs[0].company == "Company Inc"

        assert jobs[1].title == "Product Manager"
        assert jobs[1].location == "Remote"

    def test_extract_jobs_pattern1_with_newlines(self):
        """Test extracting jobs with various newline formats"""
        scraper = FirecrawlCareerScraper()

        markdown = r"""
[Director of Engineering\n\nSan Francisco, CA](https://jobs.lever.co/company/123)
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "TechCo"
        )

        assert len(jobs) == 1
        assert jobs[0].title == "Director of Engineering"
        assert jobs[0].location == "San Francisco, CA"

    def test_extract_jobs_pattern2_headers(self):
        """Test extracting jobs from header-based listings"""
        scraper = FirecrawlCareerScraper()

        markdown = """
# Open Positions

We have 5 jobs available

## Senior Backend Engineer

Location: New York, NY

## Staff Product Manager

Location: Boston, MA

## Principal Architect

Location: Seattle, WA
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/jobs", "StartupCo"
        )

        assert len(jobs) == 3

        assert jobs[0].title == "Senior Backend Engineer"
        assert jobs[0].location == "New York, NY"
        assert jobs[0].company == "StartupCo"
        assert jobs[0].link == "https://company.com/jobs"

    def test_extract_jobs_filters_non_job_headers(self):
        """Test that non-job headers are filtered out"""
        scraper = FirecrawlCareerScraper()

        markdown = """
# Careers

We have 3 jobs

## Benefits

## Location

## Senior Software Engineer

San Francisco, CA

## Apply Now
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "TechCorp"
        )

        # Should only extract "Senior Software Engineer"
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Software Engineer"

    def test_extract_jobs_empty_markdown(self):
        """Test extraction from empty markdown"""
        scraper = FirecrawlCareerScraper()

        jobs = scraper._extract_jobs_from_markdown("", "https://company.com/careers", "Company")

        assert len(jobs) == 0

    def test_extract_jobs_no_job_indicators(self):
        """Test markdown without job count indicators returns empty"""
        scraper = FirecrawlCareerScraper()

        markdown = """
# About Us

We are a great company.

## Our Mission

To do great things.
"""

        jobs = scraper._extract_jobs_from_markdown(markdown, "https://company.com/about", "Company")

        assert len(jobs) == 0

    def test_extract_jobs_filters_short_headers(self):
        """Test that short headers are filtered (less than 10 chars)"""
        scraper = FirecrawlCareerScraper()

        markdown = """
We have 2 jobs

## Engineer

## VP of Engineering Operations
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "TechCo"
        )

        # "Engineer" is too short (< 10 chars), only extract the VP role
        assert len(jobs) == 1
        assert jobs[0].title == "VP of Engineering Operations"


class TestScrapeJobsMethod:
    """Test the main scrape_jobs method"""

    def test_scrape_jobs_returns_empty_when_firecrawl_fails(self):
        """Test that scrape_jobs returns empty list when Firecrawl fails"""
        scraper = FirecrawlCareerScraper()

        # _firecrawl_scrape returns None (placeholder)
        jobs = scraper.scrape_jobs("https://company.com/careers", "Company")

        assert jobs == []

    def test_scrape_jobs_handles_missing_markdown(self, mocker):
        """Test scrape_jobs handles missing markdown in result"""
        scraper = FirecrawlCareerScraper()

        # Mock _firecrawl_scrape to return empty dict
        mocker.patch.object(scraper, "_firecrawl_scrape", return_value={})

        jobs = scraper.scrape_jobs("https://company.com/careers", "Company")

        assert jobs == []

    def test_scrape_jobs_success(self, mocker):
        """Test successful job scraping"""
        scraper = FirecrawlCareerScraper()

        mock_result = {
            "markdown": """
[Senior Engineer

Toronto, ON](https://jobs.company.com/123)
"""
        }

        mocker.patch.object(scraper, "_firecrawl_scrape", return_value=mock_result)

        jobs = scraper.scrape_jobs("https://company.com/careers", "TestCo")

        assert len(jobs) == 1
        assert jobs[0].title == "Senior Engineer"
        assert jobs[0].company == "TestCo"

    def test_scrape_jobs_handles_exceptions(self, mocker):
        """Test that scrape_jobs handles exceptions gracefully"""
        scraper = FirecrawlCareerScraper()

        # Make _firecrawl_scrape raise an exception
        mocker.patch.object(
            scraper,
            "_firecrawl_scrape",
            side_effect=Exception("Network error"),
        )

        jobs = scraper.scrape_jobs("https://company.com/careers", "Company")

        assert jobs == []


class TestFirecrawlScrapeMethod:
    """Test the Firecrawl scraping placeholder"""

    def test_firecrawl_scrape_returns_none(self):
        """Test that _firecrawl_scrape is a placeholder returning None"""
        scraper = FirecrawlCareerScraper()

        result = scraper._firecrawl_scrape("https://company.com/careers")

        assert result is None


class TestOpportunityDataCreation:
    """Test that OpportunityData objects are created correctly"""

    def test_opportunity_data_fields(self):
        """Test that all OpportunityData fields are set correctly"""
        scraper = FirecrawlCareerScraper()

        markdown = """
[Engineering Manager

Boston, MA](https://careers.company.com/job/123)
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://careers.company.com", "BigCorp"
        )

        assert len(jobs) == 1

        job = jobs[0]
        # Verify it's an OpportunityData-like object with correct fields
        assert hasattr(job, "type")
        assert job.type == "direct_job"
        assert job.title == "Engineering Manager"
        assert job.company == "BigCorp"
        assert job.location == "Boston, MA"
        assert job.link == "https://careers.company.com/job/123"
        assert job.source == "company_monitoring"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_extract_jobs_with_special_characters_in_title(self):
        """Test job titles with special characters"""
        scraper = FirecrawlCareerScraper()

        markdown = """
[Software Engineer (C++/Python)

Remote](https://jobs.company.com/123)

[Director, Product-Engineering

San Francisco, CA](https://jobs.company.com/456)
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "TechCo"
        )

        # Should extract at least the Director role (has "director" keyword)
        assert len(jobs) >= 1
        # Check if we have the director role
        director_jobs = [j for j in jobs if "Director" in j.title]
        assert len(director_jobs) == 1
        assert "Product-Engineering" in director_jobs[0].title

    def test_extract_jobs_with_multiline_location(self):
        """Test jobs with complex location formatting"""
        scraper = FirecrawlCareerScraper()

        markdown = """
We have 2 jobs

## Lead Software Engineer

San Jose, CA

## Senior Manager

San Francisco, CA
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "Company"
        )

        assert len(jobs) >= 1
        assert any("Engineer" in job.title for job in jobs)

    def test_extract_jobs_deduplication(self):
        """Test that duplicate job listings are handled"""
        scraper = FirecrawlCareerScraper()

        markdown = """
[Senior Developer

Toronto, ON](https://jobs.company.com/123)

[Senior Developer

Toronto, ON](https://jobs.company.com/123)
"""

        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://company.com/careers", "Company"
        )

        # Both will be extracted (deduplication happens in database layer)
        assert len(jobs) == 2
