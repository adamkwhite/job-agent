# Code Quality Initiative - Task List

**PRD:** `prd.md`
**Status:** IN_PROGRESS
**Created:** 2026-01-25

---

## Relevant Files

### Week 1: Critical Bug Fixes
- `src/agents/profile_scorer.py` - Contains seniority scoring logic (Issue #219)
- `tests/unit/test_seniority_scoring.py` - NEW - Tests for seniority/role separation
- `src/utils/config_validator.py` - NEW - Profile configuration validation (Issue #220)
- `tests/unit/test_config_validator.py` - NEW - Tests for config validation
- `src/send_profile_digest.py` - Digest generation with count calculation (Issue #221)
- `tests/unit/test_digest_count_accuracy.py` - NEW - Integration tests for count accuracy
- `src/utils/url_validator.py` - NEW - URL validation utility (Issue #222)
- `tests/unit/test_url_validator.py` - NEW - Tests for URL validation
- `src/scrapers/firecrawl_career_scraper.py` - Career page scraping with URL validation
- `src/migrations/005_url_validation_tracking.py` - NEW - Database migration for URL tracking

### Week 2: Refactoring (✅ COMPLETED)
- `src/agents/job_scorer.py` - Refactored _score_role_type method (PR #216)
- `src/agents/filter_handlers.py` - NEW - Filter handler classes (PR #217)
- `src/agents/job_filter_pipeline.py` - Refactored apply_hard_filters (PR #217)

### Week 3-4: Consolidation (PLANNED)
- `src/agents/base_scorer.py` - NEW - Base scorer class
- `src/utils/keyword_matcher.py` - NEW - Centralized keyword matching
- `src/utils/score_thresholds.py` - NEW - Centralized score thresholds
- `src/utils/pydantic_models.py` - NEW - Pydantic profile models

---

## Tasks

### Week 1: Critical Bug Fixes (4 Issues)

- [ ] 1.0 Fix Seniority Silencing Bug (Issue #219)
  - [ ] 1.1 Create branch `fix/seniority-silencing-bug`
  - [ ] 1.2 Remove conditional in `profile_scorer.py:67`
  - [ ] 1.3 Add test: "Director of Marketing" scores seniority but not role
  - [ ] 1.4 Add test: "VP of Finance" scores seniority but not role
  - [ ] 1.5 Run full test suite (1,265 tests must pass)
  - [ ] 1.6 Create PR linked to Issue #219
  - [ ] 1.7 Verify SonarCloud quality gate passes

- [ ] 2.0 Add Config Missing Key Warnings (Issue #220)
  - [ ] 2.1 Create branch `feat/config-validation`
  - [ ] 2.2 Create `src/utils/config_validator.py` module
  - [ ] 2.3 Implement `check_required_keys()` function
  - [ ] 2.4 Implement `validate_profile_config()` function
  - [ ] 2.5 Integrate into ProfileScorer.__init__()
  - [ ] 2.6 Add test: missing required key raises error
  - [ ] 2.7 Add test: missing optional key logs warning
  - [ ] 2.8 Add test: valid config produces no warnings
  - [ ] 2.9 Add test: integration with incomplete profile JSON
  - [ ] 2.10 Run full test suite (1,265 tests must pass)
  - [ ] 2.11 Create PR linked to Issue #220
  - [ ] 2.12 Verify SonarCloud quality gate passes

- [ ] 3.0 Fix Count-Display Mismatch in Digests (Issue #221)
  - [ ] 3.1 Create branch `fix/digest-count-mismatch`
  - [ ] 3.2 Analyze current count calculation in `send_profile_digest.py`
  - [ ] 3.3 Move count calculation AFTER all filters
  - [ ] 3.4 Add assertion: `len(displayed_jobs) == job_count`
  - [ ] 3.5 Update email template with clear count description
  - [ ] 3.6 Add integration test: digest with location filtering
  - [ ] 3.7 Add integration test: digest with stale jobs
  - [ ] 3.8 Add integration test: digest with grade threshold
  - [ ] 3.9 Add integration test: digest with all filters combined
  - [ ] 3.10 Run full test suite (1,265 tests must pass)
  - [ ] 3.11 Create PR linked to Issue #221 (closes #199, #200)
  - [ ] 3.12 Verify SonarCloud quality gate passes

- [ ] 4.0 Fix Broken Career Page Links (Issue #222)
  - [ ] 4.1 Create branch `feat/url-validation`
  - [ ] 4.2 Create `src/utils/url_validator.py` module
  - [ ] 4.3 Implement `validate_job_url()` function with retry logic
  - [ ] 4.4 Create database migration 005 (url_validated columns)
  - [ ] 4.5 Integrate into `firecrawl_career_scraper.py`
  - [ ] 4.6 Add test: valid URL returns (True, 'valid')
  - [ ] 4.7 Add test: 404 URL returns (False, 'not_found')
  - [ ] 4.8 Add test: timeout handling
  - [ ] 4.9 Add test: server error retry logic
  - [ ] 4.10 Add test: connection error handling
  - [ ] 4.11 Run full test suite (1,265 tests must pass)
  - [ ] 4.12 Create PR linked to Issue #222 (closes #197)
  - [ ] 4.13 Verify SonarCloud quality gate passes

### Week 2: Code Quality Refactoring (✅ COMPLETED)

- [x] 5.0 Refactor `_score_role_type()` Method (PR #216)
  - [x] 5.1 Extract methods from 128-line method
  - [x] 5.2 Reduce to <50 lines orchestration
  - [x] 5.3 Add 80+ unit tests
  - [x] 5.4 Achieve 100% coverage on extracted methods
  - [x] 5.5 All 1,265 tests pass

- [x] 6.0 Refactor `apply_hard_filters()` Method (PR #217)
  - [x] 6.1 Implement Chain of Responsibility pattern
  - [x] 6.2 Create 11 filter handler classes
  - [x] 6.3 Reduce to <50 lines orchestration
  - [x] 6.4 Add 75+ unit tests
  - [x] 6.5 Achieve 97% coverage on new code
  - [x] 6.6 All 1,265 tests pass

### Week 3-4: Consolidation & Architecture (PLANNED)

- [ ] 7.0 Merge JobScorer + ProfileScorer (589 lines duplication)
  - [ ] 7.1 Design BaseScorer interface
  - [ ] 7.2 Extract shared methods to BaseScorer
  - [ ] 7.3 Migrate JobScorer to extend BaseScorer
  - [ ] 7.4 Migrate ProfileScorer to extend BaseScorer
  - [ ] 7.5 Add 50+ tests for BaseScorer
  - [ ] 7.6 All 1,265 tests pass

- [ ] 8.0 Create KeywordMatcher Utility Class
  - [ ] 8.1 Design KeywordMatcher interface
  - [ ] 8.2 Implement core matching logic
  - [ ] 8.3 Add fuzzy matching support
  - [ ] 8.4 Migrate all scorers to use KeywordMatcher
  - [ ] 8.5 Add 20+ tests
  - [ ] 8.6 All 1,265 tests pass

- [ ] 9.0 Add Pydantic Configuration Validation
  - [ ] 9.1 Define Pydantic models for profile config
  - [ ] 9.2 Migrate profile loading to use Pydantic
  - [ ] 9.3 Test with all profiles (Wes, Adam, Eli)
  - [ ] 9.4 Update documentation
  - [ ] 9.5 All 1,265 tests pass

- [ ] 10.0 Fix Circular Dependency Workaround
  - [ ] 10.1 Restructure into layered architecture
  - [ ] 10.2 Move all imports to module level
  - [ ] 10.3 Verify no circular dependencies
  - [ ] 10.4 All 1,265 tests pass

- [ ] 11.0 Centralize Score Thresholds
  - [ ] 11.1 Create `score_thresholds.py` with Grade enum
  - [ ] 11.2 Update 8+ files using hardcoded values
  - [ ] 11.3 Update tests to use Grade enum
  - [ ] 11.4 All 1,265 tests pass

---

## Notes

- **Test Coverage:** All new code must have 80%+ coverage (SonarCloud requirement)
- **Behavioral Changes:** Zero behavioral changes - all 1,265 tests must pass
- **PR Strategy:** One PR per issue for clean change tracking
- **Branch Naming:** `fix/` for bugs, `feat/` for new functionality
- **Issue Links:** All PRs must link to GitHub issues
- **User Reports:** Issues #221 closes #199, #200; Issue #222 closes #197

---

## Progress Tracking

**Week 1 Status:** IN_PROGRESS
- Issue #219: NOT STARTED
- Issue #220: NOT STARTED
- Issue #221: NOT STARTED
- Issue #222: NOT STARTED

**Week 2 Status:** ✅ COMPLETED
- PR #216: MERGED
- PR #217: MERGED

**Week 3-4 Status:** PLANNED
- Scheduled after Week 1 completion
