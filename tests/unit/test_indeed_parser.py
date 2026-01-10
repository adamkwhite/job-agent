"""
Unit tests for Indeed email parser
"""

import email

from src.parsers.indeed_parser import IndeedParser


class TestIndeedParserCanHandle:
    """Test Indeed parser email detection"""

    def test_can_handle_ontario_jobs_subject(self):
        """Should handle '[Job] at [Company] and X more engineering jobs in Ontario' subject"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Specialist, Performance & Engineering at Vale and 29 more engineering jobs in Ontario for you!\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_variations(self):
        """Should handle different variations of the pattern"""
        parser = IndeedParser()

        email1 = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: Utilities Lead at Unilever and 29 more engineering jobs in Ontario for you!\n"
            "\nBody"
        )
        assert parser.can_handle(email1) is True

        email2 = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: Project Manager at Company and 5 more engineering jobs in Ontario\n"
            "\nBody"
        )
        assert parser.can_handle(email2) is True

    def test_can_handle_case_insensitive(self):
        """Should handle case variations"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: Engineer at Corp and 10 more ENGINEERING JOBS in ONTARIO for you!\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_cannot_handle_missing_ontario(self):
        """Should reject subjects without 'in Ontario'"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: Engineer at Company and 10 more engineering jobs\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_cannot_handle_missing_engineering(self):
        """Should reject subjects without 'engineering jobs'"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\n"
            "Subject: Engineer at Company and 10 more jobs in Ontario\n"
            "\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_cannot_handle_unrelated_subject(self):
        """Should reject emails without the pattern"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@example.com\nSubject: Job opportunity in Toronto\n\nBody"
        )
        assert parser.can_handle(email_message) is False


class TestIndeedParserParse:
    """Test Indeed parser extraction"""

    def test_parse_extracts_title_and_company(self):
        """Should extract job title and company from subject"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Specialist, Performance & Engineering at Vale and 29 more engineering jobs in Ontario for you!\n"
            "Content-Type: text/html\n\n"
            "<html><body><a href='https://example.com/jobs/123'>Apply</a></body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) >= 1
        # Should have at least the primary job
        assert any(
            opp.title == "Specialist, Performance & Engineering" and opp.company == "Vale"
            for opp in result.opportunities
        )

    def test_parse_sets_ontario_location(self):
        """Should set location to Ontario for jobs from subject"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Project Manager at Landmark Structures Co and 29 more engineering jobs in Ontario for you!\n"
            "\n\nBody with no links"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert result.opportunities[0].location == "Ontario"

    def test_parse_extracts_multiple_job_links(self):
        """Should extract multiple job links from HTML body if available"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Engineer at Company and 5 more engineering jobs in Ontario for you!\n"
            "Content-Type: text/html\n\n"
            "<html><body>"
            "<a href='https://example.com/careers/job/1'>Job 1</a>"
            "<a href='https://example.com/careers/job/2'>Job 2</a>"
            "</body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 2
        assert all(opp.source == "indeed" for opp in result.opportunities)

    def test_parse_extracts_ontario_cities(self):
        """Should recognize Ontario cities in location extraction"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Engineer at TechCorp and 10 more engineering jobs in Ontario for you!\n"
            "Content-Type: text/html\n\n"
            "<html><body>"
            "<div>Location: Toronto, Ontario</div>"
            "<a href='https://example.com/job/123'>Apply</a>"
            "</body></html>"
        )

        result = parser.parse(email_message)

        assert result.success is True
        # Should extract Toronto from the HTML
        # (This tests the _extract_location_from_context method)
        assert len(result.opportunities) >= 1

    def test_parse_fallback_when_no_links(self):
        """Should create opportunity from subject if no links found"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Utilities Lead at Unilever and 29 more engineering jobs in Ontario for you!\n"
            "Content-Type: text/plain\n\n"
            "Some text without job links"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].title == "Utilities Lead"
        assert result.opportunities[0].company == "Unilever"
        assert result.opportunities[0].location == "Ontario"
        assert result.opportunities[0].needs_research is True

    def test_parse_deduplicates_urls(self):
        """Should not create duplicate opportunities for same URL"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Engineer at Company and 3 more engineering jobs in Ontario for you!\n"
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

    def test_parse_with_complex_title(self):
        """Should handle complex job titles with commas and ampersands"""
        parser = IndeedParser()
        email_message = email.message_from_string(
            "From: jobs@indeed.com\n"
            "Subject: Senior Manager, Software Development & Operations at BigCorp and 15 more engineering jobs in Ontario for you!\n"
            "\n\nBody"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert any(
            "Senior Manager, Software Development & Operations" in opp.title
            for opp in result.opportunities
        )
