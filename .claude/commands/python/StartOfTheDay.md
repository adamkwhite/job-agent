---
description: Start-of-day context loading, memory recall, and priority review
---

# Start of Day - Project Context Loading

## 1. Session Start Time

Record when this session begins:

Use `mcp__time__get_current_time` with timezone `America/Toronto`:

**Session started at:** [Display time from time server]

## 2. Git Status & Recent Changes

Check repository status and recent work:
```bash
git status
git log -5 --oneline --decorate  # Last 5 commits
git branch -a  # All branches
```

**Review:**
- Are we on main or a feature branch?
- Any uncommitted changes from previous session?
- Should we pull latest changes? `git pull`
- Any merge conflicts to address?

## 3. GitHub Issues & PRs

Check open work items:
```bash
gh pr list  # Open pull requests
gh pr checks  # Status of current PR (if on feature branch)
gh issue list --limit 10  # Recent issues
```

**Identify:**
- PRs waiting for review or merge
- Failed CI/CD checks that need fixing
- High-priority issues to address today
- Blocked items waiting on external input

## 4. Load Project Documentation

**Read these files to get project context:**

### Core Documentation (Read First)
- `README.md` - Project structure, installation, testing requirements
- `CHANGELOG.md` - **Recent session changes and version history** (PRIMARY for what changed)
- `CLAUDE.md` - Static project architecture and patterns (NOT session logs)
- `todo.md` - Current priorities and task list

### Python-Specific Docs
- `requirements.txt` or `pyproject.toml` - Dependencies
- `tests/` - Test structure and coverage reports
- `docs/TESTING_GUIDE.md` - Testing strategy (if exists)

### Recent Work
- Review `[Unreleased]` section in CHANGELOG.md for latest changes
- `docs/completed-todos.md` - Completed work archive (if exists)
- Review any files in `docs/features/` for active feature work

**Important:** Do not create any files if they don't exist - just note what's missing.

## 5. Search Claude Memory for Relevant Learnings

Use Claude Memory MCP to recall relevant past insights:

### Search by Topic
Use `mcp__claude-memory__search_conversations` to find relevant memories:

**Search queries to try:**
- "pytest configuration" - Testing setup and patterns
- "virtual environment" - Venv management solutions
- "test coverage" - Coverage improvement strategies
- "[specific module name]" - Module-specific learnings if working on known component
- "[specific bug]" - If addressing a recurring issue
- "dependency management" - Package installation and version conflicts

**Review search results for:**
- Problem-solution pairs we've encountered before
- Testing patterns that worked well
- Mistakes to avoid
- Architecture decisions and their rationale

### Get Recent Weekly Summary (Optional)
If it's Monday or you've been away, check weekly summary:
```
mcp__claude-memory__generate_weekly_summary
```

## 6. Check Virtual Environment & Dependencies

**Virtual Environment Health:**
```bash
# Check if venv is activated
which python  # Should point to project venv

# Check Python version
python --version

# List installed packages
pip list

# Check for outdated packages
pip list --outdated
```

**Dependency Verification:**
- Is `requirements.txt` or `pyproject.toml` up to date?
- Any security vulnerabilities? (Check GitHub Dependabot alerts)
- Do we need to upgrade any dependencies?

## 7. Run Tests & Check Coverage

**Test Suite Status:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=term-missing

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

**Review:**
- Are all tests passing?
- Current coverage percentage
- Any skipped or xfailed tests
- New tests needed for recent changes

## 8. Check CI/CD & Package Status

**CI/CD Pipeline:**
- Check GitHub Actions status (if configured)
- Review test results from latest commits
- Any failing builds to fix?

**Package Distribution (if applicable):**
- PyPI package status
- Version numbering strategy
- Need to prepare a new release?

## 9. Review Code Quality

**Static Analysis (if configured):**
```bash
# Linting
ruff check .  # or flake8, pylint

# Type checking
mypy .

# Code formatting
black --check .  # or ruff format
```

**Documentation:**
- Any docstrings missing?
- README.md examples still accurate?
- API documentation up to date?

## 10. Prioritize Today's Work

Based on the above review, create a prioritized task list:

### High Priority
List urgent items that must be done today:
- Critical bugs blocking users
- Failing tests or CI/CD builds
- PR review feedback requiring immediate response
- Security vulnerabilities to patch

### Medium Priority
Important but not urgent:
- Feature work in progress
- Test coverage improvements
- Documentation updates
- New feature PRs to create

### Low Priority
Nice to have if time permits:
- Code refactoring and cleanup
- Dependency updates (non-security)
- Future feature planning
- Documentation polish

## 11. Context Summary

After completing the above, provide a brief summary:

**Current State:**
- Branch: [main or feature branch name]
- Python Version: [version]
- Test Status: [passing/failing, coverage %]
- Open PRs: [number and brief description]
- Pending Issues: [critical issues to address]
- Recent Memory: [key learnings recalled from Claude Memory]

**Today's Focus:**
- [Primary goal for today's session]
- [Secondary goals if time permits]

**Blockers:**
- [Anything blocking progress]
- [Questions for the user]

## 12. Ready to Start

Confirm with user before proceeding:
- "I've loaded the project context. Should we focus on [primary goal identified], or do you have something else in mind?"
- Wait for user direction before making changes
