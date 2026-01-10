"""
Unit tests for Wellfound email parser
"""

import email

from src.parsers.wellfound_parser import WellfoundParser


class TestWellfoundParserCanHandle:
    """Test Wellfound parser email detection"""

    def test_can_handle_new_jobs_subject(self):
        """Should handle 'New jobs: [Job] at [Company] and X more jobs' subject"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Head of Engineering at NewVue.ai and 9 more jobs\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_plural_and_singular_jobs(self):
        """Should handle both 'jobs' and 'job' in subject"""
        parser = WellfoundParser()

        # Plural
        email_plural = email.message_from_string(
            "From: jobs@example.com\nSubject: New jobs: Engineer at Company and 5 more jobs\n\nBody"
        )
        assert parser.can_handle(email_plural) is True

        # Singular (edge case)
        email_singular = email.message_from_string(
            "From: jobs@example.com\nSubject: New jobs: Engineer at Company and 1 more job\n\nBody"
        )
        assert parser.can_handle(email_singular) is True

    def test_can_handle_case_insensitive(self):
        """Should handle case variations"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: NEW JOBS: Senior Manager at Corp and 10 more jobs\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_cannot_handle_missing_and_more(self):
        """Should reject subjects without 'and X more jobs'"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: New jobs: Senior Engineer at Company\n\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_cannot_handle_unrelated_subject(self):
        """Should reject emails without 'New jobs:' prefix"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: Job opportunity at Company\n\nBody"
        )
        assert parser.can_handle(email_message) is False


class TestWellfoundParserParse:
    """Test Wellfound parser extraction"""

    def test_parse_extracts_title_and_company(self):
        """Should extract primary job title and company from subject"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Sr Engineering Manager at Redpanda Data and 7 more jobs\n"
            "Content-Type: text/html\n\n"
            "<html><body><a href='https://example.com/jobs/123'>Apply</a></body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) >= 1
        # Should have at least the primary job
        assert any(
            opp.title == "Sr Engineering Manager" and opp.company == "Redpanda Data"
            for opp in result.opportunities
        )

    def test_parse_extracts_multiple_job_links(self):
        """Should extract multiple job links from HTML body if available"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Head of Engineering at StartupCo and 3 more jobs\n"
            "Content-Type: text/html\n\n"
            "<html><body>"
            "<a href='https://example.com/careers/job/1'>Job 1</a>"
            "<a href='https://example.com/careers/job/2'>Job 2</a>"
            "<a href='https://example.com/careers/job/3'>Job 3</a>"
            "</body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 3
        assert result.opportunities[0].source == "wellfound"

    def test_parse_handles_complex_title(self):
        """Should handle complex job titles with parentheses and special chars"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Head of Engineering (Hands-On, Player-Coach) at NewVue.ai and 9 more jobs\n"
            "\n\nBody"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert any(
            "Head of Engineering (Hands-On, Player-Coach)" in opp.title
            for opp in result.opportunities
        )

    def test_parse_fallback_when_no_links(self):
        """Should create opportunity from subject if no links found"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Director of Product at Company and 5 more jobs\n"
            "Content-Type: text/plain\n\n"
            "Some text without job links"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].title == "Director of Product"
        assert result.opportunities[0].company == "Company"
        assert result.opportunities[0].needs_research is True

    def test_parse_deduplicates_urls(self):
        """Should not create duplicate opportunities for same URL"""
        parser = WellfoundParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: New jobs: Engineer at TechCorp and 2 more jobs\n"
            "Content-Type: text/html\n\n"
            "<html><body>"
            "<a href='https://example.com/job/123'>Link 1</a>"
            "<a href='https://example.com/job/123'>Link 2 (duplicate)</a>"
            "<a href='https://example.com/job/456'>Link 3</a>"
            "</body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        # Should only have 2 opportunities (not 3)
        assert len(result.opportunities) == 2
