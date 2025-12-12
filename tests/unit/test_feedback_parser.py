"""
Unit tests for feedback email parser

Tests detection and parsing of replies to job digest emails.
Addresses Issue #133 - Email feedback automation
"""

import sys
from email.message import EmailMessage
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from parsers.feedback_parser import FeedbackParser


class TestFeedbackParser:
    """Test feedback email detection and parsing"""

    def _create_test_email(
        self,
        subject: str,
        body: str,
        from_addr: str = "wes@example.com",
        in_reply_to: str = "",
    ) -> EmailMessage:
        """Create a test email message"""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        msg.set_content(body)
        return msg

    def test_can_parse_detects_digest_reply_with_re(self):
        """Test that parser detects replies (Re:) to digest emails"""
        parser = FeedbackParser()

        msg = self._create_test_email(
            subject="Re: 2 Excellent Job Matches for You - 2025-12-08",
            body="This job is US only",
        )

        assert parser.can_parse(msg, "wes@example.com", msg["Subject"]), (
            "Should detect Re: digest emails"
        )

    def test_can_parse_detects_forward(self):
        """Test that parser detects forwards (Fwd:) of digest emails"""
        parser = FeedbackParser()

        msg = self._create_test_email(
            subject="Fwd: 5 Good Job Matches for You",
            body="Forwarding this job alert",
        )

        assert parser.can_parse(msg, "adam@example.com", msg["Subject"]), (
            "Should detect Fwd: digest emails"
        )

    def test_can_parse_requires_digest_keywords(self):
        """Test that parser requires digest-related keywords"""
        parser = FeedbackParser()

        # Reply but not to digest
        msg = self._create_test_email(subject="Re: Meeting tomorrow", body="Sounds good")

        assert not parser.can_parse(msg, "wes@example.com", msg["Subject"]), (
            "Should NOT detect non-digest replies"
        )

    def test_can_parse_checks_in_reply_to_header(self):
        """Test that In-Reply-To header strengthens detection"""
        parser = FeedbackParser()

        msg = self._create_test_email(
            subject="Re: Job Matches",
            body="Feedback here",
            in_reply_to="<message-id@gmail.com>",
        )

        assert parser.can_parse(msg, "eli@example.com", msg["Subject"]), (
            "Should detect with In-Reply-To header"
        )

    def test_parse_extracts_feedback_text(self):
        """Test that parser extracts user feedback text"""
        parser = FeedbackParser()

        msg = self._create_test_email(
            subject="Re: 2 Excellent Job Matches",
            body="This job is actually U.S. only. Should have been filtered.",
        )

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        assert len(feedbacks) == 1
        feedback = feedbacks[0]
        assert feedback["type"] == "feedback"
        assert feedback["user_email"] == "wes@example.com"
        assert "U.S. only" in feedback["feedback_text"]

    def test_parse_cleans_quoted_text(self):
        """Test that parser removes quoted original email"""
        parser = FeedbackParser()

        body = """This job is US only.

> On Dec 8, 2025, at 9:00 AM, adamwhite.jobalerts@gmail.com wrote:
>
> Director of Engineering at Relay
> Score: 85/115
"""

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        feedback = feedbacks[0]
        # Should only have "This job is US only", not the quoted text
        assert "On Dec 8" not in feedback["feedback_text"]
        assert "wrote:" not in feedback["feedback_text"]
        assert "This job is US only" in feedback["feedback_text"]

    def test_parse_removes_signatures(self):
        """Test that parser removes email signatures"""
        parser = FeedbackParser()

        body = """This score seems too high.

--
Best regards,
Wesley van Ooyen
"""

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        feedback = feedbacks[0]
        # Should not include signature
        assert "Best regards" not in feedback["feedback_text"]
        assert "Wesley van Ooyen" not in feedback["feedback_text"]
        assert "This score seems too high" in feedback["feedback_text"]

    def test_parse_extracts_job_title_and_company(self):
        """Test extraction of job references from feedback"""
        parser = FeedbackParser()

        body = "The Director of Engineering at Relay job is US only."

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "adam@example.com", msg["Subject"])

        feedback = feedbacks[0]
        job_refs = feedback["job_references"]

        assert len(job_refs) > 0, "Should extract job reference"
        assert "Director of Engineering" in job_refs[0]["title"]
        assert job_refs[0]["company"] == "Relay"

    def test_parse_extracts_linkedin_url(self):
        """Test extraction of LinkedIn job URLs"""
        parser = FeedbackParser()

        body = "This job https://www.linkedin.com/jobs/view/1234567890 is wrong."

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        feedback = feedbacks[0]
        job_refs = feedback["job_references"]

        assert len(job_refs) > 0
        assert job_refs[0]["linkedin_job_id"] == "1234567890"

    def test_parse_skips_very_short_feedback(self):
        """Test that very short feedback is ignored"""
        parser = FeedbackParser()

        msg = self._create_test_email(subject="Re: Job Matches", body="Ok")

        feedbacks = parser.parse(msg, "eli@example.com", msg["Subject"])

        assert len(feedbacks) == 0, "Should skip very short feedback"

    def test_parse_skips_empty_feedback(self):
        """Test that empty feedback after cleaning is ignored"""
        parser = FeedbackParser()

        body = """
> On Dec 8 wrote:
> Director of Engineering
"""

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "adam@example.com", msg["Subject"])

        assert len(feedbacks) == 0, "Should skip feedback with only quoted text"

    def test_parse_handles_multiple_job_references(self):
        """Test parsing feedback mentioning multiple jobs"""
        parser = FeedbackParser()

        body = """Both the VP of Engineering at Boston Dynamics and
the Director of Product at Tesla are US only."""

        msg = self._create_test_email(subject="Re: Job Matches", body=body)

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        feedback = feedbacks[0]
        job_refs = feedback["job_references"]

        assert len(job_refs) >= 2, "Should extract multiple job references"
        # Check we got both companies
        companies = [ref.get("company") for ref in job_refs]
        assert "Boston Dynamics" in companies
        assert "Tesla" in companies

    def test_parse_preserves_original_subject(self):
        """Test that original subject is preserved in feedback"""
        parser = FeedbackParser()

        subject = "Re: 5 Excellent Job Matches for You - 2025-12-08"
        msg = self._create_test_email(subject=subject, body="Good matches!")

        feedbacks = parser.parse(msg, "adam@example.com", subject)

        feedback = feedbacks[0]
        assert feedback["original_subject"] == subject

    def test_clean_feedback_body_removes_gmail_metadata(self):
        """Test removal of Gmail 'On ... wrote:' metadata"""
        parser = FeedbackParser()

        body = """This is my feedback.

On Mon, Dec 8, 2025 at 9:00 AM <noreply@example.com> wrote:
Previous email content here
"""

        msg = self._create_test_email(subject="Re: Jobs", body=body)

        feedbacks = parser.parse(msg, "wes@example.com", msg["Subject"])

        feedback = feedbacks[0]
        assert "On Mon" not in feedback["feedback_text"]
        assert "wrote:" not in feedback["feedback_text"]
        assert "This is my feedback" in feedback["feedback_text"]
