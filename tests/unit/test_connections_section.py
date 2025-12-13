"""Tests for connections section in email digest."""

from dataclasses import dataclass

import pytest

from src.send_profile_digest import _generate_connections_section


@dataclass
class MockConnection:
    """Mock connection for testing."""

    first_name: str
    last_name: str
    email: str
    company: str
    position: str
    connected_on: str
    url: str = ""

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"


class MockConnectionsManager:
    """Mock connections manager for testing."""

    def __init__(self, connections_data: dict[str, list[MockConnection]]):
        """Initialize with test data."""
        self.connections_data = connections_data
        self.connections_exist = len(connections_data) > 0

    def get_connection_summary(self, company: str) -> dict:
        """Get connection summary for a company."""
        connections = self.connections_data.get(company, [])
        return {"count": len(connections), "connections": connections}


@pytest.fixture
def sample_jobs():
    """Sample jobs for testing."""
    return [
        {
            "title": "VP Engineering",
            "company": "Acme Corp",
            "location": "Remote",
            "link": "https://example.com/job/1",
            "fit_score": 95,
            "fit_grade": "A",
        },
        {
            "title": "Director of Product",
            "company": "TechCo",
            "location": "San Francisco, CA",
            "link": "https://example.com/job/2",
            "fit_score": 88,
            "fit_grade": "B",
        },
        {
            "title": "Head of Engineering",
            "company": "StartupXYZ",
            "location": "New York, NY",
            "link": "https://example.com/job/3",
            "fit_score": 82,
            "fit_grade": "B",
        },
    ]


class TestGenerateConnectionsSection:
    """Test connections section generation."""

    def test_no_connections_manager(self, sample_jobs):
        """Test with no connections manager."""
        result = _generate_connections_section(sample_jobs, None)
        assert result == ""

    def test_connections_manager_no_connections(self, sample_jobs):
        """Test with connections manager but no connections."""
        manager = MockConnectionsManager({})
        result = _generate_connections_section(sample_jobs, manager)
        assert result == ""

    def test_single_company_single_connection(self, sample_jobs):
        """Test with one company having one connection."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        assert result != ""
        assert "🤝 Your Connections at These Companies" in result
        assert "Acme Corp" in result
        assert "(1 connection)" in result
        assert "John Doe" in result
        assert "Engineering Manager" in result
        assert 'href="https://linkedin.com/in/johndoe"' in result

    def test_single_company_multiple_connections(self, sample_jobs):
        """Test with one company having multiple connections."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                ),
                MockConnection(
                    first_name="Jane",
                    last_name="Smith",
                    email="jane@example.com",
                    company="Acme Corp",
                    position="Product Manager",
                    connected_on="2023-02-01",
                    url="https://linkedin.com/in/janesmith",
                ),
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        assert result != ""
        assert "Acme Corp" in result
        assert "(2 connections)" in result
        assert "John Doe" in result
        assert "Jane Smith" in result
        assert "Engineering Manager" in result
        assert "Product Manager" in result

    def test_multiple_companies_with_connections(self, sample_jobs):
        """Test with multiple companies having connections."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                )
            ],
            "TechCo": [
                MockConnection(
                    first_name="Jane",
                    last_name="Smith",
                    email="jane@example.com",
                    company="TechCo",
                    position="Product Manager",
                    connected_on="2023-02-01",
                    url="https://linkedin.com/in/janesmith",
                )
            ],
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        assert result != ""
        assert "Acme Corp" in result
        assert "TechCo" in result
        assert "John Doe" in result
        assert "Jane Smith" in result

    def test_connection_without_url(self, sample_jobs):
        """Test connection without LinkedIn URL."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="",  # No URL
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        assert result != ""
        assert "John Doe" in result
        assert "Engineering Manager" in result
        # Should not have a link
        assert 'href=""' not in result
        # Should just have the name in a span
        assert "<span" in result

    def test_sorted_by_connection_count(self, sample_jobs):
        """Test that companies are sorted by connection count (descending)."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                )
            ],
            "TechCo": [
                MockConnection(
                    first_name="Jane",
                    last_name="Smith",
                    email="jane@example.com",
                    company="TechCo",
                    position="Product Manager",
                    connected_on="2023-02-01",
                ),
                MockConnection(
                    first_name="Bob",
                    last_name="Johnson",
                    email="bob@example.com",
                    company="TechCo",
                    position="Software Engineer",
                    connected_on="2023-03-01",
                ),
                MockConnection(
                    first_name="Alice",
                    last_name="Williams",
                    email="alice@example.com",
                    company="TechCo",
                    position="Designer",
                    connected_on="2023-04-01",
                ),
            ],
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        # TechCo (3 connections) should appear before Acme Corp (1 connection)
        techco_index = result.find("TechCo")
        acme_index = result.find("Acme Corp")
        assert techco_index < acme_index

    def test_duplicate_companies_handled(self, sample_jobs):
        """Test that duplicate companies in jobs are handled correctly."""
        # Add duplicate company
        jobs_with_duplicate = sample_jobs + [
            {
                "title": "Senior Engineer",
                "company": "Acme Corp",  # Duplicate
                "location": "Boston, MA",
                "link": "https://example.com/job/4",
                "fit_score": 75,
                "fit_grade": "C",
            }
        ]

        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(jobs_with_duplicate, manager)

        # Should only show Acme Corp once
        assert result.count("Acme Corp") == 1

    def test_exception_handling(self, sample_jobs):
        """Test that exceptions in get_connection_summary are handled."""

        class BrokenConnectionsManager:
            """Mock manager that raises exceptions."""

            connections_exist = True

            def get_connection_summary(self, company: str):
                """Always raise an exception."""
                raise ValueError("Test error")

        manager = BrokenConnectionsManager()
        result = _generate_connections_section(sample_jobs, manager)

        # Should return empty string when all lookups fail
        assert result == ""

    def test_html_structure(self, sample_jobs):
        """Test that generated HTML has correct structure."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        # Check for expected HTML elements
        assert '<div style="margin-top: 40px' in result
        assert "<h2" in result
        assert "<h3" in result
        assert "<ul" in result
        assert "<li" in result
        assert "</div>" in result

    def test_styling_present(self, sample_jobs):
        """Test that proper CSS styling is applied."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        # Check for key styling elements
        assert 'style="' in result
        assert "color:" in result
        assert "margin" in result
        assert "padding" in result

    def test_linkedin_link_styling(self, sample_jobs):
        """Test that LinkedIn links have proper styling."""
        connections_data = {
            "Acme Corp": [
                MockConnection(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    company="Acme Corp",
                    position="Engineering Manager",
                    connected_on="2023-01-01",
                    url="https://linkedin.com/in/johndoe",
                )
            ]
        }
        manager = MockConnectionsManager(connections_data)
        result = _generate_connections_section(sample_jobs, manager)

        # LinkedIn links should have specific color
        assert "color: #0077b5" in result  # LinkedIn blue
        assert "text-decoration: none" in result
        assert 'target="_blank"' in result
