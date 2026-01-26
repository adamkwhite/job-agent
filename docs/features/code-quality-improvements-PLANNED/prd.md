# Code Quality & Technical Debt Reduction Initiative (Week 1-4)

**Status:** PLANNED
**Created:** 2026-01-25
**Target Completion:** 4 weeks

---

## Overview

Comprehensive code quality improvement initiative addressing critical bugs, refactoring complex methods, consolidating duplicate code, and improving architecture across the job-agent codebase. This multi-phase approach prioritizes user-facing bugs, then code quality, then architectural improvements.

**Phases:**
- **Week 1:** Critical Bug Fixes (4 issues)
- **Week 2:** Code Quality Refactoring ✅ COMPLETED (PRs #216, #217)
- **Week 3-4:** Consolidation & Architecture
- **Month 2:** Advanced Architecture (optional)

---

## Problem Statement

### Current Issues

**1. Critical Bugs Affecting Users:**
- Seniority scores incorrectly silenced when role doesn't match (Issue #219)
- Config validation absent, leading to silent failures (Issue #220)
- Digest job counts don't match displayed jobs (Issue #221, user reports #199, #200)
- Broken career page links leading to 404 errors (Issue #222, user report #197)

**2. Code Quality Debt (Week 2 - ✅ COMPLETED):**
- ~~Complex methods exceeding 100 lines (fixed: PRs #216, #217)~~
- ~~High cyclomatic complexity (fixed: PRs #216, #217)~~
- ~~Poor testability of scoring logic (fixed: PRs #216, #217)~~

**3. Architecture Debt (Week 3-4):**
- 589 lines of duplicate code between JobScorer and ProfileScorer
- Keyword matching logic scattered across files
- No centralized configuration validation
- Circular dependency workarounds
- Hard-coded score thresholds in multiple locations

---

## Goals

### Primary Goals

1. **Fix all user-reported bugs** (Week 1):
   - Correct seniority scoring logic
   - Add configuration validation
   - Align digest counts with displayed jobs
   - Validate career page URLs before storage

2. **Reduce code duplication** (Week 3):
   - Merge JobScorer and ProfileScorer into unified system
   - Extract keyword matching to utility class
   - Consolidate score threshold constants

3. **Improve maintainability** (Week 3-4):
   - Add Pydantic configuration validation
   - Fix circular dependency issues
   - Centralize configuration management

### Secondary Goals

1. Improve test coverage for extracted logic
2. Add comprehensive logging for debugging
3. Update documentation to reflect changes
4. Ensure zero behavioral changes (1,265 tests must pass)

---

## Success Criteria

**Week 1 - Critical Bugs (Issues #219-222):**
- [ ] All 4 user-facing bugs fixed
- [ ] 8+ new tests added (2 per bug)
- [ ] All 1,265 existing tests pass
- [ ] SonarCloud quality gate passes
- [ ] No user reports of same issues

**Week 2 - Code Quality (✅ COMPLETED):**
- [x] `_score_role_type()` refactored from 128 → 43 lines (PR #216)
- [x] `apply_hard_filters()` refactored from 120 → 25 lines (PR #217)
- [x] Cyclomatic complexity reduced by 75%+
- [x] 155+ new unit tests added
- [x] 100% coverage on extracted methods

**Week 3-4 - Consolidation:**
- [ ] JobScorer + ProfileScorer merged (589 lines eliminated)
- [ ] KeywordMatcher utility class created
- [ ] Pydantic config validation added
- [ ] Circular dependency resolved
- [ ] Score thresholds centralized

---

## Requirements

### Week 1: Critical Bug Fixes

#### FR1.1: Fix Seniority Silencing Bug (Issue #219)
**Functional Requirements:**
1. Seniority must be scored independently of role type
2. "Director of Marketing" must score 25 for seniority, 0 for role
3. Hard filters must still block inappropriate roles (separate concern)

**Technical Requirements:**
1. Modify `src/agents/profile_scorer.py` line 67
2. Remove conditional: `if role_score > 0 else 0`
3. Add 2+ tests for seniority/role separation

**Non-Functional Requirements:**
1. Zero behavioral change for valid jobs
2. All 1,265 tests must pass
3. Performance unchanged (<10ms per job)

---

#### FR1.2: Add Config Missing Key Warnings (Issue #220)
**Functional Requirements:**
1. System must validate profile JSON on load
2. Missing critical keys must raise clear errors
3. Missing optional keys must log warnings with defaults
4. Validation errors must specify which keys are missing

**Technical Requirements:**
1. Create `src/utils/config_validator.py` module
2. Implement `validate_profile_config(profile: Profile) -> list[str]`
3. Implement `check_required_keys(profile: Profile)` with raises
4. Integrate into ProfileScorer.__init__()

**Required Profile Keys:**
- Critical: `id`, `name`, `email`, `scoring.seniority_levels`, `scoring.domain_keywords`
- Optional: `hard_filter_keywords.exceptions`, `context_filters.contract_min_seniority_score`

**Non-Functional Requirements:**
1. Validation adds <5ms to startup time
2. Clear error messages for junior developers
3. Backwards compatible with existing profiles

---

#### FR1.3: Fix Count-Display Mismatch (Issue #221)
**Functional Requirements:**
1. Digest job count must match number of displayed jobs
2. Count must be calculated AFTER all filters applied:
   - Location filtering
   - Staleness filtering
   - Grade filtering (digest_min_grade)
3. Email template must clearly state what's being counted

**Technical Requirements:**
1. Modify `src/send_profile_digest.py`:
   - Move count calculation after filter pipeline
   - Add assertion: `assert len(displayed_jobs) == job_count`
2. Add integration test for count accuracy
3. Update email template with clear count description

**Test Cases:**
- Digest with location filtering enabled
- Digest with stale jobs in database
- Digest with grade threshold filtering
- Digest with all filters combined

**Non-Functional Requirements:**
1. No performance degradation
2. Clear logging of filter stages
3. Backwards compatible with existing digests

---

#### FR1.4: Fix Broken Career Page Links (Issue #222)
**Functional Requirements:**
1. All career page URLs must be validated before storage
2. Invalid URLs must be logged with warnings
3. Jobs with broken links must be marked as stale
4. Stale jobs must be excluded from digests

**Technical Requirements:**
1. Add URL validation in `src/scrapers/firecrawl_career_scraper.py`:
   - HTTP HEAD request to check accessibility
   - Timeout: 5 seconds
   - Retry once on transient failures
2. Create `src/utils/url_validator.py` module
3. Enhance stale job detection to mark broken URLs
4. Add `url_validated_at` timestamp to database

**URL Validation Logic:**
```python
def validate_job_url(url: str) -> tuple[bool, str]:
    """
    Validate job URL is accessible

    Returns:
        (is_valid, reason)
    """
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            return (True, "valid")
        elif response.status_code == 404:
            return (False, "not_found")
        elif response.status_code >= 500:
            return (False, "server_error_retry")
        else:
            return (False, f"http_{response.status_code}")
    except requests.Timeout:
        return (False, "timeout")
    except requests.RequestException as e:
        return (False, f"connection_error: {e}")
```

**Non-Functional Requirements:**
1. URL validation adds <2s per job scraped
2. Failed validations don't block scraping pipeline
3. Clear logging of validation failures for debugging

---

### Week 2: Code Quality Refactoring (✅ COMPLETED)

#### FR2.1: Refactor `_score_role_type()` Method ✅ (PR #216)
- **Status:** COMPLETED
- **Result:** 128 lines → 43 lines (66% reduction)
- **Extracted:** 10 testable methods
- **Tests Added:** 80+ unit tests
- **Coverage:** 100% on extracted methods

#### FR2.2: Refactor `apply_hard_filters()` Method ✅ (PR #217)
- **Status:** COMPLETED
- **Result:** 120 lines → 25 lines (79% reduction)
- **Pattern:** Chain of Responsibility (11 filter handlers)
- **Tests Added:** 75+ unit tests
- **Coverage:** 97% on new code

---

### Week 3-4: Consolidation & Architecture

#### FR3.1: Merge JobScorer + ProfileScorer
**Problem:** 589 lines of duplicate code between two scorer classes

**Solution:**
1. Create unified `BaseScorer` class with shared logic
2. JobScorer extends BaseScorer (Wesley's hardcoded profile)
3. ProfileScorer extends BaseScorer (dynamic profiles)
4. Extract shared methods:
   - `_score_seniority()`
   - `_score_domain()`
   - `_score_location()`
   - `_score_technical_keywords()`

**Implementation:**
```python
class BaseScorer:
    """Base scoring logic shared by all scorers"""

    def __init__(self, profile: dict):
        self.profile = profile
        self.role_category_keywords = load_role_category_keywords()
        self.company_classifier = CompanyClassifier()

    def score_job(self, job: dict) -> tuple[int, str, dict, dict]:
        """Shared scoring orchestration"""
        # Shared logic here
        pass

    def _score_seniority(self, title: str) -> int:
        """Shared seniority scoring"""
        pass

    # ... more shared methods

class JobScorer(BaseScorer):
    """Wesley's hardcoded profile scorer"""

    def __init__(self):
        profile = load_wes_profile()  # Hardcoded profile
        super().__init__(profile)

class ProfileScorer(BaseScorer):
    """Dynamic profile scorer"""

    def __init__(self, profile: Profile):
        profile_dict = profile.to_dict()
        super().__init__(profile_dict)
```

**Acceptance Criteria:**
- [ ] 589 lines of duplication eliminated
- [ ] All 1,265 tests pass
- [ ] Zero behavioral changes
- [ ] BaseScorer has 100% coverage

---

#### FR3.2: Create KeywordMatcher Utility Class
**Problem:** Keyword matching logic scattered across 5+ files

**Solution:**
```python
class KeywordMatcher:
    """Centralized keyword matching with fuzzy matching support"""

    def __init__(self, keywords: list[str]):
        self.keywords = [kw.lower() for kw in keywords]

    def matches(self, text: str, threshold: float = 0.8) -> list[str]:
        """
        Find keyword matches in text

        Args:
            text: Text to search
            threshold: Fuzzy match threshold (0.0-1.0)

        Returns:
            List of matched keywords
        """
        pass

    def count_matches(self, text: str, threshold: float = 0.8) -> int:
        """Count keyword matches"""
        return len(self.matches(text, threshold))

    def has_any(self, text: str, threshold: float = 0.8) -> bool:
        """Check if any keyword matches"""
        return len(self.matches(text, threshold)) > 0
```

**Usage:**
```python
domain_matcher = KeywordMatcher(["robotics", "automation", "iot"])
if domain_matcher.has_any(job_title):
    score += 25
```

**Acceptance Criteria:**
- [ ] Keyword logic centralized in one class
- [ ] 100% test coverage on KeywordMatcher
- [ ] All scorers migrated to use it
- [ ] Performance unchanged (<10ms per job)

---

#### FR3.3: Add Pydantic Configuration Validation
**Problem:** Profile JSON validation is manual and error-prone

**Solution:** Use Pydantic models for type-safe configuration
```python
from pydantic import BaseModel, Field, validator

class SeniorityLevel(BaseModel):
    points: int = Field(ge=0, le=30)
    keywords: list[str]

class ScoringConfig(BaseModel):
    seniority_levels: dict[str, SeniorityLevel]
    domain_keywords: dict[str, int]
    role_types: dict[str, dict]
    locations: dict[str, int]
    technical_keywords: dict[str, int]

    @validator('seniority_levels')
    def validate_seniority_total(cls, v):
        """Ensure total seniority points don't exceed 30"""
        total = sum(level.points for level in v.values())
        if total > 30:
            raise ValueError(f"Total seniority points ({total}) exceeds max (30)")
        return v

class ProfileConfig(BaseModel):
    id: str
    name: str
    email: str
    scoring: ScoringConfig
    digest_min_grade: str = Field(regex=r'^[A-F]$')
    notifications_enabled: bool = True
```

**Acceptance Criteria:**
- [ ] All profile JSON validated with Pydantic
- [ ] Type hints throughout codebase
- [ ] Clear validation errors on load
- [ ] Backwards compatible with existing JSONs

---

#### FR3.4: Fix Circular Dependency Workaround
**Problem:** `company_classifier.py` imports from `scoring_utils.py` which imports back

**Current Workaround:**
```python
# Import inside function to avoid circular dependency
from utils.company_classifier import should_filter_job
```

**Solution:** Restructure into layers:
1. **Foundation Layer:** `scoring_utils.py` (no dependencies)
2. **Classification Layer:** `company_classifier.py` (depends on foundation)
3. **Scoring Layer:** `job_scorer.py`, `profile_scorer.py` (depends on both)

**Acceptance Criteria:**
- [ ] No circular dependencies
- [ ] All imports at module level
- [ ] Clear architectural layers
- [ ] All tests pass

---

#### FR3.5: Centralize Score Thresholds
**Problem:** Grade thresholds hardcoded in 8+ files

**Solution:** Create `src/utils/score_thresholds.py`:
```python
from enum import Enum

class Grade(Enum):
    A = 85
    B = 70
    C = 55
    D = 40
    F = 0

def calculate_grade(score: int) -> str:
    """Convert score to letter grade"""
    for grade in [Grade.A, Grade.B, Grade.C, Grade.D]:
        if score >= grade.value:
            return grade.name
    return Grade.F.name

def score_meets_grade(score: int, min_grade: str) -> bool:
    """Check if score meets minimum grade threshold"""
    threshold = Grade[min_grade].value
    return score >= threshold
```

**Files to Update:**
- `src/agents/job_scorer.py`
- `src/agents/profile_scorer.py`
- `src/send_profile_digest.py`
- `src/tui.py`
- Documentation files (already updated in PR #218)

**Acceptance Criteria:**
- [ ] Single source of truth for thresholds
- [ ] All hardcoded values removed
- [ ] Tests use Grade enum
- [ ] All 1,265 tests pass

---

## User Stories

### Week 1 - Critical Bugs

**US1.1: As a User (Wes/Adam/Eli), I want seniority to be scored correctly even when role doesn't match, so that I see appropriate scores for all jobs**
- Given: "Director of Marketing" job
- When: Job is scored
- Then: Seniority = 25, Role = 0, Total ≠ 0

**US1.2: As a Developer, I want clear errors when profile JSON is misconfigured, so that I can fix configuration issues quickly**
- Given: Profile JSON missing `seniority_levels`
- When: System loads profile
- Then: Clear error message specifies missing key

**US1.3: As a User, I want digest job counts to match displayed jobs, so that I'm not confused by discrepancies**
- Given: Digest with 10 jobs after filtering
- When: Email is generated
- Then: Email says "10 jobs" and displays exactly 10 jobs

**US1.4: As a User, I want all job links to work, so that I can apply without frustration**
- Given: Career page URL scraped from company website
- When: URL is validated before storage
- Then: Only valid URLs are stored, broken ones are logged

---

### Week 3-4 - Consolidation

**US3.1: As a Developer, I want a single scoring implementation, so that I don't fix bugs twice**
- Given: Bug fix needed in seniority scoring
- When: Fix is applied to BaseScorer
- Then: Both JobScorer and ProfileScorer get the fix

**US3.2: As a Developer, I want centralized keyword matching, so that I can maintain logic in one place**
- Given: Need to add fuzzy matching for keywords
- When: I update KeywordMatcher class
- Then: All scorers get fuzzy matching automatically

**US3.3: As a Developer, I want type-safe configuration, so that I catch errors at load time**
- Given: Profile JSON with invalid `digest_min_grade` value
- When: System loads profile with Pydantic
- Then: Validation error caught before runtime

---

## Technical Specifications

### Week 1 Implementation Details

#### Seniority Silencing Fix (Issue #219)
**File:** `src/agents/profile_scorer.py`

**Before:**
```python
# Line 67 (WRONG)
seniority_score = self._score_seniority(title) if role_score > 0 else 0
```

**After:**
```python
# Line 67 (CORRECT)
seniority_score = self._score_seniority(title)
```

**Test Cases:**
```python
def test_director_of_marketing_scores_seniority_not_role():
    """Director title should score seniority even if role is filtered"""
    scorer = ProfileScorer(test_profile)
    job = {
        "title": "Director of Marketing",
        "company": "Test Co",
        "location": "Remote"
    }
    score, grade, breakdown, _ = scorer.score_job(job)

    assert breakdown["seniority"] == 25  # Director level
    assert breakdown["role_type"] == 0   # Marketing filtered
    assert score >= 25  # Has seniority points

def test_vp_of_finance_scores_seniority_not_role():
    """VP title should score seniority even if role is filtered"""
    scorer = ProfileScorer(test_profile)
    job = {
        "title": "VP of Finance",
        "company": "Test Co",
        "location": "Remote"
    }
    score, grade, breakdown, _ = scorer.score_job(job)

    assert breakdown["seniority"] == 30  # VP level
    assert breakdown["role_type"] == 0   # Finance filtered
    assert score >= 30  # Has seniority points
```

---

#### Config Validation (Issue #220)
**File:** `src/utils/config_validator.py` (NEW)

```python
"""Profile configuration validation utilities"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.profile_manager import Profile

logger = logging.getLogger(__name__)

# Required keys that must be present
REQUIRED_KEYS = {
    "root": ["id", "name", "email", "scoring"],
    "scoring": ["seniority_levels", "domain_keywords", "role_types", "locations", "technical_keywords"],
}

# Optional keys with defaults
OPTIONAL_KEYS = {
    "scoring": {
        "hard_filter_keywords": {},
        "context_filters": {},
        "filtering": {"aggression_level": "moderate"},
    },
    "root": {
        "digest_min_grade": "C",
        "digest_min_score": 55,
        "notifications_enabled": True,
    },
}


def check_required_keys(profile: "Profile") -> None:
    """
    Validate profile has all required keys

    Raises:
        ValueError: If any required key is missing
    """
    missing_keys = []

    # Check root-level keys
    for key in REQUIRED_KEYS["root"]:
        if not hasattr(profile, key) or getattr(profile, key) is None:
            missing_keys.append(key)

    # Check scoring keys
    if hasattr(profile, "scoring") and profile.scoring:
        for key in REQUIRED_KEYS["scoring"]:
            if key not in profile.scoring:
                missing_keys.append(f"scoring.{key}")
    else:
        missing_keys.extend([f"scoring.{k}" for k in REQUIRED_KEYS["scoring"]])

    if missing_keys:
        raise ValueError(
            f"Profile '{profile.id}' is missing required keys: {', '.join(missing_keys)}\n"
            f"Please check your profile JSON file."
        )


def validate_profile_config(profile: "Profile") -> list[str]:
    """
    Validate profile configuration and return warnings for missing optional keys

    Returns:
        List of warning messages for missing optional keys
    """
    warnings = []

    # Check optional scoring keys
    if hasattr(profile, "scoring") and profile.scoring:
        for key, default in OPTIONAL_KEYS["scoring"].items():
            if key not in profile.scoring:
                warnings.append(
                    f"Profile '{profile.id}': Missing optional key 'scoring.{key}', "
                    f"using default: {default}"
                )

    # Check optional root keys
    for key, default in OPTIONAL_KEYS["root"].items():
        if not hasattr(profile, key) or getattr(profile, key) is None:
            warnings.append(
                f"Profile '{profile.id}': Missing optional key '{key}', "
                f"using default: {default}"
            )

    return warnings
```

**Integration in ProfileScorer:**
```python
from utils.config_validator import check_required_keys, validate_profile_config

class ProfileScorer:
    def __init__(self, profile: Profile):
        # Validate required keys (raises on error)
        check_required_keys(profile)

        # Check optional keys (log warnings)
        warnings = validate_profile_config(profile)
        for warning in warnings:
            logger.warning(warning)

        self.profile = profile
        # ... rest of init
```

**Test Cases:**
```python
def test_missing_required_key_raises_error():
    """Missing critical key should raise ValueError"""
    profile = Profile(id="test", name="Test", email="test@example.com")
    # Missing 'scoring' key

    with pytest.raises(ValueError, match="missing required keys: scoring"):
        ProfileScorer(profile)

def test_missing_optional_key_logs_warning(caplog):
    """Missing optional key should log warning with default"""
    profile = create_valid_profile()
    # Missing 'hard_filter_keywords'

    scorer = ProfileScorer(profile)

    assert "Missing optional key" in caplog.text
    assert "hard_filter_keywords" in caplog.text
```

---

#### Count-Display Mismatch Fix (Issue #221)
**File:** `src/send_profile_digest.py`

**Current Logic (WRONG):**
```python
# Get jobs (line ~150)
jobs = db.get_jobs_for_profile_digest(profile_id, min_grade, min_score)
job_count = len(jobs)  # Count BEFORE filtering

# Apply filters (line ~200)
filtered_jobs = [j for j in jobs if meets_location_filter(j)]
filtered_jobs = [j for j in filtered_jobs if not is_stale(j)]

# Display (line ~300)
for job in filtered_jobs:
    # Display logic
```

**Fixed Logic:**
```python
# Get jobs
jobs = db.get_jobs_for_profile_digest(profile_id, min_grade, min_score)

# Apply ALL filters FIRST
filtered_jobs = [j for j in jobs if meets_location_filter(j)]
filtered_jobs = [j for j in filtered_jobs if not is_stale(j)]
filtered_jobs = [j for j in filtered_jobs if meets_grade_threshold(j, min_grade)]

# Count AFTER filtering
job_count = len(filtered_jobs)

# Validation
assert len(filtered_jobs) == job_count, (
    f"Count mismatch: {job_count} counted but {len(filtered_jobs)} displayed"
)

# Display with accurate count
for job in filtered_jobs:
    # Display logic
```

**Email Template Update:**
```html
<h2>Weekly Job Digest - {job_count} Jobs Matching Your Criteria</h2>
<p>
  <strong>What's included:</strong> Jobs that match your profile
  with grade {min_grade}+ ({min_score}+ points), in your preferred locations,
  posted within the last 30 days.
</p>
```

**Test Cases:**
```python
def test_digest_count_matches_displayed_jobs():
    """Job count must match number of displayed jobs"""
    profile = create_test_profile()

    # Add 10 jobs, 3 filtered by location, 2 stale
    add_test_jobs(profile, count=10, locations=["Toronto"] * 7 + ["London"] * 3)
    mark_stale(get_job_ids(profile)[:2])

    digest_html = generate_digest(profile)

    # Parse HTML
    job_count_in_header = extract_count_from_header(digest_html)
    displayed_jobs = extract_displayed_jobs(digest_html)

    # Should show 5 jobs (10 - 3 filtered - 2 stale)
    assert job_count_in_header == 5
    assert len(displayed_jobs) == 5
```

---

#### URL Validation Fix (Issue #222)
**File:** `src/utils/url_validator.py` (NEW)

```python
"""URL validation utilities for job links"""
import logging
import requests
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_job_url(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Validate job URL is accessible

    Args:
        url: Job URL to validate
        timeout: Request timeout in seconds

    Returns:
        (is_valid, reason): Tuple of validation result and reason
    """
    try:
        # Use HEAD request (faster than GET)
        response = requests.head(url, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            return (True, "valid")
        elif response.status_code == 404:
            return (False, "not_found")
        elif 500 <= response.status_code < 600:
            # Server error - might be transient, retry once
            logger.warning(f"Server error for {url}, retrying...")
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return (True, "valid_after_retry")
            return (False, f"server_error_{response.status_code}")
        else:
            return (False, f"http_{response.status_code}")

    except requests.Timeout:
        logger.warning(f"Timeout validating URL: {url}")
        return (False, "timeout")
    except requests.ConnectionError as e:
        logger.warning(f"Connection error validating URL: {url} - {e}")
        return (False, "connection_error")
    except Exception as e:
        logger.error(f"Unexpected error validating URL: {url} - {e}")
        return (False, f"error: {str(e)[:50]}")
```

**Integration in Firecrawl Scraper:**
```python
from utils.url_validator import validate_job_url

class FirecrawlCareerScraper:
    def scrape_company(self, company: dict) -> list[dict]:
        """Scrape jobs from company career page"""
        jobs = []

        # ... existing scraping logic ...

        for job in raw_jobs:
            # Validate URL before storing
            is_valid, reason = validate_job_url(job["link"])

            if not is_valid:
                logger.warning(
                    f"Invalid job URL for {company['name']}: {job['link']} "
                    f"(reason: {reason})"
                )
                # Store validation metadata
                job["url_validated"] = False
                job["url_validation_reason"] = reason
                job["url_validated_at"] = datetime.now().isoformat()
                # Mark as stale so it doesn't appear in digests
                job["is_stale"] = True
                job["stale_reason"] = f"url_invalid: {reason}"
            else:
                job["url_validated"] = True
                job["url_validated_at"] = datetime.now().isoformat()
                job["is_stale"] = False

            jobs.append(job)

        return jobs
```

**Database Schema Update:**
```sql
-- Add validation tracking columns
ALTER TABLE jobs ADD COLUMN url_validated BOOLEAN DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN url_validated_at TEXT DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN url_validation_reason TEXT DEFAULT NULL;

-- Index for querying invalid URLs
CREATE INDEX idx_jobs_url_validated ON jobs(url_validated);
```

**Test Cases:**
```python
def test_validate_job_url_returns_true_for_valid_url():
    """Valid URL should return (True, 'valid')"""
    valid_url = "https://www.google.com"
    is_valid, reason = validate_job_url(valid_url)

    assert is_valid is True
    assert reason == "valid"

def test_validate_job_url_returns_false_for_404():
    """404 URL should return (False, 'not_found')"""
    invalid_url = "https://www.google.com/this-page-does-not-exist-12345"
    is_valid, reason = validate_job_url(invalid_url)

    assert is_valid is False
    assert reason == "not_found"

@mock.patch('requests.head')
def test_validate_job_url_retries_on_server_error(mock_head):
    """Server error should trigger retry"""
    # First call returns 500, second returns 200
    mock_head.side_effect = [
        MagicMock(status_code=500),
        MagicMock(status_code=200)
    ]

    is_valid, reason = validate_job_url("https://example.com")

    assert is_valid is True
    assert reason == "valid_after_retry"
    assert mock_head.call_count == 2
```

---

## Dependencies

### External Dependencies
- **Python 3.12+**: Required for latest type hints
- **Pydantic 2.x**: For configuration validation (Week 3)
- **requests**: For URL validation (Issue #222)
- **pytest**: For new test cases (all weeks)

### Internal Dependencies
- **JobDatabase**: Used by all scorers
- **CompanyClassifier**: Used in scoring logic
- **Profile system**: Foundation for multi-profile support
- **Filter pipeline**: Hard filters and context filters (PRs #216, #217)

### Database Schema Changes (Issue #222)
```sql
-- Migration: 005_url_validation_tracking.py
ALTER TABLE jobs ADD COLUMN url_validated BOOLEAN DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN url_validated_at TEXT DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN url_validation_reason TEXT DEFAULT NULL;

CREATE INDEX idx_jobs_url_validated ON jobs(url_validated);
```

---

## Timeline

### Week 1: Critical Bug Fixes (4-5 days)
**Day 1-2:**
- [x] Issue #1.1: Grade threshold documentation fix ✅ (PR #218 merged)
- [ ] Issue #219: Seniority silencing fix (1-2 hours implementation + tests)

**Day 3:**
- [ ] Issue #220: Config validation (3-4 hours implementation + tests)

**Day 4:**
- [ ] Issue #221: Count-display mismatch (2-3 hours investigation + fix)

**Day 5:**
- [ ] Issue #222: URL validation (3-4 hours implementation + tests)
- [ ] Integration testing & documentation updates

---

### Week 2: Code Quality ✅ COMPLETED
**Status:** All work completed and merged
- [x] PR #216: `_score_role_type()` refactoring (128 → 43 lines)
- [x] PR #217: `apply_hard_filters()` refactoring (120 → 25 lines)
- [x] 155+ new tests added
- [x] 100% coverage on extracted methods

---

### Week 3: Consolidation (5-7 days)
**Day 1-3:**
- [ ] FR3.1: Merge JobScorer + ProfileScorer
  - Design BaseScorer interface
  - Extract shared methods
  - Migrate both scorers to extend BaseScorer
  - Run full test suite (1,265 tests)

**Day 4-5:**
- [ ] FR3.2: Create KeywordMatcher utility
  - Implement KeywordMatcher class
  - Add fuzzy matching support
  - Migrate all scorers to use it
  - Add 20+ tests

**Day 6-7:**
- [ ] FR3.3: Add Pydantic configuration validation
  - Define Pydantic models
  - Migrate profile loading
  - Update documentation
  - Test with all profiles (Wes, Adam, Eli)

---

### Week 4: Architecture Fixes (3-5 days)
**Day 1-2:**
- [ ] FR3.4: Fix circular dependency
  - Restructure into layered architecture
  - Move imports to module level
  - Verify no circular imports

**Day 3:**
- [ ] FR3.5: Centralize score thresholds
  - Create score_thresholds.py
  - Update 8+ files using hardcoded values
  - Run full test suite

**Day 4-5:**
- [ ] Integration testing
- [ ] Documentation updates
- [ ] Final code review

---

## Risks and Mitigation

### Risk 1: Breaking Existing Functionality
**Likelihood:** Medium
**Impact:** High (user-facing bugs)

**Mitigation:**
- Maintain 100% test coverage (1,265 tests)
- Add new tests for each change
- Use feature flags for risky changes
- Manual testing on staging environment
- Gradual rollout (merge one PR at a time)

---

### Risk 2: Performance Degradation
**Likelihood:** Low
**Impact:** Medium (slower scoring)

**Mitigation:**
- Benchmark before/after each change
- URL validation timeout: 5 seconds max
- Config validation adds <5ms to startup
- Profile scoring target: <200ms per job

---

### Risk 3: Incomplete Profile Migration to Pydantic
**Likelihood:** Medium
**Impact:** Medium (config errors)

**Mitigation:**
- Test with all 3 existing profiles (Wes, Adam, Eli)
- Provide migration guide for new profiles
- Backwards compatible for 1 release cycle
- Clear error messages for validation failures

---

### Risk 4: URL Validation False Positives
**Likelihood:** Medium
**Impact:** Low (valid jobs marked stale)

**Mitigation:**
- Retry logic for transient failures (500 errors, timeouts)
- Whitelist known flaky domains
- Manual review of validation failures
- User feedback mechanism for false positives

---

## Out of Scope

**NOT included in this initiative:**

1. **Notification System Changes:** Notification logic remains unchanged (70+ scores)
2. **New Scraping Sources:** No new job sources added
3. **UI/Frontend Changes:** TUI remains as-is (except threshold displays)
4. **Database Performance:** No query optimization or indexing improvements
5. **LLM Extraction:** Separate from this initiative (see Issue #210)
6. **Multi-Language Support:** Remains English-only
7. **API Development:** No REST API for external access
8. **Machine Learning:** No ML-based scoring enhancements

**Month 2 Architecture (Deferred):**
- Advanced testing gaps (#4.1-4.4 from original plan)
- Parser registry validation
- Additional performance optimizations

---

## Acceptance Criteria

### Week 1 Acceptance Criteria ✅
**All PRs must pass:**
- [ ] All 1,265 existing tests pass
- [ ] 8+ new tests added (2 per bug fix)
- [ ] SonarCloud quality gate passes (80%+ coverage on new code)
- [ ] Pre-commit hooks pass (Ruff, mypy, Bandit)
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] User-reported issues closed (#197, #199, #200)

**Specific to each issue:**
- [ ] Issue #219: Seniority scored independently of role
- [ ] Issue #220: Config validation catches missing keys
- [ ] Issue #221: Digest counts match displayed jobs
- [ ] Issue #222: URLs validated before storage

---

### Week 3-4 Acceptance Criteria ✅
**All PRs must pass:**
- [ ] Code duplication reduced by 50%+ (589 lines → <300 lines)
- [ ] Cyclomatic complexity <10 for all refactored methods
- [ ] 100% test coverage on new utility classes
- [ ] All 1,265 tests pass
- [ ] SonarCloud quality gate passes
- [ ] Documentation updated

**Specific to each FR:**
- [ ] FR3.1: JobScorer + ProfileScorer extend BaseScorer
- [ ] FR3.2: All keyword matching uses KeywordMatcher
- [ ] FR3.3: All profiles validated with Pydantic
- [ ] FR3.4: No circular dependencies remain
- [ ] FR3.5: Score thresholds centralized in one file

---

## Open Questions

### Week 1 Questions
1. **Issue #221 (Count-Display):** Should we add a "filtered jobs" section showing what was excluded and why?
2. **Issue #222 (URL Validation):** Should we add a TUI command to manually re-validate all stored URLs?
3. **Testing:** Should we add Playwright tests for digest HTML rendering?

### Week 3 Questions
1. **BaseScorer Design:** Should we use ABC (abstract base class) or regular inheritance?
2. **KeywordMatcher:** Should fuzzy matching be enabled by default or opt-in?
3. **Pydantic Migration:** Should we migrate profiles in one PR or incrementally?

### Week 4 Questions
1. **Circular Dependency:** Should we create a new `core` package for foundation utilities?
2. **Score Thresholds:** Should thresholds be configurable per-profile, or remain global?

---

## Related Work

**GitHub Issues:**
- Issue #219: Seniority silencing bug (Week 1)
- Issue #220: Config validation (Week 1)
- Issue #221: Count-display mismatch (Week 1, links to #199, #200)
- Issue #222: Broken career links (Week 1, links to #197)

**Completed PRs (Week 2):**
- PR #216: `_score_role_type()` refactoring ✅
- PR #217: `apply_hard_filters()` refactoring ✅
- PR #218: Grade threshold documentation ✅

**Future Work:**
- Issue #210: LangSmith observability for LLM extraction
- User feedback issues (#197-203): Various digest improvements
- Advanced testing gaps (Month 2 deferred)

---

## Success Metrics

### Week 1 Success Metrics
- **Bug Fixes:** 4/4 critical bugs resolved
- **User Impact:** Zero new reports of same issues
- **Test Coverage:** 8+ new tests added
- **Performance:** No degradation (<200ms per job)
- **Documentation:** All docs updated to reflect fixes

### Week 2 Success Metrics ✅ (COMPLETED)
- **Line Reduction:** 248 lines → 68 lines (73% reduction)
- **Complexity:** Cyclomatic complexity reduced by 75%+
- **Test Coverage:** 155+ new tests, 100% coverage on extracted methods
- **Maintainability:** Code easier to understand and modify

### Week 3-4 Success Metrics
- **Code Duplication:** 589 lines eliminated
- **Architecture:** Layered design with no circular dependencies
- **Configuration:** Type-safe validation with Pydantic
- **Test Coverage:** 100% coverage on all new utility classes
- **Developer Experience:** Faster debugging and easier maintenance

---

## Appendix

### File Structure After Completion
```
job-agent/
├── src/
│   ├── agents/
│   │   ├── base_scorer.py          # NEW - Week 3
│   │   ├── job_scorer.py           # Modified - Week 3
│   │   ├── profile_scorer.py       # Modified - Weeks 1, 3
│   │   ├── filter_handlers.py      # ✅ Week 2 (PR #217)
│   │   └── job_filter_pipeline.py  # ✅ Week 2 (PR #217)
│   ├── utils/
│   │   ├── config_validator.py     # NEW - Week 1 (Issue #220)
│   │   ├── url_validator.py        # NEW - Week 1 (Issue #222)
│   │   ├── keyword_matcher.py      # NEW - Week 3
│   │   ├── score_thresholds.py     # NEW - Week 4
│   │   └── scoring_utils.py        # Modified - Week 4
│   ├── send_profile_digest.py      # Modified - Week 1 (Issue #221)
│   └── scrapers/
│       └── firecrawl_career_scraper.py  # Modified - Week 1 (Issue #222)
├── tests/
│   └── unit/
│       ├── test_config_validator.py      # NEW - Week 1
│       ├── test_url_validator.py         # NEW - Week 1
│       ├── test_digest_count_accuracy.py # NEW - Week 1
│       ├── test_seniority_scoring.py     # NEW - Week 1
│       ├── test_keyword_matcher.py       # NEW - Week 3
│       └── test_base_scorer.py           # NEW - Week 3
└── docs/
    └── features/
        └── code-quality-improvements-PLANNED/
            └── prd.md                    # This document
```

### Test Coverage Goals
- **Overall Coverage:** Maintain >60% (current: 67%)
- **New Code Coverage:** 80%+ (SonarCloud requirement)
- **Critical Paths:** 100% coverage on scoring logic
- **Utility Classes:** 100% coverage (KeywordMatcher, config validators)

### Documentation Updates Required
- [ ] CLAUDE.md: Update architecture section with new utilities
- [ ] README.md: Update testing instructions
- [ ] CHANGELOG.md: Document all changes by week
- [ ] Profile JSON examples: Add Pydantic validation examples
- [ ] Developer guide: Add BaseScorer usage instructions

---

**END OF PRD**
