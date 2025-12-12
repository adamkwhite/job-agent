"""LinkedIn Connections Manager.

Handles loading, parsing, and matching LinkedIn connections data
for displaying in job digests.
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz


@dataclass
class Connection:
    """Represents a LinkedIn connection."""

    first_name: str
    last_name: str
    email: str
    company: str
    position: str
    connected_on: str

    @property
    def full_name(self) -> str:
        """Return full name of connection."""
        return f"{self.first_name} {self.last_name}"


class ConnectionsManager:
    """Manages LinkedIn connections data for a user profile."""

    # Required CSV columns from LinkedIn export
    REQUIRED_COLUMNS = {
        "First Name",
        "Last Name",
        "Email Address",
        "Company",
        "Position",
        "Connected On",
    }

    # Company name suffixes to normalize
    COMPANY_SUFFIXES = [
        ", Inc.",
        " Inc.",
        ", LLC",
        " LLC",
        ", Corp.",
        " Corp.",
        ", Ltd.",
        " Ltd.",
        ", Corporation",
        " Corporation",
    ]

    def __init__(
        self,
        profile_name: str,
        data_dir: Path = Path("data"),
        similarity_threshold: float = 85.0,
    ):
        """Initialize connections manager.

        Args:
            profile_name: Name of the user profile (e.g., 'wes', 'adam')
            data_dir: Base data directory (default: 'data/')
            similarity_threshold: Minimum similarity score for company matching (0-100)
        """
        self.profile_name = profile_name
        self.data_dir = data_dir
        self.similarity_threshold = similarity_threshold

        # Paths
        self.profile_dir = data_dir / "profiles" / profile_name
        self.connections_file = self.profile_dir / "connections.csv"
        self.cache_file = self.profile_dir / "connections_cache.json"

        # In-memory data
        self._connections: list[Connection] | None = None
        self._company_cache: dict[str, list[str]] = {}

    @property
    def connections_exist(self) -> bool:
        """Check if connections file exists for this profile."""
        return self.connections_file.exists()

    def load_connections(self) -> list[Connection]:
        """Load connections from CSV file.

        Returns:
            List of Connection objects

        Raises:
            FileNotFoundError: If connections file doesn't exist
            ValueError: If CSV is malformed or missing required columns
        """
        if self._connections is not None:
            return self._connections

        if not self.connections_exist:
            raise FileNotFoundError(
                f"No connections file found at {self.connections_file}. "
                f"Upload LinkedIn CSV export using: "
                f"python scripts/upload_connections.py --profile {self.profile_name} connections.csv"
            )

        connections = []

        try:
            with open(self.connections_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Validate required columns
                if reader.fieldnames is None:
                    raise ValueError("CSV file is empty or has no header row")

                missing_columns = self.REQUIRED_COLUMNS - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(
                        f"CSV missing required columns: {', '.join(missing_columns)}. "
                        f"Expected columns: {', '.join(sorted(self.REQUIRED_COLUMNS))}"
                    )

                # Parse connections
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        connection = Connection(
                            first_name=row["First Name"].strip(),
                            last_name=row["Last Name"].strip(),
                            email=row["Email Address"].strip(),
                            company=row["Company"].strip(),
                            position=row["Position"].strip(),
                            connected_on=row["Connected On"].strip(),
                        )
                        connections.append(connection)
                    except KeyError as e:
                        # Should not happen if validation passed, but be defensive
                        raise ValueError(f"Row {row_num}: Missing column {e}") from e

        except UnicodeDecodeError as e:
            raise ValueError(
                f"Failed to read CSV file. Ensure it's UTF-8 encoded. Error: {e}"
            ) from e
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {e}") from e

        self._connections = connections
        return connections

    def normalize_company_name(self, company: str) -> str:
        """Normalize company name for matching.

        Removes common suffixes and standardizes spacing/casing.

        Args:
            company: Raw company name

        Returns:
            Normalized company name (lowercase, trimmed)
        """
        if not company:
            return ""

        company_clean = company.strip()

        # Remove common suffixes
        for suffix in self.COMPANY_SUFFIXES:
            if company_clean.endswith(suffix):
                company_clean = company_clean[: -len(suffix)]

        return company_clean.lower().strip()

    def match_company(self, job_company: str) -> list[Connection]:
        """Find connections at a given company using fuzzy matching.

        Args:
            job_company: Company name from job posting

        Returns:
            List of Connection objects at matching companies
        """
        if not job_company:
            return []

        # Load connections if not already loaded
        try:
            connections = self.load_connections()
        except (FileNotFoundError, ValueError):
            # No connections file or invalid - return empty
            return []

        # Check cache first
        cache_key = job_company.lower().strip()
        if cache_key in self._company_cache:
            # Return cached matches
            cached_companies = self._company_cache[cache_key]
            return [c for c in connections if c.company in cached_companies]

        # Normalize job company name
        job_company_normalized = self.normalize_company_name(job_company)
        if not job_company_normalized:
            return []

        # Find matches
        matched_companies = []
        matches = []

        for connection in connections:
            # Skip connections with empty company
            if not connection.company:
                continue

            # Normalize connection company
            conn_company_normalized = self.normalize_company_name(connection.company)

            # Skip if normalized name is empty
            if not conn_company_normalized:
                continue

            # Try multiple matching strategies
            is_match = False

            # Strategy 1: Exact substring match (e.g., "Meta" in "Meta Platforms")
            if (
                job_company_normalized in conn_company_normalized
                or conn_company_normalized in job_company_normalized
            ):
                is_match = True

            # Strategy 2: Fuzzy similarity match
            if not is_match:
                similarity = fuzz.ratio(job_company_normalized, conn_company_normalized)
                if similarity >= self.similarity_threshold:
                    is_match = True

            if is_match:
                matches.append(connection)
                if connection.company not in matched_companies:
                    matched_companies.append(connection.company)

        # Cache result
        self._company_cache[cache_key] = matched_companies

        return matches

    def get_connection_summary(self, job_company: str) -> dict:
        """Get summary of connections at a company.

        Args:
            job_company: Company name from job posting

        Returns:
            Dictionary with:
            - count: Number of connections
            - connections: List of Connection objects
            - company_variations: List of company name variations found
        """
        connections = self.match_company(job_company)

        # Get unique company name variations
        company_variations = list({c.company for c in connections})

        return {
            "count": len(connections),
            "connections": connections,
            "company_variations": company_variations,
        }

    def clear_cache(self):
        """Clear in-memory company match cache."""
        self._company_cache = {}

    def save_cache(self):
        """Save company match cache to disk for persistence."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._company_cache, f, indent=2)

    def load_cache(self):
        """Load company match cache from disk if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self._company_cache = json.load(f)
            except (OSError, json.JSONDecodeError):
                # Cache file corrupted or unreadable - start fresh
                self._company_cache = {}
