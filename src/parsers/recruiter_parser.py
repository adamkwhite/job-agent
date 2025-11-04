"""
Direct recruiter and LinkedIn saved jobs email parser
Handles:
1. LinkedIn saved/recommended job emails
2. Direct recruiter outreach
3. Forwarded job opportunities
"""

import re

from bs4 import BeautifulSoup


def parse_recruiter_email(html_content: str) -> list[dict[str, str]]:
    """
    Parse recruiter and LinkedIn job emails
    """
    soup = BeautifulSoup(html_content, "html.parser")
    jobs: list[dict[str, str]] = []

    # Try LinkedIn format first - look for job links
    linkedin_jobs = parse_linkedin_jobs(soup)
    if linkedin_jobs:
        return linkedin_jobs

    # Try to extract single job from recruiter email
    recruiter_job = parse_single_recruiter_job(soup)
    if recruiter_job:
        return [recruiter_job]

    return jobs


def parse_linkedin_jobs(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    Parse LinkedIn job recommendation/saved jobs emails
    """
    jobs: list[dict[str, str]] = []

    # Look for LinkedIn job links
    job_links = soup.find_all("a", href=re.compile(r"linkedin\.com/.*jobs/view/\d+"))

    for link in job_links:
        try:
            # Extract URL
            url = link.get("href", "")

            # Clean LinkedIn tracking parameters
            if "trackingId=" in url:
                url = url.split("?")[0]

            # Extract job ID from URL
            job_id_match = re.search(r"/jobs/view/(\d+)", url)
            if not job_id_match:
                continue

            # Build clean URL
            job_id = job_id_match.group(1)
            clean_url = f"https://www.linkedin.com/jobs/view/{job_id}"

            # Find job title - usually in the link text or nearby
            title = link.get_text(strip=True)

            # Skip generic link text
            if title in ["View on LinkedIn", "Apply", "Learn more", "View job"]:
                title = ""

            # If link text is not the title, search nearby
            if not title or len(title) < 3:
                # Look for title in parent structure
                parent = link.find_parent("td") or link.find_parent("div")
                if parent:
                    # Look for styled text that looks like a title
                    title_elem = parent.find(
                        ["a", "span", "p"], style=re.compile(r"font-size:\s*1[6-8]px")
                    )
                    if title_elem:
                        title = title_elem.get_text(strip=True)

            # Find company and location
            company = "Unknown Company"
            location = "Unknown Location"

            # Look for company logo and info nearby - search more thoroughly
            parent_container = link.find_parent(["td", "div", "table"])
            if parent_container:
                # Strategy 1: Company often in text with middot separator
                company_text = parent_container.find(text=re.compile(r"·"))
                if company_text:
                    parts = company_text.split("·")
                    if len(parts) >= 2:
                        company = parts[0].strip()
                        location = parts[1].strip()

                # Strategy 2: Look for company in alt text of images
                if company == "Unknown Company":
                    img = parent_container.find("img", alt=True)
                    if img and img["alt"] and img["alt"] != title:
                        company = img["alt"]

                # Strategy 3: Search in all text nodes near the link
                if company == "Unknown Company":
                    # Get all text from parent, split by newlines
                    all_text = parent_container.get_text(separator="\n", strip=True)
                    lines = [line.strip() for line in all_text.split("\n") if line.strip()]

                    # Look for line with middot that might be company·location
                    for line in lines:
                        if "·" in line:
                            parts = line.split("·")
                            # First part before · is often company
                            if len(parts) >= 1 and parts[0].strip() and parts[0].strip() != title:
                                company = parts[0].strip()
                                if len(parts) >= 2:
                                    location = parts[1].strip()
                                break

            # Skip if we don't have essential information
            if not title or title == company or len(title) < 3:
                continue

            jobs.append(
                {"title": title, "company": company, "location": location, "link": clean_url}
            )

        except Exception as e:
            print(f"Error parsing LinkedIn job: {e}")
            continue

    # Deduplicate jobs by link (in case email has multiple links to same job)
    unique_jobs = {}
    for job in jobs:
        link = job["link"]
        # Keep the job with more complete information (prefer ones with real company names)
        if link not in unique_jobs:
            unique_jobs[link] = job
        else:
            # If we already have this link, keep the one with more complete title
            if len(job["title"]) > len(unique_jobs[link]["title"]):
                unique_jobs[link] = job

    return list(unique_jobs.values())


def parse_single_recruiter_job(soup: BeautifulSoup) -> dict[str, str] | None:
    """
    Parse a single job from a recruiter outreach email
    """
    # Common patterns in recruiter emails
    title_patterns = [
        r"(?:position|role|opportunity|opening|job)[\s:]+(?:for\s+)?(?:a\s+)?(?:an\s+)?([^\.\n]+?)(?:\s+role|\s+position|\s+at\s+)",
        r"(?:hiring|seeking|looking for)[\s:]+(?:a\s+)?(?:an\s+)?([^\.\n]+?)(?:\s+at\s+)",
        r'apply\s+(?:now\s+)?to\s+["\']?([^"\']+)["\']?',
        r'fit\s+for\s+.*?["\']([^"\']+)["\']',
    ]

    title = None
    company = None
    location = None
    link = None

    # Extract text content
    text = soup.get_text()

    # Try to find job title
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the last captured group (varies by pattern)
            title = match.groups()[-1].strip() if match.groups() else match.group(0).strip()
            # Clean up title - use non-greedy matching to prevent ReDoS
            title = re.sub(r" at .*", "", title)  # Remove "at Company" part
            title = re.sub(r" role.*", "", title, flags=re.IGNORECASE)
            break

    # Find company name - often after "at" or in email context
    # Match company name including multi-word names and endings like "Inc."
    company_match = re.search(r"at\s+([A-Z][^,\n\.]+)(?:\.|\s*$|\s*\n)", text)
    if company_match:
        company = company_match.group(1).strip()
        # Check if the next character is a period (for Inc. etc)
        match_end = company_match.end(1)
        if (
            match_end < len(text)
            and text[match_end] == "."
            and re.search(r"\b(?:Inc|LLC|Ltd|Corp|Co)$", company)
        ):
            company = company + "."

    # Find location - look for common location patterns
    location_patterns = [
        r"Location:\s*([^\n]+)",  # Explicit "Location:" label
        r"([A-Z][^,\n]+,\s*[A-Z]{2}\s*\([^)]+\))",  # City, ST (Type)
        r"([A-Z][^,]+,\s*[A-Z]{2})",  # City, ST
        r"(Remote|Hybrid|On-site)(?!\))",  # Work type when not in parentheses
        r"([A-Z][^,]+,\s*[^,]+,\s*(?:United States|Canada|USA))",
    ]

    for pattern in location_patterns:
        loc_match = re.search(pattern, text)
        if loc_match:
            location = loc_match.group(1).strip()
            break

    # Find apply link
    apply_link = soup.find("a", text=re.compile(r"apply|view|learn more", re.IGNORECASE))
    if apply_link and hasattr(apply_link, "get"):
        link = apply_link.get("href", "")
    else:
        # Look for any LinkedIn job link
        linkedin_link = soup.find("a", href=re.compile(r"linkedin\.com.*job"))
        if linkedin_link and hasattr(linkedin_link, "get"):
            link = linkedin_link.get("href", "")

    # Clean up link
    if link and isinstance(link, str) and "?" in link:
        # Remove tracking parameters
        link = link.split("?")[0]

    # Only return if we have at least a title and some other info
    if title and (company or location or link):
        return {
            "title": title,
            "company": company or "Unknown Company",
            "location": location or "Unknown Location",
            "link": str(link) if link else "",
        }

    return None


def can_parse(from_addr: str, subject: str) -> bool:
    """
    Check if this parser can handle the email
    """
    from_lower = from_addr.lower()
    subject_lower = subject.lower()

    # LinkedIn emails
    if "linkedin" in from_lower:
        return True

    # Common recruiter patterns in subject
    recruiter_keywords = [
        "apply to",
        "apply now",
        "you may be a fit",
        "great fit",
        "opportunity",
        "opening",
        "hiring",
        "seeking",
        "looking for",
        "saved job",
        "job match",
        "position at",
        "role at",
    ]

    for keyword in recruiter_keywords:
        if keyword in subject_lower:
            return True

    # Forwarded job emails
    return subject_lower.startswith("fwd:") and any(
        kw in subject_lower for kw in ["job", "role", "position"]
    )
