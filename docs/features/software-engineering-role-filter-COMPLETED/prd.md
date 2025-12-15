# PRD: Software Engineering Role Filtering for Hardware-Focused Profiles

## Overview

Implement a comprehensive role type + domain filtering system to prevent software engineering leadership roles from appearing in hardware-focused job digests, while maintaining product leadership matches across all company types. This feature will use a multi-signal company classification system with configurable aggression levels and manual override capabilities.

## Problem Statement

Wes van Ooyen is receiving too many software engineering leadership roles in his digest that don't match his hardware/robotics expertise. His feedback: _"These roles are almost exclusively software. An area I don't feel like I have technical expertise in. I'm really wanting to focus my search on hardware companies."_

**Current Issue:**
- System scores all engineering leadership equally, regardless of company domain
- No distinction between software vs hardware company contexts
- Product leadership expertise transfers across domains, but engineering leadership does not
- Latest digest included roles like "Program Director" at software-focused companies (scored 80/115 B grade)

**Critical Distinctions:**
- ❌ **NOT a fit**: Engineering leadership at software companies (VP Eng at SaaS, Director of Software Engineering)
- ✅ **IS a fit**: Product leadership at ANY company (VP Product at SaaS is fine)
- ✅ **IS a fit**: Engineering leadership at hardware/robotics companies (VP Eng at Boston Dynamics)

**Real Examples from Latest Digest:**
```
❌ "Program Director" at "Jobs via Dice" (software-focused, 80/115 B grade)
❌ "VP of Engineering" at SaaS/fintech companies
✅ "VP of Product" at any company (product expertise transfers)
✅ "VP of Engineering" at Boston Dynamics (hardware/robotics)
```

## Goals

### Primary Goals
1. **Reduce software engineering noise** - Eliminate 80%+ of software engineering leadership roles from Wes's digest
2. **Increase hardware match rate** - Boost hardware engineering leadership matches by 50%+
3. **Preserve product matches** - Maintain or increase product leadership matches across all company types
4. **Multi-profile framework** - Build generic system usable by all profiles, not just Wes-specific

### Secondary Goals
5. **Configurable aggression** - Allow users to tune filtering sensitivity via TUI and config
6. **Manual overrides** - Enable users to correct company classifications (software/hardware/both)
7. **Transparency** - Log filtering decisions for debugging and validation
8. **Extensibility** - Design for future expansion to other role type + domain combinations

## Success Criteria

- [ ] Wes's digest shows 80%+ reduction in software engineering roles
- [ ] Hardware engineering leadership matches increase by 50%+
- [ ] Product leadership matches maintained or increased across all company types
- [ ] System works for all enabled profiles (Wes, Adam, Eli)
- [ ] Configurable aggression levels (conservative, moderate, aggressive)
- [ ] Manual company classification overrides functional
- [ ] All tests passing with 80%+ coverage on new code
- [ ] Tested against recent digest data (verify "Program Director" filtered)

## Requirements

### Functional Requirements

**FR1: Multi-Signal Company Classification**
- FR1.1: Classify companies as "software", "hardware", "both", or "unknown"
- FR1.2: Use keyword matching in company name (e.g., "saas", "fintech", "software", "robotics")
- FR1.3: Maintain curated lists of known hardware companies (Boston Dynamics, Figure, Sanctuary AI, etc.)
- FR1.4: Check job domain keywords against hardware terms (robotics, mechatronics, embedded, etc.)
- FR1.5: Combine multiple signals with weighted scoring for classification confidence

**FR2: Role Type Detection**
- FR2.1: Identify "engineering leadership" roles (VP Eng, Director of Engineering, etc.)
- FR2.2: Identify "product leadership" roles (VP Product, CPO, etc.)
- FR2.3: Handle dual roles (Product Engineering, Technical Product Manager)
- FR2.4: Use existing `role_types` from profile configuration

**FR3: Filtering Logic**
- FR3.1: Filter out "engineering leadership" + "software company" combinations
- FR3.2: Allow "product leadership" + any company type
- FR3.3: Allow "engineering leadership" + "hardware company" combinations
- FR3.4: Apply profile-specific `software_engineering_avoid` keywords as additional filter
- FR3.5: Log filtering decisions with classification reasoning

**FR4: Configurable Aggression Levels**
- FR4.1: Conservative mode - Only filter obvious software engineering roles ("VP of Software Engineering")
- FR4.2: Moderate mode (default) - Filter engineering roles at companies with software-heavy keywords
- FR4.3: Aggressive mode - Filter any engineering role without explicit hardware/robotics keywords
- FR4.4: Store aggression level in profile configuration
- FR4.5: Allow selection via TUI interface

**FR5: Manual Company Overrides**
- FR5.1: Store user-provided company classifications in database
- FR5.2: Allow marking companies as "software", "hardware", "both", or "unknown"
- FR5.3: Manual overrides take precedence over automated classification
- FR5.4: Expose override interface via TUI (future: Issue #119)
- FR5.5: Log override actions with timestamp and user

**FR6: Scoring Integration**
- FR6.1: Apply scoring penalty (-20 points) for filtered software engineering roles
- FR6.2: Apply scoring boost (+10 points) for hardware company matches
- FR6.3: Maintain existing scoring for product leadership roles
- FR6.4: Store classification metadata in `job_scores` table

### Technical Requirements

**TR1: Database Schema**
- TR1.1: Add `company_classifications` table with columns: `company_name`, `classification` (enum), `confidence_score`, `source` (auto/manual), `created_at`, `updated_at`
- TR1.2: Add `classification_metadata` JSON field to `job_scores` table
- TR1.3: Add indexes on `company_name` and `classification` for performance

**TR2: Profile Configuration**
- TR2.1: Add `software_engineering_avoid` array to profile schema
- TR2.2: Add `filtering_aggression` field (conservative/moderate/aggressive)
- TR2.3: Validate profile configuration on load
- TR2.4: Provide sensible defaults for existing profiles

**TR3: Code Organization**
- TR3.1: Create `src/utils/company_classifier.py` for classification logic
- TR3.2: Extend `src/agents/job_scorer.py` with filtering integration
- TR3.3: Add classification logic to scoring pipeline
- TR3.4: Create `config/company_classifications.json` for curated lists

**TR4: Testing**
- TR4.1: Unit tests for company classifier (20+ test cases)
- TR4.2: Unit tests for filtering logic (15+ test cases)
- TR4.3: Integration tests with real digest data
- TR4.4: Edge case tests (unknown companies, dual-domain companies)
- TR4.5: Achieve 80%+ code coverage on new modules

### Non-Functional Requirements

**NFR1: Performance**
- NFR1.1: Company classification must complete in <100ms per job
- NFR1.2: Cache classification results to avoid re-computation
- NFR1.3: Batch classification for digest generation

**NFR2: Maintainability**
- NFR2.1: Clear separation between classification logic and scoring logic
- NFR2.2: Documented company classification algorithm
- NFR2.3: Logging at INFO level for classification decisions
- NFR2.4: Logging at DEBUG level for classification signals

**NFR3: Extensibility**
- NFR3.1: Design to support future role type + domain combinations
- NFR3.2: Generic framework not specific to Wes's profile
- NFR3.3: Easy to add new company classification signals

**NFR4: User Experience**
- NFR4.1: Clear feedback when jobs are filtered
- NFR4.2: Ability to review filtered jobs (future: TUI improvement)
- NFR4.3: Transparent classification reasoning in logs

## User Stories

### As Wes (Hardware Engineering Executive)
- **Story 1**: As Wes, I want software engineering leadership roles filtered from my digest, so I only see opportunities matching my hardware/robotics expertise
- **Story 2**: As Wes, I want product leadership roles at ANY company, because my product expertise transfers across domains
- **Story 3**: As Wes, I want engineering leadership roles at hardware companies, because that's where my technical expertise is valuable

### As Adam (Software Product Manager)
- **Story 4**: As Adam, I want software product leadership roles prioritized, while filtering out pure hardware engineering roles I'm not qualified for
- **Story 5**: As Adam, I want to adjust filtering aggression based on how selective I want to be

### As System Administrator
- **Story 6**: As an admin, I want to review filtered jobs to validate the classification system is working correctly
- **Story 7**: As an admin, I want to manually override incorrect company classifications when the automated system fails
- **Story 8**: As an admin, I want to understand why jobs were filtered for debugging and improvement

## Technical Specifications

### Company Classifier Algorithm

```python
class CompanyClassifier:
    """Multi-signal company classification system"""

    def classify_company(
        self,
        company_name: str,
        job_title: str = "",
        job_description: str = "",
        domain_keywords: list[str] = []
    ) -> CompanyClassification:
        """
        Classify company using multiple signals

        Returns:
            CompanyClassification with fields:
            - type: "software" | "hardware" | "both" | "unknown"
            - confidence: float (0.0-1.0)
            - signals: dict of signal contributions
        """
        # Check manual overrides first
        if manual_override := self.get_manual_override(company_name):
            return manual_override

        signals = {}

        # Signal 1: Company name keywords (weight: 0.3)
        signals['name'] = self._check_company_name_keywords(company_name)

        # Signal 2: Curated company list (weight: 0.4)
        signals['curated'] = self._check_curated_lists(company_name)

        # Signal 3: Domain keyword matching (weight: 0.2)
        signals['domain'] = self._check_domain_keywords(domain_keywords)

        # Signal 4: Job title/description analysis (weight: 0.1)
        signals['job_content'] = self._analyze_job_content(job_title, job_description)

        # Combine signals with weights
        classification = self._combine_signals(signals)

        return classification
```

### Filtering Decision Logic

```python
def should_filter_job(
    job: Job,
    profile: Profile,
    company_classification: CompanyClassification,
    aggression_level: str = "moderate"
) -> tuple[bool, str]:
    """
    Determine if job should be filtered based on role type + domain

    Returns:
        (should_filter: bool, reason: str)
    """
    role_type = classify_role_type(job.title, profile.role_types)

    # Product leadership always passes (any company)
    if role_type == "product_leadership":
        return (False, "product_leadership_any_company")

    # Engineering leadership depends on company type
    if role_type == "engineering_leadership":
        if company_classification.type == "software":
            # Apply aggression level logic
            if aggression_level == "conservative":
                # Only filter if title contains explicit software keywords
                if any(kw in job.title.lower() for kw in ["software engineering", "vp of software"]):
                    return (True, "software_engineering_explicit")

            elif aggression_level == "moderate":  # DEFAULT
                # Filter if company is classified as software with medium+ confidence
                if company_classification.confidence >= 0.6:
                    return (True, "software_company_moderate_confidence")

            elif aggression_level == "aggressive":
                # Filter any engineering role without explicit hardware keywords
                hardware_keywords = ["hardware", "robotics", "mechatronics", "embedded"]
                if not any(kw in job.title.lower() for kw in hardware_keywords):
                    return (True, "no_hardware_keywords_aggressive")

        elif company_classification.type == "hardware":
            return (False, "hardware_company_engineering_match")

        elif company_classification.type == "both":
            # Dual-domain companies need additional context
            # Check job description for hardware vs software focus
            return self._analyze_dual_domain_job(job, profile)

    return (False, "no_filter_applied")
```

### Configuration Schema

```json
{
  "profiles/wes.json": {
    "filtering": {
      "aggression_level": "moderate",
      "software_engineering_avoid": [
        "software engineer", "software engineering",
        "vp of software", "director of software",
        "frontend", "backend", "full stack",
        "web developer", "mobile app", "devops",
        "cloud engineer", "saas", "fintech software"
      ],
      "hardware_company_boost": 10,
      "software_company_penalty": -20
    }
  }
}
```

```json
{
  "config/company_classifications.json": {
    "hardware_companies": [
      "Boston Dynamics", "Figure", "Sanctuary AI",
      "Agility Robotics", "1X Technologies", "Skydio",
      "Skild AI", "Dexterity", "Covariant", "Nuro"
    ],
    "software_companies": [
      "Stripe", "Shopify", "Atlassian", "Slack", "Zoom"
    ],
    "both_domains": [
      "Tesla", "Apple", "Amazon", "Google"
    ]
  }
}
```

### Database Migrations

```sql
-- Migration: Add company_classifications table
CREATE TABLE company_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    classification TEXT NOT NULL CHECK(classification IN ('software', 'hardware', 'both', 'unknown')),
    confidence_score REAL NOT NULL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
    source TEXT NOT NULL CHECK(source IN ('auto', 'manual')),
    signals JSON,  -- Store classification signal breakdown
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_company_classifications_name ON company_classifications(company_name);
CREATE INDEX idx_company_classifications_type ON company_classifications(classification);

-- Migration: Add classification metadata to job_scores
ALTER TABLE job_scores ADD COLUMN classification_metadata JSON;
```

## Dependencies

### External Dependencies
- None (uses existing libraries)

### Internal Dependencies
- `src/agents/job_scorer.py` - Integration point for filtering logic
- `profiles/*.json` - Profile configuration schema updates
- `src/database/models.py` - Database schema extensions
- `src/tui.py` - Future TUI integration for manual overrides (Issue #119)

## Timeline

### Phase 1: Core Classification System (Week 1)
- Implement `CompanyClassifier` with multi-signal approach
- Create curated company lists configuration
- Add database schema for company classifications
- Unit tests for classifier (20+ tests)
- **Deliverable**: Working classification system with 85%+ accuracy

### Phase 2: Filtering Integration (Week 1-2)
- Extend `job_scorer.py` with filtering logic
- Implement aggression level logic (conservative/moderate/aggressive)
- Add profile configuration for filtering preferences
- Integration tests with real digest data
- **Deliverable**: Filtered digest for Wes with 80%+ software role reduction

### Phase 3: Manual Overrides & Polish (Week 2)
- Implement manual company classification overrides
- Add comprehensive logging and debugging output
- Validate against recent digest data
- Documentation and CLAUDE.md updates
- **Deliverable**: Production-ready system with manual override capability

### Phase 4: TUI Integration (Future - Issue #119)
- Add company classification review screen
- Enable manual override via TUI
- Display filtering statistics
- **Deliverable**: User-friendly classification management

## Risks and Mitigation

### Risk 1: Dual-Domain Companies (Tesla, Apple, Amazon)
**Impact**: Medium - May incorrectly filter relevant roles at companies doing both hardware and software
**Mitigation**:
- Classify as "both" domain
- Analyze job description for hardware vs software focus
- Allow manual overrides for specific jobs
- Log dual-domain decisions for review

### Risk 2: Classification Accuracy
**Impact**: High - Incorrect classifications lead to missed opportunities or noise
**Mitigation**:
- Multi-signal approach reduces single-point-of-failure
- Confidence scoring allows filtering borderline cases
- Manual override system for corrections
- Comprehensive testing with real job data
- Start with moderate aggression (safer default)

### Risk 3: Performance Degradation
**Impact**: Low - Classification adds processing time to scoring pipeline
**Mitigation**:
- Cache classification results in database
- Batch classify during digest generation
- Target <100ms per job classification
- Profile performance with pytest-benchmark

### Risk 4: Maintenance Burden of Curated Lists
**Impact**: Medium - Company lists need ongoing updates as new companies emerge
**Mitigation**:
- Start with top 50 robotics/hardware companies
- Allow manual additions via overrides
- Log "unknown" classifications for review
- Future: Automated company discovery (Issue #95)

### Risk 5: User Confusion About Filtered Jobs
**Impact**: Medium - Users may miss relevant jobs if filtering is too aggressive
**Mitigation**:
- Default to moderate aggression level
- Add "filtered jobs" review in TUI (Issue #119)
- Comprehensive logging of filter reasons
- Email digest shows "X jobs filtered" summary

## Out of Scope

### Excluded from this PRD
- ❌ **Automated company discovery** - Will be addressed in Issue #95
- ❌ **AI-powered classification** - Current multi-signal approach is sufficient
- ❌ **User-facing classification UI** - Will be addressed in Issue #119 (Textual TUI)
- ❌ **Industry-specific classification** - Focus on software vs hardware only
- ❌ **Geographic company data** - Not needed for classification
- ❌ **Salary range filtering** - Separate feature
- ❌ **Seniority-based filtering** - Already handled by existing scoring

### Future Enhancements
- Automated company classification learning from user feedback
- Integration with external company databases (Crunchbase, LinkedIn)
- Role type + domain combinations beyond engineering/product
- Company size-based filtering
- Industry vertical classification (MedTech, Fintech, etc.)

## Acceptance Criteria

### Functional Acceptance
- [ ] Company classifier correctly identifies Boston Dynamics as "hardware" (confidence >0.8)
- [ ] Company classifier correctly identifies Stripe as "software" (confidence >0.8)
- [ ] Company classifier correctly identifies Tesla as "both" (confidence >0.6)
- [ ] "VP of Engineering" at SaaS company is filtered for Wes
- [ ] "VP of Product" at SaaS company is NOT filtered for Wes
- [ ] "VP of Engineering" at Boston Dynamics is NOT filtered for Wes
- [ ] "Program Director" at "Jobs via Dice" is filtered (real example)
- [ ] All three aggression levels work correctly (conservative, moderate, aggressive)
- [ ] Manual company override persists in database
- [ ] Manual override takes precedence over automated classification

### Technical Acceptance
- [ ] All unit tests passing (50+ tests total)
- [ ] Code coverage ≥80% on new modules
- [ ] Integration test with recent digest shows 80%+ reduction in software roles
- [ ] Performance benchmark: <100ms per job classification
- [ ] Database migrations run successfully
- [ ] Profile schema validation passes
- [ ] Logging output is clear and actionable

### Documentation Acceptance
- [ ] CLAUDE.md updated with filtering system explanation
- [ ] Profile schema documented in README.md
- [ ] Company classification algorithm documented in code
- [ ] Aggression level options explained in TUI help text (future)
- [ ] Manual override process documented

## Related Work

- **Issue #4**: Make scoring weights configurable (long-term enhancement)
- **Issue #95**: Automated Robotics Company Monitoring (more hardware job sources)
- **Issue #119**: Textual TUI Migration (future manual override UI)
- **Issue #123**: Add hardware-focused job boards (increase volume)
- **PR #120**: LinkedIn validator fix (quality improvements)
- **Wes's Feedback**: "Almost exclusively software... wanting to focus on hardware companies"

## Open Questions

1. ✅ **Resolved**: Should we maintain curated lists or rely on keyword matching? → Use both with weighted signals
2. ✅ **Resolved**: How aggressive should default filtering be? → Moderate (balance safety and accuracy)
3. ✅ **Resolved**: Should this be Wes-specific or generic? → Generic framework for all profiles
4. ⏳ **Pending**: What companies should be in initial curated lists? → Start with top 50 robotics companies from Issue #95
5. ⏳ **Pending**: How should we handle job descriptions that mention both software and hardware? → Analyze description keywords with weighted scoring

---

**Status**: PLANNED
**Created**: 2025-12-07
**Last Updated**: 2025-12-07
**Owner**: Adam White
**Stakeholder**: Wesley van Ooyen
