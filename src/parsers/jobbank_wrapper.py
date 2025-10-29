"""
Wrapper class for Job Bank parser to match ParserBase interface
"""

from email.message import Message

from parsers.base_parser import BaseEmailParser
from parsers.jobbank_parser import can_parse, parse_jobbank_email


class JobBankParser(BaseEmailParser):
    """Job Bank Canada job alerts parser"""

    def name(self) -> str:
        return "jobbank"

    def can_handle(self, email_message: Message) -> bool:
        """Check if this parser can handle the given email"""
        from_addr = str(email_message.get("From", ""))
        subject = str(email_message.get("Subject", ""))
        return can_parse(from_addr, subject)

    def can_parse(self, from_addr: str, subject: str) -> bool:
        """Check if this parser can handle the email"""
        return can_parse(from_addr, subject)

    def parse(self, html_content: str) -> list[dict[str, str]]:
        """Parse Job Bank email content"""
        return parse_jobbank_email(html_content)
