"""
Unit tests for NewMatch email parser
"""

import email

from src.parsers.newmatch_parser import NewMatchParser


class TestNewMatchParserCanHandle:
    """Test NewMatch parser email detection"""

    def test_can_handle_new_match_subject(self):
        """Should handle 'New match: [Job] at [Company]' subject"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: New match: Staff Product Manager at Harvey\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_new_match_with_special_chars(self):
        """Should handle titles with special characters"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: New match: Director of Product - AI/ML at TechCorp\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_case_insensitive(self):
        """Should handle case variations"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: NEW MATCH: Senior Engineer at Company\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_cannot_handle_missing_at(self):
        """Should reject subjects without ' at '"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: New match: Senior Engineer\n\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_cannot_handle_unrelated_subject(self):
        """Should reject emails without 'New match:' prefix"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: Job opportunity at Company\n\nBody"
        )
        assert parser.can_handle(email_message) is False


class TestNewMatchParserParse:
    """Test NewMatch parser extraction"""

    def test_parse_extracts_title_and_company(self):
        """Should extract job title and company from subject"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New match: Staff Product Manager at Harvey\n"
            "Content-Type: text/html\n\n"
            "<html><body><a href='https://example.com/jobs/123'>Apply</a></body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        opp = result.opportunities[0]
        assert opp.title == "Staff Product Manager"
        assert opp.company == "Harvey"
        assert opp.source == "newmatch"

    def test_parse_extracts_job_link_from_html(self):
        """Should extract job link from HTML body"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New match: Senior Engineer at TechCorp\n"
            "Content-Type: text/html\n\n"
            "<html><body><a href='https://techcorp.com/careers/job/456'>View Job</a></body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].link == "https://techcorp.com/careers/job/456"
        assert result.opportunities[0].needs_research is False

    def test_parse_handles_missing_link(self):
        """Should create opportunity with needs_research=True if no link found"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New match: Director of Engineering at Company\n"
            "Content-Type: text/plain\n\n"
            "Some text without job links"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].link == ""
        assert result.opportunities[0].needs_research is True

    def test_parse_with_complex_title(self):
        """Should handle complex job titles"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New match: Senior Engineering Manager, Device Software & Systems at RoboCo\n"
            "\n\nBody"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert (
            result.opportunities[0].title == "Senior Engineering Manager, Device Software & Systems"
        )
        assert result.opportunities[0].company == "RoboCo"

    def test_parse_filters_non_job_links(self):
        """Should filter out non-job links (unsubscribe, etc.)"""
        parser = NewMatchParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New match: Product Manager at StartupCo\n"
            "Content-Type: text/html\n\n"
            "<html><body>"
            "<a href='https://example.com/unsubscribe'>Unsubscribe</a>"
            "<a href='https://example.com/careers/job/789'>Apply Here</a>"
            "</body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        # Should find the job link, not the unsubscribe link
        assert result.opportunities[0].link == "https://example.com/careers/job/789"
