"""
Send job digest to any profile
Multi-person version of send_digest_to_wes.py

Scoring includes company classification filtering (Issue #122):
- Company Fit: ±20 points (hardware boost or software penalty)
- Filtering based on aggression level (conservative/moderate/aggressive)

Usage:
    python src/send_profile_digest.py --profile wes
    python src/send_profile_digest.py --profile adam
    python src/send_profile_digest.py --all  # Send to all enabled profiles
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from database import JobDatabase
from utils.connections_manager import ConnectionsManager
from utils.job_validator import JobValidator
from utils.profile_manager import Profile, get_profile_manager

load_dotenv()


def _generate_job_table_rows(
    jobs: list[dict], connections_manager: ConnectionsManager | None = None
) -> str:
    """Generate HTML table rows for job listings"""
    rows = ""
    for job in jobs:
        score = job.get("fit_score", 0)
        grade = job.get("fit_grade", "N/A")
        breakdown = json.loads(job.get("score_breakdown", "{}"))
        location = job.get("location") or ""

        # Get connections for this company
        connections_cell = ""
        if connections_manager and connections_manager.connections_exist:
            try:
                summary = connections_manager.get_connection_summary(job["company"])
                if summary["count"] > 0:
                    # Build compact list of clickable names (max 4, no titles)
                    name_links = []
                    max_display = 4
                    for conn in summary["connections"][:max_display]:
                        if conn.url:
                            name_links.append(
                                f"<a href='{conn.url}' target='_blank' style='color: #0077b5; text-decoration: none;'>{conn.full_name}</a>"
                            )
                        else:
                            name_links.append(conn.full_name)

                    # Add "and X more" if there are additional connections
                    if summary["count"] > max_display:
                        remaining = summary["count"] - max_display
                        connections_cell = f"👥 {summary['count']}: {', '.join(name_links)}, <span style='color: #7f8c8d;'>and {remaining} more</span>"
                    else:
                        connections_cell = f"👥 {summary['count']}: {', '.join(name_links)}"
                else:
                    connections_cell = "—"
            except Exception:
                connections_cell = "—"
        else:
            connections_cell = "—"

        # Create LinkedIn search URL for 1st degree connections at this company
        import urllib.parse

        linkedin_search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(job['company'])}&network=%5B%22F%22%5D"

        # Check if job needs review (validation warning)
        validation_warning = ""
        if job.get("needs_review") or job.get("validation_reason"):
            reason = job.get("validation_reason", "unverified")

            # Different messages for LinkedIn vs other validation issues
            if reason in ["linkedin_unverifiable", "linkedin"]:
                validation_warning = f' <span style="color: #3498db; font-size: 11px; background: #ebf5fb; padding: 2px 6px; border-radius: 3px;" title="{reason}">🔒 Requires login to verify</span>'
            else:
                validation_warning = f' <span style="color: #e67e22; font-size: 11px; background: #fef5e7; padding: 2px 6px; border-radius: 3px;" title="{reason}">⚠️ Couldn\'t verify freshness</span>'

        rows += f"""
                <tr>
                    <td>
                        <div><a href="{linkedin_search_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600;">{job["company"]}</a></div>
                        <div class="company">📌 {location}</div>
                    </td>
                    <td class="job-title">
                        <a href="{job["link"]}" target="_blank">{job["title"]}</a>{validation_warning}
                    </td>
                    <td class="score-cell">{connections_cell}</td>
                    <td class="score-cell">{breakdown.get("seniority", 0)}</td>
                    <td class="score-cell">{breakdown.get("domain", 0)}</td>
                    <td class="score-cell">{breakdown.get("role_type", 0)}</td>
                    <td class="score-cell">{breakdown.get("location", 0)}</td>
                    <td class="score-cell">{breakdown.get("technical", 0)}</td>
                    <td class="score-cell">{breakdown.get("company_classification", 0):+d}</td>
                    <td class="score-cell">
                        <span class="score grade-{grade}">{score}</span>
                    </td>
                </tr>
            """
    return rows


def _generate_connections_section(
    jobs: list[dict], connections_manager: ConnectionsManager | None
) -> str:
    """Generate connections section showing all connections at job companies"""
    if not connections_manager or not connections_manager.connections_exist:
        return ""

    # Collect all companies with connections
    companies_with_connections = {}
    for job in jobs:
        try:
            summary = connections_manager.get_connection_summary(job["company"])
            # Only add if not already present (avoid duplicates)
            if summary["count"] > 0 and job["company"] not in companies_with_connections:
                companies_with_connections[job["company"]] = summary
        except Exception:
            continue

    if not companies_with_connections:
        return ""

    # Generate HTML
    html = """
        <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
            <h2 style="color: #34495e; margin-top: 0;">🤝 Your Connections at These Companies</h2>
    """

    # Sort by connection count (descending)
    sorted_companies = sorted(
        companies_with_connections.items(), key=lambda x: x[1]["count"], reverse=True
    )

    for company, summary in sorted_companies:
        html += f"""
            <div style="margin-bottom: 20px;">
                <h3 style="color: #2c3e50; margin-bottom: 8px;">{company} ({summary["count"]} connection{"s" if summary["count"] > 1 else ""})</h3>
                <ul style="list-style: none; padding-left: 0; margin: 0;">
        """
        for conn in summary["connections"]:
            # Make name clickable if URL is available
            if conn.url:
                name_html = f'<a href="{conn.url}" target="_blank" style="color: #0077b5; text-decoration: none; font-weight: 600;">{conn.full_name}</a>'
            else:
                name_html = f'<span style="font-weight: 600;">{conn.full_name}</span>'

            html += f'<li style="margin: 4px 0;">• {name_html} - {conn.position}</li>'

        html += """
                </ul>
            </div>
        """

    html += """
        </div>
    """

    return html


def _format_seniority_list(profile: Profile, max_items: int = 7) -> str:
    """Format seniority list: 'VP, Director, Head of...'"""
    items = profile.get_target_seniority()[:max_items]
    formatted = [item.title() for item in items]
    result = ", ".join(formatted)
    if len(profile.get_target_seniority()) > max_items:
        result += "..."
    return result


def _format_domain_list(profile: Profile, max_items: int = 10) -> str:
    """Format domain keywords: 'Robotics, Automation, IoT...'"""
    items = profile.get_domain_keywords()[:max_items]
    formatted = [item.title() for item in items]
    result = ", ".join(formatted)
    if len(profile.get_domain_keywords()) > max_items:
        result += "..."
    return result


def _format_role_types(profile: Profile) -> str:
    """Format role types: 'Engineering leadership > Product leadership'"""
    role_types = profile.scoring.get("role_types", {})
    type_names = [name.replace("_", " ").title() for name in role_types]
    return " > ".join(type_names) if type_names else "Not specified"


def _format_location_prefs(profile: Profile) -> str:
    """Format location: 'Remote (Toronto, Ontario), Hybrid'"""
    loc = profile.scoring.get("location_preferences", {})
    parts = []

    cities = loc.get("preferred_cities", [])[:3]
    regions = loc.get("preferred_regions", [])[:2]

    if loc.get("remote_keywords"):
        location_str = ", ".join([c.title() for c in cities + regions])
        if location_str:
            parts.append(f"Remote ({location_str})")
        else:
            parts.append("Remote")

    if loc.get("hybrid_keywords"):
        parts.append("Hybrid")

    return ", ".join(parts) if parts else "Not specified"


def generate_email_html(
    jobs: list[dict], profile: Profile, connections_manager: ConnectionsManager | None = None
) -> str:
    """Generate HTML email with top jobs for a specific profile"""

    # Filter for B+ and good grade jobs
    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    good_scoring = [j for j in jobs if 70 <= j.get("fit_score", 0) < 80]

    # Calculate total displayable jobs (70+)
    total_displayed = len(high_scoring) + len(good_scoring)

    # Get profile-specific targeting info
    target_seniority = ", ".join(profile.get_target_seniority()[:3])
    target_domains = ", ".join(profile.get_domain_keywords()[:5])

    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 14px;
            }}
            th {{
                background: #34495e;
                color: white;
                padding: 10px 8px;
                text-align: left;
                font-weight: 600;
                font-size: 12px;
            }}
            td {{
                padding: 10px 8px;
                border-bottom: 1px solid #ecf0f1;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            .job-title {{
                font-weight: 600;
                color: #2c3e50;
            }}
            .job-title a {{
                color: #3498db;
                text-decoration: none;
            }}
            .job-title a:hover {{
                text-decoration: underline;
            }}
            .company {{
                color: #7f8c8d;
                font-size: 13px;
            }}
            .connections-badge {{
                margin-top: 8px;
                padding: 6px 10px;
                background: #e3f2fd;
                border-left: 3px solid #2196f3;
                font-size: 13px;
                color: #1976d2;
                border-radius: 3px;
            }}
            .score {{
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 3px;
                display: inline-block;
                color: white;
            }}
            .score.grade-A {{
                background: #27ae60;
            }}
            .score.grade-B {{
                background: #3498db;
            }}
            .score.grade-C {{
                background: #f39c12;
            }}
            .score.grade-D {{
                background: #e67e22;
            }}
            .score-cell {{
                text-align: center;
                font-size: 13px;
            }}
            .summary {{
                background: #ecf0f1;
                padding: 20px;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #ecf0f1;
                font-size: 14px;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <h1>🎯 Your Personalized Job Matches</h1>

        <p>Hi {profile.name.split()[0]},</p>

        <p>I've analyzed <strong>{total_displayed} opportunities</strong> scored against your profile targeting <strong>{target_seniority}</strong> roles in <strong>{target_domains}</strong>.</p>

        <div class="summary">
            <strong>📊 Summary:</strong><br>
            • <strong>{len(high_scoring)}</strong> excellent matches (80+ score)<br>
            • <strong>{len(good_scoring)}</strong> good matches (70-79 score)<br>
            • Scored on: Seniority (30), Domain (25), Role Type (20), Location (15 if unrestricted remote/Canada-friendly), Technical (10), Company Fit (±20)
        </div>
    """

    if high_scoring:
        html += "<h2>⭐ Top Matches (80+ Score)</h2>"
        html += """
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Job Title</th>
                    <th style="text-align: center;">Connections</th>
                    <th style="text-align: center;">Seniority<br>/30</th>
                    <th style="text-align: center;">Domain<br>/25</th>
                    <th style="text-align: center;">Role<br>/20</th>
                    <th style="text-align: center;">Location<br>/15</th>
                    <th style="text-align: center;">Tech<br>/10</th>
                    <th style="text-align: center;">Company<br>Fit</th>
                    <th style="text-align: center;">Total<br>/115</th>
                </tr>
            </thead>
            <tbody>
        """
        html += _generate_job_table_rows(high_scoring, connections_manager)
        html += """
            </tbody>
        </table>
        """

    if good_scoring:
        html += "<h2>✅ Also Worth Considering (70-79 Score)</h2>"
        html += """
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Job Title</th>
                    <th style="text-align: center;">Connections</th>
                    <th style="text-align: center;">Seniority<br>/30</th>
                    <th style="text-align: center;">Domain<br>/25</th>
                    <th style="text-align: center;">Role<br>/20</th>
                    <th style="text-align: center;">Location<br>/15</th>
                    <th style="text-align: center;">Tech<br>/10</th>
                    <th style="text-align: center;">Company<br>Fit</th>
                    <th style="text-align: center;">Total<br>/115</th>
                </tr>
            </thead>
            <tbody>
        """
        html += _generate_job_table_rows(good_scoring, connections_manager)
        html += """
            </tbody>
        </table>
        """

    # Add connections section
    connections_section = _generate_connections_section(jobs, connections_manager)
    html += connections_section

    html += f"""
        <div class="footer">
            <p><strong>How scoring works for {profile.name}:</strong></p>
            <ul>
                <li><strong>Seniority (0-30):</strong> {_format_seniority_list(profile)}</li>
                <li><strong>Domain (0-25):</strong> {_format_domain_list(profile)}</li>
                <li><strong>Role Type (0-20):</strong> {_format_role_types(profile)}</li>
                <li><strong>Location (0-15):</strong> {_format_location_prefs(profile)}</li>
                <li><strong>Technical (0-10):</strong> Technical keyword matches</li>
            </ul>

            <p style="margin-top: 20px;">
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}<br>
                🤖 Powered by Job Agent
            </p>
        </div>
    </body>
    </html>
    """

    return html


def send_digest_to_profile(
    profile_id: str, force_resend: bool = False, dry_run: bool = False, max_age_days: int = 7
) -> bool:
    """
    Send digest email to a specific profile

    Args:
        profile_id: Profile ID to send digest to
        force_resend: Include previously sent jobs
        dry_run: Don't actually send, just show what would be sent
        max_age_days: Include jobs from last N days (default: 7)

    Returns:
        True if sent successfully
    """
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        print(f"Profile not found: {profile_id}")
        return False

    if not profile.enabled:
        print(f"Profile {profile_id} is disabled, skipping")
        return False

    print(f"\n{'=' * 60}")
    print(f"Generating digest for: {profile.name} ({profile.id})")
    print(f"{'=' * 60}")

    db = JobDatabase()

    # Get jobs for this profile's digest
    if force_resend:
        print("⚠️  Force resend mode - including previously sent jobs")
        # Get all jobs with scores for this profile
        jobs = db.get_jobs_for_profile_digest(
            profile_id=profile_id,
            min_grade="F",
            min_location_score=0,  # No location filtering in force-resend
            limit=100,
            max_age_days=max_age_days,
        )
    else:
        jobs = db.get_jobs_for_profile_digest(
            profile_id=profile_id,
            min_grade=profile.digest_min_grade,
            min_location_score=profile.digest_min_location_score,
            limit=100,
            max_age_days=max_age_days,
        )

    print(f"✓ Found {len(jobs)} unsent jobs for {profile.name}")

    if len(jobs) == 0:
        print(f"\n⏸  No new jobs to send to {profile.name}")
        return False

    # Validate job URLs before sending
    print("\n🔍 Validating job URLs...")
    validator = JobValidator(timeout=5)
    valid_jobs, flagged_jobs, invalid_jobs = validator.filter_valid_jobs(jobs)

    if flagged_jobs:
        print(f"  📋 {len(flagged_jobs)} jobs flagged for review (included in digest):")
        for job in flagged_jobs:
            reason = job.get("validation_reason", "unknown")
            print(f"    - {job['company']} - {job['title'][:50]}... ({reason})")
            print(f"      URL: {job.get('link', 'N/A')}")

    if invalid_jobs:
        print(f"  ⛔ Filtered out {len(invalid_jobs)} invalid jobs:")
        for job in invalid_jobs:
            reason = job.get("validation_reason", "unknown")
            print(f"    - {job['company']} - {job['title'][:50]}... ({reason})")
            print(f"      URL: {job.get('link', 'N/A')}")

        # Mark invalid jobs in database to skip future validation
        for job in invalid_jobs:
            job_hash = job.get("job_hash")
            reason = job.get("validation_reason", "invalid")

            # Simplify status values
            if reason.startswith("stale_"):
                url_status = "stale"
            elif reason == "404_not_found":
                url_status = "404"
            elif reason == "connection_error":
                url_status = "connection_error"
            elif reason == "invalid_response":
                url_status = "invalid_response"
            else:
                url_status = reason

            if job_hash:
                db.update_url_validation(job_hash, url_status)

    # Also mark valid jobs as validated
    if valid_jobs or flagged_jobs:
        for job in valid_jobs:
            job_hash = job.get("job_hash")
            if job_hash:
                db.update_url_validation(job_hash, "valid")
        for job in flagged_jobs:
            job_hash = job.get("job_hash")
            reason = job.get("validation_reason", "needs_review")

            # Simplify status values for flagged jobs
            if reason == "rate_limited_assumed_valid":
                url_status = "rate_limited"
            elif reason.startswith("linkedin_"):
                url_status = "linkedin"
            elif reason.startswith("generic_"):
                url_status = "generic_page"
            else:
                url_status = reason

            if job_hash:
                db.update_url_validation(job_hash, url_status)

    # Include both valid and flagged jobs in digest
    jobs = valid_jobs + flagged_jobs
    print(
        f"  ✓ {len(valid_jobs)} verified jobs + {len(flagged_jobs)} flagged for review = {len(jobs)} total"
    )

    # Filter for staleness (age + content check)
    print("\n🗓️  Filtering stale jobs...")
    fresh_jobs = []
    stale_jobs = []
    total = len(jobs)

    for idx, job in enumerate(jobs, 1):
        # Show progress
        company = job.get("company", "Unknown")[:20]
        title = job.get("title", "Unknown")[:30]
        print(f"  [{idx}/{total}] {company} - {title}...", end="", flush=True)

        is_valid, stale_reason = validator.validate_for_digest(job, use_cache=True)
        if is_valid:
            fresh_jobs.append(job)
            print(" ✓")
        else:
            stale_jobs.append((job, stale_reason))
            print(f" ⛔ {stale_reason}")
            # Update database with staleness reason
            job_hash = job.get("job_hash")
            if job_hash:
                db.update_url_validation(job_hash, stale_reason or "stale")

    jobs = fresh_jobs

    # Summary
    if stale_jobs:
        print(f"\n  ⛔ Filtered {len(stale_jobs)} stale jobs")
    print(f"  ✓ {len(jobs)} fresh jobs remaining")

    if len(jobs) == 0:
        print("\n⏸  No valid jobs to send after filtering")
        return False

    # Count by grade
    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    good_scoring = [j for j in jobs if j.get("fit_score", 0) >= 70]

    print(f"  - {len(high_scoring)} excellent matches (80+)")
    print(f"  - {len(good_scoring)} good matches (70+)")

    if dry_run:
        print(f"\n🧪 DRY RUN - Would send to {profile.email}")
        print(
            f"  Subject: 🎯 {len(high_scoring)} Job Matches - {datetime.now().strftime('%Y-%m-%d')}"
        )
        return True

    # Initialize connections manager for this profile
    connections_manager = ConnectionsManager(profile_name=profile_id)
    if connections_manager.connections_exist:
        print(f"✓ Loaded LinkedIn connections for {profile.name}")

    # Generate email HTML
    html_body = generate_email_html(jobs, profile, connections_manager)

    # Build email message
    msg = MIMEMultipart("mixed")

    if len(high_scoring) > 0:
        subject = f"🎯 {len(high_scoring)} Excellent Job Match{'es' if len(high_scoring) > 1 else ''} for You"
    elif len(good_scoring) > 0:
        subject = (
            f"✨ {len(good_scoring)} Good Job Match{'es' if len(good_scoring) > 1 else ''} Found"
        )
    else:
        subject = "📋 Job Digest - No Top Matches This Week"

    subject += f" - {datetime.now().strftime('%Y-%m-%d')}"

    # Use profile-specific email credentials
    gmail_user = profile.email_username
    gmail_password = profile.email_app_password

    # Fallback to legacy credentials if profile credentials not set
    if not gmail_password:
        print("  ⚠️  Using legacy GMAIL credentials (profile password not set)")
        gmail_user = os.getenv("GMAIL_USERNAME")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print(f"  ✗ No email credentials available for {profile_id}")
        return False

    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = profile.email

    # CC Adam on all digests for monitoring
    cc_email = "adamkwhite@gmail.com"
    msg["Cc"] = cc_email

    # Create message body
    text_body = f"""
Hi {profile.name.split()[0]},

I've found {len(high_scoring)} excellent job matches (80+ score) and {len(good_scoring)} good matches (70-79 score).

Open the HTML email to see full details and apply links.

Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}
"""

    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(text_body, "plain"))
    msg_alternative.attach(MIMEText(html_body, "html"))
    msg.attach(msg_alternative)

    # Send via SMTP
    try:
        print(f"\nSending digest to {profile.email}...")

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_password)

        # Send to both To and CC recipients
        recipients = [profile.email, cc_email]
        server.send_message(msg, to_addrs=recipients)
        server.quit()

        print(f"✓ Email sent successfully to {profile.email}")
        print(f"  CC: {cc_email}")
        print(f"📧 Subject: {subject}")

        # Mark jobs as sent for this profile
        if not force_resend:
            job_ids = [job["id"] for job in jobs]
            db.mark_profile_digest_sent(job_ids, profile_id)
            print(f"✓ Marked {len(job_ids)} jobs as sent for {profile.name}")

        return True

    except Exception as e:
        print(f"✗ Error sending email: {e}")
        import traceback

        traceback.print_exc()
        return False


def send_all_digests(force_resend: bool = False, dry_run: bool = False, max_age_days: int = 7):
    """Send digests to all enabled profiles"""
    manager = get_profile_manager()
    results = {}

    for profile in manager.get_enabled_profiles():
        success = send_digest_to_profile(
            profile.id, force_resend=force_resend, dry_run=dry_run, max_age_days=max_age_days
        )
        results[profile.id] = success

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for profile_id, success in results.items():
        status = "✓ Sent" if success else "✗ Not sent"
        print(f"  {profile_id}: {status}")

    return results


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Send job digest to profile(s)")
    parser.add_argument(
        "--profile",
        type=str,
        help="Profile ID to send digest to (e.g., 'wes', 'adam')",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Send digest to all enabled profiles",
    )
    parser.add_argument(
        "--force-resend",
        action="store_true",
        help="Include previously sent jobs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually send, just show what would be sent",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Include jobs from last N days (default: 7)",
    )

    args = parser.parse_args()

    if args.all:
        send_all_digests(
            force_resend=args.force_resend, dry_run=args.dry_run, max_age_days=args.max_age_days
        )
    elif args.profile:
        send_digest_to_profile(
            args.profile,
            force_resend=args.force_resend,
            dry_run=args.dry_run,
            max_age_days=args.max_age_days,
        )
    else:
        # Show available profiles
        manager = get_profile_manager()
        print("Available profiles:")
        for profile in manager.get_all_profiles():
            status = "✓" if profile.enabled else "✗"
            print(f"  {status} {profile.id}: {profile.name} ({profile.email})")
        print("\nUsage: python src/send_profile_digest.py --profile <id>")
        print("       python src/send_profile_digest.py --all")


if __name__ == "__main__":
    main()
