# PRD: LangSmith Observability for LLM Extraction Pipeline

**Status**: PLANNED
**Created**: 2025-12-15
**Owner**: Adam
**Priority**: P1 (High)

## Related Work
- **Issue #210**: Add LangSmith instrumentation to LLM extraction pipeline

## Problem Statement

The job agent now uses LLM extraction (Claude 3.5 Sonnet via OpenRouter) to find jobs that regex patterns miss. However, we have zero visibility into:

### Cost & Budget
- **Total spend per run**: We know month-to-date ($13.30) but not per-scrape-run
- **Cost per company**: Which companies are expensive to scrape?
- **Cost per job found**: What's our cost efficiency?
- **Budget alerts**: No proactive warnings before hitting limits

### Performance
- **Latency**: How long does LLM extraction take per company?
- **Token usage**: Are we sending too much context?
- **Cache effectiveness**: How often do we use cached markdown vs fresh scrapes?

### Quality & Debugging
- **JSON parse failures**: 9 companies failed in Mario's run - why?
- **Prompt effectiveness**: Is our extraction prompt optimal?
- **False positives**: Is LLM extracting non-leadership jobs?
- **Missing jobs**: Are we missing jobs that exist on the page?

### Example from Mario's Scrape (2025-12-15)
- **108 companies** scraped
- **~$0.70 LLM cost** (estimated)
- **12 jobs stored** (10 via LLM, 2 via regex)
- **9 JSON parse failures** (ABB, Adobe, Amazon, etc.)
- **No way to debug** why failures happened or optimize prompts

## Goals

### Primary Goals
1. **Cost Visibility**: Track LLM API costs per run, per company, per job found
2. **Performance Monitoring**: Measure latency distribution (P50/P95/P99)
3. **Quality Metrics**: Track extraction success rates and failure reasons
4. **Debugging Tools**: View exact prompts/responses for failed extractions

### Secondary Goals
1. **Budget Alerts**: Proactive notifications before hitting limits
2. **Prompt Optimization**: A/B test different extraction prompts
3. **ROI Analysis**: Cost per quality job (C+ grade) vs all jobs

## Non-Goals
- Replacing existing LLM budget service (complement, don't replace)
- Observability for non-LLM parts of pipeline (separate PRD)
- Real-time dashboards (batch analytics sufficient for now)

## Success Metrics

### Adoption
- [ ] LangSmith integrated into LLM extraction pipeline
- [ ] 100% of LLM API calls traced
- [ ] Team regularly uses LangSmith for debugging

### Impact
- [ ] Reduce LLM cost by 20% through prompt optimization
- [ ] Reduce JSON parse failures from 8% to <2%
- [ ] Identify top 10 most expensive companies to optimize

### Quality
- [ ] Zero trace data contains PII (profile names, connections data)
- [ ] Traces capture all relevant metadata (company, model, tokens, cost)

## User Stories

### As Adam (developer)
- **I want to** see which companies cause expensive LLM calls
  **So that** I can optimize prompts or switch to regex for those companies

- **I want to** debug JSON parse failures with exact LLM responses
  **So that** I can fix prompt issues or parsing logic

- **I want to** compare LLM vs regex extraction effectiveness
  **So that** I can decide when to use each method

### As Mario (job seeker)
- **I want to** know the cost of finding jobs for me
  **So that** I can understand the value I'm getting

- **I want to** see which companies yield the most relevant jobs
  **So that** I can prioritize applications

## Design

### Architecture Overview

```
┌─────────────────────────────────────────────┐
│ CompanyScraper                              │
│  ├─ Firecrawl (not traced)                  │
│  └─ LLM Extractor ✓                         │
│      └─ @traceable decorator                │
└─────────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ LangSmith Cloud                             │
│  ├─ Traces (prompts, responses, errors)     │
│  ├─ Metrics (tokens, cost, latency)         │
│  └─ Dashboards (aggregated analytics)       │
└─────────────────────────────────────────────┘
```

### Instrumentation Points

**1. LLM Extraction (`src/extractors/llm_extractor.py`)**
```python
from langsmith import traceable

@traceable(
    name="extract_jobs_llm",
    tags=["llm-extraction"],
    metadata={"model": "claude-3.5-sonnet"}
)
def extract_jobs(self, markdown: str, company_name: str):
    # Existing extraction logic
    # LangSmith automatically captures:
    # - Input: markdown (truncated), company_name
    # - Output: extracted jobs
    # - Tokens, cost, latency
    # - Errors with stack traces
    pass
```

**2. Company Scraper (`src/jobs/company_scraper.py`)**
```python
from langsmith import Client

def scrape_company(self, company: dict):
    if self.langsmith_client:
        with self.langsmith_client.trace(
            name="scrape_company",
            inputs={"company": company["name"], "url": company["url"]},
            tags=["company-scraper"],
            metadata={
                "extraction_method": "llm+regex" if llm_enabled else "regex",
                "profile": "REDACTED"  # Don't log PII
            }
        ):
            return self._scrape_impl(company)
```

### PII Handling Strategy

**Safe to Trace (Not PII)**:
- Company names
- Job titles
- Job links
- Locations
- Scores/grades
- Model names, token counts, costs

**Exclude from Traces (PII)**:
- Profile names (Wes, Eli, Mario, Adam)
- LinkedIn connections data
- Email addresses
- Profile-specific keywords/preferences

**Implementation**:
- Use metadata filters to exclude PII fields
- Sanitize company names (keep) vs profile names (redact)
- Never log full markdown (truncate to first 500 chars)

### Data Captured

**Per LLM API Call**:
- Company name
- Model used
- Prompt tokens
- Completion tokens
- Total cost (USD)
- Latency (ms)
- Jobs extracted (count + titles)
- Errors (type + message)

**Aggregated Metrics**:
- Total cost per scraper run
- Avg cost per company
- Avg cost per job found
- Token efficiency (tokens/job)
- Success rate (% successful extractions)
- P50/P95/P99 latency

## Implementation Plan

### Phase 1: Core Instrumentation (1-2 hours)
- [x] Add `langsmith` to requirements.txt
- [ ] Add `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` to .env
- [ ] Instrument `extract_jobs()` with `@traceable` decorator
- [ ] Test with 5 companies, verify traces appear in LangSmith
- [ ] Verify PII exclusion (no profile names in traces)

### Phase 2: Company Scraper Context (1 hour)
- [ ] Add trace context to `scrape_company()`
- [ ] Include extraction method metadata (llm vs regex)
- [ ] Test full scraper run, verify nested traces

### Phase 3: Dashboards & Alerts (2 hours)
- [ ] Create LangSmith dashboard with:
  - Daily LLM cost breakdown
  - Extraction success rate
  - Top 10 expensive companies
  - P50/P95/P99 latency
- [ ] Set up Slack/email alerts for:
  - Daily spend > $2
  - JSON parse failure rate > 10%
  - Individual company cost > $0.50

### Phase 4: Optimization (ongoing)
- [ ] Identify prompt improvements from trace data
- [ ] A/B test different prompts
- [ ] Optimize token usage (reduce markdown context)
- [ ] Switch expensive companies to regex if LLM not adding value

## Open Questions

1. **Data Retention**: How long should we keep LangSmith traces? (Default: 14 days)
2. **Budget**: LangSmith free tier: 5k traces/month. Estimate: ~500 traces/week. Sufficient?
3. **Alerting**: Slack, email, or both? Who gets alerts?
4. **Prompt Versioning**: Track prompt changes over time?

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| PII leakage in traces | High | Strict PII exclusion policy, code review |
| LangSmith API costs | Low | Free tier sufficient, monitor usage |
| Trace volume exceeds limits | Medium | Implement sampling (trace 50% of companies) |
| Dev dependencies break | Low | Pin langsmith version, test in CI |

## Alternatives Considered

### 1. OpenTelemetry + Custom Backend
**Pros**: Vendor-neutral, export to multiple backends
**Cons**: More setup complexity, less LLM-specific features
**Decision**: Use LangSmith (purpose-built for LLM observability)

### 2. Manual Logging to Database
**Pros**: Full control, no external dependencies
**Cons**: Reinventing the wheel, no visualization
**Decision**: Use LangSmith (better UX, less maintenance)

### 3. Just Use Existing Budget Service
**Pros**: Already built
**Cons**: No prompt/response visibility, no latency tracking
**Decision**: LangSmith complements budget service

## References

- [LangSmith Documentation](https://docs.langchain.com/langsmith/observability)
- [LangSmith Python SDK](https://github.com/langchain-ai/langsmith-sdk)
- OpenRouter Claude 3.5 Sonnet Pricing: $3/1M input, $15/1M output
- Current LLM Budget Service: `src/api/llm_budget_service.py`
- LLM Extraction Config: `config/llm-extraction-settings.json`

## Appendix: Example Traces

### Successful Extraction
```json
{
  "trace_id": "abc123",
  "name": "extract_jobs_llm",
  "inputs": {
    "company_name": "Atlassian",
    "markdown_preview": "# Careers at Atlassian\n\nWe're hiring...(truncated)"
  },
  "outputs": {
    "jobs_found": 1,
    "jobs": [
      {"title": "Head of Product Management", "link": "https://..."}
    ]
  },
  "metadata": {
    "model": "anthropic/claude-3.5-sonnet",
    "tokens_in": 2847,
    "tokens_out": 156,
    "cost_usd": 0.1229,
    "latency_ms": 7800
  },
  "status": "success"
}
```

### Failed Extraction (JSON Parse)
```json
{
  "trace_id": "def456",
  "name": "extract_jobs_llm",
  "inputs": {
    "company_name": "ABB",
    "markdown_preview": "# ABB Careers\n..."
  },
  "outputs": null,
  "error": {
    "type": "JSONDecodeError",
    "message": "Extra data: line 3 column 1 (char 4)",
    "response_preview": "```json\n[]\n```\nNo leadership positions..."
  },
  "metadata": {
    "model": "anthropic/claude-3.5-sonnet",
    "tokens_in": 2456,
    "tokens_out": 42,
    "cost_usd": 0.0798,
    "latency_ms": 4800
  },
  "status": "error"
}
```
