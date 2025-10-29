"""
Base parser class - all email parsers inherit from this
"""

import re
from abc import ABC, abstractmethod
from email.message import Message

from src.models import ParserResult


class BaseEmailParser(ABC):
    """Abstract base class for all email parsers"""

    def __init__(self):
        self.name = self.__class__.__name__.replace("Parser", "").lower()

    @abstractmethod
    def can_handle(self, email_message: Message) -> bool:
        """
        Check if this parser can handle the given email

        Args:
            email_message: Email message object

        Returns:
            True if this parser should handle this email
        """
        pass

    @abstractmethod
    def parse(self, email_message: Message) -> ParserResult:
        """
        Parse email and extract opportunities

        Args:
            email_message: Email message object

        Returns:
            ParserResult with list of OpportunityData objects
        """
        pass

    # Helper methods available to all parsers

    def extract_email_address(self, from_field: str) -> str:
        """Extract email address from From field"""
        match = re.search(r"[\w\.-]+@[\w\.-]+", from_field)
        return match.group(0) if match else from_field

    def extract_email_body(self, email_message: Message) -> tuple:
        """
        Extract HTML and plain text body from email

        Returns:
            Tuple of (html_body, text_body)
        """
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
                except:
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

    def is_job_link(self, url: str) -> bool:
        """Check if URL looks like a job posting link"""
        job_keywords = [
            "job",
            "career",
            "position",
            "opening",
            "apply",
            "posting",
            "vacancy",
            "hiring",
        ]
        exclude_keywords = ["unsubscribe", "preferences", "settings", "privacy", "terms"]

        url_lower = url.lower()

        if any(keyword in url_lower for keyword in exclude_keywords):
            return False

        return any(keyword in url_lower for keyword in job_keywords)

    def clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace"""
        if not text:
            return ""
        # Remove multiple spaces/newlines
        text = re.sub(r"\s+", " ", text)
        return text.strip()
