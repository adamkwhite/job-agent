"""Models package

Provides unified data models for the job agent.
"""

from pydantic import BaseModel, Field

from .company import Company


# Re-export ParserResult for backwards compatibility with existing parsers
# This is defined inline to avoid circular imports with src/models.py
class ParserResult(BaseModel):
    """Result from parsing an email"""

    parser_name: str
    success: bool
    opportunities: list = Field(default_factory=list)  # type: ignore
    error: str | None = None


__all__ = ["Company", "ParserResult"]
