"""
Unit tests for company classifications migration and configuration
Tests for Issue #122 - Software Engineering Role Filtering
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Import migration module directly (has dashes in filename)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "migrations"))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "migration_002",
    Path(__file__).parent.parent.parent / "src" / "migrations" / "002_company_classifications.py",
)
assert spec is not None, "Migration spec should not be None"
assert spec.loader is not None, "Migration loader should not be None"
migration_002_company_classifications = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_002_company_classifications)


class TestCompanyClassificationsMigration:
    """Test database migration for company classifications system"""

    def test_migration_creates_company_classifications_table(self):
        """Test that migration creates company_classifications table with correct schema"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create job_scores table first (migration 002 depends on it)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE job_scores (
                    id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    profile_id TEXT,
                    fit_score INTEGER
                )
            """)
            conn.commit()
            conn.close()

            # Run migration
            success = migration_002_company_classifications.migrate(db_path)
            assert success, "Migration should succeed"

            # Verify table exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='company_classifications'
            """)
            assert cursor.fetchone() is not None, "company_classifications table should exist"

            # Verify column schema
            cursor.execute("PRAGMA table_info(company_classifications)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            expected_columns = {
                "id": "INTEGER",
                "company_name": "TEXT",
                "classification": "TEXT",
                "confidence_score": "REAL",
                "source": "TEXT",
                "signals": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            }

            for col_name, col_type in expected_columns.items():
                assert col_name in columns, f"Column {col_name} should exist"
                assert columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

            conn.close()

        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)

    def test_migration_creates_indexes(self):
        """Test that migration creates all required indexes"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create job_scores table first
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE job_scores (
                    id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    profile_id TEXT
                )
            """)
            conn.commit()
            conn.close()

            success = migration_002_company_classifications.migrate(db_path)
            assert success

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all indexes for company_classifications table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='company_classifications'
            """)
            indexes = [row[0] for row in cursor.fetchall()]

            # Verify expected indexes exist
            assert "idx_company_classifications_name" in indexes
            assert "idx_company_classifications_type" in indexes
            assert "idx_company_classifications_source" in indexes

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_migration_adds_classification_metadata_column(self):
        """Test that migration adds classification_metadata to job_scores table"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create job_scores table first (simulating existing database)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE job_scores (
                    id INTEGER PRIMARY KEY,
                    job_id INTEGER,
                    profile_id TEXT,
                    fit_score INTEGER
                )
            """)
            conn.commit()
            conn.close()

            # Run migration
            success = migration_002_company_classifications.migrate(db_path)
            assert success

            # Verify column was added
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(job_scores)")
            columns = [row[1] for row in cursor.fetchall()]

            assert "classification_metadata" in columns, (
                "classification_metadata column should be added to job_scores"
            )

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_migration_is_idempotent(self):
        """Test that migration can be run multiple times without errors"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create job_scores table first
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE job_scores (
                    id INTEGER PRIMARY KEY,
                    job_id INTEGER
                )
            """)
            conn.commit()
            conn.close()

            # Run migration twice
            success1 = migration_002_company_classifications.migrate(db_path)
            success2 = migration_002_company_classifications.migrate(db_path)

            assert success1, "First migration should succeed"
            assert success2, "Second migration should succeed"

            # Verify table still exists and has correct structure
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='company_classifications'
            """)
            assert cursor.fetchone() is not None

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_migration_rollback_drops_table(self):
        """Test that rollback drops company_classifications table"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Run migration then rollback
            migration_002_company_classifications.migrate(db_path)
            success = migration_002_company_classifications.rollback(db_path)

            assert success, "Rollback should succeed"

            # Verify table no longer exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='company_classifications'
            """)
            assert cursor.fetchone() is None, (
                "company_classifications table should not exist after rollback"
            )

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_migration_check_constraints(self):
        """Test that CHECK constraints on classification and source columns work"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            migration_002_company_classifications.migrate(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Valid classification values should work
            cursor.execute("""
                INSERT INTO company_classifications
                (company_name, classification, confidence_score, source, created_at, updated_at)
                VALUES ('Test Co', 'software', 0.8, 'auto', datetime('now'), datetime('now'))
            """)

            # Invalid classification should fail
            try:
                cursor.execute("""
                    INSERT INTO company_classifications
                    (company_name, classification, confidence_score, source, created_at, updated_at)
                    VALUES ('Bad Co', 'invalid_type', 0.5, 'auto', datetime('now'), datetime('now'))
                """)
                conn.commit()
                pytest.fail("Should not allow invalid classification value")
            except sqlite3.IntegrityError:
                pass  # Expected

            # Invalid source should fail
            try:
                cursor.execute("""
                    INSERT INTO company_classifications
                    (company_name, classification, confidence_score, source, created_at, updated_at)
                    VALUES ('Bad Co 2', 'software', 0.5, 'invalid_source', datetime('now'), datetime('now'))
                """)
                conn.commit()
                pytest.fail("Should not allow invalid source value")
            except sqlite3.IntegrityError:
                pass  # Expected

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_migration_unique_company_name(self):
        """Test that company_name has UNIQUE constraint"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            migration_002_company_classifications.migrate(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Insert first company
            cursor.execute("""
                INSERT INTO company_classifications
                (company_name, classification, confidence_score, source, created_at, updated_at)
                VALUES ('Unique Co', 'hardware', 0.9, 'manual', datetime('now'), datetime('now'))
            """)
            conn.commit()

            # Try to insert duplicate
            try:
                cursor.execute("""
                    INSERT INTO company_classifications
                    (company_name, classification, confidence_score, source, created_at, updated_at)
                    VALUES ('Unique Co', 'software', 0.7, 'auto', datetime('now'), datetime('now'))
                """)
                conn.commit()
                pytest.fail("Should not allow duplicate company_name")
            except sqlite3.IntegrityError:
                pass  # Expected

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)


class TestCompanyClassificationsConfig:
    """Test company classifications configuration file"""

    def test_config_file_exists(self):
        """Test that config file exists"""
        config_path = Path("config/company_classifications.json")
        assert config_path.exists(), "config/company_classifications.json should exist"

    def test_config_file_valid_json(self):
        """Test that config file is valid JSON"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)
        assert isinstance(config, dict), "Config should be a dictionary"

    def test_config_has_required_sections(self):
        """Test that config has all required sections"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        assert "hardware_companies" in config, "Config should have hardware_companies list"
        assert "software_companies" in config, "Config should have software_companies list"
        assert "both_domains" in config, "Config should have both_domains list"

    def test_config_lists_are_non_empty(self):
        """Test that all company lists have entries"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        assert len(config["hardware_companies"]) > 0, "hardware_companies should not be empty"
        assert len(config["software_companies"]) > 0, "software_companies should not be empty"
        assert len(config["both_domains"]) > 0, "both_domains should not be empty"

    def test_config_lists_are_strings(self):
        """Test that all entries in company lists are strings"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        for company in config["hardware_companies"]:
            assert isinstance(company, str), f"Hardware company '{company}' should be a string"

        for company in config["software_companies"]:
            assert isinstance(company, str), f"Software company '{company}' should be a string"

        for company in config["both_domains"]:
            assert isinstance(company, str), f"Both domain company '{company}' should be a string"

    def test_config_no_duplicates_within_lists(self):
        """Test that there are no duplicate companies within each list"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        hardware_set = set(config["hardware_companies"])
        assert len(hardware_set) == len(config["hardware_companies"]), (
            "hardware_companies should have no duplicates"
        )

        software_set = set(config["software_companies"])
        assert len(software_set) == len(config["software_companies"]), (
            "software_companies should have no duplicates"
        )

        both_set = set(config["both_domains"])
        assert len(both_set) == len(config["both_domains"]), (
            "both_domains should have no duplicates"
        )

    def test_config_contains_known_robotics_companies(self):
        """Test that config contains expected robotics/hardware companies"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        # Test for priority robotics companies from robotics_priority_companies.json
        expected_robotics = [
            "Boston Dynamics",
            "Figure",
            "Agility Robotics",
            "1X Technologies",
            "Skydio",
            "Dexterity",
            "Covariant",
            "Nuro",
        ]

        for company in expected_robotics:
            assert company in config["hardware_companies"], (
                f"{company} should be in hardware_companies"
            )

    def test_config_contains_known_software_companies(self):
        """Test that config contains expected software companies"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        # Test for well-known software companies
        expected_software = ["Dropbox", "Stripe", "Anthropic", "Microsoft", "Salesforce"]

        for company in expected_software:
            assert company in config["software_companies"], (
                f"{company} should be in software_companies"
            )

    def test_config_contains_known_dual_domain_companies(self):
        """Test that config contains expected dual-domain companies"""
        config_path = Path("config/company_classifications.json")
        with open(config_path) as f:
            config = json.load(f)

        # Test for companies with both hardware and software
        expected_both = ["Google", "Tesla", "Apple", "Amazon", "Meta"]

        for company in expected_both:
            assert company in config["both_domains"], f"{company} should be in both_domains"
