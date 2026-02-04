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


# ========== RELATIVE SENIORITY SCORING TESTS (Issue #244) ==========


class TestDetectSeniorityLevel:
    """Test _detect_seniority_level() helper method (Sub-task 3.1)"""

    def test_detect_level_0_junior(self, test_profile):
        """Level 0: Junior/Intern/Entry-level roles"""
        scorer = TestScorer(test_profile)

        assert scorer._detect_seniority_level("junior developer") == 0
        assert scorer._detect_seniority_level("intern software engineer") == 0
        assert scorer._detect_seniority_level("entry level qa engineer") == 0
        assert scorer._detect_seniority_level("associate engineer") == 0

    def test_detect_level_2_senior(self, test_profile):
        """Level 2: Senior/Staff/Principal IC roles"""
        scorer = TestScorer(test_profile)

        assert scorer._detect_seniority_level("senior engineer") == 2
        assert scorer._detect_seniority_level("staff software engineer") == 2
        assert scorer._detect_seniority_level("principal qa engineer") == 2
        assert scorer._detect_seniority_level("senior software developer") == 2

    def test_detect_level_6_director(self, test_profile):
        """Level 6: Director level roles"""
        scorer = TestScorer(test_profile)

        assert scorer._detect_seniority_level("director of engineering") == 6
        assert scorer._detect_seniority_level("engineering director") == 6
        assert scorer._detect_seniority_level("senior manager of qa") == 6

    def test_detect_level_8_c_level(self, test_profile):
        """Level 8: C-level executive roles"""
        scorer = TestScorer(test_profile)

        assert scorer._detect_seniority_level("cto") == 8
        assert scorer._detect_seniority_level("chief technology officer") == 8
        assert scorer._detect_seniority_level("chief product officer") == 8
        assert scorer._detect_seniority_level("ceo") == 8
        assert scorer._detect_seniority_level("executive director") == 8

    def test_detect_ambiguous_senior_manager(self, test_profile):
        """Ambiguous: 'Senior Manager' should prioritize manager level"""
        scorer = TestScorer(test_profile)

        # "Senior Manager" contains both "senior" (level 2) and "manager" (level 5)
        # Should return 6 (senior manager is director-level)
        result = scorer._detect_seniority_level("senior manager")
        assert result == 6  # senior manager maps to level 6


class TestDetectHighestTargetLevel:
    """Test _detect_highest_target_level() helper method (Sub-task 3.2)"""

    def test_single_target(self, test_profile):
        """Single target keyword returns its exact match level"""
        scorer = TestScorer(test_profile)

        # Exact match in hierarchy (not substring matching)
        assert (
            scorer._detect_highest_target_level(["senior"]) == 2
        )  # Level 2: ["senior", "staff", "principal"]
        assert (
            scorer._detect_highest_target_level(["director"]) == 6
        )  # Level 6: ["director", "senior manager"]
        assert (
            scorer._detect_highest_target_level(["vp"]) == 7
        )  # Level 7: ["vp", "vice president", "head of"]
        assert scorer._detect_highest_target_level(["staff"]) == 2
        assert scorer._detect_highest_target_level(["architect"]) == 4

    def test_multiple_targets(self, test_profile):
        """Multiple targets return highest level across all exact matches"""
        scorer = TestScorer(test_profile)

        # Mario's target: senior (2), staff (2), lead (3), principal (2), architect (4)
        # Highest is architect at level 4
        mario_targets = ["senior", "staff", "lead", "principal", "architect"]
        assert scorer._detect_highest_target_level(mario_targets) == 4  # architect

        # Eli's target: director (6), vp (7), cto (8), head of (7)
        eli_targets = ["director", "vp", "cto", "head of"]
        assert scorer._detect_highest_target_level(eli_targets) == 8  # cto

    def test_empty_target(self, test_profile):
        """Empty target list returns -1"""
        scorer = TestScorer(test_profile)

        assert scorer._detect_highest_target_level([]) == -1


class TestRelativeSeniorityScoring:
    """Test relative _score_seniority() algorithm (Sub-task 3.3)"""

    @pytest.fixture
    def mario_profile(self):
        """Mario's profile (targets Senior IC roles - levels 2, 3, 4)"""
        return {
            "target_seniority": ["senior", "staff", "lead", "principal", "architect"],
            # Target levels: senior/staff/principal (2), lead (3), architect (4)
            "domain_keywords": ["qa", "testing", "quality"],
            "role_types": {"engineering": ["qa engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["montreal"],
                "preferred_regions": ["quebec"],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }

    def test_perfect_match(self, mario_profile):
        """Perfect match: Job level IN target levels → 30pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels 2, 3, 4
        # These jobs are in target levels → perfect match
        assert scorer._score_seniority("senior qa engineer") == 30  # level 2
        assert scorer._score_seniority("lead qa engineer") == 30  # level 3
        assert scorer._score_seniority("qa architect") == 30  # level 4

    def test_one_level_up(self, mario_profile):
        """One level up from target: 25pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels [2, 3, 4]
        # Manager (5) is one level above architect (4) → 25pts
        assert scorer._score_seniority("qa manager") == 25  # level 5

    def test_one_level_down(self, mario_profile):
        """One level down from target: 25pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels [2, 3, 4]
        # Mid-level (1) is one level below senior (2) → 25pts
        assert scorer._score_seniority("mid-level qa engineer") == 25  # level 1

    def test_two_levels_away(self, mario_profile):
        """Two levels away from nearest target: 15pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels [2, 3, 4]
        # Junior (0) is two levels below senior (2) → 15pts
        # Director (6) is two levels above architect (4) → 15pts
        assert scorer._score_seniority("junior qa engineer") == 15  # level 0
        assert scorer._score_seniority("director of qa") == 15  # level 6

    def test_three_levels_away(self, mario_profile):
        """Three levels away from nearest target: 10pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels [2, 3, 4]
        # VP (7) is three levels above architect (4) → 10pts
        assert scorer._score_seniority("vp of qa") == 10

    def test_major_mismatch(self, mario_profile):
        """Four+ levels away from any target: 5pts"""
        scorer = TestScorer(mario_profile)

        # Mario targets levels [2, 3, 4]
        # CTO (8) is four levels above architect (4) → 5pts
        assert scorer._score_seniority("cto") == 5  # level 8

    def test_fallback_to_absolute_no_target(self):
        """Fallback to absolute scoring when target_seniority is empty"""
        profile_no_target = {
            "target_seniority": [],  # Empty target
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile_no_target)

        # Should use absolute scoring: VP = 30pts (top tier)
        assert scorer._score_seniority("vp of engineering") == 30

    def test_ic_role_no_seniority(self, mario_profile):
        """IC role with no seniority keywords → 0pts"""
        scorer = TestScorer(mario_profile)

        # Job has no seniority keywords (level -1)
        assert scorer._score_seniority("qa engineer") == 0
        assert scorer._score_seniority("software developer") == 0

    def test_ambiguous_title_senior_manager(self, mario_profile):
        """Ambiguous title: 'Senior Manager' prioritizes higher level"""
        scorer = TestScorer(mario_profile)

        # "Senior Manager" contains both "senior" (level 2) and "manager" (level 5)
        # Detects as level 6 (senior manager)
        # Mario targets levels [2, 3, 4], job is level 6 → two levels away → 15pts
        assert scorer._score_seniority("senior manager of qa") == 15

    def test_multiple_target_levels_match_any(self):
        """Multiple target levels: Job matching ANY target level gets 30pts"""
        profile = {
            "target_seniority": ["senior", "lead"],  # levels 2, 3
            "domain_keywords": ["qa"],
            "role_types": {"engineering": ["qa"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile)

        # Both target levels should score 30pts
        assert scorer._score_seniority("senior qa engineer") == 30  # level 2 IN [2,3]
        assert scorer._score_seniority("lead qa engineer") == 30  # level 3 IN [2,3]


class TestRelativeScoringIntegration:
    """Integration tests for relative scoring across all profiles (Sub-task 3.4)"""

    def test_mario_profile_scoring(self):
        """Mario: Targets senior/staff/lead/principal/architect (levels 2, 3, 4)"""
        import json
        from pathlib import Path

        mario_path = Path(__file__).parent.parent.parent / "profiles" / "mario.json"
        with open(mario_path) as f:
            mario_data = json.load(f)

        # Use scoring section as profile dict
        mario_profile = mario_data["scoring"]
        scorer = TestScorer(mario_profile)

        # Mario's target levels: [2, 3, 4] (senior, lead, architect)
        # Perfect match: any job IN target levels → 30pts
        assert scorer._score_seniority("senior qa engineer") == 30  # level 2 IN [2,3,4]
        assert scorer._score_seniority("lead qa engineer") == 30  # level 3 IN [2,3,4]
        assert scorer._score_seniority("qa architect") == 30  # level 4 IN [2,3,4]

        # One level away: Manager (level 5) is 1 away from architect (4) → 25pts
        assert scorer._score_seniority("qa manager") == 25

    def test_adam_profile_scoring(self):
        """Adam: Targets senior/staff/lead/principal/architect (levels 2, 3, 4)"""
        import json
        from pathlib import Path

        adam_path = Path(__file__).parent.parent.parent / "profiles" / "adam.json"
        with open(adam_path) as f:
            adam_data = json.load(f)

        # Use scoring section as profile dict
        adam_profile = adam_data["scoring"]
        scorer = TestScorer(adam_profile)

        # Adam's target levels: [2, 3, 4]
        # Perfect match: any job IN target levels → 30pts
        assert scorer._score_seniority("senior software engineer") == 30  # level 2 IN [2,3,4]
        assert scorer._score_seniority("software architect") == 30  # level 4 IN [2,3,4]

        # One level away: Manager (level 5) is 1 away from architect (4) → 25pts
        assert scorer._score_seniority("engineering manager") == 25

    def test_eli_profile_scoring(self):
        """Eli: Targets director/vp/cto/head of (levels 6, 7, 8)"""
        import json
        from pathlib import Path

        eli_path = Path(__file__).parent.parent.parent / "profiles" / "eli.json"
        with open(eli_path) as f:
            eli_data = json.load(f)

        # Use scoring section as profile dict
        eli_profile = eli_data["scoring"]
        scorer = TestScorer(eli_profile)

        # Eli's target levels: [6, 7, 8] (director, vp, cto)
        # Perfect match: any job IN target levels → 30pts
        assert scorer._score_seniority("director of engineering") == 30  # level 6 IN [6,7,8]
        assert scorer._score_seniority("vp of engineering") == 30  # level 7 IN [6,7,8]
        assert scorer._score_seniority("chief technology officer") == 30  # level 8 IN [6,7,8]

    def test_wes_profile_scoring(self):
        """Wes: Targets vp/director/head of/chief/cto/cpo (levels 6, 7, 8)"""
        import json
        from pathlib import Path

        wes_path = Path(__file__).parent.parent.parent / "profiles" / "wes.json"
        with open(wes_path) as f:
            wes_data = json.load(f)

        # Use scoring section as profile dict
        wes_profile = wes_data["scoring"]
        scorer = TestScorer(wes_profile)

        # Wes's target levels: [6, 7, 8] (director, vp, cto/cpo/chief)
        # Perfect match: any job IN target levels → 30pts
        assert scorer._score_seniority("director of product") == 30  # level 6 IN [6,7,8]
        assert scorer._score_seniority("vp of product") == 30  # level 7 IN [6,7,8]
        assert scorer._score_seniority("cto") == 30  # level 8 IN [6,7,8]
        assert scorer._score_seniority("chief product officer") == 30  # level 8 IN [6,7,8]


class TestRegressionStability:
    """Regression tests for Eli/Wes score stability (Sub-task 3.5)"""

    def test_eli_scores_stable(self):
        """Eli: Sample jobs should score within ±5pts of expected baseline"""
        import json
        from pathlib import Path

        eli_path = Path(__file__).parent.parent.parent / "profiles" / "eli.json"
        with open(eli_path) as f:
            eli_data = json.load(f)

        eli_profile = eli_data["scoring"]
        scorer = TestScorer(eli_profile)

        # Eli targets: ["director", "vp", "cto", "chief technology officer", "head of"]
        # Target levels: [6, 7, 8] (director, vp, cto)
        # Sample jobs with expected seniority scores
        test_cases = [
            ("CTO", 30),  # level 8 IN [6,7,8] → 30pts
            ("Chief Technology Officer", 30),  # level 8 IN [6,7,8] → 30pts
            ("VP of Engineering", 30),  # level 7 IN [6,7,8] → 30pts
            ("Head of Engineering", 30),  # level 7 IN [6,7,8] → 30pts
            ("Director of Engineering", 30),  # level 6 IN [6,7,8] → 30pts
            ("Engineering Director", 30),  # level 6 IN [6,7,8] → 30pts
            ("Senior Manager Engineering", 30),  # level 6 IN [6,7,8] → 30pts (senior manager = 6)
            ("Engineering Manager", 25),  # level 5, nearest target 6 → 1 away → 25pts
            ("Lead Engineer", 10),  # level 3, nearest target 6 → 3 away → 10pts
            ("Senior Software Engineer", 5),  # level 2, nearest target 6 → 4 away → 5pts
        ]

        for title, expected_score in test_cases:
            actual_score = scorer._score_seniority(title.lower())
            # Allow ±5pts tolerance
            assert abs(actual_score - expected_score) <= 5, (
                f"Eli scoring regression: '{title}' expected {expected_score}pts, "
                f"got {actual_score}pts (diff: {abs(actual_score - expected_score)})"
            )

    def test_wes_scores_stable(self):
        """Wes: Sample jobs should score within ±5pts of expected baseline"""
        import json
        from pathlib import Path

        wes_path = Path(__file__).parent.parent.parent / "profiles" / "wes.json"
        with open(wes_path) as f:
            wes_data = json.load(f)

        wes_profile = wes_data["scoring"]
        scorer = TestScorer(wes_profile)

        # Wes targets: ["vp", "director", "head of", "executive", "chief", "cto", "cpo"]
        # Target levels: [6, 7, 8] (director, vp, cto/cpo/chief)
        # Sample jobs with expected seniority scores
        test_cases = [
            ("VP of Product", 30),  # level 7 IN [6,7,8] → 30pts
            ("VP of Engineering", 30),  # level 7 IN [6,7,8] → 30pts
            ("Head of Robotics", 30),  # level 7 IN [6,7,8] → 30pts
            ("CTO", 30),  # level 8 IN [6,7,8] → 30pts
            ("Chief Product Officer", 30),  # level 8 IN [6,7,8] → 30pts
            ("Director of Engineering", 30),  # level 6 IN [6,7,8] → 30pts
            ("Engineering Director", 30),  # level 6 IN [6,7,8] → 30pts
            ("Senior Manager Engineering", 30),  # level 6 IN [6,7,8] → 30pts
            ("Engineering Manager", 25),  # level 5, nearest target 6 → 1 away → 25pts
            ("Lead Engineer", 10),  # level 3, nearest target 6 → 3 away → 10pts
        ]

        for title, expected_score in test_cases:
            actual_score = scorer._score_seniority(title.lower())
            # Allow ±5pts tolerance
            assert abs(actual_score - expected_score) <= 5, (
                f"Wes scoring regression: '{title}' expected {expected_score}pts, "
                f"got {actual_score}pts (diff: {abs(actual_score - expected_score)})"
            )


class TestEdgeCases:
    """Edge case tests for relative seniority scoring (Sub-task 3.6)"""

    def test_multiple_targets_at_different_levels(self):
        """Multiple targets at different levels: Uses all target levels for matching"""
        profile = {
            "target_seniority": ["senior", "director", "vp"],  # levels 2, 6, 7
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile)

        # All target levels should get 30pts
        assert scorer._score_seniority("senior engineer") == 30  # level 2 IN [2,6,7]
        assert scorer._score_seniority("director of engineering") == 30  # level 6 IN [2,6,7]
        assert scorer._score_seniority("vp of engineering") == 30  # level 7 IN [2,6,7]

    def test_title_with_no_seniority_keywords(self):
        """Title with no seniority keywords: IC role → 0pts"""
        profile = {
            "target_seniority": ["senior", "staff"],
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile)

        # No seniority keywords (level -1) → 0pts
        assert scorer._score_seniority("software developer") == 0
        assert scorer._score_seniority("qa engineer") == 0

    def test_profile_with_no_target_seniority(self):
        """Profile with no target_seniority: Fallback to absolute scoring"""
        profile_no_target = {
            "target_seniority": [],  # Empty
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile_no_target)

        # Should use absolute scoring
        assert scorer._score_seniority("vp of engineering") == 30  # VP tier
        assert scorer._score_seniority("director of engineering") == 25  # Director tier
        assert scorer._score_seniority("senior engineer") == 15  # Senior tier

    def test_title_with_multiple_seniority_keywords(self):
        """Title with multiple seniority keywords: Uses highest level"""
        profile = {
            "target_seniority": ["senior"],
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile)

        # "Senior Lead Engineer" contains "senior" (level 2) and "lead" (level 3)
        # Should detect as level 3 (lead)
        # Target is senior (level 2), job is lead (level 3) → one level off → 25pts
        assert scorer._score_seniority("senior lead engineer") == 25

    def test_case_sensitivity(self):
        """Case sensitivity: Scoring should work with uppercase/lowercase"""
        profile = {
            "target_seniority": ["senior"],
            "domain_keywords": ["engineering"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [],
                "preferred_regions": [],
            },
            "filtering": {
                "aggression_level": "conservative",
                "hardware_company_boost": 0,
                "software_company_penalty": 0,
            },
        }
        scorer = TestScorer(profile)

        # All should score the same (method lowercases inputs)
        assert scorer._score_seniority("SENIOR ENGINEER") == 30
        assert scorer._score_seniority("senior engineer") == 30
        assert scorer._score_seniority("Senior Engineer") == 30
