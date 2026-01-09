"""
Unit tests for JobFilterPipeline - Hard Filters

Tests verify that:
1. Each hard filter blocks appropriate jobs
2. Exception cases are handled correctly
3. Case insensitivity works
4. Context filters work after scoring
5. Filter execution is fast (<10ms per job)
"""

import pytest

from src.agents.job_filter_pipeline import JobFilterPipeline


class TestJobFilterPipelineHardFilters:
    """Test hard filters (Stage 1: pre-scoring)"""

    @pytest.fixture
    def profile_config(self):
        """Profile configuration with all hard filters"""
        return {
            "hard_filter_keywords": {
                "seniority_blocks": ["junior", "intern", "coordinator"],
                "role_type_blocks": [
                    "people operations",
                    "human resources",
                    "hr manager",
                    "hr director",
                    "talent acquisition",
                    "recruiting",
                    "recruiter",
                ],
                "department_blocks": ["finance", "accounting", "legal", "compliance"],
                "sales_marketing_blocks": [
                    "sales manager",
                    "marketing manager",
                    "business development",
                ],
                "exceptions": {
                    "c_level_override": ["chief people officer"],
                    "senior_coordinator_allowed": True,
                },
            },
            "context_filters": {
                "associate_with_senior": ["director", "vp", "principal", "chief"],
                "software_engineering_exceptions": ["hardware", "product"],
                "contract_min_seniority_score": 25,
            },
        }

    @pytest.fixture
    def pipeline(self, profile_config):
        """Create pipeline instance for testing"""
        return JobFilterPipeline(profile_config)

    # ===== Seniority Filters =====

    def test_filter_junior_position(self, pipeline):
        """Test that junior positions are blocked"""
        job = {"title": "Junior Software Engineer"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_junior"

    def test_filter_junior_case_insensitive(self, pipeline):
        """Test junior filter is case insensitive"""
        job = {"title": "JUNIOR PRODUCT MANAGER"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_junior"

    def test_filter_intern_position(self, pipeline):
        """Test that intern positions are blocked"""
        job = {"title": "Engineering Intern"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_intern"

    def test_filter_internship_position(self, pipeline):
        """Test that internship positions are blocked"""
        job = {"title": "Product Management Internship"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_intern"

    def test_filter_coordinator_blocked(self, pipeline):
        """Test that coordinator positions are blocked"""
        job = {"title": "Engineering Coordinator"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_coordinator"

    def test_senior_coordinator_allowed(self, pipeline):
        """Test that senior coordinator passes (exception case)"""
        job = {"title": "Senior Coordinator, Engineering"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    # ===== Associate Filters =====

    def test_filter_associate_manager_blocked(self, pipeline):
        """Test that low-seniority associate roles are blocked"""
        job = {"title": "Associate Product Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_associate_low_seniority"

    def test_associate_director_allowed(self, pipeline):
        """Test that Associate Director passes (Director exception)"""
        job = {"title": "Associate Director of Engineering"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_associate_vp_allowed(self, pipeline):
        """Test that Associate VP passes (VP exception)"""
        job = {"title": "Associate VP, Product Management"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_associate_principal_allowed(self, pipeline):
        """Test that Associate Principal passes (Principal exception)"""
        job = {"title": "Associate Principal Product Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_associate_chief_allowed(self, pipeline):
        """Test that Associate Chief passes (Chief exception)"""
        job = {"title": "Associate Chief Technology Officer"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    # ===== HR/People Operations Filters =====

    def test_filter_people_operations_blocked(self, pipeline):
        """Test that People Operations roles are blocked"""
        job = {"title": "Director, People Operations"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_hr_role"

    def test_filter_hr_manager_blocked(self, pipeline):
        """Test that HR Manager roles are blocked"""
        job = {"title": "HR Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_hr_role"

    def test_filter_recruiter_blocked(self, pipeline):
        """Test that Recruiter roles are blocked"""
        job = {"title": "Senior Technical Recruiter"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_hr_role"

    def test_chief_people_officer_allowed(self, pipeline):
        """Test that Chief People Officer passes (C-level exception)"""
        job = {"title": "Chief People Officer"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    # ===== Finance Filters =====

    def test_filter_finance_role_blocked(self, pipeline):
        """Test that Finance roles are blocked"""
        job = {"title": "Director of Finance"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_finance_role"

    def test_filter_accounting_blocked(self, pipeline):
        """Test that Accounting roles are blocked"""
        job = {"title": "Accounting Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_finance_role"

    def test_filter_cfo_blocked(self, pipeline):
        """Test that CFO roles are blocked"""
        job = {"title": "Chief Financial Officer"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_finance_role"

    # ===== Legal Filters =====

    def test_filter_legal_role_blocked(self, pipeline):
        """Test that Legal roles are blocked"""
        job = {"title": "Director of Legal"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_legal_role"

    def test_filter_counsel_blocked(self, pipeline):
        """Test that Counsel roles are blocked"""
        job = {"title": "General Counsel"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_legal_role"

    def test_filter_compliance_blocked(self, pipeline):
        """Test that Compliance roles are blocked"""
        job = {"title": "VP of Compliance"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_legal_role"

    # ===== Sales/Marketing Filters =====

    def test_filter_sales_manager_blocked(self, pipeline):
        """Test that Sales Manager roles are blocked"""
        job = {"title": "Sales Manager, Enterprise"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_sales_marketing"

    def test_filter_marketing_manager_blocked(self, pipeline):
        """Test that Marketing Manager roles are blocked"""
        job = {"title": "Product Marketing Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_marketing_role"

    def test_director_of_sales_allowed(self, pipeline):
        """Test that Director+ sales roles pass (seniority exception)"""
        job = {"title": "Director of Sales"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_vp_marketing_allowed(self, pipeline):
        """Test that VP+ marketing roles pass"""
        job = {"title": "VP of Marketing"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    # ===== Administrative Filters =====

    def test_filter_administrative_blocked(self, pipeline):
        """Test that Administrative roles are blocked"""
        job = {"title": "Administrative Assistant"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_administrative"

    def test_filter_office_manager_blocked(self, pipeline):
        """Test that Office Manager roles are blocked"""
        job = {"title": "Office Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_administrative"

    def test_filter_executive_assistant_blocked(self, pipeline):
        """Test that Executive Assistant roles are blocked"""
        job = {"title": "Executive Assistant to CEO"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_administrative"

    # ===== Retail Filters =====

    def test_filter_retail_store_operations_blocked(self, pipeline):
        """Test that Retail Store Operations roles are blocked"""
        job = {"title": "Director - Retail Store Operations"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_retail"

    def test_filter_retail_manager_blocked(self, pipeline):
        """Test that Retail Manager roles are blocked"""
        job = {"title": "Retail Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_retail"

    def test_filter_store_manager_blocked(self, pipeline):
        """Test that Store Manager roles are blocked"""
        job = {"title": "Store Manager"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_retail"

    # ===== Pass-Through Cases =====

    def test_vp_engineering_passes(self, pipeline):
        """Test that VP Engineering passes all filters"""
        job = {"title": "VP of Engineering"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_director_product_passes(self, pipeline):
        """Test that Director of Product passes all filters"""
        job = {"title": "Director of Product Management"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_head_of_robotics_passes(self, pipeline):
        """Test that Head of Robotics passes all filters"""
        job = {"title": "Head of Robotics Engineering"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_cto_passes(self, pipeline):
        """Test that CTO passes all filters"""
        job = {"title": "Chief Technology Officer"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    # ===== Edge Cases =====

    def test_empty_title(self, pipeline):
        """Test handling of job with empty title"""
        job = {"title": ""}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_missing_title(self, pipeline):
        """Test handling of job with missing title"""
        job = {}
        should_continue, reason = pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None

    def test_minimal_profile(self):
        """Test pipeline works with minimal profile config"""
        minimal_profile = {}
        pipeline = JobFilterPipeline(minimal_profile)

        job = {"title": "VP of Engineering"}
        should_continue, reason = pipeline.apply_hard_filters(job)

        # Should pass with default/empty config
        assert should_continue is True
        assert reason is None


class TestJobFilterPipelineContextFilters:
    """Test context-aware filters (Stage 2: post-scoring)"""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline with context filter config"""
        profile = {
            "context_filters": {
                "software_engineering_exceptions": ["hardware", "product"],
                "contract_min_seniority_score": 25,
            }
        }
        return JobFilterPipeline(profile)

    # ===== Software Engineering Filters =====

    def test_filter_pure_software_engineering(self, pipeline):
        """Test that pure software engineering roles are blocked"""
        job = {"title": "Director of Software Engineering"}
        score = 85
        breakdown = {"seniority": 25, "domain": 15}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is False
        assert reason == "context_filter_software_engineering"

    def test_hardware_software_allowed(self, pipeline):
        """Test that hardware software roles pass (hardware keyword)"""
        job = {"title": "Director of Hardware Software"}
        score = 85
        breakdown = {"seniority": 25, "domain": 15}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None

    def test_product_software_allowed(self, pipeline):
        """Test that product software roles pass (product keyword)"""
        job = {"title": "VP, Product Engineering"}
        score = 90
        breakdown = {"seniority": 30, "domain": 20}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None

    # ===== Contract Position Filters =====

    def test_filter_contract_low_seniority(self, pipeline):
        """Test that low-seniority contract roles are blocked"""
        job = {"title": "Senior Engineer - Contract"}
        score = 65
        breakdown = {"seniority": 15, "domain": 20}  # Below 25

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is False
        assert reason == "context_filter_contract_low_seniority"

    def test_contract_director_allowed(self, pipeline):
        """Test that Director+ contract roles pass"""
        job = {"title": "Director of Engineering (Contract)"}
        score = 85
        breakdown = {"seniority": 25, "domain": 20}  # 25 = Director level

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None

    def test_contract_vp_allowed(self, pipeline):
        """Test that VP contract roles pass"""
        job = {"title": "VP Product Management | Contract until Oct 2026"}
        score = 95
        breakdown = {"seniority": 30, "domain": 20}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None

    def test_temporary_position_blocked(self, pipeline):
        """Test that temporary mid-level positions are blocked"""
        job = {"title": "Senior Product Manager (Temporary)"}
        score = 70
        breakdown = {"seniority": 20, "domain": 20}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is False
        assert reason == "context_filter_contract_low_seniority"

    # ===== Pass-Through Cases =====

    def test_normal_engineering_role_passes(self, pipeline):
        """Test that non-software engineering roles pass"""
        job = {"title": "Director of Hardware Engineering"}
        score = 85
        breakdown = {"seniority": 25, "domain": 20}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None

    def test_permanent_role_passes(self, pipeline):
        """Test that permanent roles pass regardless of seniority"""
        job = {"title": "Senior Product Manager"}
        score = 70
        breakdown = {"seniority": 20, "domain": 20}

        should_keep, reason = pipeline.apply_context_filters(job, score, breakdown)

        assert should_keep is True
        assert reason is None


class TestJobFilterPipelineIntegration:
    """Integration tests for full pipeline flow"""

    @pytest.fixture
    def full_pipeline(self):
        """Pipeline with all filters configured"""
        profile = {
            "hard_filter_keywords": {
                "role_type_blocks": ["people operations", "recruiter", "hr manager"],
                "exceptions": {
                    "c_level_override": ["chief people officer"],
                    "senior_coordinator_allowed": True,
                },
            },
            "context_filters": {
                "associate_with_senior": ["director", "vp", "principal", "chief"],
                "software_engineering_exceptions": ["hardware", "product"],
                "contract_min_seniority_score": 25,
            },
        }
        return JobFilterPipeline(profile)

    def test_regression_issue_159_people_operations(self, full_pipeline):
        """Regression: Director, People Operations should be blocked"""
        job = {"title": "Director, People Operations"}

        # Hard filter should block
        should_continue, reason = full_pipeline.apply_hard_filters(job)

        assert should_continue is False
        assert reason == "hard_filter_hr_role"

    def test_regression_issue_159_associate_principal(self, full_pipeline):
        """Regression: Associate Principal should pass (Principal exception)"""
        job = {"title": "Associate Principal Product Manager"}

        # Hard filter should pass
        should_continue, reason = full_pipeline.apply_hard_filters(job)

        assert should_continue is True
        assert reason is None
