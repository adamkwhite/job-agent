"""Models package

Provides unified data models for the job agent.

This package directory coexists with src/models.py for backwards compatibility.
We re-export models from models.py so existing code continues to work.
"""

# Import from this package
# Re-export from the old models.py file for backwards compatibility
# Use importlib to avoid Python treating src/models as this package
import importlib.util
from pathlib import Path

from .company import Company

_models_file = Path(__file__).parent.parent / "models.py"
_spec = importlib.util.spec_from_file_location("_old_models", _models_file)
if _spec and _spec.loader:
    _old_models = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_old_models)
    OpportunityData = _old_models.OpportunityData
    EnrichmentResult = _old_models.EnrichmentResult
    ParserResult = _old_models.ParserResult
else:
    # Fallback - will cause errors but at least won't break imports
    OpportunityData = None  # type: ignore
    EnrichmentResult = None  # type: ignore
    ParserResult = None  # type: ignore

__all__ = ["Company", "OpportunityData", "EnrichmentResult", "ParserResult"]
