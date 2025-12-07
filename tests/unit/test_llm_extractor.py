"""
Unit tests for LLM job extraction
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock scrapegraphai before importing LLMExtractor
sys.modules["scrapegraphai"] = MagicMock()
sys.modules["scrapegraphai.graphs"] = MagicMock()

from src.extractors.llm_extractor import LLMExtractor  # noqa: E402
from src.models import OpportunityData  # noqa: E402


@pytest.fixture
def mock_config():
    """Mock LLM extraction configuration"""
    return {
        "enabled": True,
        "provider": "scrapegraphai",
        "llm_config": {
            "llm": {
                "api_key_env": "OPENROUTER_API_KEY",
                "model": "anthropic/claude-3.5-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.1,
            }
        },
        "budget": {"monthly_limit_usd": 5.0, "pause_when_exceeded": True},
        "timeout_seconds": 30,
        "extraction_prompt": "Extract jobs from {company_name}: {markdown_content}",
        "leadership_levels": ["VP", "Director", "Senior Manager"],
    }


@pytest.fixture
def temp_config_file(mock_config):
    """Create temporary config file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mock_config, f)
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink(missing_ok=True)


@pytest.fixture
def mock_env_var(monkeypatch):
    """Mock OPENROUTER_API_KEY environment variable"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key-12345")


@pytest.fixture
def temp_logs_dir():
    """Create temporary logs directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestLLMExtractorInit:
    """Test LLMExtractor initialization"""

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_init_loads_config(self, mock_budget_service, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that extractor loads configuration file"""
        extractor = LLMExtractor(config_path=temp_config_file)

        assert extractor.config["enabled"] is True
        assert extractor.config["provider"] == "scrapegraphai"
        assert extractor.config["timeout_seconds"] == 30
        # Verify budget service was initialized
        mock_budget_service.assert_called_once_with(
            monthly_limit=5.0,
            alert_threshold=0.8,
        )

    def test_init_missing_config_file(self, mock_env_var):  # noqa: ARG002
        """Test that missing config file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            LLMExtractor(config_path="nonexistent.json")

    def test_init_missing_api_key(self, temp_config_file, monkeypatch):
        """Test that missing API key raises ValueError"""
        # Ensure OPENROUTER_API_KEY is not set
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Missing OPENROUTER_API_KEY"):
            LLMExtractor(config_path=temp_config_file)

    def test_init_creates_graph_config(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that graph config is created with correct structure"""
        extractor = LLMExtractor(config_path=temp_config_file)

        assert "llm" in extractor.graph_config
        assert extractor.graph_config["llm"]["api_key"] == "test-api-key-12345"
        assert extractor.graph_config["llm"]["model"] == "anthropic/claude-3.5-sonnet"
        assert extractor.graph_config["verbose"] is True
        assert extractor.graph_config["headless"] is True


class TestBudgetAvailable:
    """Test budget checking"""

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_when_not_paused(
        self,
        mock_budget_service_class,  # noqa: ARG002
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test budget_available returns True when pause_when_exceeded is False"""
        # Modify config to disable pause
        config = json.loads(Path(temp_config_file).read_text())
        config["budget"]["pause_when_exceeded"] = False
        Path(temp_config_file).write_text(json.dumps(config))

        extractor = LLMExtractor(config_path=temp_config_file)
        assert extractor.budget_available() is True

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_uses_service(
        self,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test budget_available uses budget service"""
        # Mock budget service to return True for check_budget_available
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        extractor = LLMExtractor(config_path=temp_config_file)
        # Should use budget service
        assert extractor.budget_available() is True
        mock_service.check_budget_available.assert_called_once()

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_when_exceeded(
        self,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test budget_available returns False when budget exceeded"""
        # Mock budget service to return False for check_budget_available
        mock_service = Mock()
        mock_service.check_budget_available.return_value = False
        mock_budget_service_class.return_value = mock_service

        extractor = LLMExtractor(config_path=temp_config_file)
        assert extractor.budget_available() is False


class TestExtractJobs:
    """Test job extraction with LLM"""

    def test_extract_jobs_disabled_config(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that extraction returns empty list when disabled"""
        # Disable extraction in config
        config = json.loads(Path(temp_config_file).read_text())
        config["enabled"] = False
        Path(temp_config_file).write_text(json.dumps(config))

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test markdown", "Test Company")

        assert jobs == []

    def test_extract_jobs_empty_markdown(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that empty markdown returns empty list"""
        extractor = LLMExtractor(config_path=temp_config_file)

        jobs = extractor.extract_jobs("", "Test Company")
        assert jobs == []

        jobs = extractor.extract_jobs("   ", "Test Company")
        assert jobs == []

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.SmartScraperGraph")
    def test_extract_jobs_success(
        self,
        mock_smart_scraper_class,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test successful job extraction"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock SmartScraperGraph response
        mock_graph = Mock()
        mock_graph.run.return_value = {
            "result": [
                {
                    "title": "VP of Engineering",
                    "location": "Remote",
                    "link": "https://example.com/jobs/vp-eng",
                },
                {
                    "title": "Director of Product",
                    "location": "San Francisco, CA",
                    "link": "https://example.com/jobs/director-product",
                },
            ]
        }
        mock_smart_scraper_class.return_value = mock_graph

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test Career Page", "Test Company")

        assert len(jobs) == 2
        assert all(isinstance(job, OpportunityData) for job in jobs)
        assert jobs[0].title == "VP of Engineering"
        assert jobs[0].location == "Remote"
        assert jobs[0].company == "Test Company"
        assert jobs[0].source == "llm_extraction"
        assert jobs[1].title == "Director of Product"

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.SmartScraperGraph")
    def test_extract_jobs_timeout(
        self,
        mock_smart_scraper_class,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that timeout is detected and raised"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock SmartScraperGraph.run() to take a long time
        mock_graph = Mock()

        def slow_run():
            import time

            time.sleep(0.1)  # Simulate slow LLM response
            return {"result": []}

        mock_graph.run.side_effect = slow_run
        mock_smart_scraper_class.return_value = mock_graph

        # Create config with very short timeout
        config = json.loads(Path(temp_config_file).read_text())
        config["timeout_seconds"] = 0.05  # 50ms timeout
        Path(temp_config_file).write_text(json.dumps(config))

        extractor = LLMExtractor(config_path=temp_config_file)

        with pytest.raises(TimeoutError, match="LLM extraction timeout"):
            extractor.extract_jobs("# Test markdown", "Test Company")

    @patch("src.extractors.llm_extractor.SmartScraperGraph")
    def test_extract_jobs_llm_exception(
        self,
        mock_smart_scraper_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that LLM exceptions are caught and logged"""
        # Mock SmartScraperGraph to raise exception
        mock_graph = Mock()
        mock_graph.run.side_effect = Exception("LLM API error")
        mock_smart_scraper_class.return_value = mock_graph

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test markdown", "Test Company")

        assert jobs == []  # Should return empty list on error

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_skipped_when_budget_exceeded(
        self,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that extraction is skipped when budget exceeded"""
        # Mock budget service to return False for budget check
        mock_service = Mock()
        mock_service.check_budget_available.return_value = False
        mock_budget_service_class.return_value = mock_service

        extractor = LLMExtractor(config_path=temp_config_file)

        # Try to extract jobs
        jobs = extractor.extract_jobs("# Test markdown", "Test Company")

        # Should return empty list without calling LLM
        assert jobs == []

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.SmartScraperGraph")
    def test_extract_jobs_records_api_call(
        self,
        mock_smart_scraper_class,
        mock_budget_service_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that successful extraction records API call in budget"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock SmartScraperGraph response with usage info
        mock_graph = Mock()
        mock_graph.run.return_value = {
            "result": [
                {
                    "title": "VP of Engineering",
                    "location": "Remote",
                    "link": "https://example.com/jobs/vp-eng",
                }
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 200},
        }
        mock_smart_scraper_class.return_value = mock_graph

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test Career Page", "Test Company")

        # Verify extraction succeeded
        assert len(jobs) == 1

        # Verify budget service recorded the call
        mock_service.record_api_call.assert_called_once()
        call_args = mock_service.record_api_call.call_args
        assert call_args.kwargs["tokens_in"] == 500
        assert call_args.kwargs["tokens_out"] == 200
        assert call_args.kwargs["cost_usd"] > 0  # Should have calculated cost
        assert call_args.kwargs["company_name"] == "Test Company"


class TestParseLLMResponse:
    """Test parsing LLM responses"""

    def test_parse_llm_response_with_result_key(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response with 'result' key"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {
            "result": [
                {
                    "title": "Senior Director of Engineering",
                    "location": "Remote, USA",
                    "link": "https://example.com/job/123",
                }
            ]
        }

        jobs = extractor._parse_llm_response(result, "Test Company")

        assert len(jobs) == 1
        assert jobs[0].title == "Senior Director of Engineering"
        assert jobs[0].location == "Remote, USA"
        assert jobs[0].company == "Test Company"

    def test_parse_llm_response_with_data_key(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response with 'data' key"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {
            "data": [
                {
                    "title": "VP Product",
                    "location": "New York, NY",
                    "link": "https://example.com/jobs/vp-product",
                }
            ]
        }

        jobs = extractor._parse_llm_response(result, "Test Company")

        assert len(jobs) == 1
        assert jobs[0].title == "VP Product"

    def test_parse_llm_response_direct_array(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response that is a direct array"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = [
            {
                "title": "Director of Operations",
                "location": "Boston, MA",
                "link": "https://example.com/jobs/director-ops",
            }
        ]

        jobs = extractor._parse_llm_response(result, "Test Company")

        assert len(jobs) == 1
        assert jobs[0].title == "Director of Operations"

    def test_parse_llm_response_json_string(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response that is a JSON string"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {
            "result": json.dumps(
                [
                    {
                        "title": "CTO",
                        "location": "Remote",
                        "link": "https://example.com/jobs/cto",
                    }
                ]
            )
        }

        jobs = extractor._parse_llm_response(result, "Test Company")

        assert len(jobs) == 1
        assert jobs[0].title == "CTO"

    def test_parse_llm_response_empty_result(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing empty result"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {"result": []}
        jobs = extractor._parse_llm_response(result, "Test Company")

        assert jobs == []

    def test_parse_llm_response_invalid_item(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that invalid job items are skipped"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {
            "result": [
                {
                    "title": "Valid Job",
                    "location": "Remote",
                    "link": "https://example.com/job/1",
                },
                {
                    # Missing required fields - should be skipped
                    "title": None,
                    "location": None,
                    "link": None,
                },
                {
                    "title": "Another Valid Job",
                    "location": "Austin, TX",
                    "link": "https://example.com/job/2",
                },
            ]
        }

        jobs = extractor._parse_llm_response(result, "Test Company")

        # Should parse 2 valid jobs, skip 1 invalid
        assert len(jobs) == 2
        assert jobs[0].title == "Valid Job"
        assert jobs[1].title == "Another Valid Job"

    def test_parse_llm_response_no_data(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response with no job data"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {"some_other_key": "value"}
        jobs = extractor._parse_llm_response(result, "Test Company")

        assert jobs == []

    def test_parse_llm_response_invalid_json_string(self, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response with invalid JSON string"""
        extractor = LLMExtractor(config_path=temp_config_file)

        result = {"result": "not valid json {[}]"}
        jobs = extractor._parse_llm_response(result, "Test Company")

        assert jobs == []
