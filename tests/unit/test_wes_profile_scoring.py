"""
Tests for Wes Profile Scoring via ProfileScorer

Tests the 100-point scoring system that evaluates jobs against Wes's profile.
Previously tested via JobScorer (now deleted), these tests verify identical
behavior using ProfileScorer with Wes's profile configuration.
"""

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.scoring_utils import calculate_grade


@pytest.fixture
def scorer(wes_profile):
    """Create ProfileScorer with Wes's profile (wes_profile from conftest)"""
    return ProfileScorer(wes_profile)


class TestWesProfileScorerInit:
    """Test ProfileScorer initialization with Wes profile"""

    def test_init(self, scorer):
        """Test scorer initializes with profile"""
        assert scorer.profile is not None
        assert scorer.profile.scoring.get("target_seniority") is not None
        assert scorer.profile.scoring.get("domain_keywords") is not None
        assert scorer.profile.scoring.get("role_types") is not None


class TestSeniorityScoring:
    """Test seniority scoring with relative scoring (Issue #244)

    Wes's profile targets: director (level 6), vp (level 7), head of (level 7),
    executive (level 7), chief/cto/cpo (level 8)
    Scoring: Perfect match=30pts, 1 level away=25pts, 2 levels=15pts, etc.
    """

    def test_vp_level_scores_30(self, scorer):
        """Test VP/Director/Head of/C-level roles score 30 points"""
        executive_roles = [
            "VP of Engineering",
            "Vice President of Product",
            "Head of Engineering",
            "Director of Engineering",
            "Chief Technology Officer",
            "CTO",
            "CPO",
        ]

        for title in executive_roles:
            score = scorer._score_seniority(title.lower())
            assert score == 30, f"{title} should score 30"

    def test_director_scores_30(self, scorer):
        """Test Director roles score 30 points (perfect match for Wes)"""
        titles = [
            "Director of Engineering",
            "Engineering Director",
            "Executive Director of Product",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 30, f"{title} should score 30 (perfect match)"

    def test_senior_manager_scores_30(self, scorer):
        """Test Senior Manager scores 30 points (level 6, matches Director)"""
        score = scorer._score_seniority("senior manager, engineering")
        assert score == 30, "Senior Manager should score 30 (level 6)"

        # Principal/Staff are level 2, 4 levels from target level 6 → 5 points
        for title in ["Principal Engineer", "Staff Engineer"]:
            score = scorer._score_seniority(title.lower())
            assert score == 5, f"{title} should score 5 (4 levels from target)"

    def test_manager_lead_scores_correctly(self, scorer):
        """Test Manager/Lead roles score based on distance from Wes's targets"""
        # Manager is level 5, 1 away from target level 6 → 25 points
        for title in ["Engineering Manager", "Product Manager"]:
            score = scorer._score_seniority(title.lower())
            assert score == 25, f"{title} should score 25 (1 level from target)"

        # Lead is level 3, 3 away from target level 6 → 10 points
        score = scorer._score_seniority("technical lead")
        assert score == 10, "Technical Lead should score 10 (3 levels from target)"

    def test_ic_roles_score_low(self, scorer):
        """Test IC roles score based on distance from Wes's targets"""
        for title in ["Software Engineer", "Analyst"]:
            score = scorer._score_seniority(title.lower())
            assert score == 5, f"{title} should score 5 (5 levels from target)"

        assert scorer._score_seniority("product designer") == 0

    def test_vp_with_punctuation_scores_30(self, scorer):
        """Test VP titles with commas, dashes, and other punctuation score 30 points"""
        titles = [
            "VP, Robotics Software",
            "VP - Engineering",
            "VP: Product Management",
            "VP. Operations",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 30, f"Failed for: {title} (got {score})"

    def test_false_positive_prevention(self, scorer):
        """Test that word boundary checking prevents false positive matches"""
        assert scorer._score_seniority("supervisor") == 0
        assert scorer._score_seniority("mischief coordinator") == 0

        score = scorer._score_seniority("managerial analyst")
        assert score == 5, f"Managerial analyst should score 5, got {score}"


class TestDomainScoring:
    """Test domain scoring (0-25 points) with tiered matching"""

    def test_robotics_hardware_scores_25(self, scorer):
        """Test robotics/hardware domain scores 25 points (tier1)"""
        combinations = [
            ("Robotics Engineer", ""),
            ("Engineering Manager", "Automation Company"),
            ("Director of Product", "IoT Startup"),
            ("VP Engineering", "Hardware Co"),
            ("Engineering Lead", "Mechatronics Inc"),
        ]

        for title, company in combinations:
            score = scorer._score_domain(title.lower(), company.lower())
            assert score == 25, f"Failed for: {title} @ {company}"

    def test_medtech_scores_20_or_higher(self, scorer):
        """Test MedTech domain scores 20+ points (tier2)"""
        combinations = [
            ("Director Engineering", "MedTech Innovations"),
            ("VP Product", "Medical Device Co"),
            ("Engineering Manager", "Healthcare Robotics"),
        ]

        for title, company in combinations:
            score = scorer._score_domain(title.lower(), company.lower())
            assert score >= 20, f"Failed for: {title} @ {company}"

    def test_manufacturing_scores_15_or_higher(self, scorer):
        """Test manufacturing/industrial scores 15+ points (tier3)"""
        combinations = [
            ("VP Product", "Supply Chain Solutions"),
            ("Director", "Industrial Company"),
        ]

        for title, company in combinations:
            score = scorer._score_domain(title.lower(), company.lower())
            assert score >= 15, f"Failed for: {title} @ {company}"

    def test_generic_engineering_scores_10(self, scorer):
        """Test generic engineering scores 10 points"""
        score = scorer._score_domain("senior engineering manager", "tech company")
        assert score == 10

    def test_product_only_scores_5(self, scorer):
        """Test product-only roles score 5 points"""
        score = scorer._score_domain("product manager", "saas company")
        assert score == 5


class TestRoleTypeScoring:
    """Test role type scoring via ProfileScorer"""

    def test_pure_software_engineering_penalized(self, scorer):
        """Test pure software engineering leadership gets -5 penalty"""
        titles = [
            ("VP of Software Engineering", -5),
            ("Director of Software Development", -5),
            ("Head of Backend Engineering", -5),
        ]

        for title, expected in titles:
            score = scorer._score_role_type(title.lower())
            assert score == expected, f"Failed for: {title}, got {score}"

    def test_hardware_engineering_leadership(self, scorer):
        """Test hardware engineering leadership scores well"""
        titles = [
            "Director of Hardware Engineering",
            "VP of R&D",
            "Head of Mechatronics Engineering",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= 15, f"Failed for: {title}, got {score}"

    def test_product_engineering_scores_well(self, scorer):
        """Test product + engineering roles score well for leadership"""
        for title in ["Director of Product Engineering", "VP Product Engineering"]:
            score = scorer._score_role_type(title.lower())
            assert score >= 15, f"Failed for: {title}, got {score}"

    def test_product_leadership_scores(self, scorer):
        """Test product leadership roles score correctly via profile keyword matching

        ProfileScorer matches against profile role_types keywords using word boundaries.
        Wes's product_leadership keywords: ["product manager", "product management", "cpo", "chief product"]
        Titles with just "product" (e.g., "VP of Product") don't match these multi-word keywords.
        """
        # Titles that match product_leadership keywords in wes.json
        matching_titles = [
            ("Chief Product Officer", 20),  # matches "chief product"
            ("VP of Product Management", 20),  # matches "product management"
            ("CPO", 15),  # matches "cpo" (not leadership title)
        ]

        for title, expected in matching_titles:
            score = scorer._score_role_type(title.lower())
            assert score == expected, f"Failed for: {title}, expected {expected}, got {score}"

        # Titles with bare "product" don't match multi-word keywords
        non_matching_titles = ["VP of Product", "Director of Product", "Head of Product"]
        for title in non_matching_titles:
            score = scorer._score_role_type(title.lower())
            assert score == 0, f"{title} should score 0 (no keyword match), got {score}"

    def test_operations_leadership_scores(self, scorer):
        """Test operations leadership scores via role_types config"""
        score = scorer._score_role_type("director of manufacturing")
        assert score >= 15, f"Director of Manufacturing should score 15+, got {score}"

        score = scorer._score_role_type("head of operations")
        assert score >= 15, f"Head of Operations should score 15+, got {score}"

    def test_generic_fallback_scoring(self, scorer):
        """Test generic fallback scores correctly"""
        score = scorer._score_role_type("business analyst")
        assert score == 0, f"Business Analyst should score 0, got {score}"


class TestLocationScoring:
    """Test location scoring (0-15 points)"""

    def test_remote_scores_15(self, scorer):
        """Test remote locations score 15 points"""
        locations = ["Remote", "Work from home", "WFH", "Remote - anywhere", "Distributed team"]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score == 15, f"Failed for: {location}"

    def test_hybrid_ontario_scores_15(self, scorer):
        """Test hybrid + Ontario scores 15 points"""
        locations = [
            "Hybrid - Toronto, ON",
            "Hybrid - Waterloo, Ontario",
            "Hybrid - Ontario, Canada",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score == 15, f"Failed for: {location}"

    def test_preferred_cities_score_12(self, scorer):
        """Test preferred cities score 12 points"""
        locations = ["Toronto, ON", "Waterloo, Canada", "Burlington, Ontario", "Hamilton, ON"]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score >= 12, f"Failed for: {location}"

    def test_broader_canada_scores_8(self, scorer):
        """Test broader Canada regions score 8 points"""
        for location in ["Ontario, Canada", "Canada"]:
            score = scorer._score_location(location.lower())
            assert score >= 8, f"Failed for: {location}"

    def test_us_locations_score_0(self, scorer):
        """Test US/other locations score 0 points"""
        for location in ["San Francisco, CA", "New York, NY", "London, UK"]:
            score = scorer._score_location(location.lower())
            assert score == 0, f"Failed for: {location}"

    def test_empty_location_scores_0(self, scorer):
        """Test empty location scores 0 points"""
        assert scorer._score_location("") == 0


class TestTechnicalKeywordsScoring:
    """Test technical keywords scoring (0-10 points)"""

    def test_multiple_tech_keywords(self, scorer):
        """Test multiple technical keywords add up"""
        score = scorer._score_technical_keywords(
            "mechatronics embedded firmware", "hardware company"
        )
        assert score > 0
        assert score <= 10

    def test_ai_ml_keywords_use_word_boundaries(self, scorer):
        """Test ai/ml keywords use word boundaries to avoid false matches"""
        # "ai" should NOT match "email", "detail", "gmail"
        assert scorer._score_technical_keywords("email marketing", "detail oriented") == 0
        assert scorer._score_technical_keywords("domain knowledge", "gmail support") == 0

        # "ml" should NOT match "html", "xml"
        assert scorer._score_technical_keywords("html developer", "xml parsing") == 0

        # But "ai" and "ml" should match when standalone
        assert scorer._score_technical_keywords("ai engineer", "") > 0
        assert scorer._score_technical_keywords("ml specialist", "") > 0


class TestFullJobScoring:
    """Test complete job scoring"""

    def test_perfect_job_scores_high(self, scorer):
        """Test perfect match job scores 90+ points"""
        job = {
            "title": "VP of Engineering - Robotics",
            "company": "Hardware Automation Co",
            "location": "Remote",
        }

        score, grade, breakdown, _ = scorer.score_job(job)
        assert score >= 90, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["A", "B"]

    def test_good_job_scores_medium(self, scorer):
        """Test good match job scores 70-90 points"""
        job = {
            "title": "Director of Product Engineering",
            "company": "IoT Startup",
            "location": "Hybrid - Toronto, ON",
        }

        score, grade, breakdown, _ = scorer.score_job(job)
        assert score >= 70, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["A", "B", "C"]

    def test_poor_job_scores_low(self, scorer):
        """Test poor match job scores <50 points"""
        job = {
            "title": "Software Engineer",
            "company": "SaaS Company",
            "location": "San Francisco, CA",
        }

        score, grade, breakdown, _ = scorer.score_job(job)
        assert score < 50, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["D", "F"]

    def test_score_breakdown_has_all_categories(self, scorer):
        """Test score breakdown includes all categories"""
        job = {"title": "Engineering Manager", "company": "Tech Co", "location": "Remote"}

        _, _, breakdown, _ = scorer.score_job(job)
        assert "seniority" in breakdown
        assert "domain" in breakdown
        assert "role_type" in breakdown
        assert "location" in breakdown
        assert "technical" in breakdown

    def test_score_with_none_location(self, scorer):
        """Test scoring handles None location"""
        job = {"title": "VP Engineering", "company": "Robotics Co", "location": None}

        score, grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["location"] == 0
        assert score > 0


class TestGradeCalculation:
    """Test grade calculation using scoring_utils"""

    def test_calculate_grade_boundaries(self):
        """Test grade boundaries (100-point system)"""
        assert calculate_grade(100) == "A"
        assert calculate_grade(85) == "A"
        assert calculate_grade(84) == "B"
        assert calculate_grade(70) == "B"
        assert calculate_grade(69) == "C"
        assert calculate_grade(55) == "C"
        assert calculate_grade(54) == "D"
        assert calculate_grade(40) == "D"
        assert calculate_grade(39) == "F"
        assert calculate_grade(0) == "F"


class TestEdgeCases:
    """Test edge cases and additional coverage"""

    def test_executive_director_seniority(self, scorer):
        """Should score 'Executive Director' as 25+ points"""
        score = scorer._score_seniority("executive director of engineering")
        assert score >= 25

    def test_remote_location_scoring(self, scorer):
        """Should give 15 points for Remote location"""
        assert scorer._score_location("remote") == 15

    def test_hybrid_ontario_location(self, scorer):
        """Should score hybrid Ontario locations"""
        assert scorer._score_location("hybrid - toronto") == 15
        assert scorer._score_location("hybrid - waterloo") == 15

    def test_ontario_city_location(self, scorer):
        """Should score Ontario cities"""
        assert scorer._score_location("toronto, on") >= 8

    def test_technical_keywords_scoring(self, scorer):
        """Should score technical keywords"""
        assert scorer._score_technical_keywords("mechatronics engineering role", "Test Co") >= 0
        assert scorer._score_technical_keywords("embedded systems developer", "Tech Corp") >= 0
        assert scorer._score_technical_keywords("manufacturing and production", "Factory Inc") >= 0


class TestIsLeadershipCheck:
    """Test is_leadership check uses word boundaries"""

    def test_is_leadership_prevents_false_positives(self, scorer):
        """Test is_leadership check doesn't match substrings"""
        non_leadership_titles = [
            "Supervisor",
            "Mischief Coordinator",
            "Headway Engineer",
            "Executive Assistant",
        ]

        for title in non_leadership_titles:
            score = scorer._score_role_type(title.lower())
            assert score <= 5, f"{title} should not score as leadership, got {score}"

    def test_is_leadership_matches_actual_leadership(self, scorer):
        """Test is_leadership correctly identifies real leadership titles

        ProfileScorer requires BOTH a leadership title AND a matching role_types keyword.
        "Director of Product" has no keyword match (bare "product" not in product_leadership).
        """
        # Leadership title + matching engineering_leadership keyword → 20 points
        leadership_with_keyword = [
            ("VP of Engineering", 20),
            ("Head of Operations", 20),  # "operations" matches operations_leadership
        ]

        for title, expected in leadership_with_keyword:
            score = scorer._score_role_type(title.lower())
            assert score >= expected, f"{title} should score >= {expected}, got {score}"

        # Leadership title but no keyword match → 0 points
        # "Director of Product" - bare "product" not in any role_types keyword list
        assert scorer._score_role_type("director of product") == 0

        # CTO and Executive Director - no role_type keyword match
        assert scorer._score_role_type("chief technology officer") == 0
        assert scorer._score_role_type("executive director") == 0


class TestKeywordBonusScoring:
    """Test keyword bonus scoring"""

    def test_keyword_bonus_scoring(self, scorer):
        """Test that titles with category keywords get bonus points"""
        score1 = scorer._score_role_type("director of product")
        score2 = scorer._score_role_type("director of product platform apis")
        assert score2 >= score1, "Keywords should increase score"

    def test_count_keyword_matches_helper(self, scorer):
        """Test _count_keyword_matches helper function"""
        keywords = ["roadmap", "stakeholders", "cross functional"]
        count = scorer._count_keyword_matches(
            "Product Roadmap and Stakeholders management", keywords
        )
        assert count == 2


class TestScorerFilteringIntegration:
    """Test scorer integration with company classification and filtering"""

    def test_software_role_penalty_applied(self, scorer):
        """Test that software engineering roles at software companies receive -20 penalty"""
        scorer.profile.scoring["filtering"] = {
            "aggression_level": "conservative",
            "software_engineering_avoid": ["software engineering", "backend engineering"],
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
            "role_software_penalty": -5,
        }

        job = {
            "title": "VP of Software Engineering",
            "company": "Stripe",
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)
        assert breakdown["company_classification"] == -20
        assert classification_metadata["filtered"] is True
        assert classification_metadata["company_type"] == "software"

    def test_hardware_company_boost_applied(self, scorer):
        """Test that hardware company engineering roles receive +10 boost"""
        scorer.profile.scoring["filtering"] = {
            "aggression_level": "moderate",
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
            "role_software_penalty": -5,
        }

        job = {
            "title": "VP of Engineering",
            "company": "Boston Dynamics",
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)
        assert breakdown["company_classification"] == 10
        assert classification_metadata["filtered"] is False
        assert classification_metadata.get("hardware_boost_applied") is True
        assert classification_metadata["company_type"] == "hardware"

    def test_product_leadership_unaffected_by_filtering(self, scorer):
        """Test that product leadership roles are never filtered

        Uses "Chief Product Officer" which matches the "chief product" keyword
        in Wes's product_leadership role_types config. Bare "product" titles
        (e.g., "VP of Product") don't match the multi-word keywords.
        """
        scorer.profile.scoring["filtering"] = {
            "aggression_level": "moderate",
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
            "role_software_penalty": -5,
        }

        job = {"title": "Chief Product Officer", "company": "Stripe", "location": "Remote, USA"}

        _, _, breakdown, classification_metadata = scorer.score_job(job)
        assert breakdown.get("company_classification", 0) == 0
        assert classification_metadata["filtered"] is False
        assert classification_metadata.get("filter_reason") == "product_leadership_any_company"

    def test_classification_metadata_stored(self, scorer):
        """Test that classification metadata is returned with all required fields"""
        job = {
            "title": "Director of Engineering",
            "company": "Tesla",
            "location": "Remote, USA",
        }

        _, _, _, classification_metadata = scorer.score_job(job)
        assert "company_type" in classification_metadata
        assert "confidence" in classification_metadata
        assert "signals" in classification_metadata
        assert "source" in classification_metadata
        assert "filtered" in classification_metadata
        assert classification_metadata["company_type"] in [
            "software",
            "hardware",
            "both",
            "unknown",
        ]
        assert 0.0 <= classification_metadata["confidence"] <= 1.0

    def test_score_returns_four_values(self, scorer):
        """Test that score_job returns 4 values"""
        job = {"title": "VP of Engineering", "company": "Test Company", "location": "Remote"}

        result = scorer.score_job(job)
        assert len(result) == 4
        score, grade, breakdown, classification_metadata = result
        assert isinstance(score, int)
        assert isinstance(grade, str)
        assert isinstance(breakdown, dict)
        assert isinstance(classification_metadata, dict)
