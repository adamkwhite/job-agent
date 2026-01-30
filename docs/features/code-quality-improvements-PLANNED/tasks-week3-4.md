# Week 3-4: Consolidation & Architecture - Task List

**PRD:** `prd.md` (Sections FR3.1 - FR3.5)
**Status:** PLANNED
**Created:** 2026-01-28
**Mode:** Hybrid (Parallel within groups, approval between groups)

---

## Execution Strategy

**Mode:** Hybrid Parallel Execution
**Total Groups:** 3 execution groups
**Parallel Opportunities:** Group 1 has 3 independent tasks

**Time Estimates:**
- **Serial Execution:** ~18 hours
- **Parallel Execution:** ~13 hours
- **Time Savings:** 5 hours (28% faster)

**Approach:**
- Group 1: Run 3 tasks in parallel (low risk, independent)
- Group 2: Run 1 task supervised (high risk, major refactoring)
- Group 3: Run 1 task after Group 2 (depends on unified scorers)

---

## Task Dependency Graph

```
Group 1 (Parallel Safe - 3 agents):
├─ FR3.3: Add Pydantic Config Validation
│  Files: pydantic_models.py (NEW), profile_manager.py
│  Risk: LOW (new validation layer)
│  Time: 3-4 hours
│
├─ FR3.4: Fix Circular Dependency
│  Files: scoring_utils.py, company_classifier.py (imports only)
│  Risk: LOW (mechanical refactoring)
│  Time: 2-3 hours
│
└─ FR3.5: Centralize Score Thresholds
   Files: score_thresholds.py (NEW), 8+ files using hardcoded values
   Risk: LOW (extract constants)
   Time: 2-3 hours

Group 2 (Serial - Supervised):
└─ FR3.1: Merge JobScorer + ProfileScorer
   Files: base_scorer.py (NEW), job_scorer.py, profile_scorer.py
   Dependencies: NONE (but should run on clean main after Group 1)
   Risk: HIGH (589 lines refactoring, core business logic)
   Time: 5-6 hours
   Recommendation: SUPERVISED execution, not autonomous

Group 3 (Serial - Depends on FR3.1):
└─ FR3.2: Create KeywordMatcher Utility
   Files: keyword_matcher.py (NEW), job_scorer.py, profile_scorer.py
   Dependencies: FR3.1 (needs unified scorer interface)
   Risk: MEDIUM (changes scoring logic)
   Time: 3-4 hours
```

**Critical Path:** Group 1 → Group 2 → Group 3
**Bottleneck:** FR3.1 (can't be parallelized, highest risk)

---

## Relevant Files

### Group 1 Files (No Conflicts)

**FR3.3: Pydantic Config Validation**
- `src/utils/pydantic_models.py` - NEW - Pydantic model definitions
- `src/utils/profile_manager.py` - MODIFIED - Use Pydantic for loading
- `tests/unit/test_pydantic_models.py` - NEW - Model validation tests
- `profiles/wes.json` - UNCHANGED - Test with existing profiles
- `profiles/adam.json` - UNCHANGED - Test with existing profiles
- `profiles/eli.json` - UNCHANGED - Test with existing profiles

**FR3.4: Fix Circular Dependency**
- `src/utils/scoring_utils.py` - MODIFIED - Restructure into foundation layer
- `src/utils/company_classifier.py` - MODIFIED - Move to classification layer
- `src/agents/job_scorer.py` - MODIFIED - Import from foundation
- `src/agents/profile_scorer.py` - MODIFIED - Import from foundation
- `tests/unit/test_circular_imports.py` - NEW - Verify no cycles

**FR3.5: Centralize Score Thresholds**
- `src/utils/score_thresholds.py` - NEW - Grade enum and utilities
- `src/agents/job_scorer.py` - MODIFIED - Use Grade enum
- `src/agents/profile_scorer.py` - MODIFIED - Use Grade enum
- `src/send_profile_digest.py` - MODIFIED - Use Grade enum
- `src/tui.py` - MODIFIED - Use Grade enum
- `tests/unit/test_score_thresholds.py` - NEW - Grade threshold tests

### Group 2 Files (Major Refactoring)

**FR3.1: Merge JobScorer + ProfileScorer**
- `src/agents/base_scorer.py` - NEW - Shared scoring logic (300+ lines)
- `src/agents/job_scorer.py` - MODIFIED - Extend BaseScorer (589 → ~200 lines)
- `src/agents/profile_scorer.py` - MODIFIED - Extend BaseScorer (303 → ~150 lines)
- `tests/unit/test_base_scorer.py` - NEW - BaseScorer tests (50+ tests)
- `tests/unit/test_job_scorer.py` - MODIFIED - Verify unchanged behavior
- `tests/unit/test_profile_scorer.py` - MODIFIED - Verify unchanged behavior

### Group 3 Files (Depends on Group 2)

**FR3.2: Create KeywordMatcher Utility**
- `src/utils/keyword_matcher.py` - NEW - Centralized keyword matching
- `src/agents/base_scorer.py` - MODIFIED - Use KeywordMatcher
- `tests/unit/test_keyword_matcher.py` - NEW - Matcher tests (20+ tests)

### Shared Files (Updated After All Groups)
- `CHANGELOG.md` - Updated at end
- `docs/features/code-quality-improvements-PLANNED/status.md` - Updated per group
- `docs/features/code-quality-improvements-PLANNED/tasks-week3-4.md` - This file

---

## Tasks

### Group 1: Independent Utilities (Parallel Execution)

- [ ] 3.0 Add Pydantic Configuration Validation (FR3.3)
  - **Files:** `pydantic_models.py` (NEW), `profile_manager.py`
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - **Risk:** LOW
  - **Time Estimate:** 3-4 hours
  - [ ] 3.1 Create `src/utils/pydantic_models.py` with model definitions
    - ProfileConfig, ScoringConfig, SeniorityLevel models
    - Validators for seniority totals, grade formats
    - JSON schema generation for documentation
  - [ ] 3.2 Integrate Pydantic into `profile_manager.py`
    - Update Profile class to use Pydantic models
    - Add validation on profile load
    - Maintain backwards compatibility
  - [ ] 3.3 Create comprehensive tests (`test_pydantic_models.py`)
    - Test valid profile loading
    - Test validation errors for missing fields
    - Test validation errors for invalid types
    - Test seniority total validator (must not exceed 30)
  - [ ] 3.4 Test with all existing profiles (Wes, Adam, Eli)
    - Verify all profiles load correctly
    - No behavioral changes to scoring
  - [ ] 3.5 Run full test suite (1,275+ tests must pass)
  - [ ] 3.6 Create PR and link to PRD
  - [ ] 3.7 Verify SonarCloud quality gate passes

- [ ] 4.0 Fix Circular Dependency Workaround (FR3.4)
  - **Files:** `scoring_utils.py`, `company_classifier.py`, scorers
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - **Risk:** LOW
  - **Time Estimate:** 2-3 hours
  - [ ] 4.1 Analyze current import structure
    - Document current circular dependency pattern
    - Identify foundation vs classification vs scoring layers
  - [ ] 4.2 Restructure `scoring_utils.py` as foundation layer
    - Move all imports to module level
    - Remove "import inside function" workarounds
    - Keep only utility functions (no external dependencies)
  - [ ] 4.3 Update `company_classifier.py` as classification layer
    - Import from scoring_utils (foundation)
    - Ensure no reverse dependencies
  - [ ] 4.4 Update scorers to import from proper layers
    - job_scorer.py imports from both foundation and classification
    - profile_scorer.py imports from both foundation and classification
  - [ ] 4.5 Create test to verify no circular imports
    - `test_circular_imports.py` with import order validation
  - [ ] 4.6 Run full test suite (1,275+ tests must pass)
  - [ ] 4.7 Create PR and link to PRD
  - [ ] 4.8 Verify SonarCloud quality gate passes

- [ ] 5.0 Centralize Score Thresholds (FR3.5)
  - **Files:** `score_thresholds.py` (NEW), 8+ files with hardcoded values
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - **Risk:** LOW
  - **Time Estimate:** 2-3 hours
  - [ ] 5.1 Create `src/utils/score_thresholds.py` with Grade enum
    - Grade enum (A=85, B=70, C=55, D=40, F=0)
    - calculate_grade(score: int) -> str
    - score_meets_grade(score: int, min_grade: str) -> bool
  - [ ] 5.2 Update `src/agents/job_scorer.py` to use Grade enum
    - Replace hardcoded _calculate_grade() implementation
    - Import from score_thresholds
  - [ ] 5.3 Update `src/agents/profile_scorer.py` to use Grade enum
    - Import from score_thresholds
    - Remove any hardcoded threshold values
  - [ ] 5.4 Update `src/send_profile_digest.py` to use Grade enum
    - Replace threshold comparisons with Grade.*.value
  - [ ] 5.5 Update `src/tui.py` to use Grade enum
    - Display logic using Grade enum values
  - [ ] 5.6 Search for and update any other hardcoded thresholds
    - `git grep -n "85\|70\|55\|40" src/` to find candidates
    - Update 4-6 additional files identified
  - [ ] 5.7 Create tests (`test_score_thresholds.py`)
    - Test Grade enum values
    - Test calculate_grade() boundaries
    - Test score_meets_grade() logic
  - [ ] 5.8 Run full test suite (1,275+ tests must pass)
  - [ ] 5.9 Create PR and link to PRD
  - [ ] 5.10 Verify SonarCloud quality gate passes

### Group 2: Major Refactoring (Serial, Supervised)

- [ ] 1.0 Merge JobScorer + ProfileScorer into BaseScorer (FR3.1)
  - **Files:** `base_scorer.py` (NEW), `job_scorer.py`, `profile_scorer.py`
  - **Dependencies:** Group 1 complete (clean main branch)
  - **Parallel Safe:** ❌ No (major refactoring, needs supervision)
  - **Execution Group:** Group 2
  - **Risk:** HIGH (589 lines duplication, core logic)
  - **Time Estimate:** 5-6 hours
  - **Recommendation:** SUPERVISED execution, not fully autonomous
  - [ ] 1.1 Design BaseScorer interface
    - Identify all shared methods between JobScorer and ProfileScorer
    - Document abstract vs concrete methods
    - Plan inheritance hierarchy
  - [ ] 1.2 Create `src/agents/base_scorer.py` with shared logic
    - Abstract base class with shared methods:
      - _score_seniority()
      - _score_domain()
      - _score_location()
      - _score_technical_keywords()
      - _calculate_grade()
      - score_job() orchestration
    - Constructor takes profile dict
    - Shared initialization (company_classifier, keyword loading)
  - [ ] 1.3 Refactor `job_scorer.py` to extend BaseScorer
    - Change: class JobScorer(BaseScorer)
    - Override __init__ to load hardcoded Wes profile
    - Remove duplicate methods (now in BaseScorer)
    - Keep only Wes-specific logic
    - Target: 589 lines → ~200 lines
  - [ ] 1.4 Refactor `profile_scorer.py` to extend BaseScorer
    - Change: class ProfileScorer(BaseScorer)
    - Override __init__ to accept Profile parameter
    - Remove duplicate methods (now in BaseScorer)
    - Keep only dynamic profile logic
    - Target: 303 lines → ~150 lines
  - [ ] 1.5 Create comprehensive BaseScorer tests
    - `tests/unit/test_base_scorer.py` with 50+ tests
    - Test all shared methods in isolation
    - Test score_job() orchestration
    - 100% coverage on BaseScorer
  - [ ] 1.6 Run JobScorer tests (verify no behavior change)
    - All existing JobScorer tests must pass
    - No score changes for any job
  - [ ] 1.7 Run ProfileScorer tests (verify no behavior change)
    - All existing ProfileScorer tests must pass
    - No score changes for any profile
  - [ ] 1.8 Run full test suite (1,275+ tests must pass)
  - [ ] 1.9 Create PR and link to PRD
  - [ ] 1.10 Verify SonarCloud quality gate passes
  - [ ] 1.11 **CHECKPOINT:** Review with user before merge
    - Significant refactoring requires approval
    - Verify zero behavioral changes

### Group 3: Dependent Refactoring (Serial)

- [ ] 2.0 Create KeywordMatcher Utility Class (FR3.2)
  - **Files:** `keyword_matcher.py` (NEW), `base_scorer.py`
  - **Dependencies:** FR3.1 complete (needs BaseScorer)
  - **Parallel Safe:** ❌ No (depends on unified scorers)
  - **Execution Group:** Group 3
  - **Risk:** MEDIUM
  - **Time Estimate:** 3-4 hours
  - [ ] 2.1 Design KeywordMatcher interface
    - matches(text: str, threshold: float) -> list[str]
    - count_matches(text: str) -> int
    - has_any(text: str) -> bool
    - Support for fuzzy matching (threshold 0.0-1.0)
  - [ ] 2.2 Create `src/utils/keyword_matcher.py`
    - KeywordMatcher class implementation
    - Case-insensitive matching by default
    - Fuzzy matching using difflib (optional)
    - Phrase matching support ("machine learning" as single keyword)
  - [ ] 2.3 Update `base_scorer.py` to use KeywordMatcher
    - Replace manual keyword loops with matcher.has_any()
    - Use matcher.count_matches() for bonus calculations
    - Update all domain/role/technical keyword checking
  - [ ] 2.4 Migrate scorers to use KeywordMatcher
    - Both JobScorer and ProfileScorer inherit from BaseScorer
    - Should automatically use KeywordMatcher
    - Remove any remaining manual keyword checks
  - [ ] 2.5 Create comprehensive tests (`test_keyword_matcher.py`)
    - Test exact matching
    - Test case insensitivity
    - Test fuzzy matching with various thresholds
    - Test phrase matching
    - Test performance (should be <10ms for 100 keywords)
    - 20+ test cases, 100% coverage
  - [ ] 2.6 Run full test suite (1,275+ tests must pass)
  - [ ] 2.7 Create PR and link to PRD
  - [ ] 2.8 Verify SonarCloud quality gate passes

---

## Notes

### Execution Recommendations

**Group 1 (Parallel):**
- ✅ Safe for autonomous execution
- ✅ Can run while you sleep/work
- ✅ 3 independent PRs created
- ✅ Low risk of breaking changes

**Group 2 (Supervised):**
- ⚠️ **Do NOT run fully autonomous**
- ⚠️ Review BaseScorer design before implementation
- ⚠️ Major refactoring needs careful validation
- ⚠️ Consider pair programming approach

**Group 3 (Standard):**
- ✅ Can run autonomous after Group 2 merged
- ✅ Depends on unified scorers
- ✅ Medium complexity, well-defined

### Test Coverage Requirements

- All new code: 80%+ coverage (SonarCloud requirement)
- BaseScorer: 100% coverage (core business logic)
- KeywordMatcher: 100% coverage (utility class)
- Pydantic models: 90%+ coverage (validation logic)

### Behavioral Changes

**CRITICAL:** Zero behavioral changes allowed!
- All 1,275+ tests must pass after each task
- No score changes for any job in any profile
- No changes to job filtering logic
- No changes to digest generation

**Verification:**
```bash
# Before starting any task
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v > baseline_tests.txt

# After completing task
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v > task_tests.txt

# Compare
diff baseline_tests.txt task_tests.txt
# Should show: 0 differences (or only new tests added)
```

### Risk Mitigation

**For FR3.1 (High Risk):**
1. Create feature branch from clean main
2. Extract one shared method at a time
3. Run tests after each extraction
4. Use git commits frequently (easy rollback)
5. Keep old methods as private helpers initially
6. Delete old methods only after tests pass
7. User review before merge

**For All Tasks:**
- Run pre-commit hooks before each commit
- Monitor SonarCloud for code smells
- Verify test coverage reaches 80%+
- Check performance (scoring must stay <200ms per job)

---

## Progress Tracking

**Group 1 Status:** NOT STARTED
- FR3.3: Pydantic validation (NOT STARTED)
- FR3.4: Circular dependency fix (NOT STARTED)
- FR3.5: Centralize thresholds (NOT STARTED)

**Group 2 Status:** BLOCKED (waiting for Group 1)
- FR3.1: Merge scorers (BLOCKED)

**Group 3 Status:** BLOCKED (waiting for Group 2)
- FR3.2: KeywordMatcher (BLOCKED)

**Overall Progress:** 0/5 tasks complete

---

## Estimated Timeline

**Group 1 (Parallel):**
- Start: After user approval
- Duration: ~4 hours (all 3 agents running simultaneously)
- 3 PRs ready for review

**Group 2 (Supervised):**
- Start: After Group 1 PRs reviewed/merged
- Duration: ~6 hours (supervised, careful approach)
- 1 PR ready for review (requires user approval)

**Group 3 (Serial):**
- Start: After Group 2 PR merged
- Duration: ~4 hours (autonomous)
- 1 PR ready for review

**Total Time:**
- Optimistic: 13-14 hours (if no issues)
- Realistic: 16-18 hours (including reviews, fixes)
- Conservative: 20-24 hours (if major issues in FR3.1)

**Completion Target:** 2-3 days with autonomous agents + user reviews

---

## Success Criteria

**Week 3-4 Complete When:**
- [x] All 5 tasks completed
- [x] All 5 PRs merged to main
- [x] All 1,275+ tests passing
- [x] Zero behavioral changes (verified)
- [x] 589 lines duplication eliminated
- [x] SonarCloud quality gates passing
- [x] Documentation updated
- [x] CHANGELOG.md updated

---

## Ready for Execution

**Next Step:** User approves execution plan

**Recommended:** Start Group 1 in parallel (hybrid mode)
- Spawn 3 autonomous agents for FR3.3, FR3.4, FR3.5
- Low risk, high confidence
- ~4 hours completion time
- Pause before Group 2 for review

**Alternative:** Full autonomous execution (parallel mode)
- Start all safe tasks (Group 1 + Group 3 after dependencies)
- Pause only before FR3.1 (high risk)
- Maximum speed

**User Decision Needed:**
1. Approve task list and execution plan
2. Choose execution mode (Hybrid recommended)
3. Confirm ready to start Group 1
