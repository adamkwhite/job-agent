"""
Tests for TUI (Terminal User Interface)
"""

from unittest.mock import patch

from src.tui import select_action


class TestSelectAction:
    """Test action selection functionality"""

    def test_scrape_action(self):
        """Test scrape only action selection"""
        with patch("src.tui.Prompt.ask", return_value="1"):
            result = select_action()
            assert result == "scrape"

    def test_digest_action(self):
        """Test send digest action selection"""
        with patch("src.tui.Prompt.ask", return_value="2"):
            result = select_action()
            assert result == "digest"

    def test_both_action(self):
        """Test scrape and digest action selection"""
        with patch("src.tui.Prompt.ask", return_value="3"):
            result = select_action()
            assert result == "both"

    def test_quit_action(self):
        """Test quit action selection"""
        with patch("src.tui.Prompt.ask", return_value="q"):
            result = select_action()
            assert result is None

    def test_back_action(self):
        """Test back action selection"""
        with patch("src.tui.Prompt.ask", return_value="b"):
            result = select_action()
            assert result == "back"

    def test_criteria_action(self):
        """Test view criteria action selection"""
        with patch("src.tui.Prompt.ask", return_value="c"):
            result = select_action()
            assert result == "criteria"

    def test_metrics_action(self):
        """Test LLM metrics action selection"""
        with patch("src.tui.Prompt.ask", return_value="m"):
            result = select_action()
            assert result == "metrics"

    def test_default_is_scrape_and_digest(self):
        """Test that default choice is option 3 (scrape and digest)"""
        # The Prompt.ask is called with default="3"
        with patch("src.tui.Prompt.ask") as mock_prompt:
            mock_prompt.return_value = "3"
            select_action()
            # Verify default parameter is "3"
            args, kwargs = mock_prompt.call_args
            assert kwargs.get("default") == "3"


class TestHandleSecondaryAction:
    """Test _handle_secondary_action routes correctly."""

    def test_metrics_action_calls_show_extraction_metrics(self):
        """Metrics action should call show_extraction_metrics."""
        from src.tui import _handle_secondary_action

        with patch("src.tui.show_extraction_metrics") as mock_metrics:
            result = _handle_secondary_action("metrics")
            assert result is True
            mock_metrics.assert_called_once()

    def test_failures_action_calls_review_llm_failures(self):
        """Failures action should call review_llm_failures."""
        from src.tui import _handle_secondary_action

        with patch("src.tui.review_llm_failures") as mock_failures:
            result = _handle_secondary_action("failures")
            assert result is True
            mock_failures.assert_called_once()

    def test_scrape_action_returns_none(self):
        """Main workflow actions should return None."""
        from src.tui import _handle_secondary_action

        result = _handle_secondary_action("scrape")
        assert result is None
