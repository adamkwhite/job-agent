# PRD: Job Link Verification

## Overview
Add link verification to filter out expired/closed job postings before including them in digest emails.

## Problem Statement
Users receive digest emails containing links to job postings that are no longer accepting applications. This wastes time clicking dead links and reduces trust in the system.

**Example:** Staff Product Manager, AI/ML @ Absorb Software was stored Nov 8, included in digest Nov 22, but LinkedIn showed "No longer accepting applications."

## Current State
- Jobs are filtered by age (14 days max) - implemented
- No verification that job links are still active
- Expired jobs slip through if they close before the 14-day window

## Proposed Solution
Before including a job in a digest, verify the link is still active by checking for "closed" indicators on the job page.

## Functional Requirements

### FR1: Link Verification Service
- Create a service that checks if a job URL is still accepting applications
- Support LinkedIn job URLs initially (majority of jobs)
- Return status: `active`, `closed`, `unknown`, `error`

### FR2: LinkedIn-Specific Detection
- Detect "No longer accepting applications" text
- Detect redirect to job search (job removed)
- Detect 404 errors
- Handle rate limiting gracefully

### FR3: Digest Integration
- Before sending digest, verify each job link
- Exclude jobs with `closed` status
- Include jobs with `active` or `unknown` status (fail open)
- Log verification results for debugging

### FR4: Caching & Performance
- Cache verification results for 24 hours
- Don't re-verify same URL within cache period
- Add `last_verified_at` and `verification_status` to database

### FR5: Rate Limiting
- Limit verification requests to avoid being blocked
- Max 10 requests per minute to LinkedIn
- Spread requests over time if many jobs to verify

## Non-Functional Requirements

### NFR1: Performance
- Verification should add <30 seconds to digest generation
- Use async/parallel requests where possible

### NFR2: Reliability
- Fail open: if verification fails, include job anyway
- Don't block digest if LinkedIn is unreachable

### NFR3: Observability
- Log verification attempts and results
- Track success/failure rates

## Out of Scope
- Verifying non-LinkedIn job boards (future enhancement)
- Real-time verification when jobs are stored
- Automatic job status updates

## Success Metrics
- Reduce expired job links in digests by 90%
- Digest generation time increase <30 seconds

## Technical Approach
1. Use Firecrawl API (already integrated) to fetch job pages
2. Parse response for closed indicators
3. Store verification status in database
4. Filter during digest generation

## Related
- Issue #42: Job links pointing to closed/expired postings
- Age filter (14 days) already implemented
