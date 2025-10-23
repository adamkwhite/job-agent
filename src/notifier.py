"""
Notification module for SMS and email alerts
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

from dotenv import load_dotenv


class JobNotifier:
    """Send job notifications via SMS and Email"""

    def __init__(self, config_path: str = "config/notification-settings.json"):
        load_dotenv()

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Load credentials from environment
        self.gmail_username = os.getenv('GMAIL_USERNAME')
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        self.notification_phone = os.getenv('NOTIFICATION_PHONE')

        # Twilio setup
        if TWILIO_AVAILABLE:
            self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

            if self.twilio_account_sid and self.twilio_auth_token:
                self.twilio_client = TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
            else:
                self.twilio_client = None
        else:
            self.twilio_client = None

    def notify_job(self, job: Dict) -> Dict[str, bool]:
        """
        Send notifications for a job

        Args:
            job: Job dictionary

        Returns:
            Dictionary with notification results {sms: bool, email: bool}
        """
        results = {
            'sms': False,
            'email': False
        }

        # Send SMS if enabled
        if self.config['notifications']['sms']['enabled']:
            try:
                results['sms'] = self.send_sms(job)
            except Exception as e:
                print(f"SMS notification failed: {e}")

        # Send email if enabled
        if self.config['notifications']['email']['enabled']:
            try:
                results['email'] = self.send_email(job)
            except Exception as e:
                print(f"Email notification failed: {e}")

        return results

    def send_sms(self, job: Dict) -> bool:
        """Send SMS notification via Twilio"""
        if not self.twilio_client:
            print("Twilio not configured or unavailable")
            return False

        if not self.notification_phone or not self.twilio_phone_number:
            print("Phone numbers not configured")
            return False

        # Format SMS message (max 160 chars for efficient delivery)
        message = self._format_sms_message(job)

        try:
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=self.notification_phone
            )
            print(f"SMS sent for: {job['title']}")
            return True
        except Exception as e:
            print(f"Twilio error: {e}")
            return False

    def send_email(self, job: Dict) -> bool:
        """Send email notification via SMTP"""
        if not self.gmail_username or not self.gmail_password:
            print("Gmail credentials not configured")
            return False

        if not self.notification_email:
            print("Notification email not configured")
            return False

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = self._format_email_subject(job)
        msg['From'] = self.gmail_username
        msg['To'] = self.notification_email

        # Create plain text and HTML versions
        text_body = self._format_email_text(job)
        html_body = self._format_email_html(job)

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        # Send email
        try:
            smtp_config = self.config['notifications']['email']
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(self.gmail_username, self.gmail_password)
                server.send_message(msg)

            print(f"Email sent for: {job['title']}")
            return True
        except Exception as e:
            print(f"SMTP error: {e}")
            return False

    def _format_sms_message(self, job: Dict) -> str:
        """Format SMS message (concise, under 160 chars ideal)"""
        max_length = self.config['content']['max_message_length']

        # Build message parts
        title = job.get('title', 'Job Opportunity')[:50]
        company = job.get('company', 'Unknown')[:30]
        link = job.get('link', '')

        # Try to fit everything
        message = f"🎯 {title} at {company}\n{link}"

        # Truncate if too long
        if len(message) > max_length and max_length > 0:
            # Prioritize link
            message = f"{title[:30]}...\n{link}"

        return message

    def _format_email_subject(self, job: Dict) -> str:
        """Format email subject line"""
        title = job.get('title', 'Job Opportunity')
        company = job.get('company', 'Company')
        return f"🎯 New Job Match: {title} at {company}"

    def _format_email_text(self, job: Dict) -> str:
        """Format plain text email body"""
        lines = [
            "New Job Match Found!",
            "=" * 50,
            "",
            f"Title: {job.get('title', 'N/A')}",
            f"Company: {job.get('company', 'N/A')}",
            f"Location: {job.get('location', 'N/A')}",
            "",
            f"Link: {job.get('link', 'N/A')}",
            "",
        ]

        # Add matched keywords
        if job.get('keywords_matched'):
            lines.append(f"Matched Keywords: {', '.join(job['keywords_matched'])}")
            lines.append("")

        # Add description if available
        if job.get('description') and self.config['content']['include_job_description']:
            lines.append("Description:")
            lines.append(job['description'][:500] + "...")
            lines.append("")

        # Add metadata
        lines.append(f"Source: {job.get('source', 'Unknown')}")
        lines.append(f"Received: {job.get('received_at', 'Unknown')}")

        return "\n".join(lines)

    def _format_email_html(self, job: Dict) -> str:
        """Format HTML email body"""
        keywords_html = ""
        if job.get('keywords_matched'):
            keywords = ", ".join(job['keywords_matched'])
            keywords_html = f"""
            <div style="margin: 15px 0;">
                <strong>✓ Matched Keywords:</strong>
                <span style="color: #27ae60;">{keywords}</span>
            </div>
            """

        description_html = ""
        if job.get('description') and self.config['content']['include_job_description']:
            description_html = f"""
            <div style="margin: 15px 0;">
                <strong>Description:</strong>
                <p style="color: #555;">{job['description'][:500]}...</p>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">🎯 New Job Match!</h1>
            </div>

            <div style="background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">{job.get('title', 'Job Opportunity')}</h2>

                <div style="margin: 15px 0;">
                    <strong>🏢 Company:</strong> {job.get('company', 'N/A')}
                </div>

                <div style="margin: 15px 0;">
                    <strong>📍 Location:</strong> {job.get('location', 'N/A')}
                </div>

                {keywords_html}

                {description_html}

                <div style="margin: 25px 0;">
                    <a href="{job.get('link', '#')}"
                       style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Apply Now →
                    </a>
                </div>

                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px;">
                    <div>Source: {job.get('source', 'Unknown')}</div>
                    <div>Received: {job.get('received_at', 'Unknown')}</div>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def send_digest(self, jobs: List[Dict]) -> Dict[str, bool]:
        """
        Send a digest of multiple jobs

        Args:
            jobs: List of job dictionaries

        Returns:
            Dictionary with notification results
        """
        if not jobs:
            return {'email': False}

        # For now, just send individual notifications
        # Can be enhanced to send a single digest email with all jobs
        results = {'email': False, 'sms': False}

        for job in jobs:
            job_results = self.notify_job(job)
            results['email'] = results['email'] or job_results['email']
            results['sms'] = results['sms'] or job_results['sms']

        return results

    def test_notifications(self) -> Dict[str, bool]:
        """Test notification system with sample job"""
        test_job = {
            'title': 'Senior Product Manager - Test',
            'company': 'Test Healthcare Tech',
            'location': 'Remote',
            'link': 'https://example.com/job/test',
            'keywords_matched': ['product manager', 'healthcare technology'],
            'source': 'Test',
            'received_at': datetime.now().isoformat()
        }

        print("Sending test notifications...")
        return self.notify_job(test_job)


if __name__ == "__main__":
    # Test the notifier
    notifier = JobNotifier()
    print("Notifier initialized successfully")
    print("\nTo test notifications, run:")
    print("python src/notifier.py")
