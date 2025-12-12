#!/usr/bin/env python3
"""
Generate a profile JSON file from a simple text template.

Usage:
    python scripts/generate_profile_json.py yourname

This reads profiles/yourname.txt and creates profiles/yourname.json
"""

import json
import sys
from pathlib import Path


def parse_value(value: str) -> str | list[str] | bool | int:
    """Parse a value from the text file into the appropriate Python type."""
    value = value.strip()

    # Boolean values
    if value.lower() in ("yes", "true", "enabled"):
        return True
    if value.lower() in ("no", "false", "disabled"):
        return False

    # Numeric values
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)

    # Comma-separated list
    if "," in value:
        return [item.strip() for item in value.split(",") if item.strip()]

    # Single string value
    return value


def parse_profile_txt(txt_path: Path) -> dict:
    """Parse a profile text file into a dictionary."""
    config = {}

    with open(txt_path) as f:
        for line in f:
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Skip section headers (lines that are just text without colons)
            if ":" not in line:
                continue

            # Parse key: value pairs
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # Skip if value is empty
            if not value:
                continue

            config[key] = parse_value(value)

    return config


def build_profile_json(config: dict) -> dict:
    """Build the full profile JSON structure from parsed config."""

    # Build role_types from individual role categories
    role_types = {}
    if "engineering_roles" in config:
        role_types["engineering"] = config["engineering_roles"]
    if "data_roles" in config:
        role_types["data"] = config["data_roles"]
    if "devops_roles" in config:
        role_types["devops"] = config["devops_roles"]
    if "product_roles" in config:
        role_types["product"] = config["product_roles"]

    # Build the profile JSON structure
    profile = {
        "name": config.get("name", ""),
        "email": config.get("email", ""),
        "enabled": config.get("enabled", True),
        "scoring": {
            "target_seniority": config.get("target_seniority", []),
            "domain_keywords": config.get("domain_keywords", []),
            "role_types": role_types,
            "company_stage": config.get("company_stage", []),
            "avoid_keywords": config.get("avoid_keywords", []),
            "location_preferences": {
                "remote_keywords": config.get("remote_keywords", []),
                "hybrid_keywords": config.get("hybrid_keywords", []),
                "preferred_cities": config.get("preferred_cities", []),
                "preferred_regions": config.get("preferred_regions", []),
            },
            "filtering": {
                "aggression_level": config.get("filtering_aggression", "moderate"),
                "software_engineering_avoid": [],
                "hardware_company_boost": config.get("hardware_company_boost", 0),
                "software_company_penalty": config.get("software_company_penalty", 0),
            },
        },
        "digest": {
            "min_grade": config.get("digest_min_grade", "C"),
            "min_score": config.get("digest_min_score", 63),
            "min_location_score": config.get("digest_min_location_score", 8),
            "include_grades": ["A", "B", "C", "D"],
            "send_frequency": config.get("digest_frequency", "weekly"),
        },
        "notifications": {
            "enabled": config.get("notifications_enabled", True),
            "min_grade": config.get("notifications_min_grade", "B"),
            "min_score": config.get("notifications_min_score", 80),
        },
    }

    # Add email credentials if provided
    email_username = config.get("email_username")
    app_password_env = config.get("app_password_env")

    if email_username and app_password_env:
        profile["email_credentials"] = {
            "username": email_username,
            "app_password_env": app_password_env,
        }

    # Auto-generate include_grades from min_grade
    min_grade = config.get("digest_min_grade", "C")
    grade_order = ["A", "B", "C", "D", "F"]
    if min_grade in grade_order:
        min_index = grade_order.index(min_grade)
        profile["digest"]["include_grades"] = grade_order[: min_index + 1]

    return profile


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_profile_json.py <profile_name>")
        print("Example: python scripts/generate_profile_json.py adam")
        print("\nThis reads profiles/adam.txt and creates profiles/adam.json")
        sys.exit(1)

    profile_name = sys.argv[1]

    # Paths
    project_root = Path(__file__).parent.parent
    txt_path = project_root / "profiles" / f"{profile_name}.txt"
    json_path = project_root / "profiles" / f"{profile_name}.json"

    # Check if text file exists
    if not txt_path.exists():
        print(f"❌ Error: Profile text file not found: {txt_path}")
        print("\nCreate it first by copying the template:")
        print(f"  cp profiles/TEMPLATE.txt profiles/{profile_name}.txt")
        print(f"  vim profiles/{profile_name}.txt")
        sys.exit(1)

    try:
        # Parse the text file
        print(f"📖 Reading profile from: {txt_path}")
        config = parse_profile_txt(txt_path)

        # Build JSON structure
        print("🔨 Building JSON structure...")
        profile = build_profile_json(config)

        # Write JSON file
        print(f"💾 Writing JSON to: {json_path}")
        with open(json_path, "w") as f:
            json.dump(profile, f, indent=2)

        print(f"\n✅ Success! Profile created at: {json_path}")
        print("\nNext steps:")
        print(f"  1. Review the generated JSON: cat {json_path}")
        print(f"  2. Test the profile: ./run-tui.sh (select '{profile_name}' profile)")
        print(
            f"  3. Add to .env if you have email credentials: {config.get('app_password_env', 'N/A')}"
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
