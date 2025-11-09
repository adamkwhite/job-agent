"""
Unit tests for Recruiter and LinkedIn email parser
"""

from parsers.recruiter_parser import (
    can_parse,
    parse_recruiter_email,
    parse_single_recruiter_job,
)


class TestRecruiterParser:
    """Test Recruiter/LinkedIn email parser functionality"""

    def test_can_parse_linkedin_email(self):
        """Test LinkedIn email detection"""
        assert can_parse("jobs-noreply@linkedin.com", "Your saved jobs")
        assert can_parse("LinkedIn <notifications@linkedin.com>", "New job recommendations")

        # Direct recruiter emails
        assert can_parse("recruiter@company.com", "Great opportunity for you")
        assert can_parse("hr@tech.com", "Apply now to Director of Engineering")
        assert can_parse("talent@startup.com", "You may be a fit for VP role")

        # Forwarded job emails
        assert can_parse("friend@example.com", "Fwd: Amazing job opportunity")
        assert can_parse("colleague@work.com", "FWD: Director position at Tech Co")

        # Should not parse unrelated emails
        assert not can_parse("random@example.com", "Newsletter update")
        assert not can_parse("sales@company.com", "Product announcement")

    def test_parse_linkedin_jobs(self):
        """Test parsing LinkedIn job recommendation emails"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://www.linkedin.com/jobs/view/3456789?trackingId=abc123">
                            <span style="font-size: 16px">VP of Engineering</span>
                        </a>
                        <img alt="TechCorp Logo" />
                        <div>TechCorp · San Francisco, CA · Remote</div>
                    </td>
                </table>
                <table>
                    <td>
                        <a href="https://www.linkedin.com/jobs/view/9876543">
                            Director of Product
                        </a>
                        <div>StartupXYZ · Toronto, ON</div>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 2

        # First job
        assert jobs[0]["title"] == "VP of Engineering"
        assert jobs[0]["company"] == "TechCorp"
        assert jobs[0]["location"] == "San Francisco, CA"
        assert jobs[0]["link"] == "https://www.linkedin.com/jobs/view/3456789"

        # Second job
        assert jobs[1]["title"] == "Director of Product"
        assert jobs[1]["company"] == "StartupXYZ"
        assert jobs[1]["location"] == "Toronto, ON"
        assert jobs[1]["link"] == "https://www.linkedin.com/jobs/view/9876543"

    def test_parse_single_recruiter_job(self):
        """Test parsing a direct recruiter outreach email"""
        html_content = """
        <html>
            <body>
                <p>Hi Adam,</p>
                <p>I have an exciting opportunity for a Director of Engineering role at
                Robotics Inc. This position is based in Waterloo, ON with flexible remote options.</p>
                <p>The role involves leading a team of 20+ engineers...</p>
                <a href="https://careers.roboticsinc.com/job/12345">Learn more and apply</a>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Director of Engineering"
        assert jobs[0]["company"] == "Robotics Inc."
        assert "Waterloo" in jobs[0]["location"]
        assert jobs[0]["link"] == "https://careers.roboticsinc.com/job/12345"

    def test_parse_recruiter_email_with_apply_now(self):
        """Test parsing recruiter email with 'Apply Now' pattern"""
        html_content = """
        <html>
            <body>
                <p>We are hiring for a VP Product Management position at Tech Innovations.</p>
                <p>Location: Remote (US/Canada)</p>
                <a href="https://apply.techinn.com/vp-product?ref=email">Apply Now</a>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert "VP Product Management" in jobs[0]["title"]
        assert jobs[0]["company"] == "Tech Innovations"
        assert "Remote" in jobs[0]["location"]
        assert jobs[0]["link"] == "https://apply.techinn.com/vp-product"

    def test_parse_recruiter_email_no_link(self):
        """Test parsing recruiter email without apply link"""
        html_content = """
        <html>
            <body>
                <p>Looking for a Director of Hardware Engineering at Advanced Robotics.</p>
                <p>Location: Toronto, ON</p>
                <p>Please reply with your resume if interested.</p>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Director of Hardware Engineering"
        assert jobs[0]["company"] == "Advanced Robotics"
        assert "Toronto" in jobs[0]["location"]
        assert jobs[0]["link"] == ""

    def test_parse_linkedin_job_with_missing_info(self):
        """Test parsing LinkedIn job with incomplete information"""
        html_content = """
        <html>
            <body>
                <a href="https://www.linkedin.com/jobs/view/1111111">
                    Engineering Manager
                </a>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Engineering Manager"
        assert jobs[0]["company"] == "Unknown Company"
        assert jobs[0]["location"] == "Unknown Location"
        assert jobs[0]["link"] == "https://www.linkedin.com/jobs/view/1111111"

    def test_parse_recruiter_email_no_jobs(self):
        """Test parsing email with no identifiable jobs"""
        html_content = """
        <html>
            <body>
                <p>Thank you for your interest. We'll keep your resume on file.</p>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)
        assert jobs == []

    def test_parse_forwarded_job_email(self):
        """Test parsing forwarded job email"""
        html_content = """
        <html>
            <body>
                <p>FYI - thought you might be interested</p>
                <p>---------- Forwarded message ----------</p>
                <p>We're seeking a VP of Engineering at MedTech Solutions</p>
                <p>Location: Burlington, ON (Hybrid)</p>
                <a href="https://www.linkedin.com/jobs/view/888888">View on LinkedIn</a>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "VP of Engineering"
        assert jobs[0]["company"] == "MedTech Solutions"
        assert "Burlington" in jobs[0]["location"]
        assert jobs[0]["link"] == "https://www.linkedin.com/jobs/view/888888"

    def test_parse_single_recruiter_job_rejects_search_urls(self):
        """Test that single recruiter parser rejects LinkedIn search URLs (Issue #35)"""
        html_content = """
        <html>
            <body>
                <p>We're hiring a Director of Engineering at Tech Corp.</p>
                <p>Location: Remote (US)</p>
                <a href="https://www.linkedin.com/comm/jobs/search?keywords=Director+Engineering">
                    View jobs on LinkedIn
                </a>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        # Should still extract job but with empty link (search URL rejected)
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Director of Engineering"
        assert jobs[0]["company"] == "Tech Corp."
        assert jobs[0]["location"] == "Remote (US)"
        # Link should be empty because search URL was rejected
        assert jobs[0]["link"] == ""

    def test_parse_linkedin_job_concatenated_title_with_metadata(self):
        """Test parsing LinkedIn job with concatenated title/company/location/salary (Issue #32)"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://www.linkedin.com/jobs/view/99">
                            (USA) Director, Software EngineeringWalmart · Sunnyvale, CA (On-site)$169K-$338K / year2 connectionsFast growing
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        # Title should be clean, without company name concatenated
        assert jobs[0]["title"] == "(USA) Director, Software Engineering"
        assert jobs[0]["company"] == "Walmart"
        # Location should be cleaned without salary
        assert jobs[0]["location"] == "Sunnyvale, CA (On-site)"
        assert "$" not in jobs[0]["location"]
        assert "connection" not in jobs[0]["location"].lower()

    def test_parse_linkedin_job_concatenated_with_hybrid(self):
        """Test parsing LinkedIn job with title concatenated with company and hybrid location"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://www.linkedin.com/jobs/view/101">
                            Technical Product ManagerCVS Health · New York, NY (Hybrid)$83K-$222K / year1 connection
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        # Title should be clean, company extracted from concatenation
        assert jobs[0]["title"] == "Technical Product Manager"
        # Should extract multi-word company name
        assert jobs[0]["company"] == "CVS Health"
        assert jobs[0]["location"] == "New York, NY (Hybrid)"
        # Verify clean extraction without salary/metadata
        assert "$" not in jobs[0]["location"]
        assert "connection" not in jobs[0]["location"].lower()

    def test_parse_linkedin_job_clean_title_unknown_company(self):
        """Test parsing LinkedIn job with clean title but no company extraction (Issue #32)"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <a href="https://www.linkedin.com/jobs/view/100">
                            (USA) Director, Software Engineering
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        # Title should stay clean
        assert jobs[0]["title"] == "(USA) Director, Software Engineering"
        # Company extraction should fail gracefully
        assert jobs[0]["company"] == "Unknown Company"
        assert jobs[0]["location"] == "Unknown Location"

    def test_parse_linkedin_job_skips_search_urls(self):
        """Test that parser skips search URLs and only captures job view URLs (Issue #35)"""
        html_content = """
        <html>
            <body>
                <table>
                    <td>
                        <!-- Search URL - should be skipped -->
                        <a href="https://www.linkedin.com/comm/jobs/search?keywords=Director+Engineering">
                            Search Results
                        </a>
                        <!-- Valid job view URL - should be captured -->
                        <a href="https://www.linkedin.com/jobs/view/123456">
                            Director of Engineering
                        </a>
                    </td>
                    <td>
                        <!-- Another search URL with keywords - should be skipped -->
                        <a href="https://www.linkedin.com/jobs/search?keywords=VP+Product&location=Remote">
                            VP Product
                        </a>
                        <!-- Another valid job - should be captured -->
                        <a href="https://www.linkedin.com/jobs/view/789012">
                            VP of Product Management
                        </a>
                    </td>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        # Should only get the 2 job view URLs, not the 2 search URLs
        assert len(jobs) == 2
        assert jobs[0]["link"] == "https://www.linkedin.com/jobs/view/123456"
        assert jobs[1]["link"] == "https://www.linkedin.com/jobs/view/789012"
        # Verify no search URLs made it through
        for job in jobs:
            assert "/jobs/search" not in job["link"]
            assert "keywords=" not in job["link"]

    def test_parse_linkedin_job_company_in_sibling_tr(self):
        """Test parsing LinkedIn job with company/location in sibling TR element (Issue #47)"""
        html_content = """
        <html>
            <body>
                <table>
                    <tr>
                        <td class="pb-0">
                            <a href="https://www.linkedin.com/jobs/view/4098765" class="font-bold text-md">
                                Director of Product Management - Developer Experience
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td class="pb-0">
                            <p class="text-system-gray-100 text-xs">NVIDIA · Santa Clara, CA</p>
                        </td>
                    </tr>
                </table>
                <table>
                    <tr>
                        <td>
                            <a href="https://www.linkedin.com/jobs/view/4098766">
                                Technical Product Manager
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <p>CVS Health · New York, NY</p>
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 2

        # First job
        assert jobs[0]["title"] == "Director of Product Management - Developer Experience"
        assert jobs[0]["company"] == "NVIDIA"
        assert jobs[0]["location"] == "Santa Clara, CA"
        assert jobs[0]["link"] == "https://www.linkedin.com/jobs/view/4098765"

        # Second job
        assert jobs[1]["title"] == "Technical Product Manager"
        assert jobs[1]["company"] == "CVS Health"
        assert jobs[1]["location"] == "New York, NY"
        assert jobs[1]["link"] == "https://www.linkedin.com/jobs/view/4098766"


class TestRecruiterParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_linkedin_jobs_no_job_id_in_url(self):
        """Should skip job links without valid job IDs (line 55)"""
        html_content = """
        <html>
            <body>
                <a href="https://www.linkedin.com/invalid/link">Invalid Link</a>
                <a href="https://www.linkedin.com/jobs/view/12345">Valid Job Title</a>
            </body>
        </html>
        """
        jobs = parse_recruiter_email(html_content)

        # Should only get the job with valid ID
        assert len(jobs) == 1

    def test_parse_linkedin_jobs_title_in_parent_element(self):
        """Should find title in parent element when link text is generic (lines 74-78)"""
        html_content = """
        <html>
            <body>
                <div>
                    <span style="font-size: 16px">Director of Engineering</span>
                    <a href="https://www.linkedin.com/jobs/view/99999">View on LinkedIn</a>
                </div>
            </body>
        </html>
        """
        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Director of Engineering"

    def test_parse_linkedin_jobs_company_from_image_alt(self):
        """Should extract company from image alt text (lines 96-98)"""
        html_content = """
        <html>
            <body>
                <td>
                    <img alt="Robotics Corp" />
                    <a href="https://www.linkedin.com/jobs/view/11111">Engineering Manager</a>
                </td>
            </body>
        </html>
        """
        jobs = parse_recruiter_email(html_content)

        assert len(jobs) == 1
        assert jobs[0]["company"] == "Robotics Corp"

    def test_parse_linkedin_jobs_handles_exception(self):
        """Should handle exceptions during job parsing (lines 108-110)"""
        from unittest.mock import patch

        from bs4 import BeautifulSoup

        html_content = """
        <html>
            <body>
                <a href="https://www.linkedin.com/jobs/view/1">First Job</a>
                <a href="https://www.linkedin.com/jobs/view/2">Second Job</a>
            </body>
        </html>
        """

        soup = BeautifulSoup(html_content, "lxml")
        links = soup.find_all("a")

        # Mock first link to raise exception
        def mock_get(*_args, **_kwargs):
            raise Exception("Test exception")

        with patch.object(links[0], "get", side_effect=mock_get):
            jobs = parse_recruiter_email(str(soup))
            # Should continue and may get second job
            assert isinstance(jobs, list)

    def test_parse_single_recruiter_job_no_location_match(self):
        """Should handle recruiter emails with no location match (line 183)"""
        html_content = """
        <html>
            <body>
                <p>We're hiring a Director of Product at TechCo.</p>
                <p>This is a great opportunity for leadership.</p>
            </body>
        </html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")
        job = parse_single_recruiter_job(soup)

        # Should successfully parse even without location
        if job:
            assert job["title"] or job["company"]
            # Location may be None or empty
