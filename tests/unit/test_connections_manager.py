"""Unit tests for ConnectionsManager."""

import csv

import pytest

from src.utils.connections_manager import Connection, ConnectionsManager


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for testing."""
    return tmp_path / "data"


@pytest.fixture
def sample_connections_csv(temp_data_dir):
    """Create sample connections CSV file."""
    profile_dir = temp_data_dir / "profiles" / "test_user"
    profile_dir.mkdir(parents=True)

    csv_file = profile_dir / "connections.csv"

    # Write sample CSV data
    with open(csv_file, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "First Name",
                "Last Name",
                "Email Address",
                "Company",
                "Position",
                "Connected On",
            ]
        )
        writer.writerow(
            [
                "John",
                "Doe",
                "john.doe@bostondynamics.com",
                "Boston Dynamics",
                "Senior Engineer",
                "01 Jan 2023",
            ]
        )
        writer.writerow(
            [
                "Jane",
                "Smith",
                "jane.smith@google.com",
                "Google LLC",
                "Product Manager",
                "15 Mar 2022",
            ]
        )
        writer.writerow(
            [
                "Bob",
                "Johnson",
                "bob.j@meta.com",
                "Meta Platforms, Inc.",
                "Engineering Manager",
                "20 Jun 2021",
            ]
        )
        writer.writerow(
            [
                "Alice",
                "Williams",
                "alice.w@nvidia.com",
                "NVIDIA Corporation",
                "Staff Engineer",
                "10 Nov 2020",
            ]
        )

    return csv_file


class TestConnection:
    """Test Connection dataclass."""

    def test_connection_creation(self):
        """Test creating a Connection object."""
        conn = Connection(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            company="Acme Corp",
            position="Engineer",
            connected_on="01 Jan 2023",
        )

        assert conn.first_name == "John"
        assert conn.last_name == "Doe"
        assert conn.email == "john@example.com"
        assert conn.company == "Acme Corp"
        assert conn.position == "Engineer"
        assert conn.connected_on == "01 Jan 2023"

    def test_full_name_property(self):
        """Test full_name property."""
        conn = Connection(
            first_name="Jane",
            last_name="Smith",
            email="",
            company="",
            position="",
            connected_on="",
        )

        assert conn.full_name == "Jane Smith"


class TestConnectionsManager:
    """Test ConnectionsManager class."""

    def test_init(self, temp_data_dir):
        """Test manager initialization."""
        manager = ConnectionsManager(
            profile_name="test_user",
            data_dir=temp_data_dir,
            similarity_threshold=90.0,
        )

        assert manager.profile_name == "test_user"
        assert manager.data_dir == temp_data_dir
        assert manager.similarity_threshold == 90.0
        assert (
            manager.connections_file == temp_data_dir / "profiles" / "test_user" / "connections.csv"
        )

    def test_connections_exist_false(self, temp_data_dir):
        """Test connections_exist when file doesn't exist."""
        manager = ConnectionsManager("nonexistent_user", data_dir=temp_data_dir)
        assert not manager.connections_exist

    def test_connections_exist_true(self, temp_data_dir, sample_connections_csv):
        """Test connections_exist when file exists."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)
        assert manager.connections_exist

    def test_load_connections_success(self, temp_data_dir, sample_connections_csv):
        """Test loading valid connections CSV."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)
        connections = manager.load_connections()

        assert len(connections) == 4
        assert connections[0].first_name == "John"
        assert connections[0].last_name == "Doe"
        assert connections[0].company == "Boston Dynamics"
        assert connections[1].company == "Google LLC"
        assert connections[2].company == "Meta Platforms, Inc."

    def test_load_connections_cached(self, temp_data_dir, sample_connections_csv):
        """Test that connections are cached after first load."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # First load
        connections1 = manager.load_connections()

        # Second load should return cached version (same object)
        connections2 = manager.load_connections()

        assert connections1 is connections2

    def test_load_connections_file_not_found(self, temp_data_dir):
        """Test loading when file doesn't exist."""
        manager = ConnectionsManager("nonexistent_user", data_dir=temp_data_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            manager.load_connections()

        assert "No connections file found" in str(exc_info.value)
        assert "upload_connections.py" in str(exc_info.value)

    def test_load_connections_empty_csv(self, temp_data_dir):
        """Test loading empty CSV file."""
        profile_dir = temp_data_dir / "profiles" / "empty_user"
        profile_dir.mkdir(parents=True)
        csv_file = profile_dir / "connections.csv"
        csv_file.write_text("")

        manager = ConnectionsManager("empty_user", data_dir=temp_data_dir)

        with pytest.raises(ValueError) as exc_info:
            manager.load_connections()

        assert "empty or has no header row" in str(exc_info.value)

    def test_load_connections_missing_columns(self, temp_data_dir):
        """Test loading CSV with missing required columns."""
        profile_dir = temp_data_dir / "profiles" / "bad_user"
        profile_dir.mkdir(parents=True)
        csv_file = profile_dir / "connections.csv"

        with open(csv_file, "w", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["First Name", "Last Name"])  # Missing required columns
            writer.writerow(["John", "Doe"])

        manager = ConnectionsManager("bad_user", data_dir=temp_data_dir)

        with pytest.raises(ValueError) as exc_info:
            manager.load_connections()

        assert "missing required columns" in str(exc_info.value).lower()

    def test_normalize_company_name(self, temp_data_dir):
        """Test company name normalization."""
        manager = ConnectionsManager("test", data_dir=temp_data_dir)

        # Test suffix removal
        assert manager.normalize_company_name("Acme Corp.") == "acme"
        assert manager.normalize_company_name("Acme, Inc.") == "acme"
        assert manager.normalize_company_name("Acme LLC") == "acme"
        assert manager.normalize_company_name("Acme Corporation") == "acme"
        assert manager.normalize_company_name("Acme, Ltd.") == "acme"

        # Test case normalization
        assert manager.normalize_company_name("NVIDIA Corporation") == "nvidia"
        assert manager.normalize_company_name("Google LLC") == "google"

        # Test whitespace handling
        assert manager.normalize_company_name("  Boston Dynamics  ") == "boston dynamics"

        # Test empty string
        assert manager.normalize_company_name("") == ""
        assert manager.normalize_company_name("   ") == ""

    def test_match_company_exact(self, temp_data_dir, sample_connections_csv):
        """Test exact company name matching."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        matches = manager.match_company("Boston Dynamics")
        assert len(matches) == 1
        assert matches[0].first_name == "John"
        assert matches[0].company == "Boston Dynamics"

    def test_match_company_with_suffix(self, temp_data_dir, sample_connections_csv):
        """Test matching company name with different suffixes."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # "Google" should match "Google LLC"
        matches = manager.match_company("Google")
        assert len(matches) == 1
        assert matches[0].first_name == "Jane"

        # "Meta" should match "Meta Platforms, Inc."
        matches = manager.match_company("Meta")
        assert len(matches) == 1
        assert matches[0].first_name == "Bob"

    def test_match_company_case_insensitive(self, temp_data_dir, sample_connections_csv):
        """Test case-insensitive matching."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # Different case variations
        assert len(manager.match_company("boston dynamics")) == 1
        assert len(manager.match_company("BOSTON DYNAMICS")) == 1
        assert len(manager.match_company("Boston Dynamics")) == 1

    def test_match_company_no_matches(self, temp_data_dir, sample_connections_csv):
        """Test matching when no connections exist at company."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        matches = manager.match_company("Apple")
        assert len(matches) == 0

    def test_match_company_empty_input(self, temp_data_dir, sample_connections_csv):
        """Test matching with empty company name."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        matches = manager.match_company("")
        assert len(matches) == 0

    def test_match_company_caching(self, temp_data_dir, sample_connections_csv):
        """Test that match results are cached."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # First match
        matches1 = manager.match_company("Google")

        # Check cache was populated
        assert "google" in manager._company_cache

        # Second match should use cache
        matches2 = manager.match_company("Google")

        assert len(matches1) == len(matches2)

    def test_match_company_no_connections_file(self, temp_data_dir):
        """Test matching when connections file doesn't exist (graceful degradation)."""
        manager = ConnectionsManager("nonexistent_user", data_dir=temp_data_dir)

        # Should return empty list instead of raising exception
        matches = manager.match_company("Any Company")
        assert len(matches) == 0

    def test_get_connection_summary(self, temp_data_dir, sample_connections_csv):
        """Test getting connection summary."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        summary = manager.get_connection_summary("Boston Dynamics")

        assert summary["count"] == 1
        assert len(summary["connections"]) == 1
        assert summary["connections"][0].first_name == "John"
        assert "Boston Dynamics" in summary["company_variations"]

    def test_get_connection_summary_no_matches(self, temp_data_dir, sample_connections_csv):
        """Test summary with no matching connections."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        summary = manager.get_connection_summary("Apple")

        assert summary["count"] == 0
        assert len(summary["connections"]) == 0
        assert len(summary["company_variations"]) == 0

    def test_clear_cache(self, temp_data_dir, sample_connections_csv):
        """Test clearing the match cache."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # Populate cache
        manager.match_company("Google")
        assert len(manager._company_cache) > 0

        # Clear cache
        manager.clear_cache()
        assert len(manager._company_cache) == 0

    def test_save_and_load_cache(self, temp_data_dir, sample_connections_csv):
        """Test saving and loading cache to/from disk."""
        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)

        # Populate cache
        manager.match_company("Google")
        manager.match_company("Boston Dynamics")

        # Save cache
        manager.save_cache()
        assert manager.cache_file.exists()

        # Create new manager and load cache
        manager2 = ConnectionsManager("test_user", data_dir=temp_data_dir)
        manager2.load_cache()

        assert "google" in manager2._company_cache
        assert "boston dynamics" in manager2._company_cache

    def test_load_cache_corrupted_file(self, temp_data_dir):
        """Test loading corrupted cache file (should start fresh)."""
        profile_dir = temp_data_dir / "profiles" / "test_user"
        profile_dir.mkdir(parents=True)
        cache_file = profile_dir / "connections_cache.json"

        # Write corrupted JSON
        cache_file.write_text("{ invalid json }")

        manager = ConnectionsManager("test_user", data_dir=temp_data_dir)
        manager.load_cache()

        # Should have empty cache (not crash)
        assert manager._company_cache == {}

    def test_similarity_threshold_custom(self, temp_data_dir, sample_connections_csv):
        """Test custom similarity threshold."""
        # Strict threshold (90%) - fewer matches
        manager_strict = ConnectionsManager(
            "test_user", data_dir=temp_data_dir, similarity_threshold=90.0
        )

        # Lenient threshold (70%) - more matches
        manager_lenient = ConnectionsManager(
            "test_user", data_dir=temp_data_dir, similarity_threshold=70.0
        )

        # Both should match exact names
        assert len(manager_strict.match_company("Boston Dynamics")) == 1
        assert len(manager_lenient.match_company("Boston Dynamics")) == 1
