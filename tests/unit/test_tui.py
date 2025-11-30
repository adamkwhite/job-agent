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

    def test_default_is_scrape_and_digest(self):
        """Test that default choice is option 3 (scrape and digest)"""
        # The Prompt.ask is called with default="3"
        with patch("src.tui.Prompt.ask") as mock_prompt:
            mock_prompt.return_value = "3"
            select_action()
            # Verify default parameter is "3"
            args, kwargs = mock_prompt.call_args
            assert kwargs.get("default") == "3"
