"""
LLM Budget Tracking Service - Monitor and enforce monthly API cost limits
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LLMBudgetService:
    """Track LLM API costs and enforce monthly budget limits"""

    def __init__(
        self,
        monthly_limit: float = 5.0,
        alert_threshold: float = 0.8,
        logs_dir: str = "logs",
    ):
        """Initialize budget tracking service

        Args:
            monthly_limit: Maximum monthly spending in USD (default: $5.00)
            alert_threshold: Fraction of budget to trigger alert (default: 0.8 = 80%)
            logs_dir: Directory for budget tracking files
        """
        self.monthly_limit = monthly_limit
        self.alert_threshold = alert_threshold
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        # Track if alert has been sent for current month
        self._alert_sent_this_month = False

    def _get_budget_file_path(self, year: int | None = None, month: int | None = None) -> Path:
        """Get path to budget tracking file for a specific month

        Args:
            year: Year (default: current year)
            month: Month 1-12 (default: current month)

        Returns:
            Path to budget file
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        filename = f"llm-budget-{year}-{month:02d}.json"
        return self.logs_dir / filename

    def _load_budget_data(
        self, year: int | None = None, month: int | None = None
    ) -> dict[str, Any]:
        """Load budget data for a specific month

        Args:
            year: Year (default: current year)
            month: Month 1-12 (default: current month)

        Returns:
            Budget data dictionary with 'records' list and 'total_cost' float
        """
        budget_file = self._get_budget_file_path(year, month)

        if not budget_file.exists():
            return {"records": [], "total_cost": 0.0}

        try:
            with budget_file.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load budget data from {budget_file}: {e}")
            return {"records": [], "total_cost": 0.0}

    def _save_budget_data(
        self, data: dict[str, Any], year: int | None = None, month: int | None = None
    ) -> None:
        """Save budget data for a specific month

        Args:
            data: Budget data dictionary
            year: Year (default: current year)
            month: Month 1-12 (default: current month)
        """
        budget_file = self._get_budget_file_path(year, month)

        try:
            with budget_file.open("w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save budget data to {budget_file}: {e}")

    def get_monthly_spend(self, year: int | None = None, month: int | None = None) -> float:
        """Get total spending for a specific month

        Args:
            year: Year (default: current year)
            month: Month 1-12 (default: current month)

        Returns:
            Total spending in USD
        """
        data = self._load_budget_data(year, month)
        return data.get("total_cost", 0.0)

    def get_remaining_budget(self, year: int | None = None, month: int | None = None) -> float:
        """Get remaining budget for a specific month

        Args:
            year: Year (default: current year)
            month: Month 1-12 (default: current month)

        Returns:
            Remaining budget in USD (can be negative if over budget)
        """
        spent = self.get_monthly_spend(year, month)
        return self.monthly_limit - spent

    def check_budget_available(self, year: int | None = None, month: int | None = None) -> bool:
        """Check if budget is available for LLM extraction

        Args:
            year: Year (default: current year)
            month: Month 1-12 (default: current month)

        Returns:
            True if budget available, False if exceeded
        """
        remaining = self.get_remaining_budget(year, month)
        return remaining > 0

    def record_api_call(
        self,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        company_name: str | None = None,
        model: str | None = None,
    ) -> None:
        """Record an LLM API call and update budget tracking

        Args:
            tokens_in: Input tokens used
            tokens_out: Output tokens generated
            cost_usd: Cost in USD
            company_name: Company being extracted (optional)
            model: LLM model used (optional)
        """
        now = datetime.now()
        year = now.year
        month = now.month

        # Load current month's data
        data = self._load_budget_data(year, month)

        # Create record
        record = {
            "timestamp": now.isoformat(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "company_name": company_name,
            "model": model,
        }

        # Update data
        data["records"].append(record)
        data["total_cost"] = data.get("total_cost", 0.0) + cost_usd

        # Save updated data
        self._save_budget_data(data, year, month)

        # Log the record (no user-controlled data)
        logger.info("Recorded API call successfully")

        # Check if alert threshold reached
        if (
            data["total_cost"] >= (self.monthly_limit * self.alert_threshold)
            and not self._alert_sent_this_month
        ):
            self._send_budget_alert()
            self._alert_sent_this_month = True

        # Check if budget exceeded
        if data["total_cost"] >= self.monthly_limit:
            logger.warning(f"Monthly budget limit of ${self.monthly_limit:.2f} has been exceeded")

    def _send_budget_alert(self) -> None:
        """Send alert email when budget threshold is reached"""
        threshold_amount = self.monthly_limit * self.alert_threshold

        logger.warning(f"Budget alert: spending threshold of ${threshold_amount:.2f} reached")

        # TODO: Integrate with existing email notification system
        # For now, just log the alert
        # In future PR, this will call the notifier service
        logger.info("Budget alert notification triggered")

    def should_pause_extraction(self) -> bool:
        """Check if LLM extraction should be paused due to budget

        Returns:
            True if extraction should be paused, False otherwise
        """
        return not self.check_budget_available()

    def get_budget_status(self) -> dict[str, Any]:
        """Get comprehensive budget status for current month

        Returns:
            Dictionary with budget metrics
        """
        now = datetime.now()
        spent = self.get_monthly_spend()
        remaining = self.get_remaining_budget()
        data = self._load_budget_data()

        return {
            "month": f"{now.year}-{now.month:02d}",
            "monthly_limit": self.monthly_limit,
            "total_spent": spent,
            "remaining": remaining,
            "percentage_used": (spent / self.monthly_limit) * 100,
            "api_calls": len(data.get("records", [])),
            "budget_available": remaining > 0,
            "alert_threshold": self.monthly_limit * self.alert_threshold,
            "alert_triggered": spent >= (self.monthly_limit * self.alert_threshold),
        }
