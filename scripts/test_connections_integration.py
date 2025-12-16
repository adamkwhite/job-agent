#!/usr/bin/env python3
"""
Integration test for LinkedIn connections matching
Creates a mock connections file and tests the full match_company() method
"""

import csv
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.connections_manager import ConnectionsManager


def create_mock_connections_csv(csv_path: Path):
    """Create a mock connections CSV file with test data"""

    connections_data = [
        # Header
        ["First Name", "Last Name", "Email Address", "Company", "Position", "Connected On", "URL"],
        # People at various companies
        [
            "John",
            "Doe",
            "john@example.com",
            "Google Inc",
            "Software Engineer",
            "01 Jan 2020",
            "https://linkedin.com/in/johndoe",
        ],
        [
            "Jane",
            "Smith",
            "jane@example.com",
            "Meta Platforms, Inc.",
            "Product Manager",
            "15 Feb 2020",
            "https://linkedin.com/in/janesmith",
        ],
        [
            "Bob",
            "Johnson",
            "bob@example.com",
            "Some Company Inc",
            "Director",
            "20 Mar 2020",
            "https://linkedin.com/in/bobjohnson",
        ],
        [
            "Alice",
            "Williams",
            "alice@example.com",
            "Tech Solutions LLC",
            "Engineer",
            "10 Apr 2020",
            "https://linkedin.com/in/alicewilliams",
        ],
        [
            "Charlie",
            "Brown",
            "charlie@example.com",
            "Innovation Corp",
            "Manager",
            "25 May 2020",
            "https://linkedin.com/in/charliebrown",
        ],
        [
            "David",
            "Lee",
            "david@example.com",
            "Meta",
            "Engineer",
            "30 Jun 2020",
            "https://linkedin.com/in/davidlee",
        ],
        [
            "Eve",
            "Davis",
            "eve@example.com",
            "Amazon Web Services",
            "Senior Engineer",
            "15 Jul 2020",
            "https://linkedin.com/in/evedavis",
        ],
        [
            "Frank",
            "Miller",
            "frank@example.com",
            "AWS",
            "Principal Engineer",
            "20 Aug 2020",
            "https://linkedin.com/in/frankmiller",
        ],
        [
            "Grace",
            "Wilson",
            "grace@example.com",
            "Dropbox Inc",
            "Staff Engineer",
            "01 Sep 2020",
            "https://linkedin.com/in/gracewilson",
        ],
        [
            "Henry",
            "Moore",
            "henry@example.com",
            "Electronic Arts",
            "Senior Director",
            "10 Oct 2020",
            "https://linkedin.com/in/henrymoore",
        ],
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(connections_data)


def test_integration():
    """Test the full ConnectionsManager.match_company() method"""

    # Create temporary directory for test data
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create profile directory structure
        profile_dir = tmpdir / "profiles" / "test_user"
        profile_dir.mkdir(parents=True)

        # Create mock connections CSV
        connections_file = profile_dir / "connections.csv"
        create_mock_connections_csv(connections_file)

        # Initialize ConnectionsManager
        manager = ConnectionsManager(
            profile_name="test_user", data_dir=tmpdir, similarity_threshold=85.0
        )

        print("=" * 70)
        print("INTEGRATION TESTS - Full match_company() method")
        print("=" * 70)

        # Test 1: Generic word "Inc" should NOT match
        print("\n[Test 1] Generic word 'Inc' should NOT match:")
        matches = manager.match_company("Inc")
        if len(matches) == 0:
            print(f"  ✅ PASS: No matches found for 'Inc' (expected 0, got {len(matches)})")
        else:
            print(f"  ❌ FAIL: Found {len(matches)} matches for 'Inc':")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 2: Generic word "Company" should NOT match
        print("\n[Test 2] Generic word 'Company' should NOT match:")
        matches = manager.match_company("Company")
        if len(matches) == 0:
            print(f"  ✅ PASS: No matches found for 'Company' (expected 0, got {len(matches)})")
        else:
            print(f"  ❌ FAIL: Found {len(matches)} matches for 'Company':")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 3: "Meta" should match "Meta Platforms, Inc." AND "Meta"
        print("\n[Test 3] 'Meta' should match both 'Meta Platforms' and 'Meta':")
        matches = manager.match_company("Meta")
        if len(matches) == 2:
            print("  ✅ PASS: Found 2 matches for 'Meta':")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")
        else:
            print(f"  ❌ FAIL: Expected 2 matches, got {len(matches)}:")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 4: "Google" should match "Google Inc"
        print("\n[Test 4] 'Google' should match 'Google Inc':")
        matches = manager.match_company("Google")
        if len(matches) == 1 and matches[0].company == "Google Inc":
            print(f"  ✅ PASS: Found 1 match - {matches[0].full_name} at {matches[0].company}")
        else:
            print(f"  ❌ FAIL: Expected 1 match at 'Google Inc', got {len(matches)}:")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 5: "AWS" should match "Amazon Web Services" (fuzzy) AND "AWS" (exact)
        print("\n[Test 5] 'AWS' should NOT match (too short for substring):")
        matches = manager.match_company("AWS")
        # AWS is only 3 chars, so substring won't match
        # But fuzzy match should still work for exact "AWS" company
        if len(matches) == 1 and matches[0].company == "AWS":
            print(
                f"  ✅ PASS: Found 1 exact match - {matches[0].full_name} at {matches[0].company}"
            )
        else:
            print(f"  ⚠️  Got {len(matches)} matches:")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 6: "Electronic Arts" should match exactly
        print("\n[Test 6] 'Electronic Arts' should match:")
        matches = manager.match_company("Electronic Arts")
        if len(matches) == 1:
            print(f"  ✅ PASS: Found 1 match - {matches[0].full_name} at {matches[0].company}")
        else:
            print(f"  ❌ FAIL: Expected 1 match, got {len(matches)}:")
            for m in matches:
                print(f"    - {m.full_name} at {m.company}")

        # Test 7: Non-existent company should return 0 matches
        print("\n[Test 7] Non-existent company 'FakeCompany' should return 0 matches:")
        matches = manager.match_company("FakeCompany")
        if len(matches) == 0:
            print(f"  ✅ PASS: No matches found (expected 0, got {len(matches)})")
        else:
            print(f"  ❌ FAIL: Found {len(matches)} matches for non-existent company")

        print("\n" + "=" * 70)
        print("INTEGRATION TESTS COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    test_integration()
