"""
Email Company Extractor

Extracts company names and career page URLs from job alert emails.
Replaces the old approach of extracting full job details from emails.

Simpler, more robust, and unified with other sources.
"""

import re
from email.message import Message

from models.company import Company


class EmailCompanyExtractor:
    """Extract company information from job alert emails"""

    def __init__(self):
        self.name = "email_company_extractor"

    def extract_companies(self, email: Message) -> list[Company]:
        """
        Extract companies from email

        Args:
            email: Email message object

        Returns:
            List of Company objects with name and careers_url
        """
        from_addr = email.get("From", "").lower()
        subject = email.get("Subject", "")
        body = self._get_email_body(email)

        # Determine email source
        if "linkedin" in from_addr:
            return self._extract_from_linkedin(body, subject)
        elif "supra" in from_addr or "product leadership" in subject.lower():
            return self._extract_from_supra(body, subject)
        elif "builtin" in from_addr:
            return self._extract_from_builtin(body, subject)
        elif "f6s" in from_addr:
            return self._extract_from_f6s(body, subject)
        elif "artemis" in from_addr or "artemis" in subject.lower():
            return self._extract_from_artemis(body, subject)
        else:
            # Generic extraction
            return self._extract_generic(body, subject)

    def _get_email_body(self, email: Message) -> str:
        """Extract email body text"""
        if email.is_multipart():
            for part in email.walk():
                if (
                    part.get_content_type() == "text/html"
                    or part.get_content_type() == "text/plain"
                ):
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="ignore")
        else:
            payload = email.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode("utf-8", errors="ignore")
        return ""

    def _extract_from_linkedin(self, body: str, _subject: str) -> list[Company]:
        """
        Extract companies from LinkedIn job alerts

        LinkedIn format:
        Job Title
        Company Name
        Location
        """
        companies = []

        # Known locations to filter out (cities, provinces, countries, remote)
        locations = {
            "remote",
            "hybrid",
            "on-site",
            "canada",
            "usa",
            "united states",
            "ontario",
            "quebec",
            "british columbia",
            "alberta",
            "toronto",
            "montreal",
            "vancouver",
            "ottawa",
            "calgary",
            "edmonton",
            "mississauga",
            "waterloo",
            "kitchener",
            "hamilton",
            "london",
            "new york",
            "san francisco",
            "seattle",
            "boston",
            "austin",
            "los angeles",
            "chicago",
            "denver",
            "portland",
            "santa clara",
        }

        # Pattern 1: Company after job title
        # LinkedIn emails have: "Job Title\nCompany Name\nLocation"
        # Split by lines and look for company names
        lines = body.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines or lines that are too short
            if len(line) < 3 or len(line) > 100:
                continue

            # Check if this looks like a company name (capitalized words)
            if (
                re.match(r"^[A-Z][A-Za-z0-9\s&.,\'-]+$", line)
                and line.lower() not in locations
                and i > 0
            ):
                # Check if the previous line looks like a job title (has common job keywords)
                prev_line = lines[i - 1].strip()
                job_keywords = [
                    "manager",
                    "director",
                    "engineer",
                    "lead",
                    "head",
                    "vp",
                    "president",
                    "analyst",
                    "specialist",
                    "coordinator",
                ]
                if any(keyword in prev_line.lower() for keyword in job_keywords):
                    company_name = line

                    # Skip if it's just a single letter or number
                    if len(company_name) < 2:
                        continue

                    # Skip footer/boilerplate text
                    skip_phrases = [
                        "you are receiving",
                        "unsubscribe",
                        "click here",
                        "view job",
                        "apply now",
                        "privacy policy",
                        "terms of service",
                    ]
                    if any(phrase in company_name.lower() for phrase in skip_phrases):
                        continue

                    # Construct LinkedIn careers URL
                    company_slug = (
                        company_name.lower().replace(" ", "-").replace("&", "and").replace("'", "")
                    )
                    careers_url = f"https://www.linkedin.com/company/{company_slug}/jobs/"

                    companies.append(
                        Company(
                            name=company_name,
                            careers_url=careers_url,
                            source="email",
                            source_details="LinkedIn job alert",
                        )
                    )

        return companies

    def _extract_from_supra(self, body: str, _subject: str) -> list[Company]:
        """
        Extract companies from Supra Product Leadership newsletter

        Format: *Company Name* is hiring a Job Title -
                URL
        """
        companies = []

        # Pattern: *Company Name* is hiring
        # Character class: letters, digits, &.,', whitespace, hyphen
        pattern = re.compile(
            r"\*([A-Za-z0-9&.,'\s\-]+)\*\s+is hiring", re.MULTILINE | re.IGNORECASE
        )

        matches = pattern.findall(body)

        for company_name in matches:
            company_name = company_name.strip()

            # Skip if too short or too long
            if len(company_name) < 2 or len(company_name) > 100:
                continue

            # Skip common false positives
            if company_name.lower() in ["supra", "subscribe", "forwarded"]:
                continue

            # Try to find the careers URL (usually on the next line after the company)
            # Look for the company in body, then find URL after it
            company_pos = body.find(f"*{company_name}*")
            if company_pos != -1:
                # Get next 500 chars
                context = body[company_pos : company_pos + 500]

                # Look for greenhouse, lever, ashby, workable, or other ATS URLs
                url_match = re.search(
                    r"https?://[^\s<>]+(?:greenhouse|lever|ashby|workable|jobs|careers|apply)[^\s<>]+",
                    context,
                )

                if url_match:
                    careers_url = url_match.group(0)
                    # Clean up URL (remove trailing characters)
                    careers_url = careers_url.rstrip(".,;)")
                else:
                    # Fallback: construct Google search URL
                    careers_url = (
                        f"https://www.google.com/search?q={company_name.replace(' ', '+')}+careers"
                    )
            else:
                careers_url = (
                    f"https://www.google.com/search?q={company_name.replace(' ', '+')}+careers"
                )

            companies.append(
                Company(
                    name=company_name,
                    careers_url=careers_url,
                    source="email",
                    source_details="Supra Product Leadership newsletter",
                )
            )

        return companies

    def _extract_from_builtin(self, body: str, _subject: str) -> list[Company]:
        """
        Extract companies from Built In job alerts

        Built In emails contain job URLs but not company names directly.
        We extract the job URLs and will scrape them individually.
        """
        companies = []

        # Built In wraps URLs in AWS tracking links
        # Pattern: https://cb4sdw3d.r.us-west-2.awstrack.me/L0/https:%2F%2Fbuiltin.com%2Fjob%2F...
        # Or direct: https://builtin.com/job/...

        # Find all href attributes that contain builtin.com/job URLs
        # Fixed ReDoS: Use explicit character sets to prevent backtracking
        # Matches both direct links and AWS tracking links containing builtin.com URLs
        # Character class: URL-safe chars (letters, digits, :/.%?=&_-)
        url_pattern = re.compile(
            r'href="([a-zA-Z0-9:/.%?=&_\-]*builtin\.com[a-zA-Z0-9:/.%?=&_\-]*)"', re.IGNORECASE
        )

        matches = url_pattern.findall(body)

        job_urls = []
        for url in matches:
            # Decode URL-encoded characters
            decoded_url = url.replace("%2F", "/").replace("%3F", "?").replace("%3D", "=")

            # Extract the actual builtin.com URL if wrapped in tracking
            if "builtin.com/job" in decoded_url:
                # Get just the builtin.com part
                builtin_match = re.search(r"(https://builtin\.com/job/[^&\s]+)", decoded_url)
                if builtin_match:
                    job_url = builtin_match.group(1)
                    # Remove query params
                    job_url = job_url.split("?")[0]
                    job_urls.append(job_url)

        # For Built In, we create one "company" per job since we don't know companies upfront
        # Alternative: return a generic Built In company that links to search
        # For now, let's return one entry that represents "check Built In jobs"

        if job_urls:
            # Return a single entry pointing to Built In jobs
            # The scraper can then process these URLs individually
            companies.append(
                Company(
                    name="Built In",
                    careers_url="https://builtin.com/jobs",
                    source="email",
                    source_details=f"Built In job alert ({len(job_urls)} jobs)",
                    notes=f"Job URLs: {', '.join(job_urls[:5])}",  # Store first 5 URLs
                )
            )

        return companies

    def _extract_from_f6s(self, body: str, _subject: str) -> list[Company]:
        """Extract companies from F6S job alerts"""
        companies = []

        # F6S has company names as headers
        pattern = re.compile(r"<h2[^>]*>([^<]+)</h2>", re.IGNORECASE)

        matches = pattern.findall(body)

        for company_name in matches:
            company_name = company_name.strip()

            if len(company_name) < 3 or "F6S" in company_name:
                continue

            careers_url = f"https://www.google.com/search?q={company_name}+careers"

            companies.append(
                Company(
                    name=company_name,
                    careers_url=careers_url,
                    source="email",
                    source_details="F6S job alert",
                )
            )

        return companies

    def _extract_from_artemis(self, body: str, _subject: str) -> list[Company]:
        """Extract companies from Artemis job alerts"""
        return self._extract_generic(body, _subject)

    def _extract_generic(self, body: str, _subject: str) -> list[Company]:
        """
        Generic company extraction

        Looks for:
        - URLs containing "career", "jobs", "hiring"
        - Company names near those URLs
        """
        companies = []

        # Find careers URLs
        url_pattern = re.compile(
            r"https?://([^/\s]+)/(?:careers?|jobs?|hiring|apply)[^\s]*", re.IGNORECASE
        )

        matches = url_pattern.findall(body)

        for domain in set(matches):  # Deduplicate
            # Extract company name from domain
            parts = domain.split(".")

            # Skip "www" prefix
            if parts[0].lower() == "www" and len(parts) > 1:
                company_name = parts[1].title()
            else:
                company_name = parts[0].title()

            # Skip if too short or looks like a TLD
            if len(company_name) < 3 or company_name.lower() in [
                "com",
                "org",
                "net",
                "ca",
                "uk",
                "gov",
            ]:
                continue

            careers_url = f"https://{domain}/careers"

            companies.append(
                Company(
                    name=company_name,
                    careers_url=careers_url,
                    source="email",
                    source_details="Generic job alert",
                )
            )

        return companies


# For testing
if __name__ == "__main__":
    extractor = EmailCompanyExtractor()
    print("Email Company Extractor initialized")
