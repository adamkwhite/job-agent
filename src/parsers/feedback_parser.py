"""
Email parser for job digest feedback

Detects replies to job digest emails and extracts user feedback
for automatic GitHub issue creation.

Note: This parser is different from job parsers - it doesn't inherit
from BaseEmailParser because it returns feedback data, not job opportunities.
"""

import logging
import re
from email.message import Message

logger = logging.getLogger(__name__)


class FeedbackParser:
    """Parse replies to job digest emails for feedback"""

    def __init__(self):
        self.name = "feedback"

    def can_parse(self, msg: Message, _from_addr: str, subject: str) -> bool:
        """
        Detect if email is a reply to a job digest

        Checks for:
        - In-Reply-To header (Gmail threading)
        - Subject line containing "Re:" or "Fwd:"
        - Subject containing digest keywords
        """
        subject_lower = subject.lower()

        # Check if it's a reply (Re:) or forward (Fwd:)
        if not any(kw in subject_lower for kw in ["re:", "fwd:", "fw:"]):
            return False

        # Check if subject mentions job matches/digest
        digest_keywords = [
            "job matches",
            "job match",
            "excellent job",
            "good job",
            "digest",
        ]

        if not any(kw in subject_lower for kw in digest_keywords):
            return False

        # Check for In-Reply-To header (stronger signal)
        in_reply_to = msg.get("In-Reply-To", "")
        if in_reply_to:
            logger.info(f"Found digest reply with In-Reply-To: {in_reply_to}")
            return True

        # Subject suggests it's a reply to digest
        logger.info(f"Found potential digest reply from subject: {subject}")
        return True

    def parse(self, msg: Message, from_addr: str, subject: str) -> list[dict]:
        """
        Parse feedback from digest reply

        Returns feedback as dict with:
        - type: "feedback"
        - user_email: Email address of sender
        - feedback_text: User's feedback text
        - job_references: List of jobs mentioned (if any)
        - original_subject: Subject line
        """
        logger.info(f"Parsing feedback from: {from_addr}")

        # Get email body
        body = self._get_email_body(msg)
        if not body:
            logger.warning("No email body found")
            return []

        # Clean body (remove quoted text, signatures)
        clean_body = self._clean_feedback_body(body)

        if not clean_body or len(clean_body.strip()) < 10:
            logger.info("Feedback too short or empty after cleaning")
            return []

        # Extract job references from feedback
        job_refs = self._extract_job_references(clean_body)

        feedback = {
            "type": "feedback",
            "user_email": from_addr,
            "feedback_text": clean_body,
            "job_references": job_refs,
            "original_subject": subject,
            "source": "digest_reply",
        }

        logger.info(f"Parsed feedback: {len(clean_body)} chars, {len(job_refs)} job refs")

        return [feedback]

    def _get_email_body(self, msg: Message) -> str:
        """Extract plain text body from email"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload and isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                return payload.decode("utf-8", errors="ignore")
        return ""

    def _clean_feedback_body(self, body: str) -> str:
        """
        Clean feedback text by removing:
        - Quoted original email (lines starting with >)
        - Email signatures
        - Gmail metadata (On ... wrote:)
        - Extra whitespace

        Returns only the user's new feedback text
        """
        lines = body.split("\n")
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Stop at quoted text markers
            if line_stripped.startswith(">"):
                break

            # Stop at Gmail metadata
            if re.match(r"On .+wrote:", line_stripped):
                break

            # Stop at signature markers
            if line_stripped in ["--", "___", "Thanks", "Best", "Regards"]:
                break

            # Skip very short lines (likely formatting)
            if len(line_stripped) > 3:
                cleaned_lines.append(line_stripped)

        cleaned_text = "\n".join(cleaned_lines).strip()
        return cleaned_text

    def _extract_job_references(self, text: str) -> list[dict]:
        """
        Extract job references from feedback text

        Looks for patterns like:
        - Job title mentions ("Director of Engineering at Relay")
        - Company names
        - LinkedIn URLs
        - Score mentions ("85/115", "80 points")

        Returns list of potential job references with extracted info
        """
        job_refs = []

        # Pattern: "Title at Company"
        title_company_pattern = r"([A-Z][a-zA-Z\s]+(?:Director|VP|Engineer|Manager|Lead|Head)(?:[a-zA-Z\s]+)?)\s+at\s+([A-Z][a-zA-Z0-9\s&,.-]+)"
        matches = re.findall(title_company_pattern, text)
        for title, company in matches:
            job_refs.append(
                {
                    "title": title.strip(),
                    "company": company.strip(),
                    "source": "text_pattern",
                }
            )

        # Pattern: LinkedIn URLs
        linkedin_pattern = r"https?://(?:www\.)?linkedin\.com/jobs/view/(\d+)"
        matches = re.findall(linkedin_pattern, text)
        for job_id in matches:
            job_refs.append({"linkedin_job_id": job_id, "source": "linkedin_url"})

        # Pattern: Score mentions "85/115" or "80 points"
        score_pattern = r"(\d{1,3})(?:/115|\s*points?)"
        matches = re.findall(score_pattern, text)
        for score in matches:
            # Scores help identify which job, but need other context
            logger.debug(f"Found score reference: {score}")

        return job_refs
