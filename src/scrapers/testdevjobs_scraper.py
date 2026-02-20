"""
TestDevJobs Scraper

Scrapes QA/testing jobs from TestDevJobs.com.
Primary beneficiary: Mario (QA/testing profile).

Job board focuses on remote testing positions with clean markdown structure.
"""

import re
from dataclasses import dataclass
from typing import TypedDict


class JobFields(TypedDict):
    """Type definition for job fields extracted from markdown"""

    location: str
    salary: str
    remote_status: str
    job_type: str
    tech_tags: list[str]


@dataclass
class TestDevJob:
    """Represents a job from TestDevJobs"""

    company: str
    title: str
    location: str
    link: str
    posted_date: str
    salary: str
    remote_status: str
    job_type: str
    tech_tags: list[str]


class TestDevJobsScraper:
    """Scraper for TestDevJobs.com remote jobs board"""

    def parse_jobs_from_page(self, markdown: str) -> list[TestDevJob]:
        """
        Parse job listings from TestDevJobs markdown

        Args:
            markdown: Page content from Firecrawl

        Returns:
            List of TestDevJob objects

        Structure:
            [CompanyLetter](company-url)

            Company Name

            Date

            [Job Title](job-url)

            📍 Location
            💵 Salary (optional)
            🌐 Remote Status
            ⏰ Job Type

            [Tech1] [Tech2]...
        """
        jobs = []

        # Split by company sections (lines starting with company initial link)
        # Pattern: [Letter](url)\n\nCompany Name\n\nDate\n\n[Title](url)
        job_blocks = re.split(r"\n\[([A-Z])\]\(https://testdevjobs\.com/job/", markdown)

        # Process blocks in groups of 2 (letter, then content)
        for i in range(1, len(job_blocks), 2):
            if i + 1 >= len(job_blocks):
                break

            # Extract job URL and content
            url_content = self._extract_job_url_and_content(job_blocks[i + 1])
            if not url_content:
                continue
            job_url, content = url_content

            # Extract basic job info (company, date, title)
            basic_info = self._extract_basic_job_info(content)
            if not basic_info:
                continue

            # Extract additional fields
            fields = self._extract_job_fields(content)

            job = TestDevJob(
                company=basic_info["company"],
                title=basic_info["title"],
                posted_date=basic_info["posted_date"],
                location=fields["location"],
                link=job_url,
                salary=fields["salary"],
                remote_status=fields["remote_status"],
                job_type=fields["job_type"],
                tech_tags=fields["tech_tags"],
            )
            jobs.append(job)

        return jobs

    def _extract_job_url_and_content(self, job_block: str) -> tuple[str, str] | None:
        """Extract job URL and content from a job block"""
        job_url_match = re.search(r"^([^)]+)\)", job_block)
        if not job_url_match:
            return None

        job_url = "https://testdevjobs.com/job/" + job_url_match.group(1)
        content = job_block[job_url_match.end() :]
        return (job_url, content)

    def _extract_basic_job_info(self, content: str) -> dict[str, str] | None:
        """Extract company, date, and title from job content"""
        # Extract company name and date (first two non-empty lines)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) < 4:
            return None

        # Extract job title (markdown link pattern)
        title_match = re.search(r"\[([^\]]+)\]", content)
        if not title_match:
            return None

        return {
            "company": lines[0],
            "posted_date": lines[1],
            "title": title_match.group(1),
        }

    def _extract_job_fields(self, content: str) -> JobFields:
        """Extract location, salary, remote status, job type, and tech tags"""
        # Extract location (after 📍 emoji)
        location_match = re.search(r"📍\s*([^\n💵🌐⏰]+)", content)
        location = location_match.group(1).strip() if location_match else "Remote"

        # Extract salary (after 💵 emoji, optional)
        salary_match = re.search(r"💵\s*([^\n🌐⏰]+)", content)
        salary = salary_match.group(1).strip() if salary_match else ""

        # Extract remote status (after 🌐 emoji)
        remote_match = re.search(r"🌐\s*([^\n⏰]+)", content)
        remote_status = remote_match.group(1).strip() if remote_match else "Remote"

        # Extract job type (after ⏰ emoji)
        job_type_match = re.search(r"⏰\s*([^\n\[]+)", content)
        job_type = job_type_match.group(1).strip() if job_type_match else "Full Time"

        # Extract tech tags (markdown links after job type)
        tech_section = content[content.find("⏰") :] if "⏰" in content else ""
        tech_tags = re.findall(r"\[([^\]]+)\]\(https://testdevjobs\.com/tag/", tech_section)

        return {
            "location": location,
            "salary": salary,
            "remote_status": remote_status,
            "job_type": job_type,
            "tech_tags": tech_tags,
        }
