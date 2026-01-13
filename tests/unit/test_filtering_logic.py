"""
Unit tests for software role filtering logic
Tests for Issue #122 - Batch 3: Filtering Logic & Scorer Integration
"""

from src.utils.company_classifier import (
    CompanyClassification,
    classify_role_type,
    should_filter_job,
)


class TestClassifyRoleType:
    """Test role type classification helper function"""

    def test_engineering_leadership_role(self):
        """Test that engineering leadership roles are correctly classified"""
        role_types = {
            "engineering_leadership": ["engineering", "r&d", "technical", "hardware"],
            "product_leadership": ["product", "cpo", "chief product"],
            "dual_role": ["product engineering", "technical product"],
        }

        assert classify_role_type("VP of Engineering", role_types) == "engineering_leadership"
        assert classify_role_type("Director of R&D", role_types) == "engineering_leadership"
        assert (
            classify_role_type("Head of Technical Operations", role_types)
            == "engineering_leadership"
        )
        assert classify_role_type("VP Engineering", role_types) == "engineering_leadership"

    def test_product_leadership_role(self):
        """Test that product leadership roles are correctly classified"""
        role_types = {
            "engineering_leadership": ["engineering", "r&d", "technical"],
            "product_leadership": ["product", "cpo", "chief product"],
            "dual_role": ["product engineering"],
        }

        assert classify_role_type("VP of Product", role_types) == "product_leadership"
        assert classify_role_type("Chief Product Officer", role_types) == "product_leadership"
        assert classify_role_type("Director of Product", role_types) == "product_leadership"

    def test_dual_role(self):
        """Test that dual roles (product + engineering) are correctly classified"""
        role_types = {
            "engineering_leadership": ["engineering"],
            "product_leadership": ["product"],
            "dual_role": ["product engineering", "technical product"],
        }

        assert classify_role_type("VP of Product Engineering", role_types) == "dual_role"
        assert classify_role_type("Director of Technical Product", role_types) == "dual_role"

    def test_other_role(self):
        """Test that non-matching roles return 'other'"""
        role_types = {
            "engineering_leadership": ["engineering"],
            "product_leadership": ["product"],
        }

        assert classify_role_type("VP of Marketing", role_types) == "other"
        assert classify_role_type("Director of Sales", role_types) == "other"
        assert classify_role_type("Head of Operations", role_types) == "other"


class TestShouldFilterJobConservative:
    """Test filtering logic with conservative aggression level"""

    def test_explicit_software_engineering_filtered(self):
        """Conservative mode filters explicit 'VP of Software Engineering' titles"""
        classification = CompanyClassification(
            type="software", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {
                "aggression_level": "conservative",
                "software_engineering_avoid": ["software engineer", "software engineering"],
            },
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Software Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="conservative",
        )

        assert should_filter is True
        assert reason == "software_engineering_explicit_conservative"

    def test_vp_of_engineering_not_filtered_conservative(self):
        """Conservative mode does NOT filter generic 'VP of Engineering' at software company"""
        classification = CompanyClassification(
            type="software", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {
                "aggression_level": "conservative",
                "software_engineering_avoid": ["software engineer", "software engineering"],
            },
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="conservative",
        )

        assert should_filter is False
        assert reason == "no_filter_applied"


class TestShouldFilterJobModerate:
    """Test filtering logic with moderate aggression level (default)"""

    def test_engineering_at_software_company_filtered(self):
        """Moderate mode filters engineering roles at software companies with confidence ≥0.6"""
        classification = CompanyClassification(
            type="software", confidence=0.7, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {
                "aggression_level": "moderate",
                "software_engineering_avoid": [],
            },
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is True
        assert reason == "software_company_moderate_confidence"

    def test_low_confidence_not_filtered(self):
        """Moderate mode does NOT filter if confidence < 0.6"""
        classification = CompanyClassification(
            type="software", confidence=0.5, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Unknown Startup",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is False
        assert reason == "no_filter_applied"


class TestShouldFilterJobAggressive:
    """Test filtering logic with aggressive aggression level"""

    def test_engineering_without_hardware_keywords_filtered(self):
        """Aggressive mode filters engineering roles without hardware keywords"""
        classification = CompanyClassification(
            type="software", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="aggressive",
        )

        assert should_filter is True
        assert reason == "no_hardware_keywords_aggressive"

    def test_hardware_engineering_not_filtered_aggressive(self):
        """Aggressive mode does NOT filter if title contains hardware keywords"""
        classification = CompanyClassification(
            type="software", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Hardware Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="aggressive",
        )

        assert should_filter is False
        assert reason == "no_filter_applied"


class TestShouldFilterJobProductLeadership:
    """Test that product leadership roles are NEVER filtered"""

    def test_product_leadership_never_filtered(self):
        """Product leadership roles should never be filtered regardless of company type"""
        classification = CompanyClassification(
            type="software", confidence=1.0, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Product",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is False
        assert reason == "product_leadership_any_company"

    def test_dual_role_never_filtered(self):
        """Dual product/engineering roles should never be filtered"""
        classification = CompanyClassification(
            type="software", confidence=1.0, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
                "dual_role": ["product engineering"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Product Engineering",
            company_name="Stripe",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is False
        assert reason == "dual_role_any_company"


class TestShouldFilterJobHardwareCompany:
    """Test filtering logic for hardware companies"""

    def test_engineering_at_hardware_company_not_filtered(self):
        """Engineering roles at hardware companies should never be filtered"""
        classification = CompanyClassification(
            type="hardware", confidence=0.9, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {},
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Boston Dynamics",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is False
        assert reason == "hardware_company_engineering_allowed"


class TestShouldFilterJobDualDomainCompany:
    """Test filtering logic for dual-domain companies (both hardware and software)"""

    def test_software_focused_title_at_dual_domain_filtered(self):
        """Software-focused titles at dual-domain companies should be filtered"""
        classification = CompanyClassification(
            type="both", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {
                "software_engineering_avoid": ["software engineering", "backend", "frontend"],
            },
        }

        should_filter, reason = should_filter_job(
            job_title="Director of Backend Engineering",
            company_name="Tesla",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is True
        assert reason == "dual_domain_software_focused"

    def test_ambiguous_title_at_dual_domain_not_filtered(self):
        """Ambiguous engineering titles at dual-domain companies should NOT be filtered"""
        classification = CompanyClassification(
            type="both", confidence=0.8, signals={}, source="auto"
        )
        profile = {
            "role_types": {
                "engineering_leadership": ["engineering"],
                "product_leadership": ["product"],
            },
            "filtering": {
                "software_engineering_avoid": ["software engineering"],
            },
        }

        should_filter, reason = should_filter_job(
            job_title="VP of Engineering",
            company_name="Tesla",
            company_classification=classification,
            profile=profile,
            aggression_level="moderate",
        )

        assert should_filter is False
        assert reason == "dual_domain_ambiguous"
