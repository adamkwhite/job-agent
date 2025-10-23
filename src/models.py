"""
Standardized data models for job opportunities
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OpportunityData(BaseModel):
    """
    Standardized format for all job opportunities
    Parsers convert their specific formats into this model
    """

    # Source information
    source: str = Field(..., description="Source of the opportunity (linkedin, f6s, indeed, etc.)")
    source_email: str | None = Field(None, description="Email address that sent the alert")

    # Opportunity type
    type: Literal["direct_job", "funding_lead"] = Field(..., description="Type of opportunity")

    # Company information
    company: str = Field(..., description="Company name")
    company_location: str | None = Field(None, description="Company location/headquarters")
    company_website: str | None = Field(None, description="Company website URL")

    # Job information (for direct_job type)
    title: str | None = Field(None, description="Job title (for direct jobs)")
    location: str | None = Field(None, description="Job location")
    link: str | None = Field(None, description="Direct link to job posting")
    description: str | None = Field(None, description="Job description")
    salary: str | None = Field(None, description="Salary information")
    job_type: str | None = Field(None, description="Full-time, Contract, etc.")
    posted_date: str | None = Field(None, description="When job was posted")

    # Funding information (for funding_lead type)
    funding_stage: str | None = Field(None, description="Seed, Series A, Series B, etc.")
    funding_amount: str | None = Field(None, description="Amount raised (e.g., $7m)")
    funding_amount_usd: float | None = Field(None, description="Normalized funding in USD")
    investors: list[str] | None = Field(None, description="List of investors")
    industry_tags: list[str] | None = Field(
        None, description="Industry categories (AI, Healthcare, etc.)"
    )

    # Research flags
    needs_research: bool = Field(
        default=False, description="Whether company needs career page research"
    )
    career_page_url: str | None = Field(None, description="Career/jobs page URL if found")
    research_attempted: bool = Field(default=False, description="Whether research was attempted")
    research_notes: str | None = Field(None, description="Notes from research attempt")

    # Metadata
    received_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    raw_content: str | None = Field(None, description="Raw content for debugging")

    # Filtering results (populated later)
    keywords_matched: list[str] | None = Field(None, description="Keywords that matched")
    filter_passed: bool | None = Field(None, description="Whether it passed filtering")
    filter_reason: str | None = Field(None, description="Reason for filter decision")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "source": "linkedin",
                    "type": "direct_job",
                    "company": "Acme Corp",
                    "title": "Senior Product Manager",
                    "link": "https://linkedin.com/jobs/12345",
                    "needs_research": False,
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
                    "needs_research": True,
                },
            ]
        }


class EnrichmentResult(BaseModel):
    """Result from career page research/enrichment"""

    success: bool
    career_page_url: str | None = None
    jobs_found: list[OpportunityData] = Field(default_factory=list)
    method_used: str | None = None  # pattern, google, manual
    error: str | None = None


class ParserResult(BaseModel):
    """Result from parsing an email"""

    parser_name: str
    success: bool
    opportunities: list[OpportunityData] = Field(default_factory=list)
    error: str | None = None
