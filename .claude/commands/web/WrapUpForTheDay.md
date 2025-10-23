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
- Check for temporary files in root (temp_*, debug_*, demo_*, scratch_*)
- Verify README.md structure matches actual directories
- Move bug screenshots to `bugs/` directory
- Move issue documentation to `issues/` directory
- Check if any docs should move to `docs/archive/`

### Git Housekeeping
```bash
git status  # Review all changes
```
- Stage all intentional deletions and moves
- Verify untracked files should exist or be gitignored
- Check `.gitignore` is catching test-results/ and build artifacts

## 3. SEO & Website Maintenance (CRITICAL)

### If New Pages Were Added
Run through `docs/SITE_MAINTENANCE_GUIDE.md` checklist:
- [ ] Added canonical tags to new `.html` pages
- [ ] Added redirects to `netlify.toml`
- [ ] Updated `sitemap.xml` with new URLs
- [ ] Verified all internal links use `.html` extension
- [ ] Updated lastmod dates in sitemap

### Content Updates
- [ ] Updated `style-guide.html` if new components were added
- [ ] Verified responsive breakpoints (375px, 768px, 1024px, 1440px) if UI changed
- [ ] Checked mobile navigation and forms if modified

## 4. Documentation Updates

### Update todo.md
Add any outstanding:
- Tasks to complete
- Bugs discovered (link to screenshots in `bugs/`)
- SEO tasks (new pages, meta tag updates needed)
- Content updates (images, testimonials, copy changes)

### Update Claude.md
Document what changed during this session:

**Pages Modified:**
- List which HTML pages were edited and why

**SEO Changes:**
- Meta tags, canonical tags, or sitemap updates
- New redirects added

**Component Updates:**
- New or modified components in style-guide.html
- CSS or JavaScript changes

**Implementation Details:**
- Architecture decisions made
- Solutions to problems encountered
- Workarounds or compromises

**Next Steps:**
- What needs to be done next
- Blockers or questions remaining

**Known Issues:**
- New bugs discovered
- Technical debt identified

## 5. Store Learnings in Claude Memory

Use the Claude Memory MCP to store important learnings from this session.

### What to Store:
Store insights that would be valuable in future sessions:

**Problem-Solution Pairs:**
```
Title: [Brief problem description]
Content:
Problem: [What went wrong or what challenge we faced]
Solution: [How we solved it, with code examples if relevant]
Context: Adam White coaching website, [specific page/feature]
Date: [Today's date]
```

**SEO & Maintenance Lessons:**
```
Title: SEO Maintenance - [Topic]
Content:
- What we learned about canonical tags, redirects, or sitemap management
- Common mistakes to avoid
- Tools or techniques that worked well
Context: Static website on Netlify
```

**Design Patterns & Components:**
```
Title: Component Pattern - [Component name]
Content:
- How we implemented [feature]
- CSS or JS techniques used
- Responsive considerations
- Browser compatibility notes
```

**Deployment & Configuration:**
```
Title: Netlify Configuration - [Feature]
Content:
- How we configured [redirects/forms/headers]
- Why certain settings were chosen
- Issues encountered and solutions
```

### Store the Memory:
After drafting the summary, use the Claude Memory MCP to store it:
```
mcp__claude-memory__add_conversation with:
- title: Brief descriptive title
- content: Structured summary as above
- date: Today's date
```

## 6. Create Feature Branch & PR

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
- SEO checklist completion status (if applicable)
- Testing performed
- Screenshots (for UI changes)

## 7. Session Summary

Record when this session ends and calculate duration:

**Session ended at:** [Time from section 1]

**Session duration:** [Calculate time from StartOfTheDay to end time]

**Session accomplishments:**
- [Key tasks completed]
- [PRs created/merged]
- [Pages modified/created]
- [SEO updates completed]
- [Issues resolved]
- [Learnings captured]

## 8. Final Verification

- [ ] All todo items documented
- [ ] Claude.md updated with session learnings
- [ ] Key learnings stored in Claude Memory
- [ ] Git branch created and pushed
- [ ] PR created with complete description
- [ ] No temporary files left in root
- [ ] No untracked files that should be committed