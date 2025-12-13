"""
Integration tests for email parsers with MIME-encoded subjects

Tests the full email parsing pipeline with real Gmail MIME encoding:
1. MIME-encoded email subjects (Base64, Quoted-Printable)
2. Integration with email message objects
3. Real-world encoding scenarios from Gmail

Addresses Issue #142 - Integration tests for MIME-encoded emails
"""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.processor_v2 import decode_email_subject


class TestMIMEDecoding:
    """Test MIME decoding with real Gmail encodings"""

    def test_decode_work_in_tech_subject(self):
        """Test decoding Work In Tech MIME-encoded subject"""
        # Real example from Work In Tech newsletter (Base64 with Unicode RIGHT SINGLE QUOTATION MARK)
        encoded = "New jobs for you in Work In =?UTF-8?B?VGVjaOKAmXM=?= job board"
        expected = "New jobs for you in Work In Tech\u2019s job board"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_linkedin_job_alert(self):
        """Test decoding LinkedIn MIME-encoded subject"""
        # Quoted-printable encoding with EM DASH
        encoded = "=?UTF-8?Q?Jobs_matching_Director=E2=80=94Engineering?="
        expected = "Jobs matching Director—Engineering"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_supra_newsletter_subject(self):
        """Test decoding Supra newsletter MIME-encoded subject"""
        # Base64 with multiple encoded segments
        encoded = "=?UTF-8?B?U3VwcmE=?= Product Leadership =?UTF-8?B?Sm9icw==?="
        expected = "Supra Product Leadership Jobs"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_special_characters(self):
        """Test decoding subjects with various special characters"""
        # Unicode RIGHT SINGLE QUOTATION MARK + EM DASH + BULLET
        encoded = "=?UTF-8?B?RGlyZWN0b3LigJlzIFJvbGXigJQgUmVtb3Rl?="
        expected = "Director\u2019s Role\u2014 Remote"

        result = decode_email_subject(encoded)
        assert result == expected


class TestMIMEEncodingEdgeCases:
    """Test edge cases in MIME encoding"""

    def test_mixed_encoded_and_plain_text(self):
        """Test subjects mixing MIME-encoded and plain text"""
        # Common pattern: plain text + encoded word + plain text
        encoded = "Weekly Alert from =?UTF-8?B?TGlua2VkSW4=?= Jobs"
        expected = "Weekly Alert from LinkedIn Jobs"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_multiple_encoded_segments(self):
        """Test subjects with multiple encoded segments"""
        encoded = "=?UTF-8?B?VlA=?= of =?UTF-8?B?RW5naW5lZXJpbmc=?= Role"
        expected = "VP of Engineering Role"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_latin1_encoding(self):
        """Test subjects with Latin-1 encoding"""
        encoded = "=?ISO-8859-1?Q?Caf=E9?= Manager Position"
        expected = "Café Manager Position"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_malformed_encoding_fallback(self):
        """Test fallback to original string on malformed encoding"""
        malformed = "Subject with =?INVALID?X?broken?= encoding"

        # Should not crash
        result = decode_email_subject(malformed)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_subject(self):
        """Test handling of empty subject"""
        result = decode_email_subject("")
        assert result == ""

    def test_plain_text_subject_unchanged(self):
        """Test that plain text subjects pass through unchanged"""
        plain = "Plain text subject with no encoding"

        result = decode_email_subject(plain)
        assert result == plain


class TestMIMEEmailMessages:
    """Test MIME decoding with email.message.Message objects"""

    def _create_mime_email(self, subject: str, body: str, from_addr: str) -> email.message.Message:
        """Helper to create MIME email with encoded subject"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = "test@example.com"
        msg.attach(MIMEText(body, "html"))
        return msg

    def test_decode_subject_from_email_message(self):
        """Test decoding MIME-encoded subject from email.message.Message"""
        # Create email with MIME-encoded subject
        subject = "=?UTF-8?B?Sm9icyBtYXRjaGluZyBEaXJlY3Rvcg==?="
        msg = self._create_mime_email(subject, "<html><body>Test</body></html>", "test@example.com")

        # Extract and decode subject
        decoded = decode_email_subject(msg["Subject"])

        assert "Jobs matching Director" in decoded
        assert decoded == "Jobs matching Director"

    def test_decode_quoted_printable_from_message(self):
        """Test decoding Quoted-Printable subject from email message"""
        # Quoted-printable with EM DASH
        subject = "=?UTF-8?Q?Supra_Product_Leadership_Jobs=E2=80=94Weekly_Digest?="
        msg = self._create_mime_email(subject, "<html><body>Test</body></html>", "test@example.com")

        decoded = decode_email_subject(msg["Subject"])

        assert "Supra Product Leadership Jobs" in decoded
        assert "\u2014" in decoded  # EM DASH
        assert "Weekly Digest" in decoded

    def test_decode_base64_with_unicode_from_message(self):
        """Test decoding Base64 with Unicode from email message"""
        # Real Work In Tech encoding
        subject = "New jobs for you in Work In =?UTF-8?B?VGVjaOKAmXM=?= job board"
        msg = self._create_mime_email(
            subject, "<html><body>Test</body></html>", "jobs@workintech.io"
        )

        decoded = decode_email_subject(msg["Subject"])

        assert "Work In Tech\u2019s job board" in decoded  # RIGHT SINGLE QUOTATION MARK


class TestRealWorldScenarios:
    """Test real-world MIME encoding scenarios from Gmail"""

    def test_linkedin_multiple_jobs_alert(self):
        """Test LinkedIn's typical job alert subject encoding"""
        # Real pattern from LinkedIn job alerts
        subjects = [
            "=?UTF-8?Q?5_jobs_matching_your_preferences?=",
            "=?UTF-8?B?Sm9icyBtYXRjaGluZyBEaXJlY3Rvcg==?=",
            "=?UTF-8?Q?VP_Engineering=E2=80=94Remote_Opportunities?=",
        ]

        expected = [
            "5 jobs matching your preferences",
            "Jobs matching Director",
            "VP Engineering—Remote Opportunities",
        ]

        for encoded, exp in zip(subjects, expected):
            result = decode_email_subject(encoded)
            assert result == exp

    def test_builtin_job_match_subject(self):
        """Test Built In's job match email subject encoding"""
        # Built In often uses EM DASH in subjects
        encoded = "=?UTF-8?B?Sm9iIE1hdGNo4oCUUHJvZHVjdCAmIEVuZ2luZWVyaW5n?="
        expected = "Job Match—Product & Engineering"

        result = decode_email_subject(encoded)
        assert result == expected
        assert "\u2014" in result  # EM DASH

    def test_f6s_weekly_opportunities(self):
        """Test F6S weekly opportunities subject encoding"""
        encoded = "=?UTF-8?Q?F6S_Weekly_Opportunities=E2=80=94VP_&_Director_Roles?="
        expected = "F6S Weekly Opportunities—VP & Director Roles"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_supra_with_special_chars(self):
        """Test Supra newsletter with special characters"""
        # Supra uses RIGHT SINGLE QUOTATION MARK and EM DASH
        encoded = "=?UTF-8?B?U3VwcmHigJlzIFByb2R1Y3QgTGVhZGVyc2hpcOKAlA==?= Weekly Digest"
        expected = "Supra\u2019s Product Leadership\u2014 Weekly Digest"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_artemis_newsletter_encoding(self):
        """Test Artemis newsletter subject encoding"""
        # Artemis typically uses simple Base64 encoding
        encoded = "=?UTF-8?B?QXJ0ZW1pcw==?= Weekly Update: Leadership Roles"
        expected = "Artemis Weekly Update: Leadership Roles"

        result = decode_email_subject(encoded)
        assert result == expected
