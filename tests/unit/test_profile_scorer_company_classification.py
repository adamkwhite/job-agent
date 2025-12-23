"""
Unit tests for ProfileScorer with CompanyClassifier integration

Tests company classification, filtering logic, and scoring adjustments.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.profile_scorer import ProfileScorer
from utils.company_classifier import CompanyClassification
from utils.profile_manager import Profile


@pytest.fixture
def mock_wes_profile():
    """Create a mock Wes profile with filtering config"""
    profile = MagicMock(spec=Profile)
    profile.id = "wes"
    profile.name = "Wesley van Ooyen"
    profile.scoring = {
        "target_seniority": ["vp", "director", "head of"],
        "domain_keywords": ["robotics", "automation", "hardware", "mechatronics"],
        "role_types": {
            "engineering_leadership": ["engineering", "r&d", "technical"],
            "product_leadership": ["product", "cpo"],
            "dual_role": ["product engineering"],
        },
        "filtering": {
            "aggression_level": "moderate",
            "software_engineering_avoid": ["software engineer", "software engineering"],
            "hardware_company_boost": 10,
            "software_company_penalty": -20,
        },
    }
    profile.get_target_seniority = lambda: ["vp", "director", "head of"]
    profile.get_domain_keywords = lambda: ["robotics", "automation", "hardware"]
    profile.get_location_preferences = lambda: {
        "remote_keywords": ["remote"],
        "preferred_cities": ["toronto"],
        "preferred_regions": ["ontario"],
    }
    return profile


def score_job_with_classification(
    profile,
    job_title,
    company_name,
    company_type,
    confidence,
    signals=None,
):
    """Helper to score a job with mocked company classification"""
    scorer = ProfileScorer(profile)

    job = {
        "title": job_title,
        "company": company_name,
        "location": "Remote",
    }

    mock_classification = CompanyClassification(
        type=company_type,
        confidence=confidence,
        signals=signals or {},
        source="auto",
    )

    with patch.object(
        scorer.company_classifier, "classify_company", return_value=mock_classification
    ):
        return scorer.score_job(job)


class TestProfileScorerCompanyClassification:
    """Test suite for CompanyClassifier integration in ProfileScorer"""

    @pytest.mark.parametrize(
        "company_type,confidence,expected_adjustment,expected_filtered",
        [
            ("software", 0.9, -20, True),  # Software penalty
            ("hardware", 0.95, 10, False),  # Hardware boost
            ("unknown", 0.2, 0, False),  # No adjustment
            ("both", 0.8, 0, False),  # Dual-domain, ambiguous
        ],
    )
    def test_company_type_adjustments(
        self, mock_wes_profile, company_type, confidence, expected_adjustment, expected_filtered
    ):
        """Test that different company types receive appropriate score adjustments"""
        _, _, breakdown, metadata = score_job_with_classification(
            mock_wes_profile,
            "VP of Engineering",
            "Test Company",
            company_type,
            confidence,
        )

        assert breakdown["company_classification"] == expected_adjustment
        assert metadata["filtered"] == expected_filtered
        assert metadata["company_type"] == company_type
        assert metadata["confidence"] == confidence

    def test_product_role_at_software_company_not_filtered(self, mock_wes_profile):
        """Test that product roles at software companies are NOT filtered"""
        _, _, breakdown, metadata = score_job_with_classification(
            mock_wes_profile,
            "VP of Product",
            "Stripe",
            "software",
            0.9,
        )

        assert breakdown["company_classification"] == 0
        assert metadata["filtered"] is False
        assert metadata["filter_reason"] == "product_leadership_any_company"

    def test_classification_metadata_stored(self, mock_wes_profile):
        """Test that classification metadata is properly stored"""
        signals = {
            "name": {"score": 0.8, "type": "software", "matched_keywords": ["software"]},
            "curated": {"score": 1.0, "type": "software", "list_match": "software_companies"},
        }

        _, _, _, metadata = score_job_with_classification(
            mock_wes_profile,
            "VP of Engineering",
            "Stripe",
            "software",
            0.85,
            signals=signals,
        )

        assert metadata["company_type"] == "software"
        assert metadata["confidence"] == 0.85
        assert metadata["source"] == "auto"
        assert metadata["signals"] == signals
        assert all(
            key in metadata
            for key in [
                "company_type",
                "confidence",
                "signals",
                "source",
                "filtered",
                "filter_reason",
            ]
        )

    @pytest.mark.parametrize(
        "aggression_level,job_title,expected_filtered,expected_reason",
        [
            ("conservative", "VP of Engineering", False, None),  # Not filtered
            (
                "conservative",
                "VP of Software Engineering",
                True,
                "software_engineering_explicit_conservative",
            ),
            ("aggressive", "VP of Engineering", True, "no_hardware_keywords_aggressive"),
            ("aggressive", "VP of Hardware Engineering", False, None),  # Hardware keyword saves it
        ],
    )
    def test_aggression_levels(
        self, mock_wes_profile, aggression_level, job_title, expected_filtered, expected_reason
    ):
        """Test filtering behavior across different aggression levels"""
        mock_wes_profile.scoring["filtering"]["aggression_level"] = aggression_level

        _, _, breakdown, metadata = score_job_with_classification(
            mock_wes_profile,
            job_title,
            "Test Company",
            "software",
            0.9,
        )

        assert metadata["filtered"] == expected_filtered
        if expected_filtered:
            assert breakdown["company_classification"] == -20
            assert metadata["filter_reason"] == expected_reason
        else:
            # Either 0 (no adjustment) or positive (hardware boost)
            assert breakdown["company_classification"] >= 0

    def test_hardware_boost_metadata(self, mock_wes_profile):
        """Test that hardware boost metadata is properly set"""
        _, _, breakdown, metadata = score_job_with_classification(
            mock_wes_profile,
            "VP of Engineering",
            "Boston Dynamics",
            "hardware",
            0.95,
        )

        assert breakdown["company_classification"] == 10
        assert metadata["hardware_boost_applied"] is True
        assert metadata["filtered"] is False

    def test_company_classifier_caching(self, mock_wes_profile):
        """Test that CompanyClassifier is called for each score_job invocation"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }

        mock_classification = CompanyClassification(
            type="software",
            confidence=0.9,
            signals={},
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ) as mock_classify:
            scorer.score_job(job)
            scorer.score_job(job)

            # ProfileScorer doesn't cache, but CompanyClassifier does internally
            assert mock_classify.call_count == 2
