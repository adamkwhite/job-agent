"""
Unit tests for BaseScorer shared scoring logic

Tests all shared methods extracted from JobScorer and ProfileScorer:
- _score_seniority() - Seniority level scoring (0-30 points)
- _score_domain() - Domain keyword matching (0-25 points)
- _score_location() - Location preferences (0-15 points)
- _score_technical_keywords() - Technical keywords (0-10 points)
- Utility methods (_has_keyword, _has_any_keyword, etc.)
- score_job() orchestration

BaseScorer is abstract, so tests use a concrete test subclass.
"""

import pytest

from agents.base_scorer import BaseScorer


class TestScorer(BaseScorer):
    """Concrete test subclass for BaseScorer testing"""

    def _score_role_type(self, title: str) -> int:
        """Simple implementation for testing - just check for 'engineer'"""
        if "engineer" in title.lower():
            return 20
        return 0


@pytest.fixture
def test_profile():
    """Basic profile for testing shared methods"""
    return {
        "target_seniority": ["vp", "director", "senior", "manager"],
        "domain_keywords": ["robotics", "automation", "hardware", "ai", "ml"],
        "role_types": {"engineering": ["engineering", "technical"]},
        "location_preferences": {
            "remote_keywords": ["remote", "work from home", "wfh", "anywhere"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto", "waterloo", "san francisco"],
            "preferred_regions": ["ontario", "canada", "california"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }


class TestSeniorityScoring:
    """Test seniority level scoring (0-30 points)"""

    def test_vp_level_scores_30(self, test_profile):
        """VP/C-level titles score 30 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_seniority("vp of engineering") == 30
        assert scorer._score_seniority("vice president product") == 30
        assert scorer._score_seniority("chief technology officer") == 30
        assert scorer._score_seniority("cto") == 30
        assert scorer._score_seniority("cpo") == 30
        assert scorer._score_seniority("head of engineering") == 30

    def test_director_scores_25(self, test_profile):
        """Director titles score 25 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_seniority("director of engineering") == 25
        assert scorer._score_seniority("executive director") == 25
        assert scorer._score_seniority("engineering director") == 25

    def test_senior_scores_15(self, test_profile):
        """Senior/Principal/Staff titles score 15 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_seniority("senior manager, engineering") == 15
        assert scorer._score_seniority("principal engineer") == 15
        assert scorer._score_seniority("staff engineer") == 15
        assert scorer._score_seniority("senior software engineer") == 15

    def test_manager_lead_scores_10(self, test_profile):
        """Manager/Lead titles score 10 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_seniority("engineering manager") == 10
        assert scorer._score_seniority("technical lead") == 10
        assert scorer._score_seniority("team leadership") == 10

    def test_ic_roles_score_0(self, test_profile):
        """Individual contributor roles score 0 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_seniority("software engineer") == 0
        assert scorer._score_seniority("data scientist") == 0
        assert scorer._score_seniority("product designer") == 0

    def test_word_boundary_matching(self, test_profile):
        """Test word boundaries prevent false matches"""
        scorer = TestScorer(test_profile)

        # "vp" should NOT match "supervisor"
        assert scorer._score_seniority("supervisor of engineering") == 0

        # "chief" should NOT match "mischief"
        assert scorer._score_seniority("mischief maker") == 0


class TestDomainScoring:
    """Test domain keyword matching (0-25 points)"""

    def test_three_plus_keywords_scores_25(self, test_profile):
        """3+ domain keyword matches score 25 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("robotics automation engineer", "hardware ai company")
        assert score == 25  # robotics, automation, hardware, ai = 4 matches

    def test_two_keywords_scores_20(self, test_profile):
        """2 domain keyword matches score 20 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("robotics engineer", "hardware startup")
        assert score == 20  # robotics, hardware = 2 matches

    def test_one_keyword_scores_15(self, test_profile):
        """1 domain keyword match scores 15 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("ml engineer", "tech company")
        assert score == 15  # ml = 1 match

    def test_engineering_keyword_scores_10(self, test_profile):
        """Generic engineering keyword scores 10 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("engineering manager", "saas startup")
        assert score == 10

    def test_product_keyword_scores_10(self, test_profile):
        """Generic product keyword scores 10 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("product manager", "fintech company")
        assert score == 10

    def test_no_keywords_scores_5(self, test_profile):
        """No matching keywords score 5 points (default)"""
        scorer = TestScorer(test_profile)

        score = scorer._score_domain("sales director", "consulting firm")
        assert score == 5

    def test_case_insensitive_matching(self, test_profile):
        """Domain matching works correctly when inputs are lowercased"""
        scorer = TestScorer(test_profile)

        # Method expects lowercase inputs (handled by score_job)
        score1 = scorer._score_domain("ROBOTICS ENGINEER".lower(), "HARDWARE COMPANY".lower())
        score2 = scorer._score_domain("robotics engineer", "hardware company")
        assert score1 == score2 == 20


class TestLocationScoring:
    """Test location preferences (0-15 points)"""

    def test_remote_scores_15(self, test_profile):
        """Remote locations score 15 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("remote") == 15
        assert scorer._score_location("work from home") == 15
        assert scorer._score_location("wfh") == 15
        assert scorer._score_location("anywhere (remote)") == 15

    def test_hybrid_preferred_city_scores_15(self, test_profile):
        """Hybrid + preferred city scores 15 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("hybrid - toronto, on") == 15
        assert scorer._score_location("waterloo, canada (hybrid)") == 15

    def test_hybrid_preferred_region_scores_15(self, test_profile):
        """Hybrid + preferred region scores 15 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("hybrid - ontario, canada") == 15
        assert scorer._score_location("california (hybrid)") == 15

    def test_preferred_city_scores_12(self, test_profile):
        """Preferred city scores 12 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("toronto, on") == 12
        assert scorer._score_location("waterloo, canada") == 12
        assert scorer._score_location("san francisco, ca") == 12

    def test_preferred_region_scores_8(self, test_profile):
        """Preferred region scores 8 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("ontario, canada") == 8
        assert scorer._score_location("california, usa") == 8

    def test_other_locations_score_0(self, test_profile):
        """Non-preferred locations score 0 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("new york, ny") == 0
        assert scorer._score_location("london, uk") == 0

    def test_empty_location_scores_0(self, test_profile):
        """Empty location scores 0 points"""
        scorer = TestScorer(test_profile)

        assert scorer._score_location("") == 0
        assert scorer._score_location(None) == 0

    def test_case_insensitive_location_matching(self, test_profile):
        """Location matching is case insensitive"""
        scorer = TestScorer(test_profile)

        score1 = scorer._score_location("REMOTE")
        score2 = scorer._score_location("remote")
        assert score1 == score2 == 15


class TestTechnicalKeywordsScoring:
    """Test technical keyword bonus (0-10 points)"""

    def test_multiple_keywords_max_10(self, test_profile):
        """Multiple technical keywords cap at 10 points"""
        scorer = TestScorer(test_profile)

        # Should get 10 points (max) even with 5 matches
        score = scorer._score_technical_keywords(
            "robotics automation ai ml engineer", "hardware company"
        )
        assert score == 10

    def test_five_keywords_scores_10(self, test_profile):
        """5 keyword matches score 10 points (capped)"""
        scorer = TestScorer(test_profile)

        score = scorer._score_technical_keywords("robotics automation hardware", "ai ml startup")
        assert score == 10  # 5 matches * 2 = 10, capped

    def test_two_keywords_scores_4(self, test_profile):
        """2 keyword matches score 4 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_technical_keywords("robotics engineer", "automation company")
        assert score == 4  # 2 matches * 2

    def test_one_keyword_scores_2(self, test_profile):
        """1 keyword match scores 2 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_technical_keywords("ml specialist", "tech company")
        assert score == 2

    def test_no_keywords_scores_0(self, test_profile):
        """No keyword matches score 0 points"""
        scorer = TestScorer(test_profile)

        score = scorer._score_technical_keywords("sales director", "consulting firm")
        assert score == 0


class TestUtilityMethods:
    """Test utility helper methods"""

    def test_has_keyword_word_boundaries(self, test_profile):
        """_has_keyword uses word boundaries"""
        scorer = TestScorer(test_profile)

        # Should match
        assert scorer._has_keyword("vp of engineering", "vp") is True
        assert scorer._has_keyword("chief engineer", "chief") is True

        # Should NOT match (no word boundary)
        assert scorer._has_keyword("supervisor role", "vp") is False
        assert scorer._has_keyword("mischief maker", "chief") is False

    def test_has_any_keyword(self, test_profile):
        """_has_any_keyword returns True if any keyword matches"""
        scorer = TestScorer(test_profile)

        keywords = ["vp", "director", "chief"]

        assert scorer._has_any_keyword("vp of product", keywords) is True
        assert scorer._has_any_keyword("director of engineering", keywords) is True
        assert scorer._has_any_keyword("manager role", keywords) is False

    def test_count_keyword_matches(self, test_profile):
        """_count_keyword_matches counts matching keywords"""
        scorer = TestScorer(test_profile)

        keywords = ["robotics", "automation", "hardware", "iot"]

        assert scorer._count_keyword_matches("robotics automation engineer", keywords) == 2
        assert scorer._count_keyword_matches("hardware iot startup", keywords) == 2
        assert scorer._count_keyword_matches("software engineer", keywords) == 0

    def test_is_leadership_title(self, test_profile):
        """_is_leadership_title detects leadership positions"""
        scorer = TestScorer(test_profile)

        assert scorer._is_leadership_title("vp of engineering") is True
        assert scorer._is_leadership_title("director of product") is True
        assert scorer._is_leadership_title("head of r&d") is True
        assert scorer._is_leadership_title("chief technology officer") is True
        assert scorer._is_leadership_title("executive director") is True

        assert scorer._is_leadership_title("software engineer") is False
        assert scorer._is_leadership_title("senior engineer") is False


class TestScoreJobOrchestration:
    """Test score_job() orchestration method"""

    def test_score_job_returns_four_values(self, test_profile):
        """score_job returns (score, grade, breakdown, metadata)"""
        scorer = TestScorer(test_profile)

        job = {
            "title": "Senior Software Engineer",
            "company": "Robotics Startup",
            "location": "Remote",
        }

        result = scorer.score_job(job)
        assert len(result) == 4
        score, grade, breakdown, metadata = result

        assert isinstance(score, int)
        assert isinstance(grade, str)
        assert isinstance(breakdown, dict)
        assert isinstance(metadata, dict)

    def test_score_breakdown_has_all_categories(self, test_profile):
        """Breakdown includes all scoring categories"""
        scorer = TestScorer(test_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Robotics Company",
            "location": "Remote",
        }

        _, _, breakdown, _ = scorer.score_job(job)

        assert "seniority" in breakdown
        assert "domain" in breakdown
        assert "role_type" in breakdown
        assert "location" in breakdown
        assert "technical" in breakdown
        assert "company_classification" in breakdown

    def test_total_score_is_sum_of_breakdown(self, test_profile):
        """Total score equals sum of breakdown values"""
        scorer = TestScorer(test_profile)

        job = {
            "title": "Director of Robotics Engineering",
            "company": "Hardware Automation AI Startup",
            "location": "Toronto, Canada",
        }

        score, _, breakdown, _ = scorer.score_job(job)

        expected_total = sum(breakdown.values())
        assert score == expected_total

    def test_grade_calculation(self, test_profile):
        """Grades are correctly assigned based on score"""
        scorer = TestScorer(test_profile)

        # High scoring job (should be A grade)
        job_high = {
            "title": "VP of Robotics Engineering",
            "company": "Hardware Automation AI Company",
            "location": "Remote",
        }
        _, grade_high, _, _ = scorer.score_job(job_high)
        assert grade_high in ["A", "B"]  # Should score high

        # Low scoring job (should be lower grade)
        job_low = {
            "title": "Software Engineer",
            "company": "Consulting Firm",
            "location": "New York, NY",
        }
        _, grade_low, _, _ = scorer.score_job(job_low)
        assert grade_low in ["C", "D", "F"]  # Should score low


class TestProfileAccessors:
    """Test profile accessor methods (dict and Profile object support)"""

    def test_get_target_seniority_from_dict(self, test_profile):
        """_get_target_seniority works with dict profile"""
        scorer = TestScorer(test_profile)

        seniority = scorer._get_target_seniority()
        assert seniority == ["vp", "director", "senior", "manager"]

    def test_get_domain_keywords_from_dict(self, test_profile):
        """_get_domain_keywords works with dict profile"""
        scorer = TestScorer(test_profile)

        keywords = scorer._get_domain_keywords()
        assert keywords == ["robotics", "automation", "hardware", "ai", "ml"]

    def test_get_location_preferences_from_dict(self, test_profile):
        """_get_location_preferences works with dict profile"""
        scorer = TestScorer(test_profile)

        prefs = scorer._get_location_preferences()
        assert "remote_keywords" in prefs
        assert "preferred_cities" in prefs

    def test_get_role_types_from_dict(self, test_profile):
        """_get_role_types works with dict profile"""
        scorer = TestScorer(test_profile)

        role_types = scorer._get_role_types()
        assert "engineering" in role_types

    def test_get_filtering_config_from_dict(self, test_profile):
        """_get_filtering_config works with dict profile"""
        scorer = TestScorer(test_profile)

        filtering = scorer._get_filtering_config()
        assert filtering["aggression_level"] == "moderate"


class TestAbstractMethod:
    """Test that _score_role_type must be implemented"""

    def test_abstract_method_raises_error(self, test_profile):
        """BaseScorer._score_role_type raises NotImplementedError if not overridden"""

        class IncompleteScorer(BaseScorer):
            pass  # Doesn't implement _score_role_type

        scorer = IncompleteScorer(test_profile)

        # Calling _score_role_type should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="must implement _score_role_type"):
            scorer._score_role_type("test title")
