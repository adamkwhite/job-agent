"""
Send job digest to Wesley van Ooyen - Version 2
Only sends NEW jobs that haven't been sent before
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


def generate_email_html(jobs):
    """Generate HTML email with NEW jobs only"""

    # Filter for B+ grade jobs (acceptable locations preferred)
    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    acceptable_scoring = [j for j in jobs if 70 <= j.get("fit_score", 0) < 80]

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
            .job {{
                background: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 15px;
                margin: 15px 0;
                border-radius: 4px;
            }}
            .job.new {{
                border-left: 4px solid #27ae60;
                background: #f0f9ff;
            }}
            .new-badge {{
                background: #27ae60;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 8px;
            }}
            .job-title {{
                font-size: 18px;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 8px;
            }}
            .company {{
                color: #7f8c8d;
                margin-bottom: 5px;
            }}
            .score {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: 600;
                margin-right: 10px;
            }}
            .grade-A {{ background: #d4edda; color: #155724; }}
            .grade-B {{ background: #cce5ff; color: #004085; }}
            .grade-C {{ background: #fff3cd; color: #856404; }}
            .grade-D {{ background: #f8d7da; color: #721c24; }}
            .location {{
                color: #666;
                font-size: 14px;
                margin: 8px 0;
            }}
            .score-breakdown {{
                font-size: 12px;
                color: #666;
                margin: 8px 0;
                padding: 8px;
                background: white;
                border-radius: 4px;
            }}
            .apply-btn {{
                display: inline-block;
                margin-top: 10px;
                padding: 8px 16px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            .apply-btn:hover {{
                background: #2980b9;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                font-size: 14px;
                color: #666;
            }}
            .summary {{
                background: #e8f4f8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>🎯 New Job Opportunities for Wesley</h1>

        <div class="summary">
            <h3>📊 New Jobs Summary</h3>
            <p>
                <strong>{len(jobs)}</strong> new job(s) since your last digest<br>
                <strong>{len(high_scoring)}</strong> excellent matches (80+ score)<br>
                <strong>{len(acceptable_scoring)}</strong> good matches (70-79 score)
            </p>
        </div>
    """

    if not jobs:
        html += """
        <p style="padding: 20px; background: #f0f0f0; border-radius: 8px;">
            No new job opportunities since your last digest. We'll notify you as soon as new matching positions become available!
        </p>
        """
    else:
        if high_scoring:
            html += "<h2>🏆 New Excellent Matches (80+ Score)</h2>"
            for job in high_scoring[:5]:  # Top 5
                score = job.get("fit_score", 0)
                grade = job.get("fit_grade", "N/A")
                breakdown = job.get("score_breakdown", {})

                html += f"""
                <div class="job new">
                    <span class="new-badge">NEW</span>
                    <div class="job-title">{job["title"]}</div>
                    <div class="company">🏢 {job["company"]}</div>
                    <div>
                        <span class="score grade-{grade}">Score: {score}/115 (Grade: {grade})</span>
                    </div>
                    <div class="location">📍 {job.get("location") or "Location not specified"}</div>
                    <div class="score-breakdown">
                        💼 Breakdown:
                        Seniority: {breakdown.get("seniority", 0)} |
                        Domain: {breakdown.get("domain", 0)} |
                        Role: {breakdown.get("role_type", 0)} |
                        Location: {breakdown.get("location", 0)}
                    </div>
                    <a href="{job["link"]}" class="apply-btn">View Job →</a>
                </div>
                """

        if acceptable_scoring:
            html += "<h2>✅ New Good Matches (70-79 Score)</h2>"
            for job in acceptable_scoring[:5]:
                score = job.get("fit_score", 0)
                grade = job.get("fit_grade", "N/A")

                html += f"""
                <div class="job new">
                    <span class="new-badge">NEW</span>
                    <div class="job-title">{job["title"]}</div>
                    <div class="company">📍 {job["company"]}</div>
                    <div>
                        <span class="score grade-{grade}">{grade} {score}/115</span>
                    </div>
                    <div class="location">📌 {job.get("location") or "Location not specified"}</div>
                    <a href="{job["link"]}" class="apply-btn">View Job →</a>
                </div>
                """

    html += f"""
        <div class="footer">
            <p><strong>How scoring works:</strong></p>
            <ul>
                <li><strong>Seniority (0-30):</strong> VP/Director roles score highest</li>
                <li><strong>Domain (0-25):</strong> Robotics, hardware, automation, IoT, MedTech</li>
                <li><strong>Role Type (0-20):</strong> Engineering leadership > Product leadership</li>
                <li><strong>Location (0-15):</strong> Remote, Hybrid Ontario, or Ontario cities</li>
                <li><strong>Technical (0-10):</strong> Mechatronics, embedded, manufacturing keywords</li>
            </ul>

            <p style="margin-top: 20px;">
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}<br>
                🤖 Powered by Claude Code
            </p>
        </div>
    </body>
    </html>
    """

    return html


def send_digest():
    """Send digest email to Wesley with ONLY NEW jobs"""

    print("Generating NEW job digest for Wesley van Ooyen...")

    # Initialize database
    import sqlite3

    db_path = Path(__file__).parent.parent / "data" / "jobs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, company, location, link, fit_score, fit_grade, score_breakdown
        FROM jobs
        WHERE (sent_to_wes = 0 OR sent_to_wes IS NULL)
        AND fit_score >= 70
        ORDER BY fit_score DESC
    """)

    jobs = []
    job_ids = []
    for row in cursor.fetchall():
        job_id, title, company, location, link, fit_score, fit_grade, score_breakdown = row
        score_breakdown_dict = json.loads(score_breakdown) if score_breakdown else {}
        jobs.append(
            {
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "link": link,
                "fit_score": fit_score,
                "fit_grade": fit_grade,
                "score_breakdown": score_breakdown_dict,
            }
        )
        job_ids.append(job_id)

    # Check if there are any new jobs to send
    if not jobs:
        print("❌ No new jobs to send to Wesley (all high-scoring jobs already sent)")
        print("\nTo see what's already been sent:")
        cursor.execute("""
            SELECT COUNT(*) FROM jobs WHERE sent_to_wes = 1
        """)
        sent_count = cursor.fetchone()[0]
        print(f"  - {sent_count} jobs already sent")

        cursor.execute("""
            SELECT COUNT(*) FROM jobs WHERE fit_score >= 70
        """)
        total_high = cursor.fetchone()[0]
        print(f"  - {total_high} total high-scoring jobs in database")

        conn.close()
        return

    print(f"✓ Found {len(jobs)} NEW unsent jobs")

    high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]
    good_scoring = [j for j in jobs if j.get("fit_score", 0) >= 70]

    print(f"  - {len(high_scoring)} excellent matches (80+)")
    print(f"  - {len(good_scoring)} good matches (70+)")

    # Generate HTML email
    html_body = generate_email_html(jobs)

    # Send to Wesley's email
    wes_email = "wesvanooyen@gmail.com"

    print(f"\nSending digest to {wes_email}...")

    try:
        load_dotenv()

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"🆕 {len(jobs)} New Job Matches - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = os.getenv("GMAIL_USERNAME")
        msg["To"] = wes_email

        # Plain text version
        text_body = f"""
Hi Wes,

I've found {len(jobs)} NEW job opportunities since your last digest:
- {len(high_scoring)} excellent matches (80+ score)
- {len([j for j in jobs if 70 <= j["fit_score"] < 80])} good matches (70-79 score)

These are all NEW positions that weren't in your previous digests.

Top new matches are scored based on:
- Director/VP seniority
- Robotics, hardware, automation, IoT domains
- Engineering leadership roles
- Remote or Ontario locations

Open the HTML email to see full details and apply links.

Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}
"""

        # Create alternative part for text/html
        msg_alternative = MIMEMultipart("alternative")
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg_alternative.attach(part1)
        msg_alternative.attach(part2)
        msg.attach(msg_alternative)

        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv("GMAIL_USERNAME"), os.getenv("GMAIL_APP_PASSWORD"))
        server.send_message(msg)
        server.quit()

        print(f"✓ Email sent successfully to {wes_email}")

        # Mark jobs as sent
        timestamp = datetime.now().isoformat()
        for job_id in job_ids:
            cursor.execute(
                """
                UPDATE jobs
                SET sent_to_wes = 1,
                    sent_to_wes_at = ?
                WHERE id = ?
            """,
                (timestamp, job_id),
            )

        conn.commit()
        print(f"✓ Marked {len(job_ids)} jobs as sent to Wes")

        print(
            f"\n📧 Subject: 🆕 {len(jobs)} New Job Matches - {datetime.now().strftime('%Y-%m-%d')}"
        )
        print(f"📊 Content: {len(jobs)} new jobs with scoring breakdown")

    except Exception as e:
        print(f"❌ Error sending email: {e}")
    finally:
        conn.close()


def main():
    """Main entry point"""
    send_digest()


if __name__ == "__main__":
    main()
