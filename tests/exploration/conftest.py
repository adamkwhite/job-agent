"""
Pytest configuration for exploration tests.

These are experimental/research tests that may have optional dependencies
not included in requirements.txt. Tests will be skipped if dependencies
are missing.
"""

import pytest


def pytest_configure(config):
    """Register custom markers for exploration tests."""
    config.addinivalue_line(
        "markers",
        "requires_scrapegraphai: mark test as requiring scrapegraphai package (may be skipped)",
    )


def pytest_collection_modifyitems(_config, items):
    """Skip exploration tests with missing dependencies."""
    skip_scrapegraphai = pytest.mark.skip(reason="scrapegraphai not available or incompatible")

    for item in items:
        # Skip test_llm_extraction.py if scrapegraphai import fails
        if "test_llm_extraction" in str(item.fspath):
            try:
                from scrapegraphai.graphs import SmartScraperGraph  # noqa: F401
            except ImportError:
                item.add_marker(skip_scrapegraphai)
