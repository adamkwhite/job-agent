"""Email parsers for different job sources"""

from .base_parser import BaseEmailParser
from .parser_registry import ParserRegistry, get_registry

__all__ = ["BaseEmailParser", "ParserRegistry", "get_registry"]
