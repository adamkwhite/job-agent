# LinkedIn Connections Matching - Product Requirements Document

**Feature Name:** LinkedIn Connections Matching
**Status:** IN_PROGRESS
**Created:** 2025-12-11
**Owner:** Adam White
**GitHub Issue:** #134

## Overview

Enable users to see their LinkedIn connections at companies featured in job digests, helping them leverage their professional network for referrals, insights, and stronger applications.

## Problem Statement

Job seekers reviewing dozens of job postings have no visibility into which companies they already have connections at. This represents a significant missed opportunity:

- **Referrals:** Internal referrals dramatically increase interview rates (3-5x industry standard)
- **Insights:** Connections can provide insider information about company culture, team dynamics, and hiring processes
- **Application Strength:** Mentioning mutual connections in cover letters/applications shows genuine interest

Currently, users must manually cross-reference each company name against their LinkedIn network, a tedious and error-prone process that rarely happens in practice.

## Goals

### Primary Goals
1. **Reduce friction in leveraging professional networks** - Automatically surface connection data during job review
2. **Increase application success rates** - Help users identify referral opportunities
3. **Improve decision-making** - Provide social proof/insights to aid in prioritizing applications

### Secondary Goals
1. **Privacy-first design** - Keep LinkedIn data local, no external API calls
2. **Zero-configuration for MVP** - Work with standard LinkedIn CSV exports
3. **Minimal database changes** - Avoid complex schema migrations for v1

## Success Criteria

- [ ] Users can upload LinkedIn connections CSV export
- [ ] Digest emails show connection counts for companies with 1+ connections
- [ ] HTML job report displays connection names and titles
- [ ] System handles company name variations (e.g., "Boston Dynamics" vs "Boston Dynamics, Inc.")
- [ ] 80%+ test coverage for new code
- [ ] All SonarCloud quality gates pass
- [ ] No performance degradation in digest generation (<5% increase in processing time)

## Requirements

### Functional Requirements

**FR1:** System must accept LinkedIn connections CSV export file
- Standard LinkedIn export format (Connections.csv)
- Fields: First Name, Last Name, Email Address, Company, Position, Connected On

**FR2:** System must parse and store connection data
- Store in lightweight format (CSV or JSON in `data/` directory)
- No PII in main database (privacy consideration)

**FR3:** System must match connections to job companies
- Fuzzy matching to handle company name variations
- Case-insensitive matching
- Handle common suffixes (Inc., LLC, Corp., Ltd.)

**FR4:** Digest emails must display connection information
- Format: "👥 You have 2 connections at Boston Dynamics"
- Show only for jobs with 1+ connections
- Include in job metadata section

**FR5:** HTML job report must show detailed connection info
- Display connection names and job titles
- Group by company
- Sortable/filterable by connection count

**FR6:** System must support profile-specific connections
- Each user profile can upload their own connections CSV
- Connections data stored separately per profile
- Digest shows connections relevant to that profile

### Technical Requirements

**TR1:** LinkedIn CSV parser
- Handle UTF-8 encoding
- Robust error handling for malformed CSV
- Validate required fields exist

**TR2:** Company name matching algorithm
- Use fuzzy string matching (rapidfuzz library)
- Configurable similarity threshold (default: 85%)
- Cache matches to avoid repeated computation

**TR3:** Data storage
- Store connections in `data/profiles/{profile_name}/connections.csv`
- Load on-demand during digest generation
- No database schema changes for v1

**TR4:** Performance optimization
- Lazy load connections data
- In-memory caching during single digest run
- Process only companies in current digest batch

### Non-Functional Requirements

**NFR1:** Privacy & Security
- Connections data never leaves local system
- No API calls to external services
- User controls their own data (can delete anytime)

**NFR2:** Maintainability
- Type hints for all new code
- Comprehensive docstrings
- Unit tests for all matching logic

**NFR3:** Performance
- Digest generation time increase < 5%
- Support up to 5,000 connections without degradation
- Company matching < 50ms per job

**NFR4:** User Experience
- Clear error messages for CSV upload failures
- Graceful degradation if connections file missing
- Visual distinction in digest for high-connection jobs (3+ connections)

## User Stories

### As Wes (Robotics Executive)
- **US1:** I want to upload my LinkedIn connections CSV so the system knows my professional network
- **US2:** When I receive my weekly digest, I want to see "👥 3 connections" next to companies where I know people
- **US3:** I want to click through to the HTML report and see the names of my connections at each company
- **US4:** I want connections to be highlighted for VP/Director roles at robotics companies (higher priority)

### As Adam (Software Professional)
- **US5:** I want my connections data to be separate from Wes's data
- **US6:** I want to easily update my connections CSV when my network grows
- **US7:** I want to see which of my connections work at startups in my digest

## Technical Specifications

### LinkedIn CSV Format

Expected columns from LinkedIn export:
```csv
First Name,Last Name,Email Address,Company,Position,Connected On
John,Doe,john@example.com,Boston Dynamics,Senior Engineer,01 Jan 2023
```

### Data Storage Structure

```
data/
  profiles/
    wes/
      connections.csv           # Wes's LinkedIn connections
      connections_cache.json    # Company match cache
    adam/
      connections.csv           # Adam's LinkedIn connections
      connections_cache.json    # Company match cache
```

### Company Matching Logic

```python
from rapidfuzz import fuzz

def match_company(job_company: str, connection_companies: list[str]) -> list[str]:
    """
    Match job company name against connection company names.

    Returns list of matching connection companies (fuzzy match >= 85%)
    """
    matches = []
    job_company_clean = normalize_company_name(job_company)

    for conn_company in connection_companies:
        conn_company_clean = normalize_company_name(conn_company)
        score = fuzz.ratio(job_company_clean, conn_company_clean)

        if score >= 85:
            matches.append(conn_company)

    return matches

def normalize_company_name(name: str) -> str:
    """Remove common suffixes and normalize spacing."""
    suffixes = [', Inc.', ' Inc.', ', LLC', ' LLC', ', Corp.', ' Corp.', ', Ltd.', ' Ltd.']
    name_clean = name.strip()

    for suffix in suffixes:
        if name_clean.endswith(suffix):
            name_clean = name_clean[:-len(suffix)]

    return name_clean.lower().strip()
```

### Email Template Enhancement

```html
<!-- In send_profile_digest.py email template -->
<tr>
  <td>
    <strong>Boston Dynamics</strong><br>
    Director of Robotics Engineering<br>
    Score: 87/115 (A)

    <!-- NEW: Connection info -->
    {{#if connections}}
      <div style="margin-top: 8px; padding: 8px; background: #f0f7ff; border-left: 3px solid #0066cc;">
        👥 You have {{connections.count}} connection{{#if connections.plural}}s{{/if}} here
      </div>
    {{/if}}
  </td>
</tr>
```

### HTML Report Enhancement

```html
<!-- In jobs.html template -->
<div class="job-card">
  <h3>Director of Robotics - Boston Dynamics</h3>
  <p class="score">Score: 87/115 (A)</p>

  <!-- NEW: Connections section -->
  {{#if connections}}
    <div class="connections-section">
      <h4>👥 Your Connections ({{connections.count}})</h4>
      <ul>
        {{#each connections.people}}
          <li>
            <strong>{{firstName}} {{lastName}}</strong> - {{position}}
          </li>
        {{/each}}
      </ul>
    </div>
  {{/if}}
</div>
```

## Dependencies

### External Dependencies
- **rapidfuzz** (≥3.0.0) - Fast fuzzy string matching library
- Already in requirements.txt or needs to be added

### Internal Dependencies
- `src/send_profile_digest.py` - Email digest generator (needs updates)
- `src/generate_jobs_html.py` - HTML report generator (needs updates)
- `src/models/profile_manager.py` - Profile data management (connections storage path)

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Add rapidfuzz to requirements.txt
- [ ] Create ConnectionsManager class
- [ ] Implement CSV parser with validation
- [ ] Implement company name normalization
- [ ] Implement fuzzy matching algorithm
- [ ] Write unit tests for matching logic (target: 95% coverage)

### Phase 2: Integration (Week 1)
- [ ] Add connections loading to digest generation
- [ ] Update email template with connection counts
- [ ] Update HTML report with connection details
- [ ] Add CLI command for uploading connections CSV
- [ ] Test with real LinkedIn export data

### Phase 3: Polish & Documentation (Week 1)
- [ ] Error handling for missing/malformed CSV
- [ ] Performance testing with 1,000+ connections
- [ ] Update user documentation (README.md)
- [ ] Add TUI option for uploading connections
- [ ] Integration tests for full workflow

## Risks and Mitigation

### Risk 1: Company Name Matching Accuracy
**Impact:** Medium - False negatives (missed connections) or false positives (wrong matches)
**Mitigation:**
- Start with conservative 85% similarity threshold
- Add manual override/mapping file for common mismatches
- Log all matches with confidence scores for tuning
- Allow users to review matches in HTML report

### Risk 2: Privacy Concerns
**Impact:** High - Users uncomfortable with storing network data
**Mitigation:**
- Keep all data local (no cloud/API)
- Clear documentation on data usage
- Easy deletion mechanism
- Optional feature (users opt-in)

### Risk 3: Performance Degradation
**Impact:** Medium - Digest generation becomes slow with large networks
**Mitigation:**
- Lazy loading (only load when generating digest)
- In-memory caching during single run
- Profile-specific data (don't load all profiles' connections)
- Benchmark with 5,000 connection dataset

### Risk 4: LinkedIn Export Format Changes
**Impact:** Low - LinkedIn changes CSV format, breaks parser
**Mitigation:**
- Version detection in CSV parser
- Flexible column mapping
- Clear error messages if format unrecognized
- Fallback to manual column specification

## Out of Scope (v1)

### Explicitly NOT Included
1. **API Integration** - No LinkedIn API, Dex, Apollo.io (v2 consideration)
2. **Automatic Sync** - Manual CSV upload only (no auto-refresh)
3. **Connection Insights** - No "strength of connection" scoring
4. **Multi-degree Connections** - Only direct connections (2nd/3rd degree in v2)
5. **Mutual Connections** - Don't show "You and Wes both know..."
6. **Historical Tracking** - No "connection added on" timeline
7. **Email Notifications** - No "new connection at company you applied to"
8. **Mobile App** - Web/email only

### Future Enhancements (v2+)
- API integration for real-time sync
- Connection strength scoring (recency, interaction frequency)
- 2nd/3rd degree connection discovery
- Company insights from connections (tenure, job satisfaction signals)
- Integration with application tracking

## Acceptance Criteria

### Data Management
- [ ] User can upload LinkedIn connections CSV via CLI: `python src/upload_connections.py --profile wes connections.csv`
- [ ] System validates CSV has required columns
- [ ] System shows clear error if CSV malformed
- [ ] Connections data stored in `data/profiles/{profile}/connections.csv`
- [ ] User can delete connections data: `rm data/profiles/wes/connections.csv`

### Matching Logic
- [ ] "Boston Dynamics" matches "Boston Dynamics, Inc." (100% confidence)
- [ ] "Google" matches "Google LLC" (100% confidence)
- [ ] "Meta" matches "Meta Platforms, Inc." (100% confidence)
- [ ] Case-insensitive: "NVIDIA" matches "Nvidia Corporation"
- [ ] No false positives: "Apple" does NOT match "Applebee's"

### Email Digest Display
- [ ] Jobs with 1 connection show: "👥 You have 1 connection at {Company}"
- [ ] Jobs with 2+ connections show: "👥 You have {N} connections at {Company}"
- [ ] Jobs with 0 connections show nothing (no visual clutter)
- [ ] Connection info appears below job title/score
- [ ] Styling distinct but not overwhelming

### HTML Report Display
- [ ] Connection section shows all matching connections
- [ ] Each connection shows: First Name, Last Name, Position
- [ ] Connections grouped by company
- [ ] Jobs sortable by connection count (high to low)
- [ ] Filter jobs: "Show only jobs with connections"

### Performance
- [ ] Digest generation time increase < 5% with 1,000 connections
- [ ] Company matching < 50ms per job
- [ ] Memory usage increase < 50MB for 5,000 connections

### Testing
- [ ] Unit test coverage ≥ 80% for new code
- [ ] All tests pass locally
- [ ] All SonarCloud quality gates pass
- [ ] Pre-commit hooks pass (ruff, mypy, bandit)

### Documentation
- [ ] README.md updated with connections upload instructions
- [ ] CLAUDE.md updated with architecture notes
- [ ] Code includes comprehensive docstrings
- [ ] CLI help text explains usage

## Open Questions

1. **Caching Strategy:** Should we cache company matches across digest runs?
   → **Decision:** Yes, cache in `connections_cache.json` per profile

2. **Similarity Threshold:** 85% or 90% for fuzzy matching?
   → **Decision:** Start with 85%, make configurable later

3. **Display Priority:** Show connection count in subject line?
   → **Decision:** No for v1, subject line stays clean

4. **CSV Column Flexibility:** What if LinkedIn export has different column names?
   → **Decision:** Strict validation for v1, flexible mapping in v2

## Success Metrics

### Qualitative
- User feedback positive on seeing connections
- Users report using connections for referrals
- Feature described as "helpful" in user testing

### Quantitative
- \>50% of active users upload connections CSV within 2 weeks
- Digest emails with connections have 20% higher open rate
- Users click "view full report" 15% more often when connections present

## Related Work

- **Issue #133:** Email feedback automation (similar digest enhancements)
- **Issue #131:** Company monitoring expansion (company data quality)
- **Multi-profile system:** Existing infrastructure for per-user data

---

**Document Status:** DRAFT - Ready for Implementation
**Last Updated:** 2025-12-11 23:45 EST
**Next Review:** After Phase 1 completion
