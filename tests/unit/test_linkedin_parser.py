"""
Unit tests for LinkedIn email parser
"""

import email

from src.parsers.linkedin_parser import LinkedInParser


class TestLinkedInParserCanHandle:
    """Test LinkedIn parser email detection"""

    def test_can_handle_linkedin_from_address(self):
        """Should handle emails from jobs-noreply@linkedin.com"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Job alert for you\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_linkedin_domain(self):
        """Should handle emails from linkedin.com domain"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: notifications@linkedin.com\nSubject: New jobs matching your search\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_job_alert_subject(self):
        """Should handle emails with 'job alert' subject"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Job Alert: Engineering Jobs\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_jobs_matching_subject(self):
        """Should handle emails with 'jobs matching' subject"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: 10 jobs matching your preferences\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_new_jobs_subject(self):
        """Should handle emails with 'new jobs' subject"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: New jobs for you\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_jobs_similar_subject(self):
        """Should handle emails with 'jobs similar' subject"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Jobs similar to your search\n\nBody"
        )
        assert parser.can_handle(email_message) is True

    def test_can_handle_forwarded_linkedin_email(self):
        """Should handle forwarded LinkedIn emails based on body content"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            """From: friend@example.com
Subject: FWD: Job alert
Content-Type: text/html

<html>
<body>
    Forwarded from jobs-noreply@linkedin.com
    <a href="https://linkedin.com/jobs/view/12345">Job Link</a>
</body>
</html>
"""
        )
        assert parser.can_handle(email_message) is True

    def test_cannot_handle_unrelated_email(self):
        """Should reject emails without LinkedIn indicators"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: random@example.com\nSubject: Newsletter\n\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_cannot_handle_linkedin_without_job_keywords(self):
        """Should reject LinkedIn emails without job alert keywords"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Profile views update\n\nBody"
        )
        assert parser.can_handle(email_message) is False

    def test_can_handle_case_insensitive(self):
        """Should handle case-insensitive matching"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: JOBS-NOREPLY@LINKEDIN.COM\nSubject: JOB ALERT\n\nBody"
        )
        assert parser.can_handle(email_message) is True


class TestLinkedInParserParse:
    """Test LinkedIn parser parsing logic"""

    def test_parse_plain_text_fallback(self):
        """Should parse plain text emails when no HTML"""
        parser = LinkedInParser()
        text_content = """
        Here are your job recommendations:

        https://www.linkedin.com/jobs/view/12345
        VP Engineering - TechCorp

        https://www.linkedin.com/jobs/view/67890
        Director Product - StartupXYZ
        """
        email_message = email.message_from_string(
            f"From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/plain\n\n{text_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 2

        # Plain text fallback uses generic values
        assert result.opportunities[0].company == "Unknown"
        assert result.opportunities[0].title == "Job Opportunity"
        assert result.opportunities[0].link == "https://www.linkedin.com/jobs/view/12345"

    def test_parse_filters_non_job_links(self):
        """Should filter out non-job links"""
        parser = LinkedInParser()
        html_content = """
        <html><body>
            <a href="https://www.linkedin.com/jobs/view/555">VP Engineering</a>
            <a href="https://www.linkedin.com/settings/unsubscribe">Unsubscribe</a>
            <a href="https://www.linkedin.com/privacy">Privacy Policy</a>
            <a href="https://www.linkedin.com/help">Help</a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1  # Only the job link
        assert result.opportunities[0].link == "https://www.linkedin.com/jobs/view/555"

    def test_parse_skips_jobs_without_title_or_company(self):
        """Should skip jobs missing both title and company"""
        parser = LinkedInParser()
        html_content = """
        <html><body>
            <a href="https://www.linkedin.com/jobs/view/666"></a>
            <a href="https://www.linkedin.com/jobs/view/777">Good Job Title</a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1  # Only the one with title

    def test_parse_uses_title_attribute_fallback(self):
        """Should use title attribute when link text is short"""
        parser = LinkedInParser()
        html_content = """
        <html><body>
            <tr>
                <td>
                    <a href="https://www.linkedin.com/jobs/view/888" title="VP of Product">VP of Product TestCorp</a>
                </td>
            </tr>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert "VP of Product" in result.opportunities[0].title

    def test_parse_handles_exception(self):
        """Should return error result on exception"""
        parser = LinkedInParser()

        # Create a mock that raises an exception
        def mock_extract_body(_msg):
            raise ValueError("Simulated parsing error")

        parser.extract_email_body = mock_extract_body

        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Job Alert\n\n"
        )

        result = parser.parse(email_message)

        assert result.success is False
        assert result.error is not None
        assert "Simulated parsing error" in result.error
        assert len(result.opportunities) == 0

    def test_parse_extracts_source_email(self):
        """Should extract and store source email address"""
        parser = LinkedInParser()
        html_content = """
        <html><body>
            <a href="https://www.linkedin.com/jobs/view/999">Test Job</a>
        </body></html>
        """
        email_message = email.message_from_string(
            f"From: LinkedIn Jobs <jobs-noreply@linkedin.com>\nSubject: Job Alert\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 1
        assert result.opportunities[0].source_email == "jobs-noreply@linkedin.com"


class TestLinkedInParserExtractTitle:
    """Test title extraction logic"""

    def test_extract_title_from_link_text(self):
        """Should extract title from link text when long enough"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <a href="https://linkedin.com/jobs/view/1">Senior Product Manager</a>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        title = parser._extract_title(link, soup)

        assert title == "Senior Product Manager"

    def test_extract_title_from_parent_tr(self):
        """Should extract title from parent <tr> text"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <a href="https://linkedin.com/jobs/view/2">
                        Director of Engineering Robotics Inc · Toronto, ON
                    </a>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        title = parser._extract_title(link, soup)

        assert "Director of Engineering" in title

    def test_extract_title_uses_title_attribute(self):
        """Should use title attribute when link text is short"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <a href="https://linkedin.com/jobs/view/3" title="VP of Product">Apply</a>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        title = parser._extract_title(link, soup)

        assert title == "VP of Product"

    def test_extract_title_returns_short_text(self):
        """Should return short text if no better option"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <a href="https://linkedin.com/jobs/view/4">Job</a>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        title = parser._extract_title(link, soup)

        assert title == "Job"


class TestLinkedInParserExtractCompany:
    """Test company extraction logic"""

    def test_extract_company_from_job_info(self):
        """Should extract company from parsed job info"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <a href="https://linkedin.com/jobs/view/1">
                        Engineering Manager CompanyName · Remote
                    </a>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        company = parser._extract_company(link, soup)

        assert company == "CompanyName"

    def test_extract_company_from_pattern_company_colon(self):
        """Should extract company from 'Company: X' pattern"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/2">Job Title</a>
                <span>Company: TechCorp</span>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        company = parser._extract_company(link, soup)

        assert company == "TechCorp"

    def test_extract_company_from_pattern_at(self):
        """Should extract company from 'at X' pattern"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/3">Job Title</a>
                <span>at: StartupXYZ</span>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        company = parser._extract_company(link, soup)

        assert company == "StartupXYZ"

    def test_extract_company_returns_empty_when_not_found(self):
        """Should return empty string when company not found"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <a href="https://linkedin.com/jobs/view/4">Just a title</a>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        company = parser._extract_company(link, soup)

        assert company == ""


class TestLinkedInParserExtractLocation:
    """Test location extraction logic"""

    def test_extract_location_from_job_info(self):
        """Should extract location from parsed job info"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <a href="https://linkedin.com/jobs/view/1">
                        VP Engineering TechCorp · San Francisco, CA
                    </a>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        location = parser._extract_location(link, soup)

        assert location == "San Francisco, CA"

    def test_extract_location_from_pattern_location_colon(self):
        """Should extract location from 'Location: X' pattern"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/2">Job Title</a>
                <span>Location: Toronto, ON</span>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        location = parser._extract_location(link, soup)

        assert location == "Toronto, ON"

    def test_extract_location_from_pattern_in(self):
        """Should extract location from 'in X' pattern"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/3">Job Title</a>
                <span>in: Waterloo, ON</span>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        location = parser._extract_location(link, soup)

        assert location == "Waterloo, ON"

    def test_extract_location_from_city_state_pattern(self):
        """Should extract location from City, ST pattern"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/4">Job Title</a>
                <span>Available in Burlington, ON for immediate start</span>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        location = parser._extract_location(link, soup)

        assert location == "Burlington, ON"

    def test_extract_location_returns_empty_when_not_found(self):
        """Should return empty string when location not found"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <a href="https://linkedin.com/jobs/view/5">Just a title</a>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        location = parser._extract_location(link, soup)

        assert location == ""


class TestLinkedInParserParseJobInfo:
    """Test job info parsing logic"""

    def test_parse_job_info_with_middle_dot(self):
        """Should parse job info with middle dot separator"""
        parser = LinkedInParser()
        job_info = "Director of Product - Customer Care & AI Wealthsimple · Canada (Remote)"

        title, company, location = parser._parse_job_info(job_info)

        assert "Director of Product" in title
        assert company == "Wealthsimple"
        assert location == "Canada (Remote)"

    def test_parse_job_info_simple_format(self):
        """Should parse simple job info format"""
        parser = LinkedInParser()
        job_info = "Engineering Manager CompanyName · Toronto, ON"

        title, company, location = parser._parse_job_info(job_info)

        assert "Engineering Manager" in title
        assert company == "CompanyName"
        assert location == "Toronto, ON"

    def test_parse_job_info_no_location(self):
        """Should handle job info without location"""
        parser = LinkedInParser()
        job_info = "Senior Product Manager TechCorp"

        title, company, location = parser._parse_job_info(job_info)

        assert "Senior Product Manager" in title
        assert location == ""

    def test_parse_job_info_excludes_title_words_from_company(self):
        """Should not treat title words as company name"""
        parser = LinkedInParser()
        job_info = "Senior Engineering Manager · Remote"

        title, company, location = parser._parse_job_info(job_info)

        # "Senior", "Engineering", "Manager" should be in title, not company
        assert "Senior" in title or "Engineering" in title or "Manager" in title
        assert location == "Remote"

    def test_parse_job_info_handles_slash_in_title(self):
        """Should handle titles with slashes like AI/ML"""
        parser = LinkedInParser()
        job_info = "Product Manager - AI/ML TechCompany · Remote"

        title, company, location = parser._parse_job_info(job_info)

        assert "AI/ML" in title
        assert company == "TechCompany"

    def test_parse_job_info_returns_whole_as_title_if_no_company(self):
        """Should return whole string as title if company can't be parsed"""
        parser = LinkedInParser()
        job_info = "senior engineering manager remote"

        title, company, location = parser._parse_job_info(job_info)

        assert title == "senior engineering manager remote" or title == "senior engineering manager"
        assert company == "" or company == "remote"


class TestLinkedInParserGetJobInfoText:
    """Test job info text extraction"""

    def test_get_job_info_from_parent_tr(self):
        """Should get job info text from parent <tr>"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <a href="https://linkedin.com/jobs/view/1">
                        VP Engineering TechCorp · Remote
                    </a>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        job_info = parser._get_job_info_text(link)

        assert "VP Engineering" in job_info
        assert "TechCorp" in job_info
        assert "Remote" in job_info

    def test_get_job_info_searches_up_hierarchy(self):
        """Should search up to 5 levels to find <tr>"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <div>
                        <div>
                            <a href="https://linkedin.com/jobs/view/2">
                                Director CompanyX · Location
                            </a>
                        </div>
                    </div>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        job_info = parser._get_job_info_text(link)

        assert "Director" in job_info
        assert len(job_info) > 10

    def test_get_job_info_returns_empty_if_no_tr(self):
        """Should return empty string if no <tr> parent found"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <div>
                <a href="https://linkedin.com/jobs/view/3">Job</a>
            </div>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        job_info = parser._get_job_info_text(link)

        assert job_info == ""

    def test_get_job_info_filters_short_text(self):
        """Should filter out very short text"""
        parser = LinkedInParser()
        html = """
        <html><body>
            <tr>
                <td>
                    <a href="https://linkedin.com/jobs/view/4">X</a>
                </td>
            </tr>
        </body></html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        link = soup.find("a")

        job_info = parser._get_job_info_text(link)

        # Should be empty or at least check length requirement
        assert len(job_info) == 0 or len(job_info) > 10


class TestLinkedInParserHelperMethods:
    """Test base parser helper methods"""

    def test_is_job_link_linkedin_jobs(self):
        """Should identify LinkedIn job links"""
        parser = LinkedInParser()

        assert parser.is_job_link("https://www.linkedin.com/jobs/view/12345") is True
        # Search URLs should be rejected (Issue #35)
        assert parser.is_job_link("https://linkedin.com/jobs/search") is False
        assert parser.is_job_link("https://linkedin.com/jobs/search?keywords=director") is False

    def test_is_job_link_excludes_settings(self):
        """Should exclude settings and unsubscribe links"""
        parser = LinkedInParser()

        assert parser.is_job_link("https://linkedin.com/settings/unsubscribe") is False
        assert parser.is_job_link("https://linkedin.com/privacy") is False

    def test_clean_text_removes_whitespace(self):
        """Should clean up extra whitespace"""
        parser = LinkedInParser()

        assert parser.clean_text("  Multiple   spaces  ") == "Multiple spaces"
        assert parser.clean_text("Line\nbreaks\nhere") == "Line breaks here"
        assert parser.clean_text("") == ""
        assert parser.clean_text(None) == ""

    def test_clean_title_removes_jobs_similar_to_prefix(self):
        """Should remove 'Jobs similar to' prefix from email subject lines (Issue #41)"""
        parser = LinkedInParser()

        # Test basic "Jobs similar to" removal
        assert (
            parser._clean_title("Jobs similar to Head of Engineering, Americas at")
            == "Head of Engineering, Americas"
        )

        # Test with " at" suffix
        assert (
            parser._clean_title("Jobs similar to Director, R&D Software Engineering at")
            == "Director, R&D Software Engineering"
        )

        # Test with " at [Company]" in middle
        assert (
            parser._clean_title("Jobs similar to Senior Engineering Manager at Dropbox")
            == "Senior Engineering Manager"
        )

        # Test normal title without prefix (should be unchanged)
        assert parser._clean_title("Software Engineer") == "Software Engineer"

        # Test empty/None
        assert parser._clean_title("") == ""
        assert parser._clean_title(None) is None


class TestLinkedInParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_empty_html(self):
        """Should handle empty HTML gracefully"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/html\n\n"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 0

    def test_parse_malformed_html(self):
        """Should handle malformed HTML"""
        parser = LinkedInParser()
        html_content = "<html><body><a href=>Broken</a></body></html>"
        email_message = email.message_from_string(
            f"From: jobs-noreply@linkedin.com\nSubject: Job Alert\nContent-Type: text/html\n\n{html_content}"
        )

        result = parser.parse(email_message)

        # Should not crash
        assert result.success is True

    def test_parse_no_content(self):
        """Should handle emails with no HTML or text"""
        parser = LinkedInParser()
        email_message = email.message_from_string(
            "From: jobs-noreply@linkedin.com\nSubject: Job Alert\n\n"
        )

        result = parser.parse(email_message)

        assert result.success is True
        assert len(result.opportunities) == 0

    def test_extract_email_address_with_name(self):
        """Should extract email from 'Name <email>' format"""
        parser = LinkedInParser()

        email_addr = parser.extract_email_address("LinkedIn Jobs <jobs-noreply@linkedin.com>")

        assert email_addr == "jobs-noreply@linkedin.com"

    def test_extract_email_address_plain(self):
        """Should handle plain email address"""
        parser = LinkedInParser()

        email_addr = parser.extract_email_address("jobs-noreply@linkedin.com")

        assert email_addr == "jobs-noreply@linkedin.com"
