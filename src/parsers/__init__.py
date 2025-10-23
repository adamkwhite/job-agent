"""Email parsers for different job sources"""

from parsers.base_parser import BaseEmailParser
from parsers.parser_registry import ParserRegistry, get_registry

__all__ = ["BaseEmailParser", "ParserRegistry", "get_registry"]
