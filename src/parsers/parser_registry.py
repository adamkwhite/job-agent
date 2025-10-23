"""
Parser registry - routes emails to appropriate parsers
"""
from email.message import Message
from typing import List, Optional
import json
from pathlib import Path

from models import ParserResult, OpportunityData
from parsers.base_parser import BaseEmailParser


class ParserRegistry:
    """Manages all email parsers and routes emails to appropriate handlers"""

    def __init__(self, config_path: str = "config/parsers.json"):
        self.parsers: List[BaseEmailParser] = []
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load parser configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"parsers": []}

    def register(self, parser: BaseEmailParser):
        """Register a new parser"""
        # Check if parser is enabled in config
        parser_config = self._get_parser_config(parser.name)

        if parser_config and parser_config.get('enabled', True):
            self.parsers.append(parser)
            print(f"Registered parser: {parser.name}")
        else:
            print(f"Skipped disabled parser: {parser.name}")

    def _get_parser_config(self, parser_name: str) -> Optional[dict]:
        """Get configuration for a specific parser"""
        for p in self.config.get('parsers', []):
            if p.get('name') == parser_name:
                return p
        return None

    def find_parser(self, email_message: Message) -> Optional[BaseEmailParser]:
        """
        Find the appropriate parser for an email

        Args:
            email_message: Email message object

        Returns:
            Parser that can handle this email, or None
        """
        for parser in self.parsers:
            if parser.can_handle(email_message):
                return parser
        return None

    def parse_email(self, email_message: Message) -> ParserResult:
        """
        Parse email using appropriate parser

        Args:
            email_message: Email message object

        Returns:
            ParserResult with opportunities
        """
        parser = self.find_parser(email_message)

        if parser:
            print(f"Using parser: {parser.name}")
            return parser.parse(email_message)
        else:
            # No parser found - return empty result
            return ParserResult(
                parser_name="unknown",
                success=False,
                opportunities=[],
                error=f"No parser found for email: {email_message.get('Subject', 'Unknown')}"
            )

    def get_enabled_parsers(self) -> List[str]:
        """Get list of enabled parser names"""
        return [p.name for p in self.parsers]


# Global registry instance
registry = ParserRegistry()


def get_registry() -> ParserRegistry:
    """Get the global parser registry"""
    return registry
