"""
Tests for inline link job extraction (Ashby-style career pages)

Covers the _extract_jobs_from_inline_links pattern that handles job boards
where jobs are formatted as: [TitleDepartment • Location • Type](url)

This pattern is common on Ashby-hosted career pages (1Password, Harvey, etc.)
where multiple jobs are concatenated on a single line separated by ###.
"""

import pytest

from src.scrapers.base_career_scraper import BaseCareerScraper


class TestExtractDepartmentNames:
    """Test department name extraction from ## headers"""

    def test_extracts_departments(self):
        markdown = "## Technology\n### [Dev](url)\n## Marketing\n### [PM](url)"
        result = BaseCareerScraper._extract_department_names(markdown)
        assert "Technology" in result
        assert "Marketing" in result

    def test_ignores_single_char_departments(self):
        markdown = "## A\n## Technology\n"
        result = BaseCareerScraper._extract_department_names(markdown)
        assert "Technology" in result
        assert len(result) == 1

    def test_empty_markdown(self):
        assert BaseCareerScraper._extract_department_names("") == []


class TestParseInlineLinkText:
    """Test parsing title and location from inline link text"""

    def test_basic_bullet_format(self):
        text = "Engineering Manager, API PlatformTechnology • Remote (US | Canada) • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(text, ["Technology"])
        assert title == "Engineering Manager, API Platform"
        assert location == "Remote (US | Canada)"

    def test_strips_department_suffix(self):
        text = "Developer, BackendTechnology • Remote • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(
            text, ["Technology", "Marketing"]
        )
        assert title == "Developer, Backend"

    def test_strips_longer_department_first(self):
        """Longer dept names should be tried first to avoid partial matches"""
        text = "Senior ManagerCustomer Experience • Remote • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(
            text, ["Customer Experience", "Experience"]
        )
        assert title == "Senior Manager"

    def test_no_department_match(self):
        text = "Software Engineer • Remote • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(text, ["Technology"])
        assert title == "Software Engineer"
        assert location == "Remote"

    def test_location_with_city(self):
        text = "VP of EngineeringGTM • New York, NY • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(text, ["GTM"])
        assert title == "VP of Engineering"
        assert location == "New York, NY"

    def test_no_bullet_separator(self):
        text = "Software Engineer at Some Company"
        title, location = BaseCareerScraper._parse_inline_link_text(text, [])
        assert title == "Software Engineer at Some Company"
        assert location == ""

    def test_hybrid_location(self):
        text = "Director of SalesGTM • Toronto, ON • Full time • Hybrid"
        title, location = BaseCareerScraper._parse_inline_link_text(text, ["GTM"])
        assert title == "Director of Sales"
        assert location == "Toronto, ON"

    def test_department_same_as_title_not_stripped(self):
        """Don't strip dept if it would leave empty title"""
        text = "Technology • Remote • Full time"
        title, location = BaseCareerScraper._parse_inline_link_text(text, ["Technology"])
        # Can't strip — would leave empty string
        assert title == "Technology"


class TestExtractJobsFromInlineLinks:
    """Test full inline link extraction pipeline"""

    @pytest.fixture
    def scraper(self):
        """Create a minimal scraper for testing static/instance methods"""
        # Use a concrete subclass — PlaywrightCareerScraper has no API key requirement
        from src.scrapers.playwright_career_scraper import PlaywrightCareerScraper

        return PlaywrightCareerScraper()

    def test_ashby_style_single_job(self, scraper):
        markdown = (
            "## Technology\n\n"
            "### [Senior Software EngineerTechnology "
            "• Remote (United States | Canada) • Full time • Remote]"
            "(/company/abc-123)\n"
        )
        jobs = scraper._extract_jobs_from_inline_links(markdown, "TestCo")
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Software Engineer"
        assert jobs[0].location == "Remote (United States | Canada)"
        assert jobs[0].company == "TestCo"
        assert jobs[0].link == "/company/abc-123"

    def test_ashby_style_concatenated_jobs(self, scraper):
        """The critical bug case: multiple ### jobs on one line"""
        markdown = (
            "## Technology\n\n"
            "### [Developer, BackendTechnology • Remote • Full time]"
            "(/co/aaa)### [Engineering ManagerTechnology • Toronto, ON • Full time]"
            "(/co/bbb)### [Staff DeveloperTechnology • Remote • Full time]"
            "(/co/ccc)\n"
        )
        jobs = scraper._extract_jobs_from_inline_links(markdown, "TestCo")
        assert len(jobs) == 3
        assert jobs[0].title == "Developer, Backend"
        assert jobs[1].title == "Engineering Manager"
        assert jobs[1].location == "Toronto, ON"
        assert jobs[2].title == "Staff Developer"

    def test_multiple_departments(self, scraper):
        markdown = (
            "## Engineering\n\n"
            "### [Senior EngineerEngineering • Remote • Full time](/co/a)\n\n"
            "## Marketing\n\n"
            "### [Product ManagerMarketing • NYC • Full time](/co/b)\n"
        )
        jobs = scraper._extract_jobs_from_inline_links(markdown, "TestCo")
        titles = [j.title for j in jobs]
        assert "Senior Engineer" in titles
        # Product Manager is a job keyword (manager)
        assert "Product Manager" in titles

    def test_filters_navigation_links(self, scraper):
        """Non-job links like 'Powered by Ashby' should be filtered out"""
        markdown = (
            "## Technology\n\n"
            "### [Senior EngineerTechnology • Remote • Full time](/co/a)\n"
            "[Powered by Ashby](https://www.ashbyhq.com)\n"
            "[Privacy Policy](https://www.ashbyhq.com/privacy)\n"
        )
        jobs = scraper._extract_jobs_from_inline_links(markdown, "TestCo")
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Engineer"

    def test_empty_markdown(self, scraper):
        jobs = scraper._extract_jobs_from_inline_links("", "TestCo")
        assert len(jobs) == 0

    def test_no_inline_links(self, scraper):
        markdown = "# Careers\n\nWe're hiring! Check back soon."
        jobs = scraper._extract_jobs_from_inline_links(markdown, "TestCo")
        assert len(jobs) == 0

    def test_real_1password_format(self, scraper):
        """Test against actual 1Password Ashby board format"""
        markdown = """# Open Positions (64)

## Customer Experience

### [Senior Manager, CX Operations & ProgramsCustomer Experience • Remote (United States | Canada) • Full time • Remote](/1password/5d323673)

## G&A

### [Director, Corporate Development G&A • Remote (United States | Canada) • Full time • Remote](/1password/4aedfb1b)### [Senior Manager, Strategic OperationsG&A • Remote (United States | Canada) • Full time • Remote](/1password/005f5f65)

## Technology

### [Engineering Manager, API PlatformTechnology • Remote (United States | Canada) • Full time](/1password/eef5c8da)### [Senior Director Engineering, Identity Security Platform InfrastructureTechnology • Remote US • Full time • Remote](/1password/ff98345b)

[Powered by Ashby](https://www.ashbyhq.com)
"""
        jobs = scraper._extract_jobs_from_inline_links(markdown, "1Password")
        assert len(jobs) == 5
        titles = [j.title for j in jobs]
        assert "Senior Manager, CX Operations & Programs" in titles
        assert "Director, Corporate Development" in titles
        assert "Engineering Manager, API Platform" in titles
        assert "Senior Director Engineering, Identity Security Platform Infrastructure" in titles

        # Check locations are parsed
        eng_mgr = next(j for j in jobs if "API Platform" in j.title)
        assert eng_mgr.location == "Remote (United States | Canada)"

        # Check company and source
        assert all(j.company == "1Password" for j in jobs)
        assert all(j.source == "company_monitoring" for j in jobs)


class TestExtractionPriority:
    """Test that extraction methods are tried in the correct order"""

    @pytest.fixture
    def scraper(self):
        from src.scrapers.playwright_career_scraper import PlaywrightCareerScraper

        return PlaywrightCareerScraper()

    def test_inline_links_tried_before_pattern2(self, scraper):
        """Inline links should prevent pattern2 from creating monster entries"""
        # This markdown has jobs as inline links AND ## headers
        # If pattern2 ran first, it would create concatenated entries
        markdown = (
            "## Technology\n\n"
            "### [Senior EngineerTechnology • Remote • Full time](/co/a)"
            "### [Staff EngineerTechnology • Remote • Full time](/co/b)\n"
        )
        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://example.com/careers", "TestCo"
        )
        # Should get 2 individual jobs, not 1 concatenated monster
        assert len(jobs) == 2
        assert all(len(j.title) < 200 for j in jobs)

    def test_pattern1_still_takes_priority(self, scraper):
        """Pattern 1 (double-newline format) should still work when applicable"""
        markdown = (
            "[Senior Engineer\n\nNew York, NY](https://example.com/job1)\n"
            "[Staff Developer\n\nRemote](https://example.com/job2)\n"
        )
        jobs = scraper._extract_jobs_from_markdown(
            markdown, "https://example.com/careers", "TestCo"
        )
        assert len(jobs) == 2
        assert jobs[0].title == "Senior Engineer"
        assert jobs[0].location == "New York, NY"


class TestPattern2MaxLengthGuard:
    """Test that pattern2 rejects suspiciously long headers"""

    @pytest.fixture
    def scraper(self):
        from src.scrapers.playwright_career_scraper import PlaywrightCareerScraper

        return PlaywrightCareerScraper()

    def test_rejects_very_long_headers(self, scraper):
        """Headers over 200 chars should be rejected as likely concatenated"""
        long_title = "Senior Engineer at Company " * 10  # ~270 chars
        markdown = f"# Jobs\n\n## {long_title}\n"
        jobs = scraper._extract_jobs_from_pattern2(
            markdown, "https://example.com/careers", "TestCo"
        )
        assert len(jobs) == 0

    def test_accepts_normal_length_headers(self, scraper):
        """Normal-length headers should still work"""
        markdown = "# Current Jobs\n\n## Senior Software Engineer\n"
        jobs = scraper._extract_jobs_from_pattern2(
            markdown, "https://example.com/careers", "TestCo"
        )
        assert len(jobs) == 1
