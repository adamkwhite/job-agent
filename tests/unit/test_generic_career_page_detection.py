"""
Test generic career page detection in job validator.

Related to: Codebase Analysis Issue #1.5 - Broken Career Page Links
"""

from src.utils.job_validator import JobValidator


class TestGenericCareerPageDetection:
    """Test that validator detects generic career pages vs specific job postings"""

    def test_ashby_generic_vs_specific(self):
        """Ashby URLs: Detect generic company page vs specific job posting"""
        validator = JobValidator(check_content=False)  # Disable content checking for unit tests

        # Generic pages (should be flagged)
        generic_urls = [
            "https://jobs.ashbyhq.com/company",  # Just company
            "https://jobs.ashbyhq.com/company/",
            "https://jobs.ashbyhq.com",  # Root
        ]

        # Specific job postings (should be valid)
        specific_urls = [
            "https://jobs.ashbyhq.com/company/12345678-1234-1234-1234-123456789abc",
            "https://jobs.ashbyhq.com/roboticsco/engineering-manager",
        ]

        for url in generic_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason == "generic_career_page" and needs_review, (
                f"Should flag generic Ashby URL: {url}"
            )

        for url in specific_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason != "generic_career_page", f"Should NOT flag specific Ashby job URL: {url}"

    def test_lever_generic_vs_specific(self):
        """Lever URLs: Detect generic company page vs specific job posting"""
        validator = JobValidator(check_content=False)

        # Generic pages
        generic_urls = [
            "https://jobs.lever.co/company",
            "https://jobs.lever.co/company/",
        ]

        # Specific job postings
        specific_urls = [
            "https://jobs.lever.co/company/12345678-1234-1234-1234-123456789abc",
            "https://jobs.lever.co/figureai/director-of-engineering",
        ]

        for url in generic_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason == "generic_career_page", f"Should flag generic Lever URL: {url}"

        for url in specific_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason != "generic_career_page", f"Should NOT flag specific Lever job URL: {url}"

    def test_greenhouse_generic_vs_specific(self):
        """Greenhouse URLs: Detect generic company page vs specific job posting"""
        validator = JobValidator(check_content=False)

        # Generic pages (no /jobs/ or /job/ in URL)
        generic_urls = [
            "https://boards.greenhouse.io/company",
            "https://boards.greenhouse.io/company/",
            "https://company.greenhouse.io",
        ]

        # Specific job postings (has /jobs/ or /job/ in URL)
        specific_urls = [
            "https://boards.greenhouse.io/company/jobs/1234567",
            "https://boards.greenhouse.io/bostondynamics/job/director-of-engineering",
            "https://company.greenhouse.io/job/engineering-manager",
        ]

        for url in generic_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason == "generic_career_page", f"Should flag generic Greenhouse URL: {url}"

        for url in specific_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason != "generic_career_page", (
                f"Should NOT flag specific Greenhouse job URL: {url}"
            )

    def test_workday_generic_vs_specific(self):
        """Workday URLs: Detect generic search page vs specific job posting"""
        validator = JobValidator(check_content=False)

        # Generic pages (search or company landing)
        generic_urls = [
            "https://cisco.wd1.myworkdayjobs.com/careers",
            "https://cisco.wd1.myworkdayjobs.com/careers/",
            "https://company.wd5.myworkdayjobs.com/external",
        ]

        # Specific job postings (has /job/ with ID)
        specific_urls = [
            "https://cisco.wd1.myworkdayjobs.com/careers/job/San-Jose/Engineering-Manager_R12345",
            "https://company.wd5.myworkdayjobs.com/external/job/Boston/Director-of-Robotics_R67890",
        ]

        for url in generic_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason == "generic_career_page", (
                f"Should flag generic Workday URL: {url} (got: {reason})"
            )

        for url in specific_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason != "generic_career_page", (
                f"Should NOT flag specific Workday job URL: {url}"
            )

    def test_smartrecruiters_generic_vs_specific(self):
        """SmartRecruiters URLs: Detect generic company page vs specific job"""
        validator = JobValidator(check_content=False)

        # Generic pages
        generic_urls = [
            "https://careers.smartrecruiters.com/Company",
            "https://careers.smartrecruiters.com/Company/",
        ]

        # Specific job postings (has job ID after company)
        specific_urls = [
            "https://careers.smartrecruiters.com/Company/743999123456789-engineering-manager",
            "https://jobs.smartrecruiters.com/Company/12345-director-robotics",
        ]

        for url in generic_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason == "generic_career_page", (
                f"Should flag generic SmartRecruiters URL: {url} (got: {reason})"
            )

        for url in specific_urls:
            is_valid, reason, needs_review = validator.validate_url(url)
            assert reason != "generic_career_page", (
                f"Should NOT flag specific SmartRecruiters job URL: {url}"
            )

    def test_generic_career_paths(self):
        """Generic career paths that should be flagged regardless of platform"""
        validator = JobValidator(check_content=False)

        # These look like landing pages, not specific jobs
        generic_patterns = [
            "https://company.com/careers",
            "https://company.com/careers/",
            "https://company.com/jobs",
            "https://company.com/jobs/",
            "https://jobs.company.com",
            "https://jobs.company.com/",
            "https://careers.company.com",
            "https://careers.company.com/",
        ]

        for url in generic_patterns:
            is_valid, reason, needs_review = validator.validate_url(url)
            # These should either be flagged or at least marked for review
            assert reason == "generic_career_page" or needs_review, (
                f"Should flag or review generic career path: {url} (got: {reason}, needs_review={needs_review})"
            )

    def test_specific_job_paths_not_flagged(self):
        """Specific job paths should NOT be flagged as generic"""
        validator = JobValidator(check_content=False)

        # These clearly point to specific jobs
        specific_patterns = [
            "https://company.com/careers/engineering-manager-12345",
            "https://company.com/jobs/director-robotics",
            "https://jobs.company.com/postings/12345",
            "https://careers.company.com/role/vp-engineering",
        ]

        for url in specific_patterns:
            is_valid, reason, needs_review = validator.validate_url(url)
            # Should NOT be flagged as generic (might be valid or other status)
            assert reason != "generic_career_page", f"Should NOT flag specific job URL: {url}"

    def test_real_world_cisco_example(self):
        """
        Real-world example from Issue #197: Cisco job link goes to main careers page

        User reported: Job link for Cisco goes to https://jobs.cisco.com/ instead of
        specific job posting.
        """
        validator = JobValidator(check_content=False)

        # Generic Cisco career page (the problematic URL)
        generic_url = "https://jobs.cisco.com/"

        is_valid, reason, needs_review = validator.validate_url(generic_url)

        # Should be flagged as generic career page for manual review
        assert reason == "generic_career_page" or needs_review, (
            f"Cisco generic careers page should be flagged: {generic_url} (got: {reason}, needs_review={needs_review})"
        )

        # Specific Cisco job (should NOT be flagged)
        specific_url = (
            "https://jobs.cisco.com/jobs/ProjectDetail/Engineering-Manager-Software/1234567"
        )

        is_valid, reason, needs_review = validator.validate_url(specific_url)

        assert reason != "generic_career_page", (
            f"Cisco specific job should NOT be flagged: {specific_url}"
        )

    def test_flagged_jobs_included_but_marked_for_review(self):
        """
        Flagged jobs (generic_career_page) should be included in digest but marked
        for manual review, not completely rejected.

        This allows users to see potentially good opportunities even if URL validation
        couldn't confirm they're specific job postings.
        """
        validator = JobValidator(check_content=False)

        generic_url = "https://jobs.ashbyhq.com/company"  # Generic page

        is_valid, reason, needs_review = validator.validate_url(generic_url)

        # Should be valid=True (included) but needs_review=True (flagged)
        assert is_valid, "Generic pages should be included (valid=True)"
        assert needs_review, "Generic pages should be flagged for review"
        assert reason == "generic_career_page", "Reason should indicate generic page"
