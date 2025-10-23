---
description: Shared base template for end-of-day wrap-up routines
---

# End-of-Day Wrap-Up - Base Template

This is a shared base template containing common elements for end-of-day routines.
Project-specific templates in `web/` and `python/` directories extend this base.

## Core Components

### 1. Session End Time

Use `mcp__time__get_current_time` with timezone `America/Toronto`:

**Session ending at:** [Display time from time server]

---

### 2. File Organization & Cleanup

**Root Directory:**
- Remove temporary files (temp_*, debug_*, demo_*, scratch_*)
- Verify README.md structure matches actual directories
- Move screenshots/artifacts to appropriate directories
- Check if docs should move to `docs/archive/`

**Git Housekeeping:**
```bash
git status  # Review all changes
```
- Stage intentional deletions and moves
- Verify untracked files are intentional or gitignored
- Check `.gitignore` catches build artifacts and temporary files

### 3. Documentation Updates

**Update todo.md:**
- Outstanding tasks to complete
- Bugs discovered (with context)
- Improvements needed
- Future work identified

**Update CLAUDE.md:**

**What Changed:**
- Files/modules modified and why
- Features added or bugs fixed
- Configuration changes

**Implementation Details:**
- Architecture decisions made
- Solutions to problems encountered
- Workarounds or compromises
- Performance considerations

**Next Steps:**
- What needs to be done next
- Blockers or questions remaining

**Known Issues:**
- New bugs discovered
- Technical debt identified
- Compatibility concerns

### 4. Claude Memory Storage

Use `mcp__claude-memory__add_conversation` to store learnings:

**Problem-Solution Pairs:**
```
Title: [Brief problem description]
Content:
Problem: [Challenge faced]
Solution: [How we solved it, with examples]
Context: [Project name], [technology], [component]
Date: [Today's date]
```

**Architecture & Design Patterns:**
```
Title: Design Pattern - [Pattern name]
Content:
- Implementation approach
- Why this pattern was chosen
- Trade-offs considered
- When to apply this pattern
```

**Configuration & Setup:**
```
Title: [Tool/Service] Configuration
Content:
- How we configured [feature]
- Settings chosen and why
- Issues encountered and solutions
- Best practices discovered
```

### 5. Git Workflow

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

**PR Description Should Include:**
- Summary of changes
- Links to related issues or PRs
- Testing performed
- Breaking changes (if any)
- Screenshots (for UI changes)

### 6. CI/CD Monitoring

```bash
# Check PR status
gh pr checks

# Watch workflow run (if available)
gh run watch
```

**Verify:**
- All CI checks passing or in progress
- Build succeeds
- Tests run successfully
- Deployment previews working (if applicable)

### 7. Session Summary

Record when this session ends and calculate duration:

**Session ended at:** [Time from section 1]

**Session duration:** [Calculate time from StartOfTheDay to end time]

**Session accomplishments:**
- [Key tasks completed]
- [PRs created/merged]
- [Issues resolved]
- [Learnings captured]

### 8. Final Verification Checklist

- [ ] All todo items documented
- [ ] CLAUDE.md updated with session learnings
- [ ] Key learnings stored in Claude Memory
- [ ] Git branch created and pushed
- [ ] PR created with complete description
- [ ] CI/CD checks passing or in progress
- [ ] No temporary files left in root
- [ ] No untracked files that should be committed
- [ ] No sensitive data or credentials committed
