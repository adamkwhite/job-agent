# PRD: Generic Company List Scraper

## Status

**Status**: PARTIALLY IMPLEMENTED (CLI only)
**Priority**: Medium
**Created**: 2025-10-23
**Target Release**: V2.5

## Related Work

- **Issue #9**: Generic company list scraper enhancements

## Problem Statement

When researching job opportunities, users need to track companies from various sources:
- Event exhibitor lists (HardTech Summit, robotics conferences)
- Curated "Top N Companies" lists (CEO Review Magazine, BestStartup.ca)
- Industry rankings and directories

Currently, there's no easy way to extract and track companies from these diverse sources. Manual copying is tedious and error-prone.

## Current Implementation (V1 - Oct 23, 2025)

### What's Built

✅ **CLI Scraper** (`src/scrapers/company_list_scraper.py`)
- AI extraction mode with dual provider support:
  - Anthropic API (ANTHROPIC_API_KEY)
  - OpenRouter API (OPENROUTER_API_KEY) - cheaper alternative
- Pattern matching fallback (no API key needed)
- JSON output support
- Extracts: company name, website, location, funding stage, description

### Test Results

**CEO Review Magazine** (Top 10 Robotics):
- Pattern matching: 7/10 companies (70%)
- Extracted: name, location, stage, description
- Missing: websites (pattern matching limitation)

### Usage

```bash
# Pattern matching (no API key)
job-agent-venv/bin/python src/scrapers/company_list_scraper.py \
  "URL" --no-ai --output companies.json

# AI extraction with OpenRouter (cheaper)
job-agent-venv/bin/python src/scrapers/company_list_scraper.py \
  "URL" --provider openrouter --output companies.json
```

## Planned Enhancements

### Phase 1: Core Improvements

1. **Better Pattern Matching** - Improve website extraction
2. **Batch Processing** - Process multiple URLs from file
3. **Database Integration** - Auto-store as funding_leads

### Phase 2: Enrichment

4. **Careers Page Discovery** - Auto-find /careers URLs
5. **Company Scoring** - Score against candidate profile

## Success Metrics

**V1 (Current)**: 70% extraction rate on structured lists
**V2 (Target)**: 90%+ extraction, batch processing, database integration

## References

- [Usage Guide](../../development/company-list-scraper-usage.md)
- [Code](../../../src/scrapers/company_list_scraper.py)
