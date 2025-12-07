"""
Unit tests for ExtractionComparator
"""

from datetime import datetime

import pytest

from src.extractors.extraction_comparator import ExtractionComparator
from src.models import OpportunityData


@pytest.fixture
def comparator():
    """Fixture for ExtractionComparator instance"""
    return ExtractionComparator()


@pytest.fixture
def sample_regex_jobs():
    """Sample regex extraction results"""
    jobs = [
        (
            OpportunityData(
                source="regex_extraction",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                location="San Francisco, CA",
                link="https://testco.com/jobs/vp-eng",
            ),
            "regex",
        ),
        (
            OpportunityData(
                source="regex_extraction",
                type="direct_job",
                company="TestCo",
                title="Director of Product",
                location=None,  # Missing location
                link="https://testco.com/jobs/dir-product",
            ),
            "regex",
        ),
        (
            OpportunityData(
                source="regex_extraction",
                type="direct_job",
                company="TestCo",
                title="Head of Robotics",
                location="Remote",
                link="https://testco.com/jobs/head-robotics",
            ),
            "regex",
        ),
    ]
    return jobs


@pytest.fixture
def sample_llm_jobs():
    """Sample LLM extraction results"""
    jobs = [
        (
            OpportunityData(
                source="llm_extraction",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",  # Same as regex
                location="San Francisco, CA",
                link="https://testco.com/jobs/vp-eng",
            ),
            "llm",
        ),
        (
            OpportunityData(
                source="llm_extraction",
                type="direct_job",
                company="TestCo",
                title="Director of Product",  # Same as regex
                location="Boston, MA",  # LLM found location!
                link="https://testco.com/jobs/dir-product",
            ),
            "llm",
        ),
        (
            OpportunityData(
                source="llm_extraction",
                type="direct_job",
                company="TestCo",
                title="Staff Software Engineer",  # LLM-only
                location="Remote",
                link="https://testco.com/jobs/staff-eng",
            ),
            "llm",
        ),
    ]
    return jobs


class TestExtractionComparatorInit:
    """Test ExtractionComparator initialization"""

    def test_init(self, comparator):
        """Test comparator initializes correctly"""
        assert comparator is not None
        assert isinstance(comparator, ExtractionComparator)


class TestCompareMethod:
    """Test the compare() method"""

    def test_compare_basic_metrics(self, comparator, sample_regex_jobs, sample_llm_jobs):
        """Test basic metrics calculation"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")

        assert metrics["company_name"] == "TestCo"
        assert "scrape_date" in metrics
        assert metrics["regex_jobs_found"] == 3
        assert metrics["llm_jobs_found"] == 3

    def test_compare_location_metrics(self, comparator, sample_regex_jobs, sample_llm_jobs):
        """Test location extraction rate calculation"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")

        # Regex: 2/3 have location (VP, Head) = 66.7%
        assert metrics["regex_with_location"] == 2
        assert metrics["regex_location_rate"] == pytest.approx(2 / 3, rel=0.01)

        # LLM: 3/3 have location (all) = 100%
        assert metrics["llm_with_location"] == 3
        assert metrics["llm_location_rate"] == pytest.approx(1.0, rel=0.01)

    def test_compare_overlap_calculation(self, comparator, sample_regex_jobs, sample_llm_jobs):
        """Test overlap calculation between methods"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")

        # Both found: VP, Director = 2 jobs
        assert metrics["overlap_count"] == 2

        # Regex only: Head of Robotics = 1 job
        assert metrics["regex_unique"] == 1

        # LLM only: Staff Engineer = 1 job
        assert metrics["llm_unique"] == 1

    def test_compare_empty_regex(self, comparator, sample_llm_jobs):
        """Test comparison when regex found no jobs"""
        metrics = comparator.compare([], sample_llm_jobs, "TestCo")

        assert metrics["regex_jobs_found"] == 0
        assert metrics["regex_location_rate"] == 0.0
        assert metrics["llm_jobs_found"] == 3
        assert metrics["overlap_count"] == 0
        assert metrics["llm_unique"] == 3

    def test_compare_empty_llm(self, comparator, sample_regex_jobs):
        """Test comparison when LLM found no jobs"""
        metrics = comparator.compare(sample_regex_jobs, [], "TestCo")

        assert metrics["regex_jobs_found"] == 3
        assert metrics["llm_jobs_found"] == 0
        assert metrics["llm_location_rate"] == 0.0
        assert metrics["overlap_count"] == 0
        assert metrics["regex_unique"] == 3

    def test_compare_both_empty(self, comparator):
        """Test comparison when both methods found no jobs"""
        metrics = comparator.compare([], [], "TestCo")

        assert metrics["regex_jobs_found"] == 0
        assert metrics["llm_jobs_found"] == 0
        assert metrics["regex_location_rate"] == 0.0
        assert metrics["llm_location_rate"] == 0.0
        assert metrics["overlap_count"] == 0

    def test_compare_includes_scrape_date(self, comparator, sample_regex_jobs):
        """Test that scrape_date is included and valid"""
        metrics = comparator.compare(sample_regex_jobs, [], "TestCo")

        assert "scrape_date" in metrics
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(metrics["scrape_date"])

    def test_compare_initializes_llm_cost(self, comparator, sample_regex_jobs):
        """Test that llm_api_cost is initialized to 0"""
        metrics = comparator.compare(sample_regex_jobs, [], "TestCo")

        assert "llm_api_cost" in metrics
        assert metrics["llm_api_cost"] == 0.0


class TestNormalizeTitle:
    """Test title normalization for matching"""

    def test_normalize_title_lowercase(self, comparator):
        """Test title is lowercased"""
        assert comparator._normalize_title("VP OF ENGINEERING") == "vp of engineering"

    def test_normalize_title_strip_whitespace(self, comparator):
        """Test whitespace is stripped"""
        assert comparator._normalize_title("  Director of Product  ") == "director of product"

    def test_normalize_title_remove_double_spaces(self, comparator):
        """Test double spaces are removed"""
        assert comparator._normalize_title("Head  of  Robotics") == "head of robotics"

    def test_normalize_title_hyphens_to_spaces(self, comparator):
        """Test hyphens converted to spaces"""
        assert comparator._normalize_title("Director-Product") == "director product"

    def test_normalize_title_remove_parentheses(self, comparator):
        """Test parentheses are removed"""
        assert (
            comparator._normalize_title("VP of Engineering (Remote)") == "vp of engineering remote"
        )

    def test_normalize_title_empty_string(self, comparator):
        """Test empty string returns empty"""
        assert comparator._normalize_title("") == ""

    def test_normalize_title_none(self, comparator):
        """Test None returns empty string"""
        assert comparator._normalize_title(None) == ""

    def test_normalize_title_complex(self, comparator):
        """Test complex title with multiple normalizations"""
        title = "  VP-of-Engineering  (Remote-US)  "
        expected = "vp of engineering remote us"
        assert comparator._normalize_title(title) == expected


class TestCalculateOverlap:
    """Test overlap calculation"""

    def test_calculate_overlap_identical_titles(self, comparator):
        """Test overlap with identical job titles"""
        jobs_a = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
        ]
        jobs_b = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
        ]

        overlap = comparator._calculate_overlap(jobs_a, jobs_b)
        assert overlap == 1

    def test_calculate_overlap_case_insensitive(self, comparator):
        """Test overlap matching is case-insensitive"""
        jobs_a = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
        ]
        jobs_b = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="vp of engineering",  # Lowercase
                link="https://test.com/1",
            ),
        ]

        overlap = comparator._calculate_overlap(jobs_a, jobs_b)
        assert overlap == 1

    def test_calculate_overlap_no_matches(self, comparator):
        """Test overlap with completely different jobs"""
        jobs_a = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
        ]
        jobs_b = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="Director of Product",
                link="https://test.com/2",
            ),
        ]

        overlap = comparator._calculate_overlap(jobs_a, jobs_b)
        assert overlap == 0

    def test_calculate_overlap_partial_matches(self, comparator):
        """Test overlap with some matching, some different"""
        jobs_a = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="Director of Product",
                link="https://test.com/2",
            ),
        ]
        jobs_b = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="Staff Engineer",
                link="https://test.com/3",
            ),
        ]

        overlap = comparator._calculate_overlap(jobs_a, jobs_b)
        assert overlap == 1

    def test_calculate_overlap_empty_lists(self, comparator):
        """Test overlap with empty job lists"""
        assert comparator._calculate_overlap([], []) == 0

    def test_calculate_overlap_one_empty(self, comparator):
        """Test overlap when one list is empty"""
        jobs = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/1",
            ),
        ]

        assert comparator._calculate_overlap(jobs, []) == 0
        assert comparator._calculate_overlap([], jobs) == 0

    def test_calculate_overlap_missing_titles(self, comparator):
        """Test overlap handles jobs with missing titles"""
        jobs_a = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title=None,  # Missing title
                link="https://test.com/1",
            ),
        ]
        jobs_b = [
            OpportunityData(
                source="test",
                type="direct_job",
                company="TestCo",
                title="VP of Engineering",
                link="https://test.com/2",
            ),
        ]

        overlap = comparator._calculate_overlap(jobs_a, jobs_b)
        assert overlap == 0


class TestPrintComparisonTable:
    """Test console output formatting"""

    def test_print_comparison_table(self, comparator, sample_regex_jobs, sample_llm_jobs, capsys):
        """Test comparison table prints correctly"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")
        comparator.print_comparison_table(metrics)

        captured = capsys.readouterr()
        output = captured.out

        # Check table structure
        assert "EXTRACTION COMPARISON: TestCo" in output
        assert "Method" in output
        assert "Jobs Found" in output
        assert "Location Rate" in output

        # Check data rows
        assert "Regex" in output
        assert "LLM" in output

        # Check metrics appear
        assert "3" in output  # Both found 3 jobs
        assert "Overlap Analysis" in output

    def test_print_comparison_table_shows_improvement(
        self, comparator, sample_regex_jobs, sample_llm_jobs, capsys
    ):
        """Test table shows LLM improvement indicator"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")
        comparator.print_comparison_table(metrics, show_location_improvement=True)

        captured = capsys.readouterr()
        output = captured.out

        # LLM has 100% vs regex 66.7%, should show improvement
        assert "✅" in output or "improved" in output.lower()

    def test_print_comparison_table_hides_improvement(
        self, comparator, sample_regex_jobs, sample_llm_jobs, capsys
    ):
        """Test table can hide improvement indicator"""
        metrics = comparator.compare(sample_regex_jobs, sample_llm_jobs, "TestCo")
        comparator.print_comparison_table(metrics, show_location_improvement=False)

        captured = capsys.readouterr()
        output = captured.out

        # Should not show improvement indicator
        assert "✅" not in output
        assert "improved" not in output.lower()

    def test_print_comparison_table_shows_cost(self, comparator, capsys):
        """Test table shows LLM API cost when available"""
        metrics = {
            "company_name": "TestCo",
            "scrape_date": datetime.now().isoformat(),
            "regex_jobs_found": 3,
            "regex_with_location": 2,
            "regex_location_rate": 0.667,
            "llm_jobs_found": 3,
            "llm_with_location": 3,
            "llm_location_rate": 1.0,
            "llm_api_cost": 0.0245,  # Cost present
            "overlap_count": 2,
            "regex_unique": 1,
            "llm_unique": 1,
        }

        comparator.print_comparison_table(metrics)

        captured = capsys.readouterr()
        output = captured.out

        assert "LLM API Cost" in output
        assert "$0.0245" in output
