#!/usr/bin/env python3
"""
Test script to verify LinkedIn connections matching fix
Tests the problematic cases identified by Adam
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.connections_manager import ConnectionsManager


def test_substring_matching():
    """Test that short generic words don't match anymore"""

    manager = ConnectionsManager(profile_name="adam")

    # Test cases that should NOT match
    print("Testing problematic cases (should NOT match):")
    print("=" * 60)

    # Case 1: "Inc" should not match "Something Inc"
    job_company = "Inc"
    conn_company = "Google Inc"

    job_norm = manager.normalize_company_name(job_company)
    conn_norm = manager.normalize_company_name(conn_company)

    print(f"\nTest 1: '{job_company}' vs '{conn_company}'")
    print(f"  Normalized: '{job_norm}' vs '{conn_norm}'")
    print(f"  Job length: {len(job_norm)}, Connection length: {len(conn_norm)}")

    # Check if substring match would trigger
    min_length = 4
    if len(job_norm) >= min_length and len(conn_norm) >= min_length:
        if job_norm in conn_norm or conn_norm in job_norm:
            print("  ❌ FAIL: Would match (substring)")
        else:
            print("  ✓ PASS: Would not match (different strings)")
    else:
        print(
            f"  ✓ PASS: Would not match (too short: {len(job_norm)} or {len(conn_norm)} < {min_length})"
        )

    # Case 2: "Company" should not match random companies with "Company" in name
    job_company2 = "Company"
    conn_company2 = "Some Company Inc"

    job_norm2 = manager.normalize_company_name(job_company2)
    conn_norm2 = manager.normalize_company_name(conn_company2)

    print(f"\nTest 2: '{job_company2}' vs '{conn_company2}'")
    print(f"  Normalized: '{job_norm2}' vs '{conn_norm2}'")
    print(f"  Job length: {len(job_norm2)}, Connection length: {len(conn_norm2)}")

    # Check if generic word
    generic_words = ["company", "inc", "llc", "corp", "corporation", "ltd"]
    is_generic = job_norm2 in generic_words or conn_norm2 in generic_words

    if is_generic:
        print(f"  ✓ PASS: Would not match (generic word: '{job_norm2}' or '{conn_norm2}')")
    elif len(job_norm2) >= min_length and len(conn_norm2) >= min_length:
        if job_norm2 in conn_norm2 or conn_norm2 in job_norm2:
            print(f"  ⚠️  Would match (substring) - '{job_norm2}' in '{conn_norm2}'")
        else:
            print("  ✓ PASS: Would not match")
    else:
        print("  ✓ PASS: Would not match (too short)")

    # Test cases that SHOULD still match
    print("\n" + "=" * 60)
    print("Testing valid cases (SHOULD match):")
    print("=" * 60)

    # Case 3: "Meta" should match "Meta Platforms"
    job_company3 = "Meta"
    conn_company3 = "Meta Platforms, Inc."

    job_norm3 = manager.normalize_company_name(job_company3)
    conn_norm3 = manager.normalize_company_name(conn_company3)

    print(f"\nTest 3: '{job_company3}' vs '{conn_company3}'")
    print(f"  Normalized: '{job_norm3}' vs '{conn_norm3}'")
    print(f"  Job length: {len(job_norm3)}, Connection length: {len(conn_norm3)}")

    if len(job_norm3) >= min_length and len(conn_norm3) >= min_length:
        if job_norm3 in conn_norm3 or conn_norm3 in job_norm3:
            print("  ✓ PASS: Would match (substring)")
        else:
            print("  ❌ FAIL: Would not match")
    else:
        print("  ❌ FAIL: Too short to match")

    # Case 4: "Google" should match "Google LLC"
    job_company4 = "Google"
    conn_company4 = "Google LLC"

    job_norm4 = manager.normalize_company_name(job_company4)
    conn_norm4 = manager.normalize_company_name(conn_company4)

    print(f"\nTest 4: '{job_company4}' vs '{conn_company4}'")
    print(f"  Normalized: '{job_norm4}' vs '{conn_norm4}'")
    print(f"  Job length: {len(job_norm4)}, Connection length: {len(conn_norm4)}")

    if len(job_norm4) >= min_length and len(conn_norm4) >= min_length:
        if job_norm4 in conn_norm4 or conn_norm4 in job_norm4:
            print("  ✓ PASS: Would match (substring)")
        else:
            print("  ❌ FAIL: Would not match")
    else:
        print("  ❌ FAIL: Too short to match")


if __name__ == "__main__":
    test_substring_matching()
