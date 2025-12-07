"""
LLM-based job extraction using LangChain with Claude 3.5 Sonnet via OpenRouter
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.api.llm_budget_service import LLMBudgetService
from src.database import JobDatabase
from src.models import OpportunityData

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Extract job postings from markdown using LLM (Claude 3.5 Sonnet via OpenRouter)"""

    def __init__(self, config_path: str = "config/llm-extraction-settings.json"):
        """Initialize LLM extractor with configuration

        Args:
            config_path: Path to LLM extraction configuration file
        """
        self.config = self._load_config(config_path)
        self.database = JobDatabase()

        # Initialize budget tracking service
        self.budget_service = LLMBudgetService(
            monthly_limit=self.config["budget"]["monthly_limit_usd"],
            alert_threshold=0.8,  # 80% threshold for alerts
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
            model=self.config["llm_config"]["llm"]["model"],
            temperature=self.config["llm_config"]["llm"]["temperature"],
        )

        self.timeout_seconds = self.config.get("timeout_seconds", 30)

    def _load_config(self, config_path: str) -> dict[str, Any]:
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

    def budget_available(self) -> bool:
        """Check if monthly budget has not been exceeded

        Returns:
            True if budget available, False if exceeded
        """
        if not self.config["budget"]["pause_when_exceeded"]:
            return True

        # Check budget via budget service
        return self.budget_service.check_budget_available()

    def extract_jobs(self, markdown: str, company_name: str) -> list[OpportunityData]:
        """Extract leadership jobs from markdown using LLM

        Args:
            markdown: Career page markdown content
            company_name: Company name for context

        Returns:
            List of extracted job opportunities

        Raises:
            TimeoutError: If extraction exceeds timeout
            Exception: If LLM extraction fails
        """
        if not self.config["enabled"]:
            logger.info("LLM extraction disabled in config")
            return []

        # Check budget before extraction
        if not self.budget_available():
            logger.warning(
                f"LLM extraction skipped for {company_name}: monthly budget limit reached"
            )
            return []

        if not markdown or not markdown.strip():
            logger.warning(f"Empty markdown for {company_name}")
            return []

        try:
            start_time = time.time()

            # Format prompt with company name and markdown
            prompt_text = self.config["extraction_prompt"].format(
                company_name=company_name,
                markdown_content=markdown[:10000],  # Limit to 10k chars
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
                    failure_reason="Timeout",
                    error_details=error_msg,
                )
                raise TimeoutError(error_msg)

            # Parse LLM response
            jobs = self._parse_llm_response(response.content, company_name)

            # Log successful extraction
            logger.info(f"LLM extracted {len(jobs)} jobs from {company_name} in {elapsed:.1f}s")

            # Track cost/tokens
            # Extract token usage from response metadata
            tokens_in = 0
            tokens_out = 0
            cost_usd = 0.0

            # LangChain response includes usage_metadata
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)

            # Estimate cost if not provided
            # OpenRouter Claude 3.5 Sonnet pricing (approximate):
            # Input: $3.00 per 1M tokens, Output: $15.00 per 1M tokens
            if cost_usd < 0.01:  # Treat values < $0.01 as zero to avoid float comparison
                input_cost = (tokens_in / 1_000_000) * 3.00
                output_cost = (tokens_out / 1_000_000) * 15.00
                cost_usd = input_cost + output_cost

            # Record API call in budget service
            if cost_usd > 0 or tokens_in > 0 or tokens_out > 0:
                self.budget_service.record_api_call(
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                    company_name=company_name,
                    model=self.config["llm_config"]["llm"]["model"],
                )

            return jobs

        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"LLM extraction failed for {company_name}: {e}", exc_info=True)

            # Store failure in database
            self.database.store_llm_failure(
                company_name=company_name,
                failure_reason=type(e).__name__,
                error_details=str(e),
            )

            return []

    def _parse_llm_response(self, content: str, company_name: str) -> list[OpportunityData]:
        """Parse LLM response into OpportunityData objects

        Args:
            content: LLM response content (JSON string)
            company_name: Company name

        Returns:
            List of OpportunityData objects
        """
        jobs = []

        # Parse JSON response
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]  # Remove ```json
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]  # Remove ```
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]  # Remove trailing ```
            cleaned = cleaned.strip()

            # Parse JSON
            job_data = json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response for {company_name}: {e}")
            logger.debug(f"Response content: {content[:500]}")
            return []

        # Ensure job_data is a list
        if not isinstance(job_data, list):
            logger.warning(f"Expected JSON array for {company_name}, got {type(job_data)}")
            return []

        # Process each job item
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
