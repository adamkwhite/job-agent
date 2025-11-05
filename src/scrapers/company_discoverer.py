"""
Company Discoverer - Extract companies from job sources

Discovers companies from various job sources (like robotics sheet)
and prepares them for addition to the company monitoring system.
"""

from urllib.parse import urlparse


class CompanyDiscoverer:
    """Extract and normalize company data from job sources"""

    def __init__(self):
        self.discovered_companies: dict[str, str] = {}  # name -> careers_url

    def discover_from_robotics_sheet(self, opportunities: list) -> list[dict[str, str]]:
        """
        Extract unique companies from robotics sheet opportunities

        Args:
            opportunities: List of OpportunityData objects from robotics scraper

        Returns:
            List of company dicts with: name, careers_url, source, notes
        """
        companies_map = {}  # careers_url -> company data

        for opp in opportunities:
            # Handle both dict and Pydantic object
            if hasattr(opp, "company"):
                company_name = (opp.company or "").strip()
                job_url = (opp.link or "").strip()
            else:
                company_name = opp.get("company", "").strip()
                job_url = opp.get("link", "").strip()

            if not company_name or not job_url:
                continue

            # Extract base career page URL from job URL
            careers_url = self._extract_careers_url(job_url)

            if not careers_url:
                continue

            # Use careers_url as key to deduplicate
            # (same company might have multiple job URLs pointing to same career page)
            if careers_url not in companies_map:
                companies_map[careers_url] = {
                    "name": company_name,
                    "careers_url": careers_url,
                    "source": "robotics_sheet_auto",
                    "notes": "Auto-discovered from robotics deeptech sheet",
                }

        # Convert to list
        companies = list(companies_map.values())

        print(
            f"\n[CompanyDiscoverer] Found {len(companies)} unique companies from {len(opportunities)} opportunities"
        )

        return companies

    def _extract_greenhouse_url(self, domain: str, path: str) -> str | None:  # noqa: ARG002
        """Extract Greenhouse ATS career page URL"""
        parts = path.strip("/").split("/")
        if len(parts) >= 1:
            return f"https://boards.greenhouse.io/{parts[0]}"
        return None

    def _extract_lever_url(self, domain: str, path: str) -> str | None:  # noqa: ARG002
        """Extract Lever ATS career page URL"""
        parts = path.strip("/").split("/")
        if len(parts) >= 1:
            return f"https://jobs.lever.co/{parts[0]}"
        return None

    def _extract_workday_url(self, domain: str, path: str) -> str | None:
        """Extract Workday ATS career page URL"""
        parts = path.strip("/").split("/")
        if len(parts) >= 1:
            return f"https://{domain}/{parts[0]}"
        return None

    def _extract_generic_careers_url(self, domain: str, path: str) -> str:
        """Extract career page URL from generic company website"""
        if "/careers" in path.lower() or "/jobs" in path.lower():
            # Find the careers or jobs segment
            path_parts = path.split("/")
            careers_index = next(
                (
                    i
                    for i, part in enumerate(path_parts)
                    if "career" in part.lower() or "job" in part.lower()
                ),
                None,
            )
            if careers_index is not None:
                base_path = "/".join(path_parts[: careers_index + 1])
                return f"https://{domain}{base_path}"

        # Fallback: use domain + first path segment
        first_segment = path.strip("/").split("/")[0] if path.strip("/") else ""
        if first_segment:
            return f"https://{domain}/{first_segment}"

        # Last resort: domain with /careers
        return f"https://{domain}/careers"

    def _extract_careers_url(self, job_url: str) -> str:
        """
        Extract base career page URL from a specific job posting URL

        Examples:
            Input:  https://boards.greenhouse.io/company/jobs/123456
            Output: https://boards.greenhouse.io/company

            Input:  https://jobs.lever.co/company/abc123-job-title
            Output: https://jobs.lever.co/company

            Input:  https://company.wd1.myworkdayjobs.com/CareerSite/job/Location/Title/JR123456
            Output: https://company.wd1.myworkdayjobs.com/CareerSite

        Args:
            job_url: Full URL to specific job posting

        Returns:
            Base career page URL, or empty string if unable to extract
        """
        if not job_url:
            return ""

        try:
            parsed = urlparse(job_url)
            domain = parsed.netloc
            path = parsed.path

            # Try known ATS platforms first
            if "greenhouse.io" in domain:
                return self._extract_greenhouse_url(domain, path) or ""

            if "lever.co" in domain:
                return self._extract_lever_url(domain, path) or ""

            if "myworkdayjobs.com" in domain:
                return self._extract_workday_url(domain, path) or ""

            # Generic company career page
            return self._extract_generic_careers_url(domain, path)

        except Exception as e:
            print(f"[CompanyDiscoverer] Error extracting careers URL from {job_url}: {e}")
            return ""

    def filter_by_company_names(
        self, companies: list[dict[str, str]], target_names: list[str]
    ) -> list[dict[str, str]]:
        """
        Filter companies to only include specified company names

        Args:
            companies: List of company dicts
            target_names: List of company names to include (case-insensitive)

        Returns:
            Filtered list of companies
        """
        target_names_lower = [name.lower() for name in target_names]

        filtered = [
            company for company in companies if company["name"].lower() in target_names_lower
        ]

        print(
            f"\n[CompanyDiscoverer] Filtered to {len(filtered)} companies (from {len(companies)})"
        )
        for company in filtered:
            print(f"  ✓ {company['name']}: {company['careers_url']}")

        return filtered
