# Parallel Task List Execution

Guidelines for executing task lists using **parallel autonomous agents** to maximize speed while maintaining quality.

---

## When to Use This Workflow

Use parallel execution when:
- ✅ Tasks touch **different files** (no merge conflicts)
- ✅ Tasks are **well-defined** with clear acceptance criteria
- ✅ PRD has **detailed specifications** with code examples
- ✅ User wants **autonomous execution** (e.g., while sleeping)
- ✅ Time is important (50-75% faster than serial)

**Don't use parallel execution when:**
- ❌ Tasks modify the same files
- ❌ Approach is uncertain or experimental
- ❌ User wants to review each step
- ❌ Tasks have complex dependencies

---

## Git Worktrees for Parallel Branch Work

**⚠️ CRITICAL:** When parallel agents work on **different branches**, you MUST use git worktrees to prevent branch interference.

### The Problem

Git only supports **one checked-out branch per working directory**. If:
- Session 1 works on `feature/branch-a`
- Session 2 runs `git checkout -b feature/branch-b`

Then Session 1's commits will **go to the wrong branch** because git's state changed globally.

### The Solution: Git Worktrees

Create **separate working directories** for each branch:

```bash
# Main repository (Session 1)
cd ~/Code/job-agent  # Works on main or existing branch

# Create worktree for parallel work (Session 2)
git worktree add ../job-agent-worktree-fix feature/fix-logging
cd ../job-agent-worktree-fix
# This directory has feature/fix-logging checked out
```

Each worktree has:
- ✅ Independent checked-out branch
- ✅ Shared `.git` repository (commits visible to both)
- ✅ Isolated working directory (no interference)

### When to Use Worktrees

**Use worktrees when:**
- ✅ Parallel Claude sessions working on different branches
- ✅ Parallel agents creating separate PRs for independent tasks
- ✅ You need to test one branch while working on another

**Don't need worktrees when:**
- ❌ All parallel work on same branch (just coordinate commits)
- ❌ Serial execution (one task at a time)
- ❌ Only one session working at a time

### Worktree Workflow

**Setup (before spawning agents):**
```bash
# For each parallel agent working on different branch:
git worktree add ../job-agent-worktree-1 feature/task-1
git worktree add ../job-agent-worktree-2 feature/task-2
git worktree add ../job-agent-worktree-3 feature/task-3

# Verify worktrees
git worktree list
```

**Agent Instructions:**
Update agent prompt template to specify worktree path:
```markdown
**Working Directory:** /home/user/Code/job-agent-worktree-1
1. cd /home/user/Code/job-agent-worktree-1
2. Verify branch: git branch --show-current
3. [Make changes]
4. Commit: git add -A && git commit -m "..."
5. Push: git push -u origin feature/task-1
```

**Cleanup (after agents complete):**
```bash
# Remove worktrees after PRs merged
git worktree remove ../job-agent-worktree-1
git worktree remove ../job-agent-worktree-2
git worktree remove ../job-agent-worktree-3

# Or remove all at once
git worktree list | grep worktree | awk '{print $1}' | xargs -I {} git worktree remove {}
```

### Alternative: Same Branch Coordination

If all parallel agents can work on the **same branch** (no conflicts):
```bash
# All agents work in ~/Code/job-agent on feature/multi-task
# Coordinate commits to avoid conflicts
# Single PR with all changes
```

This is simpler but requires careful file coordination.

---

## Execution Process

### Phase 1: Group Planning

1. **Analyze Dependency Groups** from tasks.md
   - Read the "Task Dependency Graph" section
   - Identify parallel-safe groups
   - Note sequential dependencies

2. **Create Execution Plan**
   ```markdown
   Execution Plan:
   - Group 1: Tasks 1.0, 2.0, 3.0 (3 parallel agents)
   - Group 2: Task 4.0 (1 agent, waits for Group 1)
   - Group 3: Task 5.0 (serial, documentation)
   ```

3. **Confirm with User**
   - Present the execution plan
   - Show estimated time savings
   - Get approval to proceed

---

### Phase 2: Parallel Execution (Per Group)

For each execution group, spawn N agents in a **single message**:

```python
# Example: Spawning 4 agents in parallel
Task(subagent_type="general-purpose", description="Fix bug A", prompt="...")
Task(subagent_type="general-purpose", description="Fix bug B", prompt="...")
Task(subagent_type="general-purpose", description="Fix bug C", prompt="...")
Task(subagent_type="general-purpose", description="Fix bug D", prompt="...")
# All 4 in ONE message for true parallelism
```

---

### Agent Prompt Template

**Option A: Using Worktrees (Recommended for parallel branches)**

```markdown
**Autonomous Task: [Task Title]**

**Goal:** [Brief description]

**Context:**
- PRD: docs/features/[feature]/prd.md (Section [X])
- Issue: https://github.com/user/repo/issues/[N]
- Branch: [branch-name]
- **Worktree Directory:** /home/user/Code/job-agent-worktree-[N]

**Instructions:**
1. **Navigate to worktree:** cd /home/user/Code/job-agent-worktree-[N]
2. **Verify branch:** git branch --show-current (should show [branch-name])
3. [Step-by-step implementation]
4. Run tests: PYTHONPATH=$PWD venv/bin/pytest [test-file] -v
5. Run full suite: PYTHONPATH=$PWD venv/bin/pytest tests/ -v
6. **COMMIT CHANGES:** git add -A && git commit -m "[commit message]\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
7. **PUSH BRANCH:** git push -u origin [branch-name]
8. Create PR: gh pr create --title "[title]" --body "[body]"
9. Update tasks.md in MAIN repo: cd /home/user/Code/job-agent && mark task [N] complete

**⚠️ CRITICAL:** You MUST commit changes (step 6) and push (step 7) BEFORE creating PR (step 8).
If you skip commits, your work will be LOST when the agent terminates.
```

**Option B: Same Branch (All agents on one branch)**

```markdown
**Autonomous Task: [Task Title]**

**Goal:** [Brief description]

**Context:**
- PRD: docs/features/[feature]/prd.md (Section [X])
- Issue: https://github.com/user/repo/issues/[N]
- Branch: [branch-name] (shared with other agents)
- **Working Directory:** /home/user/Code/job-agent

**Instructions:**
1. Verify branch: git branch --show-current (should show [branch-name])
2. **Pull latest:** git pull origin [branch-name] (in case other agents committed)
3. [Step-by-step implementation]
4. Run tests: PYTHONPATH=$PWD venv/bin/pytest [test-file] -v
5. Run full suite: PYTHONPATH=$PWD venv/bin/pytest tests/ -v
6. **COMMIT CHANGES:** git add -A && git commit -m "[commit message]\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
7. **PUSH BRANCH:** git push origin [branch-name]
8. Update tasks.md: Mark task [N] as complete

**⚠️ CRITICAL:** You MUST commit changes (step 6) and push (step 7).
If you skip commits, your work will be LOST when the agent terminates.

**Success Criteria:**
- All tests pass
- PR created and linked
- SonarCloud passes

**Important:**
- Work autonomously (no user approval needed)
- Don't modify files outside your scope
- Document blockers in PR description
```

---

## Coordination Strategy

**Shared File Management:**

1. **During Execution:**
   - Each agent updates only their task in tasks.md
   - Agents skip status.md updates

2. **After Group Completes:**
   - Single consolidation updates status.md
   - Merges all task results
   - Resolves conflicts

---

## Validation Checkpoints

**After Each Group Completes:**

Before proceeding to the next group, the parent session MUST verify:

```bash
# If using worktrees: Check each worktree directory
for worktree in ../job-agent-worktree-*; do
  echo "=== Checking $worktree ==="
  cd "$worktree"
  git log --oneline -3
  git status --short  # Should be clean
done
cd ~/Code/job-agent  # Return to main repo

# Check that agents committed their work
git log --oneline -10  # Should show commits from all agents
git branch -a | grep feature/  # Should show all feature branches

# Verify branches exist on remote
git branch -r | grep [task-branch-name]

# If using same branch: Check for uncommitted changes
git status --short  # Should not show modified files from completed tasks
```

**If validation fails:**
1. ❌ STOP immediately - do NOT proceed to next group
2. 🔍 Investigate which agent failed to commit
3. 🛠️ Manually commit the changes or re-run the agent
4. ✅ Re-validate before continuing

**Red Flags:**
- Agent reports "success" but no git commits exist
- `git status` shows modified files for completed tasks
- No branch exists on remote for completed task

---

## Example: Week 1 Execution

```markdown
PRD: docs/features/code-quality-improvements-PLANNED/prd.md

Group 1: All 4 tasks parallel (independent files)
- Agent 1: Issue #219 (profile_scorer.py)
- Agent 2: Issue #220 (config_validator.py - new)
- Agent 3: Issue #221 (send_profile_digest.py)
- Agent 4: Issue #222 (url_validator.py - new)

Results:
- Completed in ~2 hours (vs 8 hours serial)
- 4 PRs created (#224-227)
- 0 merge conflicts
- Time saved: 75%
```

---

## Error Handling

**If Agent Fails:**

1. **Independent Failure:** Other agents continue
2. **Blocking Failure:** Stop dependent tasks only
3. **User Decision:** Fix and retry, or skip

---

## Success Metrics

- N/N tasks completed
- N PRs passing CI/CD
- 0 merge conflicts
- Accurate tasks.md updates

---

## AI Instructions

When executing parallel tasks:

1. **Spawn all group agents in ONE message**
2. **Don't wait between spawns**
3. **After group completion:**
   - Update status.md once
   - Commit documentation
   - Notify user
4. **Between groups (Hybrid mode):**
   - Pause and report
   - Wait for "continue"
