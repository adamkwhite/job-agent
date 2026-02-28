"""
Pytest configuration for unit tests
"""

import copy
import sys
from pathlib import Path

import pytest

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from utils.profile_manager import Profile  # noqa: E402


def _build_wes_profile() -> Profile:
    """Build Wes's profile inline for CI-safe testing (profiles/ is gitignored)"""
    return Profile(
        id="wes",
        name="Wesley van Ooyen",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": [
                "vp",
                "director",
                "head of",
                "executive",
                "chief",
                "cto",
                "cpo",
            ],
            "domain_keywords": [
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
            "role_types": {
                "engineering_leadership": [
                    "engineering",
                    "r&d",
                    "technical",
                    "hardware",
                    "robotics",
                    "automation",
                    "mechatronics",
                ],
                "product_leadership": [
                    "product manager",
                    "product management",
                    "cpo",
                    "chief product",
                ],
                "dual_role": [
                    "product engineering",
                    "technical product",
                    "hardware product",
                ],
                "operations_leadership": [
                    "manufacturing",
                    "operations",
                    "supply chain",
                ],
            },
            "company_stage": [
                "series a",
                "series b",
                "series c",
                "growth",
                "scale-up",
                "funded",
            ],
            "candidate_country": "canada",
            "domain_tiers": {
                "tier1": ["robotics", "automation", "hardware", "iot", "mechatronics", "embedded"],
                "tier2": ["medtech", "medical device", "healthcare", "pharma"],
                "tier3": ["manufacturing", "supply chain", "industrial", "mechanical"],
            },
            "technical_keywords": [
                "robotics",
                "automation",
                "iot",
                "hardware",
                "embedded",
                "firmware",
                "mechanical",
                "mechatronics",
                "manufacturing",
                "supply chain",
                "dfm",
                "industrial",
                "ml",
                "ai",
            ],
            "avoid_keywords": ["junior", "associate", "intern", "coordinator"],
            "location_preferences": {
                "remote_keywords": ["remote", "work from home", "wfh", "anywhere", "distributed"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": [
                    "toronto",
                    "waterloo",
                    "burlington",
                    "oakville",
                    "hamilton",
                    "mississauga",
                    "kitchener",
                    "guelph",
                ],
                "preferred_regions": [
                    "ontario",
                    "canada",
                    "greater toronto area",
                    "gta",
                ],
                "country_restriction_enabled": True,
            },
            "filtering": {
                "aggression_level": "moderate",
                "software_engineering_avoid": [
                    "software engineer",
                    "software engineering",
                    "vp of software",
                    "director of software",
                    "frontend",
                    "backend",
                    "full stack",
                    "web developer",
                    "mobile app",
                    "devops",
                    "cloud engineer",
                    "saas",
                    "fintech software",
                ],
                "hardware_company_boost": 10,
                "software_company_penalty": -20,
                "role_software_penalty": -5,
            },
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
                    "software engineering",
                    "software engineer",
                    "ui & ux",
                    "ui/ux",
                    "user interface",
                    "user experience",
                    "frontend",
                    "backend",
                    "full stack",
                    "web development",
                    "mobile development",
                    "app development",
                    "serverless",
                    "saas platform",
                    "cloud platform",
                    "platform engineering",
                    "infrastructure engineering",
                ],
                "department_blocks": [
                    "finance",
                    "accounting",
                    "legal",
                    "compliance",
                    "marketing",
                ],
                "sales_marketing_blocks": [
                    "sales manager",
                    "marketing manager",
                    "business development",
                    "product marketing",
                    "marketing operations",
                    "marketing strategy",
                    "marketing platform",
                    "head of marketing",
                    "director of marketing",
                    "vp of marketing",
                    "chief marketing",
                    "cmo",
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
        },
        digest_min_grade="D",
        digest_min_score=47,
        digest_min_location_score=8,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=True,
        notifications_min_grade="C",
        notifications_min_score=59,
    )


def _build_mario_profile() -> Profile:
    """Build Mario's profile inline for CI-safe testing"""
    return Profile(
        id="mario",
        name="Mario",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
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
        },
        digest_min_grade="C",
        digest_min_score=55,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="B",
        notifications_min_score=70,
    )


# Build profiles once, then deep copy per test
_INLINE_PROFILES = {
    "wes": _build_wes_profile,
    "mario": _build_mario_profile,
}


@pytest.fixture
def wes_profile():
    """Wes profile fixture — deep copied for test isolation"""
    return copy.deepcopy(_build_wes_profile())


@pytest.fixture(autouse=True)
def _patch_profile_manager_for_ci():
    """Patch get_profile_manager to return inline profiles when profiles/ is gitignored in CI"""
    from utils.profile_manager import get_profile_manager

    pm = get_profile_manager()
    if pm._profiles:
        # Real profiles exist (local dev), no patching needed
        return

    # CI environment: inject inline profiles into the manager
    for profile_id, builder in _INLINE_PROFILES.items():
        pm._profiles[profile_id] = builder()
