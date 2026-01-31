"""
System Health Checker - Aggregate health metrics for TUI display

Consolidates metrics from:
- Database statistics (jobs, scores, by profile)
- LLM extraction failures
- Budget tracking
- Recent scraper activity
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.api.llm_budget_service import LLMBudgetService
from src.database import JobDatabase

logger = logging.getLogger(__name__)


class SystemHealthChecker:
    """Aggregates system health metrics for display in TUI"""

    def __init__(
        self,
        db: JobDatabase,
        config_path: str = "config/health-check-settings.json",
    ):
        """Initialize health checker

        Args:
            db: Job database instance
            config_path: Path to health check configuration file
        """
        self.db = db
        self.budget_service = LLMBudgetService(
            monthly_limit=15.0,  # From config/llm-extraction-settings.json
            alert_threshold=0.8,
        )
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict[str, Any]:
        """Load health check configuration

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        config_file = Path(config_path)

        # Default configuration
        default_config = {
            "alert_thresholds": {
                "llm_failures_24h": 50,
                "llm_failures_pending": 10,
                "budget_warning_percent": 80,
                "budget_critical_percent": 100,
                "days_since_scrape": 7,
            },
            "auto_display": {
                "enabled": True,
                "on_startup": True,
                "critical_only": True,
            },
            "display_options": {
                "show_per_profile_stats": True,
                "show_recent_jobs": 10,
            },
        }

        if not config_file.exists():
            logger.info(f"Config file {config_path} not found, using defaults")
            return default_config

        try:
            with config_file.open() as f:
                user_config = json.load(f)
                # Merge with defaults
                config = default_config.copy()
                config.update(user_config)
                return config
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return default_config

    def get_health_summary(self) -> dict[str, Any]:
        """Get complete system health snapshot

        Returns:
            Dictionary with health metrics:
            - llm_failures: LLM extraction failure statistics
            - budget: Budget status
            - database: Database health metrics
            - recent_activity: Recent scraper runs
            - critical_issues: List of critical issues
        """
        return {
            "llm_failures": self._get_llm_failure_stats(),
            "budget": self._get_budget_health(),
            "database": self._get_database_health(),
            "recent_activity": self._get_recent_activity(),
            "critical_issues": self._get_critical_issues(),
        }

    def _get_llm_failure_stats(self) -> dict[str, Any]:
        """Get LLM extraction failure statistics

        Returns:
            Dictionary with failure metrics:
            - total_pending: Count of failures awaiting review
            - last_24h: Count of failures in last 24 hours
            - most_common_error: Most common error type
            - last_failure_time: Timestamp of most recent failure
            - last_failure_company: Company name of most recent failure
        """
        # Get pending failures
        pending_failures = self.db.get_llm_failures(review_action="pending")
        total_pending = len(pending_failures)

        # Get all recent failures to count last 24h
        all_failures = self.db.get_llm_failures(limit=1000)

        # Count failures in last 24h
        cutoff_time = datetime.now() - timedelta(hours=24)
        last_24h_count = 0
        for failure in all_failures:
            try:
                failure_time = datetime.fromisoformat(failure["occurred_at"])
                if failure_time > cutoff_time:
                    last_24h_count += 1
            except (ValueError, KeyError):
                continue

        # Find most common error
        error_counts: dict[str, int] = {}
        for failure in all_failures:
            reason = failure.get("failure_reason", "Unknown")
            error_counts[reason] = error_counts.get(reason, 0) + 1

        most_common_error = None
        most_common_count = 0
        if error_counts:
            most_common_error = max(error_counts.keys(), key=lambda k: error_counts[k])
            most_common_count = error_counts[most_common_error]

        # Get most recent failure
        last_failure = all_failures[0] if all_failures else None

        return {
            "total_pending": total_pending,
            "last_24h": last_24h_count,
            "most_common_error": most_common_error,
            "most_common_count": most_common_count,
            "last_failure_time": last_failure["occurred_at"] if last_failure else None,
            "last_failure_company": last_failure["company_name"] if last_failure else None,
        }

    def _get_budget_health(self) -> dict[str, Any]:
        """Get budget status from LLMBudgetService

        Returns:
            Dictionary with budget metrics from budget service
        """
        return self.budget_service.get_budget_status()

    def _get_database_health(self) -> dict[str, Any]:
        """Get database statistics (jobs, by grade, by profile)

        Returns:
            Dictionary with database metrics:
            - total_jobs: Total number of jobs in database
            - notified_jobs: Jobs that triggered notifications
            - jobs_by_source: Breakdown by source
            - high_quality_jobs: Count of A/B grade jobs
            - by_grade: Breakdown by grade
        """
        # Get overall stats
        stats = self.db.get_stats()

        # Count A/B grade jobs across all profiles
        conn = self.db.db_path
        db_conn = sqlite3.connect(conn)
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM job_scores
            WHERE fit_grade IN ('A', 'B')
        """)
        high_quality_jobs = cursor.fetchone()[0]

        # Get grade breakdown
        cursor.execute("""
            SELECT fit_grade, COUNT(*) as count
            FROM job_scores
            GROUP BY fit_grade
        """)
        by_grade = dict(cursor.fetchall())

        db_conn.close()

        return {
            "total_jobs": stats["total_jobs"],
            "notified_jobs": stats["notified_jobs"],
            "jobs_by_source": stats.get("jobs_by_source", {}),
            "high_quality_jobs": high_quality_jobs,
            "by_grade": by_grade,
        }

    def _get_recent_activity(self) -> dict[str, Any]:
        """Get recent scraper runs and job discoveries

        Returns:
            Dictionary with recent activity metrics:
            - last_run_time: Timestamp of most recent scrape
            - jobs_found_last_run: Number of jobs discovered
            - last_run_source: Source of last run
        """
        # Get most recently added job
        conn = self.db.db_path
        db_conn = sqlite3.connect(conn)
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT received_at, source FROM jobs
            ORDER BY received_at DESC
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            last_run_time = result[0]
            last_run_source = result[1]

            # Count jobs from same time (within 5 minutes)
            cursor.execute(
                """
                SELECT COUNT(*) FROM jobs
                WHERE datetime(received_at) >= datetime(?, '-5 minutes')
            """,
                (last_run_time,),
            )
            jobs_found = cursor.fetchone()[0]
        else:
            last_run_time = None
            last_run_source = None
            jobs_found = 0

        db_conn.close()

        return {
            "last_run_time": last_run_time,
            "jobs_found_last_run": jobs_found,
            "last_run_source": last_run_source,
        }

    def _get_critical_issues(self) -> list[dict[str, Any]]:
        """Identify critical issues requiring attention

        Returns:
            List of issue dictionaries with severity, message, and suggested action
        """
        issues = []
        thresholds = self.config["alert_thresholds"]

        # Check LLM failures
        failure_stats = self._get_llm_failure_stats()

        if failure_stats["last_24h"] >= thresholds["llm_failures_24h"]:
            issues.append(
                {
                    "severity": "red",
                    "category": "llm_failures",
                    "message": f"{failure_stats['last_24h']} LLM failures in last 24h",
                    "action": "Review failures to avoid wasting budget",
                }
            )

        if failure_stats["total_pending"] >= thresholds["llm_failures_pending"]:
            issues.append(
                {
                    "severity": "yellow",
                    "category": "llm_failures",
                    "message": f"{failure_stats['total_pending']} LLM failures need review",
                    "action": "Review and retry or skip failed extractions",
                }
            )

        # Check budget
        budget = self._get_budget_health()

        if budget["percentage_used"] >= thresholds["budget_critical_percent"]:
            issues.append(
                {
                    "severity": "red",
                    "category": "budget",
                    "message": f"Budget exceeded: ${budget['total_spent']:.2f} / ${budget['monthly_limit']:.2f}",
                    "action": "LLM extraction is paused until next month",
                }
            )
        elif budget["percentage_used"] >= thresholds["budget_warning_percent"]:
            issues.append(
                {
                    "severity": "yellow",
                    "category": "budget",
                    "message": f"Budget at {budget['percentage_used']:.0f}% (${budget['total_spent']:.2f} / ${budget['monthly_limit']:.2f})",
                    "action": "Monitor usage closely to avoid exceeding budget",
                }
            )

        # Check scraper activity
        activity = self._get_recent_activity()
        if activity["last_run_time"]:
            try:
                last_run = datetime.fromisoformat(activity["last_run_time"])
                days_since = (datetime.now() - last_run).days

                if days_since >= thresholds["days_since_scrape"]:
                    issues.append(
                        {
                            "severity": "yellow",
                            "category": "activity",
                            "message": f"No jobs scraped in {days_since} days",
                            "action": "Check if weekly scraper is running",
                        }
                    )
            except ValueError:
                pass

        return issues

    def should_auto_display(self) -> bool:
        """Check if health check should auto-display at startup

        Returns:
            True if auto-display is enabled and conditions are met
        """
        auto_config = self.config["auto_display"]

        if not auto_config["enabled"] or not auto_config["on_startup"]:
            return False

        if auto_config["critical_only"]:
            # Only show if there are critical issues
            critical = self._get_critical_issues()
            return len(critical) > 0

        return True
