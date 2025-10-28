"""
Work In Tech job board email parser
Handles job alerts from getro.com/Work In Tech platform
"""

import re

from bs4 import BeautifulSoup


def parse_workintech_email(html_content: str) -> list[dict[str, str]]:
    """
    Parse Work In Tech job board emails from getro.com

    Email format:
    - From: Work In Tech or getro.com
    - Subject: New jobs for you in Work In Tech's job board
    """
    soup = BeautifulSoup(html_content, "html.parser")
    jobs = []

    # Find job links - they link to getro.com with job details
    job_links = soup.find_all("a", href=re.compile(r"getro\.com/.*click\?"))

    # Track processed jobs to avoid duplicates
    processed_jobs = set()

    for link in job_links:
        try:
            # Look for job title in link or nearby span
            title_span = link.find("span", style=re.compile(r"font-size:\s*16px"))
            title = title_span.get_text(strip=True) if title_span else link.get_text(strip=True)

            # Skip if not a job title (navigation links, etc.)
            if not title or len(title) < 5:
                continue
            if title in ["See more jobs", "this link", "Work In Tech"]:
                continue

            # Avoid duplicates
            if title in processed_jobs:
                continue
            processed_jobs.add(title)

            # Extract URL
            url = link.get("href", "")

            # The actual job link is often embedded in the tracking URL
            # Work In Tech uses redirects, so we'll use the tracking URL
            if not url.startswith("http"):
                url = f"https://{url}"

            # Find company name - usually in image alt text or nearby text
            company = "Unknown Company"
            location = "Unknown Location"

            # Look in parent container
            parent_container = link.find_parent(["td", "table", "div"])
            if parent_container:
                # Company often in image alt attribute
                img = parent_container.find("img", alt=True)
                if img and "Logo" in img.get("alt", ""):
                    company = img["alt"].replace(" Logo", "").strip()

                # Or in preceding text
                if company == "Unknown Company":
                    # Look for text patterns
                    text = parent_container.get_text()
                    # Extract company from patterns like "Company Name · Location"
                    company_match = re.search(r"([^·\n]+)\s*·\s*([^·\n]+)", text)
                    if company_match:
                        potential_company = company_match.group(1).strip()
                        potential_location = company_match.group(2).strip()
                        # Make sure it's not the job title
                        if potential_company != title:
                            company = potential_company
                            location = potential_location

            # Additional location extraction
            if location == "Unknown Location":
                # Look for location in subscription preferences mentioned in email
                location_text = soup.find(
                    text=re.compile(r"Ontario|Toronto|Canada|Remote", re.IGNORECASE)
                )
                if location_text:
                    location = "Ontario, Canada"  # Default for this job board

            jobs.append({"title": title, "company": company, "location": location, "link": url})

        except Exception as e:
            print(f"Error parsing Work In Tech job: {e}")
            continue

    return jobs


def can_parse(from_addr: str, subject: str) -> bool:
    """
    Check if this parser can handle the email
    """
    from_lower = from_addr.lower()
    subject_lower = subject.lower()

    # Work In Tech/Getro emails
    if "getro" in from_lower or "work in tech" in from_lower:
        return True

    if "work in tech" in subject_lower and "job" in subject_lower:
        return True

    # Pattern for getro job board emails
    return "job board" in subject_lower and (
        "new job" in subject_lower or "job matching" in subject_lower
    )
