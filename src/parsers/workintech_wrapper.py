"""
Wrapper class for Work In Tech parser to match ParserBase interface
"""

from email.message import Message

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser
from parsers.workintech_parser import can_parse, parse_workintech_email


class WorkInTechParser(BaseEmailParser):
    """Work In Tech job board parser"""

    def name(self) -> str:
        return "workintech"

    def can_handle(self, email_message: Message) -> bool:
        """Check if this parser can handle the given email"""
        from_addr = str(email_message.get("From", ""))
        subject = str(email_message.get("Subject", ""))
        return can_parse(from_addr, subject)

    def can_parse(self, from_addr: str, subject: str) -> bool:
        """Check if this parser can handle the email"""
        return can_parse(from_addr, subject)

    def parse(self, email_message: Message) -> ParserResult:
        """Parse Work In Tech email content"""
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

            # Parse using the workintech parser
            jobs = parse_workintech_email(content)

            # Convert to OpportunityData objects
            opportunities = [
                OpportunityData(
                    type="direct_job",
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    link=job["link"],
                    source="workintech",
                    source_email=from_email,
                )
                for job in jobs
            ]

            return ParserResult(parser_name=self.name, success=True, opportunities=opportunities)

        except Exception as e:
            return ParserResult(
                parser_name=self.name, success=False, opportunities=[], error=str(e)
            )
