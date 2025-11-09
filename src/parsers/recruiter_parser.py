"""
Direct recruiter and LinkedIn saved jobs email parser
Handles:
1. LinkedIn saved/recommended job emails
2. Direct recruiter outreach
3. Forwarded job opportunities
"""

import re

from bs4 import BeautifulSoup

# Constants
UNKNOWN_COMPANY = "Unknown Company"
UNKNOWN_LOCATION = "Unknown Location"


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

            # Skip search URLs - we only want actual job postings
            if "/jobs/search" in url or "keywords=" in url:
                continue

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
            full_link_text = link.get_text(strip=True)

            # Skip generic link text
            if full_link_text in ["View on LinkedIn", "Apply", "Learn more", "View job"]:
                full_link_text = ""

            # Extract clean title from link text
            # LinkedIn often concatenates: Title[Company] · [Location][Salary]...
            # Split at first middot to separate title from metadata
            title = full_link_text
            if "·" in full_link_text:
                # Everything before first middot might be title+company concatenated
                # We'll clean it further after extracting company
                title = full_link_text.split("·")[0].strip()

            # If link text is not usable, search nearby
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
                        # Clean this too
                        if "·" in title:
                            title = title.split("·")[0].strip()

            # Find company and location
            company = UNKNOWN_COMPANY
            location = UNKNOWN_LOCATION

            # Look for company logo and info nearby - search more thoroughly
            parent_container = link.find_parent(["td", "div", "table"])
            if parent_container:
                # Strategy 1: Look for company in the full link text with middot
                # Format: Title[Company] · [Location]
                if "·" in full_link_text and company == UNKNOWN_COMPANY:
                    parts = full_link_text.split("·")
                    if len(parts) >= 2:
                        # Part before first middot contains title+company
                        before_middot = parts[0].strip()
                        # Part after first middot has location
                        after_middot = parts[1].strip()

                        # Try to extract company from before_middot
                        # Company names are usually capitalized and at the end
                        # Strategy: First split any concatenated words, then find company
                        words = before_middot.split()

                        # Step 1: Check all words for concatenation and split them
                        for i in range(len(words)):
                            word = words[i]
                            # Find first capital that comes after a lowercase letter
                            concat_idx = None
                            for j in range(1, len(word)):
                                if word[j].isupper() and word[j - 1].islower():
                                    concat_idx = j
                                    break

                            if concat_idx:
                                # Split word: "ManagerCVS" → ["Manager", "CVS"]
                                words[i] = word[:concat_idx]
                                # Insert the company part after this word
                                words.insert(i + 1, word[concat_idx:])
                                break  # Only handle one concatenation

                        # Step 2: Find the company (everything after the last title keyword)
                        # Iterate backwards to find the last title keyword or role descriptor
                        title_keywords = [
                            "director",
                            "manager",
                            "senior",
                            "lead",
                            "vp",
                            "head",
                            "chief",
                            "principal",
                            "staff",
                            "software",
                            "hardware",
                            "engineering",
                            "product",
                            "technical",
                            "program",
                            "project",
                        ]
                        company_start_idx = None
                        for i in range(len(words) - 1, -1, -1):
                            word = words[i]
                            # Strip punctuation for comparison
                            word_clean = word.strip(",.;:()[]").lower()
                            # Check if this is a title keyword or role descriptor
                            if word_clean in title_keywords:
                                # Found a title keyword - company starts after this
                                company_start_idx = i + 1
                                break

                        # If we found a title keyword, everything after it is the company
                        if company_start_idx is not None and company_start_idx < len(words):
                            company = " ".join(words[company_start_idx:])
                            title = " ".join(words[:company_start_idx]).strip()
                        # Otherwise, assume last capitalized word(s) are the company
                        elif len(words) > 1 and words[-1][0].isupper():
                            # Take last word as company (or last 2 if both capitalized)
                            if (
                                len(words) > 2
                                and words[-2][0].isupper()
                                and words[-2].lower() not in ["and", "of", "the"]
                            ):
                                company = " ".join(words[-2:])
                                title = " ".join(words[:-2]).strip()
                            else:
                                company = words[-1]
                                title = " ".join(words[:-1]).strip()

                        # Extract location (before salary info)
                        # Location format: "City, STATE (Type)" or just "City, STATE"
                        location_match = re.search(
                            r"([A-Z][^$\d·]+(?:,\s*[A-Z]{2})?(?:\s*\([^)]+\))?)", after_middot
                        )
                        if location_match:
                            location = location_match.group(1).strip()

                # Strategy 2: Look for company/location in paragraph tag in sibling TR elements
                # LinkedIn emails often have structure: <tr><a>Title</a></tr><tr><p>Company · Location</p></tr>
                if company == UNKNOWN_COMPANY:
                    # Try to find parent TR
                    parent_tr = link.find_parent("tr")
                    if parent_tr:
                        # Look in next TR sibling
                        next_tr = parent_tr.find_next_sibling("tr")
                        if next_tr:
                            # Look for paragraph with middot (company · location format)
                            p_tag = next_tr.find("p", string=re.compile(r"·"))
                            if p_tag:
                                p_text = p_tag.get_text(strip=True)
                                if "·" in p_text:
                                    parts = p_text.split("·")
                                    if len(parts) >= 2:
                                        company = parts[0].strip()
                                        location = parts[1].strip()

                # Strategy 3: Company often in text with middot separator (legacy)
                if company == UNKNOWN_COMPANY:
                    company_text = parent_container.find(text=re.compile(r"·"))
                    if company_text:
                        parts = company_text.split("·")
                        if len(parts) >= 2:
                            potential_company = parts[0].strip()
                            # Only use if it's not the full concatenated title
                            if potential_company != full_link_text.split("·")[0].strip():
                                company = potential_company
                                location = parts[1].strip()

                # Strategy 4: Look for company in alt text of images
                if company == UNKNOWN_COMPANY:
                    img = parent_container.find("img", alt=True)
                    if img and img["alt"] and img["alt"] != title:
                        company = img["alt"]

                # Strategy 5: Search in all text nodes near the link
                if company == UNKNOWN_COMPANY:
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

            # Final title cleanup: remove company name if it's still in title
            if company != UNKNOWN_COMPANY and company in title:
                title = title.replace(company, "").strip()

            # Clean up location: remove salary and extra metadata
            if location != UNKNOWN_LOCATION:
                # Remove everything after closing parenthesis (salary, connections, etc.)
                if ")" in location:
                    location = location[: location.rfind(")") + 1]
                # Remove dollar amounts - find $ position and slice (no regex needed)
                dollar_pos = location.find("$")
                if dollar_pos != -1:
                    location = location[:dollar_pos].strip()
                # Remove connection counts - find "connection" substring (no regex needed)
                location_lower = location.lower()
                conn_pos = location_lower.find(" connection")
                if conn_pos != -1:
                    location = location[:conn_pos].strip()

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

    # Reject search URLs - we only want actual job postings
    if link and isinstance(link, str) and ("/jobs/search" in link or "keywords=" in link):
        link = ""

    # Clean up link
    if link and isinstance(link, str) and "?" in link:
        # Remove tracking parameters
        link = link.split("?")[0]

    # Only return if we have at least a title and some other info
    if title and (company or location or link):
        return {
            "title": title,
            "company": company or UNKNOWN_COMPANY,
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
