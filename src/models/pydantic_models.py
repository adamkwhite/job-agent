"""
Pydantic Models for Profile Configuration Validation

This module provides type-safe validation for user profile configurations using Pydantic v2.
Validates profile JSON files on load to ensure data integrity and catch configuration errors early.

Key Validations:
- Required fields are present and non-empty
- Valid types and ranges (scores 0-110, grades A-F)
- Valid aggression levels (conservative, moderate, aggressive)
- Email credentials are properly structured
"""

from typing import Any

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class EmailCredentials(BaseModel):
    """Email credentials configuration"""

    username: str = Field(
        ..., min_length=1, description="Email username (e.g., user.jobalerts@gmail.com)"
    )
    app_password_env: str = Field(
        ..., min_length=1, description="Environment variable name for app password"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is not just whitespace"""
        if not v.strip():
            raise ValueError("username cannot be empty or whitespace")
        return v

    @field_validator("app_password_env")
    @classmethod
    def validate_app_password_env(cls, v: str) -> str:
        """Ensure app_password_env is not just whitespace"""
        if not v.strip():
            raise ValueError("app_password_env cannot be empty or whitespace")
        return v


class LocationPreferences(BaseModel):
    """Location preferences configuration"""

    remote_keywords: list[str] = Field(
        default_factory=list, description="Keywords indicating remote work"
    )
    hybrid_keywords: list[str] = Field(
        default_factory=list, description="Keywords indicating hybrid work"
    )
    preferred_cities: list[str] = Field(default_factory=list, description="Preferred cities")
    preferred_regions: list[str] = Field(default_factory=list, description="Preferred regions")


class Filtering(BaseModel):
    """Company classification filtering configuration"""

    aggression_level: str = Field(
        default="moderate",
        description="Filtering aggression level (conservative, moderate, aggressive)",
    )
    software_engineering_avoid: list[str] = Field(
        default_factory=list, description="Software engineering keywords to avoid"
    )
    hardware_company_boost: int = Field(
        default=0, ge=-50, le=50, description="Score boost for hardware companies"
    )
    software_company_penalty: int = Field(
        default=0, ge=-50, le=50, description="Score penalty for software companies"
    )

    @field_validator("aggression_level")
    @classmethod
    def validate_aggression_level(cls, v: str) -> str:
        """Validate aggression level is one of the allowed values"""
        allowed = ["conservative", "moderate", "aggressive"]
        if v not in allowed:
            raise ValueError(f"aggression_level must be one of {allowed}, got '{v}'")
        return v


class HardFilterKeywords(BaseModel):
    """Hard filter keywords configuration"""

    seniority_blocks: list[str] = Field(
        default_factory=list, description="Seniority levels to block"
    )
    role_type_blocks: list[str] = Field(default_factory=list, description="Role types to block")
    department_blocks: list[str] = Field(default_factory=list, description="Departments to block")
    sales_marketing_blocks: list[str] = Field(
        default_factory=list, description="Sales/marketing roles to block"
    )
    exceptions: dict[str, Any] = Field(
        default_factory=dict, description="Exceptions to hard filters"
    )


class ContextFilters(BaseModel):
    """Context filters configuration"""

    associate_with_senior: list[str] = Field(
        default_factory=list, description="Senior keywords for associate context"
    )
    software_engineering_exceptions: list[str] = Field(
        default_factory=list, description="Keywords that override software engineering filter"
    )
    contract_min_seniority_score: int = Field(
        default=0, ge=0, le=30, description="Minimum seniority score for contract roles"
    )


class RoleTypes(BaseModel):
    """Role types configuration - flexible dictionary of role categories"""

    model_config = {"extra": "allow"}  # Allow any additional role categories

    # Common role categories (optional)
    engineering_leadership: list[str] = Field(
        default_factory=list, description="Engineering leadership keywords"
    )
    product_leadership: list[str] = Field(
        default_factory=list, description="Product leadership keywords"
    )
    dual_role: list[str] = Field(default_factory=list, description="Dual role keywords")
    operations_leadership: list[str] = Field(
        default_factory=list, description="Operations leadership keywords"
    )


class Scoring(BaseModel):
    """Scoring configuration"""

    target_seniority: list[str] = Field(..., min_length=1, description="Target seniority levels")
    domain_keywords: list[str] = Field(..., min_length=1, description="Domain keywords")
    role_types: RoleTypes = Field(..., description="Role type keywords")
    company_stage: list[str] = Field(default_factory=list, description="Preferred company stages")
    avoid_keywords: list[str] = Field(default_factory=list, description="Keywords to avoid")
    location_preferences: LocationPreferences = Field(
        default_factory=LocationPreferences, description="Location preferences"
    )
    filtering: Filtering = Field(
        default_factory=Filtering, description="Company classification filtering"
    )
    hard_filter_keywords: HardFilterKeywords | None = Field(
        default=None, description="Hard filter keywords (optional)"
    )
    context_filters: ContextFilters | None = Field(
        default=None, description="Context filters (optional)"
    )

    @field_validator("target_seniority")
    @classmethod
    def validate_target_seniority(cls, v: list[str]) -> list[str]:
        """Ensure at least one seniority level is specified"""
        if not v:
            raise ValueError("target_seniority must contain at least one seniority level")
        return v

    @field_validator("domain_keywords")
    @classmethod
    def validate_domain_keywords(cls, v: list[str]) -> list[str]:
        """Ensure at least one domain keyword is specified"""
        if not v:
            raise ValueError("domain_keywords must contain at least one keyword")
        return v


class Digest(BaseModel):
    """Digest configuration"""

    min_grade: str = Field(..., description="Minimum grade for digest inclusion")
    min_score: int = Field(..., ge=0, le=110, description="Minimum score for digest inclusion")
    min_location_score: int = Field(default=0, ge=0, le=15, description="Minimum location score")
    include_grades: list[str] = Field(..., min_length=1, description="Grades to include in digest")
    send_frequency: str = Field(default="weekly", description="Digest send frequency")

    @field_validator("min_grade")
    @classmethod
    def validate_min_grade(cls, v: str) -> str:
        """Validate min_grade is a valid grade"""
        valid_grades = ["A", "B", "C", "D", "F"]
        if v not in valid_grades:
            raise ValueError(f"min_grade must be one of {valid_grades}, got '{v}'")
        return v

    @field_validator("include_grades")
    @classmethod
    def validate_include_grades(cls, v: list[str]) -> list[str]:
        """Validate all grades are valid"""
        valid_grades = ["A", "B", "C", "D", "F"]
        for grade in v:
            if grade not in valid_grades:
                raise ValueError(
                    f"include_grades contains invalid grade '{grade}', must be one of {valid_grades}"
                )
        return v

    @field_validator("send_frequency")
    @classmethod
    def validate_send_frequency(cls, v: str) -> str:
        """Validate send_frequency is a recognized value"""
        valid_frequencies = ["daily", "weekly", "biweekly", "monthly"]
        if v not in valid_frequencies:
            raise ValueError(f"send_frequency must be one of {valid_frequencies}, got '{v}'")
        return v


class Notifications(BaseModel):
    """Notifications configuration"""

    enabled: bool = Field(default=False, description="Whether notifications are enabled")
    min_grade: str = Field(..., description="Minimum grade for notifications")
    min_score: int = Field(..., ge=0, le=110, description="Minimum score for notifications")

    @field_validator("min_grade")
    @classmethod
    def validate_min_grade(cls, v: str) -> str:
        """Validate min_grade is a valid grade"""
        valid_grades = ["A", "B", "C", "D", "F"]
        if v not in valid_grades:
            raise ValueError(f"min_grade must be one of {valid_grades}, got '{v}'")
        return v


class ProfileConfig(BaseModel):
    """
    Complete profile configuration model with comprehensive validation.

    This model validates all aspects of a user profile configuration:
    - User identity (id, name, email)
    - Email credentials
    - Scoring preferences
    - Digest settings
    - Notification preferences

    Raises:
        ValidationError: If any field fails validation
    """

    id: str = Field(..., min_length=1, description="Profile ID")
    name: str = Field(..., min_length=1, description="User's full name")
    email: str = Field(..., min_length=1, description="User's email address")
    enabled: bool = Field(default=True, description="Whether profile is enabled")

    email_credentials: EmailCredentials | None = Field(
        default=None, description="Email credentials (optional)"
    )
    scoring: Scoring = Field(..., description="Scoring configuration")
    digest: Digest = Field(..., description="Digest configuration")
    notifications: Notifications = Field(..., description="Notification configuration")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is not just whitespace"""
        if not v.strip():
            raise ValueError("id cannot be empty or whitespace")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace"""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation"""
        if not v.strip():
            raise ValueError("email cannot be empty or whitespace")
        if "@" not in v:
            raise ValueError(f"email must contain '@', got '{v}'")
        return v
