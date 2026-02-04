# Job-Agent Monetization Strategy

**Author:** Adam White + Claude (Business Coach Analysis)
**Date:** 2026-02-02
**Status:** Strategy Document

---

## Executive Summary

This document outlines two viable monetization paths for the job-agent platform based on comprehensive market research and analysis of current product performance.

**Key Findings:**
- **Current state:** 4 active profiles, 965 jobs in database, multi-profile architecture working
- **Product-market fit evidence:** Wes gets 8.6% hit rate (71 A/B jobs from 828 total) proving concept works
- **Core problem identified:** Job source-to-profile mismatch (Mario gets 0% hit rate due to lack of QA-specific sources)
- **Competitive advantage:** Email-based job aggregation avoids TOS/rate-limiting issues of direct web scraping

**Two Recommended Paths:**
1. **Path 1: Executive Job Concierge (B2C)** - Fastest to revenue, $199/month per user
2. **Path 2: Talent Intelligence Platform (B2B SaaS)** - Highest revenue ceiling, $499-1,999/month per firm

---

## Table of Contents

1. [Current Product Analysis](#current-product-analysis)
2. [Path 1: Executive Job Concierge (B2C)](#path-1-executive-job-concierge-b2c)
3. [Path 2: Talent Intelligence Platform (B2B SaaS)](#path-2-talent-intelligence-platform-b2b-saas)
4. [Side-by-Side Comparison](#side-by-side-comparison)
5. [Validation Checklists](#validation-checklists)
6. [Engineering Roadmaps](#engineering-roadmaps)
7. [Financial Projections](#financial-projections)
8. [Recommendation](#recommendation)

---

## Current Product Analysis

### Product Performance Data (as of 2026-02-02)

**Database Statistics:**
- **965 total jobs** in production database (4.2MB)
- **3,609 job scores** across 4 profiles
- **Multi-profile scoring** working as designed

**Profile Performance:**

| Profile | Total Jobs | A/B Jobs | A/B/C Jobs | Hit Rate | Status |
|---------|------------|----------|------------|----------|--------|
| **Wes** | 828 | 71 (8.6%) | 169 (20.4%) | ✅ Good | Best match: VP Robotics @ Agility (92 pts) |
| **Eli** | 931 | 46 (4.9%) | 102 (11.0%) | ⚠️ OK | Best match: VP Tech @ Aspire (82 pts) |
| **Adam** | 919 | 2 (0.2%) | 207 (22.5%) | ❌ Poor | Best match: Staff PM AI/ML @ Absorb (76 pts) |
| **Mario** | 931 | 0 (0%) | 1 (0.1%) | ❌ Broken | Best match: Dir AI Eng Ops @ ServicePoint (67 pts) |

**Key Insight:** The scoring system works (proven by Wes's 8.6% hit rate). The problem is **source-to-profile mismatch**:
- Wes gets good results because robotics exec jobs ARE in LinkedIn/Supra/F6S newsletters
- Mario gets zero results because QA/testing jobs are NOT in these newsletters
- Solution: Either add niche-specific sources OR let users bring their own sources

### Technical Foundation (24.5K Lines of Production Code)

**Core Components:**
- ✅ Multi-source email parsing (17 parsers: LinkedIn, Supra, F6S, Artemis, Built In, etc.)
- ✅ Intelligent 100-point scoring system with company classification
- ✅ Multi-profile architecture (4 active profiles, unlimited scalability)
- ✅ Web scraping infrastructure (Firecrawl, BeautifulSoup, Playwright)
- ✅ Email digest system with HTML reports
- ✅ LinkedIn connections matching
- ✅ SQLite database with 22-column schema
- ✅ Weekly automation via cron
- ✅ Database backup system (tiered retention)
- ✅ CI/CD with SonarCloud (80% coverage requirement)
- ✅ Pre-commit hooks (Ruff, mypy, Bandit)

**Maturity Level:** Beta/Production-ready for personal use, needs SaaS hardening for commercial deployment

---

## Path 1: Executive Job Concierge (B2C)

### Overview

**Target Customer:** Senior executives (VP+, Director, CTO) earning $200K+ who value time over money

**Product Positioning:** "Your personal job search concierge - we find the perfect roles so you can focus on networking"

**Pricing:** $199-499/month per user (3-month minimum: $597-1,497 upfront)

**Business Model:** Premium B2C subscription service

---

### Why This Path Works

**Evidence of Product-Market Fit:**
1. ✅ **4 active users** already using weekly (Wes, Adam, Eli, Mario)
2. ✅ **Proven results** - Wes gets 71 A/B jobs per processing cycle
3. ✅ **Automated retention** - Weekly digests create habitual usage
4. ✅ **Word-of-mouth demand** - Built for Wes, then Adam/Eli/Mario asked for it
5. ✅ **Measurable value** - Saves 5-10 hours/week of manual job searching

**Market Opportunity:**
- **Market size:** 6.5M executives in US earning $150K+
- **TAM (Total Addressable Market):** Job seekers spend $10K-50K on search (recruiter fees, resume services, coaching)
- **Willingness-to-pay:** Executives spend $40-120/month on LinkedIn Premium - your service is 2-5X better
- **Competitive alternatives:** Executive search firms ($30K-50K per placement), TheLadders ($25-50/month), LinkedIn Premium ($40-120/month)

**Your Competitive Advantages:**
1. **Multi-source aggregation** - 6+ email sources + web scraping (LinkedIn Premium is LinkedIn-only)
2. **Intelligent scoring** - 100-point system beats keyword search
3. **Domain-specific filtering** - Robotics, fintech, QA, etc. (generic job boards can't do this)
4. **LinkedIn connection matching** - See which companies you have connections at
5. **Email-based ingestion** - Legal safe harbor, no TOS violations

---

### Target Customer Segments

**Segment 1: Robotics/Hardware Executives (like Wes)**
- Target roles: VP/Director Engineering, Head of Hardware, CTO
- Domain: Robotics, automation, IoT, MedTech, mechatronics
- Willingness-to-pay: **High** ($199-299/month)
- Market size: ~50K robotics/hardware execs in US
- **This works TODAY** - Wes proves it

**Segment 2: Fintech/SaaS Executives (like Eli)**
- Target roles: Director/VP Engineering, CTO
- Domain: Fintech, healthtech, proptech, SaaS
- Willingness-to-pay: **Medium-High** ($149-199/month)
- Market size: ~200K fintech/SaaS execs in US
- **Needs better sources** - Currently 4.9% hit rate

**Segment 3: QA/Testing Leaders (like Mario)**
- Target roles: Director QA, VP Quality, Head of Testing, SDET Lead
- Domain: Quality engineering, test automation, reliability
- Willingness-to-pay: **Medium** ($99-149/month)
- Market size: ~30K QA leaders in US
- **Needs QA-specific sources** - Currently 0% hit rate

**Segment 4: Product Leaders (like Adam)**
- Target roles: Senior/Staff PM, Director Product, VP Product
- Domain: Software, AI/ML, B2B SaaS
- Willingness-to-pay: **Medium** ($99-149/month)
- Market size: ~150K product leaders in US
- **Scoring may need tuning** - Currently 0.2% hit rate but 22.5% C-grade

---

### Revenue Model

**Pricing Tiers:**

| Tier | Price/Month | Annual (Save 20%) | Target Segment |
|------|-------------|-------------------|----------------|
| **Essentials** | $99/month | $950/year | QA leaders, individual contributors |
| **Professional** | $199/month | $1,910/year | Directors, VPs in tech |
| **Executive** | $299/month | $2,870/year | C-level, robotics/hardware execs |

**What's Included:**
- Weekly personalized job digest (A/B/C grade jobs)
- Custom scoring profile (30-min onboarding call)
- LinkedIn connection matching
- Email alerts for A-grade jobs (85+ points)
- Company monitoring for 10 target companies
- HTML report with filtering (remote/hybrid/location)

**Add-Ons (Future):**
- **Resume customization:** $99/month - AI-powered resume tailoring per job
- **Interview prep:** $149/month - Company research, talking points, interview questions
- **Application automation:** $199/month - Semi-automated application submission

---

### Go-to-Market Strategy

**Phase 1: Beta Launch (Month 1) - Get 5 Customers @ $99/month**

**Week 1-2: Build Minimal Billing**
- [ ] Stripe account + payment links
- [ ] Google Form for profile intake
- [ ] Manual JSON profile creation (15 min/customer)
- [ ] Personalized onboarding email template

**Week 3-4: Beta Customer Acquisition**
- [ ] Offer to Wes/Adam/Eli/Mario: "$99/month beta price - want in?"
- [ ] Post in exec communities: Lenny's Newsletter, OnDeck, South Park Commons
- [ ] LinkedIn outreach to 20 VPs/Directors in robotics/hardware
- [ ] Target: 5 customers × $99/month = **$495/month MRR**

**Phase 2: Product Iteration (Month 2) - Reach $1,990/month MRR**

**Week 5-6: Self-Service Onboarding**
- [ ] Typeform or custom HTML form
- [ ] Auto-generate profile JSON from form
- [ ] Auto-send welcome email + first digest
- [ ] Stripe subscription (auto-charge monthly)

**Week 7-8: Feedback Loop + Price Increase**
- [ ] Survey beta customers: "What would make this 10X better?"
- [ ] Add top 2 features (likely: more companies, faster alerts)
- [ ] Raise price to $199/month for new customers
- [ ] Target: 10 customers (5 @ $99 + 5 @ $199) = **$1,990/month MRR**

**Phase 3: Public Launch (Month 3) - Reach $3,980/month MRR**

**Week 9-10: Marketing Assets**
- [ ] Landing page (Carrd/Webflow)
- [ ] Testimonials from beta customers
- [ ] Blog post: "How I automated my executive job search"
- [ ] 2-min demo video

**Week 11-12: Public Launch**
- [ ] ProductHunt (Tuesday-Thursday launch)
- [ ] HackerNews ShowHN
- [ ] LinkedIn posts in exec communities
- [ ] Email outreach to 100 VPs/Directors
- [ ] Target: 20 customers × $199/month = **$3,980/month MRR ($47,760 ARR)**

---

### Engineering Requirements (Minimal)

**Phase 1: MVP (2-4 weeks)**
- [x] Multi-profile support (already working!)
- [x] Email scraping + parsing (already working!)
- [x] 100-point scoring system (already working!)
- [x] Weekly digest automation (already working!)
- [ ] Stripe integration (new: 2 days)
- [ ] Self-service onboarding form (new: 3 days)
- [ ] Simple login/dashboard (new: 5 days)

**Total new engineering:** ~2 weeks for billing + self-service onboarding

**Phase 2: Customer Dashboard (Month 2-3)**
- [ ] Flask/FastAPI web app (1 week)
- [ ] Job history view (last 50 jobs) (2 days)
- [ ] Profile settings editor (3 days)
- [ ] Subscription management (2 days)

**Total engineering:** 2-3 weeks for web dashboard

**Phase 3: Premium Features (Month 4-6)**
- [ ] Resume customization (LLM-powered) (2 weeks)
- [ ] Interview prep automation (1 week)
- [ ] Application tracking (1 week)

---

### Financial Projections (Path 1)

**Conservative Case:**

| Month | Customers | Avg Price | MRR | ARR | Notes |
|-------|-----------|-----------|-----|-----|-------|
| 1 | 5 | $99 | $495 | $5,940 | Beta launch |
| 2 | 10 | $149 | $1,490 | $17,880 | Price increase |
| 3 | 20 | $199 | $3,980 | $47,760 | Public launch |
| 6 | 40 | $199 | $7,960 | $95,520 | Organic growth |
| 12 | 80 | $199 | $15,920 | $191,040 | Paid ads + referrals |

**Moderate Case:**

| Month | Customers | Avg Price | MRR | ARR |
|-------|-----------|-----------|-----|-----|
| 6 | 60 | $219 | $13,140 | $157,680 |
| 12 | 150 | $229 | $34,350 | $412,200 |
| 24 | 300 | $239 | $71,700 | $860,400 |

**Assumptions:**
- Average price increases over time as you add features
- 10% monthly churn (high for B2C but job search is seasonal)
- 20% organic growth + 30% paid acquisition
- CAC: $200/customer (mostly organic + paid ads)
- LTV: $2,400 (12 months avg retention × $200/month)

---

### Risks & Mitigation (Path 1)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Seasonal churn** (people find jobs, cancel) | High | Medium | Annual pricing (12 months for 10), focus on passive job seekers |
| **Source quality degrades** | Medium | High | Continuously add new sources, let users suggest newsletters |
| **Pricing too high** | Medium | Medium | Start at $99, validate willingness-to-pay with surveys |
| **Feature creep** | High | Low | Stay focused on core value: personalized job matching |
| **Competition from LinkedIn** | Low | High | Differentiate on multi-source + domain-specific scoring |

---

## Path 2: Talent Intelligence Platform (B2B SaaS)

### Overview

**Target Customer:** Mid-market recruiting firms (10-50 recruiters), executive search firms, RPO providers

**Product Positioning:** "The job aggregation engine for recruiting firms - find 10X more placements with intelligent job discovery"

**Pricing:** $499-1,999/month per firm (5-20 recruiter seats)

**Business Model:** B2B SaaS with per-seat pricing

---

### Why This Path Could Work

**Market Opportunity:**
- **$50B global recruiting industry** (2025)
- **$5B recruiting software market** (growing 15% annually)
- **30K recruiting firms in US** (1,000+ with 10+ recruiters)
- **Average recruiter software budget:** $40K-80K/year per seat
- **Recruiter productivity:** $625-1,041/hour equivalent (placement fees / hours worked)

**Pain Points You'd Solve:**
1. **Job fragmentation** - Jobs scattered across LinkedIn, Indeed, company sites, niche boards
2. **Manual aggregation** - Recruiters spend 5-10 hours/week checking multiple sources
3. **Stale postings** - Jobs stay live for months after filled, wasting recruiter time
4. **Poor filtering** - Keyword search returns 1,000 jobs (95% irrelevant)
5. **No candidate-to-job matching** - Recruiter has 50 candidates, no tool suggests matching jobs

**Competitive Landscape:**
- **LinkedIn Recruiter:** $10,800/year - candidate sourcing, not job aggregation
- **Gem:** $24,540/year - CRM + candidate sourcing, no job aggregation
- **SeekOut:** $15K-25K/year - advanced candidate search, not job-focused
- **Gap in market:** No one aggregates jobs + scores them for recruiter specialties

---

### Target Customer Segments

**Segment 1: Mid-Market Recruiting Firms (10-50 recruiters)**
- Annual revenue: $5M-25M
- Software budget: $50K-200K/year
- Decision cycle: 30-90 days
- **Sweet spot:** Large enough to pay $2K-10K/month, small enough to decide quickly

**Segment 2: Boutique Executive Search (5-15 recruiters)**
- Annual revenue: $2M-10M
- Software budget: $25K-100K/year
- Decision cycle: 30-60 days
- **Value prop:** Find more exec-level jobs faster

**Segment 3: RPO Firms (Recruitment Process Outsourcing)**
- Annual revenue: $10M-100M+
- Software budget: $200K-1M/year
- Decision cycle: 90-180 days
- **Value prop:** Scale job discovery across multiple client accounts

**Segment 4: In-House Recruiters (Agency Recruiters at Tech Companies)**
- Annual revenue: N/A (cost center)
- Software budget: $10K-50K/year per recruiter
- Decision cycle: 60-120 days
- **Value prop:** Stay on top of competitive job market

---

### Revenue Model

**Pricing Tiers:**

| Plan | Price/Month | Seats | Features | Target Customer |
|------|-------------|-------|----------|-----------------|
| **Solo** | $99/month | 1 | 3 specialty streams, 100 jobs/day, email digest | Individual recruiters |
| **Team** | $499/month | 5 | Unlimited streams, 500 jobs/day, shared workspaces | Small firms (5-10 recruiters) |
| **Agency** | $1,999/month | 20 | White-label, ATS integration, 2,000 jobs/day | Mid-market firms (20-50 recruiters) |
| **Enterprise** | Custom | Unlimited | Dedicated support, custom features, API access | Large firms (100+ recruiters) |

**Revenue Scenarios:**

| Year | Solo | Team | Agency | Enterprise | Total MRR | ARR |
|------|------|------|--------|------------|-----------|-----|
| **Year 1** | 20 @ $99 | 5 @ $499 | 2 @ $1,999 | 0 | $8,473 | $101,676 |
| **Year 2** | 50 @ $99 | 20 @ $499 | 10 @ $1,999 | 0 | $34,920 | $419,040 |
| **Year 3** | 100 @ $99 | 50 @ $499 | 25 @ $1,999 | 5 @ $5,000 | $109,825 | $1,317,900 |

---

### Product Features (What You'd Build)

**Core Features (MVP - Months 1-3):**
1. **Multi-Source Job Aggregation**
   - Email-based ingestion (user forwards job newsletters to system)
   - Web scraping: LinkedIn, Indeed, Built In, company career pages
   - Deduplicate across sources (same job, different titles)
   - Real-time updates (daily scraping)

2. **Intelligent Job Scoring**
   - Score jobs by match to recruiter's specialty
   - Example: "You focus on robotics execs → this job scores 92/100"
   - Learn from past placements to improve scoring

3. **Specialty-Based Streams**
   - Recruiter sets up "streams": "Robotics Execs", "Fintech Directors", "QA Leaders"
   - System auto-matches new jobs to streams
   - Daily digest: "10 new robotics exec jobs this week"

4. **Email Digest System**
   - Weekly/daily digest of top jobs per stream
   - Configurable thresholds (A/B grade only, 70+ points, etc.)
   - Click-through to full job details

5. **Simple Web Dashboard**
   - Browse jobs by stream
   - Filter by location, grade, date posted
   - Export to CSV for ATS import

**Intelligence Layer (Months 4-6):**
1. **ML-Based Scoring**
   - Recruiter provides feedback: "good match" or "bad match"
   - System learns and improves scoring over time
   - Personalized scoring per recruiter's placement history

2. **Stale Job Detection**
   - Auto-check if job URL is still active (weekly validation)
   - Flag jobs >30 days old as "likely filled"
   - Save recruiter time on dead leads

3. **Candidate-to-Job Matching (Reverse Search)**
   - Recruiter uploads candidate profiles
   - System suggests: "Here are 10 jobs perfect for Candidate X"
   - Reduces manual matching time

4. **Analytics Dashboard**
   - Job discovery metrics: new jobs/week, hit rate by stream
   - Placement tracking: which jobs led to placements
   - ROI reporting: hours saved, fees generated

**ATS Integration (Months 7-12):**
1. **Bullhorn Integration**
   - One-click export jobs to Bullhorn
   - Sync job status (open/filled/stale)
   - Auto-create job records in ATS

2. **Greenhouse/Lever Integration**
   - Same workflow as Bullhorn
   - Cover 80% of ATS market

3. **REST API**
   - For custom integrations
   - Third-party tools can consume job data
   - Webhooks for real-time job notifications

4. **White-Label Option**
   - Rebrand as recruiting firm's own tool
   - Custom domain, logo, email templates
   - Premium feature for Agency/Enterprise tiers

---

### Go-to-Market Strategy (B2B)

**Phase 1: Customer Discovery (Month 1-2) - Validate Before Building**

**Goal:** Interview 10-20 recruiting firms to validate pain point + willingness-to-pay

**Outreach Email Template:**
```
Subject: Quick question about recruiting workflow

Hi [Name],

I'm exploring a tool idea for recruiting firms and would love your input as someone who knows the space.

Would you have 20 minutes this week for a quick call? I want to understand how you find jobs to work on and whether there's a better way.

No pitch - just questions. Happy to buy you coffee/lunch if you're local.

Thanks!
Adam
```

**Interview Questions (8 must-asks):**
1. "What % of your week goes to finding jobs vs. finding candidates?"
2. "Walk me through how you find new jobs to work on. What tools do you use?"
3. "On a scale of 1-10, how painful is job discovery vs. candidate sourcing?"
4. "If a tool aggregated all jobs from multiple sources with intelligent matching, how much would you pay per month?"
5. "What features would make this 10X better than manual search?"
6. "Who makes software purchasing decisions at your firm? What's the approval process?"
7. "What tools do you currently use for job discovery? Why aren't they good enough?"
8. "Do you know 3-5 other recruiting firms who would be interested?"

**Success Criteria:**
- ✅ >70% say job discovery is a top-3 pain point
- ✅ >50% would pay $100+/month
- ✅ 3+ referrals to other recruiting firms
- ✅ Average time on job discovery: >30% of week

**If validation fails:** Pivot to Path 1 (B2C) or don't build at all

---

**Phase 2: Manual MVP (Month 2-3) - Prove Concept Without Code**

**Goal:** Get 3-5 pilot customers paying $99-249/month for manually curated job feeds

**Offer:**
> "I'm launching a beta version. For the next 3 months, I'll manually curate jobs for your specialties (robotics, fintech, QA, etc.) and send daily digests. $99/month. If you don't find at least 10 good jobs/week, I'll refund you."

**Manual Process:**
1. Recruiter tells you their specialties (e.g., "robotics execs, fintech directors")
2. You set up email forwarding for relevant newsletters
3. You manually tag jobs in Notion database
4. You send daily email digest with top 10 jobs
5. You collect feedback: "Which jobs were most useful?"

**Success Criteria:**
- ✅ 3+ pilot customers pay $99-249/month
- ✅ NPS score >50 (would recommend to others)
- ✅ >80% of customers renew after 3 months
- ✅ Feedback guides product roadmap

**If manual MVP fails:** Don't build automated version, pivot to Path 1

---

**Phase 3: Build Automated MVP (Month 4-6) - Only If Manual MVP Succeeds**

**Goal:** Convert manual process into automated product, reach $5K MRR

**Engineering Tasks:**
- [ ] Multi-tenant PostgreSQL database (schema-per-tenant)
- [ ] User authentication (Auth0 or Clerk)
- [ ] Web dashboard (React + Tailwind)
- [ ] Email ingestion system (users forward newsletters to dedicated email addresses)
- [ ] Job deduplication engine (fuzzy matching across sources)
- [ ] Scoring system (adapt current 100-point system for recruiter specialties)
- [ ] Email digest automation (already have this!)
- [ ] Stripe billing (already scoped for Path 1)

**Timeline:** 8-12 weeks full-time development

**Success Criteria:**
- ✅ Convert 3 manual pilot customers to automated product
- ✅ Add 5 new customers (8 total @ $500 avg = $4K MRR)
- ✅ <5% churn (sticky product)

---

**Phase 4: Scale (Month 7-12) - ATS Integrations + Sales**

**Goal:** Reach $20K MRR through ATS integrations and direct sales

**Engineering:**
- [ ] Bullhorn integration (80 hours)
- [ ] Greenhouse/Lever integration (60 hours)
- [ ] REST API (40 hours)
- [ ] White-label configuration (30 hours)

**Sales/Marketing:**
- [ ] Hire SDR or freelance sales (commission-only to start)
- [ ] Partner with ATS providers (co-marketing)
- [ ] Content marketing (blog, YouTube, LinkedIn)
- [ ] Paid ads (LinkedIn Ads targeting recruiters)

**Success Criteria:**
- ✅ 10-20 paying customers @ $1K avg = $10K-20K MRR
- ✅ 2-3 Agency tier customers ($1,999/month each)
- ✅ <10% monthly churn
- ✅ 3-6 month sales cycle (down from typical 6-12 months)

---

### How Recruiter's Day-to-Day Changes (See Separate Section Below)

---

### Engineering Requirements (Substantial)

**Phase 1: Multi-Tenant Architecture (Months 1-3) - 200-300 hours**
- [ ] PostgreSQL database with schema-per-tenant or row-level security (20 hrs)
- [ ] User authentication & authorization (Auth0/Clerk) (15 hrs)
- [ ] Admin dashboard (user management, billing, usage) (40 hrs)
- [ ] Web dashboard for recruiters (React + Tailwind) (40 hrs)
- [ ] Email ingestion system (IMAP or dedicated email addresses) (30 hrs)
- [ ] Job deduplication engine (fuzzy matching, ML-based) (30 hrs)
- [ ] Scoring system (adapt current 100-point system) (20 hrs)
- [ ] Stripe billing with usage metering (15 hrs)

**Phase 2: Intelligence Layer (Months 4-6) - 150-200 hours**
- [ ] Specialty streams (create custom job feeds) (30 hrs)
- [ ] ML-based scoring (recruiter feedback loop) (50 hrs)
- [ ] Stale job detection (URL validation, status tracking) (20 hrs)
- [ ] Analytics dashboard (job metrics, ROI reporting) (30 hrs)
- [ ] Browser extension (quick job import from websites) (40 hrs)

**Phase 3: ATS Integration (Months 7-12) - 200-300 hours**
- [ ] REST API (for third-party integrations) (40 hrs)
- [ ] Bullhorn integration (OAuth, sync jobs, webhooks) (80 hrs)
- [ ] Greenhouse/Lever integration (60 hrs)
- [ ] White-label configuration (custom branding, domains) (30 hrs)
- [ ] Advanced analytics (placement tracking, revenue attribution) (50 hrs)

**Total Engineering Time: 550-800 hours = 4-6 months full-time**

**Technology Stack:**
- Backend: Python (FastAPI), PostgreSQL, Redis, Celery
- Frontend: React + TypeScript, Tailwind CSS, Shadcn/UI
- Infrastructure: AWS or Render, Cloudflare, Sentry, PostHog
- Third-party: Stripe, Auth0/Clerk, SendGrid, Firecrawl

---

### Financial Projections (Path 2)

**Unit Economics:**

| Metric | Value | Notes |
|--------|-------|-------|
| **CAC (Customer Acquisition Cost)** | $2,000-5,000 | B2B sales, 3-6 month cycles, need sales team |
| **LTV (Lifetime Value)** | $15,000-30,000 | 2-3 year retention × $500-1,000 ARPU/month |
| **LTV:CAC Ratio** | 3-6:1 | Healthy for B2B SaaS (target >3:1) |
| **Gross Margin** | 75-85% | Software costs low, scraping infra main expense |
| **Payback Period** | 12-18 months | Typical for B2B SaaS |
| **Monthly Churn** | 3-5% | Sticky due to ATS integrations |

**Revenue Projections:**

**Conservative (Path 2):**

| Year | Solo | Team | Agency | Enterprise | Total MRR | ARR | Notes |
|------|------|------|--------|------------|-----------|-----|-------|
| 1 | 20 | 5 | 2 | 0 | $8,473 | $101,676 | MVP launch, manual sales |
| 2 | 50 | 20 | 10 | 0 | $34,920 | $419,040 | ATS integrations, SDR hired |
| 3 | 100 | 50 | 25 | 5 | $109,825 | $1,317,900 | Enterprise deals, partnerships |

**Moderate (Path 2):**

| Year | Total Customers | Avg MRR/Customer | Total MRR | ARR |
|------|----------------|------------------|-----------|-----|
| 1 | 30 | $350 | $10,500 | $126,000 |
| 2 | 100 | $500 | $50,000 | $600,000 |
| 3 | 250 | $600 | $150,000 | $1,800,000 |

**Assumptions:**
- Year 1: Mostly Solo/Team tiers, slow sales ramp
- Year 2: ATS integrations unlock Agency tier, sales accelerate
- Year 3: Enterprise deals + partnerships drive average price up
- 3-5% monthly churn (low due to workflow integration)
- CAC improves over time (referrals, content marketing, partnerships)

---

### Risks & Mitigation (Path 2)

**Technical Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Email scraping rate limits** | Low | Low | Email-based = permission-based, no TOS issues |
| **Job deduplication fails at scale** | Medium | Medium | ML-based matching, manual review queue |
| **Scoring not accurate** | Medium | High | Recruiter feedback loop, continuous improvement |
| **ATS integrations break** | Medium | High | Automated testing, maintain vendor relationships |

**Business Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Recruiters won't pay** | Medium | **Critical** | **Validate with 10+ interviews FIRST** |
| **Sales cycle too long (>6 months)** | High | High | Free trial, focus on small firms first |
| **High churn (>10%/month)** | Low | High | Build sticky integrations (ATS), prove ROI early |
| **Competitors copy product** | High | Medium | Build moat: data, relationships, integrations |

**Market Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Recruiting downturn** | Low | High | Diversify to RPO, in-house recruiters |
| **LinkedIn blocks email scraping** | Low | Low | Email = user forwarding, not web scraping |
| **Market too small** | Low | Medium | 30K recruiting firms, 1.9M recruiters = large TAM |

**Critical Validation Gate:**
- 🚨 **DO NOT BUILD Path 2 unless >70% of recruiters say job discovery is a top-3 pain point**
- 🚨 **DO NOT BUILD Path 2 unless >50% would pay $100+/month**
- 🚨 **DO validate with manual MVP first** (prove concept without 800 hours of coding)

---

## Side-by-Side Comparison

| Dimension | Path 1: Executive Concierge (B2C) | Path 2: Talent Intelligence (B2B SaaS) |
|-----------|-----------------------------------|----------------------------------------|
| **Target Customer** | Senior executives (VP+, Director, CTO) | Mid-market recruiting firms (10-50 recruiters) |
| **Pricing** | $99-299/month per user | $499-1,999/month per firm (5-20 seats) |
| **Time to First Dollar** | 2 weeks (manual onboarding + Stripe link) | 8-12 weeks (need multi-tenant architecture) |
| **Time to $10K MRR** | 3-6 months (50-100 users) | 6-12 months (10-20 firms) |
| **Engineering Required** | 2-4 weeks (billing + self-service onboarding) | 4-6 months (multi-tenant, ATS integrations) |
| **Sales Cycle** | 1-7 days (self-service or quick call) | 30-90 days (demos, trials, negotiations) |
| **CAC (Customer Acquisition Cost)** | $50-200 (mostly organic + paid ads) | $2,000-5,000 (sales team, demos, trials) |
| **LTV (Lifetime Value)** | $1,200-3,600 (6-18 months avg retention) | $15,000-30,000 (2-3 year retention) |
| **Churn** | High (10-15%/month - job search is seasonal) | Low (3-5%/month - sticky ATS integrations) |
| **Revenue Ceiling (Year 3)** | $860K ARR (300 users @ $239/month avg) | $1.8M ARR (250 firms @ $600/month avg) |
| **Competitive Advantage** | Multi-source + domain-specific + connections | Email-based aggregation + ATS integration |
| **Biggest Risk** | Seasonal churn (people find jobs, cancel) | Recruiters may not value job discovery enough |
| **Validation Required** | Ask 5-10 execs: "Would you pay $199/month?" | Ask 10-20 recruiters: "Is job discovery a top-3 pain?" |
| **Best For** | Quick revenue, bootstrapping, side income | Building $1M+ ARR business, venture-scale |

---

## Validation Checklists

### Path 1 Validation (Executive Concierge)

**Critical Questions to Ask Current Users (Wes, Eli, Mario) + 5-10 Prospects:**

- [ ] **Willingness-to-pay:** "Would you pay $99-199/month for this service?"
  - Need: >70% say yes to justify building

- [ ] **Price discovery:** "What's the max you'd pay per month for personalized job matching?"
  - Target: $150-250/month average

- [ ] **Feature prioritization:** "What's the #1 thing that would make this 10X better?"
  - Look for: Patterns in answers (more sources, faster alerts, resume help, etc.)

- [ ] **Referral potential:** "Who else do you know who would want this?"
  - Target: 3-5 referrals per person (word-of-mouth validation)

- [ ] **Current spend:** "What do you currently spend on job search (LinkedIn Premium, resume services, etc.)?"
  - Anchor: If they spend $40-120/month on LinkedIn, $199 is defensible

- [ ] **Pain intensity:** "On a scale of 1-10, how painful is job searching today?"
  - Need: 7+ average to justify premium pricing

**Validation Scorecard:**

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Willingness-to-pay (% yes @ $99+) | >70% | ___ | ⬜ |
| Average max price willing to pay | $150+ | ___ | ⬜ |
| Referrals per person | 3+ | ___ | ⬜ |
| Pain intensity (1-10 scale) | 7+ | ___ | ⬜ |
| Current spend on job search | $50+ | ___ | ⬜ |

**Decision Rule:**
- ✅ If 4/5 metrics pass → **Build Path 1**
- ⚠️ If 2-3/5 metrics pass → **Lower price or add features**
- ❌ If <2/5 metrics pass → **Don't build Path 1**

---

### Path 2 Validation (Talent Intelligence Platform)

**Critical Questions to Ask 10-20 Recruiting Firms:**

- [ ] **Time allocation:** "What % of your week goes to finding jobs vs. finding candidates?"
  - Need: >30% on job discovery to justify building

- [ ] **Current workflow:** "Walk me through how you find new jobs to work on. What tools?"
  - Look for: Manual processes, checking multiple sources, spreadsheets

- [ ] **Pain intensity:** "On 1-10 scale, how painful is job discovery vs. candidate sourcing?"
  - Need: 7+ for job discovery pain

- [ ] **Willingness-to-pay:** "If a tool aggregated all jobs with intelligent matching, how much would you pay per month?"
  - Target: $100-200/month per seat

- [ ] **Must-have features:** "What features would make this 10X better than manual search?"
  - Look for: Patterns (stale job detection, ATS integration, specialty filtering)

- [ ] **Buying process:** "Who makes software purchasing decisions? What's approval process?"
  - Need: <90 day decision cycles

- [ ] **Current tools:** "What tools do you use for job discovery? Why not good enough?"
  - Look for: Complaints about LinkedIn Recruiter, Gem, manual work

- [ ] **Referrals:** "Do you know 3-5 other recruiting firms interested in this?"
  - Target: Network effects, word-of-mouth potential

**Validation Scorecard:**

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| % time on job discovery (avg across firms) | >30% | ___ | ⬜ |
| Pain intensity for job discovery (1-10) | 7+ | ___ | ⬜ |
| Willingness-to-pay (% yes @ $100+/month) | >50% | ___ | ⬜ |
| Average max price per seat | $150+ | ___ | ⬜ |
| Decision cycle | <90 days | ___ | ⬜ |
| Referrals per firm | 3+ | ___ | ⬜ |

**Decision Rule:**
- ✅ If 5/6 metrics pass → **Build Manual MVP first, then automate**
- ⚠️ If 3-4/6 metrics pass → **Rebuild value prop, re-validate**
- ❌ If <3/6 metrics pass → **Don't build Path 2, pivot to Path 1**

---

## Engineering Roadmaps

### Path 1 Engineering Roadmap (2-4 Weeks Total)

**Week 1: Billing Infrastructure**
- [x] Multi-profile support (already working!)
- [x] Email scraping + scoring (already working!)
- [ ] Stripe account setup (2 hours)
- [ ] Create payment links for $99, $199, $299 tiers (1 hour)
- [ ] Build webhook endpoint for subscription events (4 hours)
- [ ] Add `subscription_status` field to profiles table (2 hours)
- [ ] Test end-to-end payment flow (3 hours)

**Week 2: Self-Service Onboarding**
- [ ] Build onboarding form (Typeform or custom HTML) (6 hours)
- [ ] Python script: form submission → profile JSON (4 hours)
- [ ] Auto-send welcome email template (2 hours)
- [ ] Add new profile to weekly scraper cron (2 hours)
- [ ] Test onboarding flow with 2 beta users (4 hours)

**Week 3-4: Simple Dashboard (Optional for MVP)**
- [ ] Flask/FastAPI web app setup (4 hours)
- [ ] Login page (email + password, simple auth) (4 hours)
- [ ] Dashboard: show job history (last 50 jobs) (6 hours)
- [ ] Settings page: edit profile keywords, location (6 hours)
- [ ] Subscription management: cancel, update payment (4 hours)
- [ ] Deploy to Render or AWS (4 hours)

**Total: 40-60 hours of new engineering** (rest is already built!)

---

### Path 2 Engineering Roadmap (4-6 Months Full-Time)

**Phase 1: Multi-Tenant MVP (Months 1-3) - 200-300 hours**

**Weeks 1-2: Database & Auth (40 hours)**
- [ ] PostgreSQL setup with schema-per-tenant (8 hrs)
- [ ] Database migrations (Alembic) (4 hrs)
- [ ] Auth0 or Clerk integration (8 hrs)
- [ ] User/organization models (4 hrs)
- [ ] Role-based access control (RBAC) (6 hrs)
- [ ] Tenant isolation testing (4 hrs)
- [ ] Seed data for testing (2 hrs)
- [ ] Deploy to staging environment (4 hrs)

**Weeks 3-6: Core Product (80 hours)**
- [ ] Email ingestion system (dedicated email per user) (16 hrs)
- [ ] Job deduplication engine (fuzzy matching) (20 hrs)
- [ ] Scoring system (adapt current 100-point system) (12 hrs)
- [ ] Specialty streams (create custom job feeds) (16 hrs)
- [ ] Email digest automation (already have base!) (8 hrs)
- [ ] Job export (CSV for ATS import) (4 hrs)
- [ ] Background job processing (Celery + Redis) (4 hrs)

**Weeks 7-12: Web Dashboard & Billing (80 hours)**
- [ ] React + TypeScript frontend setup (8 hrs)
- [ ] Tailwind CSS + Shadcn/UI components (4 hrs)
- [ ] Admin dashboard: user management (12 hrs)
- [ ] Admin dashboard: billing + usage (8 hrs)
- [ ] Recruiter dashboard: browse jobs (16 hrs)
- [ ] Recruiter dashboard: manage streams (12 hrs)
- [ ] Recruiter dashboard: analytics (job metrics) (8 hrs)
- [ ] Stripe billing with usage metering (12 hrs)

**Phase 2: Intelligence Layer (Months 4-6) - 150-200 hours**

**Weeks 13-16: ML & Feedback (60 hours)**
- [ ] Recruiter feedback system ("good match" / "bad match") (8 hrs)
- [ ] ML-based scoring (learn from feedback) (24 hrs)
- [ ] A/B testing framework (test scoring algorithms) (8 hrs)
- [ ] Performance metrics dashboard (12 hrs)
- [ ] Scoring explainability (why this job scored 85?) (8 hrs)

**Weeks 17-20: Automation & Tools (60 hours)**
- [ ] Stale job detection (URL validation) (12 hrs)
- [ ] Auto-refresh job status weekly (4 hrs)
- [ ] Browser extension (quick job import) (24 hrs)
- [ ] Candidate-to-job matching (reverse search) (16 hrs)
- [ ] Bulk job operations (approve/reject/tag) (4 hrs)

**Weeks 21-24: Analytics & Reporting (40 hours)**
- [ ] Advanced analytics dashboard (16 hrs)
- [ ] Placement tracking (which jobs led to placements) (8 hrs)
- [ ] ROI reporting (hours saved, fees generated) (8 hrs)
- [ ] Export reports (PDF, CSV) (4 hrs)
- [ ] Custom dashboards per user (4 hrs)

**Phase 3: ATS Integration & Scale (Months 7-12) - 200-300 hours**

**Weeks 25-32: ATS Integrations (160 hours)**
- [ ] REST API design + documentation (16 hrs)
- [ ] API authentication (OAuth 2.0) (8 hrs)
- [ ] Webhooks for real-time job notifications (8 hrs)
- [ ] Bullhorn integration (OAuth, sync jobs) (48 hrs)
- [ ] Greenhouse integration (40 hrs)
- [ ] Lever integration (40 hrs)

**Weeks 33-40: Enterprise Features (80 hours)**
- [ ] White-label configuration (custom branding) (16 hrs)
- [ ] Custom domains (subdomain per tenant) (8 hrs)
- [ ] SSO (Single Sign-On) for enterprise (16 hrs)
- [ ] Advanced permissions (team-based access) (12 hrs)
- [ ] Audit logs (compliance) (8 hrs)
- [ ] Data export (GDPR compliance) (8 hrs)
- [ ] SLA monitoring & alerting (12 hrs)

**Weeks 41-48: Polish & Scale (60 hours)**
- [ ] Performance optimization (caching, query tuning) (16 hrs)
- [ ] Load testing (handle 100+ tenants) (8 hrs)
- [ ] Error monitoring (Sentry integration) (4 hrs)
- [ ] Product analytics (PostHog integration) (4 hrs)
- [ ] Customer onboarding flow (12 hrs)
- [ ] Help documentation (16 hrs)

**Total: 550-800 hours = 14-20 weeks full-time = 4-6 months**

---

## Financial Projections (Detailed)

### Path 1: Executive Concierge - 3-Year Projection

**Year 1:**

| Quarter | Customers | Avg Price | MRR | QRR | ARR (Run Rate) | Notes |
|---------|-----------|-----------|-----|-----|----------------|-------|
| Q1 | 10 | $149 | $1,490 | $4,470 | $17,880 | Beta launch + public launch |
| Q2 | 25 | $179 | $4,475 | $13,425 | $53,700 | Organic growth |
| Q3 | 45 | $189 | $8,505 | $25,515 | $102,060 | Paid ads start |
| Q4 | 70 | $199 | $13,930 | $41,790 | $167,160 | Holiday hiring season |

**Year 1 Total Revenue:** $85,200 (average across quarters)

**Year 2:**

| Quarter | Customers | Avg Price | MRR | QRR | ARR (Run Rate) |
|---------|-----------|-----------|-----|-----|----------------|
| Q1 | 100 | $209 | $20,900 | $62,700 | $250,800 |
| Q2 | 130 | $219 | $28,470 | $85,410 | $341,640 |
| Q3 | 160 | $229 | $36,640 | $109,920 | $439,680 |
| Q4 | 200 | $239 | $47,800 | $143,400 | $573,600 |

**Year 2 Total Revenue:** $401,400

**Year 3:**

| Quarter | Customers | Avg Price | MRR | QRR | ARR (Run Rate) |
|---------|-----------|-----------|-----|-----|----------------|
| Q1 | 240 | $249 | $59,760 | $179,280 | $717,120 |
| Q2 | 270 | $259 | $69,930 | $209,790 | $839,160 |
| Q3 | 290 | $269 | $78,010 | $234,030 | $936,120 |
| Q4 | 300 | $279 | $83,700 | $251,100 | $1,004,400 |

**Year 3 Total Revenue:** $874,200

**Cumulative 3-Year Revenue:** $1,360,800

**Assumptions:**
- 10-15% monthly churn Year 1, decreasing to 7-10% Year 2-3 as product matures
- Average price increases $10-30/quarter as features added
- Customer acquisition: 70% organic (content, referrals), 30% paid ads
- CAC improves over time: $200 → $150 → $100 as brand builds

---

### Path 2: Talent Intelligence Platform - 3-Year Projection

**Year 1:**

| Quarter | Solo | Team | Agency | Enterprise | Total MRR | QRR | ARR (Run Rate) |
|---------|------|------|--------|------------|-----------|-----|----------------|
| Q1 | 5 | 2 | 0 | 0 | $1,493 | $4,479 | $17,916 |
| Q2 | 12 | 4 | 1 | 0 | $4,184 | $12,552 | $50,208 |
| Q3 | 18 | 6 | 2 | 0 | $7,776 | $23,328 | $93,312 |
| Q4 | 25 | 8 | 3 | 0 | $12,465 | $37,395 | $149,580 |

**Year 1 Total Revenue:** $77,754

**Year 2:**

| Quarter | Solo | Team | Agency | Enterprise | Total MRR | QRR | ARR (Run Rate) |
|---------|------|------|--------|------------|-----------|-----|----------------|
| Q1 | 35 | 12 | 5 | 0 | $19,453 | $58,359 | $233,436 |
| Q2 | 45 | 18 | 8 | 1 | $29,446 | $88,338 | $353,352 |
| Q3 | 55 | 24 | 12 | 2 | $41,433 | $124,299 | $497,196 |
| Q4 | 65 | 30 | 15 | 3 | $56,420 | $169,260 | $677,040 |

**Year 2 Total Revenue:** $440,193

**Year 3:**

| Quarter | Solo | Team | Agency | Enterprise | Total MRR | QRR | ARR (Run Rate) |
|---------|------|------|--------|------------|-----------|-----|----------------|
| Q1 | 80 | 40 | 20 | 5 | $77,910 | $233,730 | $934,920 |
| Q2 | 95 | 50 | 25 | 7 | $99,898 | $299,694 | $1,198,776 |
| Q3 | 105 | 60 | 30 | 10 | $125,885 | $377,655 | $1,510,620 |
| Q4 | 115 | 70 | 35 | 12 | $154,872 | $464,616 | $1,858,464 |

**Year 3 Total Revenue:** $1,350,750

**Cumulative 3-Year Revenue:** $1,868,697

**Assumptions:**
- 3-5% monthly churn (low due to ATS integrations)
- Average price per customer increases as mix shifts to Agency/Enterprise
- Sales cycle: 90 days Year 1, 60 days Year 2, 45 days Year 3 (improves with case studies, referrals)
- CAC: $5,000 Year 1 → $3,000 Year 2 → $2,000 Year 3 (word-of-mouth, partnerships)

---

## Recommendation

### **My Strong Recommendation: Start with Path 1, Pivot to Path 2 if Validated**

**Why Path 1 First:**

1. ✅ **Fastest validation** - 2 weeks to first paying customer vs. 8-12 weeks
2. ✅ **Lower risk** - $2K investment vs. $50K+ (6 months of development)
3. ✅ **Proven concept** - Wes's 8.6% hit rate proves it works for robotics execs
4. ✅ **Bootstrap to Path 2** - Use Path 1 revenue to fund Path 2 development
5. ✅ **Learn from customers** - B2C feedback informs B2B product

**Path 1 → Path 2 Transition Strategy:**

**Months 1-3: Launch Path 1 (Executive Concierge)**
- Get 10-20 paying customers @ $99-199/month
- Learn what features matter most
- Build customer testimonials
- Revenue: $2K-4K MRR

**Months 4-6: Validate Path 2 (Recruiter Interviews)**
- Use Path 1 customers as case studies for recruiter pitches
- Interview 20+ recruiting firms using validation checklist
- Run manual MVP with 3-5 pilot recruiters
- Decision point: Does >70% validate job discovery pain?

**Months 7-12: Build Path 2 (If Validated)**
- Use Path 1 revenue ($2K-4K/month) to fund development
- Keep Path 1 running (cash flow + learning)
- Build multi-tenant architecture for Path 2
- Launch Path 2 MVP to pilot customers

**Month 13+: Scale Both or Sunset Path 1**
- If Path 2 works: Focus 80% on B2B, maintain Path 1 for cash flow
- If Path 2 fails: Double down on Path 1, reach $10K-20K MRR

**Decision Framework:**

| If... | Then... |
|-------|---------|
| Path 1 gets 20+ customers in 3 months | ✅ Product-market fit, keep scaling |
| Path 1 gets <10 customers in 3 months | ⚠️ Fix pricing, sources, or positioning |
| Path 2 validation: >70% recruiters say yes | ✅ Build Path 2 in parallel |
| Path 2 validation: <50% recruiters say yes | ❌ Don't build Path 2, focus on Path 1 |
| Path 1 revenue > $5K MRR | ✅ Can fund Path 2 development |
| Path 1 revenue < $2K MRR | ⚠️ Fix Path 1 first before attempting Path 2 |

---

## Next Steps (This Week)

### **For Path 1:**
1. [ ] Ask Wes/Eli/Mario: "Would you pay $99-199/month for this?"
2. [ ] Set up Stripe account + payment link
3. [ ] Create simple landing page (Carrd: $19/year)
4. [ ] Draft email to 10 VPs/Directors in your network
5. [ ] Target: 1 paying customer this week

### **For Path 2:**
1. [ ] Reach out to recruiter contacts with interview request
2. [ ] Schedule 5-10 recruiter calls for next 2 weeks
3. [ ] Use validation checklist during calls
4. [ ] Create summary scorecard: "Should I build Path 2?"
5. [ ] Decision by end of Month 1: Build manual MVP or pivot to Path 1 only

---

## Appendix: Email Scraping as Competitive Advantage

### Why Email-Based Ingestion Beats Web Scraping

**Legal & Technical Advantages:**

1. **No TOS Violations**
   - User forwards emails TO your system (permission-based)
   - You're not scraping LinkedIn/Indeed websites
   - Safe harbor under CAN-SPAM Act (processing emails sent to you)

2. **No Rate Limiting**
   - Email forwarding = no API rate limits
   - Unlimited job sources (user subscribes to newsletters they trust)
   - Scales infinitely (each user brings their own data)

3. **Quality Signal**
   - Users subscribe to newsletters they actually read
   - Self-selecting for quality sources
   - Reduces spam/low-quality jobs

4. **Unique Data Moat**
   - Competitors scraping LinkedIn/Indeed get same data
   - Your users bring UNIQUE sources (niche newsletters, industry boards)
   - Network effects: More users = more unique sources

**How It Works:**

**For B2C (Path 1):**
1. User signs up, gets onboarding call
2. You ask: "Which job newsletters do you currently read?" (LinkedIn, Supra, Built In, etc.)
3. User forwards emails to `adam-jobs@yourdomain.com` or sets up auto-forwarding rule
4. Your system parses emails, scores jobs, sends weekly digest
5. User doesn't need to change behavior (already reading newsletters)

**For B2B (Path 2):**
1. Recruiting firm signs up
2. Each recruiter gets unique forwarding email: `recruiter1-jobs@yourdomain.com`
3. Recruiter subscribes to industry newsletters (robotics, fintech, QA, etc.)
4. Recruiter sets up Gmail filter: "Auto-forward emails from LinkedIn Jobs, Built In, etc. to forwarding email"
5. Your system aggregates across all recruiters, deduplicates, scores, sends digests
6. Recruiting firm gets "all jobs from all sources in one place"

**Positioning:**
- Path 1: "Bring your own job sources - we make sense of them all"
- Path 2: "Your recruiters already subscribe to newsletters. We turn them into your job discovery engine."

This approach:
- ✅ Avoids legal issues (permission-based)
- ✅ Scales infinitely (no rate limits)
- ✅ Creates unique data moat (niche sources competitors don't have)
- ✅ Builds on existing behavior (people already read newsletters)
- ✅ Works for both B2C and B2B models

---

**End of Document**

---

**Meta Notes:**
- **Document version:** 1.0
- **Last updated:** 2026-02-02
- **Next review:** After customer validation (Path 1: 1 month, Path 2: 2 months)
- **Owner:** Adam White
- **Related docs:**
  - `docs/development/MULTI_PROFILE_GUIDE.md` (technical architecture)
  - `docs/development/ADDING_NEW_PROFILES.md` (scaling to more users)
  - `README.md` (project overview)
