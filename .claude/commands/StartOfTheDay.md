---
description: Start-of-day project context review including git status, recent PRs, and documentation
---

# Start of Day - Project Context Loading

This command helps you load project context at the start of each session.

## Project Type Detection

**Detect project type and use the appropriate template:**

### For Python Projects
If this project uses Python (has `requirements.txt`, `pyproject.toml`, or `.py` files):
- **Use:** `.claude/commands/python/StartOfTheDay.md`
- **Includes:** pytest, coverage, venv management, pip dependencies

### For Website Projects
If this project is a website (has `.html`, `.css`, or static site files):
- **Use:** `.claude/commands/web/StartOfTheDay.md`
- **Includes:** SEO checks, Netlify deployment, sitemap verification

### For Other Project Types
If neither applies, follow the base template:
- **Use:** `.claude/commands/common/StartOfTheDay-base.md`
- **Includes:** Git workflow, GitHub checks, Claude Memory, prioritization

## Quick Start (Generic)

If you need a quick context load without project-specific checks:

### 1. Git Status & Recent Changes
```bash
git status
git log -5 --oneline --decorate
git branch -a
```

### 2. GitHub Issues & PRs
```bash
gh pr list
gh pr checks
gh issue list --limit 10
```

### 3. Load Documentation
Read these files:
- `README.md` - Project overview
- `CLAUDE.md` - Project-specific instructions
- `todo.md` - Current priorities
- `/home/adam/Code/CLAUDE.md` - Global development standards

**Important:** Do not create files if they don't exist - just note what's missing.

### 4. Search Claude Memory
Use `mcp__claude-memory__search_conversations` with:
- "[technology name]" - Find relevant past learnings
- "[specific bug/feature]" - Recall related work
- "configuration" - Setup and config solutions

### 5. Prioritize Today's Work

**High Priority:** Critical bugs, failed CI/CD, urgent PR feedback
**Medium Priority:** Feature work, documentation, testing
**Low Priority:** Refactoring, future planning, cleanup

### 6. Context Summary

**Current State:**
- Branch: [branch name]
- Open PRs: [count and descriptions]
- Pending Issues: [critical items]
- Recent Memory: [key learnings]

**Today's Focus:**
- [Primary goal]
- [Secondary goals]

**Blockers:**
- [Issues blocking progress]
- [Questions for user]

### 7. Ready to Start

Confirm with user:
- "I've loaded the project context. Should we focus on [primary goal], or do you have something else in mind?"
- Wait for user direction before making changes

---

## Customization

To customize this for your project:

1. **Copy the appropriate template:**
   ```bash
   # For Python projects:
   cp .claude/commands/python/StartOfTheDay.md .claude/commands/StartOfTheDay.md

   # For web projects:
   cp .claude/commands/web/StartOfTheDay.md .claude/commands/StartOfTheDay.md
   ```

2. **Edit project-specific sections:**
   - Add your deployment URLs
   - Customize documentation paths
   - Add project-specific health checks
   - Update Claude Memory search queries

3. **Keep the base structure:**
   - Git/GitHub workflow (sections 1-2)
   - Claude Memory integration (section 4)
   - Prioritization framework (section 5)
   - Context summary template (section 6)
