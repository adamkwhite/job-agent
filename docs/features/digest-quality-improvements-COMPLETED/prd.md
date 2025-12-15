# PRD: Digest Quality Improvements

## Overview

Improve job digest quality by implementing multi-stage filtering to prevent irrelevant jobs (stale listings, HR roles, junior positions, pure software engineering) from reaching Wesley's digest. Current system allows jobs that don't match his profile to pass scoring thresholds.

## Problem Statement

**Current Issues:**
Jobs that shouldn't reach Wes's digest are getting through:
1. **Stale jobs**: LinkedIn posts "no longer accepting applications" (3 examples in last digest)
2. **Wrong role types**: Software Engineering, HR/People Operations roles
3. **Wrong seniority**: "Associate" level roles passing despite avoid_keywords
4. **Missing filters**: No detection for Finance, Legal, Sales, Administrative roles

**Impact:**
- Wes wastes time reviewing irrelevant jobs
- Digest credibility decreases (less trust in A/B grades)
- Manual filtering burden on user
- Potential missed opportunities buried in noise

**Root Causes:**
- No job validation/freshness check before digest
- Penalty-only system for avoid_keywords (not hard filters)
- Software engineering filter uses penalties (-20), not blocks
- No HR/non-technical role detection
- Edge case handling unclear ("Associate Principal", etc.)

## Goals

### Primary Goals
1. **Hard filter** obvious non-matches before scoring (HR, junior, intern)
2. **Validate job freshness** before digest (stale job detection)
3. **Context-aware filtering** after scoring (software engineering with exceptions)
4. **Flag edge cases** for manual review ("Associate Principal")

### Secondary Goals
1. Maintain scoring system performance (<200ms per job)
2. Keep scores visible for filtered jobs (debugging/tuning)
3. Add new role type exclusions (Finance, Legal, Sales)
4. Handle contract positions intelligently (allow Director+)

## Success Criteria

- [ ] Zero HR/People Operations roles in digest
- [ ] Zero "Junior" or "Intern" roles in digest
- [ ] Zero stale LinkedIn jobs (>30 days or "no longer accepting")
- [ ] Software engineering roles only if hardware/product context
- [ ] "Associate" roles blocked unless Director/VP/Principal level
- [ ] Contract roles allowed for Director+ only
- [ ] Edge cases flagged for manual review
- [ ] Existing A/B grade jobs still pass through
- [ ] No regression in scoring performance (<200ms)
- [ ] Full test coverage on new filtering logic (≥80%)

## Requirements

### Functional Requirements

**FR1: Pre-Scoring Hard Filters**
1.1. Block jobs with "junior" in title (case-insensitive)
1.2. Block jobs with "intern" or "internship" in title
1.3. Block jobs with "coordinator" in title (unless "Senior Coordinator")
1.4. Block "Associate" roles UNLESS title contains Director/VP/Principal/Chief
1.5. Block all HR/People Operations role keywords:
     - "people operations", "human resources", "hr manager", "hr director"
     - "talent acquisition", "recruiting", "recruiter", "chief people officer"
     - Exception: "Chief People Officer" allowed (C-level)
1.6. Block Finance roles: "finance", "accounting", "controller", "treasurer"
1.7. Block Legal roles: "legal", "counsel", "compliance"
1.8. Block Sales/Marketing: "sales", "marketing", "business development" (unless Director+ at hardware company)
1.9. Block Administrative: "administrative", "office manager", "executive assistant"

**FR2: Post-Scoring Context-Aware Filters**
2.1. Software engineering penalty system remains (-20 points)
2.2. ADDITIONALLY block if:
     - Title contains "software engineering" AND
     - Title does NOT contain "hardware", "product", or domain keywords
2.3. Contract/temporary position handling:
     - Block if seniority < Director level (score < 25)
     - Allow if Director+ (score ≥ 25)

**FR3: Stale Job Detection**
3.1. Check job posting age during scraping
3.2. Mark jobs older than 60 days as "potentially_stale"
3.3. Before digest, validate LinkedIn job URLs:
     - Fetch page and check for "no longer accepting applications"
     - Mark as "stale_no_longer_accepting_applications"
3.4. Filter stale jobs from digest
3.5. Log filtered stale jobs for visibility

**FR4: Edge Case Handling**
4.1. Detect ambiguous titles: "Associate Principal", "Senior Associate"
4.2. Flag for manual review (don't auto-filter)
4.3. Store flagged jobs in separate table/field
4.4. Provide review interface (TUI or CLI)

**FR5: Filter Transparency**
5.1. Add "filter_reason" field to jobs table
5.2. Store which filter blocked the job (e.g., "hard_filter_hr_role")
5.3. Add "filtered_at" timestamp
5.4. Keep filtered jobs in database for analysis
5.5. Add filtered job stats to scraper summary

### Technical Requirements

**TR1: Database Schema Updates**
```sql
ALTER TABLE jobs ADD COLUMN filter_reason TEXT;
ALTER TABLE jobs ADD COLUMN filtered_at TEXT;
ALTER TABLE jobs ADD COLUMN manual_review_flag INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN stale_check_result TEXT; -- 'fresh', 'stale', 'not_checked'
```

**TR2: Configuration Updates**
```json
// profiles/wes.json
{
  "hard_filter_keywords": {
    "seniority_blocks": ["junior", "intern", "coordinator"],
    "role_type_blocks": [
      "people operations", "human resources", "hr manager",
      "talent acquisition", "recruiting", "recruiter"
    ],
    "department_blocks": ["finance", "accounting", "legal", "compliance"],
    "sales_marketing_blocks": ["sales manager", "marketing manager", "business development"],
    "exceptions": {
      "c_level_override": ["chief people officer"],
      "senior_coordinator_allowed": true
    }
  },
  "context_filters": {
    "associate_with_senior": ["director", "vp", "principal", "chief"],
    "software_engineering_exceptions": ["hardware", "product"],
    "contract_min_seniority_score": 25
  },
  "stale_job_settings": {
    "age_threshold_days": 60,
    "validate_linkedin_before_digest": true
  }
}
```

**TR3: Filter Pipeline Architecture**
```python
# Stage 1: Pre-scoring hard filters
def apply_hard_filters(job: dict, profile: dict) -> tuple[bool, str | None]:
    """
    Returns: (should_continue, filter_reason)
    - (True, None) = passed filters, continue to scoring
    - (False, "reason") = blocked, don't score
    """
    pass

# Stage 2: Scoring
score, grade, breakdown = scorer.score_job(job)

# Stage 3: Post-scoring context filters
def apply_context_filters(job: dict, score: int, profile: dict) -> tuple[bool, str | None]:
    """
    Returns: (should_store, filter_reason)
    - (True, None) = passed all filters
    - (False, "reason") = blocked after scoring
    """
    pass

# Stage 4: Digest validation
def validate_job_for_digest(job: dict) -> tuple[bool, str | None]:
    """
    Check job freshness before adding to digest
    Returns: (is_fresh, stale_reason)
    """
    pass
```

**TR4: Performance Requirements**
- Hard filter check: <10ms per job
- Stale job URL validation: <500ms per job (cached)
- Total filtering overhead: <50ms per job
- Batch validation support for digest (parallel requests)

### Non-Functional Requirements

**NFR1: Maintainability**
- Filters defined in profile JSON (no code changes for tuning)
- Clear separation: hard filters vs context filters vs validation
- Comprehensive logging of filter decisions
- Filter stats in scraper output

**NFR2: Debuggability**
- Keep all filtered jobs in database with reasons
- Add `--show-filtered` flag to view filtered jobs
- Include filtered job counts in digest summary
- Test mode to see what would be filtered

**NFR3: Backward Compatibility**
- Existing scoring system unchanged (keep penalties)
- New filters are additive (don't break existing behavior)
- Database migration handles existing jobs gracefully
- Profile files support both old and new formats

## User Stories

### Story 1: HR Role Filtering
**As Wes**, I want HR/People Operations roles automatically filtered out, so I don't waste time reviewing jobs outside my expertise.

**Acceptance Criteria:**
- "Director, People Operations" blocked with reason "hard_filter_hr_role"
- "Chief People Officer" allowed (C-level exception)
- "VP of Human Resources" blocked
- Filtered HR roles visible in `--show-filtered` output

### Story 2: Stale Job Detection
**As Wes**, I want stale job listings removed from my digest, so I don't apply to closed positions.

**Acceptance Criteria:**
- LinkedIn jobs checked for "no longer accepting applications"
- Jobs older than 60 days flagged as potentially stale
- Stale jobs filtered from digest with count in summary
- Fresh jobs (<60 days) pass through normally

### Story 3: Software Engineering Context Filter
**As Wes**, I want pure software engineering roles filtered, but hardware/product software roles allowed, so I see relevant technical leadership opportunities.

**Acceptance Criteria:**
- "Director of Software Engineering" at pure software company = blocked
- "Director of Hardware Software" = allowed (hardware keyword)
- "VP, Product Engineering" = allowed (product keyword)
- "Software Engineering Manager" at Tesla = allowed (hardware company)

### Story 4: Associate Title Handling
**As Wes**, I want "Associate Manager" blocked but "Associate Director" allowed, so seniority filtering is smart.

**Acceptance Criteria:**
- "Associate Manager" = blocked
- "Associate Director" = allowed (Director exception)
- "Associate VP" = allowed (VP exception)
- "Senior Associate" = flagged for manual review (ambiguous)

### Story 5: Contract Position Intelligence
**As Wes**, I want contract Director roles allowed but contract mid-level roles blocked, so I see relevant temporary opportunities.

**Acceptance Criteria:**
- "Director of Engineering (Contract)" = allowed
- "Senior Engineer - Contract" = blocked
- "VP Product Management | Contract until Oct 2026" = allowed
- Contract filtering based on seniority score (≥25)

## Technical Specifications

### Hard Filter Implementation

```python
# src/agents/job_filter_pipeline.py

from typing import Literal

FilterReason = Literal[
    "hard_filter_junior",
    "hard_filter_intern",
    "hard_filter_coordinator",
    "hard_filter_associate_low_seniority",
    "hard_filter_hr_role",
    "hard_filter_finance_role",
    "hard_filter_legal_role",
    "hard_filter_sales_marketing",
    "hard_filter_administrative",
    "context_filter_software_engineering",
    "context_filter_contract_low_seniority",
    "stale_job_age",
    "stale_no_longer_accepting_applications",
]

class JobFilterPipeline:
    def __init__(self, profile: dict):
        self.profile = profile
        self.hard_filters = profile.get("hard_filter_keywords", {})
        self.context_filters = profile.get("context_filters", {})

    def apply_hard_filters(self, job: dict) -> tuple[bool, FilterReason | None]:
        """Stage 1: Pre-scoring hard filters"""
        title = job["title"].lower()

        # Junior/Intern/Coordinator
        if "junior" in title:
            return (False, "hard_filter_junior")
        if "intern" in title or "internship" in title:
            return (False, "hard_filter_intern")
        if "coordinator" in title and "senior coordinator" not in title:
            return (False, "hard_filter_coordinator")

        # Associate (context-dependent)
        if "associate" in title:
            exceptions = self.context_filters.get("associate_with_senior", [])
            if not any(exc in title for exc in exceptions):
                return (False, "hard_filter_associate_low_seniority")

        # HR roles
        hr_keywords = self.hard_filters.get("role_type_blocks", [])
        if any(kw in title for kw in hr_keywords):
            # Exception for C-level
            if "chief people officer" not in title:
                return (False, "hard_filter_hr_role")

        # Finance/Legal/Sales/Admin
        if any(kw in title for kw in ["finance", "accounting", "controller"]):
            return (False, "hard_filter_finance_role")
        if any(kw in title for kw in ["legal", "counsel", "compliance"]):
            return (False, "hard_filter_legal_role")
        if any(kw in title for kw in ["sales manager", "marketing manager"]):
            return (False, "hard_filter_sales_marketing")
        if any(kw in title for kw in ["administrative", "office manager", "executive assistant"]):
            return (False, "hard_filter_administrative")

        return (True, None)  # Passed all hard filters

    def apply_context_filters(
        self, job: dict, score: int, breakdown: dict
    ) -> tuple[bool, FilterReason | None]:
        """Stage 3: Post-scoring context filters"""
        title = job["title"].lower()

        # Software engineering (with exceptions)
        if "software engineering" in title or "software engineer" in title:
            exceptions = self.context_filters.get("software_engineering_exceptions", [])
            has_exception = any(exc in title for exc in exceptions)
            if not has_exception:
                return (False, "context_filter_software_engineering")

        # Contract positions (based on seniority score)
        if "contract" in title or "temporary" in title:
            min_score = self.context_filters.get("contract_min_seniority_score", 25)
            seniority_score = breakdown.get("seniority", 0)
            if seniority_score < min_score:
                return (False, "context_filter_contract_low_seniority")

        return (True, None)  # Passed context filters
```

### Stale Job Validation

```python
# src/utils/job_validator.py (extends existing Issue #121 work)

import requests
from datetime import datetime, timedelta

class JobValidator:
    def __init__(self, age_threshold_days: int = 60):
        self.age_threshold_days = age_threshold_days
        self.cache = {}  # URL -> result cache

    def validate_for_digest(self, job: dict) -> tuple[bool, str | None]:
        """
        Validate job freshness before digest

        Returns:
            (is_valid, stale_reason)
        """
        # Check age
        received_at = datetime.fromisoformat(job["received_at"])
        age_days = (datetime.now() - received_at).days

        if age_days > self.age_threshold_days:
            return (False, "stale_job_age")

        # Check LinkedIn URLs for "no longer accepting"
        if "linkedin.com/jobs" in job["link"]:
            if self._is_linkedin_job_closed(job["link"]):
                return (False, "stale_no_longer_accepting_applications")

        return (True, None)

    def _is_linkedin_job_closed(self, url: str) -> bool:
        """Check if LinkedIn job shows 'no longer accepting applications'"""
        if url in self.cache:
            return self.cache[url]

        try:
            response = requests.get(url, timeout=5)
            is_closed = "no longer accepting applications" in response.text.lower()
            self.cache[url] = is_closed
            return is_closed
        except Exception:
            # If we can't check, assume it's valid (don't filter)
            return False
```

### Database Migration

```python
# src/migrations/003_filter_tracking.py

def upgrade(conn):
    """Add filter tracking fields"""
    conn.execute("""
        ALTER TABLE jobs ADD COLUMN filter_reason TEXT;
    """)
    conn.execute("""
        ALTER TABLE jobs ADD COLUMN filtered_at TEXT;
    """)
    conn.execute("""
        ALTER TABLE jobs ADD COLUMN manual_review_flag INTEGER DEFAULT 0;
    """)
    conn.execute("""
        ALTER TABLE jobs ADD COLUMN stale_check_result TEXT DEFAULT 'not_checked';
    """)

def downgrade(conn):
    """Revert filter tracking"""
    # SQLite doesn't support DROP COLUMN, would need table recreation
    pass
```

## Dependencies

### External Dependencies
- **requests** library (for LinkedIn URL validation)
- Existing JobValidator from Issue #121

### Internal Dependencies
- `src/agents/job_scorer.py` - Scoring system (unchanged)
- `src/database.py` - Database operations
- `profiles/*.json` - Profile configurations
- `config/filter-keywords.json` - Filter keyword definitions

## Timeline

### Phase 1: Core Filtering (Week 1)
- [ ] Implement JobFilterPipeline class
- [ ] Add hard filters (junior, intern, HR, finance, legal)
- [ ] Add context filters (software engineering, contracts)
- [ ] Database migration
- [ ] Unit tests for all filters

### Phase 2: Stale Job Detection (Week 1-2)
- [ ] Extend JobValidator with LinkedIn checking
- [ ] Add age-based filtering
- [ ] Implement validation caching
- [ ] Integration with digest generation

### Phase 3: Edge Cases & Manual Review (Week 2)
- [ ] Implement edge case flagging
- [ ] Add manual review table/interface
- [ ] CLI flag `--show-filtered` for debugging

### Phase 4: Testing & Deployment (Week 2)
- [ ] Integration tests with real job data
- [ ] Performance testing (<200ms requirement)
- [ ] Update profile JSON files
- [ ] Deploy and monitor first digest

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Too aggressive filtering blocks good jobs | High | Keep filtered jobs in DB, add `--show-filtered` flag, iterate based on feedback |
| LinkedIn rate limiting on URL validation | Medium | Implement caching, respect rate limits, fall back to age-based only |
| Performance degradation | Low | Optimize filters, use batch validation, cache results |
| Edge cases not caught | Medium | Flag ambiguous cases for manual review, iterate filter rules |
| Profile JSON complexity | Low | Good documentation, validation on load, backward compatibility |

## Out of Scope

- **Upstream company URL fixes** (separate PRD)
- **Machine learning-based filtering** (use rules-based for now)
- **User feedback loop** (save for future iteration)
- **Historical job re-filtering** (only apply to new jobs)
- **Multi-language job support** (English only)

## Acceptance Criteria

### Functional Validation
- [ ] All 4 problem jobs from latest digest would be filtered:
  - Miovision (stale) → `stale_no_longer_accepting_applications`
  - Unknown job (stale) → `stale_no_longer_accepting_applications`
  - MLSE Software Engineering → `context_filter_software_engineering`
  - Knix People Ops → `hard_filter_hr_role`
  - Lululemon Associate → `hard_filter_associate_low_seniority`

### Performance Validation
- [ ] Hard filter check: <10ms per job (tested with 1000 jobs)
- [ ] Context filter check: <5ms per job
- [ ] Stale job validation: <500ms per job (with caching)
- [ ] Total pipeline: <200ms per job end-to-end

### Quality Validation
- [ ] Zero false positives in Wes's next 3 digests
- [ ] Test coverage ≥80% on new filtering code
- [ ] All edge cases documented and handled
- [ ] Filter reason accuracy >95% (manual review of 100 filtered jobs)

## Related Work

### Implementation Issues
- **Issue #158**: Database migration for filter tracking fields
- **Issue #159**: Implement JobFilterPipeline - Hard Filters
- **Issue #160**: Implement JobFilterPipeline - Context-Aware Filters
- **Issue #163**: Extend JobValidator for stale job detection
- **Issue #161**: Integrate filter pipeline into job scrapers
- **Issue #162**: Integrate stale job validation into digest generation

### Related Features
- **Issue #121**: Integrate JobValidator into email processing pipeline (stale detection)
- **Issue #122**: Company Classification Filtering (software vs hardware companies)
- **PR #153**: Email review list for failed extractions
- **Scoring Update Checklist**: `docs/development/SCORING_UPDATE_CHECKLIST.md`

## Open Questions

1. Should "Chief People Officer" really be allowed? (C-level but still HR)
2. What's the exact threshold for LinkedIn rate limiting? (need to test)
3. Should we add analytics dashboard to tune filter thresholds over time?
4. How to handle "Associate Director" at different companies? (title inflation varies)
5. Should filtered job counts appear in email digest summary?

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
