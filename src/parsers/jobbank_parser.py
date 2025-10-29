"""
Job Bank Canada job alert email parser
Handles Canadian government job bank notifications
"""

from bs4 import BeautifulSoup


def parse_jobbank_email(html_content: str) -> list[dict[str, str]]:
    """
    Parse Job Bank Canada job alert emails

    Email format:
    - From: Job Alerts by Job Bank <no-reply-jobalert@hrsdc-rhdcc.gc.ca>
    - Subject: X new jobs - [Job type] in various locations
    """
    soup = BeautifulSoup(html_content, "html.parser")
    jobs = []

    # Find job listings - they're in tables with class "resultJobItem"
    job_links = soup.find_all("a", class_="resultJobItem")

    for job_link in job_links:
        try:
            # Extract title from link text
            title = job_link.get_text(strip=True)
            if not title:
                continue

            # Extract URL
            url = str(job_link.get("href", ""))
            if url and not url.startswith("http"):
                url = f"https://www.jobbank.gc.ca{url}"

            # Clean URL - remove tracking parameters
            if "?" in url:
                url = url.split("?")[0]

            # Find the company name - it's in the next row
            parent_container = job_link.find_parent("td")
            if parent_container:
                # Navigate to find company row
                company_row = parent_container.find_parent("tr")
                if company_row:
                    next_row = company_row.find_next_sibling("tr")
                    if next_row:
                        company_td = next_row.find("td")
                        if company_td:
                            company = company_td.get_text(strip=True)
                        else:
                            company = "Unknown Company"
                    else:
                        company = "Unknown Company"
                else:
                    company = "Unknown Company"
            else:
                company = "Unknown Company"

            # Find location - usually in the third row
            location = "Canada"
            if parent_container:
                container_row = parent_container.find_parent("tr")
                if container_row:
                    # Skip one row (company) and get the next
                    next_row = container_row.find_next_sibling("tr")
                    if next_row:
                        location_row = next_row.find_next_sibling("tr")
                        if location_row:
                            location_td = location_row.find("td")
                            if location_td:
                                location_text = location_td.get_text(strip=True)
                                # Extract location from format like "Ville de Québec, QC"
                                if location_text:
                                    location = location_text

            # Skip if no URL
            if not url:
                continue

            jobs.append({"title": title, "company": company, "location": location, "link": url})

        except Exception as e:
            print(f"Error parsing Job Bank job: {e}")
            continue

    return jobs


def can_parse(from_addr: str, subject: str) -> bool:
    """
    Check if this parser can handle the email
    """
    # Job Bank Canada emails
    if "jobalert@hrsdc-rhdcc.gc.ca" in from_addr.lower():
        return True
    if "job bank" in from_addr.lower():
        return True
    # Subject patterns like "3 new jobs - Mechanical engineers in various locations"
    # Use string matching instead of regex to avoid ReDoS vulnerability
    subject_lower = subject.lower()
    return " new job -" in subject_lower or " new jobs -" in subject_lower
