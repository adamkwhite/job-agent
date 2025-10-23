---
description: Shared base template for start-of-day routines
---

# Start of Day - Base Template

This is a shared base template containing common elements for start-of-day routines.
Project-specific templates in `web/` and `python/` directories extend this base.

## Core Components

### 1. Session Start Time

Record when this session begins:

Use `mcp__time__get_current_time` with timezone `America/Toronto`:

**Session started at:** [Display time from time server]

### 2. Git Status & Recent Changes

```bash
git status
git log -5 --oneline --decorate  # Last 5 commits
git branch -a  # All branches
```

**Review:**
- Current branch (main or feature branch)
- Uncommitted changes from previous session
- Need to pull latest changes? `git pull`
- Merge conflicts to address

### 3. GitHub Issues & PRs

```bash
gh pr list  # Open pull requests
gh pr checks  # Status of current PR (if on feature branch)
gh issue list --limit 10  # Recent issues
```

**Identify:**
- PRs waiting for review or merge
- Failed CI/CD checks needing fixes
- High-priority issues for today
- Blocked items waiting on external input

### 4. Load Core Documentation

**Read these files:**
- `README.md` - Project overview and structure
- `CLAUDE.md` - Project-specific AI instructions
- `todo.md` - Current priorities and task list
- `docs/completed-todos.md` - Recently completed work

**Important:** Do not create files if they don't exist - just note what's missing.

### 5. Claude Memory Integration

Use `mcp__claude-memory__search_conversations` to recall relevant insights:

**Common search queries:**
- "[technology/framework name]" - Technology-specific learnings
- "[specific bug/error]" - Previous solutions to similar issues
- "[feature name]" - Feature-specific context
- "configuration" - Setup and config solutions

**Look for:**
- Problem-solution pairs from previous sessions
- Architecture decisions and rationale
- Mistakes to avoid
- Patterns that worked well

**Weekly summary (Mondays or after breaks):**
```
mcp__claude-memory__generate_weekly_summary
```

### 6. Work Prioritization Framework

**High Priority** (Must complete today):
- Critical bugs blocking users/production
- Failed CI/CD builds or tests
- PR review feedback requiring immediate response
- Security vulnerabilities

**Medium Priority** (Important but not urgent):
- Feature work in progress
- Documentation updates
- Test coverage improvements
- New feature PRs to create

**Low Priority** (Nice to have if time permits):
- Code refactoring and cleanup
- Future feature planning
- Documentation polish
- Archive old files

### 7. Context Summary Template

**Current State:**
- Branch: [branch name]
- Open PRs: [count and brief descriptions]
- Pending Issues: [critical issues]
- Recent Memory: [key learnings from Claude Memory]

**Today's Focus:**
- [Primary goal]
- [Secondary goals if time permits]

**Blockers:**
- [Anything blocking progress]
- [Questions for user]

### 8. Confirm Before Proceeding

Always confirm with user before making changes:
- "I've loaded the project context. Should we focus on [primary goal], or do you have something else in mind?"
- Wait for user direction before starting work
