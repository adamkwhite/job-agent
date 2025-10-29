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
    job_links = soup.find_all("a", href=re.compile(r"getro\.com/"))

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
            if title in ["See more jobs", "this link", "Work In Tech", "Update your preferences"]:
                continue
            # Skip common navigation patterns
            if any(
                skip in title.lower()
                for skip in ["preferences", "unsubscribe", "settings", "view more"]
            ):
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

                # Look for company and location in div/span elements
                # Find all text elements that contain the middot separator
                for elem in parent_container.find_all(["div", "span", "p"]):
                    elem_text = elem.get_text(strip=True)
                    # Extract company from patterns like "Company Name · Location"
                    # Use split instead of regex to avoid ReDoS vulnerability
                    if "·" in elem_text:
                        parts = elem_text.split("·", 1)  # Split on first middot only
                        if len(parts) == 2:
                            potential_company = parts[0].strip()
                            potential_location = parts[1].strip()
                            # Make sure it's not the job title
                            if potential_company and potential_company != title:
                                if company == "Unknown Company":
                                    company = potential_company
                                # Always use the extracted location if found
                                if potential_location:
                                    location = potential_location
                                break

            # Additional location extraction - only use as fallback
            if location == "Unknown Location":
                # Look for location in subscription preferences mentioned in email
                location_text = soup.find(
                    string=re.compile(r"Ontario|Toronto|Canada|Remote", re.IGNORECASE)
                )
                if location_text:
                    location = "Ontario, Canada"  # Default fallback for this job board

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
