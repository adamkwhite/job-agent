# PRD: Automated Robotics Company Monitoring

## Overview

Automate the monitoring of top robotics companies by extracting company data from the robotics/deeptech Google Sheets and populating the companies table for automated Firecrawl scraping. This eliminates the manual Firecrawl workflow (Issue #65, PR #71) and enables continuous monitoring of company career pages.

## Problem Statement

**Current State:**
- Robotics spreadsheet contains 1,092 jobs from ~50-100 unique companies
- 10 priority companies require manual Firecrawl MCP command execution (semi-automated workflow)
- Manual workflow is time-consuming and error-prone
- Jobs discovered only when they appear in the spreadsheet (delayed discovery)
- Limited to spreadsheet update frequency (weekly/bi-weekly)

**Pain Points:**
1. Manual Firecrawl workflow requires human intervention for each scraping session
2. No automated monitoring of robotics company career pages
3. Job discovery is delayed until spreadsheet curator adds them
4. Cannot discover jobs that never make it to the spreadsheet
5. Inconsistent coverage due to manual process

**Desired State:**
- Top 20 robotics companies automatically monitored via Firecrawl
- Zero manual intervention for scraping workflow
- Jobs discovered as soon as they're posted to company career pages
- Comprehensive coverage of robotics/hardware job market
- Cost-efficient operation with performance monitoring

## Goals

### Primary Goals
1. **Eliminate Manual Workflow:** Replace semi-automated Firecrawl workflow with fully automated company monitoring
2. **Increase Job Discovery:** Discover jobs earlier than they appear in robotics spreadsheet
3. **Expand Coverage:** Monitor top 20 robotics companies by job volume continuously

### Secondary Goals
1. **Cost Efficiency:** Monitor and disable low-performing companies to stay within budget
2. **Quality Metrics:** Track jobs discovered per dollar spent on Firecrawl credits
3. **Maintain Reliability:** Achieve 95%+ uptime for company scraping with automatic failure handling

## Success Criteria

- [ ] All 20 target companies added to companies table with active=1
- [ ] Manual Firecrawl workflow (Issue #65) is fully replaced
- [ ] Zero manual MCP command executions required for robotics companies
- [ ] At least 10% increase in unique jobs discovered per week
- [ ] Jobs discovered 3-7 days earlier than spreadsheet appearance
- [ ] Firecrawl success rate ≥80% (jobs extracted per scrape attempt)
- [ ] Cost per unique job discovered ≤$0.50
- [ ] Automatic failure handling reduces company active status after 5 failures
- [ ] Email notifications sent for immediate scraping failures

## Requirements

### Functional Requirements

1. **Company Extraction from Spreadsheet**
   - FR-1: System shall fetch robotics/deeptech Google Sheets data
   - FR-2: System shall extract unique company names and their job URLs
   - FR-3: System shall count job volume per company to identify top 20
   - FR-4: System shall exclude companies already in companies table

2. **Career Page URL Derivation**
   - FR-5: System shall automatically parse career page URLs from job URLs using pattern matching
   - FR-6: System shall support automatic extraction for Workday, Greenhouse, Lever, and other major ATS platforms
   - FR-7: System shall flag companies requiring manual URL lookup for complex cases
   - FR-8: System shall validate career page URLs before insertion

3. **Database Population**
   - FR-9: System shall insert companies into companies table with all required fields
   - FR-10: System shall set active=1 for all inserted companies
   - FR-11: System shall set scraper_type='generic' for Firecrawl compatibility
   - FR-12: System shall add descriptive notes including job volume and insertion date

4. **Automated Scraping**
   - FR-13: System shall scrape all active companies via company_scraper.py
   - FR-14: System shall integrate with unified_weekly_scraper.py workflow
   - FR-15: System shall use Firecrawl MCP for scraping (existing infrastructure)
   - FR-16: System shall extract jobs from scraped markdown using existing processors

5. **Duplicate Handling**
   - FR-17: System shall continue scraping robotics spreadsheet in parallel
   - FR-18: System shall rely on job_hash deduplication for overlapping jobs
   - FR-19: System shall preserve source attribution for each job
   - FR-20: System shall track which source discovered each job first

6. **Performance Monitoring**
   - FR-21: System shall track Firecrawl credit usage per company
   - FR-22: System shall calculate cost per unique job discovered
   - FR-23: System shall identify low-performing companies (high cost, low job yield)
   - FR-24: System shall generate monthly cost/performance reports

7. **Failure Handling**
   - FR-25: System shall mark company as inactive=0 after 5 consecutive scraping failures
   - FR-26: System shall send email notification for immediate scraping failures
   - FR-27: System shall log failure details including error messages and timestamps
   - FR-28: System shall require manual re-enable for deactivated companies

### Technical Requirements

1. **Data Processing**
   - TR-1: Implementation shall use Python 3.13+ with existing virtual environment
   - TR-2: URL parsing shall use urllib.parse for safety and reliability
   - TR-3: CSV processing shall handle Google Sheets export format
   - TR-4: Batch database operations shall use transactions for atomicity

2. **Integration**
   - TR-5: Implementation shall integrate with existing JobDatabase class
   - TR-6: Implementation shall use existing Firecrawl MCP tool infrastructure
   - TR-7: Implementation shall work with unified_weekly_scraper.py
   - TR-8: Implementation shall maintain compatibility with multi-profile scoring

3. **URL Parsing Patterns**
   - TR-9: Workday URLs: Extract base URL before `/job/` path
   - TR-10: Greenhouse URLs: Extract domain + base path before `/jobs/`
   - TR-11: Lever URLs: Extract domain + company path before `/jobs/`
   - TR-12: Generic URLs: Extract domain + `/careers` or `/jobs` if pattern exists

4. **Error Handling**
   - TR-13: Scraping failures shall increment failure counter in database
   - TR-14: Email notifications shall use existing SMTP configuration
   - TR-15: Failure logs shall include company name, URL, error type, timestamp
   - TR-16: System shall continue processing remaining companies after individual failures

### Non-Functional Requirements

1. **Performance**
   - NFR-1: Company extraction and URL derivation shall complete within 60 seconds
   - NFR-2: Database insertion batch operation shall complete within 10 seconds
   - NFR-3: Weekly scraping shall complete within 2 hours for 20 companies
   - NFR-4: System shall handle up to 100 companies without performance degradation

2. **Reliability**
   - NFR-5: System shall achieve 95%+ uptime for automated scraping
   - NFR-6: Failure recovery shall not require manual intervention
   - NFR-7: Database operations shall be atomic (all-or-nothing)
   - NFR-8: URL parsing shall succeed for 80%+ of companies automatically

3. **Maintainability**
   - NFR-9: Code shall follow existing project patterns and style guidelines
   - NFR-10: URL parsing patterns shall be configurable via JSON or constants
   - NFR-11: Company selection criteria shall be parameterizable (top N)
   - NFR-12: Documentation shall include examples and troubleshooting guide

4. **Cost Efficiency**
   - NFR-13: System shall monitor Firecrawl credit usage in real-time
   - NFR-14: Cost per job shall not exceed $0.50 on average
   - NFR-15: Low-performing companies shall be automatically flagged for review
   - NFR-16: Budget alerts shall trigger at 80% of monthly limit

## User Stories

### As a Job Seeker (Wes/Adam)
1. "As a job seeker, I want robotics companies monitored automatically so that I discover new jobs as soon as they're posted, not when they appear in the spreadsheet."
2. "As a job seeker, I want to receive notifications for A/B grade jobs from top robotics companies without manual scraping effort."
3. "As a job seeker, I want comprehensive coverage of robotics job market so I don't miss opportunities."

### As a System Operator
1. "As an operator, I want companies automatically extracted from the spreadsheet so I don't manually maintain the companies table."
2. "As an operator, I want career page URLs automatically derived so I minimize manual lookup effort."
3. "As an operator, I want cost monitoring so I stay within budget constraints."
4. "As an operator, I want automatic failure handling so I don't need to babysit the scraping process."
5. "As an operator, I want email alerts for failures so I can intervene only when necessary."

### As a Developer
1. "As a developer, I want clear URL parsing patterns so I can add support for new ATS platforms."
2. "As a developer, I want well-documented code so I can understand and modify the company extraction logic."
3. "As a developer, I want parameterizable selection criteria so I can adjust company count easily."

## Technical Specifications

### URL Parsing Patterns

```python
# src/utils/career_url_parser.py

import re
from urllib.parse import urlparse

class CareerURLParser:
    """Parse career page URLs from job posting URLs"""

    PATTERNS = {
        # Workday: https://company.wd1.myworkdayjobs.com/CompanyName/job/12345
        # Extract: https://company.wd1.myworkdayjobs.com/CompanyName
        'workday': r'(https?://[^/]+\.myworkdayjobs\.com/[^/]+)',

        # Greenhouse: https://job-boards.greenhouse.io/company/jobs/12345
        # Extract: https://job-boards.greenhouse.io/company
        'greenhouse': r'(https?://(?:job-boards\.)?greenhouse\.io/[^/]+)',

        # Lever: https://jobs.lever.co/company/abc-123
        # Extract: https://jobs.lever.co/company
        'lever': r'(https?://jobs\.lever\.co/[^/]+)',

        # Generic: Try /careers or /jobs endpoint
        'generic': r'(https?://[^/]+(?:/careers|/jobs)?)'
    }

    def parse(self, job_url: str) -> str | None:
        """
        Extract career page URL from job posting URL.

        Args:
            job_url: Full job posting URL

        Returns:
            Career page URL if parseable, None otherwise
        """
        for pattern_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, job_url)
            if match:
                return match.group(1)
        return None
```

### Company Extraction Script

```python
# scripts/extract_robotics_companies.py

import csv
import io
import requests
from collections import Counter
from src.database import JobDatabase
from src.utils.career_url_parser import CareerURLParser

def extract_top_companies(limit: int = 20) -> list[dict]:
    """
    Extract top N companies by job volume from robotics spreadsheet.

    Args:
        limit: Number of top companies to extract

    Returns:
        List of company dicts with name, career_url, job_count
    """
    # Fetch spreadsheet
    sheet_id = "1i1OQti71WbiE9kFANDc5Pt-IknCM3UB2dD61gujPywk"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    response = requests.get(csv_url, timeout=30)
    response.raise_for_status()

    # Parse CSV and count jobs per company
    reader = csv.DictReader(io.StringIO(response.text))
    company_jobs = Counter()
    company_urls = {}  # Track job URLs per company

    for row in reader:
        company = row.get("Company", "").strip()
        job_url = row.get("Job_Url", "").strip()

        if company and job_url:
            company_jobs[company] += 1
            if company not in company_urls:
                company_urls[company] = job_url

    # Get top N companies
    top_companies = company_jobs.most_common(limit)

    # Derive career URLs
    parser = CareerURLParser()
    results = []

    for company, job_count in top_companies:
        sample_job_url = company_urls[company]
        career_url = parser.parse(sample_job_url)

        results.append({
            'name': company,
            'career_url': career_url,
            'job_url_sample': sample_job_url,
            'job_count': job_count,
            'url_parsed': career_url is not None
        })

    return results

def populate_companies_table(companies: list[dict], dry_run: bool = True):
    """
    Insert companies into database companies table.

    Args:
        companies: List of company dicts from extract_top_companies()
        dry_run: If True, print SQL without executing
    """
    db = JobDatabase()

    # Get existing companies to avoid duplicates
    existing = set()
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM companies")
    existing = {row[0] for row in cursor.fetchall()}

    # Filter and insert
    to_insert = [c for c in companies if c['name'] not in existing]

    print(f"Companies to insert: {len(to_insert)}/{len(companies)}")
    print(f"Skipped (already exist): {len(companies) - len(to_insert)}")

    for company in to_insert:
        if not company['url_parsed']:
            print(f"⚠️  Manual URL needed: {company['name']} ({company['job_url_sample']})")
            continue

        sql = """
            INSERT INTO companies (name, careers_url, scraper_type, active, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """

        notes = f"Robotics/deeptech company - {company['job_count']} jobs in spreadsheet - Added via automation {datetime.now().strftime('%Y-%m-%d')}"

        if dry_run:
            print(f"Would insert: {company['name']} → {company['career_url']}")
        else:
            cursor.execute(sql, (
                company['name'],
                company['career_url'],
                'generic',
                1,  # active
                notes
            ))

    if not dry_run:
        db.conn.commit()
        print(f"✓ Inserted {len(to_insert)} companies")

if __name__ == "__main__":
    companies = extract_top_companies(limit=20)
    populate_companies_table(companies, dry_run=False)
```

### Performance Monitoring

```python
# src/monitoring/company_performance.py

def calculate_company_metrics(company_id: int, days: int = 30) -> dict:
    """
    Calculate performance metrics for a company.

    Returns:
        {
            'jobs_discovered': int,
            'scrapes_attempted': int,
            'scrapes_successful': int,
            'success_rate': float,
            'credits_used': int,
            'cost_per_job': float,
            'last_job_date': str,
            'recommendation': 'keep' | 'review' | 'disable'
        }
    """
    pass  # Implementation details

def generate_cost_report(days: int = 30) -> dict:
    """Generate monthly cost/performance report for all companies"""
    pass  # Implementation details
```

### Email Notification

```python
# src/notifier.py (extend existing)

def send_scraping_failure_alert(company: str, error: str, url: str):
    """
    Send email notification for immediate scraping failure.

    Args:
        company: Company name
        error: Error message
        url: Career page URL that failed
    """
    subject = f"[Job Agent] Firecrawl failure: {company}"
    body = f"""
Firecrawl scraping failed for {company}.

Company: {company}
URL: {url}
Error: {error}
Time: {datetime.now().isoformat()}

The company remains active. After 5 consecutive failures, it will be automatically disabled.

Check logs: logs/unified_weekly_scraper.log
"""
    # Use existing email sending infrastructure
    pass
```

## Dependencies

### External Dependencies
- **Firecrawl MCP:** Required for career page scraping (existing)
- **Google Sheets API:** CSV export endpoint for robotics spreadsheet (existing)
- **SMTP Service:** Email notifications for failures (existing)

### Internal Dependencies
- **database.py:** JobDatabase class for companies table operations (existing)
- **company_scraper.py:** Firecrawl scraping infrastructure (existing)
- **unified_weekly_scraper.py:** Weekly automation workflow (existing)
- **job_filter.py:** Deduplication via job_hash (existing)
- **multi_scorer.py:** Multi-profile scoring system (existing)

## Timeline

### Phase 1: Implementation (Week 1-2)
- **Week 1:**
  - Implement CareerURLParser with ATS pattern matching
  - Create extract_robotics_companies.py script
  - Test URL parsing on robotics spreadsheet sample
  - Manual verification of top 20 companies and URLs

- **Week 2:**
  - Implement populate_companies_table() with dry-run mode
  - Add failure tracking and email notifications
  - Test integration with company_scraper.py
  - Document manual URL lookup process for complex cases

### Phase 2: Rollout (Week 3)
- **Full Rollout:**
  - Run extraction script with dry_run=True for review
  - Manually verify/correct any unparseable URLs
  - Execute populate_companies_table() with dry_run=False
  - Run unified_weekly_scraper.py --companies-only
  - Monitor first scraping cycle for errors

### Phase 3: Monitoring (Week 4+)
- **Ongoing:**
  - Monitor Firecrawl credit usage weekly
  - Review cost per job metrics monthly
  - Disable low-performing companies (cost >$0.50/job)
  - Update company list quarterly based on spreadsheet changes

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| URL parsing fails for many companies | High | Medium | Hybrid approach: auto + manual, thorough testing on sample data |
| Firecrawl costs exceed budget | High | Medium | Real-time monitoring, auto-disable low performers, monthly budget alerts |
| Scraping failures for complex career pages | Medium | High | Automatic retry, failure tracking, manual intervention after 5 failures |
| Duplicate jobs create noise | Medium | Low | Trust existing deduplication (job_hash), monitor for issues |
| Email alerts create alert fatigue | Low | Medium | Only send on immediate failures, batch daily summary |
| Companies change career page URLs | Medium | Low | Track last_checked, monitor success rates, update URLs manually |

## Out of Scope

### Explicitly Excluded
1. **Spreadsheet Scraping Removal:** Will NOT disable robotics spreadsheet scraping (keep both sources)
2. **Real-time Scraping:** Will NOT implement hourly/daily scraping (weekly automation sufficient)
3. **AI-Powered URL Discovery:** Will NOT use LLMs to find career page URLs (manual verification more reliable)
4. **Company Addition UI:** Will NOT create web interface for adding companies (script-based sufficient)
5. **Historical Data Backfill:** Will NOT scrape historical jobs from new companies (forward-looking only)
6. **Custom ATS Support:** Will NOT implement parsers for every ATS platform (focus on top 4-5)

### Future Enhancements (Post-V1)
- Automatic company discovery from spreadsheet updates (quarterly)
- Machine learning for URL pattern detection
- Interactive dashboard for cost/performance monitoring
- Integration with company funding/news data for prioritization

## Acceptance Criteria

### Implementation Complete
- [ ] CareerURLParser class created with 4+ ATS patterns
- [ ] extract_robotics_companies.py script functional
- [ ] populate_companies_table() tested with dry-run and live modes
- [ ] URL parsing achieves 80%+ automatic success rate
- [ ] Companies table populated with 20 companies, all active=1

### Integration Complete
- [ ] Companies appear in unified_weekly_scraper.py output
- [ ] Firecrawl scraping succeeds for 80%+ of companies
- [ ] Jobs extracted and stored in database
- [ ] Multi-profile scoring works for new jobs
- [ ] Deduplication prevents duplicate jobs

### Monitoring Complete
- [ ] Failure tracking increments counter after scraping errors
- [ ] Email notifications sent for immediate failures
- [ ] Companies auto-disabled after 5 failures
- [ ] Cost tracking implemented and reporting

### Success Metrics Achieved (4 weeks post-rollout)
- [ ] 10%+ increase in unique jobs per week
- [ ] Jobs discovered 3-7 days before spreadsheet
- [ ] Cost per job ≤$0.50
- [ ] Zero manual Firecrawl MCP commands required
- [ ] 95%+ scraping uptime

## Related Work

- **Issue #65:** Firecrawl generic career pages (semi-automated workflow) - Will be replaced by this feature
- **PR #71:** Firecrawl scraping prompt to TUI workflow - Workflow will be eliminated
- **Issue #85:** Write Firecrawl markdown immediately - Risk mitigation for data loss
- **Issue #44:** Skip generic career page URLs - URL validation patterns reused
- **Multi-Profile System:** Jobs will be scored for both Adam and Wes profiles

## References

- Companies table schema: `data/jobs.db` (id, name, careers_url, scraper_type, active, last_checked, notes)
- Robotics spreadsheet: Sheet ID `1i1OQti71WbiE9kFANDc5Pt-IknCM3UB2dD61gujPywk`
- Company scraper: `src/jobs/company_scraper.py`
- Unified scraper: `src/jobs/weekly_unified_scraper.py`
- Firecrawl MCP: `mcp__firecrawl-mcp__firecrawl_scrape`
