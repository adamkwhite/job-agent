"""
Send job digest to Wesley van Ooyen
Email the top-scoring jobs that match his profile

⚠️ IMPORTANT: Email template scoring documentation (lines 222-238) must stay
in sync with actual scoring logic in src/agents/job_scorer.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import JobDatabase
from notifier import JobNotifier


def _generate_job_table_rows(jobs: list[dict]) -> str:
    """Generate HTML table rows for job listings (extracted to avoid duplication)"""
    rows = ""
    for job in jobs:
        score = job.get("fit_score", 0)
        grade = job.get("fit_grade", "N/A")
        breakdown = json.loads(job.get("score_breakdown", "{}"))
        location = job.get("location") or ""

        rows += f"""
                <tr>
                    <td>
                        <div>{job["company"]}</div>
                        <div class="company">📌 {location}</div>
                    </td>
                    <td class="job-title">
                        <a href="{job["link"]}" target="_blank">{job["title"]}</a>
                    </td>
                    <td class="score-cell">{breakdown.get("seniority", 0)}</td>
                    <td class="score-cell">{breakdown.get("domain", 0)}</td>
                    <td class="score-cell">{breakdown.get("role_type", 0)}</td>
                    <td class="score-cell">{breakdown.get("location", 0)}</td>
                    <td class="score-cell">{breakdown.get("technical", 0)}</td>
                    <td class="score-cell">
                        <span class="score grade-{grade}">{score}</span>
                    </td>
                </tr>
            """
    return rows


def generate_email_html(jobs, recipient_name="Wes"):
    """Generate HTML email with top jobs"""

    # Filter for B+ grade jobs (acceptable locations preferred)
    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    acceptable_scoring = [j for j in jobs if j.get("fit_score", 0) >= 70]

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

        <p>Hi {recipient_name},</p>

        <p>I've analyzed <strong>{len(jobs)} opportunities</strong> from LinkedIn, Supra Product Leadership Jobs, and the Robotics/Deeptech job board, scored against your profile as a <strong>Director/VP-level Engineering & Product leader</strong> in hardware, robotics, and IoT.</p>

        <div class="summary">
            <strong>📊 Summary:</strong><br>
            • <strong>{len(high_scoring)}</strong> excellent matches (80+ score)<br>
            • <strong>{len(acceptable_scoring)}</strong> good matches (70+ score)<br>
            • Scored on: Seniority (30), Domain (25), Role Type (20), Location (15), Technical (10)<br>
            • <strong>Location preferences applied:</strong> Remote (+15 pts), Hybrid Ontario (+15 pts), Ontario cities (+12 pts)
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
                    <th style="text-align: center;">Seniority<br>/30</th>
                    <th style="text-align: center;">Domain<br>/25</th>
                    <th style="text-align: center;">Role<br>/20</th>
                    <th style="text-align: center;">Location<br>/15</th>
                    <th style="text-align: center;">Tech<br>/10</th>
                    <th style="text-align: center;">Total<br>/115</th>
                </tr>
            </thead>
            <tbody>
        """

        html += _generate_job_table_rows(high_scoring[:10])

        html += """
            </tbody>
        </table>
        """

    if acceptable_scoring and len(acceptable_scoring) > len(high_scoring):
        html += "<h2>✅ Also Worth Considering (70-79 Score)</h2>"
        html += """
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Job Title</th>
                    <th style="text-align: center;">Seniority<br>/30</th>
                    <th style="text-align: center;">Domain<br>/25</th>
                    <th style="text-align: center;">Role<br>/20</th>
                    <th style="text-align: center;">Location<br>/15</th>
                    <th style="text-align: center;">Tech<br>/10</th>
                    <th style="text-align: center;">Total<br>/115</th>
                </tr>
            </thead>
            <tbody>
        """

        html += _generate_job_table_rows(
            acceptable_scoring[len(high_scoring) : len(high_scoring) + 5]
        )

        html += """
            </tbody>
        </table>
        """

    html += f"""
        <div class="footer">
            <p><strong>How scoring works (updated Nov 2025 - 7-Category System):</strong></p>
            <ul>
                <li><strong>Seniority (0-30):</strong> VP/C-level (30), Director (25), Sr Manager/Principal (15), Manager/Lead (10)</li>
                <li><strong>Domain (0-25):</strong> Robotics/Hardware/Automation (25), MedTech (20), Physical Products (15), Engineering (10)</li>
                <li><strong>Role Type (0-20 base + keyword bonuses):</strong>
                    <ul style="margin-top: 5px; font-size: 13px;">
                        <li>Product Leadership (15-20) | Engineering Leadership (15-20)</li>
                        <li>Technical Program Management (12-18) | Manufacturing/NPI/Operations (12-18)</li>
                        <li>Platform/Integrations/Systems (15-18) | Product Development/R&D (10-15)</li>
                        <li>Robotics/Automation Engineering (10-15) | <strong>Software penalty: -5</strong></li>
                        <li>+2 bonus per matched keyword (roadmap, platform, dfm, npi, etc.)</li>
                    </ul>
                </li>
                <li><strong>Location (0-15):</strong> Remote (15), Hybrid Ontario (15), Ontario cities (12), Broader Canada (8)</li>
                <li><strong>Company Stage (0-15):</strong> Series A-C, growth stage (default: 10)</li>
                <li><strong>Technical Keywords (0-10):</strong> Robotics, automation, IoT, mechatronics, embedded, manufacturing (+2 each)</li>
            </ul>

            <p><strong>📊 Full results:</strong> Open the attached HTML file to see all {len(jobs)} jobs with interactive location filters.</p>

            <p style="margin-top: 20px;">
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}<br>
                🤖 Powered by Claude Code
            </p>
        </div>
    </body>
    </html>
    """

    return html


def send_digest(force_resend: bool = False, test_email: str | None = None):
    """Send digest email to Wesley

    Args:
        force_resend: If True, send all jobs regardless of digest_sent_at status
    """

    print("Generating job digest for Wesley van Ooyen...")

    # Get jobs that haven't been sent in digest yet
    db = JobDatabase()

    if force_resend:
        print("⚠️  Force resend mode - including previously sent jobs")
        jobs = db.get_recent_jobs(limit=100)
        jobs = sorted(jobs, key=lambda x: x.get("fit_score") or 0, reverse=True)
    else:
        jobs = db.get_jobs_for_digest(limit=100)

    print(f"✓ Found {len(jobs)} {'total' if force_resend else 'unsent'} jobs in database")

    # If no unsent jobs, skip sending
    if len(jobs) == 0:
        print("\n⏸  No new jobs to send - all jobs have been sent in previous digests")
        return False

    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    good_scoring = [j for j in jobs if j.get("fit_score", 0) >= 70]

    print(f"  - {len(high_scoring)} excellent matches (80+)")
    print(f"  - {len(good_scoring)} good matches (70+)")

    # Generate HTML email with appropriate recipient name
    recipient_name = "Adam" if test_email else "Wes"
    html_body = generate_email_html(jobs, recipient_name=recipient_name)

    # Send via notifier
    JobNotifier()

    # Send to Wesley's email (or test email if specified)
    wes_email = test_email if test_email else "wesvanooyen@gmail.com"

    if test_email:
        print(f"\n🧪 TEST MODE - Sending digest to {wes_email}...")
    else:
        print(f"\nSending digest to {wes_email}...")

    try:
        # Use the notifier's email functionality
        import os
        import smtplib
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        from dotenv import load_dotenv

        load_dotenv()

        msg = MIMEMultipart("mixed")

        # Generate subject line based on findings
        if len(high_scoring) > 0:
            subject = f"🎯 {len(high_scoring)} Excellent Job Match{'es' if len(high_scoring) > 1 else ''} for You"
        elif len(good_scoring) > 0:
            subject = f"✨ {len(good_scoring)} Good Job Match{'es' if len(good_scoring) > 1 else ''} Found"
        else:
            subject = "📋 Job Digest - No Top Matches This Week"

        subject += f" - {datetime.now().strftime('%Y-%m-%d')}"
        msg["Subject"] = subject
        gmail_user = os.getenv("GMAIL_USERNAME")
        if not gmail_user:
            raise ValueError("GMAIL_USERNAME environment variable not set")
        msg["From"] = gmail_user
        msg["To"] = wes_email

        # Only CC Adam if not in test mode
        if not test_email:
            msg["Cc"] = "adamkwhite@gmail.com"

        # Plain text version
        text_body = f"""
Hi Wes,

I've found {len(high_scoring)} excellent job matches (80+ score) and {len(good_scoring)} good matches (70+ score) from LinkedIn, Supra, and the Robotics/Deeptech job board.

Top matches are scored based on:
- Director/VP seniority
- Robotics, hardware, automation, IoT domains
- Engineering leadership roles
- Remote or Ontario locations

Open the HTML email to see full details and apply links, or open the attached file for the interactive view.

Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}
"""

        # Create alternative part for text/html
        msg_alternative = MIMEMultipart("alternative")
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg_alternative.attach(part1)
        msg_alternative.attach(part2)
        msg.attach(msg_alternative)

        # Attach the jobs.html file
        html_file_path = Path(__file__).parent.parent / "jobs.html"
        if html_file_path.exists():
            with open(html_file_path, "rb") as f:
                attachment = MIMEBase("text", "html")
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition",
                    f'attachment; filename="job_opportunities_{datetime.now().strftime("%Y-%m-%d")}.html"',
                )
                msg.attach(attachment)
            print(f"  ✓ Attached jobs.html ({html_file_path.stat().st_size / 1024:.1f} KB)")
        else:
            print(f"  ⚠️  jobs.html not found at {html_file_path}")

        # Send via SMTP
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if not gmail_password:
            raise ValueError("GMAIL_APP_PASSWORD environment variable not set")
        server.login(gmail_user, gmail_password)

        # Send to both To and CC recipients
        recipients = [wes_email]
        if not test_email:
            recipients.append("adamkwhite@gmail.com")

        server.send_message(msg, to_addrs=recipients)
        server.quit()

        print(f"✓ Email sent successfully to {wes_email}")
        if not test_email:
            print("  CC: adamkwhite@gmail.com")
        print(f"\n📧 Subject: {msg['Subject']}")
        print(f"📊 Content: {len(high_scoring)} top matches + scoring breakdown")

        # Mark all jobs as sent in digest (unless force_resend mode)
        if not force_resend:
            job_ids = [job["id"] for job in jobs]
            db.mark_digest_sent(job_ids)
            print(f"✓ Marked {len(job_ids)} jobs as sent in digest")
        else:
            print("⚠️  Force resend mode - jobs NOT marked as sent")

        return True

    except Exception as e:
        print(f"✗ Error sending email: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send weekly job digest to Wesley")
    parser.add_argument(
        "--force-resend",
        action="store_true",
        help="Force resend all jobs, ignoring digest_sent_at status",
    )
    parser.add_argument(
        "--test-email",
        type=str,
        help="Send to test email instead of Wesley (e.g., adamkwhite@gmail.com)",
    )

    args = parser.parse_args()
    send_digest(force_resend=args.force_resend, test_email=args.test_email)
