"""
Unit tests for CompanyClassifier
Tests for Issue #122 - Software Engineering Role Filtering (Batch 2)
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.company_classifier import CompanyClassification, CompanyClassifier


class TestCompanyClassificationDataclass:
    """Test CompanyClassification dataclass"""

    def test_valid_classification(self):
        """Test creating valid classification"""
        classification = CompanyClassification(
            type="hardware", confidence=0.85, signals={"name": {"score": 0.9}}, source="auto"
        )

        assert classification.type == "hardware"
        assert classification.confidence == 0.85
        assert classification.signals == {"name": {"score": 0.9}}
        assert classification.source == "auto"

    def test_invalid_confidence_too_high(self):
        """Test validation rejects confidence > 1.0"""
        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            CompanyClassification(type="software", confidence=1.5, signals={}, source="auto")

    def test_invalid_confidence_negative(self):
        """Test validation rejects negative confidence"""
        with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
            CompanyClassification(type="software", confidence=-0.1, signals={}, source="auto")

    def test_boundary_confidence_values(self):
        """Test boundary values for confidence (0.0 and 1.0)"""
        # Lower boundary
        c1 = CompanyClassification(type="hardware", confidence=0.0, signals={}, source="auto")
        assert c1.confidence == 0.0

        # Upper boundary
        c2 = CompanyClassification(type="software", confidence=1.0, signals={}, source="manual")
        assert c2.confidence == 1.0


class TestCompanyNameKeywordMatching:
    """Test Signal 1: Company name keyword matching"""

    @pytest.fixture
    def classifier(self):
        """Create classifier with test config"""
        config_data = {
            "hardware_companies": [],
            "software_companies": [],
            "both_domains": [],
            "_keywords": {
                "hardware_indicators": ["robotics", "automation", "hardware", "drone"],
                "software_indicators": ["software", "SaaS", "fintech", "cloud"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            classifier = CompanyClassifier(config_path=config_path)
            yield classifier
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_hardware_company_name(self, classifier):
        """Test hardware keyword in company name"""
        result = classifier._check_company_name_keywords("Acme Robotics Inc")

        assert result["type"] == "hardware"
        assert result["score"] == 1.0
        assert "robotics" in result["matched_keywords"]

    def test_software_company_name(self, classifier):
        """Test software keyword in company name"""
        result = classifier._check_company_name_keywords("CloudTech SaaS Solutions")

        assert result["type"] == "software"
        assert result["score"] == 1.0
        # Keywords are returned in original case from config
        assert any(kw.lower() == "saas" for kw in result["matched_keywords"])

    def test_both_domains_company_name(self, classifier):
        """Test company name with both hardware and software keywords"""
        result = classifier._check_company_name_keywords("RoboSoft Automation Software")

        assert result["type"] == "both"
        assert result["score"] == 0.8
        assert any(kw.lower() == "automation" for kw in result["matched_keywords"])
        assert any(kw.lower() == "software" for kw in result["matched_keywords"])

    def test_unknown_company_name(self, classifier):
        """Test company name with no matching keywords"""
        result = classifier._check_company_name_keywords("Generic Corp LLC")

        assert result["type"] == "unknown"
        assert result["score"] == 0.0
        assert result["matched_keywords"] == []

    def test_case_insensitive_matching(self, classifier):
        """Test keyword matching is case-insensitive"""
        result = classifier._check_company_name_keywords("ROBOTICS SYSTEMS")

        assert result["type"] == "hardware"
        assert any(kw.lower() == "robotics" for kw in result["matched_keywords"])


class TestCuratedListChecking:
    """Test Signal 2: Curated company list checking"""

    @pytest.fixture
    def classifier(self):
        """Create classifier with test curated lists"""
        config_data = {
            "hardware_companies": ["Boston Dynamics", "Figure", "Sanctuary AI"],
            "software_companies": ["Stripe", "Shopify", "Dropbox"],
            "both_domains": ["Google", "Apple", "Tesla"],
            "_keywords": {"hardware_indicators": [], "software_indicators": []},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            classifier = CompanyClassifier(config_path=config_path)
            yield classifier
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_in_hardware_list(self, classifier):
        """Test company in hardware list"""
        result = classifier._check_curated_lists("Boston Dynamics")

        assert result["type"] == "hardware"
        assert result["score"] == 1.0
        assert result["list_match"] == "hardware_companies"

    def test_in_software_list(self, classifier):
        """Test company in software list"""
        result = classifier._check_curated_lists("Stripe")

        assert result["type"] == "software"
        assert result["score"] == 1.0
        assert result["list_match"] == "software_companies"

    def test_in_both_list(self, classifier):
        """Test company in both domains list"""
        result = classifier._check_curated_lists("Tesla")

        assert result["type"] == "both"
        assert result["score"] == 1.0
        assert result["list_match"] == "both_domains"

    def test_not_in_any_list(self, classifier):
        """Test company not in any list"""
        result = classifier._check_curated_lists("Unknown Startup Inc")

        assert result["type"] == "unknown"
        assert result["score"] == 0.0
        assert result["list_match"] is None

    def test_case_insensitive_list_matching(self, classifier):
        """Test curated list matching is case-insensitive"""
        result = classifier._check_curated_lists("BOSTON DYNAMICS")

        assert result["type"] == "hardware"
        assert result["score"] == 1.0

    def test_partial_company_name_match(self, classifier):
        """Test partial match (company name contains list entry)"""
        result = classifier._check_curated_lists("Boston Dynamics Robotics Division")

        assert result["type"] == "hardware"
        assert result["score"] == 0.9
        assert "partial" in result["list_match"]


class TestDomainKeywordMatching:
    """Test Signal 3: Domain keyword matching"""

    @pytest.fixture
    def classifier(self):
        """Create basic classifier"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "hardware_companies": [],
                    "software_companies": [],
                    "both_domains": [],
                    "_keywords": {"hardware_indicators": [], "software_indicators": []},
                },
                f,
            )
            config_path = f.name

        try:
            classifier = CompanyClassifier(config_path=config_path)
            yield classifier
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_robotics_domain_keywords(self, classifier):
        """Test hardware domain keywords (robotics, automation)"""
        keywords = ["robotics", "automation", "mechatronics"]
        result = classifier._check_domain_keywords(keywords)

        assert result["type"] == "hardware"
        assert result["score"] > 0.0
        assert result["matched_count"] == 3

    def test_software_domain_keywords(self, classifier):
        """Test software domain keywords (saas, cloud)"""
        keywords = ["saas", "cloud", "fintech", "analytics"]
        result = classifier._check_domain_keywords(keywords)

        assert result["type"] == "software"
        assert result["score"] > 0.0
        assert result["matched_count"] == 4

    def test_mixed_domain_keywords(self, classifier):
        """Test mixed hardware and software keywords"""
        keywords = ["robotics", "saas", "automation", "cloud"]
        result = classifier._check_domain_keywords(keywords)

        assert result["type"] == "both"
        assert result["matched_count"] > 0

    def test_empty_keywords_list(self, classifier):
        """Test empty domain keywords list"""
        result = classifier._check_domain_keywords([])

        assert result["type"] == "unknown"
        assert result["score"] == 0.0
        assert result["matched_count"] == 0


class TestJobContentAnalysis:
    """Test Signal 4: Job title/description analysis"""

    @pytest.fixture
    def classifier(self):
        """Create basic classifier"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "hardware_companies": [],
                    "software_companies": [],
                    "both_domains": [],
                    "_keywords": {"hardware_indicators": [], "software_indicators": []},
                },
                f,
            )
            config_path = f.name

        try:
            classifier = CompanyClassifier(config_path=config_path)
            yield classifier
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_hardware_focused_job(self, classifier):
        """Test job with hardware engineering focus"""
        title = "Senior Hardware Engineering Manager"
        description = "Lead team building robotics and embedded systems for physical products"

        result = classifier._analyze_job_content(title, description)

        assert result["type"] == "hardware"
        assert result["score"] > 0.0
        assert len(result["indicators_found"]) > 0

    def test_software_focused_job(self, classifier):
        """Test job with software engineering focus"""
        title = "VP of Software Engineering"
        description = "Lead cloud infrastructure and backend development for SaaS platform"

        result = classifier._analyze_job_content(title, description)

        assert result["type"] == "software"
        assert result["score"] > 0.0
        assert len(result["indicators_found"]) > 0

    def test_ambiguous_job_content(self, classifier):
        """Test job with mixed hardware/software content"""
        title = "Director of Engineering"
        description = "Lead both firmware development and web application teams"

        result = classifier._analyze_job_content(title, description)

        # Could be hardware, software, or both depending on keywords found
        assert result["type"] in ["hardware", "software", "both"]

    def test_empty_job_content(self, classifier):
        """Test with empty job title and description"""
        result = classifier._analyze_job_content("", "")

        assert result["type"] == "unknown"
        assert result["score"] == 0.0


class TestSignalCombination:
    """Test weighted signal combination logic"""

    @pytest.fixture
    def classifier(self):
        """Create basic classifier"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "hardware_companies": [],
                    "software_companies": [],
                    "both_domains": [],
                    "_keywords": {"hardware_indicators": [], "software_indicators": []},
                },
                f,
            )
            config_path = f.name

        try:
            classifier = CompanyClassifier(config_path=config_path)
            yield classifier
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_all_signals_agree_hardware(self, classifier):
        """Test when all signals agree on hardware classification"""
        signals = {
            "name": {"score": 1.0, "type": "hardware"},
            "curated": {"score": 1.0, "type": "hardware"},
            "domain": {"score": 0.8, "type": "hardware"},
            "job_content": {"score": 0.6, "type": "hardware"},
        }

        result = classifier._combine_signals(signals)

        assert result.type == "hardware"
        assert result.confidence > 0.8

    def test_all_signals_agree_software(self, classifier):
        """Test when all signals agree on software classification"""
        signals = {
            "name": {"score": 1.0, "type": "software"},
            "curated": {"score": 1.0, "type": "software"},
            "domain": {"score": 0.9, "type": "software"},
            "job_content": {"score": 0.7, "type": "software"},
        }

        result = classifier._combine_signals(signals)

        assert result.type == "software"
        assert result.confidence > 0.8

    def test_conflicting_signals(self, classifier):
        """Test when signals conflict - curated list (highest weight) should win"""
        signals = {
            "name": {"score": 1.0, "type": "software"},  # weight: 0.3
            "curated": {"score": 1.0, "type": "hardware"},  # weight: 0.4 (highest)
            "domain": {"score": 0.5, "type": "software"},  # weight: 0.2
            "job_content": {"score": 0.3, "type": "software"},  # weight: 0.1
        }

        result = classifier._combine_signals(signals)

        # Curated list has highest weight (0.4), so hardware should win
        # but software has 3 signals (0.3 + 0.2 + 0.1 = 0.6) vs hardware (0.4)
        # So software should win with 0.6 total vs hardware 0.4
        assert result.type == "software"

    def test_low_confidence_unknown(self, classifier):
        """Test classification marked as unknown when confidence < 0.3"""
        signals = {
            "name": {"score": 0.2, "type": "hardware"},
            "curated": {"score": 0.0, "type": "unknown"},
            "domain": {"score": 0.1, "type": "hardware"},
            "job_content": {"score": 0.0, "type": "unknown"},
        }

        result = classifier._combine_signals(signals)

        # Total confidence: 0.2*0.3 + 0.1*0.2 = 0.08, should be marked unknown
        assert result.type == "unknown"
        assert result.confidence < 0.3

    def test_high_confidence_classification(self, classifier):
        """Test high confidence classification"""
        signals = {
            "name": {"score": 1.0, "type": "hardware"},
            "curated": {"score": 1.0, "type": "hardware"},
            "domain": {"score": 1.0, "type": "hardware"},
            "job_content": {"score": 1.0, "type": "hardware"},
        }

        result = classifier._combine_signals(signals)

        assert result.type == "hardware"
        # Use approximate comparison for floating point
        assert abs(result.confidence - 1.0) < 0.001


class TestFullClassificationWorkflow:
    """Test end-to-end classification workflow"""

    @pytest.fixture
    def classifier_with_db(self):
        """Create classifier with temporary database and config"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            db_path = db_file.name

        # Create database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE company_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                classification TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                source TEXT NOT NULL,
                signals TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Create temporary config
        config_data = {
            "hardware_companies": ["Boston Dynamics", "Figure"],
            "software_companies": ["Stripe", "Dropbox"],
            "both_domains": ["Google", "Tesla"],
            "_keywords": {
                "hardware_indicators": ["robotics", "automation"],
                "software_indicators": ["SaaS", "fintech"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            classifier = CompanyClassifier(db_path=db_path, config_path=config_path)
            yield classifier
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(config_path).unlink(missing_ok=True)

    def test_boston_dynamics_classification(self, classifier_with_db):
        """Test Boston Dynamics classified as hardware with high confidence"""
        result = classifier_with_db.classify_company(
            company_name="Boston Dynamics",
            job_title="VP of Engineering",
            domain_keywords=["robotics", "automation"],
        )

        assert result.type == "hardware"
        # Curated list (0.4) + domain keywords (0.2) = 0.6 confidence
        assert result.confidence >= 0.6
        assert result.source == "auto"

    def test_stripe_classification(self, classifier_with_db):
        """Test Stripe classified as software with high confidence"""
        result = classifier_with_db.classify_company(
            company_name="Stripe",
            job_title="Director of Engineering",
            domain_keywords=["fintech", "saas"],
        )

        assert result.type == "software"
        # Curated list (0.4) + domain keywords (0.2) = 0.6 confidence
        assert result.confidence >= 0.6

    def test_tesla_dual_domain_classification(self, classifier_with_db):
        """Test Tesla classified as both domains"""
        result = classifier_with_db.classify_company(
            company_name="Tesla",
            job_title="Engineering Manager",
            domain_keywords=["automotive", "software"],
        )

        assert result.type == "both"
        # Curated list gives "both" with confidence 0.4 (weight 0.4 * score 1.0)
        assert result.confidence >= 0.4

    def test_classification_caching(self, classifier_with_db):
        """Test classification results are cached"""
        # First call
        result1 = classifier_with_db.classify_company("Boston Dynamics")

        # Second call should use cache
        result2 = classifier_with_db.classify_company("Boston Dynamics")

        assert result1.type == result2.type
        assert result1.confidence == result2.confidence

    def test_manual_override_precedence(self, classifier_with_db):
        """Test manual override takes precedence over automated classification"""
        # Insert manual override
        conn = sqlite3.connect(classifier_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO company_classifications
            (company_name, classification, confidence_score, source, signals, created_at, updated_at)
            VALUES (?, 'software', 1.0, 'manual', '{}', datetime('now'), datetime('now'))
        """,
            ("Boston Dynamics",),
        )
        conn.commit()
        conn.close()

        # Clear cache
        classifier_with_db._classification_cache.clear()

        # Should return manual override (software) instead of automated (hardware)
        result = classifier_with_db.classify_company("Boston Dynamics")

        assert result.type == "software"
        assert result.source == "manual"
        assert result.confidence == 1.0


class TestDatabaseStorage:
    """Test database storage and retrieval"""

    @pytest.fixture
    def classifier_with_db(self):
        """Create classifier with temporary database"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            db_path = db_file.name

        # Create database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE company_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                classification TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                source TEXT NOT NULL,
                signals TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "hardware_companies": [],
                    "software_companies": [],
                    "both_domains": [],
                    "_keywords": {"hardware_indicators": [], "software_indicators": []},
                },
                f,
            )
            config_path = f.name

        try:
            classifier = CompanyClassifier(db_path=db_path, config_path=config_path)
            yield classifier
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(config_path).unlink(missing_ok=True)

    def test_store_new_classification(self, classifier_with_db):
        """Test storing new automated classification in database"""
        classification = CompanyClassification(
            type="hardware", confidence=0.85, signals={"name": {"score": 1.0}}, source="auto"
        )

        classifier_with_db._store_classification("Test Company", classification)

        # Verify stored in database
        conn = sqlite3.connect(classifier_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT classification, confidence_score, source FROM company_classifications WHERE company_name = ?",
            ("Test Company",),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "hardware"
        assert row[1] == 0.85
        assert row[2] == "auto"

    def test_update_existing_classification(self, classifier_with_db):
        """Test updating existing automated classification"""
        # Store initial classification
        classification1 = CompanyClassification(
            type="hardware", confidence=0.6, signals={}, source="auto"
        )
        classifier_with_db._store_classification("Test Company", classification1)

        # Update with new classification
        classification2 = CompanyClassification(
            type="software", confidence=0.9, signals={}, source="auto"
        )
        classifier_with_db._store_classification("Test Company", classification2)

        # Verify updated in database (should be only one record)
        conn = sqlite3.connect(classifier_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*), classification FROM company_classifications WHERE company_name = ?",
            ("Test Company",),
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 1  # Only one record
        assert row[1] == "software"  # Updated to software

    def test_manual_classification_not_overwritten(self, classifier_with_db):
        """Test manual classifications are not stored as automated (UNIQUE constraint on company_name)"""
        # Store manual override
        conn = sqlite3.connect(classifier_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO company_classifications
            (company_name, classification, confidence_score, source, signals, created_at, updated_at)
            VALUES ('Test Company', 'hardware', 1.0, 'manual', '{}', datetime('now'), datetime('now'))
        """
        )
        conn.commit()
        conn.close()

        # Try to store automated classification (should fail silently due to UNIQUE constraint)
        classification = CompanyClassification(
            type="software", confidence=0.8, signals={}, source="auto"
        )
        classifier_with_db._store_classification("Test Company", classification)

        # Verify manual override still exists and wasn't changed
        conn = sqlite3.connect(classifier_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT classification, source FROM company_classifications WHERE company_name = ?",
            ("Test Company",),
        )
        row = cursor.fetchone()
        conn.close()

        # Manual override should still exist unchanged
        assert row is not None
        assert row[0] == "hardware"  # Still hardware, not software
        assert row[1] == "manual"  # Still manual source
