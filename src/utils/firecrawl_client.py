"""
Firecrawl MCP Client Wrapper

Wraps Firecrawl MCP tool calls in a clean Python interface for use in scrapers.
"""

from typing import Any


class FirecrawlClient:
    """Client for Firecrawl MCP server integration"""

    def __init__(self):
        """Initialize Firecrawl client"""
        # MCP tools are called directly via function_calls in Claude Code
        # This wrapper provides a clean interface for scrapers
        pass

    def scrape(
        self,
        url: str,
        formats: list[str] | None = None,
        only_main_content: bool = True,
    ) -> dict[str, Any]:
        """
        Scrape a URL using Firecrawl

        Note: This method is a placeholder that documents the interface.
        In practice, the Firecrawl MCP tool is called directly by Claude Code
        using the mcp__firecrawl-mcp__firecrawl_scrape tool.

        Args:
            url: URL to scrape
            formats: List of formats to return (e.g., ["markdown", "html"])
            only_main_content: Extract only main content (default True)

        Returns:
            Dictionary with keys:
                - markdown: Page content as markdown
                - metadata: Page metadata (title, description, etc.)

        Example:
            result = firecrawl.scrape(
                "https://www.ministryoftesting.com/jobs",
                formats=["markdown"]
            )
            markdown = result.get("markdown", "")
        """
        raise NotImplementedError(
            "This method should be called via MCP tool: mcp__firecrawl-mcp__firecrawl_scrape"
        )

    @staticmethod
    def format_scrape_result(tool_result: dict) -> dict[str, Any]:
        """
        Format Firecrawl MCP tool result for scraper use

        Args:
            tool_result: Raw result from mcp__firecrawl-mcp__firecrawl_scrape

        Returns:
            Formatted result dict with markdown and metadata
        """
        return {
            "markdown": tool_result.get("markdown", ""),
            "html": tool_result.get("html", ""),
            "metadata": tool_result.get("metadata", {}),
            "status_code": tool_result.get("metadata", {}).get("statusCode"),
            "url": tool_result.get("metadata", {}).get("url"),
        }


def scrape_with_firecrawl(_url: str, _formats: list[str] | None = None) -> dict[str, Any]:
    """
    Helper function to document Firecrawl scraping usage

    This function serves as documentation for how to scrape with Firecrawl MCP.
    In practice, Claude Code calls the MCP tool directly.

    Args:
        _url: URL to scrape (unused, for documentation only)
        _formats: List of formats (unused, for documentation only)

    Returns:
        Formatted scrape result

    Usage in scrapers:
        # The scraper should expect to receive scrape results from Firecrawl
        # Claude Code will call the MCP tool and pass results to the scraper
        markdown = scrape_result.get("markdown", "")
        jobs = parse_jobs_from_markdown(markdown)
    """
    # This will be called by Claude Code via MCP
    # tool: mcp__firecrawl-mcp__firecrawl_scrape
    # parameters: {"url": url, "formats": formats}

    raise NotImplementedError("Use MCP tool: mcp__firecrawl-mcp__firecrawl_scrape")
