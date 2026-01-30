"""
Unit tests for Pydantic profile configuration models.

Tests validation logic for:
- ProfileConfig and nested models
- Required fields
- Valid types and ranges
- Custom validators (grades, aggression levels, etc.)
- Error messages are user-friendly
"""

import pytest
from pydantic import ValidationError

from src.models.pydantic_models import (
    ContextFilters,
    Digest,
    EmailCredentials,
    Filtering,
    HardFilterKeywords,
    LocationPreferences,
    Notifications,
    ProfileConfig,
    RoleTypes,
    Scoring,
)


class TestEmailCredentials:
    """Test EmailCredentials model validation"""

    def test_valid_email_credentials(self):
        """Test valid email credentials"""
        creds = EmailCredentials(username="test@gmail.com", app_password_env="TEST_PASSWORD")
        assert creds.username == "test@gmail.com"
        assert creds.app_password_env == "TEST_PASSWORD"

    def test_empty_username_fails(self):
        """Test empty username raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            EmailCredentials(username="", app_password_env="TEST_PASSWORD")
        assert "username" in str(exc_info.value)

    def test_whitespace_username_fails(self):
        """Test whitespace-only username raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            EmailCredentials(username="   ", app_password_env="TEST_PASSWORD")
        assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_empty_app_password_env_fails(self):
        """Test empty app_password_env raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            EmailCredentials(username="test@gmail.com", app_password_env="")
        assert "app_password_env" in str(exc_info.value)


class TestLocationPreferences:
    """Test LocationPreferences model validation"""

    def test_valid_location_preferences(self):
        """Test valid location preferences"""
        prefs = LocationPreferences(
            remote_keywords=["remote", "wfh"],
            hybrid_keywords=["hybrid"],
            preferred_cities=["toronto", "waterloo"],
            preferred_regions=["ontario", "canada"],
        )
        assert len(prefs.remote_keywords) == 2
        assert len(prefs.preferred_cities) == 2

    def test_empty_location_preferences(self):
        """Test empty location preferences (all optional)"""
        prefs = LocationPreferences()
        assert prefs.remote_keywords == []
        assert prefs.hybrid_keywords == []
        assert prefs.preferred_cities == []
        assert prefs.preferred_regions == []


class TestFiltering:
    """Test Filtering model validation"""

    def test_valid_filtering(self):
        """Test valid filtering configuration"""
        filtering = Filtering(
            aggression_level="moderate",
            software_engineering_avoid=["software engineer", "frontend"],
            hardware_company_boost=10,
            software_company_penalty=-20,
        )
        assert filtering.aggression_level == "moderate"
        assert filtering.hardware_company_boost == 10

    def test_invalid_aggression_level_fails(self):
        """Test invalid aggression level raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Filtering(aggression_level="extreme")
        assert "aggression_level must be one of" in str(exc_info.value)

    def test_boost_out_of_range_fails(self):
        """Test boost value out of range fails"""
        with pytest.raises(ValidationError) as exc_info:
            Filtering(hardware_company_boost=100)
        assert "hardware_company_boost" in str(exc_info.value)

    def test_penalty_out_of_range_fails(self):
        """Test penalty value out of range fails"""
        with pytest.raises(ValidationError) as exc_info:
            Filtering(software_company_penalty=-100)
        assert "software_company_penalty" in str(exc_info.value)


class TestRoleTypes:
    """Test RoleTypes model validation"""

    def test_valid_role_types(self):
        """Test valid role types"""
        roles = RoleTypes(
            engineering_leadership=["engineering", "technical"],
            product_leadership=["product", "cpo"],
            dual_role=["product engineering"],
        )
        assert len(roles.engineering_leadership) == 2
        assert len(roles.product_leadership) == 2

    def test_custom_role_categories_allowed(self):
        """Test custom role categories are allowed (extra='allow')"""
        roles = RoleTypes(custom_category=["custom", "keywords"])
        assert roles.model_extra["custom_category"] == ["custom", "keywords"]


class TestScoring:
    """Test Scoring model validation"""

    def test_valid_scoring_config(self):
        """Test valid scoring configuration"""
        scoring = Scoring(
            target_seniority=["vp", "director"],
            domain_keywords=["robotics", "automation"],
            role_types=RoleTypes(engineering_leadership=["engineering"]),
            company_stage=["series a", "series b"],
            avoid_keywords=["junior"],
            location_preferences=LocationPreferences(remote_keywords=["remote"]),
            filtering=Filtering(aggression_level="moderate"),
        )
        assert len(scoring.target_seniority) == 2
        assert len(scoring.domain_keywords) == 2

    def test_empty_target_seniority_fails(self):
        """Test empty target_seniority raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Scoring(
                target_seniority=[],
                domain_keywords=["robotics"],
                role_types=RoleTypes(engineering_leadership=["engineering"]),
            )
        assert "target_seniority" in str(exc_info.value)
        assert "at least 1 item" in str(exc_info.value)

    def test_empty_domain_keywords_fails(self):
        """Test empty domain_keywords raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Scoring(
                target_seniority=["vp"],
                domain_keywords=[],
                role_types=RoleTypes(engineering_leadership=["engineering"]),
            )
        assert "domain_keywords" in str(exc_info.value)
        assert "at least 1 item" in str(exc_info.value)


class TestDigest:
    """Test Digest model validation"""

    def test_valid_digest_config(self):
        """Test valid digest configuration"""
        digest = Digest(
            min_grade="C",
            min_score=55,
            min_location_score=8,
            include_grades=["A", "B", "C"],
            send_frequency="weekly",
        )
        assert digest.min_grade == "C"
        assert digest.min_score == 55

    def test_invalid_min_grade_fails(self):
        """Test invalid min_grade raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Digest(min_grade="X", min_score=50, include_grades=["A"])
        assert "min_grade must be one of" in str(exc_info.value)

    def test_invalid_include_grade_fails(self):
        """Test invalid grade in include_grades fails"""
        with pytest.raises(ValidationError) as exc_info:
            Digest(min_grade="C", min_score=50, include_grades=["A", "X"])
        assert "include_grades contains invalid grade" in str(exc_info.value)

    def test_score_out_of_range_fails(self):
        """Test min_score out of range fails"""
        with pytest.raises(ValidationError) as exc_info:
            Digest(min_grade="C", min_score=150, include_grades=["A"])
        assert "min_score" in str(exc_info.value)

    def test_invalid_send_frequency_fails(self):
        """Test invalid send_frequency raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Digest(min_grade="C", min_score=50, include_grades=["A"], send_frequency="hourly")
        assert "send_frequency must be one of" in str(exc_info.value)


class TestNotifications:
    """Test Notifications model validation"""

    def test_valid_notifications_config(self):
        """Test valid notifications configuration"""
        notif = Notifications(enabled=True, min_grade="B", min_score=70)
        assert notif.enabled is True
        assert notif.min_grade == "B"

    def test_invalid_min_grade_fails(self):
        """Test invalid min_grade raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            Notifications(enabled=True, min_grade="X", min_score=70)
        assert "min_grade must be one of" in str(exc_info.value)


class TestProfileConfig:
    """Test ProfileConfig model validation"""

    def test_valid_profile_config_with_email_creds(self):
        """Test valid profile configuration with email credentials"""
        config = ProfileConfig(
            id="test_user",
            name="Test User",
            email="test@example.com",
            enabled=True,
            email_credentials=EmailCredentials(
                username="test.jobalerts@gmail.com", app_password_env="TEST_PASSWORD"
            ),
            scoring=Scoring(
                target_seniority=["vp", "director"],
                domain_keywords=["robotics", "automation"],
                role_types=RoleTypes(engineering_leadership=["engineering"]),
            ),
            digest=Digest(min_grade="C", min_score=55, include_grades=["A", "B", "C"]),
            notifications=Notifications(enabled=True, min_grade="B", min_score=70),
        )
        assert config.id == "test_user"
        assert config.name == "Test User"
        assert config.email == "test@example.com"

    def test_valid_profile_config_without_email_creds(self):
        """Test valid profile configuration without email credentials (digest-only)"""
        config = ProfileConfig(
            id="digest_only",
            name="Digest Only User",
            email="digest@example.com",
            enabled=True,
            email_credentials=None,
            scoring=Scoring(
                target_seniority=["director"],
                domain_keywords=["fintech"],
                role_types=RoleTypes(engineering_leadership=["engineering"]),
            ),
            digest=Digest(min_grade="C", min_score=55, include_grades=["A", "B", "C"]),
            notifications=Notifications(enabled=False, min_grade="A", min_score=85),
        )
        assert config.id == "digest_only"
        assert config.email_credentials is None

    def test_empty_id_fails(self):
        """Test empty id raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                id="",
                name="Test",
                email="test@example.com",
                scoring=Scoring(
                    target_seniority=["vp"],
                    domain_keywords=["robotics"],
                    role_types=RoleTypes(engineering_leadership=["engineering"]),
                ),
                digest=Digest(min_grade="C", min_score=55, include_grades=["A"]),
                notifications=Notifications(enabled=False, min_grade="A", min_score=85),
            )
        assert "id" in str(exc_info.value)

    def test_invalid_email_fails(self):
        """Test invalid email raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                id="test",
                name="Test",
                email="invalid-email",
                scoring=Scoring(
                    target_seniority=["vp"],
                    domain_keywords=["robotics"],
                    role_types=RoleTypes(engineering_leadership=["engineering"]),
                ),
                digest=Digest(min_grade="C", min_score=55, include_grades=["A"]),
                notifications=Notifications(enabled=False, min_grade="A", min_score=85),
            )
        assert "email must contain '@'" in str(exc_info.value)


class TestRealProfileValidation:
    """Test validation of real profile configurations"""

    def test_wes_profile_structure(self):
        """Test Wes profile structure validates correctly"""
        config = ProfileConfig(
            id="wes",
            name="Wesley van Ooyen",
            email="wesvanooyen@gmail.com",
            enabled=True,
            email_credentials=EmailCredentials(
                username="Wes.jobalerts@gmail.com", app_password_env="WES_GMAIL_APP_PASSWORD"
            ),
            scoring=Scoring(
                target_seniority=["vp", "director", "head of", "executive", "chief", "cto", "cpo"],
                domain_keywords=[
                    "robotics",
                    "automation",
                    "iot",
                    "hardware",
                    "medtech",
                    "medical device",
                    "mechatronics",
                    "embedded",
                    "firmware",
                    "mechanical",
                    "physical product",
                    "manufacturing",
                    "supply chain",
                    "dfm",
                    "dfa",
                    "industrial",
                ],
                role_types=RoleTypes(
                    engineering_leadership=[
                        "engineering",
                        "r&d",
                        "technical",
                        "hardware",
                        "robotics",
                        "automation",
                    ],
                    product_leadership=[
                        "product manager",
                        "product management",
                        "cpo",
                        "chief product",
                    ],
                    dual_role=["product engineering", "technical product", "hardware product"],
                    operations_leadership=["manufacturing", "operations", "supply chain"],
                ),
                company_stage=["series a", "series b", "series c", "growth", "scale-up", "funded"],
                avoid_keywords=["junior", "associate", "intern", "coordinator"],
                location_preferences=LocationPreferences(
                    remote_keywords=["remote", "work from home", "wfh", "anywhere", "distributed"],
                    hybrid_keywords=["hybrid"],
                    preferred_cities=[
                        "toronto",
                        "waterloo",
                        "burlington",
                        "oakville",
                        "hamilton",
                        "mississauga",
                        "kitchener",
                        "guelph",
                    ],
                    preferred_regions=["ontario", "canada", "greater toronto area", "gta"],
                ),
                filtering=Filtering(
                    aggression_level="moderate",
                    software_engineering_avoid=[
                        "software engineer",
                        "software engineering",
                        "vp of software",
                        "director of software",
                        "frontend",
                        "backend",
                        "full stack",
                    ],
                    hardware_company_boost=10,
                    software_company_penalty=-20,
                ),
                hard_filter_keywords=HardFilterKeywords(
                    seniority_blocks=["junior", "intern", "coordinator"],
                    role_type_blocks=["software engineering", "software engineer"],
                    department_blocks=["finance", "accounting", "legal"],
                    sales_marketing_blocks=["sales manager", "marketing manager"],
                ),
                context_filters=ContextFilters(
                    associate_with_senior=["director", "vp", "principal", "chief"],
                    software_engineering_exceptions=["hardware", "product"],
                    contract_min_seniority_score=25,
                ),
            ),
            digest=Digest(
                min_grade="C",
                min_score=47,
                min_location_score=8,
                include_grades=["A", "B", "C"],
                send_frequency="weekly",
            ),
            notifications=Notifications(enabled=True, min_grade="B", min_score=59),
        )
        assert config.id == "wes"
        assert config.scoring.filtering.aggression_level == "moderate"

    def test_adam_profile_structure(self):
        """Test Adam profile structure validates correctly"""
        config = ProfileConfig(
            id="adam",
            name="Adam White",
            email="adamkwhite@gmail.com",
            enabled=True,
            email_credentials=EmailCredentials(
                username="adamwhite.jobalerts@gmail.com", app_password_env="ADAM_GMAIL_APP_PASSWORD"
            ),
            scoring=Scoring(
                target_seniority=["senior", "staff", "lead", "principal", "architect"],
                domain_keywords=[
                    "software",
                    "fullstack",
                    "backend",
                    "frontend",
                    "web",
                    "cloud",
                    "devops",
                ],
                role_types=RoleTypes(
                    engineering=["software engineer", "developer", "architect"],
                    data=["data engineer", "data scientist", "ml engineer"],
                    devops=["devops", "sre", "platform engineer"],
                    product=["product manager", "product owner", "product lead"],
                ),
                filtering=Filtering(
                    aggression_level="conservative",
                    software_engineering_avoid=[],
                    hardware_company_boost=0,
                    software_company_penalty=0,
                ),
            ),
            digest=Digest(
                min_grade="C", min_score=47, include_grades=["A", "B", "C"], send_frequency="weekly"
            ),
            notifications=Notifications(enabled=True, min_grade="B", min_score=59),
        )
        assert config.id == "adam"
        assert config.scoring.filtering.aggression_level == "conservative"

    def test_eli_profile_structure(self):
        """Test Eli profile structure validates correctly (no email credentials)"""
        config = ProfileConfig(
            id="eli",
            name="Eli Juni",
            email="eliyahu.juni@gmail.com",
            enabled=True,
            email_credentials=None,  # Digest-only profile
            scoring=Scoring(
                target_seniority=["director", "vp", "cto", "chief technology officer", "head of"],
                domain_keywords=[
                    "fintech",
                    "healthtech",
                    "proptech",
                    "observability",
                    "hrtech",
                    "salestech",
                    "edtech",
                    "smb",
                    "saas",
                ],
                role_types=RoleTypes(
                    engineering_leadership=[
                        "engineering",
                        "technical",
                        "cto",
                        "vp engineering",
                        "director engineering",
                    ]
                ),
                filtering=Filtering(
                    aggression_level="moderate",
                    software_engineering_avoid=["software engineer", "software engineering"],
                    hardware_company_boost=0,
                    software_company_penalty=-20,
                ),
            ),
            digest=Digest(
                min_grade="C", min_score=47, include_grades=["A", "B", "C"], send_frequency="weekly"
            ),
            notifications=Notifications(enabled=False, min_grade="B", min_score=59),
        )
        assert config.id == "eli"
        assert config.email_credentials is None
