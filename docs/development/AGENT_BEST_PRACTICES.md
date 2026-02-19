# Agent Best Practices

Guidelines for AI agents (Claude Code, overnight agents) working on this codebase to prevent common pitfalls and ensure high-quality automated changes.

## Function Signature Modifications

**Problem:** When modifying function signatures (adding/removing/changing parameters), agents may miss updating all callers, especially test mocks.

**Example Issue:** PR #297 - Agent removed unused parameters but didn't update test mocks, causing CI failures.

### Safe Refactoring Workflow

When modifying any function signature, **ALWAYS** follow these steps:

#### 1. Make the Signature Change
```python
# Before
def _handle_duplicate_job(job, job_dict, score, grade, breakdown, classification_metadata, stats):
    ...

# After
def _handle_duplicate_job(job, job_dict, stats):
    ...
```

#### 2. Find ALL Callers (Critical Step)
Use Grep to search the **entire codebase** (both `src/` and `tests/`):

```bash
# Search for function name across all Python files
grep -r "_handle_duplicate_job" src/ tests/ --include="*.py"
```

**Key points:**
- Search in **both** `src/` AND `tests/` directories
- Don't assume you know all callers - search comprehensively
- Check for partial matches (e.g., method calls, imports, mocks)

#### 3. Update Each Caller
Review **every** match from grep and update to match new signature:

```python
# Test mock - BEFORE
scraper._handle_duplicate_job(
    job=job,
    job_dict=job_dict,
    score=75,  # ← REMOVE
    grade="C+",  # ← REMOVE
    breakdown={...},  # ← REMOVE
    classification_metadata={...},  # ← REMOVE
    stats=stats,
)

# Test mock - AFTER
scraper._handle_duplicate_job(
    job=job,
    job_dict=job_dict,
    stats=stats,
)
```

#### 4. Run Affected Tests
**Before committing**, run tests for the modified module:

```bash
# Run specific test file
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_<module>.py -v

# Example
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_multi_profile_duplicate_scoring.py -v
```

**Success criteria:**
- All tests must pass (exit code = 0)
- No TypeErrors about unexpected arguments
- No missing required parameter errors

#### 5. Commit Only If Tests Pass
```bash
# Only commit if step 4 succeeded
git add <files>
git commit -m "refactor: Update function signature and all callers"
```

## Common Grep Patterns for Refactoring

### Finding Function Callers
```bash
# Direct function calls
grep -r "function_name(" src/ tests/ --include="*.py"

# Method calls (instance.method)
grep -r "\\.method_name(" src/ tests/ --include="*.py"

# Imports
grep -r "from .* import.*function_name" src/ tests/ --include="*.py"
```

### Finding Class References
```bash
# Class instantiation
grep -r "ClassName(" src/ tests/ --include="*.py"

# Class inheritance
grep -r "class.*ClassName" src/ tests/ --include="*.py"
```

### Finding Variable/Constant References
```bash
# All references to a constant
grep -r "CONSTANT_NAME" src/ tests/ --include="*.py"
```

## Parameter Removal Checklist

When removing function parameters, verify:

- [ ] Function signature updated in source file
- [ ] Grep search performed for all callers (src/ + tests/)
- [ ] All callers updated to match new signature
- [ ] Default parameter values removed if no longer needed
- [ ] Docstring updated to reflect new parameters
- [ ] Tests run successfully for modified module
- [ ] Type hints updated (if applicable)
- [ ] No TypeErrors in test output

## Test Mock Best Practices

### When Mocking Functions with Changed Signatures

**Always update mock calls** to match the current function signature:

```python
# ✅ GOOD - Mock matches actual signature
mocker.patch.object(scraper, '_handle_duplicate_job')
scraper._handle_duplicate_job(job=job, job_dict=job_dict, stats=stats)

# ❌ BAD - Mock includes removed parameters
scraper._handle_duplicate_job(
    job=job,
    job_dict=job_dict,
    score=75,  # Parameter no longer exists!
    stats=stats
)
```

### Test Discovery Pattern

When modifying a function, find its tests:

```bash
# Find test files that test the modified module
ls tests/unit/test_<module_name>.py

# Search for test methods that call the function
grep -r "def test.*" tests/unit/test_<module_name>.py | grep -i <function_name>
```

## Refactoring Safety Principles

1. **Search First, Change Second** - Always grep for references before modifying signatures
2. **Tests Are Callers Too** - Don't forget test mocks and fixtures
3. **Verify Before Commit** - Run affected tests locally before pushing
4. **Fail Fast** - If tests fail, investigate immediately - don't skip or ignore
5. **Document Changes** - Include "Updated all callers" in commit messages

## Why This Matters

**Without this workflow:**
- ❌ Test failures in CI (discovered late)
- ❌ Manual cleanup required
- ❌ Additional PR iterations
- ❌ Wasted time debugging

**With this workflow:**
- ✅ Issues caught before CI
- ✅ Clean, passing PRs on first push
- ✅ Fewer manual interventions
- ✅ Higher confidence in automated changes

## Example: Complete Refactoring Workflow

```bash
# 1. Modify function signature in src/jobs/company_scraper.py
#    Remove unused parameters from _handle_duplicate_job()

# 2. Find all callers
grep -r "_handle_duplicate_job" src/ tests/ --include="*.py"
# Output:
# src/jobs/company_scraper.py:372:    def _handle_duplicate_job(job, job_dict, stats):
# tests/unit/test_multi_profile_duplicate_scoring.py:372:    mario_scraper._handle_duplicate_job(

# 3. Update test mock (line 372 in test file)
#    Remove: score, grade, breakdown, classification_metadata parameters

# 4. Run tests
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_multi_profile_duplicate_scoring.py -v
# Output: 11 passed ✅

# 5. Commit
git add src/jobs/company_scraper.py tests/unit/test_multi_profile_duplicate_scoring.py
git commit -m "refactor: Remove unused params from _handle_duplicate_job

Removed unused parameters: score, grade, breakdown, classification_metadata
Updated all callers including test mocks.
All tests passing."
```

## Related Documentation

- [Testing Guide](TESTING.md) - Comprehensive guide to writing and running tests
- [Scoring Update Checklist](SCORING_UPDATE_CHECKLIST.md) - Specific workflow for scoring changes
- GitHub Issue #300 - Workflow improvement for signature changes

## Revision History

- 2026-02-18: Initial version (based on learnings from PR #297)
