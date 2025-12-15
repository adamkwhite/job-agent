"""
Tests for JobProcessorV2 helper methods
"""

import email
from unittest.mock import MagicMock, patch

import pytest

from src.processor_v2 import JobProcessorV2


class TestProcessorV2HelperMethods:
    """Test helper methods in JobProcessorV2"""

    @pytest.fixture
    def processor(self):
        """Create a JobProcessorV2 instance with mocked dependencies"""
        with (
            patch("src.processor_v2.IMAPEmailClient"),
            patch("src.processor_v2.JobDatabase"),
            patch("src.processor_v2.JobFilter"),
            patch("src.processor_v2.JobNotifier"),
            patch("src.processor_v2.ProfileScorer"),
            patch("src.processor_v2.EnrichmentPipeline"),
            patch("src.processor_v2.get_profile_manager"),
        ):
            processor = JobProcessorV2()
            return processor

    def test_increment_stat(self, processor):
        """Test _increment_stat helper increments counter correctly"""
        stats: dict[str, int | list[str]] = {"count": 0, "errors": []}

        processor._increment_stat(stats, "count", 1)
        assert stats["count"] == 1

        processor._increment_stat(stats, "count", 5)
        assert stats["count"] == 6

        processor._increment_stat(stats, "count")  # Default amount=1
        assert stats["count"] == 7

    def test_append_error(self, processor):
        """Test _append_error helper appends error strings correctly"""
        stats: dict[str, int | list[str]] = {"count": 0, "errors": []}

        processor._append_error(stats, "Error 1")
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1
        assert errors_list[0] == "Error 1"

        processor._append_error(stats, "Error 2")
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 2
        assert errors_list[1] == "Error 2"

    def test_handle_parse_error(self, processor):
        """Test _handle_parse_error appends error to stats"""
        stats: dict[str, int | list[str]] = {"errors": []}

        processor._handle_parse_error("Parse failed: Invalid format", stats)

        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1
        assert "Parse error: Parse failed: Invalid format" in errors_list[0]

    def test_handle_parse_error_with_none(self, processor):
        """Test _handle_parse_error handles None error"""
        stats: dict[str, int | list[str]] = {"errors": []}

        processor._handle_parse_error(None, stats)

        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1
        assert "Parse error: None" in errors_list[0]

    def test_process_single_email_parse_failure(self, processor):
        """Test _process_single_email handles parse failures"""
        stats: dict[str, int | list[str]] = {
            "emails_processed": 0,
            "opportunities_found": 0,
            "errors": [],
        }

        # Mock parser to return failure
        parse_result = MagicMock()
        parse_result.success = False
        parse_result.error = "Invalid email format"
        processor.parser_registry.parse_email = MagicMock(return_value=parse_result)

        # Create a simple email message
        email_message = email.message_from_string("Subject: Test\n\nBody")

        processor._process_single_email(email_message, stats)

        # Should have error but no email processed
        assert stats["emails_processed"] == 0
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1

    def test_process_single_email_success(self, processor):
        """Test _process_single_email processes successfully"""
        stats: dict[str, int | list[str]] = {
            "emails_processed": 0,
            "opportunities_found": 0,
            "opportunities_enriched": 0,
            "jobs_passed_filter": 0,
            "jobs_stored": 0,
            "jobs_scored": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        # Mock successful parse result
        mock_opportunity = MagicMock()
        mock_opportunity.research_attempted = True
        parse_result = MagicMock()
        parse_result.success = True
        parse_result.opportunities = [mock_opportunity]
        parse_result.parser_name = "TestParser"
        processor.parser_registry.parse_email = MagicMock(return_value=parse_result)

        # Mock enrichment to return same opportunities
        processor.enrichment.enrich_opportunities = MagicMock(return_value=[mock_opportunity])

        # Mock filter to exclude all jobs
        processor.filter.filter_jobs = MagicMock(return_value=([], []))

        # Create a simple email message
        email_message = email.message_from_string("Subject: Test\n\nBody")

        processor._process_single_email(email_message, stats)

        # Should have processed the email
        assert stats["emails_processed"] == 1
        assert stats["opportunities_found"] == 1
        assert stats["opportunities_enriched"] == 1

    def test_enrich_and_filter_opportunities(self, processor):
        """Test _enrich_and_filter_opportunities enriches and filters correctly"""
        stats: dict[str, int | list[str]] = {
            "opportunities_found": 0,
            "opportunities_enriched": 0,
            "jobs_passed_filter": 0,
        }

        # Create mock parse result
        mock_opportunity = MagicMock()
        mock_opportunity.research_attempted = True
        mock_opportunity.title = "Software Engineer"
        mock_opportunity.company = "Test Corp"
        mock_opportunity.location = "Remote"
        mock_opportunity.link = "https://example.com/job"
        mock_opportunity.description = "Great job"
        mock_opportunity.salary = "$100k"
        mock_opportunity.job_type = "Full-time"
        mock_opportunity.posted_date = "2025-10-23"
        mock_opportunity.source = "LinkedIn"
        mock_opportunity.source_email = "jobs@linkedin.com"
        mock_opportunity.received_at = "2025-10-23T10:00:00"
        mock_opportunity.keywords_matched = ["python"]
        mock_opportunity.raw_content = "raw content"
        mock_opportunity.career_page_url = None
        mock_opportunity.company_location = None

        parse_result = MagicMock()
        parse_result.opportunities = [mock_opportunity]
        parse_result.parser_name = "TestParser"

        # Mock enrichment
        enriched_opp = MagicMock()
        enriched_opp.research_attempted = True
        enriched_opp.title = "Software Engineer"
        enriched_opp.company = "Test Corp"
        enriched_opp.location = "Remote"
        enriched_opp.link = "https://example.com/job"
        enriched_opp.description = "Great job"
        enriched_opp.salary = "$100k"
        enriched_opp.job_type = "Full-time"
        enriched_opp.posted_date = "2025-10-23"
        enriched_opp.source = "LinkedIn"
        enriched_opp.source_email = "jobs@linkedin.com"
        enriched_opp.received_at = "2025-10-23T10:00:00"
        enriched_opp.keywords_matched = ["python"]
        enriched_opp.raw_content = "raw content"
        enriched_opp.career_page_url = None
        enriched_opp.company_location = None

        processor.enrichment.enrich_opportunities = MagicMock(return_value=[enriched_opp])

        # Mock filter to pass 1 job
        included_job = {"title": "Software Engineer", "company": "Test Corp"}
        processor.filter.filter_jobs = MagicMock(return_value=([included_job], []))

        result = processor._enrich_and_filter_opportunities(parse_result, stats)

        assert len(result) == 1
        assert result[0]["title"] == "Software Engineer"
        assert stats["opportunities_found"] == 1
        assert stats["opportunities_enriched"] == 1
        assert stats["jobs_passed_filter"] == 1

    def test_store_and_process_job_duplicate(self, processor):
        """Test _store_and_process_job handles duplicate jobs"""
        stats: dict[str, int | list[str]] = {"jobs_stored": 0}

        job_dict = {
            "title": "Software Engineer",
            "company": "Test Corp",
            "link": "https://test.com",
        }

        # Mock database to return None (duplicate)
        processor.database.add_job = MagicMock(return_value=None)

        processor._store_and_process_job(job_dict, stats)

        # Should not increment jobs_stored
        assert stats["jobs_stored"] == 0

    def test_store_and_process_job_new(self, processor):
        """Test _store_and_process_job processes new jobs"""
        stats: dict[str, int | list[str]] = {
            "jobs_stored": 0,
            "jobs_scored": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        job_dict = {
            "title": "Software Engineer",
            "company": "Test Corp",
            "link": "https://test.com",
            "keywords_matched": ["python"],
        }

        # Mock database to return job_id (new job)
        processor.database.add_job = MagicMock(return_value=123)

        # Mock scoring
        processor.scorer.score_job = MagicMock(
            return_value=(85, "A", {"seniority": 30, "domain": 30, "role_type": 25}, {})
        )
        processor.database.update_job_score = MagicMock()

        # Mock notification
        processor.notifier.notify_job = MagicMock(return_value={"email": True, "sms": True})
        processor.database.mark_notified = MagicMock()

        processor._store_and_process_job(job_dict, stats)

        # Should increment all counters
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1
        assert stats["notifications_sent"] == 1

    def test_score_and_update_job_success(self, processor):
        """Test _score_and_update_job successfully scores job"""
        stats: dict[str, int | list[str]] = {"jobs_scored": 0, "errors": []}

        job_dict = {"title": "Software Engineer"}

        processor.scorer.score_job = MagicMock(
            return_value=(85, "A", {"seniority": 30, "domain": 30, "role_type": 25}, {})
        )
        processor.database.update_job_score = MagicMock()

        score, grade, breakdown = processor._score_and_update_job(123, job_dict, stats)

        assert score == 85
        assert grade == "A"
        assert breakdown == {"seniority": 30, "domain": 30, "role_type": 25}
        assert stats["jobs_scored"] == 1

    def test_score_and_update_job_failure(self, processor):
        """Test _score_and_update_job handles scoring errors"""
        stats: dict[str, int | list[str]] = {"jobs_scored": 0, "errors": []}

        job_dict = {"title": "Software Engineer"}

        processor.scorer.score_job = MagicMock(side_effect=Exception("Scoring failed"))

        score, grade, breakdown = processor._score_and_update_job(123, job_dict, stats)

        assert score is None
        assert grade is None
        assert breakdown is None
        assert stats["jobs_scored"] == 0
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1

    def test_notify_if_qualified_low_score(self, processor):
        """Test _notify_if_qualified skips notification for low scores"""
        stats: dict[str, int | list[str]] = {"notifications_sent": 0, "errors": []}

        job_dict = {"title": "Software Engineer"}

        processor._notify_if_qualified(123, job_dict, 65, "C", stats)

        # Should not send notification (score < 70)
        assert stats["notifications_sent"] == 0

    def test_notify_if_qualified_high_score(self, processor):
        """Test _notify_if_qualified sends notification for high scores"""
        stats: dict[str, int | list[str]] = {"notifications_sent": 0, "errors": []}

        job_dict = {"title": "Software Engineer", "company": "Test Corp"}

        processor.notifier.notify_job = MagicMock(return_value={"email": True, "sms": True})
        processor.database.mark_notified = MagicMock()

        processor._notify_if_qualified(123, job_dict, 85, "A", stats)

        # Should send notification (score >= 70)
        assert stats["notifications_sent"] == 1
        processor.database.mark_notified.assert_called_once_with(123)

    def test_notify_if_qualified_notification_failure(self, processor):
        """Test _notify_if_qualified handles notification errors"""
        stats: dict[str, int | list[str]] = {"notifications_sent": 0, "errors": []}

        job_dict = {"title": "Software Engineer"}

        processor.notifier.notify_job = MagicMock(side_effect=Exception("SMS failed"))

        processor._notify_if_qualified(123, job_dict, 85, "A", stats)

        # Should not increment notifications_sent
        assert stats["notifications_sent"] == 0
        errors_list = stats["errors"]
        assert isinstance(errors_list, list)
        assert len(errors_list) == 1

    def test_validate_job_urls_empty_list(self, processor):
        """Test _validate_job_urls returns empty list for empty input"""
        stats: dict[str, int | list[str]] = {}

        result = processor._validate_job_urls([], stats)

        assert result == []
        assert stats == {}  # No stats updated for empty input

    @patch("src.processor_v2.JobValidator")
    def test_validate_job_urls_all_valid(self, mock_validator_class, processor):
        """Test _validate_job_urls with all valid jobs"""
        stats: dict[str, int | list[str]] = {
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
        }

        jobs = [
            {"title": "Software Engineer", "company": "Test Corp", "link": "https://test.com/job1"},
            {"title": "Product Manager", "company": "Acme Inc", "link": "https://acme.com/job2"},
        ]

        # Mock validator to return all jobs as valid
        mock_validator = MagicMock()
        mock_validator.filter_valid_jobs.return_value = (jobs, [], [])
        mock_validator_class.return_value = mock_validator

        result = processor._validate_job_urls(jobs, stats)

        # Should return all jobs
        assert len(result) == 2
        assert result == jobs

        # Should update stats correctly
        assert stats["jobs_validated"] == 2
        assert stats["jobs_valid"] == 2
        assert stats["jobs_flagged"] == 0
        assert stats["jobs_invalid"] == 0

        # Should have called validator with correct params
        mock_validator.filter_valid_jobs.assert_called_once_with(jobs, show_progress=False)

    @patch("src.processor_v2.JobValidator")
    def test_validate_job_urls_with_flagged(self, mock_validator_class, processor):
        """Test _validate_job_urls with flagged jobs (needs review)"""
        stats: dict[str, int | list[str]] = {
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
        }

        valid_job = {
            "title": "Software Engineer",
            "company": "Test Corp",
            "link": "https://test.com/job1",
        }
        flagged_job = {
            "title": "Product Manager",
            "company": "Acme Inc",
            "link": "https://linkedin.com/jobs/123",
            "validation_reason": "linkedin_unverifiable",
        }

        # Mock validator to return 1 valid, 1 flagged
        mock_validator = MagicMock()
        mock_validator.filter_valid_jobs.return_value = ([valid_job], [flagged_job], [])
        mock_validator_class.return_value = mock_validator

        result = processor._validate_job_urls([valid_job, flagged_job], stats)

        # Should return valid + flagged jobs
        assert len(result) == 2
        assert valid_job in result
        assert flagged_job in result

        # Flagged job should have needs_review flag added
        assert flagged_job.get("needs_review") is True

        # Should update stats correctly
        assert stats["jobs_validated"] == 2
        assert stats["jobs_valid"] == 1
        assert stats["jobs_flagged"] == 1
        assert stats["jobs_invalid"] == 0

    @patch("src.processor_v2.JobValidator")
    def test_validate_job_urls_with_invalid(self, mock_validator_class, processor):
        """Test _validate_job_urls filters out invalid/stale jobs"""
        stats: dict[str, int | list[str]] = {
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
        }

        valid_job = {
            "title": "Software Engineer",
            "company": "Test Corp",
            "link": "https://test.com/job1",
        }
        invalid_job = {
            "title": "Stale Job",
            "company": "Old Corp",
            "link": "https://old.com/job2",
            "validation_reason": "stale_no_longer_accepting",
        }

        # Mock validator to return 1 valid, 0 flagged, 1 invalid
        mock_validator = MagicMock()
        mock_validator.filter_valid_jobs.return_value = ([valid_job], [], [invalid_job])
        mock_validator_class.return_value = mock_validator

        result = processor._validate_job_urls([valid_job, invalid_job], stats)

        # Should return only valid jobs (invalid filtered out)
        assert len(result) == 1
        assert result == [valid_job]
        assert invalid_job not in result

        # Should update stats correctly
        assert stats["jobs_validated"] == 2
        assert stats["jobs_valid"] == 1
        assert stats["jobs_flagged"] == 0
        assert stats["jobs_invalid"] == 1

    @patch("src.processor_v2.JobValidator")
    def test_validate_job_urls_mixed_results(self, mock_validator_class, processor):
        """Test _validate_job_urls with mix of valid, flagged, and invalid jobs"""
        stats: dict[str, int | list[str]] = {
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
        }

        valid_job1 = {"title": "Job 1", "company": "Corp A", "link": "https://a.com/job1"}
        valid_job2 = {"title": "Job 2", "company": "Corp B", "link": "https://b.com/job2"}
        flagged_job = {
            "title": "Job 3",
            "company": "Corp C",
            "link": "https://linkedin.com/jobs/123",
            "validation_reason": "generic_page",
        }
        invalid_job = {
            "title": "Job 4",
            "company": "Corp D",
            "link": "https://d.com/job4",
            "validation_reason": "404_not_found",
        }

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.filter_valid_jobs.return_value = (
            [valid_job1, valid_job2],
            [flagged_job],
            [invalid_job],
        )
        mock_validator_class.return_value = mock_validator

        result = processor._validate_job_urls(
            [valid_job1, valid_job2, flagged_job, invalid_job], stats
        )

        # Should return valid + flagged (exclude invalid)
        assert len(result) == 3
        assert valid_job1 in result
        assert valid_job2 in result
        assert flagged_job in result
        assert invalid_job not in result

        # Flagged job should have needs_review flag
        assert flagged_job.get("needs_review") is True
        assert valid_job1.get("needs_review") is None
        assert valid_job2.get("needs_review") is None

        # Should update stats correctly
        assert stats["jobs_validated"] == 4
        assert stats["jobs_valid"] == 2
        assert stats["jobs_flagged"] == 1
        assert stats["jobs_invalid"] == 1

    @patch("src.processor_v2.JobValidator")
    def test_validate_job_urls_initializes_validator_correctly(
        self, mock_validator_class, processor
    ):
        """Test _validate_job_urls creates JobValidator with correct params"""
        stats: dict[str, int | list[str]] = {
            "jobs_validated": 0,
            "jobs_valid": 0,
            "jobs_flagged": 0,
            "jobs_invalid": 0,
        }

        job = {"title": "Test", "company": "Test", "link": "https://test.com"}

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.filter_valid_jobs.return_value = ([job], [], [])
        mock_validator_class.return_value = mock_validator

        processor._validate_job_urls([job], stats)

        # Should create validator with timeout=5, check_content=True
        mock_validator_class.assert_called_once_with(timeout=5, check_content=True)
