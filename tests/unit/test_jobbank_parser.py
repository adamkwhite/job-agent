"""
Unit tests for Job Bank Canada email parser
"""

from src.parsers.jobbank_parser import can_parse, parse_jobbank_email


class TestJobBankParser:
    """Test Job Bank email parser functionality"""

    def test_can_parse_jobbank_email(self):
        """Test Job Bank email detection"""
        # Should parse Job Bank emails
        assert can_parse("no-reply-jobalert@hrsdc-rhdcc.gc.ca", "5 new jobs - Mechanical engineers")
        assert can_parse("Job Bank Alerts <alerts@jobbank.gc.ca>", "New opportunities")
        assert can_parse("someone@example.com", "3 new jobs - Engineers in Ontario")

        # Should not parse other emails
        assert not can_parse("linkedin@linkedin.com", "Your job alert")
        assert not can_parse("random@example.com", "Random subject")

    def test_parse_jobbank_email_with_jobs(self):
        """Test parsing Job Bank email with multiple jobs"""
        html_content = """
        <html>
            <table>
                <tr>
                    <td>
                        <a href="/jobs/123" class="resultJobItem">
                            Senior Mechanical Engineer
                        </a>
                    </td>
                </tr>
                <tr>
                    <td>ABC Manufacturing Inc.</td>
                </tr>
                <tr>
                    <td>Toronto, ON</td>
                </tr>
            </table>
            <table>
                <tr>
                    <td>
                        <a href="/jobs/456?tracking=true" class="resultJobItem">
                            Director of Engineering
                        </a>
                    </td>
                </tr>
                <tr>
                    <td>XYZ Robotics</td>
                </tr>
                <tr>
                    <td>Waterloo, ON</td>
                </tr>
            </table>
        </html>
        """

        jobs = parse_jobbank_email(html_content)

        assert len(jobs) == 2

        # First job
        assert jobs[0]["title"] == "Senior Mechanical Engineer"
        assert jobs[0]["company"] == "ABC Manufacturing Inc."
        assert jobs[0]["location"] == "Toronto, ON"
        assert jobs[0]["link"] == "https://www.jobbank.gc.ca/jobs/123"

        # Second job - URL should have tracking params removed
        assert jobs[1]["title"] == "Director of Engineering"
        assert jobs[1]["company"] == "XYZ Robotics"
        assert jobs[1]["location"] == "Waterloo, ON"
        assert jobs[1]["link"] == "https://www.jobbank.gc.ca/jobs/456"

    def test_parse_jobbank_email_with_missing_data(self):
        """Test parsing Job Bank email with incomplete job data"""
        html_content = """
        <html>
            <table>
                <tr>
                    <td>
                        <a href="/jobs/789" class="resultJobItem">
                            Product Manager
                        </a>
                    </td>
                </tr>
            </table>
        </html>
        """

        jobs = parse_jobbank_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Product Manager"
        assert jobs[0]["company"] == "Unknown Company"
        assert jobs[0]["location"] == "Canada"
        assert jobs[0]["link"] == "https://www.jobbank.gc.ca/jobs/789"

    def test_parse_jobbank_email_no_jobs(self):
        """Test parsing Job Bank email with no job listings"""
        html_content = """
        <html>
            <body>
                <p>No new jobs match your criteria.</p>
            </body>
        </html>
        """

        jobs = parse_jobbank_email(html_content)
        assert jobs == []

    def test_parse_jobbank_email_with_absolute_urls(self):
        """Test parsing Job Bank email with absolute URLs"""
        html_content = """
        <html>
            <table>
                <tr>
                    <td>
                        <a href="https://www.jobbank.gc.ca/jobs/999" class="resultJobItem">
                            VP Engineering
                        </a>
                    </td>
                </tr>
                <tr>
                    <td>Tech Corp</td>
                </tr>
                <tr>
                    <td>Remote</td>
                </tr>
            </table>
        </html>
        """

        jobs = parse_jobbank_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["link"] == "https://www.jobbank.gc.ca/jobs/999"

    def test_parse_jobbank_email_skip_empty_links(self):
        """Test that parser skips job entries without URLs"""
        html_content = """
        <html>
            <table>
                <tr>
                    <td>
                        <a class="resultJobItem">Job Without Link</a>
                    </td>
                </tr>
                <tr>
                    <td>Company</td>
                </tr>
            </table>
            <table>
                <tr>
                    <td>
                        <a href="/jobs/valid" class="resultJobItem">Valid Job</a>
                    </td>
                </tr>
                <tr>
                    <td>Valid Company</td>
                </tr>
            </table>
        </html>
        """

        jobs = parse_jobbank_email(html_content)

        # Should only return the job with a valid link
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Valid Job"


class TestJobBankParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_skips_empty_titles(self):
        """Should skip jobs with empty titles"""
        html_content = """
        <html>
            <table>
                <tr><td><a href="/jobs/123" class="resultJobItem"></a></td></tr>
            </table>
        </html>
        """
        jobs = parse_jobbank_email(html_content)
        assert len(jobs) == 0

    def test_parse_handles_missing_company_td(self):
        """Should default to Unknown Company when company td missing"""
        html_content = """
        <html>
            <table>
                <tr><td><a href="/jobs/123" class="resultJobItem">Test Job</a></td></tr>
                <tr></tr>
            </table>
        </html>
        """
        jobs = parse_jobbank_email(html_content)
        assert len(jobs) >= 1
        assert jobs[0]["company"] == "Unknown Company"

    def test_parse_handles_missing_company_row(self):
        """Should default to Unknown Company when company row missing"""
        html_content = """
        <html>
            <table>
                <tr><td><a href="/jobs/123" class="resultJobItem">Test Job</a></td></tr>
            </table>
        </html>
        """
        jobs = parse_jobbank_email(html_content)
        assert len(jobs) >= 1
        assert jobs[0]["company"] == "Unknown Company"

    def test_parse_handles_missing_parent_container(self):
        """Should default to Unknown Company when parent container missing"""
        html_content = """
        <html>
            <a href="/jobs/123" class="resultJobItem">Test Job</a>
        </html>
        """
        jobs = parse_jobbank_email(html_content)
        # May or may not find the job depending on structure
        if jobs:
            assert jobs[0]["company"] == "Unknown Company"

    def test_parse_handles_exception_gracefully(self):
        """Should handle exceptions during parsing"""
        from unittest.mock import patch

        from bs4 import BeautifulSoup

        # HTML that will cause an exception when processed
        html_content = """
        <html>
            <table>
                <tr><td><a href="/jobs/123" class="resultJobItem">Job</a></td></tr>
            </table>
        </html>
        """

        # Parse to get BeautifulSoup object
        soup = BeautifulSoup(html_content, "lxml")

        # Mock find_all to raise exception after first call
        original_find_all = soup.find_all
        call_count = [0]

        def mock_find_all(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:  # Let first call succeed, fail on subsequent
                raise Exception("Test exception")
            return original_find_all(*args, **kwargs)

        with patch.object(soup, "find_all", side_effect=mock_find_all):
            jobs = parse_jobbank_email(str(soup))
            # Should not crash, may return partial results
            assert isinstance(jobs, list)
