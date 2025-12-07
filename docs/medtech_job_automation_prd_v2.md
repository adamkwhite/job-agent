# MedTech Job Discovery & Application Automation - PRD

## Overview
An automated workflow that discovers relevant job opportunities in medical technology companies, researches target companies, scores opportunities based on user criteria, and facilitates application preparation.

## Primary Goals
1. **Opportunity Identification**: Find medtech roles that align with user values and career objectives
2. **Application Preparation**: Streamline the process from discovery to customized application

## Target User
Product management professionals (senior IC to leadership level) seeking roles at mission-driven medtech companies focused on patient impact.

## Critical Timing Constraint
**12-Hour Application Window**: Research indicates applications must be submitted within 12 hours of job posting to avoid being lost in the queue.

## Version Roadmap

### V1: Minimal Viable Product (Week 1 Implementation)
**Goal**: Validate email-based job discovery with instant notifications

**Scope**:
- Email parsing for job alerts (10-15 emails daily)
- Basic keyword filtering (include/exclude lists)
- Instant notifications for relevant opportunities
- Manual company research and application prep

**Features**:
- **Email Monitoring**: IMAP connection to dedicated Gmail account
- **Simple Parsing**: Extract job title, company name, application link
- **Binary Filtering**: Pass/fail based on basic keywords
  - Include: "product manager", "product management", medtech indicators
  - Exclude: "EMR", "documentation", "administrative"
- **Instant Alerts**: SMS/email notification with job details
- **Manual Process**: User handles all research and application prep

**Technical Stack**:
- Self-hosted n8n on Hostinger VPS ($4-7/month)
- Gmail IMAP integration
- Basic text parsing and filtering
- SMS/email notification service

**Success Criteria**:
- Notifications arrive within 30 minutes of job posting
- 90%+ accuracy in relevant job identification
- Zero false negatives for target companies

### V2: Enhanced Intelligence (Weeks 2-4)
**Goal**: Add automated company research and opportunity scoring

**Added Features**:
- **Company Research Pipeline**: Automated intelligence gathering
  - Business metrics (funding stage, company size)
  - Employee development patterns
  - Published values and culture indicators
- **Opportunity Scoring System**: Weighted criteria evaluation
  - Mission alignment with patient impact
  - Role fit and career progression potential
  - Company stage and business health
  - Cultural values alignment
- **Enhanced Notifications**: Rich email digest with scoring breakdown
- **Application Prep Templates**: Pre-built resume and cover letter templates

**Research Categories**:
1. **Business Metrics**: Funding stage, financial health, growth trajectory
2. **Internal Insights**: Team size, organizational structure
3. **Employee Development**: Retention patterns, career progression
4. **Culture & Values**: Mission statements, workplace practices

**Technical Enhancements**:
- Company research APIs integration
- Scoring algorithm implementation
- HTML email digest generation
- Template management system

### V3: Full Automation (Future)
**Goal**: Semi-automated application submission with confidence building

**Advanced Features**:
- **Semi-Automated Applications**: System drafts, user approves
- **Intelligent Resume Customization**: AI-powered keyword integration
- **Interview Preparation**: Company-specific research and talking points
- **Success Tracking**: Monitor application effectiveness and iterate
- **Advanced Scoring**: Machine learning-based opportunity ranking

**Automation Capabilities**:
- **Auto-Submit Threshold**: Applications scoring above confidence level
- **Smart Scheduling**: Optimal timing for application submission
- **Advanced Personalization**: LinkedIn activity analysis
- **Interview Coordination**: Automated scheduling for successful applications

**Optional Explorations**:
- **Firecrawl Integration**: Enhanced web scraping for company research
- **Network Analysis**: Warm introduction identification
- **Personal Brand Optimization**: Application material enhancement

## Implementation Timeline & Costs

### V1 Costs (Week 1)
- **Hostinger VPS**: $4-7/month
- **SMS notifications**: $5-10/month
- **Total**: $9-17/month

### V2 Costs (Weeks 2-4)
- **Base hosting**: $4-7/month
- **Company research APIs**: $50-100/month
- **Enhanced notifications**: $10/month
- **Total**: $64-117/month

### V3 Costs (Future)
- **Base infrastructure**: $64-117/month
- **Advanced AI services**: $50-200/month
- **Optional Firecrawl**: $20-50/month
- **Total**: $134-367/month

## Success Metrics by Version

### V1 Success Metrics
- **Notification Speed**: Alerts within 30 minutes of job posting
- **Filtering Accuracy**: 90%+ relevant job identification
- **Coverage**: Zero missed opportunities from target companies
- **User Satisfaction**: Manual research time reduced by 50%

### V2 Success Metrics
- **Research Quality**: User satisfaction with automated company intelligence
- **Decision Speed**: Time from notification to application decision
- **Application Response Rate**: Interview requests per application submitted
- **System Trust**: User confidence in scoring accuracy

### V3 Success Metrics
- **Automation Adoption**: Percentage of applications using automated prep
- **Quality Consistency**: Variance in application quality across opportunities
- **End-to-End Speed**: Time from job discovery to application submission
- **ROI**: Cost per successful interview/offer

## Technical Architecture

### V1 Technical Stack
- **n8n Self-Hosted**: Hostinger VPS (1 CPU, 2GB RAM)
- **Email Integration**: Gmail IMAP monitoring
- **Database**: SQLite for job storage
- **Notifications**: SMS via Twilio, email via SMTP
- **Parsing**: Basic regex/string matching

### V2 Technical Enhancements
- **Company Research**: External APIs (Clearbit, LinkedIn, funding databases)
- **Scoring Engine**: Weighted algorithm implementation
- **Database**: PostgreSQL for complex queries
- **Email Templates**: HTML generation with embedded scoring
- **Web Interface**: Basic dashboard for configuration

### V3 Technical Additions
- **AI Services**: OpenAI/Claude for resume customization
- **Advanced Scraping**: Optional Firecrawl integration
- **Analytics**: Application success tracking and ML optimization
- **Mobile App**: Native mobile notifications and review
- **Integration APIs**: Connect with ATS systems

## Risk Assessment

### V1 Risks (Low)
- **Email parsing failures**: Mitigated by simple, robust parsing
- **False positives**: Acceptable with manual review
- **Server downtime**: Low impact, easy to restart

### V2 Risks (Medium)
- **API rate limits**: Managed through usage monitoring
- **Research accuracy**: Validated through user feedback
- **Increased complexity**: Managed through modular design

### V3 Risks (Higher)
- **Over-automation**: Mitigated by confidence thresholds
- **Quality degradation**: Monitored through success metrics
- **User trust**: Built through gradual automation increase

## User Experience Flow by Version

### V1 Flow
1. **Setup**: Configure email alerts and notification preferences
2. **Receive**: Get instant notifications for relevant jobs
3. **Review**: Manually research companies and roles
4. **Apply**: Manual application process with original materials

### V2 Flow
1. **Setup**: Configure scoring weights and research preferences
2. **Receive**: Rich email digest with company intelligence
3. **Review**: Drill down into scoring details and research
4. **Decide**: Click "Proceed" for promising opportunities
5. **Prepare**: Use templates for faster application creation

### V3 Flow
1. **Setup**: Configure automation thresholds and preferences
2. **Review**: Approve/modify system-generated applications
3. **Submit**: One-click submission with tracking
4. **Follow-up**: Automated interview preparation and scheduling

## Key Differentiators
- **Mission-Focused**: Specifically targets patient-impact medtech companies
- **Phased Approach**: Start simple, validate, then enhance
- **Cost-Effective**: Self-hosted solution with minimal ongoing costs
- **Speed-Optimized**: Built for 12-hour application window constraint
- **Human-Centric**: Maintains human oversight while reducing manual work

## Next Steps

### Week 1: V1 Implementation
1. Set up Hostinger VPS and n8n installation
2. Configure Gmail IMAP connections and job alert subscriptions
3. Build basic email parsing and filtering workflow
4. Test notification system and filtering accuracy
5. Document false positives/negatives for V2 improvements

### Weeks 2-4: V2 Planning
1. Evaluate V1 performance and user feedback
2. Research company intelligence APIs and pricing
3. Design scoring algorithm and weighting system
4. Plan enhanced email digest format

### Future: V3 Roadmap
1. Assess automation readiness based on V2 success
2. Investigate AI services for application customization
3. Design confidence-building mechanisms for automated submissions
4. Plan integration with external application tracking systems
