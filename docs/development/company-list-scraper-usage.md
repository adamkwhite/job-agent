# Company List Scraper Usage Guide

## Overview

The Company List Scraper extracts company data from curated lists, event pages, and rankings. It can work with or without AI assistance.

## Quick Start

### Basic Usage (Pattern Matching - No API Key Required)

```bash
job-agent-venv/bin/python src/scrapers/company_list_scraper.py \
  "https://ceoreviewmagazine.com/top-10-canada/robotics-companies-in-canada/" \
  --no-ai \
  --output companies.json
```

### Advanced Usage (AI-Powered - Requires API Key)

**Option 1: Anthropic API**

1. Add `ANTHROPIC_API_KEY` to your `.env` file
2. Run without `--no-ai` flag:

```bash
job-agent-venv/bin/python src/scrapers/company_list_scraper.py \
  "https://ceoreviewmagazine.com/top-10-canada/robotics-companies-in-canada/" \
  --output companies.json
```

**Option 2: OpenRouter API (Cheaper Alternative)**

1. Add `OPENROUTER_API_KEY` to your `.env` file
2. Run with `--provider openrouter`:

```bash
job-agent-venv/bin/python src/scrapers/company_list_scraper.py \
  "https://ceoreviewmagazine.com/top-10-canada/robotics-companies-in-canada/" \
  --provider openrouter \
  --output companies.json
```

## Data Extracted

The scraper attempts to extract:
- **Company Name** (required)
- **Website** (optional)
- **Location** (optional - city, country)
- **Funding Stage** (optional - Seed, Series A, etc.)
- **Description** (optional - brief company overview)

## Output Format

### JSON Output

```json
[
  {
    "company": "Novarc Technologies",
    "website": "",
    "location": "North Vancouver, Canada",
    "funding_stage": "Series A",
    "description": "Collaborative welding robot system...",
    "source": "company_list:ceoreviewmagazine.com"
  }
]
```

### OpportunityData Format

The scraper returns `OpportunityData` objects with:
- `type`: "funding_lead" (for company research)
- `company`: Company name
- `company_location`: Location
- `company_website`: Website URL
- `funding_stage`: Funding stage
- `description`: Company description
- `source`: "company_list:{domain}"

## Supported Formats

The scraper works best with:

1. **Numbered Lists**
   - "1. Company Name"
   - "2. Company Name"
   - etc.

2. **Structured Content**
   - Location: Toronto, Canada
   - Stage: Series A
   - Founded: 2020

3. **Event Exhibitor Pages**
   - Company cards with contact info
   - Exhibitor lists with websites

## AI vs Pattern Matching

### AI Extraction (Recommended)
- **Pros**: More accurate, handles any format, finds websites
- **Cons**: Requires API key, costs per request
- **Providers**: Anthropic (direct) or OpenRouter (cheaper, uses credits)
- **Best for**: Diverse formats, one-time scraping

### Pattern Matching (Fallback)
- **Pros**: Free, no API key needed
- **Cons**: Less accurate, misses some data
- **Best for**: Consistent formats (like CEO Review Magazine), high-volume scraping

## Example Commands

### Scrape Multiple URLs

```bash
# Create a list of URLs
cat > urls.txt <<EOF
https://ceoreviewmagazine.com/top-10-canada/robotics-companies-in-canada/
https://beststartup.ca/101-top-robotics-startups-and-companies-in-canada/
https://www.eventcombo.com/ms/ev/74865/hardtech-summit/exhibitors
EOF

# Scrape each URL
while read url; do
  job-agent-venv/bin/python src/scrapers/company_list_scraper.py "$url" --no-ai --output "companies-$(date +%s).json"
done < urls.txt
```

### Combine with Database Storage

The scraper outputs `OpportunityData` objects that can be:
1. Stored in the jobs database
2. Enriched with career page data
3. Scored against candidate profile
4. Filtered for relevant opportunities

## Limitations

### Pattern Matching Mode
- May miss 20-30% of companies
- Struggles with non-standard formats
- Website extraction unreliable

### AI Mode
- Requires API key (Anthropic or OpenRouter with credits)
- Limited to 50k characters of text
- May hallucinate data (verify important info)
- OpenRouter recommended for cost savings ($10 credits vs per-request billing)

## Future Enhancements

See [PRD: Generic Company List Scraper](../features/company-list-scraper-PLANNED/prd.md) for planned improvements:
- Careers page auto-discovery
- LinkedIn company page scraping
- Batch processing mode
- Database integration
- Web UI for monitoring

## Troubleshooting

### No Companies Found
- Check if URL is accessible
- Try without `--no-ai` (if you have API key)
- Inspect HTML structure manually
- File an issue with the URL

### Missing Websites
- Pattern matching struggles with website links
- Use AI extraction for better results
- Manually add websites after extraction

### Invalid JSON Output
- Check for malformed HTML
- Try cleaning HTML first
- Report the URL as an issue
