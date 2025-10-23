---
description: Synchronize all project .claude/settings.local.json files with master settings
---

# Sync Settings Across Projects

Synchronize all project `.claude/settings.local.json` files with the master settings file.

## Master Settings File
`/home/adam/Code/.claude/settings.local.json`

## Task Requirements

1. **Find all settings files**:
   - Search `/home/adam/Code/**/.claude/settings.local.json`
   - Exclude the master file from sync targets

2. **Compare each project file to master**:
   - Load master settings as the source of truth
   - For each project settings file:
     - Compare permissions.allow arrays
     - Compare permissions.deny arrays
     - Compare permissions.ask arrays (if present)
     - Check for additional properties (enableAllProjectMcpServers, outputStyle, etc.)
     - Identify missing permissions
     - Identify extra permissions not in master
     - Identify property differences

3. **For each out-of-sync project**:
   - Check if directory is a git repository
   - If not a git repo, skip with warning message
   - If git repo:
     a. Create feature branch: `sync-settings-YYYY-MM-DD`
     b. Update `.claude/settings.local.json` to match master
     c. Commit with message: "Sync .claude/settings.local.json with global master"
     d. Push branch to remote
     e. Create PR with detailed body showing:
        - Added permissions
        - Removed permissions
        - Property changes
     f. Track PR URL for monitoring

4. **Monitor all created PRs**:
   - Use `gh pr checks` to monitor CI status
   - Display summary table of all PRs and their status
   - Wait for PR checks to complete or fail
   - If checks pass, report success
   - If checks fail, analyze failure logs

5. **Handle PR review feedback**:
   - If PR has review comments requesting changes:
     - Parse review comments
     - For each distinct issue raised:
       - Create GitHub issue with label "settings-sync-review"
       - Link issue back to PR
       - Add issue to tracking list
   - Display all created issues

6. **Summary Report**:
   - Total projects scanned
   - Projects in sync (no action needed)
   - Projects updated (PRs created)
   - Projects skipped (not git repos)
   - PR status summary
   - Issues created (if any)

## Labels to Create (if needed)
- `settings-sync` - For PRs created by this command
- `settings-sync-review` - For issues created from PR reviews

## Error Handling
- If master file not found, exit with error
- If project file is malformed JSON, log warning and skip
- If git operations fail, log error and continue with next project
- If gh commands fail, provide troubleshooting guidance

## Notes
- Only sync projects that are git repositories
- Preserve project-specific settings that don't conflict with master
- Use force push sparingly - only if branch already exists
- Always include comparison details in PR body for transparency
