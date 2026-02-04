# Scoring System Update Checklist

**Use this checklist whenever updating the job scoring system to ensure all components stay in sync.**

## Files That Must Be Updated Together

When updating scoring criteria in `src/agents/job_scorer.py`:

### 1. ✅ Core Scoring Logic
- [ ] `src/agents/job_scorer.py` - Update scoring methods
- [ ] `config/filter-keywords.json` - Update role category keywords (if applicable)

### 2. ✅ Email Template
- [ ] `src/send_digest_to_wes.py` (lines 222-238) - Update scoring explanation in email footer
  - Ensure categories match
  - Ensure point ranges match
  - Ensure penalties/bonuses are documented

### 3. ✅ Documentation
- [ ] `CLAUDE.md` - Update "Job Scoring Engine" section if categories/ranges change
- [ ] Consider updating README.md if user-facing changes

### 4. ✅ Tests
- [ ] `tests/unit/test_job_scorer.py` - Update or add tests for new scoring logic
- [ ] Run full test suite: `PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v`
- [ ] Verify coverage remains at 80%+

### 5. ✅ Historical Data
- [ ] Run `src/rescore_all_jobs.py --dry-run` to see impact on existing jobs
- [ ] Consider running actual rescore if changes are significant
- [ ] Document notable changes in PR description

## PR Template Addition

Add this to PR descriptions when updating scoring:

```markdown
## Scoring System Changes

- [ ] Updated job_scorer.py with new criteria
- [ ] Updated email template to match
- [ ] Updated documentation (CLAUDE.md, README.md)
- [ ] Added/updated tests
- [ ] Ran rescore_all_jobs.py dry-run (attach results)
```

## Common Mistakes to Avoid

1. **Forgetting email template** - Users see outdated scoring explanation
2. **Forgetting to update tests** - Tests fail or don't cover new logic
3. **Not re-scoring historical data** - Miss opportunities that now qualify
4. **Documentation drift** - CLAUDE.md becomes outdated

## Seniority Scoring System (Issue #244)

**Current Implementation**: Relative seniority scoring (as of 2026-02-03)

The system uses a **9-level seniority hierarchy** and scores jobs based on how well they match the candidate's `target_seniority`:

**Seniority Hierarchy**:
- Level 0: Junior, Entry-level, Intern
- Level 1: Mid-level, Engineer (IC without "senior")
- Level 2: Senior, Staff, Principal
- Level 3: Lead, Team Lead, Tech Lead
- Level 4: Architect, Distinguished, Fellow
- Level 5: Manager, Engineering Manager
- Level 6: Director, Senior Manager
- Level 7: VP, Head of, Executive Director
- Level 8: Chief, CTO, CPO

**Scoring**:
- Perfect match to target: 30 points
- One level away: 25 points
- Two levels away: 15 points
- Three levels away: 10 points
- Four+ levels away: 5 points

**When updating seniority scoring**:
- If adding/removing levels, update `SENIORITY_HIERARCHY` in `src/agents/base_scorer.py`
- If changing point values, update `_score_seniority()` method
- Always update this checklist with the new hierarchy
- Test across all profiles to ensure no regressions

## Automation Ideas

### Pre-commit Hook (Future)
Could add a pre-commit hook that checks if `job_scorer.py` changed and reminds about email template.

### Test Coverage
Ensure tests validate that scoring categories in tests match actual categories in code.
