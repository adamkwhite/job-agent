"""
LLM-based job extraction using LangChain with Claude 3.5 Sonnet via OpenRouter
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.api.llm_budget_service import LLMBudgetService
from src.database import JobDatabase
from src.models import OpportunityData

logger = logging.getLogger(__name__)


class LLMExtractor(object):  # noqa: UP004
    """Extract job postings from markdown using LLM via OpenRouter"""

    # OpenRouter pricing per 1M tokens: {model_id: (input_cost, output_cost)}
    MODEL_PRICING: dict[str, tuple[float, float]] = {
        "anthropic/claude-3.5-sonnet": (3.00, 15.00),
        "anthropic/claude-3-haiku": (0.25, 1.25),
        "anthropic/claude-3.5-haiku": (0.80, 4.00),
        "google/gemini-2.5-flash": (0.30, 2.50),
        "google/gemini-2.0-flash-001": (0.10, 0.40),
        "meta-llama/llama-3.1-8b-instruct": (0.06, 0.06),
        "meta-llama/llama-3.3-70b-instruct": (0.30, 0.40),
        "mistralai/mistral-small-latest": (0.10, 0.30),
        "qwen/qwen-2.5-72b-instruct": (0.30, 0.30),
    }

    def __init__(
        self,
        config_path: str = "config/llm-extraction-settings.json",
        model_override: str | None = None,
    ) -> None:
        """Initialize LLM extractor with configuration

        Args:
            config_path: Path to LLM extraction configuration file
            model_override: Override model from config (e.g. 'google/gemini-2.5-flash')
        """
        self.config = self._load_config(config_path)
        self.database = JobDatabase()

        # Determine model: CLI override > config file
        self.model = model_override or self.config["llm_config"]["llm"]["model"]

        # Initialize budget tracking service
        # 80% threshold for alerts
        self.budget_service = LLMBudgetService(
            monthly_limit=self.config["budget"]["monthly_limit_usd"],
            alert_threshold=0.8,
        )

        # Get OpenRouter API key from environment
        api_key_env = self.config["llm_config"]["llm"]["api_key_env"]
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing {api_key_env} environment variable. Please set your OpenRouter API key."
            )

        # Initialize ChatOpenAI with OpenRouter endpoint
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=self.config["llm_config"]["llm"]["base_url"],
            model=self.model,
            temperature=self.config["llm_config"]["llm"]["temperature"],
        )

        if model_override:
            logger.info("LLM model override active")

        self.timeout_seconds = self.config.get("timeout_seconds", 30)

    @staticmethod
    def _load_config(config_path: str) -> dict[str, Any]:
        """Load LLM extraction configuration from JSON file

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config is invalid JSON
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with path.open() as f:
            return json.load(f)

    def _get_model_pricing(self) -> tuple[float, float]:
        """Get (input_cost, output_cost) per 1M tokens for the current model.

        Falls back to Sonnet pricing if model not in lookup table.
        """
        # Check exact match first, then prefix match
        if self.model in self.MODEL_PRICING:
            return self.MODEL_PRICING[self.model]

        for prefix, pricing in self.MODEL_PRICING.items():
            if self.model.startswith(prefix):
                return pricing

        # Default to Sonnet pricing as conservative estimate
        logger.warning(f"No pricing found for model '{self.model}', using Sonnet defaults")
        return 3.00, 15.00

    def budget_available(self) -> bool:
        """Check if monthly budget has not been exceeded

        Returns:
            True if budget available, False if exceeded
        """
        if not self.config["budget"]["pause_when_exceeded"]:
            return True

        # Check budget via budget service
        return self.budget_service.check_budget_available()

    def _validate_extraction_request(self, markdown: str, company_name: str) -> str | None:
        """Validate preconditions before running LLM extraction.

        Returns:
            Error reason string if extraction should be skipped, None if valid.
        """
        if not self.config["enabled"] or not self.budget_available():
            reason = "disabled in config" if not self.config["enabled"] else "budget limit reached"
            return f"LLM extraction skipped ({reason}) for {company_name}"

        if not markdown or not markdown.strip():
            return f"empty markdown for {company_name}"

        return None

    def _track_extraction_cost(self, response: AIMessage, company_name: str) -> None:
        """Extract token usage from LLM response and record in budget service."""
        tokens_in = 0
        tokens_out = 0
        cost_usd = 0.0

        # LangChain response includes usage_metadata
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            tokens_in = usage.get("input_tokens", 0)
            tokens_out = usage.get("output_tokens", 0)

        # Estimate cost using model-specific pricing
        # Treat values < $0.01 as zero to avoid float comparison
        if cost_usd < 0.01:
            input_rate, output_rate = self._get_model_pricing()
            input_cost = (tokens_in / 1_000_000) * input_rate
            output_cost = (tokens_out / 1_000_000) * output_rate
            cost_usd = input_cost + output_cost

        # Record API call in budget service
        if cost_usd > 0 or tokens_in > 0 or tokens_out > 0:
            self.budget_service.record_api_call(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                company_name=company_name,
                model=self.model,
            )

    def extract_jobs(
        self,
        markdown: str,
        company_name: str,
        careers_url: str | None = None,
    ) -> list[OpportunityData]:
        """Extract leadership jobs from markdown using LLM

        Args:
            markdown: Career page markdown content
            company_name: Company name for context
            careers_url: URL of the careers page (for failure tracking)

        Returns:
            List of extracted job opportunities

        Raises:
            TimeoutError: If extraction exceeds timeout
            Exception: If LLM extraction fails
        """
        skip_reason = self._validate_extraction_request(markdown, company_name)
        if skip_reason:
            logger.info("LLM extraction skipped: %s", skip_reason)
            return []

        try:
            jobs = self._run_llm_extraction(markdown, company_name, careers_url=careers_url)
            return jobs

        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"LLM extraction failed for {company_name}: {e}", exc_info=True)

            # Store failure in database
            self.database.store_llm_failure(
                company_name=company_name,
                careers_url=careers_url,
                failure_reason=type(e).__name__,
                error_details=str(e),
            )

            return []

    def _run_llm_extraction(
        self,
        markdown: str,
        company_name: str,
        careers_url: str | None = None,
    ) -> list[OpportunityData]:
        """Execute LLM extraction call and process response.

        Args:
            markdown: Career page markdown content
            company_name: Company name for context
            careers_url: URL of the careers page (for failure tracking)

        Returns:
            List of extracted job opportunities

        Raises:
            TimeoutError: If extraction exceeds timeout
        """
        start_time = time.time()

        # Format prompt with company name and markdown
        # Limit markdown to 10k chars
        prompt_text = self.config["extraction_prompt"].format(
            company_name=company_name,
            markdown_content=markdown[:10000],
        )

        # Add JSON schema instructions
        full_prompt = f"""{prompt_text}

IMPORTANT: Respond ONLY with a JSON array of objects. Each object must have:
- "title": Job title (required)
- "link": URL to job posting (required)
- "location": Location string (optional, can be null)

Example response format:
[
  {{"title": "VP of Engineering", "link": "https://company.com/jobs/123", "location": "San Francisco, CA"}},
  {{"title": "Director of Robotics", "link": "https://company.com/jobs/456", "location": "Remote"}}
]

Do not include any other text, explanations, or markdown formatting. Return ONLY the JSON array."""

        # Create message and invoke LLM
        message = HumanMessage(content=full_prompt)
        response = self.llm.invoke([message])

        elapsed = time.time() - start_time

        # Check timeout
        if elapsed > self.timeout_seconds:
            error_msg = f"LLM extraction timeout ({elapsed:.1f}s > {self.timeout_seconds}s)"
            logger.error(f"{error_msg} for {company_name}")
            self.database.store_llm_failure(
                company_name=company_name,
                careers_url=careers_url,
                failure_reason="Timeout",
                error_details=error_msg,
            )
            raise TimeoutError(error_msg)

        # Parse LLM response
        jobs = self._parse_llm_response(response.content, company_name)

        # Log successful extraction
        logger.info(f"LLM extracted {len(jobs)} jobs from {company_name} in {elapsed:.1f}s")

        # Track cost/tokens
        self._track_extraction_cost(response, company_name)

        return jobs

    @staticmethod
    def _parse_llm_response(content: str, company_name: str) -> list[OpportunityData]:
        """Parse LLM response into OpportunityData objects

        Args:
            content: LLM response content (JSON string)
            company_name: Company name

        Returns:
            List of OpportunityData objects
        """
        job_data = _parse_json_response(content, company_name)
        if job_data is None:
            return []

        jobs = []
        for item in job_data:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item for {company_name}")
                continue

            # Validate required fields are present and not None
            if not item.get("title") or not item.get("link"):
                logger.warning(f"Skipping job with missing title/link for {company_name}")
                continue

            try:
                job = OpportunityData(
                    source="llm_extraction",
                    source_email=None,
                    type="direct_job",
                    company=company_name,
                    title=item.get("title"),
                    location=item.get("location"),
                    link=item.get("link"),
                    description=None,
                    salary=None,
                    job_type=None,
                    posted_date=None,
                    needs_research=False,
                )
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job item for {company_name}: {e}")
                continue

        return jobs


def _parse_json_response(content: str, company_name: str) -> list[dict] | None:
    """Parse JSON from LLM response, handling markdown code blocks.

    Returns:
        Parsed list of dicts, or None if parsing fails.
    """
    try:
        cleaned = content.strip()
        # Remove markdown code block wrappers
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        job_data = json.loads(cleaned)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response for {company_name}: {e}")
        logger.debug(f"Response content: {content[:500]}")
        return None

    if not isinstance(job_data, list):
        logger.warning(f"Expected JSON array for {company_name}, got {type(job_data)}")
        return None

    return job_data
