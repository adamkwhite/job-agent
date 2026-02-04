# Relative Seniority Scoring System

**Status:** PLANNED
**Created:** 2026-02-03
**Priority:** HIGH (affects 50% of users)
**Estimated Effort:** 1-2 weeks

---

## Overview

Replace absolute seniority scoring (VP=30pts always) with relative scoring (match to target=30pts). Currently, the scoring system penalizes candidates targeting Senior/Staff/Lead roles by giving them 10-15 points while Director/VP roles get 25-30 points, regardless of candidate preferences. This systematic bias means perfect Senior-level jobs for Adam and Mario max out at ~50-60 points and never reach the 70+ threshold for weekly digests.

---

## Problem Statement

### Current Behavior (Absolute Scoring)

The `_score_seniority()` method in `base_scorer.py` (lines 169-199) uses fixed point values:

```python
# Absolute scoring - IGNORES target_seniority profile field
VP/C-level: 30 points (always)
Director: 25 points (always)
Senior/Principal: 15 points (always)
Manager/Lead: 10 points (always)
IC roles: 0 points (always)
```

### Impact on Users

**Penalized Profiles (50% of users):**
- **Adam** (target: Senior/Staff/Lead) → Perfect Senior jobs get 15pts → Max ~50-60 total
- **Mario** (target: Senior/Staff/Lead) → Perfect Lead QA jobs get 10pts → Max ~50-55 total

**Benefiting Profiles (50% of users):**
- **Eli** (target: Director/VP/CTO) → Perfect Director jobs get 25-30pts → Easily hit 70+
- **Wes** (target: VP/Director/Head) → Perfect VP jobs get 30pts → Easily hit 70+

### User Impact

**Adam & Mario:**
- Cannot reach 70+ score threshold (A/B grades) needed for weekly digests
- Perfect jobs matching ALL other criteria still fail to qualify
- 0% A/B hit rate despite system finding relevant jobs

**Example:**
- Mario gets "Senior QA Engineer @ Remote Company" scoring:
  - Seniority: 15pts (should be 30pts - this is his target!)
  - Domain: 20pts (QA matches perfectly)
  - Role: 18pts (matches QA role types)
  - Location: 15pts (remote matches perfectly)
  - **Total: 68pts (B-)** - misses 70+ digest threshold by 2 points

With relative scoring, this same job would score **83pts (A)** and appear in weekly digests.

### Root Cause

The `target_seniority` field exists in all profiles but is **never used for scoring** - only for filtering. The comment in `base_scorer.py` line 183-184 explicitly states:

```python
# NOTE: This method scores based on title keywords alone, NOT target_seniority.
# The target_seniority profile field is used by other methods (filtering, etc.)
```

This design assumes everyone wants the highest seniority possible, which is false. Candidates target specific career levels based on their experience and goals.

---

## Goals

### Primary Goal

Implement relative seniority scoring where jobs matching the candidate's `target_seniority` receive maximum points (30), creating parity across all career levels.

### Secondary Goals

1. Maintain backward compatibility - Eli and Wes should score identically
2. Zero behavioral changes for filtering logic
3. Add comprehensive tests covering all seniority combinations
4. Update documentation and email templates

---

## Proposed Solution

### Seniority Level Mapping

Define a career progression hierarchy:

```python
SENIORITY_HIERARCHY = {
    0: ["junior", "entry-level", "associate", "intern"],
    1: ["mid-level", "engineer", "analyst", "specialist"],  # IC without "senior"
    2: ["senior", "staff", "principal"],
    3: ["lead", "team lead", "tech lead"],
    4: ["manager", "engineering manager"],
    5: ["senior manager", "group manager"],
    6: ["director", "head of"],
    7: ["senior director", "executive director"],
    8: ["vp", "vice president", "cto", "cpo", "chief"],
}
```

### Relative Scoring Algorithm

```python
def _score_seniority(self, title: str) -> int:
    """
    Score based on seniority match to target (0-30 points)

    Relative scoring:
    - Perfect match to target_seniority: 30 points
    - One level above target: 25 points (stretch opportunity)
    - One level below target: 15 points
    - Two levels off: 10 points
    - Three+ levels off: 5 points
    """
    target_seniority = self._get_target_seniority()

    if not target_seniority:
        # Fallback to absolute scoring if no target specified
        return self._score_seniority_absolute(title)

    job_level = self._detect_seniority_level(title)
    target_level = self._detect_highest_target_level(target_seniority)

    level_diff = abs(job_level - target_level)

    if level_diff == 0: return 30  # Perfect match
    if level_diff == 1: return 25  # Close match (one level up/down)
    if level_diff == 2: return 15  # Somewhat off
    if level_diff == 3: return 10  # Significantly off
    return 5  # Major mismatch
```

### Examples

**Mario (target: "senior", "staff", "lead", "principal")**

| Job Title | Current Score | New Score | Difference |
|-----------|--------------|-----------|------------|
| Senior QA Engineer | 15 | **30** | +15 |
| Lead QA Engineer | 10 | **30** | +20 |
| Staff QA Engineer | 15 | **30** | +15 |
| QA Manager | 10 | **25** | +15 (one level up) |
| Director of QA | 25 | **15** | -10 (stretch is possible) |
| VP of Quality | 30 | **10** | -20 (too senior) |

**Eli (target: "director", "vp", "cto")**

| Job Title | Current Score | New Score | Difference |
|-----------|--------------|-----------|------------|
| Director of Engineering | 25 | **30** | +5 |
| VP of Engineering | 30 | **30** | 0 (no change) |
| Senior Director | 25 | **30** | +5 |
| Senior Manager | 15 | **25** | +10 (one below) |
| Staff Engineer | 15 | **10** | -5 (too junior) |

### Impact on Digest Threshold

**Before (Absolute Scoring):**
- Mario's perfect Senior QA job: 68 points (B-) → No digest
- Adam's perfect Staff Engineer job: 65 points (C+) → No digest

**After (Relative Scoring):**
- Mario's perfect Senior QA job: 83 points (A) → ✅ Weekly digest
- Adam's perfect Staff Engineer job: 80 points (A-) → ✅ Weekly digest

---

## Implementation Plan

### Phase 1: Core Algorithm (Week 1)

**Tasks:**
1. Add `SENIORITY_HIERARCHY` constant to `base_scorer.py`
2. Implement `_detect_seniority_level(title)` helper
3. Implement `_detect_highest_target_level(target_seniority)` helper
4. Update `_score_seniority()` to use relative scoring
5. Keep `_score_seniority_absolute()` as fallback

**Files Modified:**
- `src/agents/base_scorer.py` (main changes)

**Tests Required:**
- Test each seniority level detection
- Test scoring for all profiles (Adam, Mario, Eli, Wes)
- Test edge cases (multiple targets, missing targets, ambiguous titles)
- Regression tests ensuring Eli/Wes scores unchanged

### Phase 2: Rescore Historical Data (Week 2)

**Tasks:**
1. Run `src/rescore_all_jobs.py` to update existing job scores
2. Verify Adam and Mario now have A/B grade jobs
3. Verify Eli and Wes scores remain stable
4. Update digest emails with new scores

**Validation:**
- Compare before/after score distributions
- Ensure no jobs lost/gained unexpectedly for Eli/Wes
- Confirm Adam/Mario A/B counts increase

### Phase 3: Documentation & Templates (Week 2)

**Tasks:**
1. Update `CLAUDE.md` scoring documentation
2. Update `send_profile_digest.py` email footer explanation
3. Add scoring examples to `docs/development/SCORING_UPDATE_CHECKLIST.md`
4. Update profile JSON documentation

**Files Modified:**
- `CLAUDE.md`
- `src/send_profile_digest.py`
- `docs/development/SCORING_UPDATE_CHECKLIST.md`

---

## Success Criteria

### Must Have (Week 1)

- [ ] `_score_seniority()` uses relative scoring based on `target_seniority`
- [ ] All 1,265+ existing tests pass (zero behavioral regressions)
- [ ] 15+ new unit tests covering relative scoring logic
- [ ] SonarCloud quality gate passes (80% coverage on new code)
- [ ] Eli and Wes scores remain within ±5 points of current values

### Should Have (Week 2)

- [ ] All jobs rescored using new algorithm
- [ ] Mario has 5+ A/B grade jobs (currently 0)
- [ ] Adam has 10+ A/B grade jobs (TBD current count)
- [ ] Documentation updated (CLAUDE.md, email templates)

### Nice to Have

- [ ] Admin script to preview score changes before applying
- [ ] Logging to track score differences for analysis
- [ ] Dashboard showing score distribution by profile

---

## Risks & Mitigation

### Risk 1: Regression for Eli/Wes

**Mitigation:**
- Comprehensive regression tests before/after
- Rollback plan if their A/B counts drop >10%
- Fallback to absolute scoring if target_seniority is empty

### Risk 2: Ambiguous Titles

**Example:** "Senior Product Manager" - is this level 2 (Senior) or level 4 (Manager)?

**Mitigation:**
- Keyword priority: "Manager" takes precedence over "Senior"
- Test suite covering 50+ ambiguous title examples
- Manual review of top 100 job titles before deployment

### Risk 3: Profile Misconfiguration

**Example:** User sets target_seniority=["director"] but actually wants Senior roles

**Mitigation:**
- Add validation to profile loader
- Warn if target_seniority is empty
- Document target_seniority field clearly in profile templates

---

## Testing Strategy

### Unit Tests (15+ tests)

```python
def test_seniority_perfect_match():
    """Senior target + Senior job = 30 points"""

def test_seniority_one_level_up():
    """Senior target + Lead job = 25 points"""

def test_seniority_one_level_down():
    """Senior target + Mid-level job = 15 points"""

def test_seniority_major_mismatch():
    """Senior target + VP job = 5 points"""

def test_ambiguous_title_senior_manager():
    """'Senior Manager' detected as level 5 (Manager), not level 2 (Senior)"""

def test_fallback_to_absolute_when_no_target():
    """Missing target_seniority → use absolute scoring"""
```

### Integration Tests

- Score 10 jobs for each profile, verify relative scoring applied
- Rescore all jobs, verify Adam/Mario A/B counts increase
- Verify Eli/Wes digest contents unchanged

### Regression Tests

- Snapshot current scores for all profiles
- Apply relative scoring
- Verify Eli/Wes scores within ±5 points
- Verify no jobs unexpectedly filtered

---

## Rollout Plan

### Week 1: Development & Testing

1. Implement relative scoring algorithm
2. Add comprehensive unit tests
3. Manual testing with all 4 profiles
4. Code review and refinement

### Week 2: Deployment & Validation

1. Deploy to production
2. Rescore all historical jobs
3. Send test digests to all profiles
4. Monitor for unexpected behavior
5. Gather user feedback

### Week 3: Iteration (if needed)

1. Adjust scoring weights based on feedback
2. Fine-tune seniority hierarchy
3. Fix any edge cases discovered

---

## Open Questions

1. **Should one level above count as "stretch opportunity" (25pts) or penalize it (20pts)?**
   - Recommendation: 25pts - many candidates want growth opportunities

2. **How to handle profiles with mixed targets (e.g., "senior, director")?**
   - Recommendation: Use highest target level as baseline

3. **Should we add profile-specific seniority weights?**
   - Example: Mario values "Lead" at 30pts but "Principal" at 28pts
   - Recommendation: Phase 2 enhancement, not MVP

4. **Do we need to rescore ALL historical jobs or just new jobs?**
   - Recommendation: Rescore all to fix Adam/Mario's 0% A/B hit rate immediately

---

## Related Work

- Issue #212: Per-profile hard filters (seniority filtering already implemented)
- Issue #122: Company classification filtering (domain filtering already implemented)
- Issue #236: Database backup system (needed before bulk rescoring)
- `docs/development/SCORING_UPDATE_CHECKLIST.md`: Process for scoring changes

---

## Metrics to Track

**Before Deployment:**
- Adam A/B job count: TBD
- Mario A/B job count: 0
- Eli A/B job count: ~50 (from 931 total)
- Wes A/B job count: 71 (before opt-out)

**After Deployment (Week 2):**
- Mario A/B job count: Target 5-10+
- Adam A/B job count: Target 10-20+
- Eli A/B job count: Should remain ~45-55 (±10% tolerance)
- Wes A/B job count: N/A (opted out)

**Long-term (Month 1):**
- Weekly digest engagement for Adam/Mario
- False positive rate (jobs they reject vs accept)
- User satisfaction scores

---

## Next Steps

1. **Create GitHub issue** for tracking
2. **Get approval** from Adam (product owner)
3. **Branch:** `feature/relative-seniority-scoring`
4. **Implement** Phase 1 (core algorithm)
5. **Test** with all profiles
6. **Deploy** and rescore jobs
7. **Monitor** and iterate
