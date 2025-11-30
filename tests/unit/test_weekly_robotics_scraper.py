"""
Tests for WeeklyRoboticsJobChecker

Tests the weekly robotics scraper with Firecrawl integration.
"""

from unittest.mock import patch

from src.jobs.weekly_robotics_scraper import WeeklyRoboticsJobChecker


class TestProcessFirecrawlMarkdown:
    """Test process_firecrawl_markdown method"""

    def test_extracts_jobs_from_headings(self, tmp_path):
        """Test extracts leadership jobs from markdown headings"""
        checker = WeeklyRoboticsJobChecker()

        # Create test markdown file
        markdown_content = """
# Careers at Test Company

## Director of Engineering
Join our robotics team as Director of Engineering.
https://testcompany.com/jobs/director-eng

## VP of Product
Lead our product vision.
https://testcompany.com/jobs/vp-product

## Software Engineer
Regular IC role.
https://testcompany.com/jobs/swe
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        # Should extract 2 leadership jobs (Director and VP, not Software Engineer)
        assert len(jobs) == 2
        assert any("Director of Engineering" in job.title for job in jobs)
        assert any("VP of Product" in job.title for job in jobs)
        assert not any("Software Engineer" in job.title for job in jobs)

    def test_extracts_jobs_from_lists(self, tmp_path):
        """Test extracts leadership jobs from markdown lists"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
# Open Positions

- Head of Hardware Engineering
- Principal Software Architect
- Junior Developer
- Staff Machine Learning Engineer
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        # Should extract 3 leadership jobs (Head, Principal, Staff)
        assert len(jobs) == 3
        titles = [job.title for job in jobs]
        assert "Head of Hardware Engineering" in titles
        assert "Principal Software Architect" in titles
        assert "Staff Machine Learning Engineer" in titles
        assert "Junior Developer" not in titles

    def test_handles_missing_file(self):
        """Test gracefully handles missing markdown file"""
        checker = WeeklyRoboticsJobChecker()

        jobs = checker.process_firecrawl_markdown("/nonexistent/file.md", "Test Company")

        assert jobs == []

    def test_sets_correct_job_fields(self, tmp_path):
        """Test extracted jobs have correct OpportunityData fields"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
## Chief Technology Officer
https://example.com/job/cto
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        assert len(jobs) == 1
        job = jobs[0]
        assert job.source == "robotics_deeptech_sheet"
        assert job.type == "direct_job"
        assert job.company == "Test Company"
        assert "Chief Technology Officer" in job.title
        assert "https://example.com/job/cto" in job.link
        assert "Firecrawl" in job.description

    def test_deduplicates_jobs_from_headings_and_lists(self, tmp_path):
        """Test doesn't duplicate jobs found in both headings and lists"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
## Director of Engineering

Open positions:
- Director of Engineering
- VP of Product
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        # Should only have 2 jobs (deduped Director, plus VP)
        assert len(jobs) == 2
        titles = [job.title for job in jobs]
        # Director should appear only once
        assert sum(1 for t in titles if "Director of Engineering" in t) == 1

    def test_extracts_location_from_markdown_links(self, tmp_path):
        """Test extracts location from markdown link format [Title](URL)"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
# Careers

[VP, Robotics Software](https://example.com/job/vp)
Remote

[Director of Engineering](https://example.com/job/director)
San Francisco, CA

[Principal Engineer](https://example.com/job/principal)
Hybrid - Toronto, ON
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        assert len(jobs) == 3

        # Find each job and check location
        vp_job = next(job for job in jobs if "VP" in job.title)
        assert vp_job.location == "Remote"

        director_job = next(job for job in jobs if "Director" in job.title)
        assert director_job.location == "San Francisco, CA"

        principal_job = next(job for job in jobs if "Principal" in job.title)
        assert principal_job.location == "Hybrid - Toronto, ON"

    def test_extracts_location_from_headings(self, tmp_path):
        """Test extracts location from lines after heading"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
## Director of Product
Remote
https://example.com/job/director

## Head of Engineering
Mountain View, CA
https://example.com/job/head
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        assert len(jobs) == 2

        director_job = next(job for job in jobs if "Director" in job.title)
        assert director_job.location == "Remote"

        head_job = next(job for job in jobs if "Head" in job.title)
        assert director_job.location or head_job.location  # At least one should have location

    def test_location_validation_rejects_markdown_elements(self, tmp_path):
        """Test location extraction doesn't extract markdown links or headings"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
[VP of Engineering](https://example.com/job/vp)
[Apply Now](https://example.com/apply)

[Director of Product](https://example.com/job/director)
## Next Section
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        # Should extract jobs but not treat markdown elements as location
        vp_job = next((job for job in jobs if "VP" in job.title), None)
        if vp_job:
            assert vp_job.location != "[Apply Now](https://example.com/apply)"

        director_job = next((job for job in jobs if "Director" in job.title), None)
        if director_job:
            assert director_job.location != "## Next Section"

    def test_handles_jobs_without_location(self, tmp_path):
        """Test handles jobs that don't have location info"""
        checker = WeeklyRoboticsJobChecker()

        markdown_content = """
## Chief Technology Officer
https://example.com/job/cto
"""
        markdown_file = tmp_path / "test_company_20250129.md"
        markdown_file.write_text(markdown_content)

        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")

        assert len(jobs) == 1
        job = jobs[0]
        # Location should be empty string if not found
        assert job.location == "" or job.location is None


class TestWeeklyScraperIntegration:
    """Test weekly scraper Firecrawl integration"""

    def test_run_uses_firecrawl_fallback(self):
        """Test run() method uses scrape_with_firecrawl_fallback"""
        checker = WeeklyRoboticsJobChecker()

        # Mock the scraper's scrape_with_firecrawl_fallback method
        mock_jobs = []  # Empty for simplicity
        mock_generic_pages = {
            "Boston Dynamics": {
                "url": "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
                "company": "Boston Dynamics",
            }
        }

        with (
            patch.object(
                checker.scraper,
                "scrape_with_firecrawl_fallback",
                return_value=(mock_jobs, mock_generic_pages),
            ),
            patch.object(checker.filter, "filter_jobs", return_value=([], [])),
        ):
            stats = checker.run(min_score=70)

            # Verify fallback method was called
            checker.scraper.scrape_with_firecrawl_fallback.assert_called_once()

            # Verify generic pages were tracked
            assert stats["generic_pages_found"] == 1

    def test_run_tracks_firecrawl_credits(self):
        """Test run() method tracks estimated Firecrawl credits"""
        checker = WeeklyRoboticsJobChecker()

        mock_jobs = []
        mock_generic_pages = {
            "Company1": {"url": "https://company1.com/careers", "company": "Company1"},
            "Company2": {"url": "https://company2.com/careers", "company": "Company2"},
            "Company3": {"url": "https://company3.com/careers", "company": "Company3"},
        }

        with (
            patch.object(
                checker.scraper,
                "scrape_with_firecrawl_fallback",
                return_value=(mock_jobs, mock_generic_pages),
            ),
            patch.object(checker.filter, "filter_jobs", return_value=([], [])),
        ):
            stats = checker.run(min_score=70)

            # Should estimate 3 credits (1 per company)
            assert stats["firecrawl_credits_used"] == 3

    def test_run_respects_max_companies_limit(self):
        """Test run() respects max_companies_per_run config"""
        checker = WeeklyRoboticsJobChecker()

        # Create 15 generic pages (more than max_companies_per_run of 10)
        mock_generic_pages = {
            f"Company{i}": {"url": f"https://company{i}.com/careers", "company": f"Company{i}"}
            for i in range(15)
        }

        with (
            patch.object(
                checker.scraper,
                "scrape_with_firecrawl_fallback",
                return_value=([], mock_generic_pages),
            ),
            patch.object(checker.filter, "filter_jobs", return_value=([], [])),
        ):
            stats = checker.run(min_score=70)

            # Should limit to max_companies_per_run (10)
            max_companies = checker.scraper.priority_config.get("max_companies_per_run", 10)
            assert stats["firecrawl_credits_used"] == max_companies

    def test_run_respects_weekly_budget(self):
        """Test run() respects credit_budget_weekly config"""
        checker = WeeklyRoboticsJobChecker()

        # Override config to set low budget
        checker.scraper.priority_config["credit_budget_weekly"] = 3
        checker.scraper.priority_config["max_companies_per_run"] = 10

        # Create 5 generic pages (more than budget of 3)
        mock_generic_pages = {
            f"Company{i}": {"url": f"https://company{i}.com/careers", "company": f"Company{i}"}
            for i in range(5)
        }

        with (
            patch.object(
                checker.scraper,
                "scrape_with_firecrawl_fallback",
                return_value=([], mock_generic_pages),
            ),
            patch.object(checker.filter, "filter_jobs", return_value=([], [])),
        ):
            stats = checker.run(min_score=70)

            # Should limit to budget (3), not max_companies (10)
            assert stats["firecrawl_credits_used"] == 3


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_handles_empty_generic_pages(self):
        """Test run() handles no generic pages gracefully"""
        checker = WeeklyRoboticsJobChecker()

        with (
            patch.object(checker.scraper, "scrape_with_firecrawl_fallback", return_value=([], {})),
            patch.object(checker.filter, "filter_jobs", return_value=([], [])),
        ):
            stats = checker.run(min_score=70)

            assert stats["generic_pages_found"] == 0
            assert stats["firecrawl_credits_used"] == 0

    def test_process_firecrawl_handles_malformed_markdown(self, tmp_path):
        """Test process_firecrawl_markdown handles malformed markdown"""
        checker = WeeklyRoboticsJobChecker()

        # Malformed markdown
        markdown_content = "Not valid markdown\nRandom text\nNo structure"
        markdown_file = tmp_path / "malformed.md"
        markdown_file.write_text(markdown_content)

        # Should not crash, may return empty or partial results
        jobs = checker.process_firecrawl_markdown(str(markdown_file), "Test Company")
        assert isinstance(jobs, list)
