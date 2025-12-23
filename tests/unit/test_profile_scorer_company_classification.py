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


class TestProfileScorerCompanyClassification:
    """Test suite for CompanyClassifier integration in ProfileScorer"""

    def test_software_company_engineering_role_gets_penalized(self, mock_wes_profile):
        """Test that engineering roles at software companies receive penalty"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }

        # Mock company classification to return software company
        mock_classification = CompanyClassification(
            type="software",
            confidence=0.9,
            signals={
                "curated": {"score": 1.0, "type": "software", "list_match": "software_companies"}
            },
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            score, grade, breakdown, metadata = scorer.score_job(job)

        # Should have software penalty applied
        assert breakdown["company_classification"] == -20
        assert metadata["filtered"] is True
        assert metadata["filter_reason"] == "software_company_moderate_confidence"
        assert metadata["company_type"] == "software"
        assert metadata["confidence"] == 0.9

    def test_hardware_company_engineering_role_gets_boost(self, mock_wes_profile):
        """Test that engineering roles at hardware companies receive boost"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Boston Dynamics",
            "location": "Remote",
        }

        # Mock company classification to return hardware company
        mock_classification = CompanyClassification(
            type="hardware",
            confidence=0.95,
            signals={
                "curated": {"score": 1.0, "type": "hardware", "list_match": "hardware_companies"}
            },
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            score, grade, breakdown, metadata = scorer.score_job(job)

        # Should have hardware boost applied
        assert breakdown["company_classification"] == 10
        assert metadata["filtered"] is False
        assert metadata["hardware_boost_applied"] is True
        assert metadata["company_type"] == "hardware"
        assert metadata["confidence"] == 0.95

    def test_product_role_at_software_company_not_filtered(self, mock_wes_profile):
        """Test that product roles at software companies are NOT filtered"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Product",
            "company": "Stripe",
            "location": "Remote",
        }

        # Mock company classification to return software company
        mock_classification = CompanyClassification(
            type="software",
            confidence=0.9,
            signals={"curated": {"score": 1.0, "type": "software"}},
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            score, grade, breakdown, metadata = scorer.score_job(job)

        # Product roles should NOT be filtered, even at software companies
        assert breakdown["company_classification"] == 0
        assert metadata["filtered"] is False
        assert metadata["filter_reason"] == "product_leadership_any_company"

    def test_dual_domain_company_ambiguous_role(self, mock_wes_profile):
        """Test handling of engineering roles at dual-domain companies (Tesla, Apple)"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "Director of Engineering",
            "company": "Tesla",
            "location": "Remote",
        }

        # Mock company classification to return dual-domain company
        mock_classification = CompanyClassification(
            type="both",
            confidence=0.8,
            signals={"curated": {"score": 1.0, "type": "both"}},
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            score, grade, breakdown, metadata = scorer.score_job(job)

        # Dual-domain without explicit software keywords should NOT be filtered
        assert breakdown["company_classification"] == 0
        assert metadata["filtered"] is False
        assert metadata["filter_reason"] == "dual_domain_ambiguous"

    def test_unknown_company_no_adjustment(self, mock_wes_profile):
        """Test that unknown companies receive no filtering adjustment"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Unknown Startup Inc",
            "location": "Remote",
        }

        # Mock company classification to return unknown
        mock_classification = CompanyClassification(
            type="unknown",
            confidence=0.2,
            signals={},
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            score, grade, breakdown, metadata = scorer.score_job(job)

        # Unknown companies should have no adjustment
        assert breakdown["company_classification"] == 0
        assert metadata["filtered"] is False

    def test_classification_metadata_stored(self, mock_wes_profile):
        """Test that classification metadata is properly stored"""
        scorer = ProfileScorer(mock_wes_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }

        mock_classification = CompanyClassification(
            type="software",
            confidence=0.85,
            signals={
                "name": {"score": 0.8, "type": "software", "matched_keywords": ["software"]},
                "curated": {"score": 1.0, "type": "software", "list_match": "software_companies"},
            },
            source="auto",
        )

        with patch.object(
            scorer.company_classifier, "classify_company", return_value=mock_classification
        ):
            _, _, _, metadata = scorer.score_job(job)

        # Verify all metadata fields are present
        assert "company_type" in metadata
        assert "confidence" in metadata
        assert "signals" in metadata
        assert "source" in metadata
        assert "filtered" in metadata
        assert "filter_reason" in metadata
        assert metadata["company_type"] == "software"
        assert metadata["confidence"] == 0.85
        assert metadata["source"] == "auto"

    def test_conservative_aggression_only_filters_explicit_software(self, mock_wes_profile):
        """Test conservative mode only filters explicit software engineering titles"""
        # Update profile to use conservative mode
        mock_wes_profile.scoring["filtering"]["aggression_level"] = "conservative"

        scorer = ProfileScorer(mock_wes_profile)

        # Generic "VP Engineering" at software company
        job1 = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }

        # Explicit "VP of Software Engineering"
        job2 = {
            "title": "VP of Software Engineering",
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
        ):
            _, _, breakdown1, metadata1 = scorer.score_job(job1)
            _, _, breakdown2, metadata2 = scorer.score_job(job2)

        # Generic "VP Engineering" should NOT be filtered in conservative mode
        assert breakdown1["company_classification"] == 0
        assert metadata1["filtered"] is False

        # Explicit "VP Software Engineering" SHOULD be filtered
        assert breakdown2["company_classification"] == -20
        assert metadata2["filtered"] is True
        assert metadata2["filter_reason"] == "software_engineering_explicit_conservative"

    def test_aggressive_mode_filters_any_engineering_without_hardware_keywords(
        self, mock_wes_profile
    ):
        """Test aggressive mode filters any engineering role without hardware keywords"""
        # Update profile to use aggressive mode
        mock_wes_profile.scoring["filtering"]["aggression_level"] = "aggressive"

        scorer = ProfileScorer(mock_wes_profile)

        # Generic engineering role (no hardware keywords)
        job1 = {
            "title": "VP of Engineering",
            "company": "Some Company",
            "location": "Remote",
        }

        # Engineering role with hardware keywords
        job2 = {
            "title": "VP of Hardware Engineering",
            "company": "Some Company",
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
        ):
            _, _, breakdown1, metadata1 = scorer.score_job(job1)
            _, _, breakdown2, metadata2 = scorer.score_job(job2)

        # Generic engineering should be filtered in aggressive mode
        assert breakdown1["company_classification"] == -20
        assert metadata1["filtered"] is True
        assert metadata1["filter_reason"] == "no_hardware_keywords_aggressive"

        # Hardware engineering should NOT be filtered
        assert breakdown2["company_classification"] == 0
        assert metadata2["filtered"] is False

    def test_company_classifier_caching(self, mock_wes_profile):
        """Test that CompanyClassifier caching works correctly"""
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
            # Score the same job twice
            scorer.score_job(job)
            scorer.score_job(job)

            # classify_company should be called twice (ProfileScorer doesn't cache, but CompanyClassifier does internally)
            assert mock_classify.call_count == 2
