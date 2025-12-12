#!/usr/bin/env python3
"""
Process job digest feedback emails and create GitHub issues

Monitors replies to digest emails, extracts feedback, and automatically
creates GitHub issues with job context and user feedback.

Usage:
    python scripts/process_feedback_emails.py --profile wes
    python scripts/process_feedback_emails.py --all-profiles
    python scripts/process_feedback_emails.py --dry-run
"""

import argparse
import contextlib
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from imap_client import IMAPEmailClient
from parsers.feedback_parser import FeedbackParser
from utils.profile_manager import get_profile_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_github_labels_exist(labels: list[str]) -> None:
    """
    Ensure all required GitHub labels exist, creating them if needed

    Args:
        labels: List of label names to check/create
    """
    # Label definitions with colors
    label_definitions = {
        "user-feedback": {
            "description": "User feedback from digest email replies",
            "color": "C5DEF5",
        },
        "false-positive": {"description": "Job incorrectly matched or scored", "color": "E99695"},
        "location-filtering": {
            "description": "Issues with location-based job filtering",
            "color": "FEF2C0",
        },
        "digest": {"description": "Email digest and summary features", "color": "BFD4F2"},
        "scoring": {"description": "Job scoring and fit evaluation features", "color": "0E8A16"},
    }

    for label in labels:
        if label in label_definitions:
            definition = label_definitions[label]
            # Try to create label, ignore if it already exists
            with contextlib.suppress(Exception):
                subprocess.run(
                    [
                        "gh",
                        "label",
                        "create",
                        label,
                        "--description",
                        definition["description"],
                        "--color",
                        definition["color"],
                    ],
                    capture_output=True,
                    text=True,
                    check=False,  # Don't raise error if label exists
                )


def create_github_issue(feedback: dict, profile_name: str, dry_run: bool = False) -> str | None:
    """
    Create GitHub issue from user feedback

    Args:
        feedback: Feedback dict from parser
        profile_name: Profile name (wes, adam, eli)
        dry_run: If True, print issue but don't create

    Returns:
        Issue URL if created, None otherwise
    """
    # Build issue title
    job_refs = feedback.get("job_references", [])
    if job_refs and "title" in job_refs[0] and "company" in job_refs[0]:
        job = job_refs[0]
        title = f"User Feedback: {job['title']} at {job['company']}"
    else:
        title = f"User Feedback from {profile_name.title()} - {datetime.now().strftime('%Y-%m-%d')}"

    # Build issue body
    body_parts = []

    # User feedback section
    body_parts.append("## User Feedback\n")
    body_parts.append(f"**From:** {profile_name.title()}\n")
    body_parts.append(f"**Email:** {feedback['user_email']}\n")
    body_parts.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    body_parts.append(feedback["feedback_text"])
    body_parts.append("\n\n")

    # Job references section (if any)
    if job_refs:
        body_parts.append("## Referenced Jobs\n\n")
        for i, job in enumerate(job_refs, 1):
            body_parts.append(f"**Job {i}:**\n")
            if "title" in job:
                body_parts.append(f"- Title: {job['title']}\n")
            if "company" in job:
                body_parts.append(f"- Company: {job['company']}\n")
            if "linkedin_job_id" in job:
                body_parts.append(
                    f"- Link: https://www.linkedin.com/jobs/view/{job['linkedin_job_id']}\n"
                )
            body_parts.append("\n")

    # Context section
    body_parts.append("## Context\n\n")
    body_parts.append(f"- **Original Subject:** {feedback['original_subject']}\n")
    body_parts.append("- **Source:** Digest email reply\n")
    body_parts.append(f"- **Profile:** {profile_name}\n\n")

    # Footer
    body_parts.append("---\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n")

    body = "".join(body_parts)

    # Determine labels based on feedback content
    labels = ["user-feedback", "digest"]
    feedback_lower = feedback["feedback_text"].lower()

    if any(kw in feedback_lower for kw in ["false positive", "shouldn't", "wrong"]):
        labels.append("false-positive")
    if any(kw in feedback_lower for kw in ["u.s. only", "us only", "country", "location"]):
        labels.append("location-filtering")
    if any(kw in feedback_lower for kw in ["score", "scoring", "points"]):
        labels.append("scoring")

    if dry_run:
        print("=" * 80)
        print("DRY RUN - Would create GitHub issue:")
        print("=" * 80)
        print(f"Title: {title}")
        print(f"Labels: {', '.join(labels)}")
        print(f"\nBody:\n{body}")
        print("=" * 80)
        return None

    # Ensure all required labels exist
    ensure_github_labels_exist(labels)

    # Create issue using gh CLI
    try:
        cmd = [
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--label",
            ",".join(labels),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issue_url = result.stdout.strip()
        logger.info(f"✅ Created issue: {issue_url}")
        return issue_url

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create GitHub issue: {e}")
        logger.error(f"stderr: {e.stderr}")
        return None


def process_feedback_emails(profile_id: str, limit: int = 50, dry_run: bool = False) -> int:
    """
    Process feedback emails for a profile

    Args:
        profile_id: Profile to process (wes, adam, eli)
        limit: Max emails to check
        dry_run: If True, don't create issues

    Returns:
        Number of issues created
    """
    logger.info(f"Processing feedback emails for profile: {profile_id}")

    # Get profile
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        logger.error(f"Profile not found: {profile_id}")
        return 0

    # Connect to IMAP (IMAPEmailClient reads credentials from .env)
    imap = IMAPEmailClient(profile=profile_id)
    parser = FeedbackParser()

    try:
        logger.info(f"Connecting to inbox for profile {profile_id}...")
        messages = imap.fetch_recent_emails(limit=limit)
        logger.info(f"Fetched {len(messages)} emails")

        issues_created = 0

        for msg in messages:
            from_addr = msg.get("From", "")
            subject_raw = msg.get("Subject", "")

            # Decode MIME-encoded subject
            import email.header

            decoded = email.header.decode_header(subject_raw)
            subject = ""
            for text, encoding in decoded:
                if isinstance(text, bytes):
                    subject += text.decode(encoding or "utf-8")
                else:
                    subject += text

            # Check if this is a feedback email
            if not parser.can_parse(msg, from_addr, subject):
                continue

            logger.info(f"Found feedback email: {subject}")

            # Parse feedback
            feedbacks = parser.parse(msg, from_addr, subject)

            for feedback in feedbacks:
                # Create GitHub issue
                issue_url = create_github_issue(feedback, profile_id, dry_run)
                if issue_url:
                    issues_created += 1

        logger.info(f"✅ Processed {len(messages)} emails, created {issues_created} issues")
        return issues_created

    except Exception as e:
        logger.error(f"Error processing feedback emails: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Process job digest feedback emails")

    # Get available profiles
    manager = get_profile_manager()
    available_profiles = manager.get_profile_ids()

    parser.add_argument(
        "--profile",
        type=str,
        choices=available_profiles,
        help="Profile to process feedback for",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Process feedback for all profiles",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max emails to check (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating",
    )

    args = parser.parse_args()

    if not args.profile and not args.all_profiles:
        parser.error("Either --profile or --all-profiles is required")

    # Process profiles
    profiles_to_process = available_profiles if args.all_profiles else [args.profile]

    total_issues = 0
    for profile_id in profiles_to_process:
        issues = process_feedback_emails(profile_id, limit=args.limit, dry_run=args.dry_run)
        total_issues += issues

    logger.info(f"\n🎉 Total issues created: {total_issues}")
    sys.exit(0 if total_issues > 0 else 1)


if __name__ == "__main__":
    main()
