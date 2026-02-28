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
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel words that terminate a company name in feedback text
_STOP_WORDS = {"is", "are", "job", "and", "the"}

# Pattern: "Title at Company" — extracted to reduce in-function complexity
# Title must contain a leadership keyword; company stops at sentence words
_TITLE_RE = re.compile(
    r"(?:(?:the|both)\s)?"
    r"([A-Z][A-Z ]+(?:Director|VP|Engineer|Manager|Lead|Head)[A-Z ]*)"
    r"\sat\s",
    re.IGNORECASE,
)


def _extract_company(text: str) -> str | None:
    """Extract company name from text after 'at', stopping at stop words."""
    words: list[str] = []
    for word in text.split():
        if word.lower().rstrip(".,;") in _STOP_WORDS or word[0] in ".,;":
            break
        words.append(word.rstrip(".,;"))
    return " ".join(words) if words else None


_REPLY_KEYWORDS = ("re:", "fwd:", "fw:")
_DIGEST_KEYWORDS = (
    "job matches",
    "job match",
    "excellent job",
    "good job",
    "digest",
)


class FeedbackParser(object):  # noqa: UP004 (explicit object for SonarLint S1722 compatibility)
    """Parse replies to job digest emails for feedback"""

    def __init__(self) -> None:
        self.name = "feedback"

    @staticmethod
    def can_parse(msg: Message, _from_addr: str, subject: str) -> bool:
        """
        Detect if email is a reply to a job digest

        Checks for:
        - In-Reply-To header (Gmail threading)
        - Subject line containing "Re:" or "Fwd:"
        - Subject containing digest keywords
        """
        subject_lower = subject.lower()

        # Must be a reply/forward that mentions digest keywords
        if not any(kw in subject_lower for kw in _REPLY_KEYWORDS):
            return False
        if not any(kw in subject_lower for kw in _DIGEST_KEYWORDS):
            return False

        # Log which signal matched
        in_reply_to = msg.get("In-Reply-To", "")
        if in_reply_to:
            logger.info(f"Found digest reply with In-Reply-To: {in_reply_to}")
        else:
            logger.info(f"Found potential digest reply from subject: {subject}")
        return True

    def parse(self, msg: Message, from_addr: str, subject: str) -> list[dict[str, Any]]:
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

    @staticmethod
    def _get_email_body(msg: Message) -> str:
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

    @staticmethod
    def _clean_feedback_body(body: str) -> str:
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

    @staticmethod
    def _extract_job_references(text: str) -> list[dict[str, Any]]:
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

        for m in _TITLE_RE.finditer(text):
            title = m.group(1).strip()
            company = _extract_company(text[m.end() :])
            if company:
                job_refs.append(
                    {
                        "title": title,
                        "company": company,
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
