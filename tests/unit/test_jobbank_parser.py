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
