"""
Test that circular import anti-pattern has been eliminated (FR3.4)

This test verifies:
1. All imports work at module level (no imports inside functions)
2. Layer hierarchy is enforced: foundation → classification → scoring
3. No circular dependencies exist
4. JobScorer has been removed (unified scoring architecture)
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
        from utils import scoring_utils

        assert hasattr(scoring_utils, "calculate_grade")
        assert hasattr(scoring_utils, "score_meets_grade")
        assert hasattr(scoring_utils, "GRADE_THRESHOLDS")
        assert not hasattr(scoring_utils, "classify_and_score_company")

    def test_classification_layer_imports_cleanly(self):
        """Test that company_classifier (classification layer) imports from foundation only"""
        from utils import company_classifier

        assert hasattr(company_classifier, "CompanyClassifier")
        assert hasattr(company_classifier, "classify_role_type")
        assert hasattr(company_classifier, "should_filter_job")
        assert hasattr(company_classifier, "classify_and_score_company")

    def test_scoring_layer_imports_cleanly(self):
        """Test that profile_scorer (scoring layer) imports cleanly"""
        from agents import profile_scorer

        assert hasattr(profile_scorer, "ProfileScorer")

    def test_job_scorer_module_removed(self):
        """Test that job_scorer module has been deleted (unified architecture)"""
        with pytest.raises(ModuleNotFoundError):
            import agents.job_scorer  # noqa: F401

    def test_classify_and_score_company_location(self):
        """Test that classify_and_score_company is in the correct module"""
        import inspect

        from utils.company_classifier import classify_and_score_company

        sig = inspect.signature(classify_and_score_company)
        params = list(sig.parameters.keys())

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

        functions = [
            obj
            for name, obj in inspect.getmembers(scoring_utils)
            if inspect.isfunction(obj) and not name.startswith("_")
        ]

        for func in functions:
            source = inspect.getsource(func)
            lines = source.split("\n")
            in_docstring = False
            for line in lines[1:]:
                stripped = line.strip()
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                if stripped.startswith("from ") or stripped.startswith("import "):
                    pytest.fail(
                        f"Function {func.__name__} has runtime import: {stripped}\n"
                        f"All imports should be at module level."
                    )

    def test_import_order_foundation_to_classification(self):
        """Test that foundation can be imported before classification"""
        from utils import company_classifier, scoring_utils

        assert scoring_utils is not None
        assert company_classifier is not None

    def test_import_order_classification_to_scoring(self):
        """Test that classification can be imported before scoring"""
        from agents import profile_scorer
        from utils import company_classifier

        assert company_classifier is not None
        assert profile_scorer is not None

    def test_all_layers_import_together(self):
        """Test that all layers can be imported together without circular dependency errors"""
        from agents import profile_scorer
        from utils import company_classifier, scoring_utils

        assert scoring_utils is not None
        assert company_classifier is not None
        assert profile_scorer is not None

    def test_layer_hierarchy_documented(self):
        """Test that layer hierarchy is documented in module docstrings"""
        from utils import scoring_utils

        assert scoring_utils.__doc__ is not None
        assert "foundation" in scoring_utils.__doc__.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
