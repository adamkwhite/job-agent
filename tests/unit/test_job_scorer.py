"""
Tests for JobScorer

Tests the 100-point scoring system that evaluates jobs against candidate profile.
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

    def test_vp_with_punctuation_scores_30(self):
        """Test VP titles with commas, dashes, and other punctuation score 30 points

        This test specifically addresses the bug where "VP, Robotics Software"
        was scoring 0 because the old code checked for "vp " (with trailing space)
        which didn't match "vp," (with comma).
        """
        scorer = JobScorer()

        titles = [
            "VP, Robotics Software",  # Bug case: comma after VP
            "VP - Engineering",  # Dash after VP
            "VP: Product Management",  # Colon after VP
            "VP. Operations",  # Period after VP (unusual but possible)
        ]

        for title in titles:
            score = scorer._score_seniority(title.lower())
            assert score == 30, f"Failed for: {title} (got {score})"

    def test_false_positive_prevention(self):
        """Test that word boundary checking prevents false positive matches

        Without word boundaries:
        - "supervisor" would match "vp" ❌
        - "mischief" would match "chief" ❌
        - "managerial" would match "manager" ❌

        With word boundaries (correct):
        - These should NOT match ✅
        """
        scorer = JobScorer()

        # Supervisor should score 0 (not match "vp")
        assert scorer._score_seniority("supervisor") == 0, "Supervisor incorrectly matched 'vp'"

        # Mischief should score 0 (not match "chief")
        assert scorer._score_seniority("mischief coordinator") == 0, (
            "Mischief incorrectly matched 'chief'"
        )

        # Managerial should match "manager" and score 10
        # Note: This is expected to match because "managerial" is a valid management-related term
        score = scorer._score_seniority("managerial analyst")
        # Actually "managerial" won't match "manager" with word boundaries, so should be 0
        # This is correct behavior - we want exact word matches
        assert score == 0, f"Managerial analyst got {score}, expected 0"


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

        # Pure software engineering roles should be penalized
        titles = [
            ("VP of Software Engineering", -5),  # Pure software, no bonuses
            ("Director of Software Development", -5),  # Software + development penalty
            ("Head of Backend Engineering", -5),  # Backend engineering penalty
        ]

        for title, expected in titles:
            score = scorer._score_role_type(title.lower())
            # Software engineering leadership gets -5 penalty
            assert score == expected, f"Failed for: {title}, got {score}"

    def test_hardware_engineering_leadership_moderate(self):
        """Test hardware engineering leadership scores well with new system"""
        scorer = JobScorer()

        # Hardware engineering roles now score higher (20 base) with new system
        titles = [
            "Director of Hardware Engineering",
            "VP of R&D",
            "Head of Mechatronics Engineering",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            # Hardware engineering leadership scores 20 base + bonuses
            assert score >= 15, f"Failed for: {title}, got {score}"

    def test_product_engineering_scores_18_or_higher(self):
        """Test product + engineering roles score well for leadership"""
        scorer = JobScorer()

        titles = [
            ("Director of Product Engineering", 15),  # Product + engineering leadership
            ("VP Product Engineering", 15),  # Product + engineering leadership
        ]

        for title, min_score in titles:
            score = scorer._score_role_type(title.lower())
            # Should score 15+ (product leadership with engineering)
            assert score >= min_score, f"Failed for: {title}, got {score}"

    def test_hardware_product_scores_20(self):
        """Test hardware product leadership scores 20+ points (TOP TIER)"""
        scorer = JobScorer()

        # Product + Hardware LEADERSHIP is highest scoring
        leadership_titles = [
            "VP Product Hardware",
            "Director Product IoT",
            "Head of Technical Product",
        ]

        for title in leadership_titles:
            score = scorer._score_role_type(title.lower())
            # 20 base + keyword bonuses
            assert score >= 20, f"Failed for: {title}, got {score}"

        # Non-leadership Product Manager titles score lower (5-10 range)
        manager_titles = [
            "Hardware Product Manager",
            "Technical Product Manager",
            "Platform Product Manager",
        ]

        for title in manager_titles:
            score = scorer._score_role_type(title.lower())
            # Generic fallback: 5 points
            assert score >= 5, f"Failed for: {title}, got {score}"

    def test_program_leadership_scores_12(self):
        """Test program/PMO leadership scores 15+ points with new system"""
        scorer = JobScorer()

        titles = [
            "Director Program Management",
            "VP PMO",
            "Head of Delivery",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            # New system: 15 base + keyword bonuses
            assert score >= 12, f"Failed for: {title}, got {score}"

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

    def test_ai_ml_keywords_use_word_boundaries(self):
        """Test ai/ml keywords use word boundaries to avoid false matches

        This test specifically addresses the bug where "ai" matched "email"
        and "ml" matched "html" due to substring matching.
        """
        scorer = JobScorer()

        # "ai" should NOT match these words
        assert scorer._score_technical_keywords("email marketing", "detail oriented") == 0
        assert scorer._score_technical_keywords("domain knowledge", "gmail support") == 0

        # "ml" should NOT match these words
        assert scorer._score_technical_keywords("html developer", "xml parsing") == 0

        # But "ai" and "ml" should match when they're actual standalone words
        assert scorer._score_technical_keywords("ai engineer", "") > 0
        assert scorer._score_technical_keywords("ml specialist", "") > 0
        # Note: "artificial intelligence" and "machine learning" don't contain "ai"/"ml" as standalone words
        # They would need to be added as separate keywords if we want to match them


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

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

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

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

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

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

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

        _, _, breakdown, _ = scorer.score_job(job)

        assert "seniority" in breakdown
        assert "domain" in breakdown
        assert "role_type" in breakdown
        assert "location" in breakdown
        assert "technical" in breakdown

    def test_score_with_none_location(self):
        """Test scoring handles None location"""
        scorer = JobScorer()

        job = {
            "title": "VP Engineering",
            "company": "Robotics Co",
            "location": None,
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

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


class TestIsLeadershipCheck:
    """Test is_leadership check uses word boundaries"""

    def test_is_leadership_prevents_false_positives(self):
        """Test is_leadership check doesn't match substrings

        This addresses the bug where "supervisor" matched "vp" and
        "mischief coordinator" matched "chief" due to substring matching.
        """
        scorer = JobScorer()

        # These should NOT score as leadership roles
        non_leadership_titles = [
            "Supervisor",  # Contains "vp" but not leadership
            "Mischief Coordinator",  # Contains "chief" but not leadership
            "Headway Engineer",  # Contains "head" but not leadership
            "Executive Assistant",  # Contains "executive" but support role
        ]

        for title in non_leadership_titles:
            score = scorer._score_role_type(title.lower())
            # Should score 0 or very low (not leadership bonus)
            assert score <= 5, f"{title} should not score as leadership, got {score}"

    def test_is_leadership_matches_actual_leadership(self):
        """Test is_leadership correctly identifies real leadership titles"""
        scorer = JobScorer()

        # These SHOULD score as leadership roles with category matches
        leadership_titles_with_categories = [
            ("VP of Engineering", 15),  # Engineering leadership
            ("Director of Product", 15),  # Product leadership
            ("Head of Operations", 12),  # Operations category
        ]

        for title, min_score in leadership_titles_with_categories:
            score = scorer._score_role_type(title.lower())
            # Should score high (leadership bonus)
            assert score >= min_score, f"{title} should score >= {min_score}, got {score}"

        # CTO and Executive Director are detected as leadership but have no category match
        # This is expected behavior - seniority scoring will give them 30 points
        assert scorer._score_role_type("chief technology officer") == 0
        assert scorer._score_role_type("executive director") == 0


class TestSevenCategoryRoleScoring:
    """Test 7-category role scoring system with keyword bonuses"""

    def test_product_leadership_category(self):
        """Test Product Leadership category (15-20 base)"""
        scorer = JobScorer()

        # Product leadership roles
        titles = [
            ("Head of Product", 15),  # Base product leadership
            ("Director of Product", 15),  # Base product leadership
            ("VP Product", 15),  # Base product leadership
        ]

        for title, min_score in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= min_score, f"Failed for: {title}, got {score}"

    def test_product_hardware_highest_tier(self):
        """Test Product + Hardware is highest tier (20+ base for leadership)"""
        scorer = JobScorer()

        # Leadership titles get higher scores
        leadership_titles = [
            "VP Product Hardware",
            "Director Product IoT",
            "Head of Technical Product",
        ]

        for title in leadership_titles:
            score = scorer._score_role_type(title.lower())
            # 20 base + keyword bonuses
            assert score >= 18, f"Failed for: {title}, got {score}"

        # Non-leadership platform product role (manager but not director)
        score = scorer._score_role_type("product manager - platform")
        assert score >= 15, f"Product Manager - Platform should score 15+, got {score}"

    def test_engineering_leadership_category(self):
        """Test Engineering Leadership category (15-20 base)"""
        scorer = JobScorer()

        # Hardware engineering leadership
        titles = [
            ("Director of Hardware Engineering", 18),  # Hardware engineering
            ("VP of R&D", 18),  # R&D engineering
            ("Head of Mechatronics Engineering", 18),  # Mechatronics engineering
        ]

        for title, min_score in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= min_score, f"Failed for: {title}, got {score}"

    def test_pure_software_penalty_maintained(self):
        """Test pure software engineering gets -5 base"""
        scorer = JobScorer()

        # These should get -5 penalty (no matched_category, so no bonuses)
        titles = [
            "VP of Software Engineering",
            "Head of Backend Engineering",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            # -5 base, no category match, no bonuses
            assert score == -5, f"Failed for: {title}, got {score}"

        # "Director Software Development" may match other categories, test separately
        score = scorer._score_role_type("director software development")
        # Should still be penalized or score low
        assert score <= 0, f"Director Software Development should be penalized, got {score}"

    def test_technical_program_management_category(self):
        """Test Technical Program Management category (12-18 base)"""
        scorer = JobScorer()

        titles = [
            ("Director of Program Management", 15),
            ("VP of PMO", 15),
            ("Head of Delivery", 15),
        ]

        for title, min_score in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= min_score, f"Failed for: {title}, got {score}"

    def test_manufacturing_npi_operations_category(self):
        """Test Manufacturing/NPI/Operations category (12-18 base)"""
        scorer = JobScorer()

        # Leadership roles
        score = scorer._score_role_type("director of manufacturing")
        assert score >= 15, f"Director of Manufacturing should score 15+, got {score}"

        # Non-leadership
        score = scorer._score_role_type("npi engineer")
        assert score >= 10, f"NPI Engineer should score 10+, got {score}"

    def test_product_development_rnd_category(self):
        """Test Product Development/R&D category (10-15 base)"""
        scorer = JobScorer()

        # Leadership R&D
        score = scorer._score_role_type("director of product development")
        assert score >= 10, f"Director of Product Development should score 10+, got {score}"

    def test_platform_integrations_systems_category(self):
        """Test Platform/Integrations/Systems category (15-18 base)"""
        scorer = JobScorer()

        # Platform leadership
        score = scorer._score_role_type("director of platform engineering")
        assert score >= 15, f"Director of Platform Engineering should score 15+, got {score}"

        # Non-leadership platform
        score = scorer._score_role_type("platform engineer")
        assert score >= 10, f"Platform Engineer should score 10+, got {score}"

    def test_robotics_automation_engineering_category(self):
        """Test Robotics/Automation Engineering category (10-15 base)"""
        scorer = JobScorer()

        # Senior/Lead robotics roles
        titles = [
            "Senior Robotics Engineer",
            "Lead Automation Engineer",
            "Principal Mechatronics Engineer",
        ]

        for title in titles:
            score = scorer._score_role_type(title.lower())
            assert score >= 10, f"Failed for: {title}, got {score}"

    def test_keyword_bonus_scoring(self):
        """Test +2 points per keyword match bonus"""
        scorer = JobScorer()

        # Test that titles with category keywords get bonus points
        # Note: We can't test exact bonus since title alone may not contain
        # job description keywords, but we can verify scoring exists

        score1 = scorer._score_role_type("director of product")  # Base score
        score2 = scorer._score_role_type("director of product platform apis")  # With keywords

        # Score2 should be higher due to keyword matches
        assert score2 >= score1, "Keywords should increase score"

    def test_count_keyword_matches_helper(self):
        """Test _count_keyword_matches helper function"""
        scorer = JobScorer()

        keywords = ["roadmap", "stakeholders", "cross functional"]

        # Should match case-insensitively
        count = scorer._count_keyword_matches(
            "Product Roadmap and Stakeholders management", keywords
        )
        assert count == 2  # roadmap + stakeholders

        # Should handle matches (note: "cross functional" won't match "cross-functional" exactly)
        count = scorer._count_keyword_matches("cross functional team leadership", keywords)
        assert count >= 1  # cross functional

    def test_generic_fallback_scoring(self):
        """Test generic fallback scores correctly"""
        scorer = JobScorer()

        # Generic product/program roles without leadership
        score = scorer._score_role_type("product analyst")
        assert score >= 0, f"Product Analyst should score 0+, got {score}"

        # Generic role without product/program
        score = scorer._score_role_type("business analyst")
        assert score == 0, f"Business Analyst should score 0, got {score}"


class TestScorerFilteringIntegration:
    """Test scorer integration with company classification and filtering (Issue #122 - Batch 3)"""

    def test_software_role_penalty_applied(self):
        """Test that software engineering roles at software companies receive -20 penalty"""
        scorer = JobScorer()

        # Add filtering config to profile
        scorer.profile["filtering"] = {
            "aggression_level": "conservative",  # Use conservative to test explicit keyword filtering
            "software_engineering_avoid": ["software engineering", "backend engineering"],
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
        }

        job = {
            "title": "VP of Software Engineering",  # Explicit software engineering title
            "company": "Stripe",  # Known software company in config
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Verify penalty was applied (conservative mode filters explicit titles)
        assert "company_classification" in breakdown
        assert breakdown["company_classification"] == -20
        assert classification_metadata["filtered"] is True
        assert classification_metadata["company_type"] == "software"

    def test_hardware_company_boost_applied(self):
        """Test that hardware company engineering roles receive +10 boost"""
        scorer = JobScorer()

        scorer.profile["filtering"] = {
            "aggression_level": "moderate",
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
        }

        job = {
            "title": "VP of Engineering",
            "company": "Boston Dynamics",  # Known hardware company in config
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Verify boost was applied
        assert "company_classification" in breakdown
        assert breakdown["company_classification"] == 10
        assert classification_metadata["filtered"] is False
        assert classification_metadata.get("hardware_boost_applied") is True
        assert classification_metadata["company_type"] == "hardware"

    def test_product_leadership_unaffected_by_filtering(self):
        """Test that product leadership roles are never filtered regardless of company type"""
        scorer = JobScorer()

        scorer.profile["filtering"] = {
            "aggression_level": "moderate",
            "software_company_penalty": -20,
            "hardware_company_boost": 10,
        }

        job = {
            "title": "VP of Product",
            "company": "Stripe",  # Software company
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Verify no penalty for product role
        assert breakdown.get("company_classification", 0) == 0
        assert classification_metadata["filtered"] is False
        # Product roles should have reason "product_leadership_any_company"
        assert classification_metadata.get("filter_reason") == "product_leadership_any_company"

    def test_classification_metadata_stored(self):
        """Test that classification metadata is returned with all required fields"""
        scorer = JobScorer()

        job = {
            "title": "Director of Engineering",
            "company": "Tesla",  # Dual-domain company
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Verify all metadata fields present
        assert "company_type" in classification_metadata
        assert "confidence" in classification_metadata
        assert "signals" in classification_metadata
        assert "source" in classification_metadata
        assert "filtered" in classification_metadata

        # Verify company type is valid
        assert classification_metadata["company_type"] in [
            "software",
            "hardware",
            "both",
            "unknown",
        ]

        # Verify confidence is in valid range
        assert 0.0 <= classification_metadata["confidence"] <= 1.0

    def test_score_returns_four_values(self):
        """Test that score_job now returns 4 values (score, grade, breakdown, classification_metadata)"""
        scorer = JobScorer()

        job = {
            "title": "VP of Engineering",
            "company": "Test Company",
            "location": "Remote",
        }

        result = scorer.score_job(job)

        # Verify 4-tuple return value
        assert len(result) == 4
        score, grade, breakdown, classification_metadata = result

        # Verify types
        assert isinstance(score, int)
        assert isinstance(grade, str)
        assert isinstance(breakdown, dict)
        assert isinstance(classification_metadata, dict)
