"""
Unit tests for JobDescriptionEnricher (Issue #316)

Tests selective job description enrichment:
- Filtering by score threshold
- Skipping jobs with existing descriptions
- Skipping unfetchable/listing URLs
- Fetching and storing descriptions
- Description text extraction from markdown
- Stats tracking
"""

from unittest.mock import MagicMock

from enrichment.job_description_enricher import (
    MAX_DESCRIPTION_LENGTH,
    EnrichmentStats,
    JobDescriptionEnricher,
)


class TestEnrichmentFiltering:
    """Test that enrichment correctly filters jobs"""

    def test_filters_below_threshold(self):
        """Jobs below score threshold are not enriched"""
        enricher = JobDescriptionEnricher(
            firecrawl_scraper=MagicMock(),
            db=MagicMock(),
        )
        jobs = [
            {"id": 1, "link": "https://example.com/job/1", "description": "", "score": 50},
            {"id": 2, "link": "https://example.com/job/2", "description": "", "score": 65},
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.candidates == 0
        assert stats.enriched == 0

    def test_skips_existing_descriptions(self):
        """Jobs with existing descriptions are skipped"""
        enricher = JobDescriptionEnricher(
            firecrawl_scraper=MagicMock(),
            db=MagicMock(),
        )
        jobs = [
            {
                "id": 1,
                "link": "https://example.com/job/1",
                "description": "Already has a description",
                "score": 85,
            },
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.candidates == 1
        assert stats.skipped_has_description == 1
        assert stats.enriched == 0

    def test_skips_missing_urls(self):
        """Jobs without valid URLs are skipped"""
        enricher = JobDescriptionEnricher(
            firecrawl_scraper=MagicMock(),
            db=MagicMock(),
        )
        jobs = [
            {"id": 1, "link": "", "description": "", "score": 85},
            {"id": 2, "link": "not-a-url", "description": "", "score": 90},
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.skipped_no_url == 2
        assert stats.enriched == 0

    def test_skips_listing_urls(self):
        """Career listing pages (not individual job posts) are skipped"""
        enricher = JobDescriptionEnricher(
            firecrawl_scraper=MagicMock(),
            db=MagicMock(),
        )
        jobs = [
            {"id": 1, "link": "https://example.com/careers/", "description": "", "score": 85},
            {"id": 2, "link": "https://example.com/jobs/", "description": "", "score": 85},
            {
                "id": 3,
                "link": "https://boards.greenhouse.io/company",
                "description": "",
                "score": 85,
            },
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.skipped_listing_url == 3
        assert stats.enriched == 0


class TestEnrichmentFetching:
    """Test description fetching and storage"""

    def test_fetches_and_stores_description(self):
        """Successfully fetched descriptions are stored in DB"""
        mock_scraper = MagicMock()
        mock_scraper.fetch_page_markdown.return_value = (
            "# Senior Robotics Engineer\n\nBuild autonomous systems with ROS2."
        )
        mock_db = MagicMock()

        enricher = JobDescriptionEnricher(
            firecrawl_scraper=mock_scraper,
            db=mock_db,
        )
        jobs = [
            {"id": 42, "link": "https://example.com/job/42", "description": "", "score": 85},
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.enriched == 1
        mock_db.update_job_description.assert_called_once()
        call_args = mock_db.update_job_description.call_args
        assert call_args[0][0] == 42  # job_id
        assert "Robotics Engineer" in call_args[0][1]  # description text

    def test_tracks_fetch_failures(self):
        """Failed fetches are tracked"""
        mock_scraper = MagicMock()
        mock_scraper.fetch_page_markdown.return_value = None
        mock_db = MagicMock()

        enricher = JobDescriptionEnricher(
            firecrawl_scraper=mock_scraper,
            db=mock_db,
        )
        jobs = [
            {"id": 1, "link": "https://example.com/job/1", "description": "", "score": 85},
        ]

        stats = enricher.enrich_jobs(jobs, threshold=70)

        assert stats.fetch_failures == 1
        assert stats.enriched == 0
        mock_db.update_job_description.assert_not_called()

    def test_updates_job_dict_in_place(self):
        """Enriched description is written back to the job dict for rescoring"""
        mock_scraper = MagicMock()
        mock_scraper.fetch_page_markdown.return_value = "Build hardware systems."

        enricher = JobDescriptionEnricher(
            firecrawl_scraper=mock_scraper,
            db=MagicMock(),
        )
        job = {"id": 1, "link": "https://example.com/job/1", "description": "", "score": 85}

        enricher.enrich_jobs([job], threshold=70)

        assert job["description"] == "Build hardware systems."


class TestDescriptionExtraction:
    """Test markdown-to-description text extraction"""

    def test_strips_navigation_links(self):
        """Navigation-only lines are removed"""
        markdown = "[Home](/) [About](/about)\n\n# Job Title\n\nActual description here."
        result = JobDescriptionEnricher._extract_description_text(markdown)

        assert "Home" not in result
        assert "Actual description here" in result

    def test_strips_horizontal_rules(self):
        """Horizontal rule markers are removed"""
        markdown = "Description text\n---\nMore text"
        result = JobDescriptionEnricher._extract_description_text(markdown)

        assert "---" not in result
        assert "Description text" in result
        assert "More text" in result

    def test_preserves_content_lines(self):
        """Regular content lines are preserved"""
        markdown = "# Senior Engineer\n\nWe're looking for a talented engineer.\n\nRequirements:\n- Python\n- ROS2"
        result = JobDescriptionEnricher._extract_description_text(markdown)

        assert "Senior Engineer" in result
        assert "Python" in result
        assert "ROS2" in result


class TestDescriptionTruncation:
    """Test that descriptions are truncated to MAX_DESCRIPTION_LENGTH"""

    def test_long_descriptions_truncated(self):
        """Descriptions exceeding max length are truncated"""
        mock_scraper = MagicMock()
        long_text = "x" * (MAX_DESCRIPTION_LENGTH + 1000)
        mock_scraper.fetch_page_markdown.return_value = long_text
        mock_db = MagicMock()

        enricher = JobDescriptionEnricher(
            firecrawl_scraper=mock_scraper,
            db=mock_db,
        )
        job = {"id": 1, "link": "https://example.com/job/1", "description": "", "score": 85}

        enricher.enrich_jobs([job], threshold=70)

        stored_desc = mock_db.update_job_description.call_args[0][1]
        assert len(stored_desc) == MAX_DESCRIPTION_LENGTH


class TestEnrichmentStats:
    """Test EnrichmentStats dataclass"""

    def test_estimated_cost(self):
        """Cost estimate is ~$0.002 per enriched job"""
        stats = EnrichmentStats(enriched=10)
        assert stats.estimated_cost == 0.02

    def test_default_values(self):
        """Stats initialize with zeros"""
        stats = EnrichmentStats()
        assert stats.candidates == 0
        assert stats.enriched == 0
        assert stats.fetch_failures == 0


class TestUrlClassification:
    """Test URL classification for individual job posts vs listing pages"""

    def test_individual_job_urls_accepted(self):
        """Individual job post URLs pass the filter"""
        assert JobDescriptionEnricher._is_job_post_url(
            "https://example.com/job/senior-engineer-123"
        )
        assert JobDescriptionEnricher._is_job_post_url(
            "https://boards.greenhouse.io/company/jobs/12345"
        )
        assert JobDescriptionEnricher._is_job_post_url("https://lever.co/company/jobs/abc-def-ghi")

    def test_listing_page_urls_rejected(self):
        """Career listing pages are rejected"""
        assert not JobDescriptionEnricher._is_job_post_url("https://example.com/careers/")
        assert not JobDescriptionEnricher._is_job_post_url("https://example.com/jobs/")
        assert not JobDescriptionEnricher._is_job_post_url("https://boards.greenhouse.io/company")
        assert not JobDescriptionEnricher._is_job_post_url("https://jobs.lever.co/company")
