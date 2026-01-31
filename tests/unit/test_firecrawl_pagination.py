"""
Unit tests for Firecrawl pagination support

Tests URL discovery, sitemap parsing, and job deduplication
"""

from unittest.mock import Mock, patch

from src.models import OpportunityData
from src.scrapers.firecrawl_career_scraper import FirecrawlCareerScraper


class TestURLFiltering:
    """Test _is_job_url method"""

    def test_strong_indicators(self):
        """Strong job indicators should match"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        assert scraper._is_job_url("https://company.com/job/123") is True
        assert scraper._is_job_url("https://company.com/jobs/engineer") is True
        assert scraper._is_job_url("https://company.com/positions/director") is True
        assert scraper._is_job_url("https://company.com/careers?page=2") is True
        assert scraper._is_job_url("https://company.com/openings/vp") is True

    def test_weak_indicators_need_validation(self):
        """Weak indicators need job-related terms"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        # Just /careers/ without job terms should fail
        assert scraper._is_job_url("https://company.com/careers/benefits") is False
        assert scraper._is_job_url("https://company.com/careers/about") is False

        # /careers/ with job terms should pass
        assert scraper._is_job_url("https://company.com/careers/engineer") is True
        assert scraper._is_job_url("https://company.com/careers/director") is True
        assert scraper._is_job_url("https://company.com/careers/en-us/position") is True

    def test_exclusions(self):
        """Excluded patterns should not match"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        assert scraper._is_job_url("https://company.com/jobs/apply") is False
        assert scraper._is_job_url("https://company.com/careers/guide") is False
        assert scraper._is_job_url("https://company.com/positions/faq") is False
        assert scraper._is_job_url("https://company.com/jobs/benefits") is False


class TestSitemapParsing:
    """Test _parse_sitemap method"""

    @patch("src.scrapers.firecrawl_career_scraper.requests.get")
    def test_parse_sitemap_success(self, mock_get):
        """Successful sitemap parsing"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        # Mock sitemap XML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://company.com/jobs/123</loc></url>
            <url><loc>https://company.com/jobs/456</loc></url>
            <url><loc>https://company.com/careers/about</loc></url>
        </urlset>
        """
        mock_get.return_value = mock_response

        urls = scraper._parse_sitemap("https://company.com/careers")

        # Should find 2 job URLs (not the /about page)
        assert len(urls) == 2
        assert "https://company.com/jobs/123" in urls
        assert "https://company.com/jobs/456" in urls

    @patch("src.scrapers.firecrawl_career_scraper.requests.get")
    def test_parse_sitemap_no_sitemap(self, mock_get):
        """No sitemap found returns empty list"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        urls = scraper._parse_sitemap("https://company.com/careers")

        assert urls == []

    @patch("src.scrapers.firecrawl_career_scraper.requests.get")
    def test_parse_sitemap_network_error(self, mock_get):
        """Network errors return empty list"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        mock_get.side_effect = Exception("Network error")

        urls = scraper._parse_sitemap("https://company.com/careers")

        assert urls == []


class TestJobDeduplication:
    """Test _deduplicate_jobs method"""

    def test_no_duplicates(self):
        """No duplicates returns all jobs"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Engineer",
                    company="Company A",
                    link="https://a.com/1",
                    source="test",
                ),
                "regex",
            ),
            (
                OpportunityData(
                    type="direct_job",
                    title="Manager",
                    company="Company B",
                    link="https://b.com/2",
                    source="test",
                ),
                "llm",
            ),
        ]

        result = scraper._deduplicate_jobs(jobs)

        assert len(result) == 2

    def test_exact_duplicates(self):
        """Exact duplicates are removed"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Senior Engineer",
                    company="Acme",
                    link="https://acme.com/1",
                    source="test",
                ),
                "regex",
            ),
            (
                OpportunityData(
                    type="direct_job",
                    title="Senior Engineer",
                    company="Acme",
                    link="https://acme.com/2",
                    source="test",
                ),
                "llm",
            ),
        ]

        result = scraper._deduplicate_jobs(jobs)

        # Should keep only one (prefers LLM over regex)
        assert len(result) == 1
        assert result[0][1] == "llm"  # Preferred extraction method

    def test_case_insensitive_dedup(self):
        """Case-insensitive title matching"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="VP of Engineering",
                    company="Acme",
                    link="https://acme.com/1",
                    source="test",
                ),
                "regex",
            ),
            (
                OpportunityData(
                    type="direct_job",
                    title="vp of engineering",
                    company="Acme",
                    link="https://acme.com/2",
                    source="test",
                ),
                "llm",
            ),
        ]

        result = scraper._deduplicate_jobs(jobs)

        assert len(result) == 1

    def test_prefers_valid_urls(self):
        """Prefers jobs with valid URLs"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        job1 = OpportunityData(
            type="direct_job",
            title="Engineer",
            company="Acme",
            link="https://acme.com/1",
            source="test",
        )
        job1.__dict__["url_validated"] = False  # Invalid URL

        job2 = OpportunityData(
            type="direct_job",
            title="Engineer",
            company="Acme",
            link="https://acme.com/2",
            source="test",
        )
        job2.__dict__["url_validated"] = True  # Valid URL

        jobs = [(job1, "regex"), (job2, "regex")]

        result = scraper._deduplicate_jobs(jobs)

        assert len(result) == 1
        assert result[0][0].link == "https://acme.com/2"  # Valid URL wins


class TestURLDiscovery:
    """Test _discover_job_urls method"""

    @patch.object(FirecrawlCareerScraper, "_parse_sitemap")
    def test_sitemap_success(self, mock_sitemap):
        """Successful sitemap discovery"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        mock_sitemap.return_value = [
            "https://company.com/jobs/1",
            "https://company.com/jobs/2",
        ]

        urls = scraper._discover_job_urls("https://company.com/careers", "Company")

        assert len(urls) == 2
        mock_sitemap.assert_called_once()

    @patch.object(FirecrawlCareerScraper, "_firecrawl_map")
    @patch.object(FirecrawlCareerScraper, "_parse_sitemap")
    def test_fallback_to_firecrawl_map(self, mock_sitemap, mock_map):
        """Falls back to Firecrawl map when sitemap fails"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        mock_sitemap.return_value = []  # No sitemap
        mock_map.return_value = [
            "https://company.com/jobs/3",
            "https://company.com/jobs/4",
        ]

        urls = scraper._discover_job_urls("https://company.com/careers", "Company")

        assert len(urls) == 2
        mock_sitemap.assert_called_once()
        mock_map.assert_called_once()

    @patch.object(FirecrawlCareerScraper, "_firecrawl_map")
    @patch.object(FirecrawlCareerScraper, "_parse_sitemap")
    def test_no_urls_discovered(self, mock_sitemap, mock_map):
        """Returns empty list when no URLs found"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        mock_sitemap.return_value = []
        mock_map.return_value = []

        urls = scraper._discover_job_urls("https://company.com/careers", "Company")

        assert urls == []

    def test_pagination_disabled(self):
        """Returns empty list when pagination disabled"""
        scraper = FirecrawlCareerScraper(enable_pagination=False)

        urls = scraper._discover_job_urls("https://company.com/careers", "Company")

        assert urls == []

    @patch.object(FirecrawlCareerScraper, "_parse_sitemap")
    def test_limits_to_50_urls(self, mock_sitemap):
        """Limits discovered URLs to 50"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        # Return 100 URLs
        mock_sitemap.return_value = [f"https://company.com/jobs/{i}" for i in range(100)]

        urls = scraper._discover_job_urls("https://company.com/careers", "Company")

        # Should limit to 50
        assert len(urls) == 50


class TestPaginationIntegration:
    """Integration tests for pagination feature"""

    @patch.object(FirecrawlCareerScraper, "_scrape_single_page")
    @patch.object(FirecrawlCareerScraper, "_discover_job_urls")
    def test_scrape_jobs_with_pagination(self, mock_discover, mock_scrape_page):
        """scrape_jobs uses pagination when enabled"""
        scraper = FirecrawlCareerScraper(enable_pagination=True)

        # Mock URL discovery
        mock_discover.return_value = [
            "https://company.com/jobs/1",
            "https://company.com/jobs/2",
        ]

        # Mock page scraping
        job1 = (
            OpportunityData(
                type="direct_job", title="Job 1", company="Co", link="link1", source="test"
            ),
            "regex",
        )
        job2 = (
            OpportunityData(
                type="direct_job", title="Job 2", company="Co", link="link2", source="test"
            ),
            "regex",
        )

        mock_scrape_page.side_effect = [[job1], [job2], []]  # Main page + 2 discovered

        result = scraper.scrape_jobs("https://company.com/careers", "Company")

        # Should call scrape_single_page 3 times (main + 2 discovered)
        assert mock_scrape_page.call_count == 3
        assert len(result) == 2

    @patch.object(FirecrawlCareerScraper, "_scrape_single_page")
    def test_scrape_jobs_without_pagination(self, mock_scrape_page):
        """scrape_jobs works without pagination"""
        scraper = FirecrawlCareerScraper(enable_pagination=False)

        job = (
            OpportunityData(
                type="direct_job", title="Job", company="Co", link="link", source="test"
            ),
            "regex",
        )
        mock_scrape_page.return_value = [job]

        result = scraper.scrape_jobs("https://company.com/careers", "Company")

        # Should only call once (main page only)
        assert mock_scrape_page.call_count == 1
        assert len(result) == 1
