"""
Unit tests for company auto-discovery with career URL extraction

Tests the integration of CareerURLParser into processor_v2's company discovery flow.
Verifies that job posting URLs are parsed to extract career page URLs when companies
are auto-discovered from email processing.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def mock_company_service():
    """Create a mock CompanyService"""
    mock_service = MagicMock()
    mock_service.company_exists.return_value = False
    mock_service.add_discovered_company.return_value = {"success": True}
    return mock_service


@pytest.fixture
def processor_method(mock_company_service):
    """
    Create a standalone version of _check_and_add_company method for testing.

    This avoids the complexity of mocking all of JobProcessorV2's dependencies
    by testing the method in isolation.
    """
    from utils.career_url_parser import CareerURLParser

    def _check_and_add_company(
        company_name: str, source: str = "email", job_link: str | None = None
    ) -> None:
        """Standalone version of the _check_and_add_company method"""
        if not company_name or company_name == "Unknown Company":
            return

        if mock_company_service.company_exists(company_name):
            return

        careers_url = "https://placeholder.com/careers"
        url_note = ""

        if job_link and job_link.strip():
            parser = CareerURLParser()
            extracted_url = parser.parse(job_link)

            if extracted_url:
                careers_url = extracted_url
                if extracted_url.endswith("/jobs") and extracted_url.count("/") == 3:
                    url_note = " (generic fallback - verify)"
            else:
                url_note = " (URL extraction failed)"
                print(f"  ⚠ Could not extract careers URL from: {job_link}")

        result = mock_company_service.add_discovered_company(
            name=company_name, source=f"{source}_auto_discovery", careers_url=careers_url
        )

        if result["success"]:
            print(f"  🆕 Auto-discovered: {company_name}{url_note}")
            print(f"      Careers URL: {careers_url}")

    return _check_and_add_company


def test_discover_company_with_workday_url(processor_method, mock_company_service):
    """Test auto-discovery with Workday job posting URL"""
    # Arrange
    job_link = "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/VP-Engineering/12345"

    # Act
    processor_method(company_name="Boston Dynamics", source="email", job_link=job_link)

    # Assert
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["name"] == "Boston Dynamics"
    assert call_args.kwargs["source"] == "email_auto_discovery"
    assert (
        call_args.kwargs["careers_url"]
        == "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics"
    )


def test_discover_company_with_greenhouse_url(processor_method, mock_company_service):
    """Test auto-discovery with Greenhouse job posting URL"""
    # Arrange
    job_link = "https://job-boards.greenhouse.io/figureai/jobs/4123456"

    # Act
    processor_method(company_name="Figure AI", source="email", job_link=job_link)

    # Assert
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://job-boards.greenhouse.io/figureai"


def test_discover_company_with_lever_url(processor_method, mock_company_service):
    """Test auto-discovery with Lever job posting URL"""
    # Arrange
    job_link = "https://jobs.lever.co/kuka/abc-123-xyz-director-engineering"

    # Act
    processor_method(company_name="KUKA Robotics", source="email", job_link=job_link)

    # Assert
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://jobs.lever.co/kuka"


def test_discover_company_with_generic_fallback(processor_method, mock_company_service, capsys):
    """Test auto-discovery with generic fallback URL"""
    # Arrange
    job_link = "https://example-company.com/careers/senior-engineer"

    # Act
    processor_method(company_name="Example Company", source="email", job_link=job_link)

    # Assert
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args

    # Generic fallback should return base URL + /jobs
    careers_url = call_args.kwargs["careers_url"]
    assert careers_url == "https://example-company.com/jobs"

    # Should print warning about generic fallback
    captured = capsys.readouterr()
    assert "🆕 Auto-discovered: Example Company (generic fallback - verify)" in captured.out


def test_discover_company_with_unparseable_url(processor_method, mock_company_service, capsys):
    """Test auto-discovery with unparseable URL falls back to placeholder"""
    # Arrange
    job_link = "invalid-url-format"

    # Act
    processor_method(company_name="Test Company", source="email", job_link=job_link)

    # Assert
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://placeholder.com/careers"

    # Should print warning about extraction failure
    captured = capsys.readouterr()
    assert "⚠ Could not extract careers URL from: invalid-url-format" in captured.out
    assert "🆕 Auto-discovered: Test Company (URL extraction failed)" in captured.out


def test_discover_company_without_job_link(processor_method, mock_company_service):
    """Test auto-discovery without job link (backward compatibility)"""
    # Act - no job_link parameter
    processor_method(company_name="Legacy Company", source="email")

    # Assert - should fall back to placeholder
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://placeholder.com/careers"


def test_discover_company_already_exists(processor_method, mock_company_service):
    """Test auto-discovery skips if company already exists"""
    # Arrange
    mock_company_service.company_exists.return_value = True  # Company exists

    # Act
    processor_method(
        company_name="Existing Company",
        source="email",
        job_link="https://example.com/jobs/123",
    )

    # Assert - should not call add_discovered_company
    mock_company_service.add_discovered_company.assert_not_called()


def test_discover_company_empty_link(processor_method, mock_company_service):
    """Test auto-discovery with empty string job link"""
    # Act - empty string job_link
    processor_method(company_name="Test Company", source="email", job_link="")

    # Assert - should fall back to placeholder
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://placeholder.com/careers"


def test_discover_company_whitespace_link(processor_method, mock_company_service):
    """Test auto-discovery with whitespace-only job link"""
    # Act - whitespace-only job_link
    processor_method(company_name="Test Company", source="email", job_link="   \t\n  ")

    # Assert - should fall back to placeholder
    mock_company_service.add_discovered_company.assert_called_once()
    call_args = mock_company_service.add_discovered_company.call_args
    assert call_args.kwargs["careers_url"] == "https://placeholder.com/careers"


def test_discover_company_unknown_company_name(processor_method, mock_company_service):
    """Test auto-discovery skips 'Unknown Company' name"""
    # Act
    processor_method(
        company_name="Unknown Company",
        source="email",
        job_link="https://example.com/jobs/123",
    )

    # Assert - should not check or add company
    mock_company_service.company_exists.assert_not_called()
    mock_company_service.add_discovered_company.assert_not_called()


def test_discover_company_empty_name(processor_method, mock_company_service):
    """Test auto-discovery skips empty company name"""
    # Act
    processor_method(company_name="", source="email", job_link="https://example.com/jobs/123")

    # Assert - should not check or add company
    mock_company_service.company_exists.assert_not_called()
    mock_company_service.add_discovered_company.assert_not_called()
