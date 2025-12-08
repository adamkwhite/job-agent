#!/usr/bin/env python3
"""Test script for LLM failures UI - adds mock data and verifies database methods"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import JobDatabase


def main():
    db = JobDatabase()

    # Check current failures
    print("📊 Checking existing LLM failures...")
    pending = db.get_llm_failures(review_action="pending", limit=100)
    print(f"  Pending: {len(pending)}")

    retried = db.get_llm_failures(review_action="retry", limit=100)
    print(f"  Retry: {len(retried)}")

    skipped = db.get_llm_failures(review_action="skip", limit=100)
    print(f"  Skipped: {len(skipped)}")

    # Add mock failures if none exist
    if len(pending) == 0:
        print("\n➕ Adding mock LLM failures for testing...")

        mock_failures = [
            {
                "company_name": "Boston Dynamics",
                "failure_reason": "Timeout after 30 seconds",
                "markdown_path": "data/firecrawl_cache/boston_dynamics_20251207.md",
                "error_details": "Request timed out waiting for LLM response",
            },
            {
                "company_name": "Figure AI",
                "failure_reason": "JSON parsing error",
                "markdown_path": "data/firecrawl_cache/figure_ai_20251207.md",
                "error_details": "LLM returned invalid JSON format",
            },
            {
                "company_name": "Agility Robotics",
                "failure_reason": "API rate limit exceeded",
                "markdown_path": "data/firecrawl_cache/agility_robotics_20251207.md",
                "error_details": "OpenRouter API returned 429 Too Many Requests",
            },
            {
                "company_name": "Sanctuary AI",
                "failure_reason": "Empty response from LLM",
                "markdown_path": "data/firecrawl_cache/sanctuary_ai_20251207.md",
                "error_details": "LLM returned empty result array",
            },
            {
                "company_name": "Skydio",
                "failure_reason": "Invalid markdown format",
                "markdown_path": "data/firecrawl_cache/skydio_20251207.md",
                "error_details": "Markdown content too short (< 100 chars)",
            },
        ]

        for failure in mock_failures:
            failure_id = db.store_llm_failure(
                company_name=failure["company_name"],
                failure_reason=failure["failure_reason"],
                markdown_path=failure["markdown_path"],
                error_details=failure["error_details"],
            )
            print(f"  ✅ Added failure #{failure_id}: {failure['company_name']}")

        print(f"\n✨ Added {len(mock_failures)} mock failures")

    # Test update_llm_failure method
    print("\n🧪 Testing update_llm_failure() method...")
    failures = db.get_llm_failures(review_action="pending", limit=1)
    if failures:
        test_failure = failures[0]
        print(f"  Testing with failure #{test_failure['id']}: {test_failure['company_name']}")

        # Test marking as retry
        success = db.update_llm_failure(test_failure["id"], "retry")
        print(f"  Mark as retry: {'✅ Success' if success else '❌ Failed'}")

        # Verify it changed
        retried = db.get_llm_failures(review_action="retry", limit=1)
        if retried and retried[0]["id"] == test_failure["id"]:
            print("  Verification: ✅ Status updated correctly")

            # Reset back to pending
            db.update_llm_failure(test_failure["id"], "pending")
            print("  Reset to pending: ✅")
        else:
            print("  Verification: ❌ Status not updated")

    print("\n✅ Database methods working correctly!")
    print("\n📝 Next step: Run TUI to test the UI")
    print("   Command: ./run-tui.sh")


if __name__ == "__main__":
    main()
