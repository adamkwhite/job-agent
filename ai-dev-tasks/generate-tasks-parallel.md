# Rule: Generating a Task List with Parallel Execution Support

## Goal

Generate a detailed, step-by-step task list from a PRD that supports **both serial and parallel execution modes**. Tasks are analyzed for dependencies and grouped for optimal parallel execution.

## Key Enhancement: Dependency Analysis

Unlike the standard `generate-tasks.md`, this version:
1. Analyzes which tasks can run in parallel (independent files/components)
2. Identifies dependencies between tasks (shared files, sequential requirements)
3. Creates execution groups for parallel agents
4. Supports both autonomous parallel execution and supervised serial execution

---

## Output

- **Format:** Markdown (`.md`)
- **Location:** Same feature directory as the PRD (e.g., `docs/features/[feature-name]-PLANNED/`)
- **Filename:** `tasks.md`

---

## Process

### Phase 1: Analyze PRD and Generate Parent Tasks

1. **Receive PRD Reference:** User points to a specific PRD file
2. **Analyze PRD:** Read functional requirements, user stories, technical specifications
3. **Generate Parent Tasks:** Create 5-10 high-level tasks required to implement the feature
4. **Present to User:** Show parent tasks and ask for confirmation
5. **Wait for "Go":** User responds with "Go" to proceed to detailed sub-tasks

### Phase 2: Generate Sub-Tasks with Dependency Analysis

6. **Break Down Tasks:** For each parent task, create actionable sub-tasks
7. **Analyze Dependencies:** For EACH task, identify:
   - **Files Modified:** Which files does this task touch?
   - **Dependencies:** Which tasks must complete before this one?
   - **Parallel Safe:** Can this run simultaneously with other tasks?
8. **Create Execution Groups:** Group independent tasks for parallel execution
9. **Generate Final Output:** Task list with dependency metadata

### Phase 3: Choose Execution Mode

10. **Ask User for Execution Mode:**
    - **Serial Mode:** One task at a time with user approval (original workflow)
    - **Parallel Mode:** Autonomous agents for independent task groups
    - **Hybrid Mode:** Parallel within groups, serial between groups

---

## Output Format

The generated task list **must** include dependency metadata:

```markdown
## Execution Strategy

**Mode:** [Serial | Parallel | Hybrid]
**Parallel Groups:** [Number] independent groups identified
**Estimated Time:**
- Serial: [X hours]
- Parallel: [Y hours] (Z% faster)

---

## Relevant Files

- `path/to/file1.ts` - Description
- `path/to/file1.test.ts` - Unit tests
- `path/to/file2.tsx` - Description
- `path/to/file2.test.tsx` - Unit tests

### Shared Files (Require Coordination)
- `docs/features/[feature]/status.md` - Updated by all tasks
- `CHANGELOG.md` - Updated at completion

---

## Task Dependency Graph

**Group 1 (Parallel Safe):**
- Task 1.0 ← No dependencies
- Task 2.0 ← No dependencies
- Task 3.0 ← No dependencies

**Group 2 (Depends on Group 1):**
- Task 4.0 ← Depends on Tasks 1.0, 2.0

**Group 3 (Serial Only):**
- Task 5.0 ← Depends on Task 4.0, modifies shared files

---

## Tasks

- [ ] 1.0 Parent Task Title
  - **Files:** `src/module1.py`, `tests/unit/test_module1.py`
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - [ ] 1.1 Sub-task description
  - [ ] 1.2 Sub-task description

- [ ] 2.0 Parent Task Title
  - **Files:** `src/module2.py`, `tests/unit/test_module2.py`
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - [ ] 2.1 Sub-task description

- [ ] 3.0 Parent Task Title
  - **Files:** `src/module3.py`, `tests/unit/test_module3.py`
  - **Dependencies:** None
  - **Parallel Safe:** ✅ Yes
  - **Execution Group:** Group 1
  - [ ] 3.1 Sub-task description

- [ ] 4.0 Integration Task
  - **Files:** `src/integration.py`, `tests/integration/test_integration.py`
  - **Dependencies:** Tasks 1.0, 2.0, 3.0 (needs their modules)
  - **Parallel Safe:** ❌ No (depends on Group 1)
  - **Execution Group:** Group 2
  - [ ] 4.1 Sub-task description

- [ ] 5.0 Update Documentation
  - **Files:** `CHANGELOG.md`, `docs/features/[feature]/status.md`
  - **Dependencies:** All previous tasks
  - **Parallel Safe:** ❌ No (shared files, should be last)
  - **Execution Group:** Group 3 (Serial)
  - [ ] 5.1 Update CHANGELOG.md
  - [ ] 5.2 Update status.md
```

---

## Dependency Analysis Rules

### Parallel Safe Tasks
A task is **parallel safe** if:
- ✅ Modifies different files than other tasks
- ✅ Has no sequential dependency (doesn't need output from other tasks)
- ✅ Doesn't modify shared configuration or documentation files
- ✅ Test suites can run independently

### Serial Tasks
A task is **serial** if:
- ❌ Depends on output/state from another task
- ❌ Modifies shared files (CHANGELOG, status.md, shared configs)
- ❌ Needs to run database migrations before other code changes
- ❌ User explicitly requests review between steps

### Execution Groups
- **Group 1:** All parallel-safe tasks with no dependencies
- **Group 2:** Tasks depending on Group 1 completion
- **Group N:** Tasks depending on Group N-1
- **Final Group:** Documentation/cleanup tasks (always serial)

---

## Execution Mode Details

### Serial Mode (Original Workflow)
- One sub-task at a time
- User approval between each step
- Safest for complex, risky changes
- Use when: uncertain about approach, need close supervision

### Parallel Mode (New)
- Spawn N agents for N independent tasks
- Agents work autonomously without user approval
- Fastest execution (can be 50-75% faster)
- Use when: tasks are independent, well-defined, low risk

### Hybrid Mode (Recommended)
- Parallel execution within groups
- User approval between groups
- Balance of speed and control
- Use when: some tasks are risky but most are straightforward

---

## Example Usage

**User:** "Generate parallel tasks for the PRD"

**AI Response:**
```
Analyzing PRD: docs/features/user-auth-PLANNED/prd.md

Found 4 main tasks:
1. Create authentication module
2. Add login UI components
3. Create database migrations
4. Add integration tests

Dependency analysis:
- Tasks 1, 2: PARALLEL SAFE (different files)
- Task 3: DEPENDS ON Task 1 (needs auth module structure)
- Task 4: DEPENDS ON Tasks 1, 2, 3 (needs everything)

Execution Strategy:
- Group 1: Tasks 1, 2 (parallel, ~2 hours)
- Group 2: Task 3 (serial, ~1 hour)
- Group 3: Task 4 (serial, ~1 hour)

Total time:
- Serial: ~6 hours
- Parallel: ~4 hours (33% faster)

Ready to generate sub-tasks? Respond with 'Go' to proceed.
```

---

## Integration with process-task-list.md

After generating tasks with dependency metadata, the AI should:

1. **If Serial Mode:** Follow standard `process-task-list.md` workflow
2. **If Parallel Mode:** Use new `process-task-list-parallel.md` workflow
3. **If Hybrid Mode:** Mix both workflows (parallel within groups, serial between)

---

## Notes

- Always create a dependency graph visual representation
- Estimate time savings from parallel execution
- Identify shared file conflicts early
- Default to Hybrid mode if user doesn't specify
- For simple features (<3 tasks), default to Serial mode

---

## Next Step

After generating tasks.md, ask user:

**"Task list generated with [N] parallel groups identified.**

**Choose execution mode:**
- **Serial:** One task at a time with your approval (safest, slower)
- **Parallel:** Autonomous agents for all groups (fastest, less control)
- **Hybrid:** Parallel within groups, approval between groups (recommended)

**Estimated time:**
- Serial: [X hours]
- Parallel: [Y hours] ([Z]% faster)

**Which mode would you like to use?**"
