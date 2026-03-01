"""
Tests for CompanyScraper

Tests company monitoring scraping functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.jobs.company_scraper import CompanyScraper
from src.models import OpportunityData


@pytest.fixture
def company_scraper():
    """Create CompanyScraper instance with mocked dependencies"""
    with (
        patch("src.jobs.company_scraper.CompanyService"),
        patch("src.scrapers.playwright_career_scraper.PlaywrightCareerScraper"),
        patch("src.jobs.company_scraper.JobFilter"),
        patch("src.jobs.company_scraper.ProfileScorer"),
        patch("src.jobs.company_scraper.JobDatabase"),
        patch("src.jobs.company_scraper.JobNotifier"),
    ):
        scraper = CompanyScraper()
        # Mock increment_company_failures to return int (Issue #192 - failure logging)
        scraper.company_service.increment_company_failures = MagicMock(return_value=1)
        return scraper


class TestCompanyScraperInit:
    """Test CompanyScraper initialization"""

    def test_init_creates_dependencies(self, company_scraper):
        """Should initialize all required dependencies"""
        assert company_scraper.company_service is not None
        assert company_scraper.career_scraper is not None
        assert company_scraper.job_filter is not None
        assert company_scraper.scorer is not None
        assert company_scraper.database is not None
        assert company_scraper.notifier is not None


class TestScrapeAllCompanies:
    """Test scrape_all_companies method"""

    def test_scrape_all_companies_returns_stats(self, company_scraper):
        """Should return statistics dictionary"""
        # Mock company service to return empty list
        company_scraper.company_service.get_all_companies = MagicMock(return_value=[])

        stats = company_scraper.scrape_all_companies()

        assert isinstance(stats, dict)
        assert "companies_checked" in stats
        assert "jobs_scraped" in stats
        assert "jobs_stored" in stats

    def test_scrape_all_companies_processes_companies(self, company_scraper):
        """Should process each company"""
        # Mock company data
        companies = [
            {
                "id": 1,
                "name": "Test Company",
                "careers_url": "https://test.com/careers",
                "notes": "From Wes",
            }
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies()

        assert stats["companies_checked"] == 1
        company_scraper.career_scraper.scrape_jobs.assert_called_once()

    def test_scrape_all_companies_filters_by_notes(self, company_scraper):
        """Should filter companies by notes when company_filter provided"""
        companies = [
            {
                "id": 1,
                "name": "Wes Company",
                "careers_url": "https://test1.com",
                "notes": "From Wes",
            },
            {
                "id": 2,
                "name": "Other Company",
                "careers_url": "https://test2.com",
                "notes": "Other",
            },
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies(company_filter="From Wes")

        # Should only process the one company matching filter
        assert stats["companies_checked"] == 1

    def test_scrape_all_companies_handles_scraping_errors(self, company_scraper):
        """Should handle scraping errors gracefully"""
        companies = [
            {"id": 1, "name": "Test Company", "careers_url": "https://test.com", "notes": "Test"}
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(
            side_effect=Exception("Scraping failed")
        )
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies()

        assert stats["companies_checked"] == 1
        assert stats["scraping_errors"] == 1


class TestProcessScrapedJobs:
    """Test process_scraped_jobs method"""

    def test_process_scraped_jobs_filters_leadership(self, company_scraper):
        """Should filter for leadership roles"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job1",
                    source="company_monitoring",
                ),
                "regex",
            ),
            (
                OpportunityData(
                    type="direct_job",
                    title="Software Engineer",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job2",
                    source="company_monitoring",
                ),
                "regex",
            ),
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(side_effect=[True, False])
        company_scraper.scorer.score_job = MagicMock(
            return_value=(75, "B", {"seniority": 25, "domain": 20, "role_type": 15}, {})
        )
        company_scraper.database.job_exists = MagicMock(return_value=False)
        company_scraper.database.add_job = MagicMock()
        company_scraper.notifier.notify = MagicMock()

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should process leadership job but not IC role
        assert stats["leadership_jobs"] == 1

    def test_process_scraped_jobs_applies_min_score(self, company_scraper):
        """Should only store jobs above minimum score"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(45, "F", {"seniority": 15, "domain": 10, "role_type": 10}, {})
        )  # Below threshold
        company_scraper.database.job_exists = MagicMock(return_value=False)

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Job scored 45, min is 50, should not be stored
        assert stats["jobs_stored"] == 0

    def test_process_scraped_jobs_stores_high_score_job(self, company_scraper):
        """Should store jobs above minimum score using multi-scorer"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(75, "B", {"seniority": 25, "domain": 20, "role_type": 15}, {})
        )
        company_scraper.database.job_exists = MagicMock(return_value=False)
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.notifier.notify_job = MagicMock()

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should store job with 75 score (above 50 min)
        assert stats["jobs_above_threshold"] == 1
        assert stats["jobs_stored"] == 1
        company_scraper.database.add_job.assert_called_once()
        # Multi-profile scoring happens via _run_multi_profile_scoring (no direct update_job_score call)

    def test_process_scraped_jobs_sends_notifications_for_high_scores(self, company_scraper):
        """Should send notifications for jobs above notify threshold"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="VP of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(85, "A", {"seniority": 30, "domain": 25, "role_type": 20}, {})
        )
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.database.mark_notified = MagicMock()
        company_scraper.notifier.notify_job = MagicMock(return_value={"email": True, "sms": False})

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should send notification for 85 score (above 80 threshold)
        assert stats["notifications_sent"] == 1
        company_scraper.notifier.notify_job.assert_called_once()
        company_scraper.database.mark_notified.assert_called_once_with(1)

    def test_process_scraped_jobs_handles_notification_errors(self, company_scraper):
        """Should handle notification errors gracefully"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="VP of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(85, "A", {"seniority": 30, "domain": 25, "role_type": 20}, {})
        )
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.notifier.notify_job = MagicMock(
            side_effect=Exception("Notification failed")
        )

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should not crash but also not count notification as sent
        assert stats["notifications_sent"] == 0
        assert stats["jobs_stored"] == 1

    def test_process_scraped_jobs_skips_duplicates(self, company_scraper):
        """Should skip duplicate jobs"""
        jobs = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(75, "B", {"seniority": 25, "domain": 20, "role_type": 15}, {})
        )
        company_scraper.database.add_job = MagicMock(return_value=None)  # None means duplicate

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should skip duplicate
        assert stats["duplicates_skipped"] == 1
        assert stats["jobs_stored"] == 0

    def test_scrape_all_companies_aggregates_job_stats(self, company_scraper):
        """Should aggregate stats from processed jobs"""
        companies = [
            {
                "id": 1,
                "name": "Test Company",
                "careers_url": "https://test.com/careers",
                "notes": "Test",
            }
        ]
        jobs_with_methods = [
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Engineering",
                    company="Test Company",
                    location="Remote",
                    link="https://test.com/job",
                    source="company_monitoring",
                ),
                "regex",
            )
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=jobs_with_methods)
        company_scraper.company_service.update_last_checked = MagicMock()
        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(75, "B", {"seniority": 25, "domain": 20, "role_type": 15}, {})
        )
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.notifier.notify_job = MagicMock()

        stats = company_scraper.scrape_all_companies()

        # Should aggregate stats properly
        assert stats["companies_checked"] == 1
        assert stats["jobs_scraped"] == 1
        assert stats["leadership_jobs"] == 1
        assert stats["jobs_above_threshold"] == 1
        assert stats["jobs_stored"] == 1


class TestMainCLI:
    """Test main() CLI entry point"""

    def test_main_with_default_args(self, capsys):
        """Should run with default arguments"""
        import sys
        from unittest.mock import patch

        # Mock sys.argv to simulate command line arguments
        test_args = ["company_scraper.py"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.jobs.company_scraper.CompanyScraper") as mock_scraper_class,
        ):
            # Mock the scraper instance
            mock_scraper_class.return_value.scrape_all_companies = MagicMock(
                return_value={
                    "companies_checked": 5,
                    "jobs_scraped": 10,
                    "leadership_jobs": 8,
                    "jobs_hard_filtered": 0,
                    "jobs_context_filtered": 0,
                    "jobs_above_threshold": 6,
                    "jobs_stored": 6,
                    "notifications_sent": 2,
                }
            )

            # Import and call main
            from src.jobs.company_scraper import main

            main()

            # Verify scraper was called with default min_score=50
            mock_scraper_class.return_value.scrape_all_companies.assert_called_once_with(
                min_score=50, company_filter=None
            )

            # Check output contains summary
            captured = capsys.readouterr()
            assert "COMPANY SCRAPER SUMMARY" in captured.out
            assert "Companies checked: 5" in captured.out
            assert "Jobs scraped: 10" in captured.out

    def test_main_with_custom_min_score(self):
        """Should accept custom min_score argument"""
        import sys
        from unittest.mock import patch

        test_args = ["company_scraper.py", "--min-score", "70"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.jobs.company_scraper.CompanyScraper") as mock_scraper_class,
        ):
            mock_scraper_class.return_value.scrape_all_companies = MagicMock(
                return_value={
                    "companies_checked": 0,
                    "jobs_scraped": 0,
                    "leadership_jobs": 0,
                    "jobs_hard_filtered": 0,
                    "jobs_context_filtered": 0,
                    "jobs_above_threshold": 0,
                    "jobs_stored": 0,
                    "notifications_sent": 0,
                }
            )

            from src.jobs.company_scraper import main

            main()

            # Verify min_score was passed correctly
            mock_scraper_class.return_value.scrape_all_companies.assert_called_once_with(
                min_score=70, company_filter=None
            )

    def test_main_with_company_filter(self):
        """Should accept company filter argument"""
        import sys
        from unittest.mock import patch

        test_args = ["company_scraper.py", "--filter", "From Wes"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.jobs.company_scraper.CompanyScraper") as mock_scraper_class,
        ):
            mock_scraper_class.return_value.scrape_all_companies = MagicMock(
                return_value={
                    "companies_checked": 3,
                    "jobs_scraped": 5,
                    "leadership_jobs": 4,
                    "jobs_hard_filtered": 0,
                    "jobs_context_filtered": 0,
                    "jobs_above_threshold": 2,
                    "jobs_stored": 2,
                    "notifications_sent": 1,
                }
            )

            from src.jobs.company_scraper import main

            main()

            # Verify filter was passed correctly
            mock_scraper_class.return_value.scrape_all_companies.assert_called_once_with(
                min_score=50, company_filter="From Wes"
            )

    def test_main_with_all_arguments(self):
        """Should accept both min_score and filter arguments"""
        import sys
        from unittest.mock import patch

        test_args = ["company_scraper.py", "--min-score", "80", "--filter", "Priority"]

        with (
            patch.object(sys, "argv", test_args),
            patch("src.jobs.company_scraper.CompanyScraper") as mock_scraper_class,
        ):
            mock_scraper_class.return_value.scrape_all_companies = MagicMock(
                return_value={
                    "companies_checked": 2,
                    "jobs_scraped": 3,
                    "leadership_jobs": 3,
                    "jobs_hard_filtered": 0,
                    "jobs_context_filtered": 0,
                    "jobs_above_threshold": 1,
                    "jobs_stored": 1,
                    "notifications_sent": 1,
                }
            )

            from src.jobs.company_scraper import main

            main()

            # Verify both arguments were passed correctly
            mock_scraper_class.return_value.scrape_all_companies.assert_called_once_with(
                min_score=80, company_filter="Priority"
            )


class TestFilterPipelineIntegration:
    """Test filter pipeline integration in CompanyScraper"""

    @patch("src.jobs.company_scraper.get_profile_manager")
    @patch("src.jobs.company_scraper.JobFilterPipeline")
    def test_hard_filters_block_before_scoring(self, mock_pipeline_class, mock_get_pm):
        """
        Test Issue #258 fix: Jobs are NOT filtered before scoring.
        All jobs go through multi-profile scoring regardless of hard filters.
        Hard filters are now applied per-profile inside multi_scorer.
        """
        # Setup profile
        mock_profile = MagicMock()
        mock_profile.scoring = {"hard_filter_keywords": {"seniority_blocks": ["junior"]}}
        mock_pm = MagicMock()
        mock_pm.get_profile.return_value = mock_profile
        mock_get_pm.return_value = mock_pm

        mock_pipeline = MagicMock()
        # Context filters should pass (return True) in this test
        mock_pipeline.apply_context_filters.return_value = (True, None)
        mock_pipeline_class.return_value = mock_pipeline

        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.scrapers.playwright_career_scraper.PlaywrightCareerScraper"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer") as mock_scorer_class,
            patch("src.jobs.company_scraper.JobDatabase") as mock_db_class,
            patch("src.jobs.company_scraper.JobNotifier"),
        ):
            # Configure mocks
            mock_db = MagicMock()
            mock_db.add_job.return_value = 123  # Job ID
            mock_db_class.return_value = mock_db

            # Mock scorer to return 4-tuple: (score, grade, breakdown, metadata)
            mock_scorer = MagicMock()
            mock_scorer.score_job.return_value = (
                55,  # score
                "D",  # grade
                {"seniority": 15, "domain": 20, "role_type": 10},  # breakdown
                {},  # metadata
            )
            mock_scorer_class.return_value = mock_scorer

            scraper = CompanyScraper(profile="wes")
            scraper.job_filter.is_leadership_role = MagicMock(return_value=True)

            # Mock the multi_scorer that gets imported dynamically inside process_scraped_jobs
            with patch("utils.multi_scorer.get_multi_scorer") as mock_get_multi_scorer:
                mock_multi_scorer = MagicMock()
                mock_get_multi_scorer.return_value = mock_multi_scorer

                jobs = [
                    (
                        OpportunityData(
                            type="direct_job",
                            title="Junior Director",  # Would have been hard-filtered in old code
                            company="Test Company",
                            location="Remote",
                            link="https://test.com/job",
                            source="company_monitoring",
                        ),
                        "regex",
                    )
                ]

                stats = scraper.process_scraped_jobs(
                    "Test Company", jobs, min_score=50, notify_threshold=80
                )

                # NEW BEHAVIOR (Issue #258): No pre-scoring hard filtering
                assert stats["jobs_hard_filtered"] == 0
                mock_pipeline.apply_hard_filters.assert_not_called()

                # Job should be stored and multi-scored
                assert mock_db.add_job.call_count == 1
                assert mock_multi_scorer.score_job_for_all.call_count == 1

    @patch("src.jobs.company_scraper.get_profile_manager")
    @patch("src.jobs.company_scraper.JobFilterPipeline")
    def test_context_filters_block_after_scoring(self, mock_pipeline_class, mock_get_pm):
        """Should apply context filters after scoring and update job with filter_reason"""
        # Setup profile and filter pipeline
        mock_profile = MagicMock()
        mock_profile.scoring = {"context_filters": {}}
        mock_pm = MagicMock()
        mock_pm.get_profile.return_value = mock_profile
        mock_get_pm.return_value = mock_pm

        mock_pipeline = MagicMock()
        mock_pipeline.apply_hard_filters.return_value = (True, None)  # Pass hard filters
        mock_pipeline.apply_context_filters.return_value = (
            False,
            "context_filter_software_engineering",
        )
        mock_pipeline_class.return_value = mock_pipeline

        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.scrapers.playwright_career_scraper.PlaywrightCareerScraper"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
        ):
            scraper = CompanyScraper(profile="wes")
            scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
            scraper.scorer.score_job = MagicMock(
                return_value=(75, "B", {"seniority": 25, "domain": 20, "role_type": 15}, {})
            )
            scraper.database.add_job = MagicMock(return_value=1)  # Job stored successfully
            scraper.database.update_job_score = MagicMock()

            jobs = [
                (
                    OpportunityData(
                        type="direct_job",
                        title="Director of Software Engineering",
                        company="Test Company",
                        location="Remote",
                        link="https://test.com/job",
                        source="company_monitoring",
                    ),
                    "regex",
                )
            ]

            stats = scraper.process_scraped_jobs(
                "Test Company", jobs, min_score=50, notify_threshold=80
            )

            # Should apply context filter after scoring
            assert stats["jobs_context_filtered"] == 1
            assert stats["jobs_stored"] == 0  # Filtered jobs don't count as "stored"
            mock_pipeline.apply_context_filters.assert_called_once()
            # Should add filtered job to database for audit
            scraper.database.add_job.assert_called_once()
            # Multi-profile scoring happens via _run_multi_profile_scoring (no direct update_job_score call)

    @patch("src.jobs.company_scraper.get_profile_manager")
    @patch("src.jobs.company_scraper.JobFilterPipeline")
    def test_filtered_stats_aggregation(self, mock_pipeline_class, mock_get_pm):
        """
        Test Issue #258 fix: No pre-scoring hard filtering.
        Only context filters (after scoring) can block jobs.
        Stats should reflect: no hard filtered jobs, context filters still work.
        """
        mock_profile = MagicMock()
        mock_profile.scoring = {"hard_filter_keywords": {}, "context_filters": {}}
        mock_pm = MagicMock()
        mock_pm.get_profile.return_value = mock_profile
        mock_get_pm.return_value = mock_pm

        mock_pipeline = MagicMock()
        # Context filters (applied AFTER scoring): filter 1st job, pass 2nd and 3rd
        mock_pipeline.apply_context_filters.side_effect = [
            (False, "context_filter_software_engineering"),  # Job 1 filtered
            (True, None),  # Job 2 passes
            (True, None),  # Job 3 passes
        ]
        mock_pipeline_class.return_value = mock_pipeline

        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.scrapers.playwright_career_scraper.PlaywrightCareerScraper"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer") as mock_scorer_class,
            patch("src.jobs.company_scraper.JobDatabase") as mock_db_class,
            patch("src.jobs.company_scraper.JobNotifier"),
        ):
            # Configure mocks
            mock_db = MagicMock()
            # Job IDs: all jobs stored (even context-filtered ones for audit)
            mock_db.add_job.side_effect = [1, 2, 3]
            mock_db_class.return_value = mock_db

            # Mock scorer to return 4-tuple: (score, grade, breakdown, metadata)
            mock_scorer = MagicMock()
            mock_scorer.score_job.return_value = (
                75,  # score
                "B",  # grade
                {"seniority": 25, "domain": 20, "role_type": 15},  # breakdown
                {},  # metadata
            )
            mock_scorer_class.return_value = mock_scorer

            scraper = CompanyScraper(profile="wes")
            scraper.job_filter.is_leadership_role = MagicMock(return_value=True)

            # Mock the multi_scorer that gets imported dynamically inside process_scraped_jobs
            with patch("utils.multi_scorer.get_multi_scorer") as mock_get_multi_scorer:
                mock_multi_scorer = MagicMock()
                mock_get_multi_scorer.return_value = mock_multi_scorer

                jobs = [
                    (
                        OpportunityData(
                            type="direct_job",
                            title="Director of Software Engineering",  # Will be context-filtered
                            company="Test",
                            location="Remote",
                            link="https://test.com/job1",
                            source="company_monitoring",
                        ),
                        "regex",
                    ),
                    (
                        OpportunityData(
                            type="direct_job",
                            title="VP of Hardware Engineering",  # Passes
                            company="Test",
                            location="Remote",
                            link="https://test.com/job2",
                            source="company_monitoring",
                        ),
                        "regex",
                    ),
                    (
                        OpportunityData(
                            type="direct_job",
                            title="Director of Product",  # Passes
                            company="Test",
                            location="Remote",
                            link="https://test.com/job3",
                            source="company_monitoring",
                        ),
                        "regex",
                    ),
                ]

                stats = scraper.process_scraped_jobs("Test Company", jobs)

                # NEW BEHAVIOR (Issue #258)
                assert stats["jobs_hard_filtered"] == 0  # No pre-scoring hard filtering
                assert stats["jobs_context_filtered"] == 1  # One job context-filtered after scoring
                assert stats["jobs_processed"] == 3  # All jobs processed

                # Verify no hard filtering happened before scoring
                mock_pipeline.apply_hard_filters.assert_not_called()

                # Verify all jobs stored (even context-filtered for audit)
                assert mock_db.add_job.call_count == 3

                # Verify multi-profile scoring called for ALL jobs (including context-filtered)
                # Context filtering only affects whether job is "passing" for current profile
                # but all jobs get scored for all profiles regardless
                assert mock_multi_scorer.score_job_for_all.call_count == 3


class TestSkipRecentHours:
    """Test skip_recent_hours functionality"""

    def test_skip_recent_hours_filters_recently_checked(self, company_scraper):
        """Should skip companies checked within specified hours"""
        from datetime import datetime, timedelta

        # Create companies with different last_checked times
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        three_hours_ago = (datetime.now() - timedelta(hours=3)).isoformat()

        companies = [
            {
                "id": 1,
                "name": "Recent Company",
                "careers_url": "https://test1.com",
                "notes": "Test",
                "last_checked": one_hour_ago,  # Within 2 hours
            },
            {
                "id": 2,
                "name": "Old Company",
                "careers_url": "https://test2.com",
                "notes": "Test",
                "last_checked": three_hours_ago,  # Outside 2 hours
            },
            {
                "id": 3,
                "name": "Never Checked",
                "careers_url": "https://test3.com",
                "notes": "Test",
                "last_checked": None,  # Never checked
            },
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies(skip_recent_hours=2)

        # Should skip company 1 (checked 1 hour ago), scrape companies 2 and 3
        assert stats["companies_skipped"] == 1
        assert stats["companies_checked"] == 2

    def test_skip_recent_hours_none_scrapes_all(self, company_scraper):
        """Should scrape all companies when skip_recent_hours is None"""
        from datetime import datetime, timedelta

        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        companies = [
            {
                "id": 1,
                "name": "Company 1",
                "careers_url": "https://test1.com",
                "notes": "Test",
                "last_checked": one_hour_ago,
            },
            {
                "id": 2,
                "name": "Company 2",
                "careers_url": "https://test2.com",
                "notes": "Test",
                "last_checked": one_hour_ago,
            },
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies(skip_recent_hours=None)

        # Should scrape all companies
        assert stats["companies_skipped"] == 0
        assert stats["companies_checked"] == 2

    def test_skip_recent_hours_with_company_filter(self, company_scraper):
        """Should apply both skip_recent_hours and company_filter"""
        from datetime import datetime, timedelta

        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        three_hours_ago = (datetime.now() - timedelta(hours=3)).isoformat()

        companies = [
            {
                "id": 1,
                "name": "Wes Recent",
                "careers_url": "https://test1.com",
                "notes": "From Wes",
                "last_checked": one_hour_ago,  # Within 2 hours
            },
            {
                "id": 2,
                "name": "Wes Old",
                "careers_url": "https://test2.com",
                "notes": "From Wes",
                "last_checked": three_hours_ago,  # Outside 2 hours
            },
            {
                "id": 3,
                "name": "Other Company",
                "careers_url": "https://test3.com",
                "notes": "Other",
                "last_checked": None,
            },
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies(company_filter="From Wes", skip_recent_hours=2)

        # Should filter to 2 "From Wes" companies, then skip 1 (checked recently)
        assert stats["companies_skipped"] == 1
        assert stats["companies_checked"] == 1


class TestFailureLogging:
    """Test failure logging functionality (Issue #192)"""

    def test_init_creates_failure_log_attributes(self, company_scraper):
        """Should initialize failure logging attributes on init"""
        # Should have failure log path
        assert hasattr(company_scraper, "failure_log_path")
        assert "logs/scraper_failures.log" in str(company_scraper.failure_log_path)

        # Should have failure log file object
        assert hasattr(company_scraper, "failure_log")

        # Should initialize failures list
        assert hasattr(company_scraper, "failures")
        assert isinstance(company_scraper.failures, list)

    def test_log_failure_writes_to_file_and_memory(self, company_scraper, tmp_path):
        """Should log failure to file and track in memory"""
        # Use real file for this test
        log_file = tmp_path / "test_failures.log"
        company_scraper.failure_log_path = log_file
        company_scraper.failure_log = open(log_file, "a", encoding="utf-8")  # noqa: SIM115
        company_scraper.failures = []

        # Log a failure
        company_scraper._log_failure(
            company_name="Test Company",
            url="https://test.com/careers",
            failure_count=2,
            reason="0 jobs extracted",
        )

        # Close and read the file
        company_scraper.failure_log.close()
        log_content = log_file.read_text()

        # Should write to file
        assert "Test Company" in log_content
        assert "https://test.com/careers" in log_content
        assert "2/5" in log_content
        assert "0 jobs extracted" in log_content

        # Should track in memory
        assert len(company_scraper.failures) == 1
        assert company_scraper.failures[0]["company"] == "Test Company"
        assert company_scraper.failures[0]["url"] == "https://test.com/careers"
        assert company_scraper.failures[0]["failure_count"] == 2
        assert company_scraper.failures[0]["reason"] == "0 jobs extracted"

    def test_log_failure_flushes_immediately(self, company_scraper):
        """Should flush log file immediately for real-time logging"""
        mock_log_file = MagicMock()
        company_scraper.failure_log = mock_log_file
        company_scraper.failures = []

        company_scraper._log_failure(
            company_name="Test Company",
            url="https://test.com/careers",
            failure_count=1,
            reason="0 jobs extracted",
        )

        # Should flush after write
        mock_log_file.flush.assert_called_once()

    def test_scrape_logs_no_jobs_extracted_failure(self, company_scraper):
        """Should log failure when no jobs are extracted"""
        companies = [
            {
                "id": 1,
                "name": "Empty Company",
                "careers_url": "https://empty.com/careers",
                "notes": "Test",
            }
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])  # No jobs
        company_scraper.company_service.increment_company_failures = MagicMock(return_value=2)
        company_scraper.company_service.update_last_checked = MagicMock()
        company_scraper._log_failure = MagicMock()

        company_scraper.scrape_all_companies()

        # Should log the failure
        company_scraper._log_failure.assert_called_once_with(
            company_name="Empty Company",
            url="https://empty.com/careers",
            failure_count=2,
            reason="0 jobs extracted",
        )

    def test_scrape_logs_exception_failure(self, company_scraper):
        """Should log failure when exception occurs during scraping"""
        companies = [
            {"id": 1, "name": "Error Company", "careers_url": "https://error.com", "notes": "Test"}
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(
            side_effect=Exception("Firecrawl API error")
        )
        company_scraper._log_failure = MagicMock()

        stats = company_scraper.scrape_all_companies()

        # Should log the exception
        assert company_scraper._log_failure.called
        call_args = company_scraper._log_failure.call_args[1]
        assert call_args["company_name"] == "Error Company"
        assert call_args["url"] == "https://error.com"
        assert "Firecrawl API error" in call_args["reason"]

        # Should still track error in stats
        assert stats["scraping_errors"] == 1

    def test_print_failure_summary_shows_all_failures(self, company_scraper, capsys):
        """Should print summary of all failures"""
        company_scraper.failures = [
            {
                "timestamp": "2024-01-15T10:00:00",
                "company": "Company A",
                "url": "https://a.com/careers",
                "failure_count": 2,
                "reason": "0 jobs extracted",
            },
            {
                "timestamp": "2024-01-15T10:05:00",
                "company": "Company B",
                "url": "https://b.com/careers",
                "failure_count": 5,
                "reason": "Exception: API error",
            },
        ]
        company_scraper.failure_log_path = "logs/scraper_failures.log"

        company_scraper._print_failure_summary()

        captured = capsys.readouterr()

        # Should show failure count
        assert "2 companies failed" in captured.out

        # Should show first failure
        assert "Company A" in captured.out
        assert "https://a.com/careers" in captured.out
        assert "2/5" in captured.out
        assert "0 jobs extracted" in captured.out

        # Should show second failure with AUTO-DISABLED status
        assert "Company B" in captured.out
        assert "🚫 AUTO-DISABLED" in captured.out
        assert "5" in captured.out
        assert "API error" in captured.out

        # Should show log file location
        assert "logs/scraper_failures.log" in captured.out

    def test_print_failure_summary_no_output_when_no_failures(self, company_scraper, capsys):
        """Should not print anything when there are no failures"""
        company_scraper.failures = []

        company_scraper._print_failure_summary()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_close_failure_log_closes_file(self, company_scraper):
        """Should close the log file"""
        mock_log_file = MagicMock()
        mock_log_file.closed = False
        company_scraper.failure_log = mock_log_file

        company_scraper._close_failure_log()

        mock_log_file.close.assert_called_once()

    def test_close_failure_log_handles_already_closed(self, company_scraper):
        """Should handle already closed log file"""
        mock_log_file = MagicMock()
        mock_log_file.closed = True
        company_scraper.failure_log = mock_log_file

        # Should not raise exception
        company_scraper._close_failure_log()

        # Should not call close again
        mock_log_file.close.assert_not_called()

    def test_destructor_closes_log_file(self, company_scraper):
        """Should close log file in destructor"""
        mock_log_file = MagicMock()
        mock_log_file.closed = False
        company_scraper.failure_log = mock_log_file
        company_scraper._close_failure_log = MagicMock()

        # Trigger destructor
        company_scraper.__del__()

        # Should call close method
        company_scraper._close_failure_log.assert_called_once()

    def test_scrape_all_companies_calls_failure_summary_and_close(self, company_scraper):
        """Should print failure summary and close log at end of scraping"""
        companies = [
            {"id": 1, "name": "Test Company", "careers_url": "https://test.com", "notes": "Test"}
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.increment_company_failures = MagicMock(return_value=1)
        company_scraper.company_service.update_last_checked = MagicMock()
        company_scraper._print_failure_summary = MagicMock()
        company_scraper._close_failure_log = MagicMock()

        company_scraper.scrape_all_companies()

        # Should call both methods at end
        company_scraper._print_failure_summary.assert_called_once()
        company_scraper._close_failure_log.assert_called_once()


class TestScraperBackendSelection:
    """Test scraper backend selection"""

    def test_default_backend_is_playwright(self):
        """Default backend should be playwright"""
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch("scrapers.playwright_career_scraper.PlaywrightCareerScraper") as mock_playwright,
        ):
            scraper = CompanyScraper()
            mock_playwright.assert_called_once()
            assert scraper.career_scraper is not None

    def test_firecrawl_backend(self, monkeypatch):
        """scraper_backend='firecrawl' uses FirecrawlCareerScraper"""
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch("scrapers.firecrawl_career_scraper.FirecrawlCareerScraper") as mock_firecrawl,
        ):
            scraper = CompanyScraper(scraper_backend="firecrawl")
            mock_firecrawl.assert_called_once()
            assert scraper.career_scraper is not None

    def test_env_var_backend(self, monkeypatch):
        """SCRAPER_BACKEND env var is respected when no CLI arg"""
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
        monkeypatch.setenv("SCRAPER_BACKEND", "firecrawl")
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch("scrapers.firecrawl_career_scraper.FirecrawlCareerScraper") as mock_firecrawl,
        ):
            scraper = CompanyScraper()
            mock_firecrawl.assert_called_once()
            assert scraper.career_scraper is not None
