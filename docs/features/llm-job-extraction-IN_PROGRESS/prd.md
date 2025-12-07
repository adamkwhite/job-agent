# PRD: LLM-Based Job Extraction with Parallel Validation

## Status
**PLANNED** - Feature documented, not yet started

## Related Work

### GitHub Issues
- **[#86](https://github.com/adamkwhite/job-agent/issues/86)** - Parent issue: LLM-based job extraction with parallel validation
- **[#87](https://github.com/adamkwhite/job-agent/issues/87)** - [Task 1.0] Database Schema & Migrations
- **[#88](https://github.com/adamkwhite/job-agent/issues/88)** - [Task 2.0] LLM Extractor Core Implementation
- **[#89](https://github.com/adamkwhite/job-agent/issues/89)** - [Task 3.0] Budget Tracking Service Implementation
- **[#90](https://github.com/adamkwhite/job-agent/issues/90)** - [Task 4.0] Dual Extraction Pipeline Integration
- **[#91](https://github.com/adamkwhite/job-agent/issues/91)** - [Task 5.0] Comparison & Metrics Framework
- **[#92](https://github.com/adamkwhite/job-agent/issues/92)** - [Task 6.0] TUI Failure Review Interface
- **[#93](https://github.com/adamkwhite/job-agent/issues/93)** - [Task 7.0] Testing & Validation
- **[#94](https://github.com/adamkwhite/job-agent/issues/94)** - [Task 8.0] Documentation & Deployment

### Related Issues
- **[#78](https://github.com/adamkwhite/job-agent/issues/78)** - Add two-tier progressive scoring to reduce Firecrawl API costs
- **[#83](https://github.com/adamkwhite/job-agent/issues/83)** - Handle Firecrawl API credit limitations and automate MCP calls

## Overview
Migrate from regex-based job extraction to LLM-based extraction for company career pages, running both approaches in parallel during an experimental validation phase. This will improve extraction accuracy for locations, leadership job filtering, and overall job discovery while staying within a strict $5/month API budget.

## Problem Statement

### Current State
The existing regex-based extraction in `CompanyScraperWithFirecrawl._extract_jobs_from_markdown()` has several limitations:

1. **Poor location extraction accuracy** - Struggles with varied formats ("locations Waltham, MA", missing locations, inconsistent structures)
2. **False positives in leadership filtering** - Post-processing keyword matching misses context
3. **Brittle pattern matching** - Requires constant maintenance as career page formats change
4. **Limited semantic understanding** - Cannot distinguish actual leadership roles from mentions

### Evidence from Testing
Exploration tests (`tests/exploration/test_llm_extraction.py`, `test_claude_extraction.py`) demonstrate:
- LLM extraction understands semantic meaning of "leadership"
- Automatic location format cleaning (removes prefixes, standardizes format)
- Handles varied markdown structures without regex pattern updates
- Cost estimate: $0.002-0.015 per page extraction

### Constraints
- **Budget**: <$5/month for LLM API costs (~100-250 extractions)
- **Existing system**: 26+ companies scraped weekly via Firecrawl
- **Cached data**: 18+ Firecrawl markdown files already available for testing
- **Related work**: Issue #78 (two-tier progressive scoring), Issue #83 (Firecrawl credit limits)

## Goals

### Primary Goals
1. **Validate LLM superiority** - Prove LLM extraction outperforms regex on all key metrics
2. **Stay within budget** - Spend <$5/month on LLM API costs
3. **Maintain system reliability** - No regression in job discovery or uptime

### Secondary Goals
1. **Build evaluation framework** - Systematic comparison of regex vs LLM results
2. **Create TUI monitoring** - Manual review interface for LLM failures
3. **Establish migration path** - Clear decision criteria for full rollout

## Success Criteria

**Experimental Phase Complete When:**
- [ ] Both regex and LLM extraction run in parallel for 4+ weeks
- [ ] LLM extraction tested on all 18+ cached Firecrawl files
- [ ] Comprehensive metrics collected on location accuracy, leadership precision, job discovery
- [ ] Cost tracking confirms <$5/month budget adherence
- [ ] TUI interface built for reviewing failed/skipped extractions
- [ ] Decision made on full migration vs hybrid approach

**LLM Extraction Quality Gates:**
- [ ] ≥90% location extraction accuracy (vs current ~40-60% with regex)
- [ ] ≥95% leadership job filtering precision (reduce false positives)
- [ ] ≥10% increase in total leadership jobs discovered
- [ ] <5% LLM extraction failures requiring manual review

## Requirements

### Functional Requirements

**FR1: Dual Extraction Pipeline**
- Both regex and LLM extraction must run on every company scrape
- Results stored separately in database with `extraction_method` field
- No impact to existing job storage/notification flow

**FR2: ScrapeGraphAI Integration**
- Use ScrapeGraphAI library for LLM abstraction
- Support multiple LLM providers (Claude, GPT-4, etc.)
- Configure via `config/llm-extraction-settings.json`

**FR3: Budget Tracking & Limits**
- Track LLM API costs per extraction (token counts, estimated $)
- Hard limit at $5/month - pause LLM extraction when reached
- Daily/weekly cost reports via logging

**FR4: Failure Handling**
- When LLM extraction fails or times out:
  - Log failure with company name, error, timestamp
  - Store in `llm_extraction_failures` database table
  - Continue with regex extraction (no blocking)
  - Surface failures in TUI for manual review

**FR5: Comparison Metrics**
- Calculate and log for each extraction:
  - Location extraction rate (% jobs with valid location)
  - Leadership job count (total jobs flagged as leadership)
  - Duplicate rate (how many jobs overlap between methods)
  - Unique jobs found by each method
- Weekly summary reports comparing regex vs LLM performance

**FR6: TUI Review Interface**
- New section in `src/tui.py`: "Review LLM Extraction Failures"
- Display failed extractions with:
  - Company name, failure reason, timestamp
  - Link to cached markdown file
  - Option to manually retry or mark as "skip permanently"
- Filter by date range, company, failure type

### Technical Requirements

**TR1: Database Schema Changes**
```sql
-- Add extraction method tracking to jobs table
ALTER TABLE jobs ADD COLUMN extraction_method TEXT; -- 'regex', 'llm', 'manual'
ALTER TABLE jobs ADD COLUMN extraction_cost REAL;   -- API cost in USD

-- New table for LLM extraction failures
CREATE TABLE llm_extraction_failures (
    id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    careers_url TEXT,
    markdown_path TEXT,
    failure_reason TEXT,
    error_details TEXT,
    occurred_at TEXT NOT NULL,
    reviewed_at TEXT,
    review_action TEXT,  -- 'retry', 'skip', 'pending'
    UNIQUE(company_name, occurred_at)
);

-- New table for extraction comparison metrics
CREATE TABLE extraction_metrics (
    id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    scrape_date TEXT NOT NULL,
    regex_jobs_found INTEGER,
    regex_leadership_jobs INTEGER,
    regex_with_location INTEGER,
    llm_jobs_found INTEGER,
    llm_leadership_jobs INTEGER,
    llm_with_location INTEGER,
    llm_api_cost REAL,
    overlap_count INTEGER,
    regex_unique INTEGER,
    llm_unique INTEGER
);
```

**TR2: Configuration File**
New file: `config/llm-extraction-settings.json`
```json
{
  "enabled": true,
  "provider": "scrapegraphai",
  "llm_config": {
    "llm": {
      "api_key": "${OPENROUTER_API_KEY}",
      "model": "anthropic/claude-3.5-sonnet",
      "base_url": "https://openrouter.ai/api/v1",
      "temperature": 0.1
    }
  },
  "budget": {
    "monthly_limit_usd": 5.0,
    "pause_when_exceeded": true
  },
  "extraction_prompt": "Extract all leadership-level job postings...",
  "leadership_levels": [
    "Executive: VP, Vice President, Chief",
    "Director: Director, Senior Director, Head of",
    "Senior IC: Staff, Principal, Distinguished",
    "Senior Manager: Senior Manager, Technical Program Manager, Lead"
  ]
}
```

**TR3: Dependencies**
Add to `requirements.txt`:
```
scrapegraphai>=1.0.0
openai>=1.0.0  # For OpenRouter compatibility
```

**TR4: Test Dataset**
- Use all 18+ files in `data/firecrawl_cache/` as test dataset
- Create gold standard annotations for 5 companies (manual labeling)
- Automated comparison script: `scripts/compare_extraction_methods.py`

### Non-Functional Requirements

**NFR1: Performance**
- LLM extraction timeout: 30 seconds per company
- Parallel extraction (regex + LLM) must not exceed 60 seconds total
- No impact to weekly scraper runtime (<10% overhead acceptable)

**NFR2: Reliability**
- LLM failures must not crash weekly scraper
- Graceful degradation to regex-only when budget exceeded
- All extraction attempts logged for debugging

**NFR3: Cost Control**
- Real-time budget tracking updated after each LLM call
- Email alert when 80% of monthly budget consumed
- Hard stop at 100% budget (no overages)

**NFR4: Observability**
- Structured logging for all LLM API calls (tokens, cost, latency)
- Weekly metrics reports saved to `logs/extraction-metrics-YYYY-MM-DD.json`
- Grafana-compatible metrics export (future integration)

## User Stories

### As a developer validating LLM extraction
- I want to run both regex and LLM extraction in parallel so that I can compare results side-by-side
- I want to see weekly comparison reports so that I can track improvement trends
- I want to review failed LLM extractions in a TUI so that I can investigate issues efficiently

### As a cost-conscious user
- I want real-time budget tracking so that I never exceed $5/month
- I want to be alerted at 80% budget consumption so that I can decide whether to continue
- I want clear cost attribution per company so that I can prioritize which companies are worth LLM extraction

### As a job discovery user (Wesley)
- I want higher location extraction accuracy so that I can filter jobs by Remote/Hybrid/Ontario reliably
- I want more precise leadership job filtering so that I see fewer irrelevant matches
- I want to discover more leadership jobs so that I have better opportunities

## Technical Specifications

### Implementation Files

**New Files:**
- `src/extractors/llm_extractor.py` - LLM extraction logic using ScrapeGraphAI
- `src/extractors/extraction_comparator.py` - Compare regex vs LLM results
- `src/api/llm_budget_service.py` - Budget tracking and enforcement
- `config/llm-extraction-settings.json` - LLM configuration
- `scripts/compare_extraction_methods.py` - Batch comparison script for cached files
- `tests/unit/test_llm_extractor.py` - Unit tests for LLM extraction

**Modified Files:**
- `src/jobs/scrape_companies_with_firecrawl.py` - Add dual extraction pipeline
- `src/tui.py` - Add LLM failure review section
- `src/database.py` - Add schema migrations for new tables
- `requirements.txt` - Add scrapegraphai dependency

### Code Example: Dual Extraction

```python
# In CompanyScraperWithFirecrawl.process_company_markdown()

from extractors.llm_extractor import LLMExtractor
from extractors.extraction_comparator import ExtractionComparator

def process_company_markdown(self, company_name: str, markdown_content: str):
    """Run both regex and LLM extraction in parallel"""

    # Existing regex extraction
    jobs_regex = self._extract_jobs_from_markdown(markdown_content, company_name)

    # New LLM extraction (with budget check)
    llm_extractor = LLMExtractor()
    if llm_extractor.budget_available():
        try:
            jobs_llm = llm_extractor.extract_jobs(
                markdown=markdown_content,
                company_name=company_name
            )

            # Compare results
            comparator = ExtractionComparator()
            metrics = comparator.compare(jobs_regex, jobs_llm, company_name)
            self.database.store_extraction_metrics(metrics)

        except Exception as e:
            # Log failure, continue with regex
            self.database.store_llm_failure(
                company_name=company_name,
                error=str(e),
                markdown_path=f"data/firecrawl_cache/{company_name}.md"
            )
            jobs_llm = []
    else:
        logger.warning(f"LLM budget exceeded, skipping {company_name}")
        jobs_llm = []

    # For now, continue using regex results for production
    # Store LLM results separately with extraction_method='llm'
    return jobs_regex
```

### Prompt Engineering

**LLM Extraction Prompt** (stored in `config/llm-extraction-settings.json`):
```
Extract all leadership-level job postings from this {company_name} career page markdown.

Leadership levels include:
- Executive: VP, Vice President, Chief (CTO, CPO, etc.)
- Director: Director, Senior Director, Head of, Associate Director
- Senior IC: Staff, Principal, Distinguished, Senior Staff
- Senior Manager: Senior Manager, Technical Program Manager, Lead

For each job, extract:
- title: Complete job title
- location: Work location (clean format: "City, State" or "Remote". Remove prefixes like "locations")
- link: Direct application URL

Return ONLY a JSON array with this exact structure:
[
  {"title": "...", "location": "...", "link": "..."},
  ...
]

Career page markdown:
{markdown_content}
```

## Dependencies

### External Dependencies
- **ScrapeGraphAI** (new) - LLM extraction library
- **OpenRouter API** - Claude 3.5 Sonnet access ($3/M input tokens, $15/M output tokens)
- **Existing**: Firecrawl MCP, SQLite, email processors

### Internal Dependencies
- Must integrate with existing `CompanyScraperWithFirecrawl` workflow
- Must use existing `JobDatabase` for storage
- Must respect existing job scoring/notification pipeline

### Data Dependencies
- Requires cached Firecrawl markdown files for testing
- Requires `.env` variable: `OPENROUTER_API_KEY`

## Timeline

### Phase 1: Foundation (Week 1-2)
- Database schema changes and migrations
- Implement `LLMExtractor` class with ScrapeGraphAI
- Implement budget tracking service
- Add configuration file

### Phase 2: Validation Testing (Week 3-4)
- Run comparison script on all 18+ cached files
- Manually annotate 5 companies for gold standard
- Generate baseline metrics report
- Identify and fix initial issues

### Phase 3: Parallel Production (Week 5-8)
- Deploy dual extraction to weekly scraper
- Monitor for 4 weeks of production scraping
- Collect comprehensive metrics
- Weekly review of LLM failures via TUI

### Phase 4: Decision & Rollout (Week 9-10)
- Analyze 4 weeks of metrics data
- Calculate ROI (accuracy improvement vs cost)
- Decide: full migration, hybrid, or abandon
- Document learnings and update PRD status

**Total Timeline**: 10 weeks (2.5 months)

## Risks and Mitigation

### Risk 1: Budget Overruns
- **Mitigation**: Hard $5/month limit with auto-pause
- **Mitigation**: Start with only 10 highest-priority companies
- **Mitigation**: Cache LLM results aggressively (never re-extract same markdown)

### Risk 2: LLM Extraction Quality Issues
- **Mitigation**: Run in parallel with regex fallback during validation
- **Mitigation**: Manual review via TUI for all failures
- **Mitigation**: Gold standard test dataset for objective measurement

### Risk 3: API Rate Limits or Downtime
- **Mitigation**: Graceful degradation to regex-only
- **Mitigation**: Retry logic with exponential backoff
- **Mitigation**: Multiple LLM provider support (OpenRouter supports GPT-4, Claude, etc.)

### Risk 4: Longer Scraping Times
- **Mitigation**: 30-second timeout per LLM extraction
- **Mitigation**: Async/parallel processing where possible
- **Mitigation**: Accept up to 10% runtime increase for experimental phase

### Risk 5: Inconclusive Results
- **Mitigation**: Clear success criteria defined upfront (≥90% location accuracy, etc.)
- **Mitigation**: 4-week validation period provides sufficient data
- **Mitigation**: If inconclusive, default to "no migration" (no harm done)

## Out of Scope

### Explicitly NOT Included
- ❌ Full migration to LLM-only extraction (this is experimental validation only)
- ❌ LLM-based job scoring (only extraction, scoring remains unchanged)
- ❌ Real-time/on-demand LLM extraction (weekly batch only)
- ❌ Fine-tuning custom LLM models (use off-the-shelf models only)
- ❌ Multi-language support (English-only career pages)
- ❌ LLM extraction for email parsers (company career pages only)

### Future Considerations (Post-Validation)
- Two-tier progressive extraction (Issue #78) - if LLM proves valuable
- Automated retraining of extraction prompts
- A/B testing different LLM models (Claude vs GPT-4)
- Integration with Firecrawl's native AI extraction (if available)

## Acceptance Criteria

### Must Have
- [ ] Database schema updated with `extraction_method`, `extraction_cost`, new tables
- [ ] `LLMExtractor` class implemented with ScrapeGraphAI integration
- [ ] Budget tracking service enforces $5/month hard limit
- [ ] Dual extraction runs in parallel for all company scrapes
- [ ] TUI section for reviewing LLM failures implemented
- [ ] Comparison script processes all 18+ cached files successfully
- [ ] Weekly metrics reports generated automatically
- [ ] Gold standard test dataset created (5 companies, manually annotated)

### Should Have
- [ ] Email alerts at 80% budget consumption
- [ ] Structured logging for all LLM API calls (cost, tokens, latency)
- [ ] Async LLM extraction to minimize runtime impact
- [ ] Configurable LLM model switching (Claude, GPT-4, etc.)

### Nice to Have
- [ ] Grafana dashboard for extraction metrics visualization
- [ ] Automated prompt optimization experiments
- [ ] Per-company cost analysis (which companies are "worth it")

## Success Metrics

### Primary Metrics (Tracked Weekly)
1. **Location Extraction Accuracy**
   - Regex baseline: ~40-60% (estimated from exploration tests)
   - LLM target: ≥90%

2. **Leadership Job Filtering Precision**
   - Regex baseline: TBD (measure in Phase 2)
   - LLM target: ≥95% precision

3. **Total Leadership Jobs Discovered**
   - Regex baseline: Count from current system
   - LLM target: ≥10% increase

4. **LLM API Costs**
   - Hard limit: $5/month
   - Target: <$4/month (20% buffer)

### Secondary Metrics
- LLM extraction failure rate (<5% target)
- Average extraction time (regex vs LLM)
- Unique jobs found by LLM but missed by regex
- User satisfaction (Wesley's feedback on job quality)

## Resolved Questions

1. **Prompt Engineering**: ✅ YES - Experiment with multiple prompt variations during validation phase
   - Test different prompt structures, leadership definitions, output formats
   - Track which prompts yield best accuracy for location/title extraction
   - Document winning prompt in configuration file

2. **Model Selection**: ✅ NO - Stick with Claude 3.5 Sonnet only
   - Avoids complexity of multi-model comparison
   - Claude already proven effective in exploration tests
   - Can revisit GPT-4 comparison in future if needed

3. **Caching Strategy**: ✅ Cache LLM extraction results FOREVER (until disk/performance issues arise)
   - Never re-extract the same markdown file
   - Store cached results with content hash for invalidation
   - Monitor disk usage, implement cleanup only if needed

4. **Rollout Criteria**: ✅ **Option E - Quality-First (Absolute Target)**
   - Migrate if LLM achieves **≥90% location accuracy AND ≥95% precision**
   - Disregard job discovery count - focus on quality over quantity
   - Philosophy: "2 high quality jobs > 10 medium quality jobs"

5. **Priority Companies**: ✅ Prioritize REMOTE-FRIENDLY companies when budget is tight
   - Filter companies by "Remote" or "Hybrid" in job listings
   - Wes's profile gives +15 points for Remote roles
   - Suggested: Boston Dynamics, Anthropic, Figure, Skydio (verify remote policies)

## Migration Decision Framework

**SELECTED CRITERIA: Option E - Quality-First (Absolute Target)**

Migrate to LLM-based extraction IF AND ONLY IF:
1. **Location Accuracy ≥90%** - Nearly perfect location extraction
2. **Leadership Precision ≥95%** - Minimal false positives in leadership filtering

**Rationale**: "2 high quality jobs > 10 medium quality jobs"
- Prioritize signal quality over quantity
- Reduce noise in Wes's job feed
- Only A/B grade jobs matter (80+ scores)
- Better to miss some jobs than surface irrelevant matches

**Measurement Method**:
- Gold standard test dataset (5 manually annotated companies)
- Precision = True Positives / (True Positives + False Positives)
- Location accuracy = Jobs with correct location / Total jobs extracted

**If criteria NOT met**: Stay with regex extraction, document learnings, revisit in 6 months

## Additional Context
- **Exploration Tests**:
  - `tests/exploration/test_llm_extraction.py`
  - `tests/exploration/test_claude_extraction.py`
  - `tests/exploration/test_scrapegraph_extraction.py`
- **Cached Test Data**: `data/firecrawl_cache/` (18+ markdown files)

## Technical References
- ScrapeGraphAI Documentation: https://scrapegraph-ai.readthedocs.io/
- OpenRouter Pricing: https://openrouter.ai/models/anthropic/claude-3.5-sonnet
- Claude 3.5 Sonnet: $3/M input tokens, $15/M output tokens
