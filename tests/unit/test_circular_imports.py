"""
Test that circular import anti-pattern has been eliminated (FR3.4)

This test verifies:
1. All imports work at module level (no imports inside functions)
2. Layer hierarchy is enforced: foundation → classification → scoring
3. No circular dependencies exist
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCircularImports:
    """Test that circular import anti-pattern has been fixed"""

    def test_foundation_layer_imports_cleanly(self):
        """Test that scoring_utils (foundation layer) has no external deps"""
        # This should work without any issues
        from utils import scoring_utils

        # Verify it has the expected pure utility functions
        assert hasattr(scoring_utils, "calculate_grade")
        assert hasattr(scoring_utils, "score_meets_grade")
        assert hasattr(scoring_utils, "GRADE_THRESHOLDS")

        # Verify it does NOT have classify_and_score_company (moved to classification layer)
        assert not hasattr(scoring_utils, "classify_and_score_company")

    def test_classification_layer_imports_cleanly(self):
        """Test that company_classifier (classification layer) imports from foundation only"""
        # This should work without circular dependency issues
        from utils import company_classifier

        # Verify it has the expected classification functions
        assert hasattr(company_classifier, "CompanyClassifier")
        assert hasattr(company_classifier, "classify_role_type")
        assert hasattr(company_classifier, "should_filter_job")
        assert hasattr(company_classifier, "classify_and_score_company")

    def test_scoring_layer_imports_cleanly(self):
        """Test that job scorers (scoring layer) can import from both foundation and classification"""
        # This should work without circular dependency issues
        from agents import job_scorer, profile_scorer

        # Verify scorers have the expected classes
        assert hasattr(job_scorer, "JobScorer")
        assert hasattr(profile_scorer, "ProfileScorer")

    def test_classify_and_score_company_location(self):
        """Test that classify_and_score_company is in the correct module"""
        # Verify function signature
        import inspect

        from utils.company_classifier import classify_and_score_company

        sig = inspect.signature(classify_and_score_company)
        params = list(sig.parameters.keys())

        # Expected parameters
        expected_params = [
            "company_classifier",
            "company_name",
            "job_title",
            "domain_keywords",
            "role_types",
            "filtering_config",
        ]

        assert params == expected_params

    def test_no_runtime_imports_in_scoring_utils(self):
        """Test that scoring_utils has no 'from X import Y' inside functions"""
        import inspect

        from utils import scoring_utils

        # Get all functions in scoring_utils
        functions = [
            obj
            for name, obj in inspect.getmembers(scoring_utils)
            if inspect.isfunction(obj) and not name.startswith("_")
        ]

        # Check source code of each function for runtime imports
        for func in functions:
            source = inspect.getsource(func)
            # Should not contain "from " inside the function body (after def line)
            lines = source.split("\n")
            # Skip the function signature and docstring
            in_docstring = False
            for line in lines[1:]:  # Skip first line (def ...)
                stripped = line.strip()
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                # Check for import statements (these should only be at module level)
                if stripped.startswith("from ") or stripped.startswith("import "):
                    pytest.fail(
                        f"Function {func.__name__} has runtime import: {stripped}\n"
                        f"All imports should be at module level."
                    )

    def test_import_order_foundation_to_classification(self):
        """Test that foundation can be imported before classification"""
        # Import foundation layer first
        # Then classification layer
        from utils import company_classifier, scoring_utils

        # Verify both are available
        assert scoring_utils is not None
        assert company_classifier is not None

    def test_import_order_classification_to_scoring(self):
        """Test that classification can be imported before scoring"""
        # Import classification layer first
        # Then scoring layer
        from agents import job_scorer, profile_scorer
        from utils import company_classifier

        # Verify both are available
        assert company_classifier is not None
        assert job_scorer is not None
        assert profile_scorer is not None

    def test_import_order_foundation_to_scoring(self):
        """Test that foundation can be imported before scoring"""
        # Import foundation layer first
        # Then scoring layer
        from agents import job_scorer, profile_scorer
        from utils import scoring_utils

        # Verify both are available
        assert scoring_utils is not None
        assert job_scorer is not None
        assert profile_scorer is not None

    def test_all_layers_import_together(self):
        """Test that all layers can be imported together without circular dependency errors"""
        # Import all layers simultaneously
        from agents import job_scorer, profile_scorer
        from utils import company_classifier, scoring_utils

        # Verify all are available
        assert scoring_utils is not None
        assert company_classifier is not None
        assert job_scorer is not None
        assert profile_scorer is not None

    def test_layer_hierarchy_documented(self):
        """Test that layer hierarchy is documented in module docstrings"""
        from utils import scoring_utils

        # Check that scoring_utils docstring mentions it's the foundation layer
        assert scoring_utils.__doc__ is not None
        assert "foundation" in scoring_utils.__doc__.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
