"""Test multi-profile scoring for duplicate jobs"""

import contextlib
import json
import sqlite3
from datetime import datetime

import pytest

from database import JobDatabase


class TestMultiProfileDuplicateScoring:
    """Test that duplicate jobs get scored for all profiles"""

    @pytest.fixture
    def temp_db(self, test_db_path):
        """Create temporary database for testing using centralized test_db_path"""
        # Initialize database schema (creates jobs table)
        JobDatabase(profile="wes", db_path=test_db_path)

        # Create job_scores table (normally created by migration)
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                fit_score INTEGER,
                fit_grade TEXT,
                score_breakdown TEXT,
                classification_metadata TEXT,
                digest_sent_at TEXT,
                notified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                UNIQUE(job_id, profile_id)
            )
        """)

        # Add filter_reason column if it doesn't exist (from migration 003)
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE jobs ADD COLUMN filter_reason TEXT")

        # Add filtered_at column if it doesn't exist (from migration 003)
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE jobs ADD COLUMN filtered_at TEXT")

        conn.commit()
        conn.close()

        return test_db_path

    @pytest.fixture(autouse=True)
    def mock_firecrawl_scraper(self, mocker):
        """Mock FirecrawlCareerScraper to avoid needing FIRECRAWL_API_KEY in tests"""
        # Mock the FirecrawlCareerScraper initialization to avoid API key requirement
        mocker.patch("jobs.company_scraper.FirecrawlCareerScraper.__init__", return_value=None)
        # Mock the scrape_jobs method to return empty list (not used in these unit tests)
        mocker.patch("jobs.company_scraper.FirecrawlCareerScraper.scrape_jobs", return_value=[])

    def test_duplicate_job_scored_for_second_profile(self, temp_db, mocker):
        """Test that when a job is a duplicate, it still gets scored for the current profile"""
        # Setup: Create a job as Wes
        wes_db = JobDatabase(profile="wes", db_path=temp_db)

        job_dict = {
            "title": "VP of Engineering",
            "company": "TestRobotics",
            "location": "Remote",
            "link": "https://test.com/jobs/123",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        # Wes adds the job
        wes_job_id = wes_db.add_job(job_dict)
        assert wes_job_id is not None, "Job should be added for Wes"

        # Wes scores the job
        wes_db.upsert_job_score(
            job_id=wes_job_id,
            profile_id="wes",
            score=85,
            grade="B+",
            breakdown=json.dumps({"seniority": 25, "domain": 20}),
        )

        # Verify Wes has a score
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'wes'")
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should have 1 score"
        conn.close()

        # Now Mario runs and encounters the same job (duplicate)
        mario_db = JobDatabase(profile="mario", db_path=temp_db)

        # When Mario tries to add the same job, it should return None (duplicate)
        mario_job_id = mario_db.add_job(job_dict)
        assert mario_job_id is None, "Job should be detected as duplicate for Mario"

        # But Mario should still be able to score it using get_job_id_by_hash
        job_hash = mario_db.generate_job_hash(
            job_dict["title"], job_dict["company"], job_dict["link"]
        )
        existing_job_id = mario_db.get_job_id_by_hash(job_hash)
        assert existing_job_id == wes_job_id, "Should find the existing job by hash"

        # Mario scores the duplicate job
        mario_db.upsert_job_score(
            job_id=existing_job_id,
            profile_id="mario",
            score=75,
            grade="C+",
            breakdown=json.dumps({"seniority": 20, "domain": 15}),
        )

        # Verify both Wes and Mario have scores for the same job
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'wes'")
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should still have 1 score"

        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'mario'")
        mario_count = cursor.fetchone()[0]
        assert mario_count == 1, "Mario should now have 1 score"

        cursor.execute("SELECT COUNT(DISTINCT job_id) FROM job_scores")
        unique_jobs = cursor.fetchone()[0]
        assert unique_jobs == 1, "Should be 1 unique job with 2 scores"

        cursor.execute("SELECT COUNT(*) FROM job_scores")
        total_scores = cursor.fetchone()[0]
        assert total_scores == 2, "Should have 2 total scores (Wes + Mario)"

        conn.close()

    def test_get_job_id_by_hash_returns_none_for_nonexistent(self, temp_db):
        """Test that get_job_id_by_hash returns None for non-existent jobs"""
        db = JobDatabase(profile="wes", db_path=temp_db)

        # Generate hash for a job that doesn't exist
        job_hash = db.generate_job_hash(
            "Nonexistent Job", "Nonexistent Company", "https://fake.com/job"
        )

        job_id = db.get_job_id_by_hash(job_hash)
        assert job_id is None, "Should return None for non-existent job"

    def test_get_job_id_by_hash_finds_existing_job(self, temp_db):
        """Test that get_job_id_by_hash finds existing jobs by hash"""
        db = JobDatabase(profile="wes", db_path=temp_db)

        # Add a job
        job_dict = {
            "title": "Director of Product",
            "company": "RoboCorp",
            "location": "Toronto, ON",
            "link": "https://robocorp.com/careers/123",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        job_id = db.add_job(job_dict)
        assert job_id is not None, "Job should be added"

        # Find it by hash
        job_hash = db.generate_job_hash(job_dict["title"], job_dict["company"], job_dict["link"])
        found_id = db.get_job_id_by_hash(job_hash)

        assert found_id == job_id, "Should find the job by hash"

    def test_score_duplicate_for_profile_method(self, temp_db, mocker):
        """Test multi-profile scoring for duplicate jobs via multi_scorer"""
        db = JobDatabase(profile="wes", db_path=temp_db)

        # Add a job as Wes
        job_dict = {
            "title": "VP of Product",
            "company": "TestCo",
            "location": "Remote",
            "link": "https://testco.com/jobs/123",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        job_id = db.add_job(job_dict)
        assert job_id is not None

        # Mock multi-scorer to simulate scoring for all profiles
        mock_multi_scorer = mocker.MagicMock()

        # Create a side_effect function that actually writes to the database
        def mock_score_job_for_all(_job_dict, job_id):
            # Simulate scoring by writing to job_scores table for all profiles
            profiles_scores = {
                "wes": (85, "B+"),
                "mario": (75, "C+"),
                "adam": (70, "C"),
                "eli": (80, "B"),
            }
            for profile_id, (score, grade) in profiles_scores.items():
                db.upsert_job_score(
                    job_id=job_id,
                    profile_id=profile_id,
                    score=score,
                    grade=grade,
                    breakdown=json.dumps({"seniority": 20, "domain": 15}),
                )
            return profiles_scores

        mock_multi_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        mocker.patch("utils.multi_scorer.get_multi_scorer", return_value=mock_multi_scorer)

        # Score the job for all profiles using multi-scorer
        from utils.multi_scorer import get_multi_scorer

        multi_scorer = get_multi_scorer()
        profile_scores = multi_scorer.score_job_for_all(job_dict, job_id)

        # Verify all profiles have scores
        assert "wes" in profile_scores
        assert "mario" in profile_scores
        assert "adam" in profile_scores
        assert "eli" in profile_scores

        # Verify Mario has a score in database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM job_scores WHERE profile_id = 'mario' AND job_id = ?", (job_id,)
        )
        mario_count = cursor.fetchone()[0]
        assert mario_count == 1, "Mario should have 1 score for the duplicate"

        cursor.execute(
            "SELECT fit_score, fit_grade FROM job_scores WHERE profile_id = 'mario' AND job_id = ?",
            (job_id,),
        )
        score_data = cursor.fetchone()
        assert score_data is not None, "Mario should have score data"
        assert score_data[0] is not None, "Mario should have a fit_score"
        assert score_data[1] is not None, "Mario should have a fit_grade"

        conn.close()

    def test_prepare_job_dict_method(self):
        """Test the _prepare_job_dict() extracted method"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        scraper = CompanyScraper(profile="wes")

        job = OpportunityData(
            type="direct_job",
            title="Director of Engineering",
            company="RoboCorp",
            location="Toronto, ON",
            link="https://robocorp.com/jobs/456",
            source="company_monitoring",
        )

        job_dict = scraper._prepare_job_dict(job)

        assert job_dict == {
            "title": "Director of Engineering",
            "company": "RoboCorp",
            "location": "Toronto, ON",
            "link": "https://robocorp.com/jobs/456",
        }

    def test_init_job_stats_method(self):
        """Test the _init_job_stats() extracted method"""
        from jobs.company_scraper import CompanyScraper

        scraper = CompanyScraper(profile="wes")
        stats = scraper._init_job_stats()

        expected_keys = {
            "jobs_processed",
            "leadership_jobs",
            "jobs_hard_filtered",
            "jobs_context_filtered",
            "jobs_above_threshold",
            "jobs_stored",
            "notifications_sent",
            "duplicates_skipped",
        }

        assert set(stats.keys()) == expected_keys, "Stats should have all expected keys"
        assert all(v == 0 for v in stats.values()), "All stats should be initialized to 0"

    def test_handle_duplicate_job_method(self, temp_db, mocker):
        """Test the _handle_duplicate_job() extracted method"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        # Setup: Create a job as Wes
        wes_scraper = CompanyScraper(profile="wes")
        wes_scraper.database = JobDatabase(profile="wes", db_path=temp_db)

        job_dict = {
            "title": "VP of Engineering",
            "company": "TestRobotics",
            "location": "Remote",
            "link": "https://test.com/jobs/456",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        # Wes adds and scores the job
        wes_job_id = wes_scraper.database.add_job(job_dict)
        wes_scraper.database.upsert_job_score(
            job_id=wes_job_id,
            profile_id="wes",
            score=85,
            grade="B+",
            breakdown=json.dumps({"seniority": 25, "domain": 20}),
        )

        # Create Mario's scraper
        mario_scraper = CompanyScraper(profile="mario")
        mario_scraper.database = JobDatabase(profile="mario", db_path=temp_db)

        # Mock multi-scorer to simulate scoring for all profiles
        mock_multi_scorer = mocker.MagicMock()

        # Create a side_effect function that actually writes to the database
        def mock_score_job_for_all(_job_dict, job_id):
            profiles_scores = {
                "wes": (85, "B+"),
                "mario": (75, "C+"),
                "adam": (70, "C"),
                "eli": (80, "B"),
            }
            for profile_id, (score, grade) in profiles_scores.items():
                mario_scraper.database.upsert_job_score(
                    job_id=job_id,
                    profile_id=profile_id,
                    score=score,
                    grade=grade,
                    breakdown=json.dumps({"seniority": 20, "domain": 15}),
                )
            return profiles_scores

        mock_multi_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        mocker.patch("utils.multi_scorer.get_multi_scorer", return_value=mock_multi_scorer)

        # Create OpportunityData object
        job = OpportunityData(
            type="direct_job",
            title="VP of Engineering",
            company="TestRobotics",
            location="Remote",
            link="https://test.com/jobs/456",
            source="company_monitoring",
        )

        # Mario handles the duplicate
        stats = {"duplicates_skipped": 0}
        mario_scraper._handle_duplicate_job(
            job=job,
            job_dict=job_dict,
            stats=stats,
        )

        # Verify stats updated
        assert stats["duplicates_skipped"] == 1

        # Verify Mario has a score
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM job_scores WHERE profile_id = 'mario' AND job_id = ?",
            (wes_job_id,),
        )
        mario_count = cursor.fetchone()[0]
        assert mario_count == 1, "Mario should have 1 score for the duplicate"

        cursor.execute(
            "SELECT fit_score, fit_grade FROM job_scores WHERE profile_id = 'mario' AND job_id = ?",
            (wes_job_id,),
        )
        score_data = cursor.fetchone()
        assert score_data is not None, "Mario should have score data"
        assert score_data[0] is not None, "Mario should have a fit_score"
        assert score_data[1] is not None, "Mario should have a fit_grade"

        conn.close()

    def test_handle_new_job_method(self, temp_db, mocker):
        """Test the _handle_new_job() extracted method"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        scraper = CompanyScraper(profile="wes")
        scraper.database = JobDatabase(profile="wes", db_path=temp_db)

        # Mock multi-profile scorer and notifier to avoid side effects
        mock_multi_scorer = mocker.MagicMock()

        # Create a side_effect function that actually writes to the database
        def mock_score_job_for_all(_job_dict, job_id):
            profiles_scores = {
                "wes": (85, "B+"),
                "mario": (75, "C+"),
                "adam": (70, "C"),
                "eli": (80, "B"),
            }
            for profile_id, (score, grade) in profiles_scores.items():
                scraper.database.upsert_job_score(
                    job_id=job_id,
                    profile_id=profile_id,
                    score=score,
                    grade=grade,
                    breakdown=json.dumps({"seniority": 25, "domain": 20}),
                )
            return profiles_scores

        mock_multi_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        mocker.patch("utils.multi_scorer.get_multi_scorer", return_value=mock_multi_scorer)

        mock_notifier = mocker.MagicMock()
        mock_notifier.notify_job.return_value = {"email": True, "sms": False}
        scraper.notifier = mock_notifier

        # Create a job
        job_dict = {
            "title": "Director of Engineering",
            "company": "RoboCorp",
            "location": "Toronto, ON",
            "link": "https://robocorp.com/jobs/789",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        job_id = scraper.database.add_job(job_dict)

        # Create OpportunityData object
        job = OpportunityData(
            type="direct_job",
            title="Director of Engineering",
            company="RoboCorp",
            location="Toronto, ON",
            link="https://robocorp.com/jobs/789",
            source="company_monitoring",
        )

        stats = {"jobs_stored": 0, "notifications_sent": 0}

        # Handle the new job
        scraper._handle_new_job(
            job=job,
            job_dict=job_dict,
            job_id=job_id,
            score=85,
            grade="B+",
            breakdown={"seniority": 25, "domain": 20},
            extraction_method="regex",
            notify_threshold=80,
            stats=stats,
        )

        # Verify stats updated
        assert stats["jobs_stored"] == 1
        assert stats["notifications_sent"] == 1

        # Verify multi-profile scoring was called (scores go to job_scores table, not jobs table)
        mock_multi_scorer.score_job_for_all.assert_called_once()

        # Verify notification was sent (score 85 >= threshold 80)
        mock_notifier.notify_job.assert_called_once()

        # Verify score is in job_scores table (not jobs table anymore)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM job_scores WHERE job_id = ? AND profile_id = 'wes'", (job_id,)
        )
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should have a score in job_scores table"

        conn.close()

    def test_handle_hard_filtered_job_method(self, temp_db):
        """Test the _handle_hard_filtered_job() extracted method"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        scraper = CompanyScraper(profile="wes")
        scraper.database = JobDatabase(profile="wes", db_path=temp_db)

        job = OpportunityData(
            type="direct_job",
            title="Software Engineer",
            company="SoftCo",
            location="Remote",
            link="https://softco.com/jobs/123",
            source="company_monitoring",
        )

        job_dict = {
            "title": "Software Engineer",
            "company": "SoftCo",
            "location": "Remote",
            "link": "https://softco.com/jobs/123",
        }

        stats = {"jobs_hard_filtered": 0}

        scraper._handle_hard_filtered_job(
            job=job,
            job_dict=job_dict,
            filter_reason="Contains 'software engineer' keyword",
            stats=stats,
        )

        # Verify stats updated
        assert stats["jobs_hard_filtered"] == 1

        # Verify job was stored with filter reason
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE company = 'SoftCo' AND title = 'Software Engineer'"
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Filtered job should be stored"

        conn.close()

    def test_handle_context_filtered_job_method(self, temp_db, mocker):
        """Test the _handle_context_filtered_job() extracted method"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        scraper = CompanyScraper(profile="wes")
        scraper.database = JobDatabase(profile="wes", db_path=temp_db)

        # Mock multi-scorer
        mock_multi_scorer = mocker.MagicMock()

        def mock_score_job_for_all(_job_dict, job_id):
            profiles_scores = {
                "wes": (45, "D"),
                "mario": (40, "D"),
                "adam": (35, "F"),
                "eli": (50, "D"),
            }
            for profile_id, (score, grade) in profiles_scores.items():
                scraper.database.upsert_job_score(
                    job_id=job_id,
                    profile_id=profile_id,
                    score=score,
                    grade=grade,
                    breakdown=json.dumps({"seniority": 20, "domain": 10, "location": 0}),
                )
            return profiles_scores

        mock_multi_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        mocker.patch("utils.multi_scorer.get_multi_scorer", return_value=mock_multi_scorer)

        job = OpportunityData(
            type="direct_job",
            title="VP of Engineering",
            company="LowFitCo",
            location="Europe",
            link="https://lowfitco.com/jobs/123",
            source="company_monitoring",
        )

        job_dict = {
            "title": "VP of Engineering",
            "company": "LowFitCo",
            "location": "Europe",
            "link": "https://lowfitco.com/jobs/123",
        }

        stats = {"jobs_context_filtered": 0}

        scraper._handle_context_filtered_job(
            job=job,
            job_dict=job_dict,
            score=45,
            grade="D",
            breakdown={"seniority": 20, "domain": 10, "location": 0},
            filter_reason="Score too low",
            stats=stats,
        )

        # Verify stats updated
        assert stats["jobs_context_filtered"] == 1

        # Verify job was stored with filter reason
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT filter_reason FROM jobs WHERE company = 'LowFitCo'")
        filter_data = cursor.fetchone()
        assert filter_data is not None, "Filtered job should be stored"
        assert filter_data[0] == "Score too low", "Filter reason should be stored"

        # Verify score is in job_scores table (multi-profile scoring)
        cursor.execute("SELECT id FROM jobs WHERE company = 'LowFitCo'")
        job_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM job_scores WHERE job_id = ? AND profile_id = 'wes'", (job_id,)
        )
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should have a score in job_scores table"

        conn.close()

    def test_process_scraped_jobs_full_integration(self, temp_db, mocker):
        """Integration test for the full process_scraped_jobs method with duplicate handling"""
        from jobs.company_scraper import CompanyScraper
        from models import OpportunityData

        # Create Wes's scraper first (needed for mock)
        wes_scraper = CompanyScraper(profile="wes")
        wes_scraper.database = JobDatabase(profile="wes", db_path=temp_db)

        # Mock multi-profile scorer to avoid import issues - return scores for all profiles
        mock_multi_scorer = mocker.MagicMock()

        def mock_score_job_for_all(_job_dict, job_id):
            profiles_scores = {
                "wes": (75, "B"),
                "adam": (70, "C"),
                "mario": (65, "C"),
                "eli": (80, "B+"),
            }
            for profile_id, (score, grade) in profiles_scores.items():
                wes_scraper.database.upsert_job_score(
                    job_id=job_id,
                    profile_id=profile_id,
                    score=score,
                    grade=grade,
                    breakdown=json.dumps({"seniority": 25, "domain": 20}),
                )
            return profiles_scores

        mock_multi_scorer.score_job_for_all = mocker.MagicMock(side_effect=mock_score_job_for_all)
        mocker.patch("utils.multi_scorer.get_multi_scorer", return_value=mock_multi_scorer)

        # Mock notifier
        mock_notifier = mocker.MagicMock()
        mock_notifier.notify_job.return_value = {"email": True, "sms": False}
        wes_scraper.notifier = mock_notifier

        # Create test jobs - comprehensive scenarios to maximize coverage
        jobs = [
            # High-scoring leadership job - will be stored and notified
            (
                OpportunityData(
                    type="direct_job",
                    title="VP of Engineering",
                    company="RoboTech Inc",
                    location="Remote",
                    link="https://robotech.com/jobs/1",
                    source="company_monitoring",
                    received_at=datetime.now().isoformat(),
                ),
                "regex",
            ),
            # Good leadership job - will be stored
            (
                OpportunityData(
                    type="direct_job",
                    title="Director of Product",
                    company="HardwareCo",
                    location="Toronto, ON",
                    link="https://hardwareco.com/jobs/2",
                    source="company_monitoring",
                    received_at=datetime.now().isoformat(),
                ),
                "regex",
            ),
            # Non-leadership role - will be filtered early
            (
                OpportunityData(
                    type="direct_job",
                    title="Software Engineer",
                    company="SoftCo",
                    location="Remote",
                    link="https://softco.com/jobs/3",
                    source="company_monitoring",
                    received_at=datetime.now().isoformat(),
                ),
                "regex",
            ),
            # Low-scoring leadership job - will be scored but filtered by min_score threshold
            (
                OpportunityData(
                    type="direct_job",
                    title="VP Engineering",  # Leadership role
                    company="LowScoreCo",
                    location="Asia",  # Low location score
                    link="https://lowscoreco.com/jobs/4",
                    source="company_monitoring",
                    received_at=datetime.now().isoformat(),
                ),
                "regex",
            ),
        ]

        # Process jobs as Wes (min_score=50 to test filtering logic)
        stats = wes_scraper.process_scraped_jobs(
            company_name="Test Companies",
            jobs=jobs,
            min_score=50,  # Filter low-scoring jobs to test threshold logic
            notify_threshold=80,
        )

        # Verify stats - 4 jobs total, 3 leadership, some filtered
        assert stats["jobs_processed"] == 4, "Should process 4 jobs"
        assert stats["leadership_jobs"] == 3, "Should identify 3 leadership roles"
        assert stats["jobs_stored"] >= 1, "Should store high-scoring jobs"

        # Now create Mario's scraper and run the same jobs (duplicates)
        mario_scraper = CompanyScraper(profile="mario")
        mario_scraper.database = JobDatabase(profile="mario", db_path=temp_db)
        mario_scraper.notifier = mock_notifier

        # Process same jobs as Mario (min_score=50 to test duplicate handling)
        mario_stats = mario_scraper.process_scraped_jobs(
            company_name="Test Companies",
            jobs=jobs,
            min_score=50,  # Same threshold as Wes
            notify_threshold=80,
        )

        # Verify Mario's stats show duplicates
        assert mario_stats["jobs_processed"] == 4
        assert mario_stats["duplicates_skipped"] >= 1, "Should detect duplicates"

        # Verify Mario has scores for the duplicate jobs (THIS IS THE KEY FIX WE'RE TESTING)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'mario'")
        mario_scores = cursor.fetchone()[0]
        assert mario_scores >= 1, "Mario should have scores for the duplicate leadership jobs"

        # Verify the jobs exist in the jobs table
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE company IN ('RoboTech Inc', 'HardwareCo')")
        stored_jobs = cursor.fetchone()[0]
        assert stored_jobs >= 2, "Should have stored 2 leadership jobs"

        # Verify Wes's scores are in the job_scores table (new multi-profile schema)
        cursor.execute(
            """
            SELECT COUNT(*) FROM job_scores js
            JOIN jobs j ON js.job_id = j.id
            WHERE j.company IN ('RoboTech Inc', 'HardwareCo') AND js.profile_id = 'wes'
            """
        )
        wes_scored_jobs = cursor.fetchone()[0]
        assert wes_scored_jobs >= 2, "Wes should have scored 2 jobs (stored in job_scores table)"

        conn.close()
