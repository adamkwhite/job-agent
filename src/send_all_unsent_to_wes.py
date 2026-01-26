"""
Send ALL remaining unsent jobs to Wesley
Including lower-scoring jobs for completeness
"""

import json
import os
import smtplib
import sqlite3
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv


def generate_email_html(jobs_by_grade):
    """Generate HTML email with ALL unsent jobs grouped by grade"""

    total_jobs = sum(len(jobs) for jobs in jobs_by_grade.values())

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
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 8px;
            }}
            .summary {{
                background: #e8f4f8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .grade-section {{
                margin: 25px 0;
            }}
            .job {{
                background: #f8f9fa;
                border-left: 4px solid #95a5a6;
                padding: 12px;
                margin: 10px 0;
                border-radius: 4px;
            }}
            .job.grade-C {{
                border-left-color: #f39c12;
            }}
            .job.grade-D {{
                border-left-color: #e67e22;
            }}
            .job.grade-F {{
                border-left-color: #95a5a6;
                opacity: 0.9;
            }}
            .job-title {{
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 5px;
            }}
            .company {{
                color: #7f8c8d;
                margin-bottom: 3px;
                font-size: 14px;
            }}
            .score {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: 600;
                font-size: 13px;
                margin-right: 8px;
            }}
            .grade-C {{ background: #fff3cd; color: #856404; }}
            .grade-D {{ background: #f8d7da; color: #721c24; }}
            .grade-F {{ background: #e2e3e5; color: #383d41; }}
            .location {{
                color: #666;
                font-size: 13px;
                margin: 5px 0;
            }}
            .apply-btn {{
                display: inline-block;
                margin-top: 8px;
                padding: 6px 12px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 13px;
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
        </style>
    </head>
    <body>
        <h1>📋 All Remaining Job Opportunities</h1>

        <div class="summary">
            <h3>📊 Complete Job Inventory</h3>
            <p>
                <strong>{total_jobs}</strong> total unsent jobs<br>
    """

    for grade in ["C", "D", "F"]:
        if grade in jobs_by_grade:
            count = len(jobs_by_grade[grade])
            if grade == "C":
                html += f"<strong>{count}</strong> moderate matches (60-69 score)<br>"
            elif grade == "D":
                html += f"<strong>{count}</strong> lower matches (50-59 score)<br>"
            else:
                html += f"<strong>{count}</strong> minimal matches (below 50)<br>"

    html += """
            </p>
            <p style="margin-top: 10px; font-size: 13px; color: #666;">
                Note: These are all remaining jobs from the system, including lower-scoring opportunities
                that may still be worth reviewing.
            </p>
        </div>
    """

    # Grade C jobs (60-69)
    if "C" in jobs_by_grade and jobs_by_grade["C"]:
        html += "<h2>🟡 Moderate Matches (Grade C, 60-69 pts)</h2>"
        html += "<p style='color: #666; font-size: 14px;'>Jobs with some matching criteria</p>"
        for job in jobs_by_grade["C"]:
            score = job.get("fit_score", 0)
            html += f"""
            <div class="job grade-C">
                <div class="job-title">{job["title"]}</div>
                <div class="company">🏢 {job["company"]}</div>
                <span class="score grade-C">Score: {score}/115</span>
                <div class="location">📍 {job.get("location") or "Location not specified"}</div>
                <a href="{job["link"]}" class="apply-btn">View Job →</a>
            </div>
            """

    # Grade D jobs (50-59)
    if "D" in jobs_by_grade and jobs_by_grade["D"]:
        html += "<h2>🟠 Lower Matches (Grade D, 50-59 pts)</h2>"
        html += "<p style='color: #666; font-size: 14px;'>Jobs with fewer matching criteria</p>"
        for job in jobs_by_grade["D"]:
            score = job.get("fit_score", 0)
            html += f"""
            <div class="job grade-D">
                <div class="job-title">{job["title"]}</div>
                <div class="company">🏢 {job["company"]}</div>
                <span class="score grade-D">Score: {score}/115</span>
                <div class="location">📍 {job.get("location") or "Location not specified"}</div>
                <a href="{job["link"]}" class="apply-btn">View Job →</a>
            </div>
            """

    # Grade F jobs (below 50)
    if "F" in jobs_by_grade and jobs_by_grade["F"]:
        html += "<h2>⚪ Minimal Matches (Grade F, below 50 pts)</h2>"
        html += "<p style='color: #666; font-size: 14px;'>Jobs with minimal matching criteria - included for completeness</p>"
        for job in jobs_by_grade["F"][:20]:  # Limit to 20 to avoid huge email
            score = job.get("fit_score", 0)
            html += f"""
            <div class="job grade-F">
                <div class="job-title">{job["title"]}</div>
                <div class="company">🏢 {job["company"]}</div>
                <span class="score grade-F">Score: {score}/115</span>
                <div class="location">📍 {job.get("location") or "Location not specified"}</div>
                <a href="{job["link"]}" class="apply-btn">View Job →</a>
            </div>
            """

        if len(jobs_by_grade["F"]) > 20:
            html += f"""
            <p style="padding: 10px; background: #f0f0f0; border-radius: 5px; margin: 15px 0;">
                ... and {len(jobs_by_grade["F"]) - 20} more low-scoring jobs
            </p>
            """

    html += f"""
        <div class="footer">
            <p><strong>Scoring Reference:</strong></p>
            <ul style="font-size: 13px;">
                <li><strong>Grade A (85+):</strong> Perfect match</li>
                <li><strong>Grade B (70-84):</strong> Excellent match</li>
                <li><strong>Grade C (55-69):</strong> Good/moderate match</li>
                <li><strong>Grade D (40-54):</strong> Lower match</li>
                <li><strong>Grade F (<40):</strong> Minimal match</li>
            </ul>

            <p style="margin-top: 20px;">
                Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}<br>
                This email includes ALL remaining unsent jobs from the system.<br>
                🤖 Powered by Claude Code
            </p>
        </div>
    </body>
    </html>
    """

    return html


def main():
    """Send ALL unsent jobs to Wesley"""

    print("Sending ALL remaining unsent jobs to Wesley...")

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "jobs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get ALL UNSENT jobs
    cursor.execute("""
        SELECT id, title, company, location, link, fit_score, fit_grade, score_breakdown
        FROM jobs
        WHERE sent_to_wes = 0 OR sent_to_wes IS NULL
        ORDER BY fit_score DESC
    """)

    jobs_by_grade = {"C": [], "D": [], "F": []}
    all_job_ids = []

    for row in cursor.fetchall():
        job_id, title, company, location, link, fit_score, fit_grade, score_breakdown = row
        score_breakdown_dict = json.loads(score_breakdown) if score_breakdown else {}

        job_data = {
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "link": link,
            "fit_score": fit_score,
            "fit_grade": fit_grade,
            "score_breakdown": score_breakdown_dict,
        }

        all_job_ids.append(job_id)

        # Group by grade
        if fit_grade in ["C", "D", "F"]:
            jobs_by_grade[fit_grade].append(job_data)
        elif fit_score >= 60:
            jobs_by_grade["C"].append(job_data)
        elif fit_score >= 50:
            jobs_by_grade["D"].append(job_data)
        else:
            jobs_by_grade["F"].append(job_data)

    total_jobs = sum(len(jobs) for jobs in jobs_by_grade.values())

    if total_jobs == 0:
        print("No unsent jobs to send")
        conn.close()
        return

    print(f"Found {total_jobs} unsent jobs:")
    print(f"  - Grade C (60-69): {len(jobs_by_grade['C'])} jobs")
    print(f"  - Grade D (50-59): {len(jobs_by_grade['D'])} jobs")
    print(f"  - Grade F (<50):   {len(jobs_by_grade['F'])} jobs")

    # Generate email
    html_body = generate_email_html(jobs_by_grade)

    # Send to Wesley
    wes_email = "wesvanooyen@gmail.com"
    print(f"\nSending to {wes_email}...")

    try:
        load_dotenv()

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"📋 {total_jobs} Remaining Job Opportunities - Complete List"
        msg["From"] = os.getenv("GMAIL_USERNAME")
        msg["To"] = wes_email

        # Plain text version
        text_body = f"""
Hi Wes,

Here are ALL {total_jobs} remaining unsent jobs from the system:

Grade C (60-69 pts): {len(jobs_by_grade["C"])} jobs - Moderate matches
Grade D (50-59 pts): {len(jobs_by_grade["D"])} jobs - Lower matches
Grade F (<50 pts):   {len(jobs_by_grade["F"])} jobs - Minimal matches

These include all lower-scoring opportunities that weren't in previous digests.
While they score lower on the automated criteria, some may still be worth reviewing.

Open the HTML email to see all jobs with links.

Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}
"""

        # Create alternative part
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

        # Mark all jobs as sent
        timestamp = datetime.now().isoformat()
        for job_id in all_job_ids:
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
        print(f"✓ Marked {len(all_job_ids)} jobs as sent")

        print("\n📧 Summary:")
        print(f"   Subject: {total_jobs} Remaining Job Opportunities")
        print("   Content: All unsent jobs grouped by score")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
