# Textual TUI Migration Plan (Issue #119)

**Status**: Planning Phase
**Priority**: High (blocks Issue #118 - Metrics Dashboard)
**Estimated Effort**: 20-29 hours
**Target Completion**: TBD

---

## Executive Summary

Migrate the existing Rich-based TUI (`src/tui.py`, 870 lines) to Textual framework for better UX with mouse support, keyboard navigation, and screen-based architecture. The current implementation uses prompt loops which are hard to test and provide poor navigation experience.

---

## 1. Current TUI Analysis

### Current Architecture (`src/tui.py`)
**Framework**: Rich (Console, Prompt, Table, Panel)
**Lines of Code**: 870 lines
**Main Components**:
- Profile selection (dynamic from profile manager)
- Source selection (Email, Robotics, Companies)
- Advanced options (LLM extraction toggle)
- Action selection (Scrape, Digest, Both)
- Digest options (Dry run, Force resend)
- LLM failure review interface
- Scoring criteria display

### Pain Points
1. **No mouse support** - Can't click on menu items or table rows
2. **No keyboard navigation** - Can't use arrow keys to browse options
3. **Prompt loops** - `while True` with `Prompt.ask()` feels clunky
4. **Limited visual feedback** - No highlighting of selections
5. **Difficult browsing** - Hard to review failures and metrics efficiently
6. **Hard to test** - Rich console interactions and while loops make testing difficult (see `test_llm_failure_update.py` coverage issues)

### Current Features to Preserve
✅ Dynamic profile loading from profile manager
✅ Profile-specific email inbox display
✅ Source selection with volume estimates
✅ Scoring criteria display (profile-specific)
✅ LLM extraction toggle (advanced options)
✅ Digest modes (Production, Dry run, Force resend)
✅ LLM failure review with retry/skip actions
✅ Markdown preview for failures
✅ Command execution with subprocess
✅ Confirmation before execution

---

## 2. Textual Framework Research

### Key Architectural Patterns

**Sources**:
- [Python Textual: Build Beautiful UIs in the Terminal – Real Python](https://realpython.com/python-textual/)
- [7 Things I've learned building a modern TUI Framework](https://www.textualize.io/blog/7-things-ive-learned-building-a-modern-tui-framework/)
- [Textual: The Definitive Guide - Part 1](https://dev.to/wiseai/textual-the-definitive-guide-part-1-1i0p)
- [Textual - Official Documentation](https://textual.textualize.io/)

### Core Concepts

1. **Event-Driven Model**
   - Define callbacks for key presses, mouse clicks, timer ticks
   - Async event handlers for non-blocking UI
   - Built-in event system for widget interactions

2. **Reactive Programming**
   - Reactive attributes that auto-update UI when state changes
   - Borrowed from Vue.js and React
   - Example: `self.profile = reactive("wes")` auto-updates UI

3. **Widget-Based Architecture**
   - Composable widgets (Button, DataTable, Input, etc.)
   - Custom widgets by extending base Widget class
   - Rich widget library included

4. **CSS Styling**
   - Terminal CSS for styling widgets
   - Layout management (docking, grid, horizontal, vertical)
   - Responsive design for different terminal sizes

5. **Screen-Based Navigation**
   - Multiple screens within one app
   - Stack-based navigation (push/pop screens)
   - Example: DashboardScreen, FailuresScreen, MetricsScreen

6. **Async/Concurrency**
   - All event handlers are async
   - Non-blocking operations (API calls, file I/O)
   - Prevents frozen UI during long-running tasks

### Development Tools

- **Debug Console**: `textual console` - shows print() output in separate console
- **Devtools**: `textual run --dev src/tui/app.py` - hot reload and debugging
- **CSS Inspector**: Built-in tool to inspect widget styles

---

## 3. Proposed Architecture

### Directory Structure
```
src/tui/
├── app.py                 # Main Textual application
├── screens/
│   ├── __init__.py
│   ├── dashboard.py       # Job scraping workflow configuration
│   ├── failures.py        # LLM failure review and management (primary focus)
│   └── metrics.py         # LLM vs Regex comparison statistics (Issue #118)
├── widgets/
│   ├── __init__.py
│   ├── profile_selector.py
│   ├── source_selector.py
│   ├── scoring_panel.py
│   └── failure_table.py
├── data/
│   ├── __init__.py
│   └── state.py           # Shared application state
└── styles.css             # Global CSS styling

run-tui.sh                 # Update to launch new Textual app
src/tui.py                 # Deprecate (rename to tui_legacy.py)
```

### Three Primary Screens

#### 1. Dashboard Screen (Migration of current TUI workflow)
**Purpose**: Configure and execute job scraping workflow

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Job Agent Pipeline Controller               │
├─────────────────────────────────────────────┤
│ [Profile Selector Widget]                   │
│   - Wes (Robotics/Hardware)                 │
│   - Adam (Software/Product)                 │
│   - Eli (Fintech/Healthtech)                │
├─────────────────────────────────────────────┤
│ [Source Selector Widget]                    │
│   [ ] Email (~50-100 jobs)                  │
│   [ ] Robotics Sheet (~10-20 jobs)          │
│   [ ] Companies (~20-40 jobs)               │
├─────────────────────────────────────────────┤
│ [Scoring Panel Widget] (Profile-specific)   │
│   Seniority (30): VP/Director/Head          │
│   Domain (25): Robotics/Hardware            │
│   Location (15): Remote/Hybrid Ontario      │
├─────────────────────────────────────────────┤
│ [Action Selector]                           │
│   ( ) Scrape Only                           │
│   ( ) Send Digest                           │
│   (*) Scrape + Digest                       │
├─────────────────────────────────────────────┤
│ [Advanced Options]                          │
│   [ ] Enable LLM Extraction                 │
├─────────────────────────────────────────────┤
│ [Digest Options] (if sending digest)        │
│   ( ) Production                            │
│   (*) Dry Run                               │
│   ( ) Force Resend                          │
├─────────────────────────────────────────────┤
│           [Run] [Cancel]                    │
└─────────────────────────────────────────────┘
Footer: d: Dashboard | f: Failures | m: Metrics | q: Quit
```

**Key Widgets**:
- `ProfileSelector` - Radio buttons or list view
- `SourceSelector` - Checkboxes with descriptions
- `ScoringPanel` - Static display (reactive to profile selection)
- `ActionSelector` - Radio buttons
- `DigestOptions` - Radio buttons (conditional visibility)
- `Button` widgets for Run/Cancel

**Reactive Behavior**:
- Profile selection → Update scoring panel + email inbox display
- Source selection → Show/hide advanced options (LLM extraction only if "companies" selected)
- Action selection → Show/hide digest options

#### 2. Failures Screen (LLM extraction failure review)
**Purpose**: Review and manage LLM extraction failures

**Layout**:
```
┌─────────────────────────────────────────────┐
│ LLM Extraction Failures Review              │
├─────────────────────────────────────────────┤
│ Summary: 15 pending | 5 retry | 3 skip      │
├─────────────────────────────────────────────┤
│ # │ Company        │ Reason       │ Date    │
│───┼────────────────┼──────────────┼─────────│
│ 1 │ Boston Dynamic │ Timeout      │ 2025-12 │
│ 2 │ Figure         │ Parse error  │ 2025-12 │
│ 3 │ Sanctuary AI   │ Budget limit │ 2025-12 │
│ ... (DataTable with mouse/keyboard nav)     │
├─────────────────────────────────────────────┤
│ [Failure Details Panel] (selected row)      │
│ Company: Boston Dynamics                    │
│ Occurred: 2025-12-07 14:32:15               │
│ Reason: Request timeout (30s)               │
│ Markdown: data/firecrawl_cache/boston.md    │
│                                             │
│ [View Markdown] [Retry] [Skip]              │
└─────────────────────────────────────────────┘
Footer: ↑↓: Navigate | Enter: Details | r: Retry | s: Skip | a: Retry All | q: Back
```

**Key Widgets**:
- `DataTable` - Sortable, filterable failure list
- `FailureDetailPanel` - Show details for selected row
- `Button` widgets for actions
- `Static` widget for markdown preview

**Reactive Behavior**:
- Row selection → Update detail panel
- Filter by review_action (pending/retry/skip)
- Real-time updates when actions are performed

#### 3. Metrics Screen (LLM vs Regex comparison) - Issue #118
**Purpose**: Display metrics comparing LLM and Regex extraction

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Extraction Metrics Dashboard                │
├─────────────────────────────────────────────┤
│ [Overview Stats]                            │
│ Total Extractions: 150                      │
│ LLM Success: 95 (63%)                       │
│ Regex Success: 120 (80%)                    │
│ LLM-Only Jobs: 25 (17%)                     │
├─────────────────────────────────────────────┤
│ [Comparison Table]                          │
│ Company        │ LLM  │ Regex │ Overlap      │
│────────────────┼──────┼───────┼──────────────│
│ Boston Dynamic │ 9    │ 0     │ 0            │
│ Figure         │ 12   │ 8     │ 8            │
│ ... (DataTable)                             │
├─────────────────────────────────────────────┤
│ [Charts/Sparklines]                         │
│ Success Rate Over Time: ▁▂▃▅▇█              │
└─────────────────────────────────────────────┘
Footer: d: Dashboard | f: Failures | ↑↓: Navigate | q: Back
```

**Note**: Metrics screen is part of Issue #118, but should be designed now for architecture consistency.

---

## 4. Migration Plan & Checklist

### Phase 1: Core Framework Setup (4-6 hours)

**Goal**: Establish Textual app structure and basic navigation

- [ ] **Install Textual**: Add `textual>=0.47.0` to `requirements.txt`
- [ ] **Create directory structure**: `src/tui/` with subdirectories
- [ ] **Create main app** (`src/tui/app.py`):
  - [ ] Define `JobAgentApp(App)` class
  - [ ] Set up CSS binding
  - [ ] Implement screen switching (d/f/m keys)
  - [ ] Add header/footer widgets
- [ ] **Create base screens**:
  - [ ] `DashboardScreen` (stub)
  - [ ] `FailuresScreen` (stub)
  - [ ] `MetricsScreen` (stub with placeholder)
- [ ] **Test navigation**: Verify screen switching works
- [ ] **Create `styles.css`**: Basic theme (dark colors, borders)

**Deliverable**: Working Textual app with 3 stub screens and keyboard navigation

---

### Phase 2: Failures Screen Implementation (6-8 hours) **PRIMARY FOCUS**

**Goal**: Fully implement LLM failure review interface

- [ ] **Create `FailureTable` widget**:
  - [ ] Extend `DataTable` with failure data
  - [ ] Add columns: #, Company, Reason, Date
  - [ ] Load data from `JobDatabase.get_llm_failures()`
  - [ ] Handle row selection event
- [ ] **Create `FailureDetailPanel` widget**:
  - [ ] Display selected failure details
  - [ ] Reactive to row selection
  - [ ] Show markdown path, error details
- [ ] **Implement actions**:
  - [ ] View markdown (Static widget with scrolling)
  - [ ] Retry single failure (`db.update_llm_failure(id, "retry")`)
  - [ ] Skip single failure (`db.update_llm_failure(id, "skip")`)
  - [ ] Retry all pending (with confirmation dialog)
  - [ ] Skip all pending (with confirmation dialog)
- [ ] **Add filtering**:
  - [ ] Filter by review_action (pending/retry/skip)
  - [ ] Search by company name
- [ ] **Keyboard shortcuts**:
  - [ ] `↑↓`: Navigate rows
  - [ ] `Enter`: Show details
  - [ ] `r`: Retry selected
  - [ ] `s`: Skip selected
  - [ ] `a`: Retry all
  - [ ] `q`: Back to dashboard
- [ ] **Write tests**:
  - [ ] Test data loading
  - [ ] Test row selection
  - [ ] Test retry/skip actions
  - [ ] Test filtering

**Deliverable**: Fully functional failures screen with mouse/keyboard support

---

### Phase 3: Dashboard Screen Migration (4-6 hours)

**Goal**: Migrate current TUI workflow to Textual dashboard

- [ ] **Create custom widgets**:
  - [ ] `ProfileSelector` widget (from `utils/profile_manager`)
  - [ ] `SourceSelector` widget (checkboxes for Email/Robotics/Companies)
  - [ ] `ScoringPanel` widget (reactive to profile selection)
  - [ ] `ActionSelector` widget (radio buttons)
  - [ ] `DigestOptions` widget (conditional visibility)
- [ ] **Implement reactive behavior**:
  - [ ] Profile selection → Update scoring panel
  - [ ] Source selection → Show/hide LLM extraction option
  - [ ] Action selection → Show/hide digest options
- [ ] **Add confirmation dialog**:
  - [ ] Show summary before execution
  - [ ] Confirm/Cancel buttons
- [ ] **Implement execution logic**:
  - [ ] Call `run_scraper()` with selected options
  - [ ] Call `send_digest()` with digest options
  - [ ] Show progress/spinner during execution
  - [ ] Display results (success/error messages)
- [ ] **Write tests**:
  - [ ] Test widget interactions
  - [ ] Test reactive updates
  - [ ] Test execution flow (mock subprocess calls)

**Deliverable**: Fully functional dashboard screen matching current TUI features

---

### Phase 4: Metrics Screen Implementation (4-6 hours) **FOR ISSUE #118**

**Goal**: Add metrics visualization (Part of Issue #118)

- [ ] **Create `MetricsTable` widget**:
  - [ ] Load comparison data from database
  - [ ] Columns: Company, LLM Jobs, Regex Jobs, Overlap, LLM-Only
  - [ ] Sortable by columns
- [ ] **Create `MetricsStatsPanel` widget**:
  - [ ] Display overview statistics
  - [ ] Total extractions, success rates
  - [ ] LLM-only job count
- [ ] **Add visualizations**:
  - [ ] Sparklines for trends (optional)
  - [ ] Bar charts for comparison (if feasible in terminal)
- [ ] **Write tests**:
  - [ ] Test data loading
  - [ ] Test calculations
  - [ ] Test sorting

**Deliverable**: Metrics screen (completes Issue #118)

---

### Phase 5: Documentation & Deprecation (2-3 hours)

**Goal**: Update docs and deprecate old TUI

- [ ] **Update `run-tui.sh`**:
  - [ ] Point to new `src/tui/app.py`
  - [ ] Add `--dev` flag option for development
- [ ] **Deprecate old TUI**:
  - [ ] Rename `src/tui.py` → `src/tui_legacy.py`
  - [ ] Add deprecation notice at top of file
  - [ ] Update imports if needed
- [ ] **Update documentation**:
  - [ ] Update `CLAUDE.md` with new TUI info
  - [ ] Add usage instructions for new screens
  - [ ] Document keyboard shortcuts
- [ ] **Create user guide**:
  - [ ] `docs/user-guide/TUI_GUIDE.md`
  - [ ] Screenshots (textual-web for capture)
  - [ ] Common workflows
- [ ] **Update tests**:
  - [ ] Remove old TUI test coverage exclusions
  - [ ] Ensure 80%+ coverage for new screens

**Deliverable**: Complete migration with updated docs

---

## 5. Testing Strategy

### Unit Tests (`tests/unit/test_tui/`)
- Test widget data loading
- Test reactive attribute updates
- Test action handlers (mock database calls)
- Test screen navigation

### Integration Tests
- Test full workflow (select profile → run scraper → send digest)
- Test failure review workflow (select failure → retry → verify database update)

### Manual Testing
- Use `textual run --dev src/tui/app.py` for live testing
- Test keyboard navigation (↑↓, Enter, shortcuts)
- Test mouse interactions (clicks, scrolling)
- Test on different terminal sizes

### Coverage Goal
- **80%+ coverage** for all new TUI code
- No coverage exclusions needed (unlike old Rich TUI)

---

## 6. Dependencies

### Required
- `textual>=0.47.0` - TUI framework

### Optional (for enhanced UX)
- `textual-plotext` - For charts/plots in metrics screen
- `rich-pixels` - For image rendering (if needed)

### Development
- `textual-dev` - Development tools (included with textual)

---

## 7. Success Criteria

✅ All three screens fully implemented
✅ Mouse support for all interactions
✅ Keyboard navigation (arrow keys, shortcuts)
✅ Visual feedback (highlighting, selection)
✅ Footer auto-generating shortcuts
✅ 80%+ test coverage
✅ Updated documentation
✅ Old TUI deprecated
✅ No loss of functionality from current TUI

---

## 8. Risk Assessment

### Low Risk
- ✅ Textual is mature (v0.47.0+, active development)
- ✅ Good documentation and community support
- ✅ Clear migration path from Rich

### Medium Risk
- ⚠️ Learning curve for Textual reactive programming
- ⚠️ CSS styling may require iteration
- ⚠️ Time estimate may be optimistic (20-29 hours)

### Mitigation
- Start with Failures screen (simplest, most valuable)
- Incremental development (one screen at a time)
- Keep old TUI as fallback (`tui_legacy.py`)

---

## 9. Next Steps

1. **Approve this plan** - Review and confirm approach
2. **Create feature branch** - `git checkout -b feature/textual-tui-migration-issue-119`
3. **Start Phase 1** - Core framework setup
4. **Iterate** - Complete phases 2-5 sequentially
5. **Create PR** - When all phases complete

---

## References

- [Textual Official Documentation](https://textual.textualize.io/)
- [Python Textual: Build Beautiful UIs in the Terminal](https://realpython.com/python-textual/)
- [7 Things I've learned building a modern TUI Framework](https://www.textualize.io/blog/7-things-ive-learned-building-a-modern-tui-framework/)
- [Textual: The Definitive Guide - Part 1](https://dev.to/wiseai/textual-the-definitive-guide-part-1-1i0p)
- Issue #119: https://github.com/adamkwhite/job-agent/issues/119
- Issue #118: TUI Metrics Dashboard (depends on this migration)
