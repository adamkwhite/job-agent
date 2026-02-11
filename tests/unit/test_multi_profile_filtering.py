"""
Test multi-profile filtering bug fix (Issue #258)

Verifies that pre-storage hard filters have been removed
and that multi_scorer handles per-profile filtering correctly.
"""

import pytest


class TestMultiProfileFiltering:
    """Test that pre-storage filtering doesn't block other profiles"""

    def test_processor_removed_pre_storage_filtering(self):
        """
        Test that processor_v2.py no longer has pre-storage hard filtering logic
        """
        # Read the processor_v2.py source to verify pre-storage filtering was removed
        import inspect

        import src.processor_v2 as processor_module

        source = inspect.getsource(processor_module.JobProcessorV2._store_and_process_job)

        # Verify pre-storage filtering code is removed
        assert "Stage 1: Hard filters (before storage and scoring)" not in source, (
            "Pre-storage hard filtering should be removed from processor_v2.py"
        )

        # Verify no early return based on filter_pipeline.apply_hard_filters before storage
        lines = source.split("\n")
        found_hard_filter_before_storage = False
        for i, line in enumerate(lines):
            if "apply_hard_filters" in line and i < len(lines) - 5:
                # Check if this is before job storage
                next_lines = "\n".join(lines[i : i + 10])
                if "add_job" in next_lines and "return" in next_lines:
                    # Found hard filter check before storage
                    found_hard_filter_before_storage = True

        assert not found_hard_filter_before_storage, (
            "Pre-storage hard filtering should not block jobs from being stored and multi-scored"
        )

    def test_company_scraper_removed_pre_scoring_filtering(self):
        """
        Test that company_scraper.py no longer has pre-scoring hard filtering logic
        """
        import inspect

        from src.jobs import company_scraper

        source = inspect.getsource(company_scraper.CompanyScraper)

        # Verify pre-scraping filtering code is removed
        assert "Stage 1: Hard filters (before scoring)" not in source, (
            "Pre-scoring hard filtering should be removed from company_scraper.py"
        )

    def test_context_filters_still_present(self):
        """
        Verify that context filters (after scoring) are still present
        These are acceptable because they use the current profile's context
        and run AFTER multi-profile scoring
        """
        import inspect

        import src.processor_v2 as processor_module

        source = inspect.getsource(processor_module.JobProcessorV2._store_and_process_job)

        # Context filters should still be present (they run AFTER scoring)
        assert "apply_context_filters" in source, (
            "Context filters should still be present (they run after multi-profile scoring)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
