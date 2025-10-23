---
description: End-of-day wrap-up tasks including cleanup, documentation updates, and memory storage
---

# End-of-Day Wrap-Up

## 1. Session End Time

Use `mcp__time__get_current_time` with timezone `America/Toronto`:

**Session ending at:** [Display time from time server]

---

## 2. File Organization & Cleanup

### Root Directory Cleanup
- Check for temporary files in root (temp_*, debug_*, demo_*, scratch_*, test_*)
- Verify README.md structure matches actual directories
- Move test output files to appropriate directories
- Check if any docs should move to `docs/archive/`
- Remove Python cache files if committed by mistake (`__pycache__/`, `*.pyc`)

### Git Housekeeping
```bash
git status  # Review all changes
```
- Stage all intentional deletions and moves
- Verify untracked files should exist or be gitignored
- Check `.gitignore` catches test artifacts, coverage reports, venv/

## 3. Test Suite & Coverage (CRITICAL)

### Run Full Test Suite
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov --cov-report=term-missing --cov-report=html

# Check coverage percentage
coverage report
```

**Checklist:**
- [ ] All tests passing
- [ ] Coverage meets project requirements (typically 80%+)
- [ ] New code has corresponding tests
- [ ] No skipped tests without good reason
- [ ] Integration tests run successfully

### Code Quality Checks
```bash
# Linting
ruff check .  # or flake8, pylint

# Type checking (if using)
mypy .

# Code formatting
black .  # or ruff format

# Security check (if configured)
bandit -r src/
```

## 4. Dependency Management

### Update Requirements
```bash
# Freeze current dependencies
pip freeze > requirements.txt

# Or update pyproject.toml if using Poetry/PDM
poetry lock  # or pdm lock
```

**Check for:**
- [ ] New dependencies added during session
- [ ] Version pins appropriate (exact vs compatible)
- [ ] Dev dependencies separated from production
- [ ] Security vulnerabilities (`pip-audit` or `safety check`)

### Virtual Environment Health
- Verify venv is tracked in `.gitignore`
- Document Python version requirements in README.md
- Note any OS-specific dependencies

## 5. Documentation Updates

### Update todo.md
Add any outstanding:
- Tasks to complete
- Bugs discovered (with error messages/stack traces)
- Test improvements needed
- Performance issues identified
- Dependency updates needed

### Update CLAUDE.md
Document what changed during this session:

**Modules Modified:**
- List which Python modules were edited and why

**API Changes:**
- Function signatures changed
- New classes or methods added
- Breaking changes introduced

**Testing Updates:**
- New test files or test cases
- Coverage improvements
- Test infrastructure changes

**Implementation Details:**
- Architecture decisions made
- Solutions to problems encountered
- Workarounds or compromises
- Performance optimizations

**Next Steps:**
- What needs to be done next
- Blockers or questions remaining

**Known Issues:**
- New bugs discovered
- Technical debt identified
- Compatibility concerns

### Update CHANGELOG.md (if exists)
Document changes for version tracking:
- Features added
- Bugs fixed
- Breaking changes
- Deprecated functionality

## 6. Store Learnings in Claude Memory

Use the Claude Memory MCP to store important learnings from this session.

### What to Store:
Store insights that would be valuable in future sessions:

**Problem-Solution Pairs:**
```
Title: [Brief problem description]
Content:
Problem: [What went wrong or what challenge we faced]
Solution: [How we solved it, with code examples]
Context: [Project name], Python [version], [specific module/feature]
Date: [Today's date]
```

**Testing Patterns:**
```
Title: Test Pattern - [Pattern name]
Content:
- How we structured tests for [feature]
- Fixtures and mocks used
- Coverage strategy
- Edge cases discovered
```

**Dependency & Environment Lessons:**
```
Title: Dependency Management - [Topic]
Content:
- Package compatibility issues encountered
- Version conflicts and resolutions
- Virtual environment setup tips
- Installation gotchas
```

**Architecture & Design Patterns:**
```
Title: Design Pattern - [Pattern name]
Content:
- How we implemented [feature]
- Why this approach was chosen
- Trade-offs considered
- Code organization strategy
```

**Performance Optimizations:**
```
Title: Performance - [Optimization]
Content:
- Bottleneck identified
- Solution implemented
- Benchmarking results
- When to apply this pattern
```

### Store the Memory:
After drafting the summary, use the Claude Memory MCP to store it:
```
mcp__claude-memory__add_conversation with:
- title: Brief descriptive title
- content: Structured summary as above
- date: Today's date
```

## 7. Create Feature Branch & PR

### Branch Workflow
```bash
# If not already on feature branch
git checkout -b feature/[description]

# Stage changes
git add [files]

# Commit with context
git commit -m "$(cat <<'EOF'
[Summary of changes]

[Detailed explanation of what changed and why]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push branch
git push -u origin feature/[description]

# Create PR
gh pr create
```

### PR Description Should Include:
- Summary of changes
- Links to related issues or PRs
- Test results and coverage changes
- Breaking changes (if any)
- Migration guide (if needed)
- Dependencies added/updated

## 8. CI/CD Verification

### Monitor Pipeline
```bash
# Check PR status
gh pr checks

# Watch workflow run
gh run watch
```

**Verify:**
- [ ] All CI checks passing
- [ ] Tests run on multiple Python versions (if configured)
- [ ] Coverage reports generated
- [ ] Linting and type checking pass
- [ ] Build succeeds

### Package Build (if applicable)
```bash
# Build package
python -m build

# Verify package contents
tar -tzf dist/*.tar.gz
```

## 9. Session Summary

Record when this session ends and calculate duration:

**Session ended at:** [Time from section 1]

**Session duration:** [Calculate time from StartOfTheDay to end time]

**Session accomplishments:**
- [Key tasks completed]
- [PRs created/merged]
- [Issues resolved]
- [Tests added/fixed]
- [Coverage improvements]
- [Learnings captured]

## 9. Final Verification

- [ ] All tests passing locally
- [ ] Coverage meets project requirements
- [ ] No linting or type errors
- [ ] requirements.txt or pyproject.toml updated
- [ ] All todo items documented
- [ ] CLAUDE.md updated with session learnings
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Key learnings stored in Claude Memory
- [ ] Git branch created and pushed
- [ ] PR created with complete description
- [ ] CI/CD checks passing
- [ ] No temporary files left in root
- [ ] No untracked files that should be committed
- [ ] Virtual environment not committed
