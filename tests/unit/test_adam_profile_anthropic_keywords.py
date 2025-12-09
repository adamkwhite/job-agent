"""
Unit tests for Adam's profile Anthropic/Claude keyword additions

Tests that Adam's profile correctly scores developer tools and AI company jobs
after adding "anthropic", "claude", "developer tools", "ide" keywords.

Use Case: "Product Manager, Claude Code" @ Anthropic should score B grade (80+)
for Adam, not C grade (67).
"""

import pytest

from agents.profile_scorer import ProfileScorer
from utils.profile_manager import get_profile_manager


@pytest.fixture
def adam_profile():
    """Get Adam's actual profile from profile manager"""
    pm = get_profile_manager()
    profile = pm.get_profile("adam")
    if not profile:
        pytest.skip("Adam's profile not found")
    return profile


class TestAnthropicClaudeKeywords:
    """Test that Adam's profile recognizes Anthropic/Claude opportunities"""

    def test_anthropic_keyword_in_domain_keywords(self, adam_profile):
        """Verify 'anthropic' is in Adam's domain keywords"""
        domain_keywords = adam_profile.get_domain_keywords()
        assert "anthropic" in domain_keywords, (
            "Adam's profile should include 'anthropic' in domain_keywords"
        )

    def test_claude_keyword_in_domain_keywords(self, adam_profile):
        """Verify 'claude' is in Adam's domain keywords"""
        domain_keywords = adam_profile.get_domain_keywords()
        assert "claude" in domain_keywords, (
            "Adam's profile should include 'claude' in domain_keywords"
        )

    def test_developer_tools_keyword_in_domain_keywords(self, adam_profile):
        """Verify 'developer tools' is in Adam's domain keywords"""
        domain_keywords = adam_profile.get_domain_keywords()
        assert "developer tools" in domain_keywords, (
            "Adam's profile should include 'developer tools' in domain_keywords"
        )

    def test_ide_keyword_in_domain_keywords(self, adam_profile):
        """Verify 'ide' is in Adam's domain keywords"""
        domain_keywords = adam_profile.get_domain_keywords()
        assert "ide" in domain_keywords, "Adam's profile should include 'ide' in domain_keywords"


class TestAnthropicJobScoring:
    """Test actual job scoring for Anthropic positions"""

    def test_product_manager_claude_code_scores_b_grade(self, adam_profile):
        """Product Manager, Claude Code @ Anthropic should score B grade (80+)"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Product Manager, Claude Code",
            "company": "Anthropic",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Should score B grade (80+) for Adam
        assert score >= 80, (
            f"Product Manager, Claude Code @ Anthropic should score at least 80 for Adam, "
            f"got {score}/115 ({grade})"
        )
        assert grade == "B", f"Expected B grade, got {grade}"

        # Domain should score 25 (3+ keyword matches: product, anthropic, claude)
        assert breakdown["domain"] >= 20, (
            f"Domain should score at least 20 with anthropic/claude keywords, "
            f"got {breakdown['domain']}"
        )

    def test_domain_scoring_with_anthropic_claude(self, adam_profile):
        """Test domain scoring recognizes anthropic and claude keywords"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Product Manager, Claude Code",
            "company": "Anthropic",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # With "product", "anthropic", "claude" matches = 3+ matches = 25 points
        assert breakdown["domain"] == 25, (
            f"Domain should score 25 with 3+ keyword matches (product, anthropic, claude), "
            f"got {breakdown['domain']}"
        )

    def test_technical_scoring_with_anthropic_claude(self, adam_profile):
        """Test technical scoring counts anthropic/claude matches"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Product Manager, Claude Code",
            "company": "Anthropic",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Technical should score at least 4 (2 points per match, min 2 matches)
        assert breakdown["technical"] >= 4, (
            f"Technical should score at least 4 with anthropic/claude/product keywords, "
            f"got {breakdown['technical']}"
        )

    def test_senior_pm_claude_code_scores_higher(self, adam_profile):
        """Senior Product Manager, Claude Code should score even higher"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Senior Product Manager, Claude Code",
            "company": "Anthropic",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Should score B+ grade (85+) with senior keyword
        assert score >= 85, (
            f"Senior PM, Claude Code @ Anthropic should score at least 85 for Adam, "
            f"got {score}/115 ({grade})"
        )

        # Seniority should be 15 (senior-level)
        assert breakdown["seniority"] == 15, (
            f"Senior PM should get 15 seniority points, got {breakdown['seniority']}"
        )


class TestDeveloperToolsScoring:
    """Test scoring for developer tools companies"""

    def test_ide_company_job_scoring(self, adam_profile):
        """Jobs at IDE/developer tools companies should score higher"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Product Manager, Developer Tools",
            "company": "JetBrains",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Should recognize "developer tools" keyword
        assert breakdown["domain"] >= 20, (
            f"Developer tools job should score at least 20 in domain, got {breakdown['domain']}"
        )

    def test_ide_in_title_boosts_score(self, adam_profile):
        """IDE keyword in title should boost domain score"""
        scorer = ProfileScorer(adam_profile)
        job = {
            "title": "Product Manager, IDE Platform",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Should recognize "ide" keyword
        assert breakdown["domain"] >= 15, (
            f"IDE platform job should score at least 15 in domain, got {breakdown['domain']}"
        )


class TestRegressionPrevention:
    """Prevent regression - ensure keywords remain in profile"""

    def test_all_new_keywords_present(self, adam_profile):
        """Ensure all 4 new keywords are in Adam's profile"""
        domain_keywords = adam_profile.get_domain_keywords()

        new_keywords = ["anthropic", "claude", "developer tools", "ide"]
        missing_keywords = [kw for kw in new_keywords if kw not in domain_keywords]

        assert not missing_keywords, (
            f"Adam's profile is missing these keywords: {missing_keywords}. "
            f"These should be in domain_keywords."
        )

    def test_original_keywords_still_present(self, adam_profile):
        """Ensure original keywords weren't accidentally removed"""
        domain_keywords = adam_profile.get_domain_keywords()

        # Sample of important original keywords
        important_keywords = [
            "software",
            "product",
            "ai",
            "machine learning",
            "product management",
        ]
        missing_keywords = [kw for kw in important_keywords if kw not in domain_keywords]

        assert not missing_keywords, (
            f"Adam's profile is missing original keywords: {missing_keywords}"
        )
