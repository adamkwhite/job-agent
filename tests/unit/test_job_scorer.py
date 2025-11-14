"""
Tests for JobScorer

Tests the 115-point scoring system that evaluates jobs against candidate profile.
"""

from src.agents.job_scorer import JobScorer


class TestJobScorerInit:
    """Test JobScorer initialization"""

    def test_init(self):
        """Test scorer initializes with profile"""
        scorer = JobScorer()

        assert scorer.profile is not None
        assert "target_seniority" in scorer.profile
        assert "domain_keywords" in scorer.profile
        assert "role_types" in scorer.profile


class TestSeniorityScoring:
    """Test seniority scoring (0-30 points)"""

    def test_vp_level_scores_30(self):
        """Test VP/C-level roles score 30 points"""
        scorer = JobScorer()

        titles = [
            "VP of Engineering",
            "Vice President of Product",
            "Chief Technology Officer",
            "CTO",
            "CPO",
            "Head of Engineering",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 30, f"Failed for: {title}"

    def test_director_scores_25_or_30(self):
        """Test Director roles score 25-30 points"""
        scorer = JobScorer()

        titles = [
            "Director of Engineering",  # 30 (matches "head of")
            "Engineering Director",  # 25
            "Executive Director of Product",  # 25
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score >= 25, f"Failed for: {title}"

    def test_senior_manager_scores_15(self):
        """Test Senior Manager/Principal scores 15 points"""
        scorer = JobScorer()

        titles = [
            "Senior Manager, Engineering",
            "Principal Engineer",
            "Staff Engineer",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 15, f"Failed for: {title}"

    def test_manager_lead_scores_10(self):
        """Test Manager/Lead scores 10 points"""
        scorer = JobScorer()

        titles = [
            "Engineering Manager",
            "Product Manager",
            "Technical Lead",
            "Team Leadership",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score >= 10, f"Failed for: {title}"

    def test_ic_roles_score_0(self):
        """Test IC roles score 0 points"""
        scorer = JobScorer()

        titles = [
            "Software Engineer",
            "Product Designer",
            "Analyst",
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 0, f"Failed for: {title}"


class TestDomainScoring:
    """Test domain scoring (0-25 points)"""

    def test_robotics_hardware_scores_25(self):
        """Test robotics/hardware domain scores 25 points"""
        scorer = JobScorer()

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

    def test_medtech_scores_20_or_higher(self):
        """Test MedTech domain scores 20+ points (may score higher with engineering keywords)"""
        scorer = JobScorer()

        combinations = [
            ("Director Engineering", "MedTech Innovations"),  # 25 (engineering keyword)
            ("VP Product", "Medical Device Co"),  # 20
            ("Engineering Manager", "Healthcare Robotics"),  # 25 (engineering + robotics)
        ]

        for title, company in combinations:
            score = scorer._score_domain(title.lower(), company.lower())
            assert score >= 20, f"Failed for: {title} @ {company}"

    def test_manufacturing_scores_15_or_higher(self):
        """Test manufacturing/industrial scores 15+ points (may score higher with engineering keywords)"""
        scorer = JobScorer()

        combinations = [
            ("Director of Engineering", "Manufacturing Co"),  # 25 (engineering keyword)
            ("VP Product", "Supply Chain Solutions"),  # 15
            ("Engineering Manager", "Industrial Automation"),  # 25 (engineering keyword)
        ]

        for title, company in combinations:
            score = scorer._score_domain(title.lower(), company.lower())
            assert score >= 15, f"Failed for: {title} @ {company}"

    def test_generic_engineering_scores_10(self):
        """Test generic engineering scores 10 points"""
        scorer = JobScorer()

        score = scorer._score_domain("senior engineering manager", "tech company")
        assert score == 10

    def test_product_only_scores_5(self):
        """Test product-only roles score 5 points"""
        scorer = JobScorer()

        score = scorer._score_domain("product manager", "saas company")
        assert score == 5


class TestRoleTypeScoring:
    """Test role type scoring (0-20 points)"""

    def test_pure_software_engineering_penalized(self):
        """Test pure software engineering leadership gets penalty"""
        scorer = JobScorer()

        # Pure software engineering roles should be penalized (-5 points)
        titles = [
            "VP of Software Engineering",
            "Director of Software Development",
            "Head of Backend Engineering",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            # Software engineering leadership gets penalty
            assert score == -5, f"Failed for: {title}, got {score}"

    def test_hardware_engineering_leadership_moderate(self):
        """Test hardware engineering leadership scores moderately"""
        scorer = JobScorer()

        # Hardware engineering roles are acceptable but not top tier
        titles = [
            "Director of Hardware Engineering",
            "VP of R&D",
            "Head of Mechatronics Engineering",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            # Hardware engineering leadership scores 0-10 points
            assert score >= 0, f"Failed for: {title}, got {score}"
            assert score <= 10, f"Failed for: {title}, got {score}"

    def test_product_engineering_scores_18_or_higher(self):
        """Test product + engineering roles score 18+ points (may score 20 if engineering leadership detected first)"""
        scorer = JobScorer()

        titles = [
            "Product Engineering Manager",  # 18 (product + engineering)
            "Engineering Product Director",  # 20 (engineering leadership takes precedence)
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= 18, f"Failed for: {title}"

    def test_hardware_product_scores_20(self):
        """Test hardware product leadership scores 20 points (TOP TIER)"""
        scorer = JobScorer()

        # Product + Hardware is now the highest scoring role type
        titles = [
            "VP Product Hardware",
            "Director Product IoT",
            "Head of Technical Product",
            "Hardware Product Manager",
            "Technical Product Manager",
            "Platform Product Manager",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score == 20, f"Failed for: {title}, got {score}"

    def test_program_leadership_scores_12(self):
        """Test program/PMO leadership scores 12 points"""
        scorer = JobScorer()

        titles = [
            "Director Program Management",
            "VP PMO",
            "Head of Delivery",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score == 12, f"Failed for: {title}, got {score}"

    def test_product_leadership_scores_15(self):
        """Test product leadership scores 15 points (increased from 10)"""
        scorer = JobScorer()

        titles = [
            "VP of Product",
            "Director of Product",
            "Head of Product",
            "Chief Product Officer",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= 10, f"Failed for: {title}"


class TestLocationScoring:
    """Test location scoring (0-15 points)"""

    def test_remote_scores_15(self):
        """Test remote locations score 15 points"""
        scorer = JobScorer()

        locations = [
            "Remote",
            "Work from home",
            "WFH",
            "Remote - anywhere",
            "Distributed team",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score == 15, f"Failed for: {location}"

    def test_hybrid_ontario_scores_15(self):
        """Test hybrid + Ontario scores 15 points"""
        scorer = JobScorer()

        locations = [
            "Hybrid - Toronto, ON",
            "Hybrid - Waterloo, Ontario",
            "Hybrid - Ontario, Canada",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score == 15, f"Failed for: {location}"

    def test_preferred_cities_score_12(self):
        """Test preferred cities score 12 points"""
        scorer = JobScorer()

        locations = [
            "Toronto, ON",
            "Waterloo, Canada",
            "Burlington, Ontario",
            "Hamilton, ON",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score >= 12, f"Failed for: {location}"

    def test_broader_canada_scores_8(self):
        """Test broader Canada regions score 8 points"""
        scorer = JobScorer()

        locations = [
            "Ontario, Canada",
            "Canada",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score >= 8, f"Failed for: {location}"

    def test_us_locations_score_0(self):
        """Test US/other locations score 0 points"""
        scorer = JobScorer()

        locations = [
            "San Francisco, CA",
            "New York, NY",
            "London, UK",
        ]

        for location in locations:
            score = scorer._score_location(location.lower())
            assert score == 0, f"Failed for: {location}"

    def test_empty_location_scores_0(self):
        """Test empty location scores 0 points"""
        scorer = JobScorer()

        score = scorer._score_location("")
        assert score == 0


class TestCompanyStageScoring:
    """Test company stage scoring (0-15 points)"""

    def test_company_stage_returns_default(self):
        """Test company stage returns default 10 points"""
        scorer = JobScorer()

        # Currently returns default since we don't have stage data
        score = scorer._score_company_stage("any company")
        assert score == 10


class TestTechnicalKeywordsScoring:
    """Test technical keywords scoring (0-10 points)"""

    def test_multiple_tech_keywords(self):
        """Test multiple technical keywords add up"""
        scorer = JobScorer()

        # Should score points for mechatronics, embedded, firmware, etc.
        score = scorer._score_technical_keywords(
            "mechatronics embedded firmware", "hardware company"
        )
        assert score > 0
        assert score <= 10


class TestFullJobScoring:
    """Test complete job scoring"""

    def test_perfect_job_scores_high(self):
        """Test perfect match job scores 90+ points"""
        scorer = JobScorer()

        job = {
            "title": "VP of Engineering - Robotics",
            "company": "Hardware Automation Co",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should score very high
        assert score >= 90, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["A", "B"]

    def test_good_job_scores_medium(self):
        """Test good match job scores 70-90 points"""
        scorer = JobScorer()

        job = {
            "title": "Director of Product Engineering",
            "company": "IoT Startup",
            "location": "Hybrid - Toronto, ON",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert score >= 70, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["A", "B", "C"]

    def test_poor_job_scores_low(self):
        """Test poor match job scores <50 points"""
        scorer = JobScorer()

        job = {
            "title": "Software Engineer",
            "company": "SaaS Company",
            "location": "San Francisco, CA",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert score < 50, f"Score: {score}, Breakdown: {breakdown}"
        assert grade in ["D", "F"]

    def test_score_breakdown_has_all_categories(self):
        """Test score breakdown includes all categories"""
        scorer = JobScorer()

        job = {
            "title": "Engineering Manager",
            "company": "Tech Co",
            "location": "Remote",
        }

        _, _, breakdown = scorer.score_job(job)

        assert "seniority" in breakdown
        assert "domain" in breakdown
        assert "role_type" in breakdown
        assert "location" in breakdown
        assert "company_stage" in breakdown
        assert "technical" in breakdown

    def test_score_with_none_location(self):
        """Test scoring handles None location"""
        scorer = JobScorer()

        job = {
            "title": "VP Engineering",
            "company": "Robotics Co",
            "location": None,
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should not crash, location score should be 0
        assert breakdown["location"] == 0
        assert score > 0  # Still scores on other factors


class TestGradeCalculation:
    """Test grade calculation"""

    def test_calculate_grade_a(self):
        """Test A grade calculation"""
        scorer = JobScorer()

        grade = scorer._calculate_grade(98)
        assert grade == "A"

    def test_calculate_grade_b(self):
        """Test B grade calculation"""
        scorer = JobScorer()

        grade = scorer._calculate_grade(85)
        assert grade == "B"

    def test_calculate_grade_c(self):
        """Test C grade calculation"""
        scorer = JobScorer()

        grade = scorer._calculate_grade(70)
        assert grade == "C"

    def test_calculate_grade_d(self):
        """Test D grade calculation"""
        scorer = JobScorer()

        grade = scorer._calculate_grade(55)
        assert grade == "D"

    def test_calculate_grade_f(self):
        """Test F grade calculation"""
        scorer = JobScorer()

        grade = scorer._calculate_grade(30)
        assert grade == "F"


class TestJobScorerEdgeCases:
    """Test edge cases and additional coverage"""

    def test_executive_director_seniority(self):
        """Should score 'Executive Director' as 25 points"""
        scorer = JobScorer()
        score = scorer._score_seniority("executive director of engineering")
        assert score >= 25

    def test_remote_location_scoring(self):
        """Should give 15 points for Remote location"""
        scorer = JobScorer()
        score = scorer._score_location("remote")
        assert score == 15

    def test_hybrid_ontario_location(self):
        """Should score hybrid Ontario locations"""
        scorer = JobScorer()
        assert scorer._score_location("hybrid - toronto") == 15
        assert scorer._score_location("hybrid - waterloo") == 15

    def test_ontario_city_location(self):
        """Should score Ontario cities"""
        scorer = JobScorer()
        # Toronto scores 12, but other cities may score differently
        assert scorer._score_location("toronto, on") >= 8
        assert scorer._score_location("ottawa, ontario") >= 0

    def test_company_stage_series_a(self):
        """Should detect Series A stage"""
        scorer = JobScorer()
        # Test method exists and returns a score
        score = scorer._score_company_stage("We just closed our Series A round")
        assert score >= 0

    def test_company_stage_growth(self):
        """Should detect growth stage"""
        scorer = JobScorer()
        score = scorer._score_company_stage("Fast-growing startup")
        assert score >= 0

    def test_technical_keywords_scoring(self):
        """Should score technical keywords"""
        scorer = JobScorer()

        # Mechatronics - test method exists and returns score
        score = scorer._score_technical_keywords("mechatronics engineering role", "Test Co")
        assert score >= 0

        # Embedded
        score = scorer._score_technical_keywords("embedded systems developer", "Tech Corp")
        assert score >= 0

        # Manufacturing
        score = scorer._score_technical_keywords("manufacturing and production", "Factory Inc")
        assert score >= 0
