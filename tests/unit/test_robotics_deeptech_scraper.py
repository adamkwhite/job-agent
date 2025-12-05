"""
Tests for RoboticsDeeptechScraper

Tests the Google Sheets scraper for robotics/deeptech job boards.
"""

from unittest.mock import Mock, patch

import requests

from src.scrapers.robotics_deeptech_scraper import RoboticsDeeptechScraper


class TestRoboticsDeeptechScraperInit:
    """Test RoboticsDeeptechScraper initialization"""

    def test_init(self):
        """Test scraper initializes with correct attributes"""
        scraper = RoboticsDeeptechScraper()

        assert scraper.name == "robotics_deeptech"
        assert scraper.sheet_id == "1i1OQti71WbiE9kFANDc5Pt-IknCM3UB2dD61gujPywk"
        assert scraper.gid == "0"
        assert "docs.google.com" in scraper.base_url
        assert "export?format=csv" in scraper.base_url

    def test_leadership_keywords_defined(self):
        """Test leadership keywords are defined"""
        scraper = RoboticsDeeptechScraper()

        assert scraper.leadership_keywords is not None
        assert len(scraper.leadership_keywords) > 0
        assert "director" in scraper.leadership_keywords
        assert "vp" in scraper.leadership_keywords
        assert "head of" in scraper.leadership_keywords


class TestScraperScrape:
    """Test scrape method"""

    def test_scrape_skips_jobs_missing_critical_fields(self):
        """Test scraper skips jobs missing title, company, or URL"""
        scraper = RoboticsDeeptechScraper()

        # CSV with incomplete jobs
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
,Missing Company,Description,,,,,https://example.com/job1,NEW
Director of Engineering,,Description,,,,,https://example.com/job2,NEW
VP of Product,Good Company,Description,,,,,,,NEW
Complete Job,Complete Company,Description,,,,,https://example.com/job4,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            # Should only get the complete job
            assert len(opportunities) == 1
            assert opportunities[0].title == "Complete Job"
            assert opportunities[0].company == "Complete Company"

    def test_scrape_builds_location_from_city_and_country(self):
        """Test location string is built correctly"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,,,Toronto,Canada,https://example.com/1,NEW
Job2,Company2,Desc,,,San Francisco,,https://example.com/2,NEW
Job3,Company3,Desc,,,,USA,https://example.com/3,NEW
Job4,Company4,Desc,,,,,https://example.com/4,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert len(opportunities) == 4
            assert opportunities[0].location == "Toronto, Canada"
            assert opportunities[1].location == "San Francisco"
            assert opportunities[2].location == "USA"
            assert opportunities[3].location == ""

    def test_scrape_builds_enhanced_description(self):
        """Test enhanced description includes metadata"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director,Company,Great opportunity,Engineering,Senior,,,https://example.com/1,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            job = opportunities[0]
            assert "Great opportunity" in job.description
            assert "Department: Engineering" in job.description
            assert "Level: Senior" in job.description
            assert "Status: NEW" in job.description

    def test_scrape_handles_http_error(self):
        """Test scraper handles HTTP errors gracefully"""
        scraper = RoboticsDeeptechScraper()

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert opportunities == []

    def test_scrape_handles_timeout(self):
        """Test scraper handles timeout errors"""
        scraper = RoboticsDeeptechScraper()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get",
            side_effect=requests.exceptions.Timeout("Timeout"),
        ):
            opportunities = scraper.scrape()

            assert opportunities == []

    def test_scrape_handles_connection_error(self):
        """Test scraper handles connection errors"""
        scraper = RoboticsDeeptechScraper()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection failed"),
        ):
            opportunities = scraper.scrape()

            assert opportunities == []

    def test_scrape_handles_malformed_csv(self):
        """Test scraper handles malformed CSV data"""
        scraper = RoboticsDeeptechScraper()

        # Invalid CSV
        csv_data = "Not a valid CSV\nSome random text"

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            # Should not crash, may return empty or partial results
            opportunities = scraper.scrape()
            assert isinstance(opportunities, list)

    def test_scrape_strips_whitespace_from_fields(self):
        """Test scraper strips whitespace from all fields"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
  Director  ,  Robotics Co  ,  Description  ,  Engineering  ,  Senior  ,  Toronto  ,  Canada  ,  https://example.com/1  ,  NEW  """

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            job = opportunities[0]
            assert job.title == "Director"
            assert job.company == "Robotics Co"
            assert job.location == "Toronto, Canada"
            assert job.job_type == "Engineering"

    def test_scrape_sets_correct_opportunity_fields(self):
        """Test all OpportunityData fields are set correctly"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
VP Engineering,Tech Corp,Great role,Engineering,Executive,Boston,USA,https://jobs.com/1,Recent"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            job = opportunities[0]
            assert job.source == "robotics_deeptech_sheet"
            assert job.source_email == ""
            assert job.type == "direct_job"
            assert job.company == "Tech Corp"
            assert job.title == "VP Engineering"
            assert job.location == "Boston, USA"
            assert job.link == "https://jobs.com/1"
            assert job.description is not None
            assert job.job_type == "Engineering"
            assert job.needs_research is False
            assert job.research_notes is not None


class TestGetLeadershipJobsOnly:
    """Test get_leadership_jobs_only method"""

    def test_filters_for_leadership_roles(self):
        """Test filtering for leadership roles only"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director of Engineering,Company1,Desc,,,,,https://example.com/1,NEW
VP of Product,Company2,Desc,,,,,https://example.com/2,NEW
Software Engineer,Company3,Desc,,,,,https://example.com/3,NEW
Head of Design,Company4,Desc,,,,,https://example.com/4,NEW
Junior Developer,Company5,Desc,,,,,https://example.com/5,NEW
Chief Technology Officer,Company6,Desc,,,,,https://example.com/6,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            leadership_jobs = scraper.get_leadership_jobs_only()

            # Should only get leadership roles
            assert len(leadership_jobs) == 4
            titles = [job.title for job in leadership_jobs]
            assert "Director of Engineering" in titles
            assert "VP of Product" in titles
            assert "Head of Design" in titles
            assert "Chief Technology Officer" in titles
            assert "Software Engineer" not in titles
            assert "Junior Developer" not in titles

    def test_leadership_keywords_case_insensitive(self):
        """Test leadership filtering is case-insensitive"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
DIRECTOR of Engineering,Company1,Desc,,,,,https://example.com/1,NEW
vp of Product,Company2,Desc,,,,,https://example.com/2,NEW
Head Of Design,Company3,Desc,,,,,https://example.com/3,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            leadership_jobs = scraper.get_leadership_jobs_only()

            assert len(leadership_jobs) == 3

    def test_leadership_principal_staff_keywords(self):
        """Test principal/staff keywords are recognized as leadership"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Principal Engineer,Company1,Desc,,,,,https://example.com/1,NEW
Staff Software Engineer,Company2,Desc,,,,,https://example.com/2,NEW
Senior Manager Engineering,Company3,Desc,,,,,https://example.com/3,NEW
Lead Product Manager,Company4,Desc,,,,,https://example.com/4,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            leadership_jobs = scraper.get_leadership_jobs_only()

            assert len(leadership_jobs) == 4

    def test_leadership_returns_empty_when_no_matches(self):
        """Test returns empty list when no leadership roles found"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Software Engineer,Company1,Desc,,,,,https://example.com/1,NEW
Product Designer,Company2,Desc,,,,,https://example.com/2,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            leadership_jobs = scraper.get_leadership_jobs_only()

            assert len(leadership_jobs) == 0


class TestGetFreshJobsOnly:
    """Test get_fresh_jobs_only method"""

    def test_filters_for_new_status(self):
        """Test filtering for NEW status jobs"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,Engineering,Senior,,,https://example.com/1,NEW
Job2,Company2,Desc,Engineering,Senior,,,https://example.com/2,Recent
Job3,Company3,Desc,Engineering,Senior,,,https://example.com/3,OLD
Job4,Company4,Desc,Engineering,Senior,,,https://example.com/4,FILLED"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            fresh_jobs = scraper.get_fresh_jobs_only()

            # Should only get NEW and Recent
            assert len(fresh_jobs) == 2
            titles = [job.title for job in fresh_jobs]
            assert "Job1" in titles
            assert "Job2" in titles

    def test_fresh_status_case_insensitive(self):
        """Test status filtering is case-insensitive"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,Engineering,Senior,,,https://example.com/1,new
Job2,Company2,Desc,Engineering,Senior,,,https://example.com/2,RECENT
Job3,Company3,Desc,Engineering,Senior,,,https://example.com/3,New"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            fresh_jobs = scraper.get_fresh_jobs_only()

            assert len(fresh_jobs) == 3

    def test_fresh_returns_empty_when_no_matches(self):
        """Test returns empty list when no fresh jobs found"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,,,,,https://example.com/1,OLD
Job2,Company2,Desc,,,,,https://example.com/2,FILLED"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            fresh_jobs = scraper.get_fresh_jobs_only()

            assert len(fresh_jobs) == 0

    def test_fresh_handles_missing_research_notes(self):
        """Test handles jobs with missing research_notes"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,,,,,https://example.com/1,NEW
Job2,Company2,Desc,,,,,https://example.com/2,"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            fresh_jobs = scraper.get_fresh_jobs_only()

            # Job1 should be included, Job2 should not (no status)
            assert len(fresh_jobs) == 1
            assert fresh_jobs[0].title == "Job1"


class TestMainFunction:
    """Test main() CLI function"""

    def test_main_default_behavior(self, capsys):
        """Test main function with default arguments"""
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director of Engineering,Robotics Co,Great role,Engineering,Senior,Toronto,Canada,https://example.com/1,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        # Mock argparse to return default values
        with (
            patch(
                "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
            ),
            patch("sys.argv", ["script.py"]),
        ):
            from src.scrapers.robotics_deeptech_scraper import main

            main()

            captured = capsys.readouterr()
            assert "ROBOTICS/DEEPTECH JOBS" in captured.out
            assert "Director of Engineering" in captured.out

    def test_main_leadership_only_flag(self, capsys):
        """Test main function with --leadership-only flag"""
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director of Engineering,Company1,Desc,Engineering,Senior,,,https://example.com/1,NEW
Software Engineer,Company2,Desc,Engineering,Mid,,,https://example.com/2,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with (
            patch(
                "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
            ),
            patch("sys.argv", ["script.py", "--leadership-only"]),
        ):
            from src.scrapers.robotics_deeptech_scraper import main

            main()

            captured = capsys.readouterr()
            assert "Director of Engineering" in captured.out
            # Should filter out Software Engineer
            assert "Filtered to 1 leadership roles" in captured.out

    def test_main_fresh_only_flag(self, capsys):
        """Test main function with --fresh-only flag"""
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,Engineering,Senior,,,https://example.com/1,NEW
Job2,Company2,Desc,Engineering,Senior,,,https://example.com/2,OLD"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with (
            patch(
                "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
            ),
            patch("sys.argv", ["script.py", "--fresh-only"]),
        ):
            from src.scrapers.robotics_deeptech_scraper import main

            main()

            captured = capsys.readouterr()
            assert "Job1" in captured.out
            assert "Filtered to 1 fresh jobs" in captured.out

    def test_main_limit_flag(self, capsys):
        """Test main function with --limit flag"""
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Company1,Desc,,,,,https://example.com/1,NEW
Job2,Company2,Desc,,,,,https://example.com/2,NEW
Job3,Company3,Desc,,,,,https://example.com/3,NEW
Job4,Company4,Desc,,,,,https://example.com/4,NEW
Job5,Company5,Desc,,,,,https://example.com/5,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with (
            patch(
                "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
            ),
            patch("sys.argv", ["script.py", "--limit", "3"]),
        ):
            from src.scrapers.robotics_deeptech_scraper import main

            main()

            captured = capsys.readouterr()
            assert "Showing first 3 of 5" in captured.out
            assert "... and 2 more jobs" in captured.out


class TestFirecrawlMethods:
    """Test Firecrawl priority companies and fallback methods (Issue #65)"""

    def test_load_priority_companies_success(self):
        """Test loading priority companies configuration successfully"""
        scraper = RoboticsDeeptechScraper()

        # Should have loaded config
        assert scraper.priority_config is not None
        assert "priority_companies" in scraper.priority_config
        assert isinstance(scraper.priority_companies, list)
        assert len(scraper.priority_companies) == 10

        # Verify expected companies
        assert "Boston Dynamics" in scraper.priority_companies
        assert "Figure" in scraper.priority_companies
        assert "Skydio" in scraper.priority_companies

    def test_load_priority_companies_config_fields(self):
        """Test all required config fields are present"""
        scraper = RoboticsDeeptechScraper()

        config = scraper.priority_config
        assert "rate_limit_seconds" in config
        assert "max_companies_per_run" in config
        assert "failure_threshold_percent" in config
        assert "markdown_cache_enabled" in config
        assert "markdown_cache_dir" in config
        assert "credit_budget_weekly" in config
        assert "credit_budget_monthly" in config

    def test_load_priority_companies_missing_file(self):
        """Test graceful handling when config file is missing"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            scraper = RoboticsDeeptechScraper()

            # Should return default config
            assert scraper.priority_config == {"priority_companies": []}
            assert scraper.priority_companies == []

    def test_load_priority_companies_invalid_json(self):
        """Test graceful handling of invalid JSON"""
        from unittest.mock import mock_open

        invalid_json = "{ invalid json content"

        with patch("builtins.open", mock_open(read_data=invalid_json)):
            scraper = RoboticsDeeptechScraper()

            # Should return default config
            assert scraper.priority_config == {"priority_companies": []}
            assert scraper.priority_companies == []

    def test_scrape_with_firecrawl_fallback_returns_tuple(self):
        """Test scrape_with_firecrawl_fallback returns (sheet_jobs, generic_pages)"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Valid Job,Good Company,Desc,,,,,https://example.com/job/123,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should return tuple
            assert isinstance(sheet_jobs, list)
            assert isinstance(generic_pages, dict)

    def test_scrape_with_firecrawl_fallback_identifies_generic_pages(self):
        """Test identifies generic career pages from priority companies"""
        scraper = RoboticsDeeptechScraper()

        # Mix of valid jobs and generic pages from priority companies
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Valid Job,Good Company,Desc,,,,,https://example.com/job/123,NEW
Generic Page,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW
Another Valid,Other Co,Desc,,,,,https://jobs.lever.co/company/jobs/abc,NEW
Generic Page,Skydio,Desc,,,,,https://skydio.com/careers,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should get 2 direct jobs (non-generic URLs)
            assert len(sheet_jobs) == 2

            # Should identify 2 generic pages from priority companies
            assert len(generic_pages) == 2
            assert "Boston Dynamics" in generic_pages
            assert "Skydio" in generic_pages

            # Verify structure of generic_pages dict
            assert generic_pages["Boston Dynamics"]["url"] == (
                "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
            )
            assert generic_pages["Boston Dynamics"]["company"] == "Boston Dynamics"

    def test_scrape_with_firecrawl_fallback_ignores_non_priority_companies(self):
        """Test only includes generic pages from priority companies"""
        scraper = RoboticsDeeptechScraper()

        # Generic pages from both priority and non-priority companies
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Generic,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW
Generic,Non Priority Company,Desc,,,,,https://example.com/careers,NEW
Generic,Skydio,Desc,,,,,https://skydio.com/careers/,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should only include priority companies
            assert len(generic_pages) == 2
            assert "Boston Dynamics" in generic_pages
            assert "Skydio" in generic_pages
            assert "Non Priority Company" not in generic_pages

    def test_scrape_with_firecrawl_fallback_deduplicates_by_company(self):
        """Test only stores one generic page per company"""
        scraper = RoboticsDeeptechScraper()

        # Multiple rows with same company and generic URL
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW
Job2,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW
Job3,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should only have one entry for Boston Dynamics
            assert len(generic_pages) == 1
            assert "Boston Dynamics" in generic_pages

    def test_scrape_with_firecrawl_fallback_handles_http_error(self):
        """Test gracefully handles HTTP errors during generic page detection"""
        scraper = RoboticsDeeptechScraper()

        # First call succeeds (sheet_jobs), second call fails (generic pages)
        responses = [
            Mock(
                text="Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status\nJob,Co,Desc,,,,,https://example.com/1,NEW",
                raise_for_status=Mock(),
            ),
            Mock(raise_for_status=Mock(side_effect=requests.exceptions.HTTPError("404"))),
        ]

        with patch("src.scrapers.robotics_deeptech_scraper.requests.get", side_effect=responses):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should still return sheet_jobs, but empty generic_pages
            assert len(sheet_jobs) == 1
            assert generic_pages == {}

    def test_scrape_with_firecrawl_fallback_no_generic_pages_found(self):
        """Test when no generic pages exist from priority companies"""
        scraper = RoboticsDeeptechScraper()

        # All valid job URLs (no generic pages)
        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Job1,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/123,NEW
Job2,Skydio,Desc,,,,,https://boards.greenhouse.io/skydio/jobs/456,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            sheet_jobs, generic_pages = scraper.scrape_with_firecrawl_fallback()

            # Should get both jobs
            assert len(sheet_jobs) == 2

            # Should have no generic pages
            assert generic_pages == {}


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_csv_response(self):
        """Test handling of empty CSV response"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert opportunities == []

    def test_single_row_csv(self):
        """Test CSV with single job row"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director,Company,Desc,,,,,https://example.com/1,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert len(opportunities) == 1

    def test_unicode_characters_in_fields(self):
        """Test handling of Unicode characters"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director of Engineering,Robotics Co™,Great opportunity 🚀,Engineering,Senior,Montréal,Canada,https://example.com/1,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert len(opportunities) == 1
            job = opportunities[0]
            assert "Robotics Co™" in job.company
            assert "Montréal" in job.location

    def test_very_long_description(self):
        """Test handling of very long description fields"""
        scraper = RoboticsDeeptechScraper()

        long_description = "A" * 5000
        csv_data = f"""Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director,Company,{long_description},Engineering,Senior,,,https://example.com/1,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert len(opportunities) == 1
            assert len(opportunities[0].description) > 1000

    def test_special_characters_in_url(self):
        """Test handling of special characters in URLs"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director,Company,Desc,,,,,https://example.com/job?id=123&ref=abc,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            assert len(opportunities) == 1
            assert "?" in opportunities[0].link
            assert "&" in opportunities[0].link


class TestGenericCareerPageDetection:
    """Test is_generic_career_page() method (Issue #44)"""

    def test_rejects_careers_path_ending(self):
        """Should reject URLs ending in /careers or /careers/"""
        scraper = RoboticsDeeptechScraper()

        assert scraper.is_generic_career_page("https://apis-cor.com/careers/") is True
        assert scraper.is_generic_career_page("https://example.com/careers") is True
        assert scraper.is_generic_career_page("https://robotics.io/careers") is True

    def test_rejects_about_careers_path(self):
        """Should reject URLs with /about/careers path"""
        scraper = RoboticsDeeptechScraper()

        assert scraper.is_generic_career_page("https://agilityrobotics.com/about/careers") is True
        assert scraper.is_generic_career_page("https://example.com/about/careers/") is True

    def test_rejects_workday_without_job_path(self):
        """Should reject Workday URLs without /job/ in path"""
        scraper = RoboticsDeeptechScraper()

        # Generic Workday career page
        assert (
            scraper.is_generic_career_page(
                "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
            )
            is True
        )
        assert (
            scraper.is_generic_career_page("https://company.wd5.myworkdayjobs.com/Careers") is True
        )

    def test_accepts_workday_with_job_path(self):
        """Should accept Workday URLs with /job/ in path"""
        scraper = RoboticsDeeptechScraper()

        # Valid Workday job posting
        assert (
            scraper.is_generic_career_page(
                "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/123456"
            )
            is False
        )

    def test_rejects_greenhouse_without_jobs_path(self):
        """Should reject Greenhouse URLs without /jobs/ in path"""
        scraper = RoboticsDeeptechScraper()

        # Generic Greenhouse career page
        assert scraper.is_generic_career_page("https://boards.greenhouse.io/company") is True
        assert scraper.is_generic_career_page("https://grnh.se/abc123") is True

    def test_accepts_greenhouse_with_jobs_path(self):
        """Should accept Greenhouse URLs with /jobs/ in path"""
        scraper = RoboticsDeeptechScraper()

        # Valid Greenhouse job posting
        assert (
            scraper.is_generic_career_page("https://boards.greenhouse.io/company/jobs/123456")
            is False
        )

    def test_rejects_lever_without_job_id(self):
        """Should reject Lever URLs without job UUID (generic career page)"""
        scraper = RoboticsDeeptechScraper()

        # Generic Lever career pages (company only, no UUID)
        assert scraper.is_generic_career_page("https://jobs.lever.co/company") is True
        assert scraper.is_generic_career_page("https://jobs.lever.co/company/") is True

    def test_accepts_lever_with_job_id(self):
        """Should accept Lever URLs with job UUID (specific job posting)"""
        scraper = RoboticsDeeptechScraper()

        # Valid Lever job postings with UUIDs
        assert (
            scraper.is_generic_career_page(
                "https://jobs.lever.co/NimbleAI/32fed95d-6209-4215-a120-a6ebcb396467"
            )
            is False
        )
        assert (
            scraper.is_generic_career_page(
                "https://jobs.lever.co/dexterity/c09a7805-2a30-4f94-aaf4-4547fb619047"
            )
            is False
        )

    def test_accepts_valid_job_urls(self):
        """Should accept normal job posting URLs"""
        scraper = RoboticsDeeptechScraper()

        # Various valid job URL patterns
        assert scraper.is_generic_career_page("https://apply.workable.com/company/j/123/") is False
        assert scraper.is_generic_career_page("https://company.com/jobs/director-123") is False
        assert scraper.is_generic_career_page("https://company.bamboohr.com/careers/456") is False
        assert scraper.is_generic_career_page("https://jobs.ashbyhq.com/company/123") is False

    def test_case_insensitive_matching(self):
        """Should match patterns case-insensitively"""
        scraper = RoboticsDeeptechScraper()

        assert scraper.is_generic_career_page("https://example.com/CAREERS") is True
        assert scraper.is_generic_career_page("https://example.com/Careers/") is True
        assert scraper.is_generic_career_page("https://company.MyWorkdayJobs.com/Careers") is True

    def test_scrape_skips_generic_career_pages(self):
        """Test scraper skips jobs with generic career page URLs (Issue #44)"""
        scraper = RoboticsDeeptechScraper()

        csv_data = """Job_Title,Company,Description,Department,Experience_Level,City,Country,Job_Url,Status
Director,Apis Cor,Desc,,,,,https://apis-cor.com/careers/,NEW
VP Engineering,Agility,Desc,,,,,https://agilityrobotics.com/about/careers,NEW
Head of Product,Boston Dynamics,Desc,,,,,https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics,NEW
Valid Job,Good Company,Desc,,,,,https://boards.greenhouse.io/company/jobs/123456,NEW"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()

        with patch(
            "src.scrapers.robotics_deeptech_scraper.requests.get", return_value=mock_response
        ):
            opportunities = scraper.scrape()

            # Should only get the valid job URL, not generic career pages
            assert len(opportunities) == 1
            assert opportunities[0].company == "Good Company"
            assert opportunities[0].title == "Valid Job"
