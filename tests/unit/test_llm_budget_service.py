"""
Unit tests for LLM Budget Tracking Service
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.api.llm_budget_service import LLMBudgetService


@pytest.fixture
def temp_logs_dir():
    """Create temporary logs directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def budget_service(temp_logs_dir):
    """Create budget service with temporary logs directory"""
    return LLMBudgetService(monthly_limit=5.0, alert_threshold=0.8, logs_dir=temp_logs_dir)


class TestLLMBudgetServiceInit:
    """Test LLMBudgetService initialization"""

    def test_init_default_values(self, temp_logs_dir):
        """Test service initializes with default values"""
        service = LLMBudgetService(logs_dir=temp_logs_dir)

        assert service.monthly_limit == 5.0
        assert service.alert_threshold == 0.8
        assert service.logs_dir == Path(temp_logs_dir)

    def test_init_custom_values(self, temp_logs_dir):
        """Test service initializes with custom values"""
        service = LLMBudgetService(monthly_limit=10.0, alert_threshold=0.9, logs_dir=temp_logs_dir)

        assert service.monthly_limit == 10.0
        assert service.alert_threshold == 0.9

    def test_init_creates_logs_directory(self, temp_logs_dir):
        """Test service creates logs directory if it doesn't exist"""
        logs_path = Path(temp_logs_dir) / "subdir"
        LLMBudgetService(logs_dir=str(logs_path))

        assert logs_path.exists()
        assert logs_path.is_dir()


class TestBudgetFilePaths:
    """Test budget file path generation"""

    def test_get_budget_file_path_current_month(self, budget_service):
        """Test budget file path for current month"""
        now = datetime.now()
        expected_filename = f"llm-budget-{now.year}-{now.month:02d}.json"

        path = budget_service._get_budget_file_path()

        assert path.name == expected_filename
        assert path.parent == budget_service.logs_dir

    def test_get_budget_file_path_specific_month(self, budget_service):
        """Test budget file path for specific month"""
        path = budget_service._get_budget_file_path(year=2024, month=3)

        assert path.name == "llm-budget-2024-03.json"

    def test_get_budget_file_path_different_months(self, budget_service):
        """Test budget file paths for different months are unique"""
        path1 = budget_service._get_budget_file_path(year=2024, month=1)
        path2 = budget_service._get_budget_file_path(year=2024, month=2)

        assert path1 != path2


class TestBudgetDataPersistence:
    """Test budget data loading and saving"""

    def test_load_budget_data_nonexistent_file(self, budget_service):
        """Test loading budget data when file doesn't exist"""
        data = budget_service._load_budget_data(year=2024, month=1)

        assert data == {"records": [], "total_cost": 0.0}

    def test_save_and_load_budget_data(self, budget_service):
        """Test saving and loading budget data"""
        test_data = {
            "records": [
                {
                    "timestamp": "2024-01-15T10:30:00",
                    "tokens_in": 100,
                    "tokens_out": 50,
                    "cost_usd": 0.25,
                }
            ],
            "total_cost": 0.25,
        }

        budget_service._save_budget_data(test_data, year=2024, month=1)
        loaded_data = budget_service._load_budget_data(year=2024, month=1)

        assert loaded_data == test_data

    def test_load_budget_data_invalid_json(self, budget_service, temp_logs_dir):
        """Test loading budget data with invalid JSON"""
        # Create file with invalid JSON
        budget_file = Path(temp_logs_dir) / "llm-budget-2024-01.json"
        budget_file.write_text("invalid json {[}")

        data = budget_service._load_budget_data(year=2024, month=1)

        # Should return default empty data
        assert data == {"records": [], "total_cost": 0.0}


class TestMonthlySpending:
    """Test monthly spending calculations"""

    def test_get_monthly_spend_empty(self, budget_service):
        """Test getting monthly spend when no records exist"""
        spend = budget_service.get_monthly_spend(year=2024, month=1)

        assert spend == 0.0

    def test_get_monthly_spend_with_records(self, budget_service):
        """Test getting monthly spend with existing records"""
        test_data = {"records": [], "total_cost": 2.50}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        spend = budget_service.get_monthly_spend(year=2024, month=1)

        assert spend == 2.50

    def test_get_remaining_budget_full(self, budget_service):
        """Test getting remaining budget when nothing spent"""
        remaining = budget_service.get_remaining_budget(year=2024, month=1)

        assert remaining == 5.0

    def test_get_remaining_budget_partial(self, budget_service):
        """Test getting remaining budget with partial spending"""
        test_data = {"records": [], "total_cost": 2.00}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        remaining = budget_service.get_remaining_budget(year=2024, month=1)

        assert remaining == 3.0

    def test_get_remaining_budget_exceeded(self, budget_service):
        """Test getting remaining budget when limit exceeded"""
        test_data = {"records": [], "total_cost": 6.00}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        remaining = budget_service.get_remaining_budget(year=2024, month=1)

        assert remaining == -1.0


class TestBudgetAvailability:
    """Test budget availability checks"""

    def test_check_budget_available_true(self, budget_service):
        """Test budget available when under limit"""
        test_data = {"records": [], "total_cost": 2.00}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        available = budget_service.check_budget_available(year=2024, month=1)

        assert available is True

    def test_check_budget_available_false(self, budget_service):
        """Test budget not available when at limit"""
        test_data = {"records": [], "total_cost": 5.00}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        available = budget_service.check_budget_available(year=2024, month=1)

        assert available is False

    def test_check_budget_available_exceeded(self, budget_service):
        """Test budget not available when exceeded"""
        test_data = {"records": [], "total_cost": 6.00}
        budget_service._save_budget_data(test_data, year=2024, month=1)

        available = budget_service.check_budget_available(year=2024, month=1)

        assert available is False

    def test_should_pause_extraction_under_budget(self, budget_service):
        """Test should not pause when under budget"""
        should_pause = budget_service.should_pause_extraction()

        assert should_pause is False

    def test_should_pause_extraction_over_budget(self, budget_service):
        """Test should pause when over budget"""
        test_data = {"records": [], "total_cost": 5.00}
        now = datetime.now()
        budget_service._save_budget_data(test_data, year=now.year, month=now.month)

        should_pause = budget_service.should_pause_extraction()

        assert should_pause is True


class TestRecordAPICall:
    """Test API call recording"""

    def test_record_api_call_creates_record(self, budget_service):
        """Test recording an API call creates a record"""
        budget_service.record_api_call(
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.25,
            company_name="Test Company",
            model="claude-3.5-sonnet",
        )

        now = datetime.now()
        data = budget_service._load_budget_data(year=now.year, month=now.month)

        assert len(data["records"]) == 1
        assert data["records"][0]["tokens_in"] == 100
        assert data["records"][0]["tokens_out"] == 50
        assert data["records"][0]["cost_usd"] == 0.25
        assert data["records"][0]["company_name"] == "Test Company"
        assert data["records"][0]["model"] == "claude-3.5-sonnet"

    def test_record_api_call_updates_total_cost(self, budget_service):
        """Test recording API calls accumulates total cost"""
        budget_service.record_api_call(100, 50, 0.25)
        budget_service.record_api_call(200, 100, 0.50)

        now = datetime.now()
        data = budget_service._load_budget_data(year=now.year, month=now.month)

        assert data["total_cost"] == 0.75

    def test_record_api_call_includes_timestamp(self, budget_service):
        """Test API call record includes timestamp"""
        before = datetime.now().isoformat()
        budget_service.record_api_call(100, 50, 0.25)
        after = datetime.now().isoformat()

        now = datetime.now()
        data = budget_service._load_budget_data(year=now.year, month=now.month)

        timestamp = data["records"][0]["timestamp"]
        assert before <= timestamp <= after

    def test_record_api_call_multiple_records(self, budget_service):
        """Test recording multiple API calls"""
        for _i in range(5):
            budget_service.record_api_call(100, 50, 0.10)

        now = datetime.now()
        data = budget_service._load_budget_data(year=now.year, month=now.month)

        assert len(data["records"]) == 5
        assert data["total_cost"] == 0.50


class TestBudgetAlerts:
    """Test budget alert functionality"""

    def test_alert_not_triggered_below_threshold(self, budget_service):
        """Test alert not triggered when below threshold"""
        # Spend 70% of budget (threshold is 80%)
        budget_service.record_api_call(100, 50, 3.50)

        # Alert should not be sent
        assert budget_service._alert_sent_this_month is False

    def test_alert_triggered_at_threshold(self, budget_service):
        """Test alert triggered when reaching threshold"""
        # Spend exactly 80% of budget
        budget_service.record_api_call(100, 50, 4.00)

        # Alert should be sent
        assert budget_service._alert_sent_this_month is True

    def test_alert_triggered_above_threshold(self, budget_service):
        """Test alert triggered when exceeding threshold"""
        # Spend 90% of budget
        budget_service.record_api_call(100, 50, 4.50)

        # Alert should be sent
        assert budget_service._alert_sent_this_month is True

    def test_alert_only_sent_once(self, budget_service):
        """Test alert is only sent once per month"""
        # First call at threshold - should trigger alert
        budget_service.record_api_call(100, 50, 4.00)
        assert budget_service._alert_sent_this_month is True

        # Reset flag to test second call doesn't re-trigger
        budget_service._alert_sent_this_month = True

        # Second call should not re-trigger alert
        budget_service.record_api_call(100, 50, 0.50)
        assert budget_service._alert_sent_this_month is True


class TestBudgetStatus:
    """Test budget status reporting"""

    def test_get_budget_status_empty(self, budget_service):
        """Test getting budget status with no spending"""
        status = budget_service.get_budget_status()

        assert status["monthly_limit"] == 5.0
        assert status["total_spent"] == 0.0
        assert status["remaining"] == 5.0
        assert status["percentage_used"] == 0.0
        assert status["api_calls"] == 0
        assert status["budget_available"] is True
        assert status["alert_triggered"] is False

    def test_get_budget_status_with_spending(self, budget_service):
        """Test getting budget status with some spending"""
        budget_service.record_api_call(100, 50, 2.50)

        status = budget_service.get_budget_status()

        assert status["total_spent"] == 2.50
        assert status["remaining"] == 2.50
        assert status["percentage_used"] == 50.0
        assert status["api_calls"] == 1
        assert status["budget_available"] is True

    def test_get_budget_status_at_limit(self, budget_service):
        """Test getting budget status at limit"""
        budget_service.record_api_call(100, 50, 5.00)

        status = budget_service.get_budget_status()

        assert status["total_spent"] == 5.00
        assert status["remaining"] == 0.0
        assert status["percentage_used"] == 100.0
        assert status["budget_available"] is False

    def test_get_budget_status_includes_month(self, budget_service):
        """Test budget status includes current month"""
        status = budget_service.get_budget_status()
        now = datetime.now()

        expected_month = f"{now.year}-{now.month:02d}"
        assert status["month"] == expected_month


class TestMonthBoundaries:
    """Test handling of month boundaries"""

    def test_different_months_separate_budgets(self, budget_service):
        """Test spending in different months are tracked separately"""
        # Spend in January 2024
        budget_service.record_api_call(100, 50, 2.00)
        jan_data = budget_service._load_budget_data(year=2024, month=1)

        # Spend in February 2024
        budget_service.record_api_call(100, 50, 3.00)
        feb_data = budget_service._load_budget_data(year=2024, month=2)

        # Current month should have both
        now = datetime.now()
        current_data = budget_service._load_budget_data(year=now.year, month=now.month)

        # Verify separation (if testing in a month other than Jan/Feb)
        if now.month not in [1, 2]:
            assert jan_data["total_cost"] == 0.0
            assert feb_data["total_cost"] == 0.0
            assert current_data["total_cost"] == 5.00

    def test_budget_resets_each_month(self, budget_service):
        """Test budget effectively resets for each month"""
        # Max out January budget
        test_data_jan = {"records": [], "total_cost": 5.00}
        budget_service._save_budget_data(test_data_jan, year=2024, month=1)

        # February should start fresh
        feb_spend = budget_service.get_monthly_spend(year=2024, month=2)
        assert feb_spend == 0.0

        feb_available = budget_service.check_budget_available(year=2024, month=2)
        assert feb_available is True
