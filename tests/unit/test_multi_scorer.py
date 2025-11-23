"""
Tests for MultiPersonScorer - multi-profile job scoring
"""

import pytest

from src.utils.multi_scorer import MultiPersonScorer, get_multi_scorer, score_job_all_profiles


@pytest.fixture
def mock_dependencies(mocker):
    """Mock all MultiPersonScorer dependencies"""
    # Mock profile manager
    mock_manager = mocker.Mock()
    mock_profile_wes = mocker.Mock()
    mock_profile_wes.id = "wes"
    mock_profile_wes.scoring = {
        "target_seniority": ["vp", "director"],
        "domain_keywords": ["robotics", "hardware"],
        "role_types": {"engineering": ["engineering"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["ontario"],
        },
    }
    mock_profile_wes.get_target_seniority.return_value = ["vp", "director"]
    mock_profile_wes.get_domain_keywords.return_value = ["robotics", "hardware"]
    mock_profile_wes.get_avoid_keywords.return_value = ["junior"]
    mock_profile_wes.get_location_preferences.return_value = {
        "remote_keywords": ["remote"],
        "hybrid_keywords": ["hybrid"],
        "preferred_cities": ["toronto"],
        "preferred_regions": ["ontario"],
    }

    mock_profile_adam = mocker.Mock()
    mock_profile_adam.id = "adam"
    mock_profile_adam.scoring = {
        "target_seniority": ["senior", "lead"],
        "domain_keywords": ["software", "python"],
        "role_types": {"engineering": ["software"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["ontario"],
        },
    }
    mock_profile_adam.get_target_seniority.return_value = ["senior", "lead"]
    mock_profile_adam.get_domain_keywords.return_value = ["software", "python"]
    mock_profile_adam.get_avoid_keywords.return_value = ["junior"]
    mock_profile_adam.get_location_preferences.return_value = {
        "remote_keywords": ["remote"],
        "hybrid_keywords": ["hybrid"],
        "preferred_cities": ["toronto"],
        "preferred_regions": ["ontario"],
    }

    mock_manager.get_enabled_profiles.return_value = [mock_profile_wes, mock_profile_adam]

    mocker.patch("src.utils.multi_scorer.get_profile_manager", return_value=mock_manager)

    # Mock database
    mock_db = mocker.Mock()
    mock_db.upsert_job_score.return_value = None
    mock_db.get_job_score.return_value = None
    mocker.patch("src.utils.multi_scorer.JobDatabase", return_value=mock_db)

    # Reset singleton
    import src.utils.multi_scorer

    src.utils.multi_scorer._multi_scorer = None

    return {"manager": mock_manager, "db": mock_db}


class TestMultiPersonScorer:
    """Test MultiPersonScorer class"""

    def test_init_creates_scorers_for_enabled_profiles(self, mock_dependencies):  # noqa: ARG002
        """Test that scorers are created for each enabled profile"""
        scorer = MultiPersonScorer()

        assert "wes" in scorer.scorers
        assert "adam" in scorer.scorers
        assert len(scorer.scorers) == 2

    def test_score_job_for_all_returns_results(self, mock_dependencies):  # noqa: ARG002
        """Test scoring a job for all profiles"""
        scorer = MultiPersonScorer()

        job = {"title": "VP of Engineering", "company": "Robotics Co", "location": "Remote"}

        results = scorer.score_job_for_all(job, job_id=123)

        assert "wes" in results
        assert "adam" in results
        # Each result should be (score, grade)
        for _profile_id, result in results.items():
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], int)  # score
            assert result[1] in ["A", "B", "C", "D", "F"]  # grade

    def test_score_job_for_all_saves_to_database(self, mock_dependencies):
        """Test that scores are saved to database"""
        scorer = MultiPersonScorer()

        job = {"title": "Director of Hardware", "company": "IoT Corp", "location": "Toronto"}

        scorer.score_job_for_all(job, job_id=456)

        # Should have called upsert_job_score for each profile
        assert mock_dependencies["db"].upsert_job_score.call_count == 2

    def test_score_new_job_calls_score_job_for_all(self, mock_dependencies):  # noqa: ARG002
        """Test score_new_job delegates to score_job_for_all"""
        scorer = MultiPersonScorer()

        job = {"title": "Senior Engineer", "company": "Tech Co", "location": "Remote"}

        results = scorer.score_new_job(job, job_id=789)

        assert "wes" in results
        assert "adam" in results

    def test_get_best_match_profile_returns_highest_scorer(self, mock_dependencies):
        """Test finding best matching profile for a job"""
        # Setup mock to return scores
        mock_dependencies["db"].get_job_score.side_effect = [
            {"fit_score": 75, "fit_grade": "C"},  # wes
            {"fit_score": 85, "fit_grade": "B"},  # adam
        ]

        scorer = MultiPersonScorer()
        best = scorer.get_best_match_profile(job_id=123)

        assert best is not None
        assert best[0] == "adam"  # adam has higher score
        assert best[1] == 85
        assert best[2] == "B"

    def test_get_best_match_profile_returns_none_when_no_scores(self, mock_dependencies):
        """Test get_best_match_profile returns None when no scores exist"""
        mock_dependencies["db"].get_job_score.return_value = None

        scorer = MultiPersonScorer()
        best = scorer.get_best_match_profile(job_id=999)

        assert best is None


class TestMultiScorerSingleton:
    """Test singleton pattern and convenience functions"""

    def test_get_multi_scorer_returns_singleton(self, mock_dependencies):  # noqa: ARG002
        """Test that get_multi_scorer returns the same instance"""
        scorer1 = get_multi_scorer()
        scorer2 = get_multi_scorer()

        assert scorer1 is scorer2

    def test_score_job_all_profiles_convenience_function(self, mock_dependencies):  # noqa: ARG002
        """Test convenience function works"""
        job = {"title": "Lead Developer", "company": "Startup", "location": "Toronto"}

        results = score_job_all_profiles(job, job_id=100)

        assert "wes" in results
        assert "adam" in results
