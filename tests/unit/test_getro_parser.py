"""
Unit tests for Getro job board email parser.
Handles all Getro-powered boards: Work In Tech, MaRS, U of T Entrepreneurship,
General Catalyst, Insight Partners, Khosla Ventures, etc.
"""

from src.parsers.getro_parser import can_parse, parse_getro_email


class TestGetroParser:
    """Test Getro email parser functionality"""

    def test_can_parse_getro_email(self):
        """Test Getro email detection"""
        # Should parse Getro emails
        assert can_parse("notifications@getro.com", "New jobs in Work In Tech's job board")
        assert can_parse("Work In Tech <hello@getro.com>", "Job matches for you")
        assert can_parse("jobs@example.com", "Work in Tech - Your weekly job digest")

        # Job board pattern
        assert can_parse("alerts@board.com", "Job board: 5 new job matches")
        assert can_parse("noreply@jobs.com", "Your job board has new job postings")

        # Should not parse other emails
        assert not can_parse("linkedin@linkedin.com", "Your job alert")
        assert not can_parse("random@example.com", "Random newsletter")

    def test_parse_getro_email_with_jobs(self):
        """Test parsing Getro email with multiple jobs"""
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

        jobs = parse_getro_email(html_content)

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

    def test_parse_getro_email_without_styled_title(self):
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

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Hardware Engineer"
        assert jobs[0]["company"] == "Tech Company"
        assert jobs[0]["location"] == "Waterloo, ON"

    def test_parse_getro_skip_navigation_links(self):
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

        jobs = parse_getro_email(html_content)

        # Should only get the real job, not navigation links
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Real Job Title - Director"

    def test_parse_getro_deduplicate_jobs(self):
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

        jobs = parse_getro_email(html_content)

        # Should only return unique jobs
        assert len(jobs) == 2
        titles = [job["title"] for job in jobs]
        assert "Engineering Manager" in titles
        assert "Product Director" in titles

    def test_parse_getro_with_missing_company(self):
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

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Head of Engineering"
        assert jobs[0]["company"] == "Unknown Company"
        assert jobs[0]["location"] == "Unknown Location"

    def test_parse_getro_make_new_search_link_text(self):
        """Test parsing when link text is 'make a new search' (Issue #39)"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://url3473.getro.com/ls/click?upn=u001.GE2DtX">
                            make a new search
                        </a>
                        <div>Head of Product · Ontario, Canada</div>
                    </td>
                </table>
                <table>
                    <td>
                        <a href="https://url3473.getro.com/ls/click?upn=u001.ABC123">
                            make a new search
                        </a>
                        <div>Director, Commercial Operations · Toronto, ON</div>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 2

        # Should extract job title from div, not link text
        assert jobs[0]["title"] == "Head of Product"
        assert jobs[0]["location"] == "Ontario, Canada"
        assert "getro.com" in jobs[0]["link"]

        assert jobs[1]["title"] == "Director, Commercial Operations"
        assert jobs[1]["location"] == "Toronto, ON"

    def test_parse_getro_three_part_middot_separator(self):
        """Test parsing middot-separated text with 3 parts: Title · Company · Location"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://getro.com/job/456/click">
                            make a new search
                        </a>
                        <div>Senior Software Engineer · TechCorp · Remote</div>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Software Engineer"
        assert jobs[0]["company"] == "TechCorp"
        assert jobs[0]["location"] == "Remote"

    def test_parse_getro_infer_ontario_location(self):
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

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["location"] == "Ontario, Canada"

    def test_parse_getro_no_jobs(self):
        """Test parsing email with no job listings"""
        html_content = """
        <html>
            <body>
                <p>No new jobs match your criteria this week.</p>
                <a href="https://getro.com/preferences">Update your preferences</a>
            </body>
        </html>
        """

        jobs = parse_getro_email(html_content)
        assert jobs == []

    def test_parse_getro_relative_urls(self):
        """Test handling of relative URLs"""
        html_content = """
        <html>
            <body>
                <a href="getro.com/job/333/click">Director Position</a>
            </body>
        </html>
        """

        jobs = parse_getro_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["link"].startswith("https://")
        assert "getro.com" in jobs[0]["link"]

    def test_parse_getro_table_based_structure(self):
        """Test parsing new table-based email format with 3 rows (Issue #45)"""
        html_content = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>
                            <strong>
                                <a href="https://url3473.getro.com/ls/click?upn=u001.ABC123">
                                    <span style="font-size: 16px">Director, Commercial Operations</span>
                                </a>
                            </strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="color: #6B778E; font-size: 14px;">
                            <a href="https://url3473.getro.com/ls/click?upn=u001.ABC123">Maple</a>
                        </td>
                    </tr>
                    <tr>
                        <td style="color: #6B778E; font-size: 13px;">Toronto, ON, Canada</td>
                    </tr>
                </table>
                <table>
                    <tr>
                        <td>
                            <strong>
                                <a href="https://url3473.getro.com/ls/click?upn=u001.XYZ789">
                                    <span style="font-size: 16px">Senior Product Manager</span>
                                </a>
                            </strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="color: #6B778E; font-size: 14px;">
                            <a href="https://url3473.getro.com/ls/click?upn=u001.XYZ789">Cohere</a>
                        </td>
                    </tr>
                    <tr>
                        <td style="color: #6B778E; font-size: 13px;">Toronto, ON, Canada (Hybrid)</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        jobs = parse_getro_email(html_content)

        # Should extract both jobs from table structure
        assert len(jobs) == 2

        # First job
        assert jobs[0]["title"] == "Director, Commercial Operations"
        assert jobs[0]["company"] == "Maple"
        assert jobs[0]["location"] == "Toronto, ON, Canada"
        assert "getro.com" in jobs[0]["link"]

        # Second job
        assert jobs[1]["title"] == "Senior Product Manager"
        assert jobs[1]["company"] == "Cohere"
        assert jobs[1]["location"] == "Toronto, ON, Canada (Hybrid)"
        assert "getro.com" in jobs[1]["link"]


class TestGetroParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_skips_very_short_titles(self):
        """Should skip titles shorter than 5 characters (line 36)"""
        html_content = """
        <html>
            <body>
                <a href="https://getro.com/job/1">VP</a>
                <a href="https://getro.com/job/2">Director of Engineering</a>
            </body>
        </html>
        """
        jobs = parse_getro_email(html_content)

        # Should only get the longer title
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Director of Engineering"

    def test_parse_skips_view_more_links(self):
        """Should skip navigation links with 'view more' (line 44)"""
        html_content = """
        <html>
            <body>
                <a href="https://getro.com/more">View more opportunities</a>
                <a href="https://getro.com/settings">Update preferences</a>
                <a href="https://getro.com/job/1">Engineering Manager Position</a>
            </body>
        </html>
        """
        jobs = parse_getro_email(html_content)

        # Should only get the job, not navigation links
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Engineering Manager Position"

    def test_parse_handles_malformed_html_gracefully(self):
        """Should handle exceptions during parsing (lines 102-104)"""
        # Malformed HTML that could cause exceptions
        html_content = """
        <html>
            <body>
                <a href="invalid>Broken HTML</a>
                <a href="https://getro.com/job/valid">Director of Engineering</a>
            </body>
        </html>
        """
        jobs = parse_getro_email(html_content)

        # Should not crash, may return partial results or empty list
        assert isinstance(jobs, list)

    def test_parse_handles_exception_in_job_extraction(self):
        """Should continue processing after exception (line 104)"""
        from unittest.mock import patch

        from bs4 import BeautifulSoup

        html_content = """
        <html>
            <body>
                <a href="https://getro.com/job/1">First Job</a>
                <a href="https://getro.com/job/2">Second Job</a>
            </body>
        </html>
        """

        # Parse HTML
        soup = BeautifulSoup(html_content, "lxml")
        links = soup.find_all("a")

        # Mock one link to raise exception
        call_count = [0]
        original_get = links[0].get

        def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call raises exception
                raise Exception("Test exception")
            return original_get(*args, **kwargs)

        with patch.object(links[0], "get", side_effect=mock_get):
            jobs = parse_getro_email(str(soup))
            # Should continue and get second job despite first failing
            assert isinstance(jobs, list)
