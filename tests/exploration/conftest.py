"""
Pytest configuration for exploration tests.

These are experimental/research scripts that may have optional dependencies
or require local cache files (data/firecrawl_cache/) not present in CI.
Scripts that run code at module level are excluded from collection entirely.
"""

from pathlib import Path

# Exclude scripts that execute code at module level and require local files.
# These are research scripts, not proper pytest test cases.
collect_ignore = [
    "run_claude_test.py",
    "test_claude_extraction.py",
    "test_scrapegraph_extraction.py",
]

# Also skip test_llm_extraction.py if the cache file is missing
_cache_file = Path("data/firecrawl_cache/boston_dynamics_20251130.md")
if not _cache_file.exists():
    collect_ignore.append("test_llm_extraction.py")
