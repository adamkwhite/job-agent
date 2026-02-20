# Cognitive Complexity Guidelines

**Target: Keep all functions ≤15 complexity**

SonarCloud enforces a cognitive complexity limit of 15 for all functions. This document provides practical guidance for writing low-complexity code from the start and refactoring when needed.

---

## Why Cognitive Complexity Matters

**Cognitive complexity measures how hard code is to understand**, not just how many lines it has.

High complexity indicates:
- ❌ Hard to understand logic flow
- ❌ Difficult to test thoroughly
- ❌ High bug risk when modifying
- ❌ Slow code review process

Low complexity provides:
- ✅ Clear, readable code
- ✅ Easy to test and maintain
- ✅ Fast onboarding for new developers
- ✅ Confident refactoring

---

## Red Flags While Writing Code

**Stop and extract when you see:**

| Red Flag | Complexity Impact | Solution |
|----------|------------------|----------|
| Function >50 lines | +5-10 per section | Extract logical chunks |
| Nested loops (`for` inside `for`) | +3 per level | Extract inner loop |
| 3+ levels of indentation | +2 per level | Extract nested blocks |
| Multiple `if/elif` chains | +1 per branch | Extract validation/dispatch |
| Multiple distinct concerns | +5-15 total | One concern per function |
| Long boolean conditions | +2-4 per condition | Extract to named predicates |

**Example - Red Flags in Action:**

```python
# ❌ Multiple red flags (complexity ~19)
def process_data(data):
    results = []
    for item in data:  # Loop +1
        if item.type == "email":  # Branch +1
            if item.html:  # Nested branch +2
                soup = BeautifulSoup(item.html)
                for link in soup.find_all("a"):  # Nested loop +3
                    if "job" in link.href:  # Branch in loop +2
                        # ... 20 more lines of extraction
                        results.append(job)
            else:  # Branch +1
                # ... 15 lines of text parsing
        elif item.type == "web":  # Branch +1
            # ... another 30 lines
    return results

# ✅ Extracted helpers (complexity ~5)
def process_data(data):
    results = []
    for item in data:
        if item.type == "email":
            results.extend(self._process_email(item))
        elif item.type == "web":
            results.extend(self._process_web(item))
    return results
```

---

## The Extract-Method Pattern

**When complexity builds, follow this pattern:**

### Step 1: Identify Logical Chunks

Ask: "Can I name distinct sections of this function?"

```python
# If you can mentally divide it like this:
def init_database(self):
    # Create jobs table (30 lines)
    # Create failures table (25 lines)
    # Create metrics table (20 lines)
    # Apply migrations (40 lines)
    # Create indexes (15 lines)
```

### Step 2: Name the Concerns

Each chunk gets a descriptive method name:

```python
self._create_jobs_table()
self._create_failures_table()
self._create_metrics_table()
self._apply_migrations()
self._create_indexes()
```

### Step 3: Extract to Helper Methods

Move each chunk to a focused helper:

```python
def _create_jobs_table(self, cursor) -> None:
    """Create jobs table with all columns and basic indexes"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            # ... 30 lines of table definition
        )
    """)
```

### Step 4: Main Function Becomes Orchestration

The original function now just coordinates:

```python
def init_database(self):
    """Create database schema if it doesn't exist"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    self._create_jobs_table(cursor)
    self._create_failures_table(cursor)
    self._create_metrics_table(cursor)
    self._apply_migrations(cursor)
    self._create_indexes(cursor)

    conn.commit()
    conn.close()
```

**Result**: Complexity 17→5, readability dramatically improved.

---

## Real Examples from Issue #294

### Example 1: Database Initialization

**Problem**: 182-line function with 4 table creations + 4 migrations + indexing (complexity 17)

**Solution**: Extract one method per table + migrations
- `_create_jobs_table()` - Jobs table creation
- `_create_llm_failures_table()` - LLM tracking table
- `_create_extraction_metrics_table()` - Metrics table
- `_create_job_scores_table()` - Multi-profile scores
- `_migrate_scoring_columns()` - Backward compatibility
- `_create_jobs_indexes()` - Performance indexes

**Result**: 182→24 lines, complexity 17→5

### Example 2: Multi-Format Parsing

**Problem**: 73-line function parsing both HTML and text formats (complexity 19)

**Solution**: Extract by format type
- `_extract_html_opportunities()` - Parse HTML with BeautifulSoup
- `_extract_text_opportunities()` - Fallback regex URL extraction

**Result**: 73→18 lines, complexity 19→8

### Example 3: Job Field Extraction

**Problem**: 95-line function with URL parsing + basic info + field extraction (complexity 19)

**Solution**: Extract by extraction phase
- `_extract_job_url_and_content()` - Parse URL from markdown
- `_extract_basic_job_info()` - Extract company, date, title
- `_extract_job_fields()` - Extract location, salary, remote status, tags

**Result**: 95→30 lines, complexity 19→10

---

## Type Safety from the Start

**Use precise types to avoid mypy errors during refactoring:**

### ❌ Avoid Union Types for Structured Returns

```python
# ❌ mypy can't determine specific field types
def _extract_fields(self, content: str) -> dict[str, str | list[str]]:
    return {
        "location": "Remote",      # str
        "salary": "$100k",         # str
        "tech_tags": ["Python"]    # list[str]
    }

# Accessing fields causes type errors:
fields = self._extract_fields(content)
job = Job(location=fields["location"])  # Error: str | list[str] incompatible with str
```

### ✅ Use TypedDict for Precise Field Types

```python
from typing import TypedDict

class JobFields(TypedDict):
    """Type definition for extracted job fields"""
    location: str
    salary: str
    remote_status: str
    job_type: str
    tech_tags: list[str]

def _extract_fields(self, content: str) -> JobFields:
    return {
        "location": "Remote",
        "salary": "$100k",
        "remote_status": "Fully Remote",
        "job_type": "Full Time",
        "tech_tags": ["Python", "Django"]
    }

# mypy knows exact types for each field
fields = self._extract_fields(content)
job = Job(location=fields["location"])  # ✅ Type-safe
```

### ✅ Annotate Empty Collections

```python
# ❌ mypy can't infer type
opportunities = []

# ✅ Explicit type annotation
opportunities: list[OpportunityData] = []
```

---

## Common Complexity Patterns & Solutions

| Pattern | Typical Complexity | Extract Strategy |
|---------|-------------------|------------------|
| **Database setup** | 15-20 | One method per table + migrations |
| **Multi-format parsing** | 15-20 | One method per format (HTML, text, JSON) |
| **Field extraction** | 10-15 | One method per extraction phase |
| **Validation chains** | 10-15 | Extract predicate methods |
| **Nested conditionals** | 10-20 | Extract decision logic |
| **Loop + conditionals** | 8-15 | Extract loop body to method |

---

## Prevention Checklist

**Before writing a new function, ask:**

- [ ] Can I name 3+ distinct sections? → Extract from the start
- [ ] Will this parse multiple formats? → One method per format
- [ ] Am I doing validation + transformation? → Separate concerns
- [ ] Will there be nested loops? → Extract inner loop
- [ ] Does this have multiple `if/elif` branches? → Extract dispatch logic

**While writing code, stop when:**

- [ ] Function exceeds 50 lines
- [ ] Indentation reaches 4+ levels
- [ ] You add a 3rd nested loop or conditional
- [ ] You can't easily describe what the function does in one sentence

**During code review, refactor if:**

- [ ] Radon reports complexity >15
- [ ] Reviewer asks "What does this section do?"
- [ ] You hesitate when explaining the logic flow
- [ ] Tests require complex setup to cover all paths

---

## Integration with Workflow

### 1. **During Development**

Before committing, check complexity of modified functions:

```bash
# Check specific file
radon cc src/database.py -s -a

# Check all modified files
git diff --name-only main | grep "\.py$" | xargs radon cc -s
```

### 2. **Pre-Commit Hook**

Pre-commit hooks will catch complexity >15:

```bash
# If complexity check fails, extract methods before committing
# Or skip if pre-existing: SKIP=check-complexity git commit
```

### 3. **Code Review**

Use `/pragmatic-code-review` which includes complexity checking:

```bash
# AI will flag functions >15 and suggest extractions
```

### 4. **Maintenance**

Monthly complexity audits identify technical debt:

```bash
# Find top 10 most complex functions
radon cc src/ -s -n D | head -20

# Files with average complexity >10
radon cc src/ -a --total-average | grep -E "Average.*[1-9][0-9]\."
```

---

## Summary: The 50-Line Rule

**Simple heuristic: No function should exceed 50 lines.**

- If you can't fit it on one screen, it's doing too much
- 50 lines usually means 3-5 logical chunks
- Extracting keeps complexity ≤15 naturally

**When you hit 50 lines:**
1. Stop coding
2. Identify logical chunks
3. Name each chunk
4. Extract to helper methods
5. Continue with low complexity

This preventive approach is faster than fixing complexity violations later.

---

## Reference: Complexity Calculation

**Cognitive complexity adds points for:**

- `if`, `elif`, `else` statements: +1 each
- `for`, `while` loops: +1 each
- `and`, `or` in conditions: +1 per operator
- Nested structures: +1 per nesting level
- `try/except` blocks: +1
- Recursion: +1

**Example:**

```python
def example(items):           # Base: 0
    for item in items:        # +1 (loop)
        if item.valid:        # +2 (nested if)
            if item.ready:    # +3 (double nested)
                process(item)
            else:             # +2 (nested else)
                skip(item)
    return results            # Total: 8
```

**After extraction:**

```python
def example(items):           # Base: 0
    for item in items:        # +1 (loop)
        self._process_item(item)
    return results            # Total: 1

def _process_item(self, item): # Base: 0
    if item.valid:            # +1
        if item.ready:        # +2 (nested)
            process(item)
        else:                 # +1
            skip(item)
                              # Total: 4
```

Both functions now under limit (1 and 4 vs. original 8).

---

## Questions?

If you're unsure whether to extract:

1. **Check the score**: `radon cc file.py -s`
2. **Ask during code review**: Tag for AI review
3. **Err on the side of extraction**: Easier to merge helpers later than split them

**Rule of thumb**: If you're asking "Should I extract?", the answer is usually yes.
