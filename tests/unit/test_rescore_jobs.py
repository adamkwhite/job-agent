"""Tests for job re-scoring utility"""

import json
from datetime import datetime, timedelta

import pytest

from database import JobDatabase
from utils.rescore_jobs import JobRescorer


@pytest.fixture
def sample_jobs():
    """Sample job data for testing"""
    return [
        {
            "title": "VP of Engineering",
            "company": "Tesla",
            "location": "Palo Alto, CA",
            "link": "https://tesla.com/job/1",
            "description": "Lead engineering for autonomy",
            "salary": "$200k-$300k",
            "job_type": "Full-time",
            "posted_date": "2024-01-15",
        },
        {
            "title": "Director of Product",
            "company": "Rivian",
            "location": "Irvine, CA",
            "link": "https://rivian.com/job/2",
            "description": "Product leadership for electric vehicles",
            "salary": "$180k-$250k",
            "job_type": "Full-time",
            "posted_date": "2024-01-20",
        },
        {
            "title": "Senior Product Manager",
            "company": "Tesla",
            "location": "Remote",
            "link": "https://tesla.com/job/3",
            "description": "Product management for Tesla software",
            "salary": "$150k-$200k",
            "job_type": "Full-time",
            "posted_date": "2024-02-01",
        },
    ]


class TestJobRescorer:
    """Test JobRescorer functionality"""

    def test_init(self, test_db_path):
        """Test rescorer initialization"""
        rescorer = JobRescorer(db_path=test_db_path)
        assert rescorer.db is not None
        assert rescorer.multi_scorer is not None

    def test_rescore_recent_jobs_dry_run(self, test_db_path, sample_jobs, mocker):
        """Test dry run mode doesn't update database"""
        db = JobDatabase(db_path=test_db_path)

        # Add sample jobs
        job_ids = []
        base_date = datetime.now() - timedelta(days=3)
        for i, job_data in enumerate(sample_jobs):
            job_data["received_at"] = (base_date + timedelta(days=i)).isoformat()
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

        # Mock multi_scorer to track calls
        rescorer = JobRescorer(db_path=test_db_path)
        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all.return_value = {"wes": (85, "B+")}
        rescorer.multi_scorer = mock_scorer

        # Dry run shouldn't call scorer
        stats = rescorer.rescore_recent_jobs(days=7, dry_run=True)

        assert stats["jobs_processed"] == 3
        assert stats["errors"] == 0
        # In dry run, we don't actually score
        assert mock_scorer.score_job_for_all.call_count == 0

    def test_rescore_by_date_range(self, test_db_path, sample_jobs, mocker):
        """Test re-scoring by date range"""
        db = JobDatabase(db_path=test_db_path)

        # Add jobs with specific dates (relative to today)
        job_ids = []
        base_date = datetime.now() - timedelta(days=10)
        for i, job_data in enumerate(sample_jobs):
            job_data["received_at"] = (base_date + timedelta(days=i * 2)).isoformat()
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

            # Add initial scores
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=70,
                grade="C",
                breakdown=json.dumps({"seniority": 20}),
            )

        # Mock scorer to return different scores
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            # Return higher score for re-scoring
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=85,
                grade="B+",
                breakdown=json.dumps({"seniority": 30}),
            )
            return {"wes": (85, "B+")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Re-score date range (first 2 jobs: days -10 and -8 from now)
        start_date = (datetime.now() - timedelta(days=11)).strftime("%Y-%m-%d")
        end_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        stats = rescorer.rescore_by_date_range(
            start_date=start_date,
            end_date=end_date,
            profiles=["wes"],
            dry_run=False,
        )

        # Should process first 2 jobs (within date range)
        assert stats["jobs_processed"] >= 1  # At least one job in range
        assert stats["profiles_scored"] == 2
        assert stats["errors"] == 0

        # Check for significant changes (70 → 85 = 15 point delta)
        assert len(stats["significant_changes"]) >= 1
        if stats["significant_changes"]:
            for change in stats["significant_changes"]:
                assert change["old_score"] == 70
                assert change["new_score"] == 85
                assert change["delta"] == 15

    def test_rescore_by_company(self, test_db_path, sample_jobs, mocker):
        """Test re-scoring by company name"""
        db = JobDatabase(db_path=test_db_path)

        # Add sample jobs
        job_ids = []
        for job_data in sample_jobs:
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

        # Mock scorer
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=90,
                grade="A-",
                breakdown=json.dumps({"seniority": 30}),
            )
            return {"wes": (90, "A-")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Re-score Tesla jobs only
        stats = rescorer.rescore_by_company(
            company_name="Tesla",
            profiles=["wes"],
            dry_run=False,
        )

        # Should process 2 Tesla jobs
        assert stats["jobs_processed"] == 2
        assert stats["profiles_scored"] == 2
        assert stats["errors"] == 0

    def test_backfill_profile(self, test_db_path, sample_jobs, mocker):
        """Test backfilling scores for new profile"""
        db = JobDatabase(db_path=test_db_path)

        # Add jobs with scores for wes only
        job_ids = []
        for job_data in sample_jobs:
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

            # Add score for wes
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=75,
                grade="C+",
                breakdown=json.dumps({"seniority": 25}),
            )

        # Mock scorer for mario profile
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            # Only score for mario (since that's what we're backfilling)
            db.upsert_job_score(
                job_id=job_id,
                profile_id="mario",
                score=80,
                grade="B",
                breakdown=json.dumps({"seniority": 28}),
            )
            return {"mario": (80, "B")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Backfill mario profile
        stats = rescorer.backfill_profile(
            profile_id="mario",
            max_jobs=100,
            dry_run=False,
        )

        # Should process all 3 jobs
        assert stats["jobs_processed"] == 3
        assert stats["profiles_scored"] == 3
        assert stats["errors"] == 0

        # Verify mario has scores now
        for job_id in job_ids:
            mario_score = db.get_job_score(job_id, "mario")
            assert mario_score is not None
            assert mario_score["fit_score"] == 80

    def test_backfill_profile_max_jobs(self, test_db_path, sample_jobs, mocker):
        """Test backfill with max_jobs limit"""
        db = JobDatabase(db_path=test_db_path)

        # Add sample jobs
        job_ids = []
        for job_data in sample_jobs:
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

        # Mock scorer
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            db.upsert_job_score(
                job_id=job_id,
                profile_id="mario",
                score=80,
                grade="B",
                breakdown=json.dumps({"seniority": 28}),
            )
            return {"mario": (80, "B")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Backfill with max_jobs=2
        stats = rescorer.backfill_profile(
            profile_id="mario",
            max_jobs=2,
            dry_run=False,
        )

        # Should only process 2 jobs
        assert stats["jobs_processed"] == 2
        assert stats["profiles_scored"] == 2

    def test_significant_changes_tracking(self, test_db_path, sample_jobs, mocker):
        """Test tracking of significant score changes"""
        db = JobDatabase(db_path=test_db_path)

        # Add jobs with existing scores
        job_ids = []
        for job_data in sample_jobs:
            job_id = db.add_job(job_data)
            job_ids.append(job_id)

            # Add initial score
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=60,
                grade="D",
                breakdown=json.dumps({"seniority": 15}),
            )

        # Mock scorer to return significant change (60 → 85 = 25 delta)
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=85,
                grade="B+",
                breakdown=json.dumps({"seniority": 30}),
            )
            return {"wes": (85, "B+")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Re-score
        stats = rescorer.rescore_recent_jobs(days=30, profiles=["wes"], dry_run=False)

        # Should track all 3 as significant changes (delta = 25)
        assert len(stats["significant_changes"]) == 3
        for change in stats["significant_changes"]:
            assert change["old_score"] == 60
            assert change["new_score"] == 85
            assert change["delta"] == 25
            assert change["profile"] == "wes"

    def test_error_handling(self, test_db_path, mocker):
        """Test error handling during re-scoring"""
        db = JobDatabase(db_path=test_db_path)

        # Add a job
        db.add_job(
            {
                "title": "Test Job",
                "company": "Test Co",
                "location": "Remote",
                "link": "https://test.com/job/1",
                "description": "Test description",
            }
        )

        # Mock scorer to raise exception
        rescorer = JobRescorer(db_path=test_db_path)
        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all.side_effect = Exception("Test error")
        rescorer.multi_scorer = mock_scorer

        # Re-score should handle error gracefully
        stats = rescorer.rescore_recent_jobs(days=30, profiles=["wes"], dry_run=False)

        assert stats["jobs_processed"] == 0  # Job wasn't successfully processed
        assert stats["errors"] == 1

    def test_no_jobs_found(self, test_db_path):
        """Test handling when no jobs match criteria"""
        rescorer = JobRescorer(db_path=test_db_path)

        # Try to re-score with no jobs in database
        stats = rescorer.rescore_by_date_range(
            start_date="2024-01-01",
            end_date="2024-01-31",
            profiles=["wes"],
            dry_run=False,
        )

        assert stats["jobs_processed"] == 0
        assert stats["errors"] == 0
        assert len(stats["significant_changes"]) == 0

    def test_small_score_changes_not_tracked(self, test_db_path, sample_jobs, mocker):
        """Test that small score changes (< 10) aren't tracked as significant"""
        db = JobDatabase(db_path=test_db_path)

        # Add job with existing score
        job_id = db.add_job(sample_jobs[0])
        db.upsert_job_score(
            job_id=job_id,
            profile_id="wes",
            score=75,
            grade="C+",
            breakdown=json.dumps({"seniority": 25}),
        )

        # Mock scorer to return small change (75 → 80 = 5 delta)
        rescorer = JobRescorer(db_path=test_db_path)

        def mock_score_job_for_all(_job_dict, job_id):
            db.upsert_job_score(
                job_id=job_id,
                profile_id="wes",
                score=80,
                grade="B",
                breakdown=json.dumps({"seniority": 27}),
            )
            return {"wes": (80, "B")}

        mock_scorer = mocker.MagicMock()
        mock_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        rescorer.multi_scorer = mock_scorer

        # Re-score
        stats = rescorer.rescore_recent_jobs(days=30, profiles=["wes"], dry_run=False)

        # Should NOT track as significant change
        assert len(stats["significant_changes"]) == 0
        assert stats["jobs_processed"] == 1
