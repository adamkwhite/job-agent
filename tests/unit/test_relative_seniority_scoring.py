"""
Unit tests for Relative Seniority Scoring (Issue #244)

Tests the new relative seniority scoring system that matches jobs
to candidate target_seniority preferences instead of using absolute scoring.

Test Coverage:
- _detect_seniority_level() - Detect job seniority from title (5 tests)
- _detect_all_target_levels() - Parse target seniority list (3 tests)
- _score_seniority() - Relative scoring algorithm (10 tests)
- Integration tests for all profiles (4 tests)
- Edge cases (7 tests)

Total: 29 tests
"""

import pytest

from agents.base_scorer import SENIORITY_HIERARCHY, BaseScorer


class TestScorer(BaseScorer):
    """Concrete test subclass for BaseScorer testing"""

    def _score_role_type(self, title: str) -> int:
        """Simple implementation for testing"""
        return 20 if "engineer" in title.lower() else 0


@pytest.fixture
def mario_profile():
    """Mario's profile - targets Senior/Staff/Lead roles"""
    return {
        "target_seniority": ["senior", "staff", "lead", "principal"],
        "domain_keywords": ["qa", "testing", "quality"],
        "role_types": {"qa": ["qa", "quality", "test"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["ontario", "canada"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }


@pytest.fixture
def wes_profile():
    """Wes's profile - targets Director/VP/Head roles"""
    return {
        "target_seniority": ["director", "vp", "head of", "chief"],
        "domain_keywords": ["robotics", "automation", "hardware"],
        "role_types": {"engineering": ["engineering"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["ontario"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }


@pytest.fixture
def adam_profile():
    """Adam's profile - targets Senior/Staff/Principal roles"""
    return {
        "target_seniority": ["senior", "staff", "principal", "lead", "architect"],
        "domain_keywords": ["software", "product", "engineering"],
        "role_types": {"engineering": ["engineer", "developer"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["canada"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }


@pytest.fixture
def eli_profile():
    """Eli's profile - targets Director/VP/CTO roles"""
    return {
        "target_seniority": ["director", "vp", "cto", "chief technology officer", "head of"],
        "domain_keywords": ["fintech", "healthtech", "proptech"],
        "role_types": {"engineering": ["engineering"]},
        "location_preferences": {
            "remote_keywords": ["remote"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": ["toronto"],
            "preferred_regions": ["canada"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }


class TestDetectSeniorityLevel:
    """Test _detect_seniority_level() helper"""

    def test_level_0_junior(self, mario_profile):
        """Junior roles map to level 0 (but titles with other keywords may score higher)"""
        scorer = TestScorer(mario_profile)
        # "Junior Developer" has both "junior" (0) and "developer" (1), returns highest = 1
        assert scorer._detect_seniority_level("Junior Developer") == 1
        # "Entry-level Engineer" has both "entry-level" (0) and "engineer" (1), returns 1
        assert scorer._detect_seniority_level("Entry-level Engineer") == 1
        # "Intern" alone is level 0
        assert scorer._detect_seniority_level("Intern") == 0
        assert scorer._detect_seniority_level("Junior Associate") == 0  # both level 0

    def test_level_2_senior(self, mario_profile):
        """Senior/Staff/Principal map to level 2"""
        scorer = TestScorer(mario_profile)
        assert scorer._detect_seniority_level("Senior Engineer") == 2
        assert scorer._detect_seniority_level("Staff Software Engineer") == 2
        assert scorer._detect_seniority_level("Principal QA Engineer") == 2

    def test_level_6_director(self, wes_profile):
        """Director roles map to level 6"""
        scorer = TestScorer(wes_profile)
        assert scorer._detect_seniority_level("Director of Engineering") == 6
        assert scorer._detect_seniority_level("Engineering Director") == 6
        assert scorer._detect_seniority_level("Senior Manager") == 6  # senior manager maps to 6

    def test_level_8_c_level(self, wes_profile):
        """C-level roles map to level 8"""
        scorer = TestScorer(wes_profile)
        assert scorer._detect_seniority_level("CTO") == 8
        assert scorer._detect_seniority_level("Chief Technology Officer") == 8
        assert scorer._detect_seniority_level("Chief Product Officer") == 8

    def test_ambiguous_title_takes_highest(self, wes_profile):
        """For ambiguous titles with multiple keywords, return highest level"""
        scorer = TestScorer(wes_profile)
        # "Senior Manager" has both "senior" (level 2) and "manager" (level 5)
        # But "senior manager" is explicitly in level 6, so should return 6
        assert scorer._detect_seniority_level("Senior Manager") == 6

        # "Senior Director" has "senior" (2) and "director" (6)
        # "director" wins with level 6
        assert scorer._detect_seniority_level("Senior Director") == 6

    def test_no_seniority_keywords_returns_minus_one(self, mario_profile):
        """Titles with no seniority keywords return -1"""
        scorer = TestScorer(mario_profile)
        assert scorer._detect_seniority_level("Software Engineer") == 1  # "engineer" is level 1
        assert scorer._detect_seniority_level("QA Specialist") == 1  # "specialist" is level 1
        assert scorer._detect_seniority_level("Product Designer") == -1  # no keywords


class TestDetectAllTargetLevels:
    """Test _detect_all_target_levels() helper"""

    def test_single_target_level(self, mario_profile):
        """Single target keyword maps to single level"""
        scorer = TestScorer(mario_profile)
        levels = scorer._detect_all_target_levels(["senior"])
        assert levels == [2]

    def test_multiple_targets_same_level(self, mario_profile):
        """Multiple targets at same level return unique level"""
        scorer = TestScorer(mario_profile)
        levels = scorer._detect_all_target_levels(["senior", "staff", "principal"])
        assert levels == [2]  # All map to level 2

    def test_multiple_targets_different_levels(self, mario_profile):
        """Multiple targets at different levels return sorted list"""
        scorer = TestScorer(mario_profile)
        levels = scorer._detect_all_target_levels(["senior", "lead", "director"])
        assert levels == [2, 3, 6]  # senior=2, lead=3, director=6

    def test_empty_target_returns_empty_list(self, mario_profile):
        """Empty target list returns empty list"""
        scorer = TestScorer(mario_profile)
        levels = scorer._detect_all_target_levels([])
        assert levels == []


class TestRelativeSeniorityScoring:
    """Test relative _score_seniority() with different profiles"""

    def test_perfect_match_senior_level(self, mario_profile):
        """Perfect match to Senior (level 2) scores 30pts"""
        scorer = TestScorer(mario_profile)
        assert scorer._score_seniority("Senior QA Engineer") == 30
        assert scorer._score_seniority("Staff Software Engineer") == 30
        assert scorer._score_seniority("Principal Engineer") == 30

    def test_perfect_match_director_level(self, wes_profile):
        """Perfect match to Director (level 6) scores 30pts"""
        scorer = TestScorer(wes_profile)
        assert scorer._score_seniority("Director of Engineering") == 30
        assert scorer._score_seniority("Engineering Director") == 30

    def test_perfect_match_vp_level(self, wes_profile):
        """Perfect match to VP (level 7) scores 30pts"""
        scorer = TestScorer(wes_profile)
        assert scorer._score_seniority("VP of Engineering") == 30
        assert scorer._score_seniority("Vice President of Product") == 30
        assert scorer._score_seniority("Head of Engineering") == 30

    def test_one_level_up_scores_25pts(self, mario_profile):
        """One level above target scores 25pts (stretch opportunity)"""
        scorer = TestScorer(mario_profile)
        # Mario targets levels [2, 3] (senior, staff, lead)
        # Architect is level 4, which is 1 away from lead (3)
        assert scorer._score_seniority("Solutions Architect") == 25  # level 4, 1 from lead (3)
        assert scorer._score_seniority("Distinguished Engineer") == 25  # level 4

    def test_one_level_down_scores_25pts(self, wes_profile):
        """One level below target scores 25pts"""
        scorer = TestScorer(wes_profile)
        # Wes targets level 6-8 (director, vp, chief)
        # Manager (level 5) is one below director (6)
        assert scorer._score_seniority("Engineering Manager") == 25

    def test_two_levels_away_scores_15pts(self, mario_profile):
        """Two levels away scores 15pts"""
        scorer = TestScorer(mario_profile)
        # Mario targets [2, 3] (senior, staff, lead, principal)
        # Manager (5) is 2 levels from lead (3)
        assert scorer._score_seniority("QA Manager") == 15
        assert scorer._score_seniority("Engineering Manager") == 15

    def test_three_levels_away_scores_10pts(self, mario_profile):
        """Three levels away scores 10pts"""
        scorer = TestScorer(mario_profile)
        # Mario targets [2, 3]
        # Director (6) is 3 levels from lead (3)
        assert scorer._score_seniority("Director of QA") == 10

    def test_four_plus_levels_away_scores_5pts(self, mario_profile):
        """Four+ levels away scores 5pts"""
        scorer = TestScorer(mario_profile)
        # Mario targets [2, 3]
        # VP (7) is 4 levels from lead (3)
        assert scorer._score_seniority("VP of Quality") == 5
        # CTO (8) is 5 levels from lead (3)
        assert scorer._score_seniority("CTO") == 5

    def test_no_seniority_keywords_scores_0pts(self, mario_profile):
        """Jobs with no seniority keywords score 0pts"""
        scorer = TestScorer(mario_profile)
        assert scorer._score_seniority("Product Designer") == 0
        assert scorer._score_seniority("Marketing Coordinator") == 0

    def test_fallback_to_absolute_when_no_target(self):
        """Falls back to absolute scoring when target_seniority is empty"""
        profile_no_target = {
            "target_seniority": [],  # Empty target
            "domain_keywords": ["software"],
            "role_types": {},
            "location_preferences": {},
            "filtering": {},
        }
        scorer = TestScorer(profile_no_target)

        # Should use absolute scoring (VP=30, Director=25, etc.)
        assert scorer._score_seniority("VP of Engineering") == 30
        assert scorer._score_seniority("Director of Engineering") == 25
        assert scorer._score_seniority("Senior Engineer") == 15


class TestProfileIntegration:
    """Integration tests for all profile configurations"""

    def test_mario_profile_scoring(self, mario_profile):
        """Mario's profile scores Senior/Lead roles at 30pts"""
        scorer = TestScorer(mario_profile)

        # Perfect matches (levels 2-3)
        assert scorer._score_seniority("Senior QA Engineer") == 30  # level 2
        assert scorer._score_seniority("Lead QA Engineer") == 30  # level 3
        assert scorer._score_seniority("Staff QA Engineer") == 30  # level 2

        # One level up (stretch) - level 4 is 1 from level 3
        assert scorer._score_seniority("QA Architect") == 25

        # Two levels away - level 5 is 2 from level 3
        assert scorer._score_seniority("QA Manager") == 15

        # Three levels away - level 6 is 3 from level 3
        assert scorer._score_seniority("Director of QA") == 10

    def test_adam_profile_scoring(self, adam_profile):
        """Adam's profile scores Senior/Staff/Principal roles at 30pts"""
        scorer = TestScorer(adam_profile)

        assert scorer._score_seniority("Staff Software Engineer") == 30
        assert scorer._score_seniority("Principal Engineer") == 30
        assert scorer._score_seniority("Senior Engineer") == 30

    def test_eli_profile_scoring(self, eli_profile):
        """Eli's profile scores Director/VP/CTO roles at 30pts"""
        scorer = TestScorer(eli_profile)

        assert scorer._score_seniority("Director of Engineering") == 30
        assert scorer._score_seniority("VP of Engineering") == 30
        assert scorer._score_seniority("CTO") == 30

        # One level down
        assert scorer._score_seniority("Engineering Manager") == 25

    def test_wes_profile_scoring(self, wes_profile):
        """Wes's profile scores Director/VP/Head roles at 30pts"""
        scorer = TestScorer(wes_profile)

        assert scorer._score_seniority("Director of Engineering") == 30
        assert scorer._score_seniority("VP of Product") == 30
        assert scorer._score_seniority("Head of Engineering") == 30


class TestEdgeCases:
    """Edge cases and special scenarios"""

    def test_multiple_targets_matches_any_level(self, mario_profile):
        """Job matching ANY target level scores 30pts"""
        # Mario targets: senior (2), staff (2), lead (3), principal (2)
        # Target levels: [2, 3]
        scorer = TestScorer(mario_profile)

        # All these match one of Mario's target levels
        assert scorer._score_seniority("Senior Engineer") == 30  # level 2
        assert scorer._score_seniority("Lead Engineer") == 30  # level 3
        assert scorer._score_seniority("Staff Engineer") == 30  # level 2
        assert scorer._score_seniority("Principal Engineer") == 30  # level 2

    def test_case_insensitive_matching(self, mario_profile):
        """Seniority detection is case-insensitive"""
        scorer = TestScorer(mario_profile)

        assert scorer._score_seniority("SENIOR ENGINEER") == 30
        assert scorer._score_seniority("Senior Engineer") == 30
        assert scorer._score_seniority("senior engineer") == 30

    def test_word_boundary_matching(self, mario_profile):
        """Uses word boundaries to avoid false positives"""
        scorer = TestScorer(mario_profile)

        # "supervisor" should NOT match "vp"
        # "supervisor" has no seniority keywords, should be -1 → 0pts
        assert scorer._score_seniority("Supervisor") == 0

    def test_title_with_no_keywords_but_has_engineer(self, mario_profile):
        """Engineer without seniority keyword is level 1 (IC)"""
        scorer = TestScorer(mario_profile)

        # "Software Engineer" has "engineer" (level 1)
        # Level 1 is 1 level below Senior (2), so 25pts
        assert scorer._score_seniority("Software Engineer") == 25

    def test_complex_title_with_multiple_keywords(self, wes_profile):
        """Complex titles with multiple keywords use highest level"""
        scorer = TestScorer(wes_profile)

        # "Senior Director" has senior (2) and director (6)
        # Director (6) wins, perfect match for Wes
        assert scorer._score_seniority("Senior Director of Engineering") == 30

    def test_distance_calculation_uses_minimum(self, mario_profile):
        """Distance calculation uses minimum distance to ANY target level"""
        # Mario targets levels [2, 3] (senior, staff, lead, principal)
        scorer = TestScorer(mario_profile)

        # Architect is level 4
        # Distance to level 3 (lead) = 1
        # Distance to level 2 (senior) = 2
        # Should use minimum = 1 → 25pts
        assert scorer._score_seniority("Solutions Architect") == 25

    def test_seniority_hierarchy_consistency(self):
        """Verify SENIORITY_HIERARCHY constant is properly structured"""
        # Check all levels 0-8 exist
        for level in range(9):
            assert level in SENIORITY_HIERARCHY
            assert isinstance(SENIORITY_HIERARCHY[level], list)
            assert len(SENIORITY_HIERARCHY[level]) > 0

        # Verify key keywords are in expected levels
        assert "senior" in SENIORITY_HIERARCHY[2]
        assert "director" in SENIORITY_HIERARCHY[6]
        assert "vp" in SENIORITY_HIERARCHY[7]
        assert "cto" in SENIORITY_HIERARCHY[8]


# CI cache clear
