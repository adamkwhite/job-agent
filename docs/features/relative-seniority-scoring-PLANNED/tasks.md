# Relative Seniority Scoring - Implementation Tasks

**Feature:** Relative Seniority Scoring System
**PRD:** `prd.md`
**GitHub Issue:** #244
**Status:** PLANNED

---

## Execution Strategy

**Mode:** TBD (User to select: Serial | Parallel | Hybrid)
**Parallel Groups:** 3 groups identified
**Estimated Time:**
- Serial: 12-14 hours (all tasks one-by-one)
- Parallel: 7-9 hours (Group 1 in parallel, Groups 2-3 serial) - **40% faster**
- Hybrid: 8-10 hours (recommended)

---

## Relevant Files

**Core Implementation:**
- `src/agents/base_scorer.py` - Main scoring logic (Tasks 1, 2)
- `tests/unit/test_base_scorer.py` - Unit tests (Task 3)
- `tests/integration/test_profile_scoring.py` - Integration tests (Task 3)

**Rescoring:**
- `src/rescore_all_jobs.py` - Existing rescore script (Task 4)
- `data/jobs.db` - Database to rescore (Task 4)

**Documentation:**
- `CLAUDE.md` - Project documentation (Task 5)
- `src/send_profile_digest.py` - Email template with scoring explanation (Task 5)
- `docs/development/SCORING_UPDATE_CHECKLIST.md` - Scoring change process (Task 5)

**Shared Files (Require Coordination):**
- `CHANGELOG.md` - Updated at completion (Task 5)
- `docs/features/relative-seniority-scoring-PLANNED/status.md` - Progress tracking (All tasks)

---

## Task Dependency Graph

```
Group 1 (PARALLEL - Can run simultaneously):
┌─────────────────────────────────────────────┐
│ Task 1.0: Seniority Hierarchy               │ ← No dependencies
│ Task 2.0: Relative Scoring Algorithm        │ ← No dependencies
│ Task 3.0: Test Coverage                     │ ← No dependencies
└─────────────────────────────────────────────┘
                    ↓
Group 2 (SERIAL - Depends on Group 1):
┌─────────────────────────────────────────────┐
│ Task 4.0: Rescore Historical Jobs           │ ← Needs Tasks 1.0, 2.0 complete
└─────────────────────────────────────────────┘
                    ↓
Group 3 (SERIAL - Depends on Group 2):
┌─────────────────────────────────────────────┐
│ Task 5.0: Update Documentation              │ ← Needs all tasks complete
└─────────────────────────────────────────────┘
```

---

## Tasks

### GROUP 1: Core Implementation (PARALLEL SAFE)

#### Task 1.0: Create Seniority Hierarchy System
- **Files:** `src/agents/base_scorer.py`
- **Dependencies:** None
- **Parallel Safe:** ✅ Yes (independent module)
- **Execution Group:** Group 1
- **Estimated Time:** 2 hours

Sub-tasks:
- [ ] 1.1 Add `SENIORITY_HIERARCHY` constant to `base_scorer.py`
  - Define 9-level hierarchy (0=Junior → 8=C-level)
  - Map keywords to each level with word boundary matching
  - Examples: level 0: ["junior", "intern"], level 2: ["senior", "staff", "principal"]

- [ ] 1.2 Implement `_detect_seniority_level(title: str) -> int` helper method
  - Input: Job title (lowercase string)
  - Output: Seniority level (0-8 integer)
  - Logic: Check title against SENIORITY_HIERARCHY, return highest matching level
  - Handle ambiguous titles: "Senior Manager" → level 5 (Manager priority over Senior)
  - Return -1 if no seniority keywords found (IC role)

- [ ] 1.3 Implement `_detect_highest_target_level(target_seniority: list[str]) -> int` helper
  - Input: List of target seniority keywords from profile
  - Output: Highest seniority level in target list
  - Logic: Map each keyword to level, return max level
  - Example: ["senior", "lead", "director"] → 6 (director is highest)

- [ ] 1.4 Add docstrings and type hints for all new methods
  - Document the SENIORITY_HIERARCHY structure
  - Add usage examples in docstrings
  - Type hints: `-> int`, `-> list[str]`

**Validation:**
- Manual test: `_detect_seniority_level("Senior Software Engineer")` → 2
- Manual test: `_detect_highest_target_level(["senior", "staff"])` → 2

---

#### Task 2.0: Implement Relative Scoring Algorithm
- **Files:** `src/agents/base_scorer.py`
- **Dependencies:** None (can develop alongside Task 1.0, will integrate later)
- **Parallel Safe:** ✅ Yes (different method than Task 1.0)
- **Execution Group:** Group 1
- **Estimated Time:** 3 hours

Sub-tasks:
- [ ] 2.1 Rename current `_score_seniority()` to `_score_seniority_absolute()`
  - Keep existing logic as fallback
  - Add docstring: "Legacy absolute scoring, used when target_seniority is empty"
  - No functional changes, just rename

- [ ] 2.2 Implement new `_score_seniority(title: str) -> int` with relative logic
  - Get `target_seniority` from profile using `self._get_target_seniority()`
  - If target is empty → fallback to `_score_seniority_absolute()`
  - Detect job level: `job_level = self._detect_seniority_level(title)`
  - Detect target level: `target_level = self._detect_highest_target_level(target_seniority)`
  - Calculate level difference: `level_diff = abs(job_level - target_level)`

- [ ] 2.3 Implement scoring based on level difference
  - `if level_diff == 0: return 30  # Perfect match`
  - `if level_diff == 1: return 25  # One level up/down (stretch or slightly junior)`
  - `if level_diff == 2: return 15  # Two levels off`
  - `if level_diff == 3: return 10  # Three levels off`
  - `return 5  # Four+ levels off (major mismatch)`

- [ ] 2.4 Handle edge cases
  - Job level = -1 (no seniority keywords) → return 0 points
  - Target level = -1 (no target specified) → fallback to absolute scoring
  - Multiple targets at different levels → use highest target level

- [ ] 2.5 Add comprehensive docstring with examples
  - Document the relative scoring logic
  - Examples:
    - Mario targets "senior" → "Senior QA" gets 30pts, "Lead QA" gets 25pts, "Director QA" gets 15pts
    - Eli targets "director" → "Director Eng" gets 30pts, "VP Eng" gets 25pts

**Validation:**
- Manual test with Mario's profile: `_score_seniority("Senior QA Engineer")` → 30
- Manual test with Eli's profile: `_score_seniority("Director of Engineering")` → 30

---

#### Task 3.0: Add Comprehensive Test Coverage
- **Files:** `tests/unit/test_base_scorer.py`, `tests/integration/test_profile_scoring.py`
- **Dependencies:** None (can write tests before implementation, TDD approach)
- **Parallel Safe:** ✅ Yes (independent test files)
- **Execution Group:** Group 1
- **Estimated Time:** 4 hours

Sub-tasks:
- [ ] 3.1 Unit tests for `_detect_seniority_level()` (5 tests)
  - Test level 0: `_detect_seniority_level("junior developer")` → 0
  - Test level 2: `_detect_seniority_level("senior engineer")` → 2
  - Test level 6: `_detect_seniority_level("director of engineering")` → 6
  - Test level 8: `_detect_seniority_level("cto")` → 8
  - Test ambiguous: `_detect_seniority_level("senior manager")` → 5 (manager priority)

- [ ] 3.2 Unit tests for `_detect_highest_target_level()` (3 tests)
  - Test single target: `_detect_highest_target_level(["senior"])` → 2
  - Test multiple targets: `_detect_highest_target_level(["senior", "lead", "director"])` → 6
  - Test empty target: `_detect_highest_target_level([])` → -1

- [ ] 3.3 Unit tests for relative `_score_seniority()` (10 tests)
  - Test perfect match: Senior target + Senior job → 30pts
  - Test one level up: Senior target + Lead job → 25pts
  - Test one level down: Senior target + Mid-level job → 15pts
  - Test two levels off: Senior target + Director job → 15pts
  - Test major mismatch: Senior target + VP job → 5pts
  - Test fallback to absolute: Empty target + VP job → 30pts (absolute scoring)
  - Test IC role: Senior target + no seniority keywords → 0pts
  - Test ambiguous title: Senior target + "Senior Manager" → varies based on priority

- [ ] 3.4 Integration tests for all profiles (4 tests)
  - Test Mario profile: Score "Senior QA Engineer" → expect 30pts seniority
  - Test Adam profile: Score "Staff Software Engineer" → expect 30pts seniority
  - Test Eli profile: Score "Director of Engineering" → expect 30pts seniority
  - Test Wes profile: Score "VP of Product" → expect 30pts seniority

- [ ] 3.5 Regression tests for Eli/Wes stability (2 tests)
  - Test Eli: Score 10 sample jobs, verify scores within ±5pts of baseline
  - Test Wes: Score 10 sample jobs, verify scores within ±5pts of baseline

- [ ] 3.6 Edge case tests (5 tests)
  - Test multiple targets at different levels (use highest)
  - Test title with no seniority keywords (IC role)
  - Test profile with no target_seniority (fallback to absolute)
  - Test title with multiple seniority keywords ("Senior Lead Engineer")
  - Test case sensitivity ("SENIOR" vs "senior")

**Validation:**
- Run: `PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_base_scorer.py -v`
- All 25+ new tests pass
- All 1,265+ existing tests still pass (zero regressions)

---

### GROUP 2: Rescore Historical Data (SERIAL - DEPENDS ON GROUP 1)

#### Task 4.0: Rescore Historical Jobs
- **Files:** `src/rescore_all_jobs.py`, `data/jobs.db`
- **Dependencies:** Tasks 1.0, 2.0, 3.0 (needs new scoring code implemented and tested)
- **Parallel Safe:** ❌ No (depends on Group 1, modifies database)
- **Execution Group:** Group 2
- **Estimated Time:** 2 hours

Sub-tasks:
- [ ] 4.1 Create baseline snapshot before rescoring
  - Query current A/B job counts for all profiles
  - Save to `docs/features/relative-seniority-scoring-PLANNED/baseline_scores.json`
  - Include: profile_id, total_jobs, a_grade_count, b_grade_count, avg_score
  - Purpose: Compare before/after to validate changes

- [ ] 4.2 Run rescore script with new algorithm
  - Command: `PYTHONPATH=$PWD job-agent-venv/bin/python src/rescore_all_jobs.py`
  - Monitor output for errors
  - Verify all jobs rescored (check job_scores table)

- [ ] 4.3 Validate Adam's results
  - Query A/B job count for Adam after rescoring
  - Expected: 10-20+ A/B jobs (currently unknown)
  - Verify sample jobs scoring 70+ points include Senior/Staff roles

- [ ] 4.4 Validate Mario's results
  - Query A/B job count for Mario after rescoring
  - Expected: 5-10+ A/B jobs (currently 0)
  - Verify sample jobs include: "Senior QA Engineer", "Lead QA", "QA Manager"

- [ ] 4.5 Validate Eli's stability
  - Query A/B job count for Eli after rescoring
  - Expected: ~45-55 A/B jobs (currently ~50, ±10% tolerance)
  - Verify sample Director/VP jobs still scoring 70+

- [ ] 4.6 Validate Wes's stability (if re-enabled)
  - Query A/B job count for Wes after rescoring
  - Expected: ~65-75 A/B jobs (currently 71, ±10% tolerance)
  - Verify sample VP/Director jobs still scoring 70+

- [ ] 4.7 Save post-rescore snapshot
  - Query new A/B job counts for all profiles
  - Save to `docs/features/relative-seniority-scoring-PLANNED/rescore_results.json`
  - Include: profile_id, total_jobs, a_grade_count, b_grade_count, avg_score, delta_from_baseline

**Validation:**
- Mario A/B count increased from 0 → 5+
- Adam A/B count increased significantly
- Eli/Wes A/B counts remain stable (±10%)
- No database errors during rescoring

---

### GROUP 3: Documentation & Finalization (SERIAL - DEPENDS ON GROUP 2)

#### Task 5.0: Update Documentation & Templates
- **Files:** `CLAUDE.md`, `src/send_profile_digest.py`, `docs/development/SCORING_UPDATE_CHECKLIST.md`, `CHANGELOG.md`
- **Dependencies:** All previous tasks (needs final implementation details)
- **Parallel Safe:** ❌ No (modifies shared documentation files)
- **Execution Group:** Group 3
- **Estimated Time:** 1 hour

Sub-tasks:
- [ ] 5.1 Update CLAUDE.md scoring documentation
  - Locate scoring system section (search for "Job Scoring Engine")
  - Replace absolute scoring description with relative scoring
  - Add examples showing how different profiles score the same job differently
  - Update seniority points: "Matches target_seniority: 30pts, One level off: 25pts..."

- [ ] 5.2 Update email digest template in `send_profile_digest.py`
  - Locate scoring explanation in email footer (search for "Scoring Breakdown")
  - Update seniority scoring text: "Seniority (0-30): Based on match to your target level"
  - Add note: "Jobs matching your target seniority receive maximum points"

- [ ] 5.3 Update SCORING_UPDATE_CHECKLIST.md
  - Add relative seniority scoring as new step in checklist
  - Document seniority hierarchy for future reference
  - Add note about testing across all profiles when changing scoring

- [ ] 5.4 Create status.md for this feature
  - Document implementation status (COMPLETED)
  - Include rescore results from Task 4.7
  - List all modified files
  - Add "Related Issues: #244"

- [ ] 5.5 Update CHANGELOG.md
  - Add entry under "Unreleased" or version number
  - Title: "feat: Implement relative seniority scoring for all profiles"
  - Details: "Scoring now matches candidate target seniority instead of absolute VP/Director bias"
  - Impact: "Mario +5 A/B jobs, Adam +X A/B jobs, Eli/Wes stable"

**Validation:**
- All documentation files updated
- Email digest template reflects new scoring
- CHANGELOG entry added

---

## Completion Checklist

**Group 1 Completion:**
- [ ] All Group 1 tasks marked complete
- [ ] All 25+ new tests passing
- [ ] All 1,265+ existing tests still passing
- [ ] SonarCloud quality gate passed (80% coverage on new code)

**Group 2 Completion:**
- [ ] Rescore completed successfully
- [ ] Mario has 5+ A/B jobs (from 0)
- [ ] Adam has 10+ A/B jobs (TBD baseline)
- [ ] Eli A/B count within ±10% of baseline
- [ ] Wes A/B count within ±10% of baseline (if re-enabled)

**Group 3 Completion:**
- [ ] All documentation updated
- [ ] CHANGELOG entry added
- [ ] Feature status.md created

**Final Validation:**
- [ ] Create PR with all changes
- [ ] PR description includes rescore results
- [ ] CI/CD pipeline passes
- [ ] User (Adam) approves changes
- [ ] Merge to main

---

## Notes

- **Risk Mitigation:** Group 1 tasks can run in parallel safely - no file conflicts
- **Testing Strategy:** Write tests first (Task 3.0) to catch implementation bugs early
- **Rollback Plan:** Keep `_score_seniority_absolute()` as fallback if issues found
- **Communication:** Update Mario and Adam when rescoring completes with their new A/B counts

---

## Next Steps

**Choose execution mode:**

1. **Serial Mode:** Complete tasks one-by-one with approval after each
   - Time: ~12-14 hours
   - Best for: Cautious approach, want to review each step

2. **Parallel Mode:** Spawn 3 agents for Group 1 tasks, autonomous execution
   - Time: ~7-9 hours (40% faster)
   - Best for: Fast completion, confident in approach

3. **Hybrid Mode (RECOMMENDED):** Parallel Group 1, approval before Groups 2-3
   - Time: ~8-10 hours
   - Best for: Balance of speed and control
   - Workflow:
     - Run Tasks 1.0, 2.0, 3.0 in parallel (autonomous)
     - Review Group 1 results, approve to continue
     - Run Task 4.0 (rescoring)
     - Review rescore results, approve to continue
     - Run Task 5.0 (documentation)

**Which execution mode would you like to use?**
