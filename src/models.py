"""
Standardized data models for job opportunities
"""
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class OpportunityData(BaseModel):
    """
    Standardized format for all job opportunities
    Parsers convert their specific formats into this model
    """
    # Source information
    source: str = Field(..., description="Source of the opportunity (linkedin, f6s, indeed, etc.)")
    source_email: Optional[str] = Field(None, description="Email address that sent the alert")

    # Opportunity type
    type: Literal["direct_job", "funding_lead"] = Field(..., description="Type of opportunity")

    # Company information
    company: str = Field(..., description="Company name")
    company_location: Optional[str] = Field(None, description="Company location/headquarters")
    company_website: Optional[str] = Field(None, description="Company website URL")

    # Job information (for direct_job type)
    title: Optional[str] = Field(None, description="Job title (for direct jobs)")
    location: Optional[str] = Field(None, description="Job location")
    link: Optional[str] = Field(None, description="Direct link to job posting")
    description: Optional[str] = Field(None, description="Job description")
    salary: Optional[str] = Field(None, description="Salary information")
    job_type: Optional[str] = Field(None, description="Full-time, Contract, etc.")
    posted_date: Optional[str] = Field(None, description="When job was posted")

    # Funding information (for funding_lead type)
    funding_stage: Optional[str] = Field(None, description="Seed, Series A, Series B, etc.")
    funding_amount: Optional[str] = Field(None, description="Amount raised (e.g., $7m)")
    funding_amount_usd: Optional[float] = Field(None, description="Normalized funding in USD")
    investors: Optional[List[str]] = Field(None, description="List of investors")
    industry_tags: Optional[List[str]] = Field(None, description="Industry categories (AI, Healthcare, etc.)")

    # Research flags
    needs_research: bool = Field(default=False, description="Whether company needs career page research")
    career_page_url: Optional[str] = Field(None, description="Career/jobs page URL if found")
    research_attempted: bool = Field(default=False, description="Whether research was attempted")
    research_notes: Optional[str] = Field(None, description="Notes from research attempt")

    # Metadata
    received_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    raw_content: Optional[str] = Field(None, description="Raw content for debugging")

    # Filtering results (populated later)
    keywords_matched: Optional[List[str]] = Field(None, description="Keywords that matched")
    filter_passed: Optional[bool] = Field(None, description="Whether it passed filtering")
    filter_reason: Optional[str] = Field(None, description="Reason for filter decision")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "source": "linkedin",
                    "type": "direct_job",
                    "company": "Acme Corp",
                    "title": "Senior Product Manager",
                    "link": "https://linkedin.com/jobs/12345",
                    "needs_research": False
                },
                {
                    "source": "f6s",
                    "type": "funding_lead",
                    "company": "Provision.com",
                    "company_location": "Toronto, Canada",
                    "funding_stage": "Seed",
                    "funding_amount": "$7m",
                    "funding_amount_usd": 7000000,
                    "investors": ["Sequoia Capital", "One Way Ventures"],
                    "industry_tags": ["AI", "Software"],
                    "needs_research": True
                }
            ]
        }


class EnrichmentResult(BaseModel):
    """Result from career page research/enrichment"""
    success: bool
    career_page_url: Optional[str] = None
    jobs_found: List[OpportunityData] = Field(default_factory=list)
    method_used: Optional[str] = None  # pattern, google, manual
    error: Optional[str] = None


class ParserResult(BaseModel):
    """Result from parsing an email"""
    parser_name: str
    success: bool
    opportunities: List[OpportunityData] = Field(default_factory=list)
    error: Optional[str] = None
