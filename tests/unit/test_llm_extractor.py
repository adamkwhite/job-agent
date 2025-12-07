"""
Unit tests for LLM job extraction using LangChain
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.extractors.llm_extractor import LLMExtractor
from src.models import OpportunityData


@pytest.fixture
def mock_config():
    """Mock LLM extraction configuration"""
    return {
        "enabled": True,
        "provider": "langchain",
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
    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_init_loads_config(
        self, mock_chat_openai, mock_budget_service, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test that extractor loads configuration file"""
        extractor = LLMExtractor(config_path=temp_config_file)

        assert extractor.config["enabled"] is True
        assert extractor.config["provider"] == "langchain"
        assert extractor.config["timeout_seconds"] == 30
        # Verify budget service was initialized
        mock_budget_service.assert_called_once_with(
            monthly_limit=5.0,
            alert_threshold=0.8,
        )
        # Verify ChatOpenAI was initialized
        mock_chat_openai.assert_called_once()

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

    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_init_creates_llm_client(
        self, mock_chat_openai, mock_budget_service, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test that LLM client is created with correct configuration"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Verify ChatOpenAI was called with correct parameters
        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "test-api-key-12345"
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["model"] == "anthropic/claude-3.5-sonnet"
        assert call_kwargs["temperature"] == 0.1
        assert hasattr(extractor, "llm")


class TestBudgetAvailable:
    """Test budget checking"""

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_when_not_paused(
        self,
        mock_budget_service_class,  # noqa: ARG002
        mock_chat_openai,  # noqa: ARG002
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

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_uses_service(
        self,
        mock_budget_service_class,
        mock_chat_openai,  # noqa: ARG002
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

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_budget_available_when_exceeded(
        self,
        mock_budget_service_class,
        mock_chat_openai,  # noqa: ARG002
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

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_extract_jobs_disabled_config(self, mock_chat_openai, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that extraction returns empty list when disabled"""
        # Disable extraction in config
        config = json.loads(Path(temp_config_file).read_text())
        config["enabled"] = False
        Path(temp_config_file).write_text(json.dumps(config))

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test markdown", "Test Company")

        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_extract_jobs_empty_markdown(self, mock_chat_openai, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test that empty markdown returns empty list"""
        extractor = LLMExtractor(config_path=temp_config_file)

        jobs = extractor.extract_jobs("", "Test Company")
        assert jobs == []

        jobs = extractor.extract_jobs("   ", "Test Company")
        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_success(
        self,
        mock_budget_service_class,
        mock_chat_openai_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test successful job extraction"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock LLM response with usage metadata
        mock_response = Mock()
        mock_response.content = json.dumps(
            [
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
        )
        mock_response.usage_metadata = {
            "input_tokens": 100,
            "output_tokens": 50,
        }

        # Mock ChatOpenAI instance
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_class.return_value = mock_llm

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test Career Page", "Test Company")

        assert len(jobs) == 2
        assert all(isinstance(job, OpportunityData) for job in jobs)
        assert jobs[0].title == "VP of Engineering"
        assert jobs[0].location == "Remote"
        assert jobs[0].company == "Test Company"
        assert jobs[0].source == "llm_extraction"
        assert jobs[1].title == "Director of Product"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_timeout(
        self,
        mock_budget_service_class,
        mock_chat_openai_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that timeout is detected and handled"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock successful LLM response but simulate slow invoke
        mock_response = Mock()
        mock_response.content = json.dumps(
            [
                {
                    "title": "VP of Engineering",
                    "location": "Remote",
                    "link": "https://example.com/jobs/vp-eng",
                }
            ]
        )
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}

        mock_llm = Mock()

        # Simulate slow invoke by adding a sleep
        def slow_invoke(*args, **kwargs):  # noqa: ARG001
            import time

            time.sleep(0.05)  # Sleep for 50ms
            return mock_response

        mock_llm.invoke.side_effect = slow_invoke
        mock_chat_openai_class.return_value = mock_llm

        # Create extractor with very short timeout (1ms)
        extractor = LLMExtractor(config_path=temp_config_file)
        extractor.timeout_seconds = 0.001  # 1ms timeout - will definitely timeout

        # Should raise TimeoutError
        with pytest.raises(TimeoutError):
            extractor.extract_jobs("# Test Career Page", "Test Company")

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_llm_exception(
        self,
        mock_budget_service_class,
        mock_chat_openai_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that LLM exceptions are handled gracefully"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock LLM to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM API error")
        mock_chat_openai_class.return_value = mock_llm

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test Career Page", "Test Company")

        # Should return empty list on error
        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_skipped_when_budget_exceeded(
        self,
        mock_budget_service_class,
        mock_chat_openai_class,  # noqa: ARG002
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that extraction is skipped when budget exceeded"""
        # Mock budget service to return False (budget exceeded)
        mock_service = Mock()
        mock_service.check_budget_available.return_value = False
        mock_budget_service_class.return_value = mock_service

        extractor = LLMExtractor(config_path=temp_config_file)
        jobs = extractor.extract_jobs("# Test Career Page", "Test Company")

        # Should return empty list when budget exceeded
        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    def test_extract_jobs_records_api_call(
        self,
        mock_budget_service_class,
        mock_chat_openai_class,
        temp_config_file,
        mock_env_var,  # noqa: ARG002
    ):
        """Test that API calls are recorded with token usage"""
        # Mock budget service
        mock_service = Mock()
        mock_service.check_budget_available.return_value = True
        mock_budget_service_class.return_value = mock_service

        # Mock LLM response with usage metadata
        mock_response = Mock()
        mock_response.content = json.dumps(
            [{"title": "VP Eng", "location": "Remote", "link": "https://example.com/job"}]
        )
        mock_response.usage_metadata = {
            "input_tokens": 500,
            "output_tokens": 100,
        }

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_class.return_value = mock_llm

        extractor = LLMExtractor(config_path=temp_config_file)
        extractor.extract_jobs("# Test Career Page", "Test Company")

        # Verify budget service recorded the API call
        mock_service.record_api_call.assert_called_once()
        call_kwargs = mock_service.record_api_call.call_args.kwargs
        assert call_kwargs["tokens_in"] == 500
        assert call_kwargs["tokens_out"] == 100
        assert "company_name" in call_kwargs


class TestParseLLMResponse:
    """Test LLM response parsing"""

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_with_result_key(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test parsing response with 'result' key"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string (as LangChain response.content would)
        response_content = json.dumps(
            [{"title": "VP Eng", "location": "Remote", "link": "https://example.com/job"}]
        )

        jobs = extractor._parse_llm_response(response_content, "Test Company")
        assert len(jobs) == 1
        assert jobs[0].title == "VP Eng"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_with_data_key(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test parsing response with 'data' key"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string (as LangChain response.content would)
        response_content = json.dumps(
            [{"title": "Director Product", "location": "SF", "link": "https://example.com/job"}]
        )

        jobs = extractor._parse_llm_response(response_content, "Test Company")
        assert len(jobs) == 1
        assert jobs[0].title == "Director Product"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_direct_array(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test parsing response that is a direct array"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string of array (as LangChain response.content would)
        response_content = json.dumps(
            [{"title": "Head of Eng", "location": "NYC", "link": "https://example.com/job"}]
        )

        jobs = extractor._parse_llm_response(response_content, "Test Company")
        assert len(jobs) == 1
        assert jobs[0].title == "Head of Eng"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_json_string(self, mock_chat_openai, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response that is a JSON string"""
        extractor = LLMExtractor(config_path=temp_config_file)

        response_data = json.dumps(
            [{"title": "Senior Staff Eng", "location": "Remote", "link": "https://example.com/job"}]
        )

        jobs = extractor._parse_llm_response(response_data, "Test Company")
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Staff Eng"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_empty_result(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test parsing empty response"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string of empty array
        jobs = extractor._parse_llm_response(json.dumps([]), "Test Company")
        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_invalid_item(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test that items missing required fields are skipped"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string with mixed valid/invalid items
        response_content = json.dumps(
            [
                {"title": "VP Eng"},  # Missing link
                {
                    "title": "Director",
                    "location": "Remote",
                    "link": "https://example.com/job",
                },  # Valid
                {"location": "NYC", "link": "https://example.com/job2"},  # Missing title
            ]
        )

        jobs = extractor._parse_llm_response(response_content, "Test Company")
        assert len(jobs) == 1  # Only the valid job
        assert jobs[0].title == "Director"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_no_data(self, mock_chat_openai, temp_config_file, mock_env_var):  # noqa: ARG002
        """Test parsing response that is not a valid array"""
        extractor = LLMExtractor(config_path=temp_config_file)

        # Pass JSON string of empty object
        jobs = extractor._parse_llm_response(json.dumps({}), "Test Company")
        assert jobs == []

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    def test_parse_llm_response_invalid_json_string(
        self, mock_chat_openai, temp_config_file, mock_env_var
    ):  # noqa: ARG002
        """Test parsing invalid JSON string"""
        extractor = LLMExtractor(config_path=temp_config_file)

        jobs = extractor._parse_llm_response("not valid json", "Test Company")
        assert jobs == []
