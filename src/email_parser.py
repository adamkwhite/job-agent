"""
Email parser module for extracting job information from job alert emails
"""

import json
import re
from datetime import datetime
from email.message import Message

from bs4 import BeautifulSoup


class JobEmailParser:
    """Parse job alert emails and extract structured job data"""

    def __init__(self, config_path: str = "config/email-settings.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        self.sources = {s["from_email"]: s for s in self.config["job_alert_sources"]}

    def parse_email(self, email_message: Message) -> list[dict]:
        """
        Parse email and extract job listings

        Args:
            email_message: Email message object

        Returns:
            List of job dictionaries
        """
        # Get email metadata
        from_email = self._extract_email_address(email_message.get("From", ""))
        subject = email_message.get("Subject", "")
        email_message.get("Date", "")

        # Identify source
        source = self._identify_source(from_email, subject)

        # Extract email body
        body_html, body_text = self._extract_email_body(email_message)

        # Parse jobs from body
        jobs = self._extract_jobs(body_html, body_text, source)

        # Add metadata to each job
        for job in jobs:
            job["source_email"] = from_email
            job["received_at"] = datetime.now().isoformat()
            job["source"] = source["name"] if source else "Unknown"
            job["raw_email_content"] = body_text[:1000]  # Store first 1000 chars

        return jobs

    def _extract_email_address(self, from_field: str) -> str:
        """Extract email address from From field"""
        match = re.search(r"[\w\.-]+@[\w\.-]+", from_field)
        return match.group(0) if match else from_field

    def _identify_source(self, from_email: str, subject: str) -> dict | None:
        """Identify job alert source"""
        # Check known sources
        if from_email in self.sources:
            return self.sources[from_email]

        # Check subject line for hints
        subject_lower = subject.lower()
        for _email_addr, source in self.sources.items():
            for keyword in source.get("subject_contains", []):
                if keyword.lower() in subject_lower:
                    return source

        return None

    def _extract_email_body(self, email_message: Message) -> tuple:
        """Extract HTML and plain text body from email"""
        html_body = ""
        text_body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if payload and isinstance(payload, bytes):
                        if content_type == "text/html":
                            html_body = payload.decode("utf-8", errors="ignore")
                        elif content_type == "text/plain":
                            text_body = payload.decode("utf-8", errors="ignore")
                except Exception:  # Parsing external email content
                    continue
        else:
            payload = email_message.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                content_type = email_message.get_content_type()
                if content_type == "text/html":
                    html_body = payload.decode("utf-8", errors="ignore")
                elif content_type == "text/plain":
                    text_body = payload.decode("utf-8", errors="ignore")

        return html_body, text_body

    def _extract_jobs(self, html: str, text: str, source: dict | None) -> list[dict]:
        """Extract job listings from email content"""
        jobs = []

        if html:
            # Parse HTML content
            soup = BeautifulSoup(html, "lxml")
            jobs = self._parse_html_jobs(soup, source)

        if not jobs and text:
            # Fallback to text parsing
            jobs = self._parse_text_jobs(text)

        return jobs

    def _parse_html_jobs(self, soup: BeautifulSoup, _source: dict | None) -> list[dict]:
        """Parse jobs from HTML content"""
        jobs = []

        # Find all links that look like job links
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "")

            # Filter for job-related links
            if not self._is_job_link(href):
                continue

            # Extract job details
            job = {
                "link": href,
                "title": "",
                "company": "",
                "location": "",
                "description": "",
                "salary": "",
                "job_type": "",
                "posted_date": "",
            }

            # Try to find title in link text or nearby elements
            job["title"] = self._extract_title(link, soup)

            # Try to find company name
            job["company"] = self._extract_company(link, soup)

            # Try to find location
            job["location"] = self._extract_location(link, soup)

            # Only add if we found at least title or company
            if job["title"] or job["company"]:
                jobs.append(job)

        return jobs

    def _is_job_link(self, url: str) -> bool:
        """Check if URL looks like a job posting link"""
        job_keywords = ["job", "career", "position", "opening", "apply", "posting", "vacancy"]
        exclude_keywords = ["unsubscribe", "preferences", "settings", "privacy", "terms"]

        url_lower = url.lower()

        # Exclude non-job links
        if any(keyword in url_lower for keyword in exclude_keywords):
            return False

        # Include job links
        return any(keyword in url_lower for keyword in job_keywords)

    def _extract_title(self, link_element, _soup: BeautifulSoup) -> str:
        """Extract job title from link or surrounding context"""
        # Try link text first
        title = link_element.get_text(strip=True)

        if title and len(title) > 10:  # Reasonable title length
            return title

        # Try nearby heading or strong tags
        parent = link_element.parent
        if parent:
            # Check for headings
            for tag in ["h1", "h2", "h3", "h4", "strong", "b"]:
                heading = parent.find(tag)
                if heading:
                    text = heading.get_text(strip=True)
                    if len(text) > 5:
                        return text

        # Try title attribute
        if link_element.get("title"):
            return link_element.get("title")

        return title

    def _extract_company(self, link_element, _soup: BeautifulSoup) -> str:
        """Extract company name from link context"""
        parent = link_element.parent

        if parent:
            # Look for common company indicators
            text = parent.get_text()

            # Try patterns like "Company: X" or "at X"
            company_match = re.search(r"(?:Company|Employer|at):\s*([^\n\|]+)", text, re.IGNORECASE)
            if company_match:
                return company_match.group(1).strip()

            # Try finding text before location patterns
            parts = re.split(r"\s+-\s+|\s+in\s+|\s+\|\s+", text)
            if len(parts) > 1:
                return parts[1].strip()

        return ""

    def _extract_location(self, link_element, _soup: BeautifulSoup) -> str:
        """Extract location from link context"""
        parent = link_element.parent

        if parent:
            text = parent.get_text()

            # Try patterns like "Location: X" or "in X"
            location_match = re.search(r"(?:Location|in):\s*([^\n\|]+)", text, re.IGNORECASE)
            if location_match:
                return location_match.group(1).strip()

            # Look for city, state patterns
            location_match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b", text)
            if location_match:
                return location_match.group(1)

        return ""

    def _parse_text_jobs(self, text: str) -> list[dict]:
        """Parse jobs from plain text content (fallback)"""
        jobs = []

        # Find URLs in text
        urls = re.findall(r"https?://[^\s]+", text)

        for url in urls:
            if self._is_job_link(url):
                # Try to extract context around URL
                # This is a simple fallback - HTML parsing is preferred
                jobs.append(
                    {
                        "link": url,
                        "title": "Job Opportunity",  # Generic title
                        "company": "",
                        "location": "",
                        "description": "",
                        "salary": "",
                        "job_type": "",
                        "posted_date": "",
                    }
                )

        return jobs


if __name__ == "__main__":
    # Test the parser
    parser = JobEmailParser()
    print("Email parser initialized successfully")
