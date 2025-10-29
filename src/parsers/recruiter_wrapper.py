"""
Wrapper class for Recruiter parser to match ParserBase interface
"""

from email.message import Message

from parsers.base_parser import BaseEmailParser
from parsers.recruiter_parser import can_parse, parse_recruiter_email


class RecruiterParser(BaseEmailParser):
    """Direct recruiter and LinkedIn saved jobs parser"""

    def name(self) -> str:
        return "recruiter"

    def can_handle(self, email_message: Message) -> bool:
        """Check if this parser can handle the given email"""
        from_addr = str(email_message.get("From", ""))
        subject = str(email_message.get("Subject", ""))
        return can_parse(from_addr, subject)

    def can_parse(self, from_addr: str, subject: str) -> bool:
        """Check if this parser can handle the email"""
        return can_parse(from_addr, subject)

    def parse(self, html_content: str) -> list[dict[str, str]]:
        """Parse recruiter email content"""
        return parse_recruiter_email(html_content)
