"""
Unit tests for Recruiter and LinkedIn email parser
"""

from src.parsers.recruiter_parser import can_parse, parse_recruiter_email


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
