"""
Tests for centralized score thresholds module.

This test suite ensures that the Grade enum and threshold functions
provide consistent scoring behavior across the codebase.
"""

import pytest

from utils.score_thresholds import (
    Grade,
    calculate_grade,
    get_grade_threshold,
    score_meets_grade,
)


class TestGradeEnum:
    """Test the Grade enum values and structure."""

    def test_grade_enum_values(self):
        """Test that Grade enum has correct threshold values."""
        assert Grade.A.value == 85
        assert Grade.B.value == 70
        assert Grade.C.value == 55
        assert Grade.D.value == 40
        assert Grade.F.value == 0

    def test_grade_enum_ordering(self):
        """Test that grade thresholds are in descending order."""
        assert Grade.A.value > Grade.B.value
        assert Grade.B.value > Grade.C.value
        assert Grade.C.value > Grade.D.value
        assert Grade.D.value > Grade.F.value

    def test_grade_enum_membership(self):
        """Test that all expected grades exist in enum."""
        grade_names = [g.name for g in Grade]
        assert "A" in grade_names
        assert "B" in grade_names
        assert "C" in grade_names
        assert "D" in grade_names
        assert "F" in grade_names

    def test_grade_enum_access_by_name(self):
        """Test that grades can be accessed by name."""
        assert Grade["A"].value == 85
        assert Grade["B"].value == 70
        assert Grade["C"].value == 55
        assert Grade["D"].value == 40
        assert Grade["F"].value == 0


class TestCalculateGrade:
    """Test the calculate_grade function."""

    def test_a_grade_boundary(self):
        """Test A grade threshold (85+)."""
        assert calculate_grade(85) == "A"
        assert calculate_grade(86) == "A"
        assert calculate_grade(100) == "A"
        assert calculate_grade(110) == "A"  # Above max (with bonuses)

    def test_b_grade_boundary(self):
        """Test B grade threshold (70-84)."""
        assert calculate_grade(70) == "B"
        assert calculate_grade(75) == "B"
        assert calculate_grade(84) == "B"

    def test_c_grade_boundary(self):
        """Test C grade threshold (55-69)."""
        assert calculate_grade(55) == "C"
        assert calculate_grade(60) == "C"
        assert calculate_grade(69) == "C"

    def test_d_grade_boundary(self):
        """Test D grade threshold (40-54)."""
        assert calculate_grade(40) == "D"
        assert calculate_grade(45) == "D"
        assert calculate_grade(54) == "D"

    def test_f_grade_boundary(self):
        """Test F grade threshold (<40)."""
        assert calculate_grade(0) == "F"
        assert calculate_grade(20) == "F"
        assert calculate_grade(39) == "F"

    def test_boundary_transitions(self):
        """Test that grades transition correctly at boundaries."""
        # Just below each threshold should be next lower grade
        assert calculate_grade(84) == "B"  # One below A
        assert calculate_grade(69) == "C"  # One below B
        assert calculate_grade(54) == "D"  # One below C
        assert calculate_grade(39) == "F"  # One below D

        # At threshold should be that grade
        assert calculate_grade(85) == "A"
        assert calculate_grade(70) == "B"
        assert calculate_grade(55) == "C"
        assert calculate_grade(40) == "D"

    def test_negative_scores(self):
        """Test that negative scores are handled (should be F)."""
        assert calculate_grade(-1) == "F"
        assert calculate_grade(-100) == "F"

    def test_midpoint_scores(self):
        """Test scores in the middle of each grade range."""
        assert calculate_grade(92) == "A"  # Mid A range
        assert calculate_grade(77) == "B"  # Mid B range
        assert calculate_grade(62) == "C"  # Mid C range
        assert calculate_grade(47) == "D"  # Mid D range
        assert calculate_grade(20) == "F"  # Mid F range


class TestScoreMeetsGrade:
    """Test the score_meets_grade function."""

    def test_meets_a_grade(self):
        """Test checking if score meets A grade."""
        assert score_meets_grade(85, "A") is True
        assert score_meets_grade(90, "A") is True
        assert score_meets_grade(84, "A") is False
        assert score_meets_grade(70, "A") is False

    def test_meets_b_grade(self):
        """Test checking if score meets B grade."""
        assert score_meets_grade(70, "B") is True
        assert score_meets_grade(75, "B") is True
        assert score_meets_grade(85, "B") is True  # A grade also meets B
        assert score_meets_grade(69, "B") is False

    def test_meets_c_grade(self):
        """Test checking if score meets C grade."""
        assert score_meets_grade(55, "C") is True
        assert score_meets_grade(60, "C") is True
        assert score_meets_grade(70, "C") is True  # B grade also meets C
        assert score_meets_grade(54, "C") is False

    def test_meets_d_grade(self):
        """Test checking if score meets D grade."""
        assert score_meets_grade(40, "D") is True
        assert score_meets_grade(50, "D") is True
        assert score_meets_grade(70, "D") is True  # Higher grades meet D
        assert score_meets_grade(39, "D") is False

    def test_meets_f_grade(self):
        """Test checking if score meets F grade."""
        # All scores meet F grade (lowest threshold)
        assert score_meets_grade(0, "F") is True
        assert score_meets_grade(20, "F") is True
        assert score_meets_grade(100, "F") is True

    def test_invalid_grade(self):
        """Test that invalid grade raises KeyError."""
        with pytest.raises(KeyError):
            score_meets_grade(70, "X")

        with pytest.raises(KeyError):
            score_meets_grade(70, "Z")

    def test_case_sensitivity(self):
        """Test that grade strings are case-sensitive."""
        # Lower case should fail
        with pytest.raises(KeyError):
            score_meets_grade(70, "b")

        # Upper case should succeed
        assert score_meets_grade(70, "B") is True


class TestGetGradeThreshold:
    """Test the get_grade_threshold function."""

    def test_get_all_thresholds(self):
        """Test retrieving all grade thresholds."""
        assert get_grade_threshold("A") == 85
        assert get_grade_threshold("B") == 70
        assert get_grade_threshold("C") == 55
        assert get_grade_threshold("D") == 40
        assert get_grade_threshold("F") == 0

    def test_invalid_grade(self):
        """Test that invalid grade raises KeyError."""
        with pytest.raises(KeyError):
            get_grade_threshold("X")

        with pytest.raises(KeyError):
            get_grade_threshold("Z")

    def test_case_sensitivity(self):
        """Test that grade strings are case-sensitive."""
        # Lower case should fail
        with pytest.raises(KeyError):
            get_grade_threshold("a")

        # Upper case should succeed
        assert get_grade_threshold("A") == 85


class TestIntegration:
    """Integration tests ensuring consistency across functions."""

    def test_threshold_and_calculation_consistency(self):
        """Test that get_grade_threshold and calculate_grade are consistent."""
        # Scores at threshold should get that grade
        for grade_name in ["A", "B", "C", "D"]:
            threshold = get_grade_threshold(grade_name)
            assert calculate_grade(threshold) == grade_name

    def test_meets_grade_and_calculation_consistency(self):
        """Test that score_meets_grade matches calculate_grade results."""
        test_scores = [0, 39, 40, 54, 55, 69, 70, 84, 85, 100]

        for score in test_scores:
            grade = calculate_grade(score)
            # Score should meet its own grade
            assert score_meets_grade(score, grade) is True

            # Score should meet all lower grades
            grade_order = ["A", "B", "C", "D", "F"]
            grade_index = grade_order.index(grade)
            for lower_grade in grade_order[grade_index:]:
                assert score_meets_grade(score, lower_grade) is True

    def test_notification_threshold_b_grade(self):
        """Test that B grade (70) is correct threshold for notifications."""
        # This documents the business rule: notifications sent for B+ grades
        notification_threshold = Grade.B.value
        assert notification_threshold == 70

        # Scores >= 70 should trigger notifications
        assert score_meets_grade(70, "B") is True
        assert score_meets_grade(71, "B") is True
        assert score_meets_grade(85, "B") is True

        # Scores < 70 should not
        assert score_meets_grade(69, "B") is False
        assert score_meets_grade(55, "B") is False

    def test_digest_threshold_c_grade(self):
        """Test that C grade (55) is correct threshold for digests."""
        # This documents the business rule: digests include C+ grades
        digest_threshold = Grade.C.value
        assert digest_threshold == 55

        # Scores >= 55 should be in digest
        assert score_meets_grade(55, "C") is True
        assert score_meets_grade(60, "C") is True
        assert score_meets_grade(70, "C") is True

        # Scores < 55 should not
        assert score_meets_grade(54, "C") is False
        assert score_meets_grade(40, "C") is False

    def test_grade_ranges_for_display(self):
        """Test grade ranges for UI display strings."""
        # These are the ranges shown in emails/TUI
        assert Grade.A.value == 85  # "85+"
        assert Grade.B.value == 70  # "70-84"
        assert Grade.C.value == 55  # "55-69"
        assert Grade.D.value == 40  # "40-54"
        assert Grade.F.value == 0  # "<40"

        # Verify ranges don't overlap
        assert Grade.B.value < Grade.A.value
        assert Grade.C.value < Grade.B.value
        assert Grade.D.value < Grade.C.value
        assert Grade.F.value < Grade.D.value
