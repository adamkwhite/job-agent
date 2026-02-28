"""
Selective job description enrichment via Firecrawl

Fetches full job descriptions for high-scoring jobs (B+ grade, score >= threshold)
to improve domain and technical keyword matching on a second scoring pass.

Cost: ~$0.002 per Firecrawl call × ~15-20% of jobs qualifying = negligible.
"""

import logging
import re
from dataclasses import dataclass, field

from database import JobDatabase
from scrapers.firecrawl_career_scraper import FirecrawlCareerScraper

logger = logging.getLogger(__name__)

# URLs that are career listing pages (not individual job posts)
_LISTING_PAGE_PATTERNS = re.compile(
    r"/(careers|jobs|openings|positions|vacancies)/?$"
    r"|/careers/?#"
    r"|/jobs/?#"
    r"|lever\.co/[^/]+/?$"
    r"|greenhouse\.io/[^/]+/?$",
    re.IGNORECASE,
)

# Max description length to store (avoids bloating the DB)
MAX_DESCRIPTION_LENGTH = 5000


@dataclass
class EnrichmentStats:
    """Track enrichment operation statistics"""

    candidates: int = 0
    enriched: int = 0
    skipped_no_url: int = 0
    skipped_has_description: int = 0
    skipped_listing_url: int = 0
    fetch_failures: int = 0
    rescored: int = 0
    score_changes: list = field(default_factory=list)

    @property
    def estimated_cost(self) -> float:
        """Estimated Firecrawl API cost (~$0.002 per scrape)"""
        return self.enriched * 0.002


class JobDescriptionEnricher:
    """Fetch and store job descriptions for high-scoring jobs"""

    def __init__(
        self,
        firecrawl_scraper: FirecrawlCareerScraper,
        db: JobDatabase,
    ) -> None:
        self.scraper = firecrawl_scraper
        self.db = db

    def enrich_jobs(
        self,
        scored_jobs: list[dict],
        threshold: int = 70,
    ) -> EnrichmentStats:
        """
        Enrich high-scoring jobs with full descriptions.

        Args:
            scored_jobs: List of job dicts with at least {id, link, description, score}.
                         'score' is the first-pass fit_score.
            threshold: Minimum score to qualify for enrichment (default: B+ grade).

        Returns:
            EnrichmentStats with counts and cost estimate.
        """
        stats = EnrichmentStats()

        qualifying = [j for j in scored_jobs if j.get("score", 0) >= threshold]
        stats.candidates = len(qualifying)

        if not qualifying:
            return stats

        logger.info(
            "Enrichment: %d/%d jobs qualify (score >= %d)",
            len(qualifying),
            len(scored_jobs),
            threshold,
        )

        for job in qualifying:
            self._enrich_single_job(job, stats)

        logger.info(
            "Enrichment complete: %d enriched, %d failures, ~$%.3f cost",
            stats.enriched,
            stats.fetch_failures,
            stats.estimated_cost,
        )

        return stats

    def _enrich_single_job(self, job: dict, stats: EnrichmentStats) -> None:
        """Attempt to enrich a single job with its full description."""
        job_id = job.get("id")
        url = job.get("link", "")
        existing_desc = job.get("description", "")

        if existing_desc:
            stats.skipped_has_description += 1
            return

        if not url or not url.startswith("http"):
            stats.skipped_no_url += 1
            return

        if not self._is_job_post_url(url):
            stats.skipped_listing_url += 1
            return

        description = self._fetch_description(url)
        if not description:
            stats.fetch_failures += 1
            return

        # Truncate and store
        description = description[:MAX_DESCRIPTION_LENGTH]
        if job_id:
            self.db.update_job_description(job_id, description)
        job["description"] = description
        stats.enriched += 1

    @staticmethod
    def _is_job_post_url(url: str) -> bool:
        """Check if URL points to an individual job post (not a listing page)."""
        return not bool(_LISTING_PAGE_PATTERNS.search(url))

    def _fetch_description(self, url: str) -> str | None:
        """Fetch job page markdown and extract description text."""
        result = self.scraper._firecrawl_scrape(url)
        if not result:
            return None

        markdown = result.get("markdown", "")
        if not markdown:
            return None

        return self._extract_description_text(markdown)

    @staticmethod
    def _extract_description_text(markdown: str) -> str:
        """Extract meaningful description text from page markdown.

        Strips navigation links, headers with only links, and boilerplate.
        """
        lines = markdown.split("\n")
        content_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Skip empty lines at start
            if not content_lines and not stripped:
                continue
            # Skip lines that are purely navigation links
            if stripped.startswith("[") and stripped.endswith(")"):
                continue
            # Skip horizontal rules
            if stripped in ("---", "***", "___"):
                continue
            content_lines.append(stripped)

        return "\n".join(content_lines).strip()
