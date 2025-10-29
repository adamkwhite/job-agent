"""
Unit tests for Work In Tech (getro.com) email parser
"""

from src.parsers.workintech_parser import can_parse, parse_workintech_email


class TestWorkInTechParser:
    """Test Work In Tech email parser functionality"""

    def test_can_parse_workintech_email(self):
        """Test Work In Tech email detection"""
        # Should parse Work In Tech emails
        assert can_parse("notifications@getro.com", "New jobs in Work In Tech's job board")
        assert can_parse("Work In Tech <hello@workintech.com>", "Job matches for you")
        assert can_parse("jobs@example.com", "Work in Tech - Your weekly job digest")

        # Job board pattern
        assert can_parse("alerts@board.com", "Job board: 5 new job matches")
        assert can_parse("noreply@jobs.com", "Your job board has new job postings")

        # Should not parse other emails
        assert not can_parse("linkedin@linkedin.com", "Your job alert")
        assert not can_parse("random@example.com", "Random newsletter")

    def test_parse_workintech_email_with_jobs(self):
        """Test parsing Work In Tech email with multiple jobs"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <img alt="RoboTech Logo" />
                        <a href="https://getro.com/companies/robotech/click?job=123">
                            <span style="font-size: 16px">Director of Engineering</span>
                        </a>
                        <div>RoboTech · Toronto, ON</div>
                    </td>
                </table>
                <table>
                    <td>
                        <img alt="AI Innovations Logo" />
                        <a href="https://getro.com/companies/aiinn/click?job=456">
                            <span style="font-size: 16px">VP Product Management</span>
                        </a>
                        <div>AI Innovations · Remote</div>
                    </td>
                </table>
                <a href="https://getro.com/more">See more jobs</a>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        assert len(jobs) == 2

        # First job
        assert jobs[0]["title"] == "Director of Engineering"
        assert jobs[0]["company"] == "RoboTech"
        assert jobs[0]["location"] == "Toronto, ON"
        assert "getro.com" in jobs[0]["link"]
        assert "click" in jobs[0]["link"]

        # Second job
        assert jobs[1]["title"] == "VP Product Management"
        assert jobs[1]["company"] == "AI Innovations"
        assert jobs[1]["location"] == "Remote"

    def test_parse_workintech_email_without_styled_title(self):
        """Test parsing jobs where title is in link text"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://getro.com/job/789">
                            Senior Hardware Engineer
                        </a>
                        <div>Tech Company · Waterloo, ON</div>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Hardware Engineer"
        assert jobs[0]["company"] == "Tech Company"
        assert jobs[0]["location"] == "Waterloo, ON"

    def test_parse_workintech_skip_navigation_links(self):
        """Test that parser skips navigation links"""
        html_content = """
        <html>
            <body>
                <a href="https://getro.com/more/click?ref=email">See more jobs</a>
                <a href="https://getro.com/link">this link</a>
                <a href="https://getro.com/brand/click">Work In Tech</a>
                <table>
                    <td>
                        <a href="https://getro.com/job/click?id=999">
                            <span style="font-size: 16px">Real Job Title - Director</span>
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        # Should only get the real job, not navigation links
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Real Job Title - Director"

    def test_parse_workintech_deduplicate_jobs(self):
        """Test that duplicate jobs are filtered out"""
        html_content = """
        <html>
            <body>
                <a href="https://getro.com/job1/click">Engineering Manager</a>
                <a href="https://getro.com/job1/click?ref=2">Engineering Manager</a>
                <a href="https://getro.com/job2/click">Product Director</a>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        # Should only return unique jobs
        assert len(jobs) == 2
        titles = [job["title"] for job in jobs]
        assert "Engineering Manager" in titles
        assert "Product Director" in titles

    def test_parse_workintech_with_missing_company(self):
        """Test parsing job with missing company info"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://getro.com/job/111/click">
                            <span style="font-size: 16px">Head of Engineering</span>
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Head of Engineering"
        assert jobs[0]["company"] == "Unknown Company"
        assert jobs[0]["location"] == "Unknown Location"

    def test_parse_workintech_infer_ontario_location(self):
        """Test that parser infers Ontario location from context"""
        html_content = """
        <html>
            <body>
                <p>Jobs matching your preferences in Ontario, Canada</p>
                <table>
                    <td>
                        <a href="https://getro.com/job/222/click">
                            VP Engineering
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["location"] == "Ontario, Canada"

    def test_parse_workintech_no_jobs(self):
        """Test parsing email with no job listings"""
        html_content = """
        <html>
            <body>
                <p>No new jobs match your criteria this week.</p>
                <a href="https://getro.com/preferences">Update your preferences</a>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)
        assert jobs == []

    def test_parse_workintech_relative_urls(self):
        """Test handling of relative URLs"""
        html_content = """
        <html>
            <body>
                <a href="getro.com/job/333/click">Director Position</a>
            </body>
        </html>
        """

        jobs = parse_workintech_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["link"].startswith("https://")
        assert "getro.com" in jobs[0]["link"]
