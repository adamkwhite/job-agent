"""
Wrapper class for Getro parser to match ParserBase interface.
Handles job alerts from all Getro-powered job boards (VC portfolios, accelerators,
innovation hubs): Work In Tech, MaRS, U of T Entrepreneurship, General Catalyst, etc.
"""

from email.message import Message

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser
from parsers.getro_parser import can_parse, parse_getro_email


class GetroParser(BaseEmailParser):
    """Getro job board email parser — covers 29+ boards via hello@getro.com"""

    def name(self) -> str:
        return "getro"

    def can_handle(self, email_message: Message) -> bool:
        """Check if this parser can handle the given email"""
        from_addr = str(email_message.get("From", ""))
        subject = str(email_message.get("Subject", ""))
        return can_parse(from_addr, subject)

    def can_parse(self, from_addr: str, subject: str) -> bool:
        """Check if this parser can handle the email"""
        return can_parse(from_addr, subject)

    def parse(self, email_message: Message) -> ParserResult:
        """Parse Getro job board email content"""
        try:
            from_email = self.extract_email_address(email_message.get("From", ""))
            html_body, text_body = self.extract_email_body(email_message)

            # Use HTML body if available, otherwise text
            content = html_body or text_body

            if not content:
                return ParserResult(
                    parser_name=self.name,
                    success=False,
                    opportunities=[],
                    error="No email content found",
                )

            # Parse using the Getro parser
            jobs = parse_getro_email(content)

            # Convert to OpportunityData objects
            opportunities = [
                OpportunityData(
                    type="direct_job",
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    link=job["link"],
                    source="getro",
                    source_email=from_email,
                )
                for job in jobs
            ]

            return ParserResult(parser_name=self.name, success=True, opportunities=opportunities)

        except Exception as e:
            return ParserResult(
                parser_name=self.name, success=False, opportunities=[], error=str(e)
            )
