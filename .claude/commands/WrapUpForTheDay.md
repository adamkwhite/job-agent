---
description: End-of-day wrap-up tasks including cleanup, documentation updates, and memory storage
---

# End-of-Day Wrap-Up

This command helps you wrap up your session systematically.

## Project Type Detection

**Detect project type and use the appropriate template:**

### For Python Projects
If this project uses Python (has `requirements.txt`, `pyproject.toml`, or `.py` files):
- **Use:** `.claude/commands/python/WrapUpForTheDay.md`
- **Includes:** pytest, coverage reports, requirements.txt updates, venv checks

### For Website Projects
If this project is a website (has `.html`, `.css`, or static site files):
- **Use:** `.claude/commands/web/WrapUpForTheDay.md`
- **Includes:** SEO checklist, sitemap updates, Netlify deployment verification

### For Other Project Types
If neither applies, follow the base template:
- **Use:** `.claude/commands/common/WrapUpForTheDay-base.md`
- **Includes:** Git workflow, cleanup, documentation, Claude Memory storage

## Quick Wrap-Up (Generic)

If you need a quick wrap-up without project-specific checks:

### 1. File Organization & Cleanup
- Remove temporary files (temp_*, debug_*, demo_*, scratch_*)
- Verify README.md structure matches directories
- Move artifacts to appropriate locations
- Check for files to archive in `docs/archive/`

```bash
git status  # Review all changes
```

### 2. Documentation Updates

**Update todo.md:**
- Outstanding tasks
- Bugs discovered
- Improvements needed

**Update CLAUDE.md:**
- What changed and why
- Architecture decisions
- Solutions to problems
- Next steps
- Known issues

### 3. Store Learnings in Claude Memory

Use `mcp__claude-memory__add_conversation` to store:

**Problem-Solution Pairs:**
```
Title: [Brief problem]
Content:
Problem: [What went wrong]
Solution: [How we solved it]
Context: [Project], [technology], [component]
Date: [Today's date]
```

**Design Patterns:**
```
Title: Pattern - [Pattern name]
Content: Implementation, rationale, trade-offs
```

### 4. Git Workflow

```bash
# Create feature branch
git checkout -b feature/[description]

# Stage and commit
git add [files]
git commit -m "$(cat <<'EOF'
[Summary of changes]

[Detailed explanation]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push and create PR
git push -u origin feature/[description]
gh pr create
```

### 5. Monitor CI/CD

```bash
gh pr checks
gh run watch  # If available
```

### 6. Final Verification

- [ ] All todos documented
- [ ] CLAUDE.md updated
- [ ] Key learnings stored in Claude Memory
- [ ] Branch created and pushed
- [ ] PR created with complete description
- [ ] CI/CD checks passing or in progress
- [ ] No temporary files in root
- [ ] No untracked files that should be committed
- [ ] No sensitive data committed

---

## Customization

To customize this for your project:

1. **Copy the appropriate template:**
   ```bash
   # For Python projects:
   cp .claude/commands/python/WrapUpForTheDay.md .claude/commands/WrapUpForTheDay.md

   # For web projects:
   cp .claude/commands/web/WrapUpForTheDay.md .claude/commands/WrapUpForTheDay.md
   ```

2. **Edit project-specific sections:**
   - Add project-specific cleanup tasks
   - Customize verification checklists
   - Update deployment verification steps
   - Add project-specific CI/CD checks

3. **Keep the base structure:**
   - File organization (section 1)
   - Documentation updates (section 2)
   - Claude Memory storage (section 3)
   - Git workflow (section 4)
   - Final verification (section 6)

## Directory Structure Reference

```
$PROJECT_NAME/
├── src/                    # Application source code
├── tests/                  # Unit and integration tests
├── docs/                   # Documentation and design materials
│   └── archive/            # Old documents
├── scripts/                # Build and deployment scripts
├── README.md               # Project overview
└── CLAUDE.md               # Project context for Claude AI
```
