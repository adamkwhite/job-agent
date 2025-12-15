# LLM-Based Job Extraction - Implementation Tasks

> Generated from PRD: `prd.md`
> GitHub Issue: [#86](https://github.com/adamkwhite/job-agent/issues/86)

## Relevant Files

### New Files
- `src/extractors/llm_extractor.py` - Core LLM extraction logic using **LangChain + ChatOpenAI** (replaced ScrapeGraphAI)
- `src/api/llm_budget_service.py` - Track API costs via JSON files, enforce $5/month budget limit
- `config/llm-extraction-settings.json` - LLM configuration (model, prompts, budget, timeout)
- `config/llm-extraction-settings-test.json` - Test configuration with budget checking disabled
- `logs/llm-budget-YYYY-MM.json` - Monthly budget tracking files (auto-generated)
- `test_llm_extraction_direct.py` - Test script for validating LLM extraction (root directory)

### Modified Files
- `src/scrapers/firecrawl_career_scraper.py` - Add dual extraction pipeline (regex + LLM)
- `src/jobs/company_scraper.py` - Handle extraction method tagging and visual indicators
- `src/jobs/weekly_unified_scraper.py` - Add `--llm-extraction` CLI flag
- `src/database.py` - Add schema migrations and new table methods
- `src/tui.py` - Add "Advanced Options" step for enabling LLM extraction
- `requirements.txt` - Add `langchain-openai`, `langchain-core` dependencies

### Test Files
- `tests/unit/test_llm_extractor.py` - Unit tests for LLM extraction logic
- `tests/unit/test_extraction_comparator.py` - Tests for comparison metrics
- `tests/unit/test_llm_budget_service.py` - Tests for budget tracking
- `tests/integration/test_dual_extraction_pipeline.py` - End-to-end dual extraction test

### Notes
- All new code must have ≥80% test coverage (SonarCloud enforced)
- Use `PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_llm_extractor.py -v` to run specific tests
- Mock external LLM API calls in unit tests to avoid costs

### Implementation Changes
**CRITICAL**: During implementation, we replaced **ScrapeGraphAI** with **direct LangChain + ChatOpenAI** integration:
- **Reason**: ScrapeGraphAI v1.64.0-1.64.2 had incompatible langchain imports causing `ImportError: cannot import name 'init_chat_model'`
- **Solution**: Implemented direct `langchain_openai.ChatOpenAI` with OpenRouter API
- **Result**: Fully functional LLM extraction validated on production run (60 companies, $0.60 cost, 3 jobs from Figure AI)
- **Files Updated**: `src/extractors/llm_extractor.py` (complete rewrite), `requirements.txt` (langchain-openai, langchain-core)

## Tasks

- [x] 1.0 **Database Schema & Migrations** - Create new tables and columns for LLM extraction tracking ✅ **Issue #87, PR #111**
  - [x] 1.1 Add `extraction_method` (TEXT) and `extraction_cost` (REAL) columns to `jobs` table
  - [x] 1.2 Create `llm_extraction_failures` table with columns: id, company_name, careers_url, markdown_path, failure_reason, error_details, occurred_at, reviewed_at, review_action
  - [x] 1.3 Create `extraction_metrics` table with columns: id, company_name, scrape_date, regex_jobs_found, regex_leadership_jobs, regex_with_location, llm_jobs_found, llm_leadership_jobs, llm_with_location, llm_api_cost, overlap_count, regex_unique, llm_unique
  - [x] 1.4 Add database methods in `src/database.py`: `store_llm_failure()`, `get_llm_failures()`, `store_extraction_metrics()`, `get_extraction_metrics()`
  - [x] 1.5 Write migration script to update existing database schema without data loss
  - [x] 1.6 Test migrations on development database and verify schema integrity

- [x] 2.0 **LLM Extractor Core Implementation** - Build ScrapeGraphAI-based extraction engine with budget tracking ✅ **Issue #88, PR #112**
  - [x] 2.1 Install dependencies: `scrapegraphai>=1.0.0`, `openai>=1.0.0` (update requirements.txt) - **Note: Commented out to prevent CI timeouts**
  - [x] 2.2 Create `config/llm-extraction-settings.json` with model config, budget settings, extraction prompts
  - [x] 2.3 Implement `src/extractors/llm_extractor.py` with `LLMExtractor` class
  - [x] 2.4 Add method `extract_jobs(markdown: str, company_name: str) -> List[OpportunityData]`
  - [x] 2.5 Integrate ScrapeGraphAI SmartScraperGraph with OpenRouter Claude 3.5 Sonnet
  - [x] 2.6 Parse LLM JSON response and convert to OpportunityData objects
  - [x] 2.7 Add 30-second timeout per extraction (NFR1 requirement)
  - [x] 2.8 Log all LLM API calls with token counts, latency, cost estimates - **Placeholder for Issue #89**
  - [x] 2.9 Handle LLM failures gracefully (catch exceptions, log errors, return empty list)
  - [x] 2.10 Write unit tests with mocked ScrapeGraphAI calls (≥80% coverage) - **91% achieved**

- [x] 3.0 **Budget Tracking Service** - Enforce $5/month API cost limits ✅ **Issue #89, PR #113**
  - [x] 3.1 Implement `src/api/llm_budget_service.py` with `LLMBudgetService` class
  - [x] 3.2 Add method `check_budget_available() -> bool` (queries monthly spend from logs)
  - [x] 3.3 Add method `record_api_call(tokens_in, tokens_out, cost_usd)` (append to tracking file)
  - [x] 3.4 Add method `get_monthly_spend() -> float` (sum costs for current month)
  - [x] 3.5 Add method `get_remaining_budget() -> float` (5.0 - monthly_spend)
  - [x] 3.6 Store budget tracking data in `logs/llm-budget-YYYY-MM.json`
  - [x] 3.7 Implement hard pause at $5.00 monthly limit (set `enabled: false` in config)
  - [x] 3.8 Add email alert trigger at 80% budget ($4.00) using existing notifier - **Placeholder implementation**
  - [x] 3.9 Write unit tests for budget calculations and limits - **100% coverage achieved**

- [x] 4.0 **Dual Extraction Pipeline** - Integrate LLM extraction alongside existing regex in company scraper ✅ **Issue #90**
  - [x] 4.1 Modify `src/scrapers/firecrawl_career_scraper.py::scrape_jobs()` to run dual extraction
  - [x] 4.2 Run existing regex extraction first (return tuples with `extraction_method='regex'`)
  - [x] 4.3 Check LLM budget availability via `LLMExtractor.budget_available()`
  - [x] 4.4 If budget available, run LLM extraction (return tuples with `extraction_method='llm'`)
  - [x] 4.5 If LLM fails or budget exceeded, log error and continue with regex-only results
  - [x] 4.6 Database deduplication handles duplicate jobs from both methods
  - [x] 4.7 Add command-line flag `--llm-extraction` to `weekly_unified_scraper.py`
  - [x] 4.8 Add TUI "Advanced Options" step for user-friendly LLM extraction toggle
  - [x] 4.9 Test dual extraction on cached markdown (Figure AI: 3 LLM jobs, 0 regex jobs)
  - [ ] 4.10 Update weekly scraper cron script to optionally include `--llm-extraction` flag

- [ ] 5.0 **Comparison & Metrics Framework** - Build tools to measure and compare regex vs LLM performance
  - [ ] 5.1 Implement `src/extractors/extraction_comparator.py` with `ExtractionComparator` class
  - [ ] 5.2 Add method `compare(jobs_regex, jobs_llm, company_name) -> dict` returning metrics
  - [ ] 5.3 Calculate location extraction rate: `jobs_with_location / total_jobs`
  - [ ] 5.4 Calculate leadership job counts for both methods
  - [ ] 5.5 Calculate overlap (jobs found by both methods using title+company matching)
  - [ ] 5.6 Calculate unique jobs found by each method (regex-only, llm-only)
  - [ ] 5.7 Store metrics in `extraction_metrics` table via database service
  - [ ] 5.8 Create `scripts/compare_extraction_methods.py` for batch processing cached files
  - [ ] 5.9 Generate weekly summary reports in `logs/extraction-metrics-YYYY-MM-DD.json`
  - [ ] 5.10 Add visualization: Print comparison table to console (location %, precision, jobs found)
  - [ ] 5.11 Write unit tests for metric calculations

- [ ] 6.0 **TUI Failure Review Interface** - Add section to review and retry failed LLM extractions
  - [ ] 6.1 Add new menu option in `src/tui.py`: "Review LLM Extraction Failures"
  - [ ] 6.2 Query `llm_extraction_failures` table for pending failures (`review_action='pending'`)
  - [ ] 6.3 Display table with columns: Company, Failure Reason, Timestamp, Markdown Path
  - [ ] 6.4 Add filter options: by date range, by company name, by failure type
  - [ ] 6.5 For each failure, show action menu: [R]etry, [S]kip permanently, [V]iew markdown, [B]ack
  - [ ] 6.6 Implement retry action: re-run LLM extraction, update `reviewed_at` and `review_action='retry'`
  - [ ] 6.7 Implement skip action: mark as reviewed with `review_action='skip'`
  - [ ] 6.8 Implement view markdown: open file in less/cat for manual inspection
  - [ ] 6.9 Add summary stats at top: Total failures, Pending review, Retried, Skipped
  - [ ] 6.10 Test TUI with mock failures in database

- [ ] 7.0 **Testing & Validation** - Create gold standard dataset and validate against quality gates
  - [ ] 7.1 Select 5 companies for manual annotation (Boston Dynamics, Figure, Anthropic, Skydio, Dexterity)
  - [ ] 7.2 Create `scripts/create_gold_standard_dataset.py` for annotation tool
  - [ ] 7.3 Manually label all jobs in 5 companies: leadership (Y/N), location (correct value)
  - [ ] 7.4 Store annotations in `data/gold_standard/{company_name}_annotations.json`
  - [ ] 7.5 Run batch comparison on all 18+ cached Firecrawl files using `scripts/compare_extraction_methods.py`
  - [ ] 7.6 Calculate baseline metrics: regex location accuracy, regex precision (using gold standard)
  - [ ] 7.7 Calculate LLM metrics: location accuracy, precision (using gold standard)
  - [ ] 7.8 Generate validation report comparing against quality gates (≥90% location, ≥95% precision)
  - [ ] 7.9 Test prompt variations (3-5 different prompts) and track which performs best
  - [ ] 7.10 Document winning prompt in `config/llm-extraction-settings.json`
  - [ ] 7.11 Run 4-week production validation: monitor metrics weekly, track API costs
  - [ ] 7.12 Make migration decision based on quality-first criteria (Option E)

- [ ] 8.0 **Documentation & Deployment** - Update docs and deploy to production
  - [ ] 8.1 Update `CLAUDE.md` with LLM extraction overview and usage instructions
  - [ ] 8.2 Update `README.md` with new dependencies and configuration steps
  - [ ] 8.3 Add `.env.example` entry for `OPENROUTER_API_KEY`
  - [ ] 8.4 Document TUI failure review workflow in `docs/development/`
  - [ ] 8.5 Create runbook for monitoring LLM budget and handling overages
  - [ ] 8.6 Update weekly scraper cron job to enable `--llm-extraction` flag
  - [ ] 8.7 Set up budget alert email notifications (80% threshold)
  - [ ] 8.8 Deploy to production and monitor for first week
  - [ ] 8.9 Update PRD status from PLANNED → IN_PROGRESS → COMPLETED (when done)
