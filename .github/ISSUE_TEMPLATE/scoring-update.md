---
name: Scoring System Update
about: Track changes to the job scoring system
title: '[SCORING] '
labels: enhancement, scoring
assignees: ''
---

## Scoring Change Description
<!-- Describe what scoring criteria you want to change -->


## Proposed Changes
<!-- List specific changes to scoring categories, ranges, or penalties -->

- [ ] Seniority (0-30):
- [ ] Domain (0-25):
- [ ] Role Type (0-20):
- [ ] Location (0-15):
- [ ] Company Stage (0-15):
- [ ] Technical Keywords (0-10):

## Implementation Checklist
<!-- DO NOT SKIP - This ensures all components stay in sync -->

### Code Changes
- [ ] Updated `src/agents/job_scorer.py` with new scoring logic
- [ ] Updated `config/filter-keywords.json` (if role categories changed)
- [ ] Updated `tests/unit/test_job_scorer.py` with new test cases
- [ ] All tests pass with 80%+ coverage on new code

### Documentation Updates
- [ ] Updated `src/send_digest_to_wes.py` email template (lines 222-238)
- [ ] Updated `CLAUDE.md` if categories/ranges changed
- [ ] Created/updated `docs/development/SCORING_UPDATE_CHECKLIST.md`

### Historical Data
- [ ] Ran `src/rescore_all_jobs.py --dry-run --min-score 70`
- [ ] Documented impact: X jobs newly qualifying, Y jobs score increased
- [ ] Decided whether to run actual rescore (yes/no and why)

### Verification
- [ ] SonarCloud checks pass (<3% duplication, 80%+ coverage)
- [ ] Pre-commit hooks pass
- [ ] Manual testing completed

## Impact Analysis
<!-- Results from running rescore_all_jobs.py --dry-run -->

```
Total jobs: X
Newly qualifying (70+): X
Score increases: X
Score decreases: X
Grade transitions: [list notable ones]
```

## References
- See `docs/development/SCORING_UPDATE_CHECKLIST.md` for full checklist
