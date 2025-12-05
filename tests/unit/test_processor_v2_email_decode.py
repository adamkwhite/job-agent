"""
Unit tests for email subject decoding in JobProcessorV2

Tests the decode_email_subject() function that handles MIME-encoded email subjects.
Addresses Issue #101 - Email subjects showing raw MIME encoding.
"""

from src.processor_v2 import decode_email_subject


class TestDecodeEmailSubject:
    """Test email subject MIME decoding"""

    def test_decode_base64_encoded_subject(self):
        """Test decoding Base64 encoded email subjects"""
        # Real example from Work In Tech newsletter
        encoded = "New jobs for you in Work In =?UTF-8?B?VGVjaOKAmXM=?= job board"
        # Decoded contains Unicode RIGHT SINGLE QUOTATION MARK (U+2019)
        expected = "New jobs for you in Work In Tech\u2019s job board"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_quoted_printable_subject(self):
        """Test decoding Quoted-printable encoded email subjects"""
        # Quoted-printable encoding example
        encoded = "Job Alert: Software =?UTF-8?Q?Engineer=E2=80=94Toronto?="
        expected = "Job Alert: Software Engineer—Toronto"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_plain_text_subject(self):
        """Test that plain text subjects are returned unchanged"""
        plain = "Plain text subject with no encoding"

        result = decode_email_subject(plain)
        assert result == plain

    def test_decode_multiple_encoded_segments(self):
        """Test decoding subjects with multiple encoded segments"""
        encoded = "=?UTF-8?B?V2Vla2x5?= Update: =?UTF-8?B?TmV3IEpvYnM=?="
        expected = "Weekly Update: New Jobs"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_with_special_characters(self):
        """Test decoding subjects with various special characters"""
        # Contains Unicode RIGHT SINGLE QUOTATION MARK (U+2019) and EM DASH (U+2014)
        encoded = "=?UTF-8?B?RGlyZWN0b3LigJlzIFJvbGXigJQ=?= Leadership Position"
        expected = "Director\u2019s Role\u2014 Leadership Position"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_empty_string(self):
        """Test handling of empty string"""
        result = decode_email_subject("")
        assert result == ""

    def test_decode_malformed_encoding_fallback(self):
        """Test fallback to original string on decoding errors"""
        # Intentionally malformed encoding
        malformed = "Subject with =?INVALID?X?broken?= encoding"

        # Should return original string without crashing
        result = decode_email_subject(malformed)
        assert isinstance(result, str)
        # Exact result depends on decode_header behavior, but should not raise

    def test_decode_latin1_encoding(self):
        """Test decoding subjects with Latin-1 encoding"""
        encoded = "=?ISO-8859-1?Q?Caf=E9?= Job Opening"
        expected = "Café Job Opening"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_mixed_encoded_and_plain(self):
        """Test subjects mixing encoded and plain text"""
        encoded = "Weekly Alert from =?UTF-8?B?TGlua2VkSW4=?="
        expected = "Weekly Alert from LinkedIn"

        result = decode_email_subject(encoded)
        assert result == expected

    def test_decode_preserves_spaces(self):
        """Test that spacing is preserved correctly"""
        encoded = "New =?UTF-8?B?Sm9icw==?= for =?UTF-8?B?WW91?="
        expected = "New Jobs for You"

        result = decode_email_subject(encoded)
        assert result == expected
