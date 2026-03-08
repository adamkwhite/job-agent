#!/usr/bin/env python3
"""
Interactive profile onboarding script.

Walks through creating a new job agent profile, validates it loads,
backfills scores for existing jobs, and offers a dry-run digest.

Usage:
    PYTHONPATH=$PWD job-agent-venv/bin/python scripts/onboard_profile.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"
VENV_PYTHON = PROJECT_ROOT / "job-agent-venv" / "bin" / "python"


def prompt(label: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    value = input(f"  {label}{suffix}: ").strip()
    return value or default


def prompt_list(label: str, default: str = "") -> list[str]:
    """Prompt for comma-separated list."""
    raw = prompt(label, default)
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def prompt_yes_no(label: str, default: bool = False) -> bool:
    """Prompt for yes/no."""
    default_str = "Y/n" if default else "y/N"
    raw = prompt(f"{label} ({default_str})")
    if not raw:
        return default
    return raw.lower().startswith("y")


def _gather_scoring_info() -> dict[str, Any]:
    """Gather scoring-related profile fields via prompts."""
    print("\n--- TARGET ROLES ---")
    print("  Options: intern, junior, mid-level, senior, staff, lead, principal,")
    print("           director, senior director, vp, head of, cto, chief")
    target_seniority = prompt_list("Target seniority (comma-separated)")

    print("\n--- DOMAINS ---")
    print("  Examples: saas, cloud, ai, robotics, fintech, healthtech, enterprise")
    domain_keywords = prompt_list("Domain keywords (comma-separated)")
    exclude_domains = prompt_list("Domains to EXCLUDE (comma-separated)")

    print("\n--- ROLE TYPES ---")
    print("  Examples: engineering, engineering manager, vp engineering, r&d, cto")
    eng_roles = prompt_list(
        "Engineering leadership roles (comma-separated)",
        "engineering, engineering manager, director engineering, vp engineering, head of engineering",
    )

    print("\n--- COMPANY PREFERENCES ---")
    print("  Options: startup, seed, series a/b/c/d, growth, private, scale-up, public")
    company_stage = prompt_list(
        "Preferred company stages (comma-separated)", "growth, series b, series c, scale-up"
    )

    print("\n--- LOCATION ---")
    preferred_cities = prompt_list("Preferred cities (comma-separated)")
    preferred_regions = prompt_list("Preferred regions (comma-separated)", "ontario, canada")

    print("\n--- FILTERING ---")
    print("  conservative: Only filter explicit 'software engineer' IC titles")
    print("  moderate: Filter engineering roles at software companies")
    print("  aggressive: Filter any engineering role without hardware keywords")
    aggression = prompt("Filtering aggression", "conservative")

    avoid_keywords = ["junior", "associate", "intern", "coordinator"]
    avoid_keywords.extend(exclude_domains)

    return {
        "target_seniority": target_seniority,
        "domain_keywords": domain_keywords,
        "role_types": {"engineering_leadership": eng_roles},
        "company_stage": company_stage,
        "avoid_keywords": avoid_keywords,
        "location_preferences": {
            "remote_keywords": ["remote", "work from home", "wfh", "anywhere", "distributed"],
            "hybrid_keywords": ["hybrid"],
            "preferred_cities": preferred_cities,
            "preferred_regions": preferred_regions,
        },
        "filtering": {
            "aggression_level": aggression,
            "software_engineering_avoid": [
                "software engineer",
                "software engineering",
                "frontend",
                "backend",
                "full stack",
            ],
            "hardware_company_boost": 0,
            "software_company_penalty": 0,
        },
    }


def _gather_digest_info() -> tuple[dict[str, Any], dict[str, Any]]:
    """Gather digest and notification settings via prompts."""
    print("\n--- DIGEST ---")
    print("  A (85+), B (70+), C (55+), D (40+)")
    min_grade = prompt("Minimum digest grade", "B").upper()
    grade_scores = {"A": 85, "B": 70, "C": 55, "D": 40, "F": 0}
    min_score = int(prompt("Minimum digest score", str(grade_scores.get(min_grade, 70))))

    grade_order = ["A", "B", "C", "D", "F"]
    min_idx = grade_order.index(min_grade) if min_grade in grade_order else 1
    include_grades = grade_order[: min_idx + 1]

    digest = {
        "min_grade": min_grade,
        "min_score": min_score,
        "include_grades": include_grades,
        "send_frequency": "weekly",
    }
    notifications = {
        "enabled": False,
        "min_grade": min_grade,
        "min_score": min_score,
    }
    return digest, notifications


def gather_profile_info() -> dict[str, Any]:
    """Interactively gather profile information."""
    print("\n--- BASIC INFO ---")
    name = prompt("Full name")
    profile_id = prompt(
        "Profile ID (lowercase, for filename)", name.split()[0].lower() if name else ""
    )
    email = prompt("Email (where digests are sent)")

    scoring = _gather_scoring_info()
    digest, notifications = _gather_digest_info()

    has_inbox = prompt_yes_no("Does this person have their own job alerts email inbox?", False)
    inbox_config = {}
    if has_inbox:
        inbox_username = prompt("Gmail inbox address (e.g. name.jobalerts@gmail.com)")
        password_env = prompt(
            "App password env var name", f"{profile_id.upper()}_GMAIL_APP_PASSWORD"
        )
        inbox_config = {"username": inbox_username, "app_password_env": password_env}

    profile: dict[str, Any] = {
        "id": profile_id,
        "name": name,
        "email": email,
        "enabled": True,
        "scoring": scoring,
        "digest": digest,
        "notifications": notifications,
    }

    if inbox_config:
        profile["email_credentials"] = inbox_config

    return profile


def save_profile(profile: dict[str, Any]) -> Path:
    """Save profile JSON to profiles directory."""
    profile_id = profile["id"]
    json_path = PROFILES_DIR / f"{profile_id}.json"

    if json_path.exists() and not prompt_yes_no(f"  {json_path.name} already exists. Overwrite?"):
        print("  Aborted.")
        sys.exit(0)

    with open(json_path, "w") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")

    print(f"  Saved: {json_path}")
    return json_path


def validate_profile(profile_id: str) -> bool:
    """Validate the profile loads via ProfileManager."""
    result = subprocess.run(
        [
            str(VENV_PYTHON),
            "-c",
            f"""
from utils.profile_manager import get_profile_manager
pm = get_profile_manager()
p = pm.get_profile('{profile_id}')
print(f'Name: {{p.name}}')
print(f'Email: {{p.email}}')
print(f'Enabled: {{p.enabled}}')
enabled = [pr.id for pr in pm.get_enabled_profiles()]
print(f'All enabled: {{enabled}}')
""",
        ],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )

    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False

    for line in result.stdout.strip().split("\n"):
        print(f"  {line}")
    return True


def run_backfill(profile_id: str, max_jobs: int = 500) -> bool:
    """Run score backfill for the profile."""
    result = subprocess.run(
        [
            str(VENV_PYTHON),
            str(PROJECT_ROOT / "src" / "utils" / "rescore_jobs.py"),
            "--mode",
            "backfill",
            "--profile",
            profile_id,
            "--max-jobs",
            str(max_jobs),
        ],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"  Error: {result.stderr.strip()}")
        return False
    return True


def run_dry_digest(profile_id: str) -> bool:
    """Run a dry-run digest for the profile."""
    result = subprocess.run(
        [
            str(VENV_PYTHON),
            str(PROJECT_ROOT / "src" / "send_profile_digest.py"),
            "--profile",
            profile_id,
            "--dry-run",
            "--force-resend",
        ],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(PROJECT_ROOT),
            "COLUMNS": "160",
        },
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"  Error: {result.stderr.strip()}")
        return False
    return True


def print_onboarding_message(profile: dict[str, Any]) -> None:
    """Print a ready-to-send onboarding message."""
    name = profile["name"].split()[0]
    seniority = ", ".join(s.title() for s in profile["scoring"]["target_seniority"])
    domains = ", ".join(profile["scoring"]["domain_keywords"][:8])
    excluded = [
        k
        for k in profile["scoring"]["avoid_keywords"]
        if k not in ("junior", "associate", "intern", "coordinator")
    ]
    cities = ", ".join(
        c.title() for c in profile["scoring"]["location_preferences"]["preferred_cities"][:6]
    )
    regions = ", ".join(
        r.title() for r in profile["scoring"]["location_preferences"]["preferred_regions"]
    )
    min_grade = profile["digest"]["min_grade"]
    min_score = profile["digest"]["min_score"]

    exclude_line = ""
    if excluded:
        exclude_line = f"\n- **Excluded domains:** {', '.join(d.title() for d in excluded)}"

    msg = f"""
--- ONBOARDING MESSAGE (copy/paste) ---

Hey {name}, you're all set up in the job agent! Here's what to expect:

**Your profile settings:**
- **Target roles:** {seniority}
- **Domains:** {domains}{exclude_line}
- **Location:** Remote, or {cities} + {regions}

**Digest:**
- Weekly email to {profile["email"]} every Monday
- Only {min_grade}+ grade jobs (score {min_score}+)
- First digest should arrive this Monday

Let me know if you want to tweak anything (domains, cities, seniority level, digest frequency).

--- END ---
"""
    print(msg)


def main() -> None:
    """Run the interactive profile onboarding flow."""
    print("=" * 60)
    print("  JOB AGENT - PROFILE ONBOARDING")
    print("=" * 60)

    # Step 1: Gather info
    profile = gather_profile_info()

    # Step 2: Review
    print("\n--- REVIEW ---")
    print(json.dumps(profile, indent=2))
    if not prompt_yes_no("\n  Looks good? Save profile?", True):
        print("  Aborted.")
        sys.exit(0)

    # Step 3: Save
    print("\n--- SAVING PROFILE ---")
    save_profile(profile)

    # Step 4: Validate
    print("\n--- VALIDATING ---")
    if not validate_profile(profile["id"]):
        print("  Profile validation failed. Check the JSON and try again.")
        sys.exit(1)
    print("  Profile loaded successfully!")

    # Step 5: Backfill
    if prompt_yes_no("\n  Run backfill (score existing jobs for this profile)?", True):
        max_jobs = int(prompt("  Max jobs to backfill", "500"))
        print("\n--- BACKFILLING SCORES ---")
        run_backfill(profile["id"], max_jobs)

    # Step 6: Dry-run digest
    if prompt_yes_no("\n  Run dry-run digest (preview what they'd receive)?", True):
        print("\n--- DRY-RUN DIGEST ---")
        run_dry_digest(profile["id"])

    # Step 7: Onboarding message
    print("\n--- ONBOARDING MESSAGE ---")
    print_onboarding_message(profile)

    print("Done! Profile is ready for the next Monday cron run.")


if __name__ == "__main__":
    main()
