"""
Unit tests for Built In email parser
"""

import email

from src.parsers.builtin_parser import BuiltInParser


class TestBuiltInParserCanHandle:
    """Test Built In parser email detection"""

    def test_can_handle_builtin_from_address(self):
        """Should handle emails from builtin.com"""
        parser = BuiltInParser()
        email_message = email.message_from_string(
            "From: noreply@builtin.com\nSubject: Test\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_support_email(self):
        """Should handle emails from support@builtin.com"""
        parser = BuiltInParser()
        email_message = email.message_from_string(
            "From: support@builtin.com\nSubject: Test\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_job_match_subject(self):
        """Should handle emails with job match subject"""
        parser = BuiltInParser()
        email_message = email.message_from_string(
            "From: other@example.com\nSubject: New Product Management Job Matches\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_cannot_handle_unrelated_email(self):
        """Should reject unrelated emails"""
        parser = BuiltInParser()
        email_message = email.message_from_string(
            "From: other@example.com\nSubject: Random Newsletter\n\nBody"
        )
        assert parser.can_handle(email_message) is False


class TestBuiltInParserParse:
    """Test Built In parser parsing logic"""

    def test_parse_no_html_content(self):
        """Should return error when no HTML content"""
        parser = BuiltInParser()
        email_message = email.message_from_string(
            "From: support@builtin.com\nSubject: Test\nContent-Type: text/plain\n\nPlain text only"
        )

        result = parser.parse(email_message)

        assert result.success is False
        assert result.error == "No HTML content found in email"
        assert len(result.opportunities) == 0

    def test_parse_no_jobs_found(self):
        """Should return error when no job links found"""
        parser = BuiltInParser()
        html_content = "<html><body><p>No jobs here</p></body></html>"
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is False
        assert result.error == "No job opportunities found in email"
        assert len(result.opportunities) == 0

    def test_parse_valid_job(self):
        """Should successfully parse a valid job listing"""
        parser = BuiltInParser()
        html_content = """
        <html><body>
            <a href="https://builtin.com/job/senior-product-manager/123">
                <div style="font-size:16px;margin-bottom:8px">Acme Corp</div>
                <div style="font-size:20px;font-weight:700">Senior Product Manager</div>
                <div>LocationIcon<span style="vertical-align:middle">Toronto, ON</span></div>
                <div>SalaryIcon<span style="vertical-align:middle">$100k-$150k</span></div>
            </a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1

        job = result.opportunities[0]
        assert job.company == "Acme Corp"
        assert job.title == "Senior Product Manager"
        assert job.location == "Toronto, ON"
        assert job.salary == "$100k-$150k"
        assert job.link == "https://builtin.com/job/senior-product-manager/123"
        assert job.source == "builtin"
        assert job.type == "direct_job"

    def test_parse_aws_tracking_url(self):
        """Should extract clean URL from AWS tracking link"""
        parser = BuiltInParser()
        html_content = """
        <html><body>
            <a href="https://tracking.aws.com/L0/https:%2F%2Fbuiltin.com%2Fjob%2Fproduct-manager%2F456">
                <div style="font-size:16px;margin-bottom:8px">Test Co</div>
                <div style="font-size:20px;font-weight:700">Product Manager</div>
            </a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].link == "https://builtin.com/job/product-manager/456"

    def test_parse_deduplicates_urls(self):
        """Should deduplicate jobs with same URL"""
        parser = BuiltInParser()
        html_content = """
        <html><body>
            <a href="https://builtin.com/job/director/789">
                <div style="font-size:16px;margin-bottom:8px">Company A</div>
                <div style="font-size:20px;font-weight:700">Director</div>
            </a>
            <a href="https://builtin.com/job/director/789?ref=email">
                <div style="font-size:16px;margin-bottom:8px">Company A</div>
                <div style="font-size:20px;font-weight:700">Director</div>
            </a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1  # Deduplicated

    def test_parse_skips_incomplete_jobs(self):
        """Should skip jobs missing title or company"""
        parser = BuiltInParser()
        html_content = """
        <html><body>
            <a href="https://builtin.com/job/incomplete/111">
                <div style="font-size:20px;font-weight:700">Title Only</div>
            </a>
            <a href="https://builtin.com/job/valid/222">
                <div style="font-size:16px;margin-bottom:8px">Valid Corp</div>
                <div style="font-size:20px;font-weight:700">Valid Job</div>
            </a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1  # Only the valid one
        assert result.opportunities[0].company == "Valid Corp"

    def test_parse_handles_missing_location_and_salary(self):
        """Should handle jobs without location or salary"""
        parser = BuiltInParser()
        html_content = """
        <html><body>
            <a href="https://builtin.com/job/minimal/333">
                <div style="font-size:16px;margin-bottom:8px">Minimal Inc</div>
                <div style="font-size:20px;font-weight:700">Basic Job</div>
            </a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: support@builtin.com\nSubject: Test\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1

        job = result.opportunities[0]
        assert job.company == "Minimal Inc"
        assert job.title == "Basic Job"
        assert job.location == ""
        assert job.salary == ""


class TestBuiltInParserHelperMethods:
    """Test Built In parser helper methods"""

    def test_extract_clean_url_simple(self):
        """Should extract clean URL from simple builtin.com link"""
        parser = BuiltInParser()
        tracking_url = "https://builtin.com/job/test/123"

        result = parser._extract_clean_url(tracking_url)

        assert result == "https://builtin.com/job/test/123"

    def test_extract_clean_url_with_encoding(self):
        """Should decode URL-encoded characters"""
        parser = BuiltInParser()
        tracking_url = "https://tracking.com/L0/https:%2F%2Fbuiltin.com%2Fjob%2Ftest%2F123"

        result = parser._extract_clean_url(tracking_url)

        assert result == "https://builtin.com/job/test/123"

    def test_extract_clean_url_strips_query_params(self):
        """Should remove query parameters for deduplication"""
        parser = BuiltInParser()
        tracking_url = "https://builtin.com/job/test/123?ref=email&source=alert"

        result = parser._extract_clean_url(tracking_url)

        assert result == "https://builtin.com/job/test/123"

    def test_extract_clean_url_adds_https(self):
        """Should add https:// prefix if missing"""
        parser = BuiltInParser()
        tracking_url = "builtin.com/job/test/123"

        result = parser._extract_clean_url(tracking_url)

        assert result == "https://builtin.com/job/test/123"

    def test_extract_clean_url_returns_empty_for_invalid(self):
        """Should return empty string for invalid URLs"""
        parser = BuiltInParser()
        tracking_url = "https://example.com/not-builtin"

        result = parser._extract_clean_url(tracking_url)

        assert result == ""

    def test_no_html_error(self):
        """Should return proper error result for missing HTML"""
        parser = BuiltInParser()

        result = parser._no_html_error()

        assert result.success is False
        assert result.error == "No HTML content found in email"
        assert result.parser_name == "builtin"
        assert len(result.opportunities) == 0

    def test_no_jobs_error(self):
        """Should return proper error result for no jobs found"""
        parser = BuiltInParser()

        result = parser._no_jobs_error()

        assert result.success is False
        assert result.error == "No job opportunities found in email"
        assert result.parser_name == "builtin"
        assert len(result.opportunities) == 0


class TestBuiltInParserExceptionHandling:
    """Test exception handling in builtin_parser"""

    def test_parse_handles_malformed_html(self):
        """Should handle malformed HTML gracefully"""
        parser = BuiltInParser()

        # Create email with malformed HTML that will cause parsing errors
        email_msg = email.message_from_string(
            """From: jobs@builtin.com
Subject: New job matches

Content-Type: text/html

<html><body><a href="invalid>Broken HTML</body>"""
        )

        result = parser.parse(email_msg)

        # Should return result (either success with no jobs or error)
        assert result is not None
        assert result.parser_name == "builtin"

    def test_parse_job_link_handles_exception(self):
        """Should return None when exception occurs in _parse_job_link"""
        parser = BuiltInParser()
        from bs4 import BeautifulSoup

        # Create a link that will cause an exception
        html = '<a href="https://builtin.com/job/123"></a>'
        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        # Mock _extract_job_details to raise exception
        from unittest.mock import patch

        with patch.object(parser, "_extract_job_details", side_effect=Exception("Test error")):
            result = parser._parse_job_link(link, set())

            # Should return None instead of crashing
            assert result is None

    def test_extract_clean_url_removes_query_params(self):
        """Should remove query parameters from URLs"""
        parser = BuiltInParser()

        # URL with query parameters
        url = "https://builtin.com/job/123?utm_source=email&utm_campaign=test"
        clean_url = parser._extract_clean_url(url)

        assert clean_url == "https://builtin.com/job/123"
        assert "?" not in clean_url
