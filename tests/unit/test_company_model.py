"""
Tests for Company data model

Tests the unified Company model used across all V3 workflow sources.
"""

from datetime import datetime

from src.models.company import Company


class TestCompanyInit:
    """Test Company initialization"""

    def test_init_with_all_fields(self):
        """Test creating Company with all fields"""
        company = Company(
            name="TestCo",
            careers_url="https://testco.com/careers",
            source="email",
            source_details="LinkedIn job alert",
            discovered_at="2025-01-01T00:00:00",
            notes="Some notes",
        )

        assert company.name == "TestCo"
        assert company.careers_url == "https://testco.com/careers"
        assert company.source == "email"
        assert company.source_details == "LinkedIn job alert"
        assert company.discovered_at == "2025-01-01T00:00:00"
        assert company.notes == "Some notes"

    def test_init_with_required_fields_only(self):
        """Test creating Company with only required fields"""
        company = Company(name="MinimalCo", careers_url="https://minimalco.com/jobs", source="csv")

        assert company.name == "MinimalCo"
        assert company.careers_url == "https://minimalco.com/jobs"
        assert company.source == "csv"
        assert company.source_details == ""
        assert company.notes == ""
        # discovered_at should be auto-generated
        assert company.discovered_at != ""

    def test_post_init_sets_discovered_at(self):
        """Test that __post_init__ sets discovered_at if not provided"""
        company = Company(
            name="AutoTimeCo", careers_url="https://example.com/careers", source="email"
        )

        # Should have an ISO timestamp
        assert company.discovered_at != ""
        # Should parse as valid datetime
        datetime.fromisoformat(company.discovered_at)

    def test_post_init_preserves_custom_discovered_at(self):
        """Test that custom discovered_at is not overwritten"""
        custom_time = "2024-12-25T10:30:00"
        company = Company(
            name="CustomTimeCo",
            careers_url="https://example.com/careers",
            source="browser_extension",
            discovered_at=custom_time,
        )

        assert company.discovered_at == custom_time


class TestCompanyToDict:
    """Test Company.to_dict() method"""

    def test_to_dict_with_all_fields(self):
        """Test converting Company to dict with all fields"""
        company = Company(
            name="DictCo",
            careers_url="https://dictco.com/careers",
            source="csv",
            source_details="job_sources.csv row 42",
            discovered_at="2025-01-15T14:30:00",
            notes="Priority company",
        )

        result = company.to_dict()

        assert result == {
            "name": "DictCo",
            "careers_url": "https://dictco.com/careers",
            "source": "csv",
            "source_details": "job_sources.csv row 42",
            "discovered_at": "2025-01-15T14:30:00",
            "notes": "Priority company",
        }

    def test_to_dict_with_minimal_fields(self):
        """Test converting Company to dict with minimal fields"""
        company = Company(name="MinCo", careers_url="https://minco.com/jobs", source="email")

        result = company.to_dict()

        assert "name" in result
        assert "careers_url" in result
        assert "source" in result
        assert "source_details" in result
        assert "discovered_at" in result
        assert "notes" in result

        assert result["name"] == "MinCo"
        assert result["careers_url"] == "https://minco.com/jobs"
        assert result["source"] == "email"


class TestCompanySources:
    """Test different company sources"""

    def test_email_source(self):
        """Test company from email source"""
        company = Company(
            name="EmailCo",
            careers_url="https://emailco.com/careers",
            source="email",
            source_details="Supra newsletter",
        )

        assert company.source == "email"
        assert "Supra" in company.source_details

    def test_csv_source(self):
        """Test company from CSV source"""
        company = Company(
            name="CSVCo",
            careers_url="https://csvco.com/jobs",
            source="csv",
            source_details="job_sources.csv",
        )

        assert company.source == "csv"
        assert "csv" in company.source_details

    def test_browser_extension_source(self):
        """Test company from browser extension source"""
        company = Company(
            name="BrowserCo",
            careers_url="https://browserco.com/careers",
            source="browser_extension",
            source_details="Manual add via extension",
        )

        assert company.source == "browser_extension"


class TestCompanyURLFormats:
    """Test various career URL formats"""

    def test_greenhouse_url(self):
        """Test Greenhouse ATS URL"""
        company = Company(
            name="GreenhouseCo",
            careers_url="https://boards.greenhouse.io/greenhouseco",
            source="email",
        )

        assert "greenhouse.io" in company.careers_url

    def test_lever_url(self):
        """Test Lever ATS URL"""
        company = Company(
            name="LeverCo",
            careers_url="https://jobs.lever.co/leverco",
            source="email",
        )

        assert "lever.co" in company.careers_url

    def test_company_domain_url(self):
        """Test company's own careers page"""
        company = Company(
            name="OwnDomainCo",
            careers_url="https://owndomain.com/careers",
            source="csv",
        )

        assert "owndomain.com" in company.careers_url

    def test_google_search_fallback_url(self):
        """Test Google search fallback URL"""
        company = Company(
            name="UnknownCo",
            careers_url="https://www.google.com/search?q=UnknownCo+careers",
            source="email",
        )

        assert "google.com/search" in company.careers_url


class TestCompanyEdgeCases:
    """Test edge cases and special characters"""

    def test_company_name_with_special_characters(self):
        """Test company names with special characters"""
        companies = [
            Company(
                name="O'Reilly Media",
                careers_url="https://oreilly.com/careers",
                source="email",
            ),
            Company(
                name="AT&T",
                careers_url="https://att.com/careers",
                source="csv",
            ),
            Company(
                name="Procter & Gamble",
                careers_url="https://pg.com/careers",
                source="email",
            ),
        ]

        for company in companies:
            assert company.name != ""
            assert company.careers_url != ""

    def test_url_with_query_params(self):
        """Test URLs with query parameters"""
        company = Company(
            name="ParamCo",
            careers_url="https://paramco.com/careers?dept=engineering&level=senior",
            source="csv",
        )

        assert "?" in company.careers_url
        assert "dept=" in company.careers_url

    def test_url_with_fragment(self):
        """Test URLs with fragments"""
        company = Company(
            name="FragmentCo",
            careers_url="https://fragmentco.com/careers#engineering",
            source="browser_extension",
        )

        assert "#" in company.careers_url

    def test_empty_notes(self):
        """Test that notes defaults to empty string"""
        company = Company(name="NoNotesCo", careers_url="https://example.com", source="email")

        assert company.notes == ""

    def test_multiline_notes(self):
        """Test notes with multiple lines"""
        notes = """Priority: High
Contact: john@example.com
Next step: Check in Q2"""

        company = Company(
            name="MultiNoteCo",
            careers_url="https://example.com",
            source="csv",
            notes=notes,
        )

        assert "\n" in company.notes
        assert "Priority" in company.notes
