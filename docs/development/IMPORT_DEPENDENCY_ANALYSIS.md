# Import Dependency Analysis - FR3.4 Circular Import Fix

## Current State (BEFORE FIX)

### Anti-Pattern Identified
**Location**: `src/utils/scoring_utils.py` line 42
```python
def classify_and_score_company(...):
    # Import here to avoid circular dependency
    from utils.company_classifier import should_filter_job  # ❌ ANTI-PATTERN
```

### Current Import Chain
```
scoring_utils.py (Foundation Layer - VIOLATED)
    └─> imports should_filter_job from company_classifier.py at runtime

company_classifier.py (Classification Layer)
    └─> No imports from scoring_utils ✓

job_scorer.py (Scoring Layer)
    ├─> imports from scoring_utils
    └─> imports CompanyClassifier from company_classifier

profile_scorer.py (Scoring Layer)
    ├─> imports from scoring_utils
    └─> imports CompanyClassifier from company_classifier
```

### Why This Is Circular
1. `scoring_utils.py` should be the foundation (no external deps)
2. But `classify_and_score_company()` in `scoring_utils.py` imports from `company_classifier.py`
3. This creates a circular dependency if anyone tries to import `scoring_utils` from `company_classifier`
4. Current "fix" is to import inside the function - this is an anti-pattern

## Target State (AFTER FIX)

### Proper Layer Hierarchy

**Layer 1: Foundation** - `scoring_utils.py`
- Pure utility functions only
- No external dependencies (except stdlib)
- Functions:
  - `calculate_grade(score: int) -> str`
  - `score_meets_grade(score: int, min_grade: str) -> bool`
  - `GRADE_THRESHOLDS` constant

**Layer 2: Classification** - `company_classifier.py`
- Can import from foundation layer (scoring_utils)
- Contains:
  - `CompanyClassifier` class
  - `classify_role_type()` function
  - `should_filter_job()` function
  - **NEW**: `classify_and_score_company()` function (moved from scoring_utils)

**Layer 3: Scoring** - `job_scorer.py`, `profile_scorer.py`
- Can import from both foundation and classification layers
- These are the top-level consumers

### New Import Chain
```
scoring_utils.py (Foundation Layer) ✓
    └─> No external dependencies (only stdlib)

company_classifier.py (Classification Layer) ✓
    └─> can import from scoring_utils (foundation)
    └─> contains classify_and_score_company() (moved from scoring_utils)

job_scorer.py (Scoring Layer) ✓
    ├─> imports from scoring_utils (foundation)
    └─> imports from company_classifier (classification)

profile_scorer.py (Scoring Layer) ✓
    ├─> imports from scoring_utils (foundation)
    └─> imports from company_classifier (classification)
```

## Implementation Plan

### Step 1: Move `classify_and_score_company()` to `company_classifier.py`
- Move function from `scoring_utils.py` to `company_classifier.py`
- Keep all imports at module level (no imports inside functions)
- Function naturally belongs in classification layer since it uses `CompanyClassifier`

### Step 2: Update Imports in Scorers
- `job_scorer.py`: Change import to get `classify_and_score_company` from `company_classifier`
- `profile_scorer.py`: Change import to get `classify_and_score_company` from `company_classifier`

### Step 3: Clean up `scoring_utils.py`
- Remove `classify_and_score_company()` function
- Remove TYPE_CHECKING import of CompanyClassifier
- Keep only pure utility functions:
  - `calculate_grade()`
  - `score_meets_grade()`
  - `GRADE_THRESHOLDS`

### Step 4: Verify No Circular Dependencies
- Create `tests/unit/test_circular_imports.py`
- Test that all imports work at module level
- Test import order (foundation → classification → scoring)
- Verify no circular imports exist

## Benefits
1. ✅ No imports inside functions (proper Python style)
2. ✅ Clear layer hierarchy (foundation → classification → scoring)
3. ✅ `classify_and_score_company()` is in the right place (classification layer)
4. ✅ No circular dependencies possible
5. ✅ Easier to reason about module dependencies

## Risk Assessment
- **Risk Level**: LOW
- **Reason**: Pure refactoring, no logic changes
- **Verification**: All 1,275+ existing tests must pass
