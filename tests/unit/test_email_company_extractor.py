"""
Tests for EmailCompanyExtractor

Tests company extraction from various email sources:
- LinkedIn job alerts
- Supra Product Leadership newsletter
- Built In job alerts
- F6S job alerts
- Job Bank emails
- Generic career page emails
"""

import email
from email.message import Message

from src.extractors.email_company_extractor import EmailCompanyExtractor


class TestEmailCompanyExtractorInit:
    """Test EmailCompanyExtractor initialization"""

    def test_init(self):
        """Test extractor initializes with correct name"""
        extractor = EmailCompanyExtractor()
        assert extractor.name == "email_company_extractor"


class TestEmailCompanyExtractorEmailBody:
    """Test email body extraction"""

    def test_get_email_body_plain_text(self):
        """Test extracting body from plain text email"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg.set_payload(b"Test email body")

        body = extractor._get_email_body(msg)
        assert body == "Test email body"

    def test_get_email_body_multipart_html(self):
        """Test extracting body from multipart HTML email"""
        extractor = EmailCompanyExtractor()

        msg = email.message_from_string(
            """Content-Type: multipart/alternative; boundary="boundary"

--boundary
Content-Type: text/plain

Plain text version
--boundary
Content-Type: text/html

<html><body>HTML version</body></html>
--boundary--
"""
        )

        body = extractor._get_email_body(msg)
        # Implementation returns first match (text/html OR text/plain)
        assert "Plain text version" in body or "HTML version" in body

    def test_get_email_body_empty(self):
        """Test extracting body from empty email"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        body = extractor._get_email_body(msg)
        assert body == ""


class TestLinkedInExtraction:
    """Test LinkedIn job alert company extraction"""

    def test_extract_from_linkedin_single_company(self):
        """Test extracting single company from LinkedIn email"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@linkedin.com"
        msg["Subject"] = "5 new jobs for Product Manager"

        body = """
Senior Product Manager
NVIDIA
Remote

Director of Engineering
Tesla
San Francisco, CA
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 2
        assert companies[0].name == "NVIDIA"
        assert "linkedin.com/company/nvidia" in companies[0].careers_url
        assert companies[0].source == "email"
        assert companies[1].name == "Tesla"

    def test_extract_from_linkedin_filters_locations(self):
        """Test that LinkedIn extraction filters out location names"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@linkedin.com"
        msg["Subject"] = "New jobs"

        body = """
Engineering Manager
Google
Toronto

Senior Engineer
Remote
Ontario
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        # Should only extract Google, not "Remote" or "Ontario"
        assert len(companies) == 1
        assert companies[0].name == "Google"

    def test_extract_from_linkedin_requires_job_keyword(self):
        """Test that company must follow a line with job keywords"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@linkedin.com"
        msg["Subject"] = "Jobs"

        body = """
Some Random Text
Company Name Without Job Title
Location

Product Manager
Salesforce
New York
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        # Should only extract Salesforce (follows "Product Manager")
        assert len(companies) == 1
        assert companies[0].name == "Salesforce"


class TestSupraExtraction:
    """Test Supra newsletter company extraction"""

    def test_extract_from_supra_with_ats_url(self):
        """Test extracting company from Supra with ATS URL"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "hello@supra.com"
        msg["Subject"] = "Product Leadership Jobs"

        body = """
*Google* is hiring a Senior Product Manager -
https://boards.greenhouse.io/google/jobs/12345
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 1
        assert companies[0].name == "Google"
        assert "greenhouse.io" in companies[0].careers_url

    def test_extract_from_supra_without_url(self):
        """Test extracting company from Supra without explicit URL"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "hello@supra.com"
        msg["Subject"] = "Product Leadership Jobs"

        body = """
*Adobe* is hiring a Director of Product
Some other text here
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 1
        assert companies[0].name == "Adobe"
        assert "google.com/search" in companies[0].careers_url  # Fallback

    def test_extract_from_supra_filters_false_positives(self):
        """Test that Supra extraction filters known false positives"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "hello@supra.com"
        msg["Subject"] = "Product Leadership Jobs"

        body = """
*Supra* is hiring
*Subscribe* is hiring
*Forwarded* is hiring
*Real Company* is hiring
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        # Should only extract Real Company
        assert len(companies) == 1
        assert companies[0].name == "Real Company"


class TestBuiltInExtraction:
    """Test Built In job alert extraction"""

    def test_extract_from_builtin_with_job_urls(self):
        """Test extracting Built In with job URLs"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "support@builtin.com"
        msg["Subject"] = "New job matches for product manager"

        body = """
<a href="https://builtin.com/job/product-manager/12345">Product Manager</a>
<a href="https://builtin.com/job/director-engineering/67890">Director of Engineering</a>
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 1
        assert companies[0].name == "Built In"
        assert "builtin.com/jobs" in companies[0].careers_url
        assert "2 jobs" in companies[0].source_details

    def test_extract_from_builtin_with_aws_tracking(self):
        """Test extracting Built In with AWS tracking URLs"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "support@builtin.com"
        msg["Subject"] = "Job matches"

        body = """
<a href="https://cb4sdw3d.r.us-west-2.awstrack.me/L0/https:%2F%2Fbuiltin.com%2Fjob%2Fsenior-pm%2F123">Senior PM</a>
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 1
        assert "builtin.com/job/senior-pm/123" in companies[0].notes

    def test_extract_from_builtin_no_jobs(self):
        """Test Built In email with no jobs returns empty"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "support@builtin.com"
        msg["Subject"] = "Update your preferences"

        body = "No job links here"
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 0


class TestF6SExtraction:
    """Test F6S job alert extraction"""

    def test_extract_from_f6s_with_companies(self):
        """Test extracting companies from F6S email"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@f6s.com"
        msg["Subject"] = "F6S Jobs"

        body = """
<h2>Stripe</h2>
<h2>Airbnb</h2>
<h2>F6S</h2>
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        # Should extract Stripe and Airbnb, but not F6S itself
        assert len(companies) == 2
        company_names = [c.name for c in companies]
        assert "Stripe" in company_names
        assert "Airbnb" in company_names
        assert "F6S" not in company_names


class TestGenericExtraction:
    """Test generic email extraction"""

    def test_extract_generic_with_career_urls(self):
        """Test extracting companies from generic email with career URLs"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "recruiter@example.com"
        msg["Subject"] = "Job Opportunity"

        body = """
Check out https://stripe.com/careers and https://www.shopify.com/jobs
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 2
        company_names = [c.name for c in companies]
        assert "Stripe" in company_names
        assert "Shopify" in company_names

    def test_extract_generic_filters_short_names(self):
        """Test generic extraction filters short domain names"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "test@example.com"
        msg["Subject"] = "Jobs"

        body = """
https://ab.com/careers
https://validcompany.com/jobs
"""
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        # Should only extract validcompany (ab is too short)
        assert len(companies) == 1
        assert companies[0].name == "Validcompany"


class TestArtemisExtraction:
    """Test Artemis email extraction"""

    def test_extract_from_artemis_uses_generic(self):
        """Test Artemis extraction delegates to generic extraction"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "artemis@example.com"
        msg["Subject"] = "Artemis Jobs"

        body = "https://company.com/careers"
        msg.set_payload(body.encode("utf-8"))

        companies = extractor.extract_companies(msg)

        assert len(companies) == 1
        assert companies[0].name == "Company"


class TestExtractCompaniesRouting:
    """Test extract_companies routes to correct parser"""

    def test_routes_to_linkedin(self):
        """Test routing to LinkedIn parser"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@linkedin.com"
        msg["Subject"] = "Jobs"
        msg.set_payload(b"Test")

        # Should not raise, routes to LinkedIn
        companies = extractor.extract_companies(msg)
        assert isinstance(companies, list)

    def test_routes_to_supra(self):
        """Test routing to Supra parser"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "hello@supra.com"
        msg["Subject"] = "Product Leadership Jobs"
        msg.set_payload(b"Test")

        companies = extractor.extract_companies(msg)
        assert isinstance(companies, list)

    def test_routes_to_builtin(self):
        """Test routing to Built In parser"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "support@builtin.com"
        msg["Subject"] = "Jobs"
        msg.set_payload(b"Test")

        companies = extractor.extract_companies(msg)
        assert isinstance(companies, list)

    def test_routes_to_f6s(self):
        """Test routing to F6S parser"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "jobs@f6s.com"
        msg["Subject"] = "Jobs"
        msg.set_payload(b"Test")

        companies = extractor.extract_companies(msg)
        assert isinstance(companies, list)

    def test_routes_to_generic(self):
        """Test routing to generic parser for unknown source"""
        extractor = EmailCompanyExtractor()

        msg = Message()
        msg["From"] = "unknown@example.com"
        msg["Subject"] = "Jobs"
        msg.set_payload(b"Test")

        companies = extractor.extract_companies(msg)
        assert isinstance(companies, list)
