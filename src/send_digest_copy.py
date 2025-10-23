"""
Send a copy of Wesley's digest to Adam
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from send_digest_to_wes import JobDatabase, generate_email_html

load_dotenv()

# Get jobs
db = JobDatabase()
jobs = db.get_recent_jobs(limit=100)
jobs = sorted(jobs, key=lambda x: x.get("fit_score") or 0, reverse=True)

high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 80]

# Generate same HTML
html_body = generate_email_html(jobs)

# Send to Adam
adam_email = os.getenv("GMAIL_USERNAME")

msg = MIMEMultipart("mixed")
msg["Subject"] = (
    f"[COPY] 🎯 {len(high_scoring)} Top Job Matches for Wes - {datetime.now().strftime('%Y-%m-%d')}"
)
msg["From"] = adam_email
msg["To"] = adam_email

text_body = f"""
This is a copy of the email sent to Wesley van Ooyen.

{len(high_scoring)} excellent matches (80+)
{len([j for j in jobs if j.get("fit_score", 0) >= 70])} good matches (70+)

See HTML version for full details, or open the attached file for the interactive view.
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

# Send
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(os.getenv("GMAIL_USERNAME"), os.getenv("GMAIL_APP_PASSWORD"))
server.send_message(msg)
server.quit()

print(f"✓ Copy sent to {adam_email}")
