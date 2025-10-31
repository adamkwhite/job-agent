"""
Company data model for unified ingestion
All job sources (emails, CSV, browser extension) output Company objects
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Company:
    """
    Unified company representation for job scraping

    All sources (emails, CSV, browser extension) extract companies into this format.
    """

    name: str
    careers_url: str
    source: str  # 'email', 'csv', 'browser_extension'
    source_details: str = ""  # e.g., "LinkedIn email", "job_sources.csv", etc.
    discovered_at: str = ""  # ISO timestamp
    notes: str = ""  # Optional metadata

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "name": self.name,
            "careers_url": self.careers_url,
            "source": self.source,
            "source_details": self.source_details,
            "discovered_at": self.discovered_at,
            "notes": self.notes,
        }
