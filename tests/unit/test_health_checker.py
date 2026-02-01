"""
Unit tests for SystemHealthChecker

Tests health check data aggregation from:
- LLM extraction failures
- Budget tracking
- Database statistics
- Critical issue detection
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.utils.health_checker import SystemHealthChecker


class TestSystemHealthCheckerInit:
    """Test initialization and config loading"""

    def test_init_with_default_config(self):
        """Should initialize with default config when file doesn't exist"""
        db = Mock()

        with patch("src.utils.health_checker.Path.exists", return_value=False):
            checker = SystemHealthChecker(db, config_path="nonexistent.json")

        assert checker.db == db
        assert checker.config["alert_thresholds"]["llm_failures_24h"] == 50
        assert checker.config["auto_display"]["enabled"] is True

    def test_init_with_custom_config(self, tmp_path):
        """Should load custom config from file"""
        db = Mock()
        config_file = tmp_path / "health-config.json"

        custom_config = {
            "alert_thresholds": {
                "llm_failures_24h": 100,
                "budget_warning_percent": 90,
            }
        }

        config_file.write_text(json.dumps(custom_config))

        checker = SystemHealthChecker(db, config_path=str(config_file))

        assert checker.config["alert_thresholds"]["llm_failures_24h"] == 100
        assert checker.config["alert_thresholds"]["budget_warning_percent"] == 90

    def test_init_with_invalid_config(self, tmp_path):
        """Should fall back to defaults if config is invalid"""
        db = Mock()
        config_file = tmp_path / "bad-config.json"
        config_file.write_text("{ invalid json }")

        checker = SystemHealthChecker(db, config_path=str(config_file))

        # Should have default config
        assert checker.config["alert_thresholds"]["llm_failures_24h"] == 50


class TestLLMFailureStats:
    """Test _get_llm_failure_stats method"""

    def test_no_failures(self):
        """Should return zero counts when no failures"""
        db = Mock()
        db.get_llm_failures.return_value = []

        checker = SystemHealthChecker(db)
        stats = checker._get_llm_failure_stats()

        assert stats["total_pending"] == 0
        assert stats["last_24h"] == 0
        assert stats["most_common_error"] is None
        assert stats["last_failure_time"] is None

    def test_pending_failures_count(self):
        """Should count pending failures correctly"""
        db = Mock()
        db.get_llm_failures.side_effect = [
            # First call with review_action='pending'
            [
                {"id": 1, "company_name": "Company A", "failure_reason": "Timeout"},
                {"id": 2, "company_name": "Company B", "failure_reason": "Timeout"},
            ],
            # Second call with limit=1000
            [
                {
                    "id": 1,
                    "company_name": "Company A",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T10:00:00",
                },
                {
                    "id": 2,
                    "company_name": "Company B",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T11:00:00",
                },
            ],
        ]

        checker = SystemHealthChecker(db)
        stats = checker._get_llm_failure_stats()

        assert stats["total_pending"] == 2

    def test_last_24h_count(self):
        """Should count failures in last 24 hours"""
        db = Mock()

        now = datetime.now()
        recent = (now - timedelta(hours=2)).isoformat()
        old = (now - timedelta(hours=30)).isoformat()

        db.get_llm_failures.side_effect = [
            [],  # Pending failures
            [
                {"id": 1, "company_name": "A", "failure_reason": "Timeout", "occurred_at": recent},
                {"id": 2, "company_name": "B", "failure_reason": "Timeout", "occurred_at": recent},
                {"id": 3, "company_name": "C", "failure_reason": "Timeout", "occurred_at": old},
            ],
        ]

        checker = SystemHealthChecker(db)
        stats = checker._get_llm_failure_stats()

        assert stats["last_24h"] == 2  # Only recent ones

    def test_most_common_error(self):
        """Should identify most common error type"""
        db = Mock()

        db.get_llm_failures.side_effect = [
            [],  # Pending
            [
                {
                    "id": 1,
                    "company_name": "Company A",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T10:00:00",
                },
                {
                    "id": 2,
                    "company_name": "Company B",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T11:00:00",
                },
                {
                    "id": 3,
                    "company_name": "Company C",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T12:00:00",
                },
                {
                    "id": 4,
                    "company_name": "Company D",
                    "failure_reason": "APIError",
                    "occurred_at": "2026-01-31T13:00:00",
                },
            ],
        ]

        checker = SystemHealthChecker(db)
        stats = checker._get_llm_failure_stats()

        assert stats["most_common_error"] == "Timeout"
        assert stats["most_common_count"] == 3

    def test_last_failure_details(self):
        """Should capture last failure details"""
        db = Mock()

        db.get_llm_failures.side_effect = [
            [],  # Pending
            [
                {
                    "id": 1,
                    "company_name": "Latest Co",
                    "failure_reason": "Timeout",
                    "occurred_at": "2026-01-31T12:00:00",
                },
            ],
        ]

        checker = SystemHealthChecker(db)
        stats = checker._get_llm_failure_stats()

        assert stats["last_failure_time"] == "2026-01-31T12:00:00"
        assert stats["last_failure_company"] == "Latest Co"


class TestBudgetHealth:
    """Test _get_budget_health method"""

    @patch("src.utils.health_checker.LLMBudgetService")
    def test_budget_health_delegation(self, mock_budget_service_class):
        """Should delegate to LLMBudgetService.get_budget_status()"""
        db = Mock()
        mock_budget_instance = Mock()
        mock_budget_instance.get_budget_status.return_value = {
            "monthly_limit": 15.0,
            "total_spent": 6.5,
            "percentage_used": 43.3,
        }
        mock_budget_service_class.return_value = mock_budget_instance

        checker = SystemHealthChecker(db)
        budget = checker._get_budget_health()

        assert budget["monthly_limit"] == 15.0
        assert budget["total_spent"] == 6.5
        assert budget["percentage_used"] == 43.3


class TestDatabaseHealth:
    """Test _get_database_health method"""

    def test_database_stats_aggregation(self):
        """Should aggregate database statistics"""
        db = Mock()
        db.get_stats.return_value = {
            "total_jobs": 1500,
            "notified_jobs": 300,
            "jobs_by_source": {"linkedin": 800, "companies": 700},
        }
        db.db_path = ":memory:"

        # Mock sqlite3 connection
        with patch("src.utils.health_checker.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.side_effect = [
                (250,),  # High quality jobs
            ]
            mock_cursor.fetchall.return_value = [("A", 100), ("B", 150), ("C", 200)]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            checker = SystemHealthChecker(db)
            stats = checker._get_database_health()

        assert stats["total_jobs"] == 1500
        assert stats["high_quality_jobs"] == 250
        assert stats["by_grade"] == {"A": 100, "B": 150, "C": 200}


class TestRecentActivity:
    """Test _get_recent_activity method"""

    def test_recent_activity_found(self):
        """Should get most recent scrape activity"""
        db = Mock()
        db.db_path = ":memory:"

        with patch("src.utils.health_checker.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.side_effect = [
                ("2026-01-31T10:00:00", "linkedin"),  # Last run
                (25,),  # Jobs found
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            checker = SystemHealthChecker(db)
            activity = checker._get_recent_activity()

        assert activity["last_run_time"] == "2026-01-31T10:00:00"
        assert activity["last_run_source"] == "linkedin"
        assert activity["jobs_found_last_run"] == 25

    def test_no_recent_activity(self):
        """Should handle no recent activity"""
        db = Mock()
        db.db_path = ":memory:"

        with patch("src.utils.health_checker.sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            checker = SystemHealthChecker(db)
            activity = checker._get_recent_activity()

        assert activity["last_run_time"] is None
        assert activity["last_run_source"] is None
        assert activity["jobs_found_last_run"] == 0


class TestCriticalIssues:
    """Test _get_critical_issues method"""

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_no_critical_issues(self, mock_activity, mock_budget, mock_failures):
        """Should return empty list when no critical issues"""
        db = Mock()

        mock_failures.return_value = {
            "total_pending": 5,
            "last_24h": 10,
        }
        mock_budget.return_value = {
            "percentage_used": 50.0,
            "total_spent": 7.5,
            "monthly_limit": 15.0,
        }
        mock_activity.return_value = {
            "last_run_time": datetime.now().isoformat(),
        }

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert issues == []

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_high_llm_failures_24h(self, mock_activity, mock_budget, mock_failures):
        """Should flag high LLM failures in 24h as critical"""
        db = Mock()

        mock_failures.return_value = {
            "total_pending": 5,
            "last_24h": 60,  # Above threshold
        }
        mock_budget.return_value = {
            "percentage_used": 50.0,
            "total_spent": 7.5,
            "monthly_limit": 15.0,
        }
        mock_activity.return_value = {"last_run_time": datetime.now().isoformat()}

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert len(issues) == 1
        assert issues[0]["severity"] == "red"
        assert issues[0]["category"] == "llm_failures"
        assert "60 LLM failures" in issues[0]["message"]

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_pending_failures_warning(self, mock_activity, mock_budget, mock_failures):
        """Should flag pending failures as warning"""
        db = Mock()

        mock_failures.return_value = {
            "total_pending": 15,  # Above threshold
            "last_24h": 20,
        }
        mock_budget.return_value = {
            "percentage_used": 50.0,
            "total_spent": 7.5,
            "monthly_limit": 15.0,
        }
        mock_activity.return_value = {"last_run_time": datetime.now().isoformat()}

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert any(
            issue["category"] == "llm_failures" and issue["severity"] == "yellow"
            for issue in issues
        )

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_budget_exceeded(self, mock_activity, mock_budget, mock_failures):
        """Should flag budget exceeded as critical"""
        db = Mock()

        mock_failures.return_value = {"total_pending": 0, "last_24h": 0}
        mock_budget.return_value = {
            "percentage_used": 105.0,  # Over 100%
            "total_spent": 15.75,
            "monthly_limit": 15.0,
        }
        mock_activity.return_value = {"last_run_time": datetime.now().isoformat()}

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert any(issue["category"] == "budget" and issue["severity"] == "red" for issue in issues)
        assert any("exceeded" in issue["message"].lower() for issue in issues)

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_budget_warning(self, mock_activity, mock_budget, mock_failures):
        """Should flag budget warning at 80%+"""
        db = Mock()

        mock_failures.return_value = {"total_pending": 0, "last_24h": 0}
        mock_budget.return_value = {
            "percentage_used": 85.0,  # Above 80%
            "total_spent": 12.75,
            "monthly_limit": 15.0,
        }
        mock_activity.return_value = {"last_run_time": datetime.now().isoformat()}

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert any(
            issue["category"] == "budget" and issue["severity"] == "yellow" for issue in issues
        )

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    def test_stale_scraper(self, mock_activity, mock_budget, mock_failures):
        """Should flag stale scraper (7+ days)"""
        db = Mock()

        mock_failures.return_value = {"total_pending": 0, "last_24h": 0}
        mock_budget.return_value = {
            "percentage_used": 50.0,
            "total_spent": 7.5,
            "monthly_limit": 15.0,
        }

        # Last run 8 days ago
        old_run = (datetime.now() - timedelta(days=8)).isoformat()
        mock_activity.return_value = {"last_run_time": old_run}

        checker = SystemHealthChecker(db)
        issues = checker._get_critical_issues()

        assert any(
            issue["category"] == "activity" and issue["severity"] == "yellow" for issue in issues
        )


class TestHealthSummary:
    """Test get_health_summary method"""

    @patch.object(SystemHealthChecker, "_get_llm_failure_stats")
    @patch.object(SystemHealthChecker, "_get_budget_health")
    @patch.object(SystemHealthChecker, "_get_database_health")
    @patch.object(SystemHealthChecker, "_get_recent_activity")
    @patch.object(SystemHealthChecker, "_get_critical_issues")
    def test_health_summary_aggregation(
        self, mock_critical, mock_activity, mock_db, mock_budget, mock_failures
    ):
        """Should aggregate all health metrics into summary"""
        db = Mock()

        mock_failures.return_value = {"total_pending": 5}
        mock_budget.return_value = {"percentage_used": 50.0}
        mock_db.return_value = {"total_jobs": 1000}
        mock_activity.return_value = {"last_run_time": "2026-01-31T10:00:00"}
        mock_critical.return_value = []

        checker = SystemHealthChecker(db)
        summary = checker.get_health_summary()

        assert "llm_failures" in summary
        assert "budget" in summary
        assert "database" in summary
        assert "recent_activity" in summary
        assert "critical_issues" in summary
        assert summary["llm_failures"]["total_pending"] == 5
        assert summary["budget"]["percentage_used"] == 50.0


class TestAutoDisplay:
    """Test should_auto_display method"""

    def test_auto_display_disabled(self):
        """Should not auto-display if disabled in config"""
        db = Mock()

        with patch("src.utils.health_checker.Path.exists", return_value=False):
            checker = SystemHealthChecker(db)
            checker.config["auto_display"]["enabled"] = False

            assert checker.should_auto_display() is False

    @patch.object(SystemHealthChecker, "_get_critical_issues")
    def test_auto_display_critical_only_with_issues(self, mock_critical):
        """Should auto-display if critical_only=true and issues exist"""
        db = Mock()

        mock_critical.return_value = [{"severity": "red", "message": "Budget exceeded"}]

        checker = SystemHealthChecker(db)
        checker.config["auto_display"]["enabled"] = True
        checker.config["auto_display"]["on_startup"] = True
        checker.config["auto_display"]["critical_only"] = True

        assert checker.should_auto_display() is True

    @patch.object(SystemHealthChecker, "_get_critical_issues")
    def test_auto_display_critical_only_no_issues(self, mock_critical):
        """Should not auto-display if critical_only=true and no issues"""
        db = Mock()

        mock_critical.return_value = []

        checker = SystemHealthChecker(db)
        checker.config["auto_display"]["enabled"] = True
        checker.config["auto_display"]["on_startup"] = True
        checker.config["auto_display"]["critical_only"] = True

        assert checker.should_auto_display() is False
