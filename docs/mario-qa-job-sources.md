# QA/Testing Job Sources for Mario

## Overview
Mario's profile focuses on QA/testing, systems engineering, and AI safety/governance roles. The current job sources (robotics, product leadership) have a 0.99% success rate for his profile. This guide sets up dedicated QA/testing job sources.

## Target Role Types
Based on Mario's profile:
- **QA Leadership**: QA Lead, QA Manager, Director of Quality, Head of Quality
- **Test Engineering**: Test Automation Lead, Test Architect, SDET Lead
- **Systems Engineering**: Senior Systems Engineer, Systems Architect, Solution Architect
- **AI Safety/Governance**: AI Safety Engineer, AI Evaluation Engineer, AI Reliability Engineer
- **Quality Engineering**: Software Quality Engineer, Quality Assurance Manager

## Recommended Job Sources

### 1. LinkedIn Job Alerts (PRIORITY)
**Why**: Already our best source (2.4% success rate, vs 0.4% for other sources)

**Setup Steps**:
1. Go to linkedin.com/jobs
2. Create saved searches for:
   - "QA Lead" + Remote + Canada
   - "Test Automation Lead" + Remote + Canada
   - "Systems Engineer" + Remote + Canada
   - "SDET" + Remote + Canada
   - "Quality Manager" + Remote + Canada
   - "AI Safety Engineer" + Remote
   - "AI Evaluation" + Remote
3. Click "Create search alert" for each
4. Set frequency to Daily
5. Ensure emails go to: mario.jobalerts@gmail.com (or existing inbox)

**Expected Volume**: ~10-20 jobs/week

### 2. Ministry of Testing Jobs
**URL**: https://www.ministryoftesting.com/jobs
**Why**: Premier QA/testing community with high-quality job postings

**Setup Steps**:
1. Create account at ministryoftesting.com
2. Set job preferences:
   - Location: Remote, Canada
   - Level: Senior, Lead, Manager
   - Type: QA Lead, Test Automation, Quality Engineering
3. Enable email alerts (daily)
4. Forward alerts to: mario.jobalerts@gmail.com

**Expected Volume**: ~5-10 jobs/week

### 3. Test Automation University (Applitools)
**URL**: https://testautomationu.applitools.com/
**Why**: Strong community, Applitools often shares QA job postings

**Setup Steps**:
1. Join TAU Slack community
2. Subscribe to #job-postings channel
3. Set up email digests or check manually weekly

**Expected Volume**: ~3-5 jobs/week

### 4. WeTest Community
**URL**: https://www.wetest.io/ or QA community forums
**Why**: QA-focused job board with Canadian tech companies

**Setup Steps**:
1. Create account
2. Set up job alerts for:
   - Remote QA roles
   - Canadian companies
   - Senior/Lead level
3. Forward to mario.jobalerts@gmail.com

**Expected Volume**: ~2-5 jobs/week

### 5. Canadian Tech Job Boards (Existing - WorkInTech)
**URL**: https://www.workintech.ca/
**Status**: Already active (4% success rate - BEST source!)

**Optimization**:
- Current: Receiving alerts via Wes's email
- Recommendation: Set up direct alerts for:
  - "QA" + Toronto/Remote
  - "Test" + Toronto/Remote
  - "Quality" + Toronto/Remote
  - "Systems Engineer" + Toronto/Remote

**Expected Volume**: Already receiving ~2-3 qualifying jobs/month

### 6. Indeed Job Alerts
**URL**: https://ca.indeed.com/
**Why**: High volume, good coverage of Canadian market

**Setup Steps**:
1. Create account
2. Set up alerts:
   - "QA Lead" + Remote Canada
   - "Test Automation Manager" + Remote Canada
   - "Quality Manager" + Remote Canada
   - "Systems Architect" + Remote Canada
3. Set frequency: Daily
4. Ensure emails go to mario.jobalerts@gmail.com

**Expected Volume**: ~15-30 jobs/week

### 7. Glassdoor Job Alerts
**URL**: https://www.glassdoor.ca/
**Why**: Good for Canadian tech companies, salary transparency

**Setup Steps**:
1. Create account
2. Set up alerts similar to Indeed (above)
3. Filter: Remote, Canada, $100k+ salary
4. Forward to mario.jobalerts@gmail.com

**Expected Volume**: ~10-20 jobs/week

## Email Parser Requirements

Once Mario subscribes, we'll need to create parsers for:
- [ ] Ministry of Testing email format
- [ ] WeTest email format
- [ ] Indeed alerts (may already exist for Wes - check ontario_jobs parser)
- [ ] Glassdoor email format

**Note**: LinkedIn and WorkInTech parsers already exist.

## Email Account Setup

**Option A: Use Existing Outlook**
- Forward job alerts from mario.colina@outlook.com
- Add OUTLOOK_USERNAME and OUTLOOK_APP_PASSWORD to .env
- Update profiles/mario.json with outlook credentials

**Option B: Create Dedicated Gmail**
- Create mario.jobalerts@gmail.com
- Set up app password for IMAP access
- Update .env and profiles/mario.json

**Recommendation**: Option B (cleaner separation, easier debugging)

## Next Steps

1. **Mario**: Set up LinkedIn alerts (10 min) - PRIORITY
2. **Mario**: Create Ministry of Testing account (5 min)
3. **Mario**: Set up Indeed alerts (5 min)
4. **Adam**: Update parser registry when emails start arriving
5. **Adam**: Test parsers with sample emails
6. **Adam**: Consider adjusting Mario's digest settings (see Option 2 below)

## Additional Recommendations (Option 2)

While setting up new sources, also consider:

### Adjust Digest Settings in profiles/mario.json:
```json
"digest": {
  "min_grade": "C",
  "min_score": 35,              // Lower from 47 (QA roles score lower)
  "min_location_score": 8,
  "include_grades": ["A", "B", "C", "D"],  // Add D-grade
  "send_frequency": "daily",
  "max_age_days": 14            // Increase from 7 (niche roles need longer window)
}
```

**Why**: Mario's best job ever scored 62 (C-grade), most qualifying jobs are 47-54 (D-grade). QA roles are rare, so wider net = better results.

## Expected Impact

**Current State**:
- 710 jobs scored, 7 qualified (0.99%)
- 0 jobs in last 7 days
- Digests are empty

**After Implementation**:
- 40-70 new jobs/week from QA-specific sources
- Estimated 5-10% qualification rate (vs 0.99%)
- **2-7 qualifying jobs/week** (vs 0 currently)
- Non-empty digests!

## Timeline

- **Week 1**: Set up LinkedIn, Indeed, Glassdoor (Mario) - 30 min
- **Week 2**: Create parsers for new email formats (Adam) - 2-3 hours
- **Week 3**: Monitor results, adjust scoring if needed
- **Week 4**: Add Ministry of Testing, WeTest if needed

---

**Created**: 2026-01-16
**Status**: Ready to implement
**Owner**: Mario (setup), Adam (parsers)
