"""
Unit tests for database module, focusing on deduplication logic
"""

import importlib.util
from pathlib import Path

# Import migration 003 for filter tracking tests
migration_path = (
    Path(__file__).parent.parent.parent / "src" / "migrations" / "003_filter_tracking.py"
)
spec = importlib.util.spec_from_file_location("migration_003", migration_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load migration from {migration_path}")
migration_003 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_003)


class TestJobDeduplication:
    """Test job deduplication and hash generation"""

    def test_generate_hash_basic(self, test_db):
        """Test basic hash generation"""
        hash1 = test_db.generate_job_hash(
            "Software Engineer", "Tech Corp", "https://example.com/job/123"
        )
        hash2 = test_db.generate_job_hash(
            "Software Engineer", "Tech Corp", "https://example.com/job/123"
        )
        assert hash1 == hash2

    def test_generate_hash_case_insensitive(self, test_db):
        """Test that hashing is case-insensitive"""
        hash1 = test_db.generate_job_hash(
            "Software Engineer", "Tech Corp", "https://example.com/job/123"
        )
        hash2 = test_db.generate_job_hash(
            "software engineer", "tech corp", "https://example.com/job/123"
        )
        assert hash1 == hash2

    def test_generate_hash_strips_whitespace(self, test_db):
        """Test that whitespace is normalized"""
        hash1 = test_db.generate_job_hash(
            "  Software Engineer  ", "  Tech Corp  ", "  https://example.com/job/123  "
        )
        hash2 = test_db.generate_job_hash(
            "Software Engineer", "Tech Corp", "https://example.com/job/123"
        )
        assert hash1 == hash2

    def test_generate_hash_linkedin_tracking_params_ignored(self, test_db):
        """Test that LinkedIn tracking parameters are normalized (Issue #37)"""
        # Same job, different tracking parameters
        url1 = "https://www.linkedin.com/comm/jobs/view/4318329363/?trackingId=abc&refId=xyz"
        url2 = "https://www.linkedin.com/comm/jobs/view/4318329363/?trackingId=def&refId=uvw"
        url3 = "https://www.linkedin.com/jobs/view/4318329363?different=params"

        hash1 = test_db.generate_job_hash("Senior Engineer", "Dropbox", url1)
        hash2 = test_db.generate_job_hash("Senior Engineer", "Dropbox", url2)
        hash3 = test_db.generate_job_hash("Senior Engineer", "Dropbox", url3)

        # All should produce the same hash
        assert hash1 == hash2
        assert hash2 == hash3

    def test_generate_hash_linkedin_different_jobs(self, test_db):
        """Test that different LinkedIn jobs produce different hashes"""
        url1 = "https://www.linkedin.com/jobs/view/1111111?trackingId=abc"
        url2 = "https://www.linkedin.com/jobs/view/2222222?trackingId=abc"

        hash1 = test_db.generate_job_hash("Engineer A", "Company A", url1)
        hash2 = test_db.generate_job_hash("Engineer B", "Company B", url2)

        # Different jobs should have different hashes
        assert hash1 != hash2

    def test_generate_hash_non_linkedin_urls_unchanged(self, test_db):
        """Test that non-LinkedIn URLs are not modified"""
        # Non-LinkedIn URLs should work normally
        url1 = "https://greenhouse.io/job/123?param=value"
        url2 = "https://greenhouse.io/job/123?param=different"

        hash1 = test_db.generate_job_hash("Engineer", "Company", url1)
        hash2 = test_db.generate_job_hash("Engineer", "Company", url2)

        # Different URLs should produce different hashes (no normalization)
        assert hash1 != hash2

    def test_generate_hash_same_company_different_title(self, test_db):
        """Test that different titles at same company produce different hashes"""
        hash1 = test_db.generate_job_hash("Engineer", "Tech Corp", "https://example.com/job/1")
        hash2 = test_db.generate_job_hash("Manager", "Tech Corp", "https://example.com/job/1")

        assert hash1 != hash2

    def test_generate_hash_same_title_different_company(self, test_db):
        """Test that same title at different companies produces different hashes"""
        hash1 = test_db.generate_job_hash("Engineer", "Company A", "https://example.com/job/1")
        hash2 = test_db.generate_job_hash("Engineer", "Company B", "https://example.com/job/1")

        assert hash1 != hash2

    def test_linkedin_url_variations(self, test_db):
        """Test various LinkedIn URL formats are normalized correctly"""
        # Different URL formats for the same job
        urls = [
            "https://www.linkedin.com/jobs/view/123456",
            "https://www.linkedin.com/comm/jobs/view/123456",
            "https://www.linkedin.com/jobs/view/123456/",
            "https://www.linkedin.com/jobs/view/123456?trackingId=xyz",
            "HTTPS://WWW.LINKEDIN.COM/JOBS/VIEW/123456",  # Case variation
        ]

        hashes = [test_db.generate_job_hash("Engineer", "Company", url) for url in urls]

        # All should produce the same hash
        for i in range(1, len(hashes)):
            assert hashes[0] == hashes[i], f"URL variation {i} produced different hash"


class TestMarkJobFiltered:
    """Test mark_job_filtered method for filter pipeline integration"""

    def test_mark_job_filtered_updates_fields(self, test_db_path):
        """Should update filter_reason and filtered_at fields"""
        import sqlite3

        from src.database import JobDatabase

        db = JobDatabase(db_path=test_db_path)

        # Run migration to add filter_reason and filtered_at columns
        migration_003.migrate(db_path=test_db_path)

        # Add a test job
        job_dict = {
            "source": "test",
            "type": "direct_job",
            "company": "Test Company",
            "title": "Junior Director",
            "location": "Remote",
            "link": "https://test.com/job",
            "keywords_matched": "[]",
            "source_email": "",
        }

        job_id = db.add_job(job_dict)
        assert job_id is not None

        # Mark as filtered
        db.mark_job_filtered(job_id, "hard_filter_junior")

        # Verify fields were updated
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT filter_reason, filtered_at FROM jobs WHERE id = ?", (job_id,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        filter_reason, filtered_at = result
        assert filter_reason == "hard_filter_junior"
        assert filtered_at is not None
        # Verify it's a valid ISO timestamp
        from datetime import datetime

        datetime.fromisoformat(filtered_at)  # Should not raise

    def test_mark_job_filtered_different_reasons(self, test_db_path):
        """Should handle different filter reasons"""
        from src.database import JobDatabase

        db = JobDatabase(db_path=test_db_path)

        # Run migration to add filter_reason and filtered_at columns
        migration_003.migrate(db_path=test_db_path)

        reasons = [
            "hard_filter_intern",
            "context_filter_software_engineering",
            "context_filter_contract_low_seniority",
        ]

        for reason in reasons:
            job_dict = {
                "source": "test",
                "type": "direct_job",
                "company": "Test",
                "title": f"Job {reason}",
                "location": "Remote",
                "link": f"https://test.com/{reason}",
                "keywords_matched": "[]",
                "source_email": "",
            }

            job_id = db.add_job(job_dict)
            assert job_id is not None

            db.mark_job_filtered(job_id, reason)

            # Verify reason was stored
            import sqlite3

            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT filter_reason FROM jobs WHERE id = ?", (job_id,))
            result = cursor.fetchone()
            conn.close()

            assert result[0] == reason
