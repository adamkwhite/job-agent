"""
Tests for IMAPEmailClient
"""

import email
from unittest.mock import MagicMock, patch

import pytest

from imap_client import IMAPEmailClient


class TestIMAPEmailClientInit:
    """Test IMAPEmailClient initialization"""

    @patch("imap_client.os.getenv")
    def test_init_with_valid_credentials(self, mock_getenv):
        """Test initialization with valid credentials"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        client = IMAPEmailClient()

        assert client.imap_server == "imap.gmail.com"
        assert client.imap_port == 993
        assert client.username == "test@example.com"
        assert client.password == "test_password"

    @patch("imap_client.os.getenv")
    def test_init_missing_username(self, mock_getenv):
        """Test initialization fails when username is missing"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": None,
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        with pytest.raises(ValueError, match="Gmail credentials not configured"):
            IMAPEmailClient()

    @patch("imap_client.os.getenv")
    def test_init_missing_password(self, mock_getenv):
        """Test initialization fails when password is missing"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": None,
        }.get(key)

        with pytest.raises(ValueError, match="Gmail credentials not configured"):
            IMAPEmailClient()


class TestIMAPEmailClientConnect:
    """Test IMAP connection functionality"""

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_connect_imap_success(self, mock_imap_class, mock_getenv):
        """Test successful IMAP connection"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        mock_mail = MagicMock()
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        mail = client.connect_imap()

        assert mail == mock_mail
        mock_imap_class.assert_called_once_with("imap.gmail.com", 993)
        mock_mail.login.assert_called_once_with("test@example.com", "test_password")


class TestIMAPEmailClientFetchEmails:
    """Test email fetching functionality"""

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_success(self, mock_imap_class, mock_getenv):
        """Test fetching unread emails successfully"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        # Create mock email
        raw_email = b"""From: sender@example.com
To: test@example.com
Subject: Test Email

Test body"""

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1 2 3"])
        mock_mail.fetch.return_value = ("OK", [(None, raw_email)])
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails(limit=50)

        assert len(emails) == 3
        assert all(isinstance(e, email.message.Message) for e in emails)
        mock_mail.select.assert_called_once_with("INBOX")
        mock_mail.search.assert_called_once_with(None, "UNSEEN")
        mock_mail.close.assert_called_once()
        mock_mail.logout.assert_called_once()

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_no_emails(self, mock_imap_class, mock_getenv):
        """Test fetching when no unread emails exist"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("NO", [])
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails()

        assert emails == []

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_with_limit(self, mock_imap_class, mock_getenv):
        """Test fetching unread emails respects limit parameter"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        raw_email = b"""From: sender@example.com
To: test@example.com
Subject: Test Email

Test body"""

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1 2 3 4 5"])
        mock_mail.fetch.return_value = ("OK", [(None, raw_email)])
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails(limit=2)

        # Should only fetch first 2 emails even though 5 are available
        assert len(emails) == 2

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_handles_fetch_errors(self, mock_imap_class, mock_getenv):
        """Test that individual email fetch errors don't break the entire process"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        raw_email = b"""From: sender@example.com
To: test@example.com
Subject: Test Email

Test body"""

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1 2 3"])

        # First fetch succeeds, second fails, third succeeds
        mock_mail.fetch.side_effect = [
            ("OK", [(None, raw_email)]),
            Exception("Fetch failed"),
            ("OK", [(None, raw_email)]),
        ]
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails()

        # Should get 2 emails (skipping the failed one)
        assert len(emails) == 2

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_handles_invalid_responses(self, mock_imap_class, mock_getenv):
        """Test handling of invalid IMAP fetch responses"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        raw_email = b"""From: sender@example.com
To: test@example.com
Subject: Test Email

Test body"""

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1 2 3 4"])

        # Various invalid response formats
        mock_mail.fetch.side_effect = [
            ("OK", [(None, raw_email)]),  # Valid
            ("NO", None),  # Invalid status
            ("OK", []),  # Empty list
            ("OK", [(None, raw_email)]),  # Valid
        ]
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails()

        # Should only get 2 valid emails
        assert len(emails) == 2

    @patch("imap_client.os.getenv")
    @patch("imap_client.imaplib.IMAP4_SSL")
    def test_fetch_unread_emails_handles_non_bytes_payload(self, mock_imap_class, mock_getenv):
        """Test handling when email payload is not bytes"""
        mock_getenv.side_effect = lambda key: {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_APP_PASSWORD": "test_password",
        }.get(key)

        raw_email = b"""From: sender@example.com
To: test@example.com
Subject: Test Email

Test body"""

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1 2 3"])

        # Mix of valid and invalid payloads
        mock_mail.fetch.side_effect = [
            ("OK", [(None, raw_email)]),  # Valid bytes
            ("OK", [(None, "not bytes")]),  # Invalid - string instead of bytes
            ("OK", [(None, raw_email)]),  # Valid bytes
        ]
        mock_imap_class.return_value = mock_mail

        client = IMAPEmailClient()
        emails = client.fetch_unread_emails()

        # Should only get 2 valid emails (skipping the non-bytes one)
        assert len(emails) == 2
