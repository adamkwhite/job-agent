"""
Tests for JobFilter and SmartJobRanker

Tests keyword-based job filtering and ranking functionality.
"""

import tempfile
from pathlib import Path

import pytest

from src.job_filter import JobFilter, SmartJobRanker


@pytest.fixture
def config_file():
    """Create temporary config file for testing"""
    config_content = """{
  "include_keywords": ["robotics", "engineering", "director", "vp"],
  "exclude_keywords": ["intern", "junior", "entry-level"],
  "company_include": ["boston dynamics", "tesla"],
  "company_exclude": ["bad company"]
}"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(config_content)
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink()


@pytest.fixture
def job_filter(config_file):
    """Create JobFilter instance with test config"""
    return JobFilter(config_file)


class TestJobFilterInit:
    """Test JobFilter initialization"""

    def test_init_loads_keywords(self, job_filter):
        """Should load keywords from config"""
        assert "robotics" in job_filter.include_keywords
        assert "engineering" in job_filter.include_keywords
        assert "intern" in job_filter.exclude_keywords
        assert "boston dynamics" in job_filter.company_include

    def test_init_lowercases_keywords(self, job_filter):
        """Should convert all keywords to lowercase"""
        assert all(kw.islower() for kw in job_filter.include_keywords)
        assert all(kw.islower() for kw in job_filter.exclude_keywords)


class TestFilterJob:
    """Test filter_job method"""

    def test_filter_job_includes_matching(self, job_filter):
        """Should include job with matching keywords"""
        job = {
            "title": "Director of Robotics Engineering",
            "company": "Tech Corp",
            "description": "Lead robotics team",
        }
        should_include, matches, reason = job_filter.filter_job(job)

        assert should_include is True
        assert "robotics" in matches
        assert "engineering" in matches
        assert "director" in matches
        assert "Matched keywords" in reason

    def test_filter_job_excludes_with_exclude_keyword(self, job_filter):
        """Should exclude job with exclude keywords"""
        job = {
            "title": "Robotics Intern",
            "company": "Tech Corp",
            "description": "Entry-level position",
        }
        should_include, matches, reason = job_filter.filter_job(job)

        assert should_include is False
        assert "intern" in matches
        assert "Excluded due to keywords" in reason

    def test_filter_job_excludes_no_matches(self, job_filter):
        """Should exclude job with no matching keywords"""
        job = {
            "title": "Accountant",
            "company": "Finance Corp",
            "description": "Financial planning role",
        }
        should_include, matches, reason = job_filter.filter_job(job)

        assert should_include is False
        assert matches == []
        assert "No matching include keywords" in reason

    def test_filter_job_includes_company_match(self, job_filter):
        """Should include company bonus keywords in matches"""
        job = {
            "title": "Director of Engineering",
            "company": "Boston Dynamics",
            "description": "Lead team",
        }
        should_include, matches, reason = job_filter.filter_job(job)

        assert should_include is True
        assert "boston dynamics" in matches

    def test_filter_job_excludes_company_exclude(self, job_filter):
        """Should exclude jobs from excluded companies"""
        job = {
            "title": "VP of Robotics",
            "company": "Bad Company",
            "description": "Engineering role",
        }
        should_include, matches, reason = job_filter.filter_job(job)

        assert should_include is False
        assert "bad company" in matches
        assert "Excluded due to company keywords" in reason


class TestFilterJobs:
    """Test filter_jobs method"""

    def test_filter_jobs_splits_included_excluded(self, job_filter):
        """Should split jobs into included and excluded lists"""
        jobs = [
            {"title": "Director of Robotics", "company": "A"},
            {"title": "Robotics Intern", "company": "B"},
            {"title": "Accountant", "company": "C"},
        ]
        included, excluded = job_filter.filter_jobs(jobs)

        assert len(included) == 1
        assert len(excluded) == 2
        assert included[0]["title"] == "Director of Robotics"

    def test_filter_jobs_adds_metadata(self, job_filter):
        """Should add filter metadata to all jobs"""
        jobs = [{"title": "Director of Robotics", "company": "Tech"}]
        included, excluded = job_filter.filter_jobs(jobs)

        job = included[0]
        assert "filter_result" in job
        assert job["filter_result"]["included"] is True
        assert "keywords_matched" in job["filter_result"]
        assert "reason" in job["filter_result"]

    def test_filter_jobs_adds_keywords_to_included(self, job_filter):
        """Should add keywords_matched to included jobs"""
        jobs = [{"title": "Director of Robotics Engineering", "company": "Tech"}]
        included, _ = job_filter.filter_jobs(jobs)

        assert "keywords_matched" in included[0]
        assert "robotics" in included[0]["keywords_matched"]

    def test_filter_jobs_empty_list(self, job_filter):
        """Should handle empty job list"""
        included, excluded = job_filter.filter_jobs([])

        assert included == []
        assert excluded == []


class TestGetSearchableText:
    """Test _get_searchable_text method"""

    def test_combines_all_fields(self, job_filter):
        """Should combine all searchable fields"""
        job = {
            "title": "Engineer",
            "company": "TechCo",
            "description": "Build robots",
            "location": "Remote",
            "job_type": "Full-time",
        }
        text = job_filter._get_searchable_text(job)

        assert "engineer" in text
        assert "techco" in text
        assert "robots" in text
        assert "remote" in text
        assert "full-time" in text

    def test_handles_missing_fields(self, job_filter):
        """Should handle missing fields gracefully"""
        job = {"title": "Engineer"}
        text = job_filter._get_searchable_text(job)

        assert "engineer" in text
        assert text.count(" ") >= 4  # Includes empty strings joined


class TestFindMatches:
    """Test _find_matches method"""

    def test_finds_exact_matches(self, job_filter):
        """Should find exact keyword matches"""
        text = "robotics engineering position"
        keywords = ["robotics", "engineering"]
        matches = job_filter._find_matches(text, keywords)

        assert len(matches) == 2
        assert "robotics" in matches
        assert "engineering" in matches

    def test_case_insensitive(self, job_filter):
        """Should match case-insensitively"""
        text = "ROBOTICS Engineering"
        keywords = ["robotics", "engineering"]
        matches = job_filter._find_matches(text, keywords)

        assert len(matches) == 2

    def test_word_boundary_matching(self, job_filter):
        """Should use word boundaries to prevent partial matches"""
        text = "development position"
        keywords = ["pm"]  # Should not match "develo-pm-ent"
        matches = job_filter._find_matches(text, keywords)

        assert len(matches) == 0

    def test_no_matches(self, job_filter):
        """Should return empty list when no matches"""
        text = "accountant position"
        keywords = ["robotics", "engineering"]
        matches = job_filter._find_matches(text, keywords)

        assert matches == []


class TestGetStats:
    """Test get_stats method"""

    def test_returns_keyword_counts(self, job_filter):
        """Should return counts of all keyword lists"""
        stats = job_filter.get_stats()

        assert stats["include_keywords_count"] == 4
        assert stats["exclude_keywords_count"] == 3
        assert stats["company_include_count"] == 2
        assert stats["company_exclude_count"] == 1

    def test_includes_keyword_lists(self, job_filter):
        """Should include actual keyword lists"""
        stats = job_filter.get_stats()

        assert "robotics" in stats["include_keywords"]
        assert "intern" in stats["exclude_keywords"]


class TestSmartJobRanker:
    """Test SmartJobRanker class"""

    def test_init_creates_filter(self, config_file):
        """Should initialize with JobFilter"""
        ranker = SmartJobRanker(config_file)
        assert ranker.filter is not None
        assert isinstance(ranker.filter, JobFilter)

    def test_rank_jobs_adds_scores(self, config_file):
        """Should add relevance_score to all jobs"""
        ranker = SmartJobRanker(config_file)
        jobs = [
            {
                "title": "Director",
                "company": "Tech",
                "keywords_matched": ["director"],
            }
        ]
        ranked = ranker.rank_jobs(jobs)

        assert "relevance_score" in ranked[0]
        assert ranked[0]["relevance_score"] > 0

    def test_rank_jobs_scores_keyword_matches(self, config_file):
        """Should score based on keyword matches (10 pts each)"""
        ranker = SmartJobRanker(config_file)
        jobs = [{"title": "Job", "keywords_matched": ["a", "b", "c"]}]
        ranked = ranker.rank_jobs(jobs)

        # 3 keywords * 10 = 30 points
        assert ranked[0]["relevance_score"] >= 30

    def test_rank_jobs_scores_company_matches(self, config_file):
        """Should score company matches (20 pts each)"""
        ranker = SmartJobRanker(config_file)
        jobs = [
            {
                "title": "Engineer",
                "company": "Boston Dynamics",
                "keywords_matched": [],
            }
        ]
        ranked = ranker.rank_jobs(jobs)

        # Company match: 20 points
        assert ranked[0]["relevance_score"] >= 20

    def test_rank_jobs_scores_full_time(self, config_file):
        """Should give bonus for full-time (+15 pts)"""
        ranker = SmartJobRanker(config_file)
        jobs = [{"title": "Job", "job_type": "Full-time", "keywords_matched": []}]
        ranked = ranker.rank_jobs(jobs)

        assert ranked[0]["relevance_score"] >= 15

    def test_rank_jobs_scores_contract(self, config_file):
        """Should give bonus for contract (+10 pts)"""
        ranker = SmartJobRanker(config_file)
        jobs = [{"title": "Job", "job_type": "Contract", "keywords_matched": []}]
        ranked = ranker.rank_jobs(jobs)

        assert ranked[0]["relevance_score"] >= 10

    def test_rank_jobs_scores_remote(self, config_file):
        """Should give bonus for remote (+10 pts)"""
        ranker = SmartJobRanker(config_file)
        jobs = [{"title": "Job", "location": "Remote", "keywords_matched": []}]
        ranked = ranker.rank_jobs(jobs)

        assert ranked[0]["relevance_score"] >= 10

    def test_rank_jobs_sorts_by_score(self, config_file):
        """Should sort jobs by relevance_score (highest first)"""
        ranker = SmartJobRanker(config_file)
        jobs = [
            {"title": "Job1", "keywords_matched": ["a"]},
            {"title": "Job2", "keywords_matched": ["a", "b", "c"]},
            {"title": "Job3", "keywords_matched": ["a", "b"]},
        ]
        ranked = ranker.rank_jobs(jobs)

        # Should be sorted: Job2 (30), Job3 (20), Job1 (10)
        assert ranked[0]["title"] == "Job2"
        assert ranked[1]["title"] == "Job3"
        assert ranked[2]["title"] == "Job1"

    def test_rank_jobs_handles_missing_fields(self, config_file):
        """Should handle jobs with missing fields"""
        ranker = SmartJobRanker(config_file)
        jobs = [{"title": "Job"}]  # No keywords_matched, company, etc.
        ranked = ranker.rank_jobs(jobs)

        assert "relevance_score" in ranked[0]
        assert ranked[0]["relevance_score"] >= 0


class TestIsLeadershipRole:
    """Test is_leadership_role method"""

    def test_identifies_director_roles(self, job_filter):
        """Should identify Director roles as leadership"""
        assert job_filter.is_leadership_role("Director of Engineering")
        assert job_filter.is_leadership_role("Engineering Director")
        assert job_filter.is_leadership_role("director, product management")

    def test_identifies_vp_roles(self, job_filter):
        """Should identify VP roles as leadership"""
        assert job_filter.is_leadership_role("VP of Engineering")
        assert job_filter.is_leadership_role("Vice President, Product")
        assert job_filter.is_leadership_role("vp engineering")

    def test_identifies_head_of_roles(self, job_filter):
        """Should identify Head of roles as leadership"""
        assert job_filter.is_leadership_role("Head of Engineering")
        assert job_filter.is_leadership_role("head of product")

    def test_identifies_chief_roles(self, job_filter):
        """Should identify Chief roles as leadership"""
        assert job_filter.is_leadership_role("Chief Technology Officer")
        assert job_filter.is_leadership_role("Chief Engineer")

    def test_identifies_manager_roles(self, job_filter):
        """Should identify Manager roles as leadership"""
        assert job_filter.is_leadership_role("Engineering Manager")
        assert job_filter.is_leadership_role("Senior Manager, Product")
        assert job_filter.is_leadership_role("manager of operations")

    def test_identifies_lead_roles(self, job_filter):
        """Should identify Lead roles as leadership"""
        assert job_filter.is_leadership_role("Tech Lead")
        assert job_filter.is_leadership_role("Engineering Lead")

    def test_identifies_principal_roles(self, job_filter):
        """Should identify Principal roles as leadership"""
        assert job_filter.is_leadership_role("Principal Engineer")
        assert job_filter.is_leadership_role("principal software engineer")

    def test_rejects_ic_roles(self, job_filter):
        """Should not identify IC roles as leadership"""
        assert not job_filter.is_leadership_role("Software Engineer")
        assert not job_filter.is_leadership_role("Senior Software Engineer")
        assert not job_filter.is_leadership_role("Product Designer")

    def test_case_insensitive(self, job_filter):
        """Should be case insensitive"""
        assert job_filter.is_leadership_role("DIRECTOR OF ENGINEERING")
        assert job_filter.is_leadership_role("Director Of Engineering")

    def test_handles_none_and_empty_title(self, job_filter):
        """Should handle None and empty titles gracefully"""
        assert not job_filter.is_leadership_role(None)
        assert not job_filter.is_leadership_role("")
        assert not job_filter.is_leadership_role("   ")
