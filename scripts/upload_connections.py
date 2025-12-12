#!/usr/bin/env python3
"""Upload LinkedIn connections CSV for a user profile.

Usage:
    python scripts/upload_connections.py --profile wes connections.csv
    python scripts/upload_connections.py --profile adam ~/Downloads/Connections.csv
"""

import argparse
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.connections_manager import ConnectionsManager


def main():
    parser = argparse.ArgumentParser(
        description="Upload LinkedIn connections CSV for a user profile"
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Profile name (e.g., wes, adam, eli)",
    )
    parser.add_argument(
        "connections_csv",
        help="Path to LinkedIn Connections.csv export file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing connections file without confirmation",
    )

    args = parser.parse_args()

    # Validate input file exists
    source_file = Path(args.connections_csv)
    if not source_file.exists():
        print(f"❌ Error: File not found: {source_file}")
        sys.exit(1)

    # Initialize connections manager
    manager = ConnectionsManager(profile_name=args.profile)

    # Check if connections already exist
    if manager.connections_exist and not args.force:
        print(f"⚠️  Connections file already exists for profile '{args.profile}'")
        print(f"   Location: {manager.connections_file}")
        response = input("   Overwrite? (y/N): ")
        if response.lower() not in ("y", "yes"):
            print("   Upload cancelled.")
            sys.exit(0)

    # Create profile directory if it doesn't exist
    manager.profile_dir.mkdir(parents=True, exist_ok=True)

    # Validate CSV before copying
    print("📖 Validating CSV file...")
    temp_manager = ConnectionsManager(profile_name=args.profile)

    # Temporarily copy to validate
    temp_file = manager.profile_dir / "connections_temp.csv"
    shutil.copy2(source_file, temp_file)

    try:
        # Try to load connections (validates format)
        temp_manager.connections_file = temp_file
        connections = temp_manager.load_connections()

        # Validation passed - move temp file to actual location
        temp_file.rename(manager.connections_file)

        print(
            f"✅ Successfully uploaded {len(connections)} connections for profile '{args.profile}'"
        )
        print(f"   Location: {manager.connections_file}")
        print()
        print("Next steps:")
        print(f"  1. Run digest to see connections: ./run-tui.sh (select '{args.profile}')")
        print(f"  2. Or test manually: python src/send_profile_digest.py --profile {args.profile}")

    except (ValueError, FileNotFoundError) as e:
        # Validation failed - remove temp file
        if temp_file.exists():
            temp_file.unlink()
        print(f"❌ Error: {e}")
        print()
        print("Expected CSV format from LinkedIn export:")
        print("  Columns: First Name, Last Name, Email Address, Company, Position, Connected On")
        print()
        print("To export from LinkedIn:")
        print("  1. Go to https://www.linkedin.com/mypreferences/d/download-my-data")
        print("  2. Select 'Connections'")
        print("  3. Download the Connections.csv file")
        sys.exit(1)


if __name__ == "__main__":
    main()
