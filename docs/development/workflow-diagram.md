# Job Agent Workflow Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph "Data Sources"
        EMAIL[Email Sources<br/>LinkedIn, Supra, F6S,<br/>Built In, Job Bank,<br/>Recruiters]
        SCRAPER[Web Scrapers<br/>Robotics/DeepTech<br/>Google Sheets]
    end

    subgraph "Processing Layer"
        IMAP[IMAP Email Fetcher<br/>src/imap_client.py]
        PARSERS[Email Parsers<br/>src/parsers/*_parser.py]
        WEBSCRAPER[Robotics Scraper<br/>src/jobs/weekly_robotics_scraper.py]
        SCORER[Job Scoring Engine<br/>src/agents/job_scorer.py<br/>115-point system]
    end

    subgraph "Storage"
        DB[(SQLite Database<br/>data/jobs.db)]
        DEDUP[Deduplication<br/>SHA256 hash]
    end

    subgraph "Notification System"
        FILTER[Score Filter<br/>A/B grades only<br/>80+ points]
        SMS[SMS Alerts<br/>Twilio API]
        EMAILALERT[Email Alerts<br/>SMTP]
    end

    subgraph "Reporting"
        HTML[HTML Generator<br/>src/generate_jobs_html.py]
        DIGEST[Email Digest<br/>src/send_digest_to_wes_v2.py]
    end

    EMAIL --> IMAP
    IMAP --> PARSERS
    PARSERS --> SCORER
    SCRAPER --> WEBSCRAPER
    WEBSCRAPER --> SCORER
    SCORER --> DEDUP
    DEDUP --> DB
    DB --> FILTER
    FILTER --> SMS
    FILTER --> EMAILALERT
    DB --> HTML
    HTML --> DIGEST
    DIGEST --> |Weekly Email| WES[Wesley van Ooyen<br/>wesvanooyen@gmail.com]
```

## Detailed Process Flow

### 1. Email Processing Pipeline

```mermaid
sequenceDiagram
    participant Gmail
    participant IMAP
    participant Parser
    participant Scorer
    participant DB
    participant Notifier

    Gmail->>IMAP: Fetch unread emails
    IMAP->>Parser: Parse email content

    alt Email is parseable
        Parser->>Parser: Extract jobs (title, company, location, link)
        Parser->>Scorer: Score each job
        Scorer->>Scorer: Calculate 115-point score
        Scorer->>DB: Store job with score

        alt Score >= 80 (A/B grade)
            DB->>Notifier: Trigger notification
            Notifier-->>Wesley: SMS + Email alert
        end
    else Email not parseable
        Parser->>IMAP: Mark as processed, skip
    end
```

### 2. Job Scoring System (115 points)

```mermaid
graph LR
    subgraph "Scoring Categories"
        SENIORITY[Seniority<br/>0-30 points<br/>VP/Director/Head]
        DOMAIN[Domain<br/>0-25 points<br/>Robotics/Hardware]
        ROLE[Role Type<br/>0-20 points<br/>Engineering > Product]
        LOCATION[Location<br/>0-15 points<br/>Remote/Hybrid Ontario]
        STAGE[Company Stage<br/>0-15 points<br/>Series A-C]
        KEYWORDS[Keywords<br/>0-10 points<br/>Mechatronics/IoT]
    end

    SENIORITY --> TOTAL[Total Score<br/>0-115]
    DOMAIN --> TOTAL
    ROLE --> TOTAL
    LOCATION --> TOTAL
    STAGE --> TOTAL
    KEYWORDS --> TOTAL

    TOTAL --> GRADE{Grade Assignment}
    GRADE -->|98-115| A[Grade A]
    GRADE -->|80-97| B[Grade B]
    GRADE -->|63-79| C[Grade C]
    GRADE -->|46-62| D[Grade D]
    GRADE -->|0-45| F[Grade F]
```

### 3. Weekly Automation (Cron)

```mermaid
graph TD
    CRON[Cron Job<br/>Monday 9am EST]
    CRON --> MASTER[processor_master.py]

    MASTER --> EMAIL_PROC[Email Processing<br/>processor_v2.py]
    MASTER --> WEB_SCRAPE[Web Scraping<br/>weekly_robotics_scraper.py]
    MASTER --> HTML_GEN[HTML Generation<br/>generate_jobs_html.py]
    MASTER --> DIGEST_SEND[Send Digest<br/>send_digest_to_wes_v2.py]

    EMAIL_PROC --> DB[(Database)]
    WEB_SCRAPE --> DB
    DB --> HTML_GEN
    HTML_GEN --> DIGEST_SEND
    DIGEST_SEND --> EMAIL_OUT[Weekly Email to Wesley]
```

### 4. Parser Registry Pattern

```mermaid
classDiagram
    class BaseEmailParser {
        <<abstract>>
        +can_handle(message)
        +parse(html_content)
    }

    class LinkedInParser {
        +can_handle(message)
        +parse(html_content)
    }

    class SupraParser {
        +can_handle(message)
        +parse(html_content)
    }

    class BuiltInParser {
        +can_handle(message)
        +parse(html_content)
    }

    class JobBankParser {
        +can_handle(message)
        +parse(html_content)
    }

    class RecruiterParser {
        +can_handle(message)
        +parse(html_content)
    }

    class ParserRegistry {
        +parsers: List[BaseEmailParser]
        +get_parser(message)
        +parse_email(message)
    }

    BaseEmailParser <|-- LinkedInParser
    BaseEmailParser <|-- SupraParser
    BaseEmailParser <|-- BuiltInParser
    BaseEmailParser <|-- JobBankParser
    BaseEmailParser <|-- RecruiterParser
    ParserRegistry --> BaseEmailParser
```

### 5. Database Schema

```mermaid
erDiagram
    JOBS {
        int id PK
        text source
        text type
        text company
        text title
        text location
        text link
        text keywords_matched
        datetime received_at
        int fit_score
        text fit_grade
        json score_breakdown
        text research_notes
        boolean sent_to_wes
        datetime sent_to_wes_at
    }

    JOBS ||--o{ DEDUPLICATION : "unique(title,company,link)"
    JOBS ||--o{ SCORING : "fit_score 0-115"
    JOBS ||--o{ NOTIFICATIONS : "if score >= 80"
```

## Key Components

### Input Sources
1. **Email Parsers** (6 active):
   - LinkedIn Job Alerts
   - Supra Product Leadership Newsletter
   - F6S Startup Jobs
   - Built In Tech Jobs
   - Canadian Job Bank (Mechanical Engineering)
   - Direct Recruiter Emails

2. **Web Scrapers**:
   - Robotics/DeepTech Google Sheets (1,092 jobs/week)
   - Filters for Director+ roles
   - B+ grade threshold (70+ score)

### Processing Pipeline
1. **IMAP Email Fetching** - Monitors dedicated Gmail account
2. **Parser Selection** - Registry pattern matches parser to email type
3. **Job Extraction** - HTML parsing with BeautifulSoup
4. **Scoring Engine** - 115-point profile matching system
5. **Deduplication** - SHA256 hash of (title, company, link)
6. **Storage** - SQLite with tracking of sent status

### Output Channels
1. **Real-time Notifications** (A/B grades only):
   - SMS via Twilio
   - Email alerts via SMTP

2. **Weekly Digest**:
   - HTML report with interactive filtering
   - Sent Monday mornings
   - Only includes unsent jobs
   - Grouped by score grade

### Automation
- **Cron Job**: Runs weekly_robotics_scraper.py every Monday 9am
- **Master Pipeline**: processor_master.py orchestrates all components
- **Duplicate Prevention**: Tracks sent_to_wes status in database

## Performance Metrics

- **Volume**: ~50 jobs/week processed
- **Quality**: 10-15% score 70+ (B grade or better)
- **Top Source**: Robotics scraper (10 B+ jobs vs 0 from newsletters)
- **Noise Reduction**: 80+ score threshold for notifications
- **Delivery**: 100% weekly digest delivery rate
