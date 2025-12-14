# Digest Quality Issues - Analysis

## Problem Summary

Jobs that shouldn't reach Wes's digest are getting through the scoring/filtering system.

## Examples from Latest Digest (2025-12-13)

### 1. Stale Jobs (No Longer Accepting Applications)
- **Miovision** - https://www.linkedin.com/jobs/view/4336860052
- **Unknown Company** - https://www.linkedin.com/jobs/view/4325664206/
- **Status**: Both show "no longer accepting applications"
- **Root Cause**: No job validation/freshness check before digest
- **Related**: Issue #121 "Integrate JobValidator into email processing pipeline"

### 2. Wrong Role Type - Software Engineering
- **MLSE** - Director, Software Engineering
- **URL**: https://www.linkedin.com/jobs/view/4342890858/
- **Why Wrong**: Wes's profile avoids pure software engineering roles
- **Profile Setting**: `filtering.software_engineering_avoid` includes "software engineering"
- **Root Cause**: Filter applies penalty (-20 points) but doesn't hard-block

### 3. Wrong Role Type - HR/People Operations
- **Knix** - Director, People Operations (Contract)
- **URL**: https://jobs.lever.co/knix/77532ca2-5994-4200-bd14-26f8936bc604
- **Why Wrong**: HR/People Ops role, not engineering/product leadership
- **Root Cause**: No HR/non-technical role filter in scoring system

### 4. Wrong Seniority Level
- **Lululemon** - Associate Principal Product Manager | Contract until October 2026
- **URL**: https://www.linkedin.com/jobs/view/4349863017/
- **Why Wrong**: "Associate" level, not Director/VP
- **Profile Setting**: `avoid_keywords` includes "associate"
- **Root Cause**: "Associate" gives penalty but "Principal" gives +15 points (net positive score)

## Current Scoring System Analysis

### Scoring Categories (0-115 total)
1. **Seniority** (0-30): VP/Chief (30), Director (25), Principal (15), Manager (10)
2. **Domain** (0-25): Robotics, hardware, automation keywords
3. **Role Type** (0-20): Engineering vs Product leadership
4. **Location** (0-15): Remote, Hybrid Ontario, Ontario cities
5. **Company Stage** (0-15): Series A-C, growth stage
6. **Technical** (0-10): Mechatronics, embedded, manufacturing

### Avoid Keywords (Currently NOT Enforced)
- Listed in profile: `["junior", "associate", "intern", "coordinator"]`
- **Problem**: These are defined but NOT used as hard filters
- Jobs with these keywords can still score high enough to pass

### Software Engineering Filter (Moderate Aggression)
- Applies -20 point penalty for software engineering roles
- **Problem**: Penalty system, not hard block
- **Example**: Director of Software Engineering can still score 60+ and pass

### Missing Filters
- **HR/People Operations roles**: No detection or filtering
- **Contract/temporary positions**: No special handling
- **Stale job detection**: No validation before digest

## Proposed Solutions

### 1. Hard Filters (Pre-Scoring)
Reject jobs BEFORE scoring if they match:
- Avoid keywords in title: junior, associate, intern, coordinator
- HR/People role keywords: "people operations", "human resources", "hr manager", "talent acquisition", "recruiting"
- Contract/temp keywords (optional): "contract", "temporary", "interim" (if seniority < Director)

### 2. Stale Job Validation
- Check LinkedIn jobs for "no longer accepting applications"
- Check job posting age (filter if >90 days old)
- Verify job URL is still active before digest

### 3. Software Engineering Filter Enhancement
- Change from penalty (-20) to hard filter
- Exception: Keep if title contains "hardware", "product", or domain keywords

### 4. Role Type Categories
Add explicit role type detection:
- Engineering Leadership: ✅ Allow
- Product Leadership: ✅ Allow
- Software Engineering: ❌ Block (unless hardware/product)
- HR/People Ops: ❌ Block
- Finance/Legal/Admin: ❌ Block

## Files to Modify

1. **`src/agents/job_scorer.py`**
   - Add hard filter checks before scoring
   - Implement HR role detection
   - Make software engineering filter stricter

2. **`src/send_profile_digest.py`**
   - Integrate stale job validation
   - Add URL verification before digest
   - Related to Issue #121

3. **`config/filter-keywords.json`**
   - Add HR/People Ops keywords
   - Add non-technical role categories
   - Expand avoid keywords if needed

4. **`profiles/wes.json`**
   - Add hard_filter_keywords (blocking, not penalties)
   - Add excluded_role_types list
   - Keep soft avoid_keywords for penalties only

## Open Questions

1. Should contract/temporary positions be filtered for junior roles but allowed for Director+?
2. What's the threshold for "stale" jobs? 30 days? 60 days? 90 days?
3. Should "Associate Principal" be allowed or blocked? (Principal modifier vs Associate)
4. Should we add a "confidence score" for role type detection?
5. Keep penalty system for some cases, or move all to hard filters?

## Related Work

- **Issue #121**: Integrate JobValidator (stale job detection)
- **Issue #122**: Company Classification Filtering (software vs hardware)
- **PR #153**: Email review list for failed extractions
- **Profile system**: Multi-profile scoring in `profiles/*.json`
