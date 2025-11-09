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
            # Extract URL first
            url = link.get("href", "")
            if not url.startswith("http"):
                url = f"https://{url}"

            # STRATEGY: Work in Tech emails have two patterns:
            # 1. Link text contains actual job title (use link text)
            # 2. Link text is generic ("make a new search") - extract from nearby middot text

            title = None
            company = "Unknown Company"
            location = "Unknown Location"

            # First, try to get title from link/span (most common case)
            title_span = link.find("span", style=re.compile(r"font-size:\s*16px"))
            link_text = title_span.get_text(strip=True) if title_span else link.get_text(strip=True)

            # Skip obviously generic/navigation links (but not "make a new search" - that's valid for old format)
            if link_text.lower() in [
                "see more jobs",
                "this link",
                "unsubscribe",
                "getro",
                "learning center",
                "update preferences",
            ]:
                continue

            # Skip links without title_span that are part of a 3-row table (company/location links in rows 2/3)
            # These emails have structure: Row 1 (title with span) -> Row 2 (company link) -> Row 3 (location link)
            if not title_span:
                # Check if this link is in a 3-row table structure
                parent_table = link.find_parent("table")
                if parent_table:
                    rows = parent_table.find_all("tr", recursive=False)
                    if len(rows) == 3:
                        # This is a company/location link in a 3-row table, skip it
                        continue

            # STRATEGY 1: Table-based structure (newer format)
            # Structure: <table><tr><td>Title</td></tr><tr><td>Company</td></tr><tr><td>Location</td></tr></table>
            # This is the primary pattern - if we find it, use it and skip other strategies
            extracted_from_table = False
            if title_span:
                # Find the parent table containing the 3-row structure
                parent_table = title_span.find_parent("table")
                if parent_table:
                    rows = parent_table.find_all("tr", recursive=False)
                    if len(rows) == 3:
                        # Row 1: Title
                        title = title_span.get_text(strip=True)

                        # Row 2: Company
                        company_cell = rows[1].find("td")
                        if company_cell:
                            company_text = company_cell.get_text(strip=True)
                            if company_text and len(company_text) > 0:
                                company = company_text

                        # Row 3: Location
                        location_cell = rows[2].find("td")
                        if location_cell:
                            location_text = location_cell.get_text(strip=True)
                            if location_text and len(location_text) > 0:
                                location = location_text

                        # Mark that we successfully extracted from table
                        extracted_from_table = True

            # If we successfully extracted from table, skip the fallback strategies
            if extracted_from_table:
                # Skip to validation
                pass
            else:
                # STRATEGY 2: Fallback for older email formats with middot-separated text
                # Check if link text is generic/useless
                is_generic_link_text = (
                    not link_text
                    or len(link_text) < 5
                    or link_text.lower() in ["make a new search", "see more jobs", "this link"]
                )

                # If link text is good, use it as title
                if not is_generic_link_text:
                    title = link_text

            # Look in parent container for additional details or alternative title (only for fallback)
            if not extracted_from_table:
                parent_container = link.find_parent(["td", "table", "div"])

                # Only proceed with parent container extraction if we found one
                # (If we have a valid title from link text but no parent, that's OK)
                if parent_container:
                    # Company often in image alt attribute
                    img = parent_container.find("img", alt=True)
                    if img and "Logo" in img.get("alt", ""):
                        company = img["alt"].replace(" Logo", "").strip()

                    # Look for job details in div/span elements with middot separator
                    # Pattern: "Job Title · Location" or "Company · Location" or "Job Title · Company · Location"
                    for elem in parent_container.find_all(["div", "span", "p"]):
                        elem_text = elem.get_text(strip=True)

                        # Skip if this is the link text itself
                        if elem == link or elem_text == link_text:
                            continue

                        # Extract from middot-separated text
                        if "·" in elem_text:
                            parts = elem_text.split("·")
                            if len(parts) >= 2:
                                first_part = parts[0].strip()
                                last_part = parts[-1].strip()

                                # If we don't have a title yet (generic link text), extract from middot
                                if not title and first_part and len(first_part) > 5:
                                    # Check if first part looks like a job title (has job keywords)
                                    title_keywords = [
                                        "director",
                                        "manager",
                                        "engineer",
                                        "senior",
                                        "lead",
                                        "head",
                                        "vp",
                                        "vice president",
                                        "specialist",
                                    ]
                                    has_title_keyword = any(
                                        keyword in first_part.lower() for keyword in title_keywords
                                    )

                                    if has_title_keyword:
                                        # First part is likely the job title
                                        title = first_part
                                        # If 3 parts: Title · Company · Location
                                        if len(parts) == 3:
                                            company = parts[1].strip()
                                            location = last_part
                                        else:
                                            # 2 parts: Title · Location
                                            location = last_part
                                    else:
                                        # First part is likely company name, not job title
                                        if company == "Unknown Company":
                                            company = first_part
                                        location = last_part
                                else:
                                    # We already have a title from link text
                                    # Middot text is probably "Company · Location"
                                    if company == "Unknown Company":
                                        company = first_part
                                    location = last_part

                                break

            # Skip if not a valid job title
            if not title or len(title) < 5:
                continue
            if title.lower() in [
                "see more jobs",
                "this link",
                "work in tech",
                "update your preferences",
                "make a new search",
            ]:
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
