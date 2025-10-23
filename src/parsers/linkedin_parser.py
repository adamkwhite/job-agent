"""
LinkedIn job alert email parser
"""
from email.message import Message
from bs4 import BeautifulSoup
import re
from typing import List

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class LinkedInParser(BaseEmailParser):
    """Parse LinkedIn job alert emails"""

    def __init__(self):
        super().__init__()
        self.from_emails = ['jobs-noreply@linkedin.com', 'linkedin.com']
        self.subject_keywords = ['job alert', 'jobs matching', 'new jobs', 'jobs similar']

    def can_handle(self, email_message: Message) -> bool:
        """Check if this is a LinkedIn job alert email"""
        from_email = self.extract_email_address(email_message.get('From', '')).lower()
        subject = email_message.get('Subject', '').lower()

        # Get email body to check for LinkedIn content (handles forwarded emails)
        html_body, text_body = self.extract_email_body(email_message)
        body_text = (html_body + ' ' + text_body).lower()

        # Check if from LinkedIn or contains LinkedIn content
        is_from_linkedin = any(domain in from_email for domain in self.from_emails)
        is_linkedin_content = 'jobs-noreply@linkedin.com' in body_text or 'linkedin.com/jobs' in body_text

        # Check if subject matches job alert pattern
        is_job_alert = any(keyword in subject for keyword in self.subject_keywords)

        return (is_from_linkedin or is_linkedin_content) and is_job_alert

    def parse(self, email_message: Message) -> ParserResult:
        """Parse LinkedIn email and extract job opportunities"""
        try:
            from_email = self.extract_email_address(email_message.get('From', ''))
            html_body, text_body = self.extract_email_body(email_message)

            opportunities = []

            if html_body:
                opportunities = self._parse_html(html_body, from_email)
            elif text_body:
                opportunities = self._parse_text(text_body, from_email)

            return ParserResult(
                parser_name=self.name,
                success=True,
                opportunities=opportunities
            )

        except Exception as e:
            return ParserResult(
                parser_name=self.name,
                success=False,
                opportunities=[],
                error=str(e)
            )

    def _parse_html(self, html: str, from_email: str) -> List[OpportunityData]:
        """Parse HTML content for job listings"""
        soup = BeautifulSoup(html, 'lxml')
        opportunities = []

        # Find all links that look like job links
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')

            if not self.is_job_link(href):
                continue

            # Extract job details
            title = self._extract_title(link, soup)
            company = self._extract_company(link, soup)
            location = self._extract_location(link, soup)

            # Only add if we found at least a title or company
            if title or company:
                opportunity = OpportunityData(
                    source="linkedin",
                    source_email=from_email,
                    type="direct_job",
                    company=company or "Unknown",
                    title=title or "Job Opportunity",
                    location=location,
                    link=href,
                    needs_research=False  # We already have the job link
                )
                opportunities.append(opportunity)

        return opportunities

    def _parse_text(self, text: str, from_email: str) -> List[OpportunityData]:
        """Parse plain text content (fallback)"""
        opportunities = []

        # Find URLs in text
        urls = re.findall(r'https?://[^\s]+', text)

        for url in urls:
            if self.is_job_link(url):
                opportunity = OpportunityData(
                    source="linkedin",
                    source_email=from_email,
                    type="direct_job",
                    company="Unknown",
                    title="Job Opportunity",
                    link=url,
                    needs_research=False
                )
                opportunities.append(opportunity)

        return opportunities

    def _extract_title(self, link_element, soup: BeautifulSoup) -> str:
        """Extract job title from link or surrounding context"""
        # Try to get the full job info text from parent <tr>
        job_info = self._get_job_info_text(link_element)

        if job_info:
            # Parse the job info to extract just the title
            title, _, _ = self._parse_job_info(job_info)
            if title:
                return title

        # Fallback: Try link text first
        title = self.clean_text(link_element.get_text())

        if title and len(title) > 10:  # Reasonable title length
            return title

        # Try title attribute
        if link_element.get('title'):
            return link_element.get('title')

        return title

    def _extract_company(self, link_element, soup: BeautifulSoup) -> str:
        """Extract company name from link context"""
        # Try to get the full job info text from parent <tr>
        job_info = self._get_job_info_text(link_element)

        if job_info:
            # Parse the job info to extract just the company
            _, company, _ = self._parse_job_info(job_info)
            if company:
                return company

        # Fallback: old method
        parent = link_element.parent

        if parent:
            text = parent.get_text()

            # Try patterns like "Company: X" or "at X"
            company_match = re.search(r'(?:Company|Employer|at):\s*([^\n\|]+)', text, re.IGNORECASE)
            if company_match:
                return self.clean_text(company_match.group(1))

        return ''

    def _extract_location(self, link_element, soup: BeautifulSoup) -> str:
        """Extract location from link context"""
        # Try to get the full job info text from parent <tr>
        job_info = self._get_job_info_text(link_element)

        if job_info:
            # Parse the job info to extract just the location
            _, _, location = self._parse_job_info(job_info)
            if location:
                return location

        # Fallback: old method
        parent = link_element.parent

        if parent:
            text = parent.get_text()

            # Try patterns like "Location: X" or "in X"
            location_match = re.search(r'(?:Location|in):\s*([^\n\|]+)', text, re.IGNORECASE)
            if location_match:
                return self.clean_text(location_match.group(1))

            # Look for city, state patterns
            location_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b', text)
            if location_match:
                return location_match.group(1)

        return ''

    def _get_job_info_text(self, link_element) -> str:
        """Get the full job info text from parent <tr> or nearby container"""
        # LinkedIn emails typically have structure: <tr><td><a>...</a></td></tr>
        # The job info is in the <tr> text

        # Try parent <tr>
        parent = link_element.parent
        for _ in range(5):  # Search up to 5 levels
            if parent and parent.name == 'tr':
                text = parent.get_text(separator=' ', strip=True)
                # Filter out empty or very short text
                if text and len(text) > 10:
                    return text
            if parent:
                parent = parent.parent
            else:
                break

        return ''

    def _parse_job_info(self, job_info: str) -> tuple:
        """
        Parse LinkedIn job info text to extract title, company, location

        Format examples:
        - "Director of Product - Customer Care & AI Wealthsimple · Canada (Remote)"
        - "Senior Engineering Manager, Device Software Acme Corp · Toronto, ON"
        - "Product Manager - AI/ML · Remote"

        Returns:
            tuple: (title, company, location)
        """
        # Split by middle dot (·) to separate location
        parts = job_info.split('·')

        location = ''
        title_company_part = job_info

        if len(parts) >= 2:
            title_company_part = parts[0].strip()
            location = parts[1].strip()

        # Now parse title and company from the first part
        # Strategy: Find where the company name starts
        # Company names are typically capitalized words that come after the job title
        # Common pattern: "{Title with hyphens/commas} {CompanyName}"

        title = ''
        company = ''

        # Look for common title endings followed by company name
        # Examples: "Manager, Device Software" "Engineer -" "Director of Product -"

        # Try pattern: everything before last sequence of capitalized words
        words = title_company_part.split()

        # Find the last capitalized word sequence (likely the company)
        # Company names are typically the LAST capitalized word(s) with only alphanumeric chars
        company_start_idx = -1
        for i in range(len(words) - 1, -1, -1):
            word = words[i]
            # Remove punctuation for checking
            word_clean = re.sub(r'[^\w\s]', '', word)

            # Check if word looks like a company name (capitalized, alphanumeric only, not a common title word)
            if word_clean and word_clean[0].isupper() and word_clean.lower() not in [
                'senior', 'junior', 'lead', 'principal', 'staff', 'manager', 'director',
                'engineer', 'product', 'software', 'engineering', 'and', 'of', 'the', 'at', 'in',
                'care', 'ai', 'ml', 'remote', 'hybrid', 'device', 'media', 'solutions'
            ]:
                # Only consider it company name if it's alphanumeric (no slashes, dashes in middle)
                # Words like "AI/ML" or "E-Learning" are likely title parts, not company
                if '/' not in word and (i == len(words) - 1 or company_start_idx == -1):
                    company_start_idx = i
            else:
                # Stop when we hit lowercase or title words
                if company_start_idx != -1:
                    break

        if company_start_idx != -1 and company_start_idx < len(words):
            company = ' '.join(words[company_start_idx:])
            title = ' '.join(words[:company_start_idx]).strip()

        # If we couldn't parse, return the whole thing as title
        if not title:
            title = title_company_part

        return (title, company, location)
