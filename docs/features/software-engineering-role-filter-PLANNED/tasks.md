# Software Engineering Role Filtering - Implementation Tasks

## Relevant Files

- `src/utils/company_classifier.py` - New file: Multi-signal company classification system
- `tests/unit/test_company_classifier.py` - Unit tests for company classifier (20+ tests)
- `src/agents/job_scorer.py` - Modify: Integrate filtering logic with scoring system
- `tests/unit/test_job_scorer.py` - Update: Add filtering integration tests
- `config/company_classifications.json` - New file: Curated lists of hardware/software companies
- `profiles/wes.json` - Update: Add filtering configuration (aggression level, avoid keywords)
- `profiles/adam.json` - Update: Add filtering configuration
- `profiles/eli.json` - Update: Add filtering configuration
- `src/database/models.py` - Modify: Add CompanyClassification model
- `src/database/migrations/` - New migration: Add company_classifications table
- `tests/unit/test_filtering_integration.py` - New file: End-to-end filtering tests with real data
- `CLAUDE.md` - Update: Document filtering system and usage
- `README.md` - Update: Document filtering configuration options

### Notes

- Unit tests should be placed in `tests/unit/` directory
- Use `PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/` to run all unit tests
- Use `PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_company_classifier.py -v` to run specific test file
- Database migration should be tested in isolation before integration

## Tasks

- [ ] 1.0 Database Schema & Configuration Setup
  - [ ] 1.1 Create database migration for `company_classifications` table with columns: id, company_name, classification (enum), confidence_score, source (auto/manual), signals (JSON), created_at, updated_at
  - [ ] 1.2 Add indexes on company_name and classification columns for query performance
  - [ ] 1.3 Add `classification_metadata` JSON column to `job_scores` table via migration
  - [ ] 1.4 Create `config/company_classifications.json` with curated lists of hardware_companies, software_companies, and both_domains (start with top 50 from Issue #95)
  - [ ] 1.5 Test database migrations run successfully on clean database
  - [ ] 1.6 Create CompanyClassification SQLAlchemy model in `src/database/models.py`

- [ ] 2.0 Company Classifier Implementation
  - [ ] 2.1 Create `src/utils/company_classifier.py` with CompanyClassifier class skeleton
  - [ ] 2.2 Implement `CompanyClassification` dataclass with fields: type (software/hardware/both/unknown), confidence (0.0-1.0), signals (dict)
  - [ ] 2.3 Implement `_check_company_name_keywords()` method for keyword matching in company name (weight: 0.3)
  - [ ] 2.4 Implement `_check_curated_lists()` method to check against hardware/software lists from config (weight: 0.4)
  - [ ] 2.5 Implement `_check_domain_keywords()` method to analyze job domain keywords (weight: 0.2)
  - [ ] 2.6 Implement `_analyze_job_content()` method to scan job title/description (weight: 0.1)
  - [ ] 2.7 Implement `_combine_signals()` method with weighted scoring to determine final classification
  - [ ] 2.8 Implement `get_manual_override()` method to check database for user overrides
  - [ ] 2.9 Implement `classify_company()` main method that orchestrates all signals
  - [ ] 2.10 Add caching mechanism to avoid re-classifying same company multiple times
  - [ ] 2.11 Write unit tests for company name keyword matching (5 tests: hardware, software, both, unknown, edge cases)
  - [ ] 2.12 Write unit tests for curated list checking (4 tests: in hardware list, in software list, in both list, not in any list)
  - [ ] 2.13 Write unit tests for domain keyword matching (3 tests: robotics keywords, software keywords, mixed)
  - [ ] 2.14 Write unit tests for job content analysis (3 tests: hardware-focused, software-focused, ambiguous)
  - [ ] 2.15 Write unit tests for signal combination logic (5 tests: various confidence levels, conflicting signals, high confidence, low confidence)
  - [ ] 2.16 Write integration tests for full classification workflow (3 tests: Boston Dynamics, Stripe, Tesla)

- [ ] 3.0 Filtering Logic & Scorer Integration
  - [ ] 3.1 Add role type detection helper function in `src/utils/scoring_utils.py` (reuse existing role_types from profiles)
  - [ ] 3.2 Create `should_filter_job()` function in `src/utils/company_classifier.py` with signature: (job, profile, classification, aggression_level) -> (bool, str)
  - [ ] 3.3 Implement conservative aggression level logic (only filter explicit "VP of Software Engineering" titles)
  - [ ] 3.4 Implement moderate aggression level logic (filter engineering roles at software companies with confidence ≥0.6)
  - [ ] 3.5 Implement aggressive aggression level logic (filter any engineering role without explicit hardware keywords)
  - [ ] 3.6 Implement special handling for "both" domain companies (analyze job description for hardware vs software focus)
  - [ ] 3.7 Integrate `CompanyClassifier` into `src/agents/job_scorer.py` score_job() method
  - [ ] 3.8 Apply -20 point penalty for filtered software engineering roles in scorer
  - [ ] 3.9 Apply +10 point boost for hardware company engineering matches in scorer
  - [ ] 3.10 Store classification metadata (type, confidence, signals) in job_scores.classification_metadata JSON field
  - [ ] 3.11 Add comprehensive logging at INFO level for filtering decisions (log: company, classification, role_type, filter_decision, reason)
  - [ ] 3.12 Add DEBUG level logging for classification signals breakdown
  - [ ] 3.13 Write unit tests for should_filter_job() with all aggression levels (9 tests: 3 levels × 3 scenarios)
  - [ ] 3.14 Write unit tests for scorer integration (5 tests: penalty applied, boost applied, metadata stored, product leadership unaffected, logging output)

- [ ] 4.0 Profile Configuration & Aggression Levels
  - [ ] 4.1 Update profile JSON schema to include filtering configuration: filtering.aggression_level, filtering.software_engineering_avoid, filtering.hardware_company_boost, filtering.software_company_penalty
  - [ ] 4.2 Add filtering config to `profiles/wes.json` with aggression_level="moderate" and software_engineering_avoid keywords from PRD
  - [ ] 4.3 Add filtering config to `profiles/adam.json` with appropriate software product focus settings
  - [ ] 4.4 Add filtering config to `profiles/eli.json` with default moderate settings
  - [ ] 4.5 Implement profile validation in `src/utils/profile_manager.py` to check for required filtering fields
  - [ ] 4.6 Set sensible defaults for profiles missing filtering config (aggression_level="moderate", empty avoid list)
  - [ ] 4.7 Write unit tests for profile validation with filtering fields (3 tests: valid config, missing fields with defaults, invalid aggression level)

- [ ] 5.0 Testing & Validation
  - [ ] 5.1 Create `tests/unit/test_filtering_integration.py` for end-to-end filtering tests
  - [ ] 5.2 Write integration test: "Program Director at Jobs via Dice" should be filtered for Wes (reproduce real example)
  - [ ] 5.3 Write integration test: "VP of Engineering at Boston Dynamics" should NOT be filtered for Wes
  - [ ] 5.4 Write integration test: "VP of Product at Stripe" should NOT be filtered for Wes
  - [ ] 5.5 Write integration test: "VP of Engineering at Stripe" should be filtered for Wes
  - [ ] 5.6 Test conservative aggression level allows more jobs through
  - [ ] 5.7 Test moderate aggression level (default) balances safety and accuracy
  - [ ] 5.8 Test aggressive aggression level filters most software roles
  - [ ] 5.9 Test manual company override takes precedence over automated classification
  - [ ] 5.10 Test dual-domain company (Tesla) handling with job description analysis
  - [ ] 5.11 Performance test: Verify classification completes in <100ms per job (use pytest-benchmark if available)
  - [ ] 5.12 Run full test suite and verify 80%+ coverage on new modules (company_classifier.py, filtering integration)
  - [ ] 5.13 Test against 20 recent jobs from database to validate real-world behavior
  - [ ] 5.14 Verify all 859 existing unit tests still pass

- [ ] 6.0 Documentation & Deployment
  - [ ] 6.1 Update `CLAUDE.md` with section explaining software engineering role filtering system
  - [ ] 6.2 Update `README.md` Quick Start section with filtering configuration example
  - [ ] 6.3 Document company classification algorithm in `src/utils/company_classifier.py` module docstring
  - [ ] 6.4 Add inline docstrings to all public methods in CompanyClassifier class
  - [ ] 6.5 Document aggression levels in code comments (conservative/moderate/aggressive behavior)
  - [ ] 6.6 Update Issue #122 with implementation summary and link to PRD
  - [ ] 6.7 Create feature branch: `git checkout -b feature/software-role-filter-issue-122`
  - [ ] 6.8 Commit database migrations with descriptive message
  - [ ] 6.9 Commit company classifier implementation with tests
  - [ ] 6.10 Commit scorer integration with filtering logic
  - [ ] 6.11 Commit profile configuration updates
  - [ ] 6.12 Commit documentation updates
  - [ ] 6.13 Run pre-commit hooks and fix any linting/formatting issues
  - [ ] 6.14 Create PR with comprehensive description linking to PRD, Issue #122, and showing before/after examples
  - [ ] 6.15 Monitor CI/CD pipeline and fix any failures
  - [ ] 6.16 Request review and address feedback
  - [ ] 6.17 Merge PR after approval
  - [ ] 6.18 Run fresh scrape for Wes and validate digest quality improvement (80%+ software role reduction)
  - [ ] 6.19 Monitor first few digests and adjust aggression level if needed
