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

### Core Documentation
- `README.md` - Project structure, deployment info, SEO requirements
- `CLAUDE.md` - Project-specific AI instructions (if exists)
- `todo.md` - Current priorities and task list

### Website-Specific Docs
- `docs/SITE_MAINTENANCE_GUIDE.md` - SEO checklist for new pages
- `docs/marketing/keyword-mapping.md` - SEO strategy (if working on content)
- `sitemap.xml` - Current page inventory

### Recent Changes
- `docs/completed-todos.md` - Recently completed work
- Review any files in `docs/features/` for active feature work

**Important:** Do not create any files if they don't exist - just note what's missing.

## 5. Search Claude Memory for Relevant Learnings

Use Claude Memory MCP to recall relevant past insights:

### Search by Topic
Use `mcp__claude-memory__search_conversations` to find relevant memories:

**Search queries to try:**
- "SEO maintenance" - Recall canonical tag, redirect, sitemap lessons
- "Netlify configuration" - Deployment and configuration solutions
- "responsive design" - Mobile breakpoint and CSS solutions
- "[specific page name]" - Page-specific learnings if working on known page
- "[specific bug]" - If addressing a recurring issue

**Review search results for:**
- Problem-solution pairs we've encountered before
- Configuration patterns that worked well
- Mistakes to avoid
- Design decisions and their rationale

### Get Recent Weekly Summary (Optional)
If it's Monday or you've been away, check weekly summary:
```
mcp__claude-memory__generate_weekly_summary
```

## 6. Check Deployment Status

**Netlify Status Check:**
- Visit: https://app.netlify.com/sites/adamkwhite/deploys
- Or use Netlify CLI if configured
- Check for failed deployments or build errors
- Review deploy preview for open PRs

**Verify Site Health:**
- Is production site live and accessible?
- Any reports of broken links or forms?
- Check `bugs/` directory for new screenshots

## 7. Review SEO & Content Status

**Check if any SEO maintenance is pending:**
- Are there new pages without canonical tags?
- Is `sitemap.xml` up to date?
- Any redirects missing from `netlify.toml`?
- Google Search Console issues reported? (if user mentions)

**Content Assets:**
- Any new images in `bugs/` or `issues/` to process?
- Outstanding testimonial images to replace?
- Style guide updates needed?

## 8. Prioritize Today's Work

Based on the above review, create a prioritized task list:

### High Priority
List urgent items that must be done today:
- Critical bugs blocking production
- SEO maintenance for recently deployed pages
- PR review feedback requiring immediate response
- Failed CI/CD builds to fix

### Medium Priority
Important but not urgent:
- Feature work in progress
- Content updates (copy, images)
- Documentation improvements
- New feature PRs to create

### Low Priority
Nice to have if time permits:
- Style guide updates
- Archive old documentation
- Refactoring and cleanup
- Future feature planning

## 9. Context Summary

After completing the above, provide a brief summary:

**Current State:**
- Branch: [main or feature branch name]
- Open PRs: [number and brief description]
- Pending Issues: [critical issues to address]
- Recent Memory: [key learnings recalled from Claude Memory]

**Today's Focus:**
- [Primary goal for today's session]
- [Secondary goals if time permits]

**Blockers:**
- [Anything blocking progress]
- [Questions for the user]

## 10. Ready to Start

Confirm with user before proceeding:
- "I've loaded the project context. Should we focus on [primary goal identified], or do you have something else in mind?"
- Wait for user direction before making changes 