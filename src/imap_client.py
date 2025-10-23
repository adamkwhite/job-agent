"""
IMAP email client for fetching job alert emails
Shared functionality used by both processor.py and processor_v2.py
"""

import email
import imaplib
import os

from dotenv import load_dotenv


class IMAPEmailClient:
    """Client for connecting to IMAP server and fetching emails"""

    def __init__(self):
        load_dotenv()

        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
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
