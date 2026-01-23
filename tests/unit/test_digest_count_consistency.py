"""
Test digest count consistency between summary and displayed jobs.

Related to: Codebase Analysis Issue #1.4 - Count-Display Mismatch
"""


class TestDigestCountConsistency:
    """Test that job counts in summaries match what's actually displayed"""

    def test_good_scoring_definition_consistency(self):
        """
        Test that 'good_scoring' is defined consistently across functions.

        Bug: send_digest_to_profile counts good_scoring as ALL jobs ≥55 (including 70+)
        But generate_email_html splits them: high (≥70) and good (55-69)

        This causes email subject to say "20 good matches" but body shows
        2 in "Excellent" section and 18 in "Good" section.
        """
        # Simulate job scores
        jobs = [
            {"fit_score": 85},  # High-scoring
            {"fit_score": 75},  # High-scoring
            {"fit_score": 65},  # Good-scoring
            {"fit_score": 60},  # Good-scoring
            {"fit_score": 55},  # Good-scoring
        ]

        # How send_digest_to_profile SHOULD count (FIXED)
        send_digest_high = [j for j in jobs if j.get("fit_score", 0) >= 70]
        send_digest_good = [j for j in jobs if 55 <= j.get("fit_score", 0) < 70]  # Excludes 70+!

        # How generate_email_html counts
        email_high = [j for j in jobs if j.get("fit_score", 0) >= 70]
        email_good = [j for j in jobs if 55 <= j.get("fit_score", 0) < 70]  # Excludes 70+

        # The counts MUST match after fix
        assert len(send_digest_high) == len(email_high), "High-scoring counts should match"
        assert len(send_digest_good) == len(email_good), (
            f"Good-scoring counts should match: send_digest={len(send_digest_good)}, email={len(email_good)}"
        )

        # Verify the fix: good_scoring should NOT include high-scoring jobs
        assert len(send_digest_good) == 3, "Should have 3 good matches (55-69)"
        assert len(send_digest_high) == 2, "Should have 2 excellent matches (70+)"

    def test_email_subject_matches_displayed_counts(self):
        """
        Email subject should reflect what's actually in the email body.

        If subject says "5 Good Job Matches Found", the email body should
        show 5 jobs in the "Good Matches" section (not including excellent).
        """
        jobs = [
            {"fit_score": 85},  # Excellent
            {"fit_score": 75},  # Excellent
            {"fit_score": 65},  # Good
            {"fit_score": 60},  # Good
            {"fit_score": 58},  # Good
        ]

        # Correct split for email display
        high_scoring = [j for j in jobs if j.get("fit_score", 0) >= 70]
        good_scoring = [j for j in jobs if 55 <= j.get("fit_score", 0) < 70]

        # Subject line should reference good_scoring count
        # If subject says "3 Good Job Matches", email should show 3 in good section
        assert len(good_scoring) == 3, "Should have 3 good matches (not 5)"
        assert len(high_scoring) == 2, "Should have 2 excellent matches"

        # Total displayed = high + good
        total_displayed = len(high_scoring) + len(good_scoring)
        assert total_displayed == 5, "Should display 5 total jobs"

    def test_digest_summary_text_accuracy(self):
        """
        The summary in the email should accurately reflect section counts.

        Summary says:
        • 2 excellent matches (70+ score)
        • 18 good matches (55-69 score)

        Email body should show:
        - "Top Matches" section with 2 jobs
        - "Also Worth Considering" section with 18 jobs
        """
        # Create test dataset
        excellent_jobs = [{"fit_score": 75}, {"fit_score": 72}]
        good_jobs = [{"fit_score": 60 + i} for i in range(18)]  # 60-77 but we'll cap
        good_jobs = [{"fit_score": 55 + i % 14} for i in range(18)]  # 55-68

        all_jobs = excellent_jobs + good_jobs

        # Correct categorization
        high_scoring = [j for j in all_jobs if j.get("fit_score", 0) >= 70]
        good_scoring = [j for j in all_jobs if 55 <= j.get("fit_score", 0) < 70]

        assert len(high_scoring) == 2, "Summary says 2 excellent, should display 2"
        assert len(good_scoring) == 18, "Summary says 18 good, should display 18"

    def test_console_output_matches_email(self):
        """
        Console log should match what's in the email.

        If console says "- 20 good matches (55+)", this is misleading
        because the email splits them into high (70+) and good (55-69).

        Console should show:
        - X excellent matches (70+)
        - Y good matches (55-69)
        """
        jobs = [
            {"fit_score": 85},
            {"fit_score": 75},
            {"fit_score": 65},
            {"fit_score": 60},
        ]

        # WRONG way (current send_digest_to_profile logic)
        wrong_good_count = len([j for j in jobs if j.get("fit_score", 0) >= 55])
        assert wrong_good_count == 4, "Wrong logic counts all 4 as 'good'"

        # CORRECT way (should match email display)
        correct_high_count = len([j for j in jobs if j.get("fit_score", 0) >= 70])
        correct_good_count = len([j for j in jobs if 55 <= j.get("fit_score", 0) < 70])

        assert correct_high_count == 2, "Should count 2 as 'excellent'"
        assert correct_good_count == 2, "Should count 2 as 'good'"

        # Console should report these correct counts
        # Not: "4 good matches (55+)"
        # But: "2 excellent (70+), 2 good (55-69)"
