"""
IMAP email client for fetching job alert emails
Shared functionality used by both processor.py and processor_v2.py
"""

from __future__ import annotations

import email
import email.message
import imaplib
import os

from dotenv import load_dotenv


class IMAPEmailClient:
    """Client for connecting to IMAP server and fetching emails"""

    def __init__(self, profile: str | None = None):
        load_dotenv()

        self.imap_server = "imap.gmail.com"
        self.imap_port = 993

        # Try to get profile-specific credentials first
        if profile:
            from utils.profile_manager import get_profile_manager

            manager = get_profile_manager()
            profile_obj = manager.get_profile(profile)

            if profile_obj and profile_obj.email_username:
                self.username = profile_obj.email_username
                # Use profile-specific app password if set, otherwise fall back to .env
                self.password = profile_obj.email_app_password or os.getenv("GMAIL_APP_PASSWORD")
                print(f"Using profile-specific email: {self.username}")
            else:
                # Fall back to .env credentials
                self.username = os.getenv("GMAIL_USERNAME")
                self.password = os.getenv("GMAIL_APP_PASSWORD")
                print(
                    f"Profile '{profile}' not found or no email configured, using .env credentials"
                )
        else:
            # No profile specified, use .env credentials
            self.username = os.getenv("GMAIL_USERNAME")
            self.password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.username or not self.password:
            raise ValueError(
                "Gmail credentials not configured. Please set GMAIL_USERNAME and GMAIL_APP_PASSWORD in .env"
            )

    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server"""
        print(f"Connecting to {self.imap_server}...")
        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        # Type assertion: username and password are guaranteed to be str by __init__ validation
        assert isinstance(self.username, str)
        assert isinstance(self.password, str)
        mail.login(self.username, self.password)
        return mail

    def fetch_unread_emails(self, limit: int = 50) -> list[email.message.Message]:
        """Fetch unread emails from inbox"""
        mail = self.connect_imap()
        mail.select("INBOX")

        status, messages = mail.search(None, "UNSEEN")

        if status != "OK":
            print("No unread emails found")
            return []

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} unread emails")

        email_ids = email_ids[:limit]

        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if (
                    status != "OK"
                    or not msg_data
                    or not isinstance(msg_data, list)
                    or len(msg_data) == 0
                ):
                    continue

                first_msg = msg_data[0]
                if not isinstance(first_msg, tuple) or len(first_msg) < 2:
                    continue
                raw_email = first_msg[1]
                if not isinstance(raw_email, bytes):
                    continue
                email_message = email.message_from_bytes(raw_email)
                emails.append(email_message)

            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")
                continue

        mail.close()
        mail.logout()

        return emails

    def fetch_recent_emails(self, limit: int = 50) -> list[email.message.Message]:
        """Fetch recent emails from inbox (read or unread)"""
        mail = self.connect_imap()
        mail.select("INBOX")

        # Search for ALL emails
        status, messages = mail.search(None, "ALL")

        if status != "OK":
            print("No emails found")
            return []

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} total emails")

        # Get the most recent ones (email IDs are chronological)
        email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
        # Reverse to get newest first
        email_ids = list(reversed(email_ids))

        emails = []
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if (
                    status != "OK"
                    or not msg_data
                    or not isinstance(msg_data, list)
                    or len(msg_data) == 0
                ):
                    continue

                first_msg = msg_data[0]
                if not isinstance(first_msg, tuple) or len(first_msg) < 2:
                    continue
                raw_email = first_msg[1]
                if not isinstance(raw_email, bytes):
                    continue
                email_message = email.message_from_bytes(raw_email)
                emails.append(email_message)

            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")
                continue

        mail.close()
        mail.logout()

        return emails
