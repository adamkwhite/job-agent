# RLS Job Board Integration

## Source

- **URL**: `https://worker-production-a172.up.railway.app/`
- **API**: `https://worker-production-a172.up.railway.app/api/jobs`
- **Origin**: Rands Leadership Slack community — a bot (Floyd) extracts job details when members share links
- **Data**: Publicly available job postings only (no Slack-private data)

## Why This Source

- Leadership-focused roles (Product, Engineering, Design management)
- Pre-structured JSON — no scraping/parsing needed
- Includes salary ranges, experience level, remote status, location
- ~30 active postings, refreshed frequently
- High signal-to-noise for our target profiles (senior/director/VP)

## API Response Structure

```json
{
  "id": "string",
  "role_title": "Lead, Technical Product Manager",
  "company": "EdReports",
  "company_description": "...",
  "company_logo_url": "...",
  "location": "United States",
  "remote_status": "Remote",          // Remote | Hybrid | Onsite
  "salary_range": "$102,824–$139,114",
  "experience_level": "Senior",       // Senior | Mid | Staff | Executive
  "is_management": true,
  "job_function": "Product",          // Engineering | Product | Design | Operations | Other
  "role_type": "Full-time",           // Full-time | Contract | Part-time
  "job_description": "...",
  "url": "https://...",               // Application link
  "extracted_at": "2026-03-10T...",
  "classification": "..."
}
```

## Integration Plan

### Approach: New scraper module

Create `src/scrapers/rls_scraper.py` — simple HTTP GET to `/api/jobs`, map fields to our job schema.

### Field Mapping

| RLS Field | Our Field | Notes |
|---|---|---|
| `role_title` | `title` | Direct |
| `company` | `company` | Direct |
| `location` | `location` | Direct |
| `url` | `link` | Direct |
| `remote_status` | location scoring | Maps to Remote/Hybrid/Onsite |
| `experience_level` | seniority scoring | Maps to our seniority hierarchy |
| `job_function` | role type scoring | Engineering/Product/Design |
| `salary_range` | display only | Not used in scoring currently |
| `extracted_at` | `received_at` | Posting timestamp |

### Source identifier

`source = "rls_job_board"`

### Integration points

1. Add to `weekly_unified_scraper.py` as a new source (like ministry scraper)
2. Add to TUI source selection
3. No email inbox needed — direct API fetch
4. Score for all profiles automatically (existing multi-profile architecture)

### Considerations

- API has no pagination — returns all active jobs (~30)
- No auth required
- 60s auto-refresh on frontend, but we only need daily fetch
- Deduplication via existing `UNIQUE(title, company, link)` constraint
- Small dataset — no LLM extraction needed, fields are pre-structured
