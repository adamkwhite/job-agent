"""Tests for CareerPageFinder website guessing logic."""

from unittest.mock import MagicMock

import pytest

from enrichment.career_page_finder import CareerPageFinder


@pytest.fixture
def finder():
    """Create a CareerPageFinder with network calls disabled."""
    f = CareerPageFinder()
    # Disable network validation by default — individual tests can override
    f._validate_url = MagicMock(return_value=False)
    return f


class TestParentheticalDomain:
    """Strategy 1: Extract domain from parentheses."""

    def test_parenthetical_com_domain(self, finder):
        result = finder._guess_company_website("Clio (clio.com)")
        assert result == "https://clio.com"

    def test_parenthetical_ai_domain(self, finder):
        result = finder._guess_company_website("World Labs (worldlabs.ai)")
        assert result == "https://worldlabs.ai"

    def test_parenthetical_io_domain(self, finder):
        result = finder._guess_company_website("Merge Labs (merge.io)")
        assert result == "https://merge.io"


class TestDirectDomainName:
    """Strategy 2: Name itself is a domain."""

    def test_direct_domain_name(self, finder):
        result = finder._guess_company_website("Provision.com")
        assert result == "https://provision.com"

    def test_direct_io_domain(self, finder):
        result = finder._guess_company_website("example.io")
        assert result == "https://example.io"


class TestCleanNameConstruction:
    """Strategy 3: Clean name + .com fallback."""

    def test_multi_word_company(self, finder):
        result = finder._guess_company_website("Braveheart Bio")
        assert result == "https://braveheartbio.com"

    def test_strips_formerly(self, finder):
        result = finder._guess_company_website("Anterior (formerly Co:Helm)")
        assert result == "https://anterior.com"

    def test_strips_inc_suffix(self, finder):
        result = finder._guess_company_website("Taalas Inc")
        assert result == "https://taalas.com"

    def test_strips_llc_suffix(self, finder):
        result = finder._guess_company_website("Acme LLC")
        assert result == "https://acme.com"

    def test_strips_labs_suffix(self, finder):
        result = finder._guess_company_website("Quantum Labs")
        assert result == "https://quantum.com"


class TestValidateUrl:
    """Test _validate_url HEAD request logic."""

    def test_validate_url_success(self):
        finder = CareerPageFinder()
        mock_response = MagicMock()
        mock_response.status_code = 200
        finder.session.head = MagicMock(return_value=mock_response)

        assert finder._validate_url("https://example.com") is True
        finder.session.head.assert_called_once_with(
            "https://example.com", timeout=5, allow_redirects=True
        )

    def test_validate_url_not_found(self):
        finder = CareerPageFinder()
        mock_response = MagicMock()
        mock_response.status_code = 404
        finder.session.head = MagicMock(return_value=mock_response)

        assert finder._validate_url("https://nonexistent.com") is False

    def test_validate_url_network_error(self):
        finder = CareerPageFinder()
        finder.session.head = MagicMock(side_effect=ConnectionError("timeout"))

        assert finder._validate_url("https://down.com") is False


class TestTldProbing:
    """Strategy 4: Try alternative TLDs when .com fails."""

    def test_tld_probing_finds_io(self):
        finder = CareerPageFinder()

        # .io succeeds, others fail
        def mock_validate(url):
            return url.endswith(".io")

        finder._validate_url = MagicMock(side_effect=mock_validate)

        result = finder._guess_with_tld_probing("mycompany")
        assert result == "https://mycompany.io"

    def test_tld_probing_finds_ai(self):
        finder = CareerPageFinder()

        def mock_validate(url):
            return url.endswith(".ai")

        finder._validate_url = MagicMock(side_effect=mock_validate)

        result = finder._guess_with_tld_probing("mycompany")
        assert result == "https://mycompany.ai"

    def test_tld_probing_none_found(self):
        finder = CareerPageFinder()
        finder._validate_url = MagicMock(return_value=False)

        result = finder._guess_with_tld_probing("mycompany")
        assert result is None

    def test_full_flow_with_tld_probing(self):
        """Integration: .com fails validation, .io succeeds via probing."""
        finder = CareerPageFinder()

        def mock_validate(url):
            return url == "https://mergelabs.io"

        finder._validate_url = MagicMock(side_effect=mock_validate)

        # "Merge" without parenthetical — falls through to clean name + probing
        result = finder._guess_company_website("MergeLabs")
        assert result == "https://mergelabs.io"
