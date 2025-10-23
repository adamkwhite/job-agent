# Quality Infrastructure Setup Guide

This guide walks through setting up the quality gates for the job-agent project.

## Overview

The quality infrastructure includes:
- **Pre-commit hooks** - Local quality checks before committing
- **GitHub Actions CI/CD** - Automated testing, linting, and type checking
- **SonarCloud** - Code quality and security analysis
- **Security scanning** - Bandit, Safety, and Gitleaks

## Prerequisites

- Python 3.12+
- Git
- GitHub account with admin access to repository
- SonarCloud account (free for public repositories)

---

## Local Development Setup

### 1. Install Development Dependencies

```bash
make install-dev
```

This will:
- Install all development tools (pytest, ruff, mypy, pre-commit, bandit, safety)
- Install pre-commit hooks in your local repository

### 2. Available Make Commands

```bash
make help          # Show all available commands
make lint          # Run ruff linter
make format        # Format code with ruff
make typecheck     # Run mypy type checker
make security      # Run security scans
make pre-commit    # Run all pre-commit hooks
make test          # Run tests with coverage (when tests exist)
make all           # Run lint, typecheck, and test
make clean         # Remove cache and build artifacts
```

### 3. Pre-commit Hooks

Pre-commit hooks run automatically before each commit. They check:
- Code formatting (ruff)
- Linting (ruff)
- Type checking (mypy)
- Security issues (bandit high-severity only)
- Dependency vulnerabilities (safety)
- File issues (trailing whitespace, merge conflicts, etc.)
- Commit message format (conventional commits)

**Skip hooks temporarily:**
```bash
SKIP=mypy git commit -m "fix: temporary commit"
```

**Run hooks manually:**
```bash
make pre-commit
```

---

## GitHub Actions CI/CD Setup

### 1. CI Workflow (.github/workflows/ci.yml)

Runs on every push and pull request:
- **Linting** with ruff
- **Type checking** with mypy
- **Tests** with pytest and coverage reporting (when tests exist)

### 2. Security Workflow (.github/workflows/security.yml)

Runs on push, pull request, weekly schedule, and manual trigger:
- **SonarCloud** analysis with coverage
- **Bandit** security scanning
- **Safety** dependency vulnerability checking
- **Gitleaks** secret scanning

### 3. Artifacts

Both workflows upload artifacts:
- Coverage reports (HTML)
- Test reports (HTML)
- Security scan results (JSON)

Access artifacts in GitHub Actions > Workflow run > Artifacts section.

---

## SonarCloud Setup

### 1. Create SonarCloud Account

1. Go to https://sonarcloud.io
2. Sign in with GitHub
3. Allow SonarCloud access to your repositories

### 2. Import Repository

1. Click "+" in top right > "Analyze new project"
2. Select `adamkwhite/job-agent`
3. Click "Set Up"

### 3. Get SonarCloud Token

1. Go to https://sonarcloud.io/account/security
2. Generate a token named "job-agent-github-actions"
3. Copy the token (you'll need it for GitHub secrets)

### 4. Configure GitHub Secrets

1. Go to repository Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `SONAR_TOKEN` | `<your token>` | SonarCloud authentication token |
| `CODECOV_TOKEN` | `<codecov token>` | Codecov upload token (optional) |

### 5. Verify SonarCloud Configuration

The project is pre-configured with `sonar-project.properties`:

```properties
sonar.projectKey=adamkwhite_job-agent
sonar.organization=adamkwhite
sonar.sources=src
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
```

**Update if needed:**
- Change `sonar.projectKey` if SonarCloud generates a different key
- Change `sonar.organization` to your SonarCloud organization

### 6. First SonarCloud Scan

After merging this PR:
1. Go to https://sonarcloud.io/dashboard?id=adamkwhite_job-agent
2. Check the quality gate status
3. Review any bugs, vulnerabilities, code smells, or security hotspots

---

## Quality Gates

### Pre-commit (Local)

✅ **Pass criteria:**
- Code formatted with ruff
- No high-severity linting errors
- Type checking passes (with `--ignore-missing-imports`)
- No high-severity security issues

### CI Workflow (GitHub Actions)

✅ **Pass criteria:**
- All linting checks pass
- Type checking passes
- Tests pass (when tests exist)
- Coverage meets threshold (currently 0%, will increase as tests are added)

### Security Workflow (GitHub Actions)

✅ **Pass criteria:**
- No high-severity Bandit security issues
- No vulnerable dependencies (Safety)
- No hardcoded secrets (Gitleaks)

❌ **Fail criteria:**
- High-severity security issues found
- Vulnerable dependencies detected
- Hardcoded secrets detected

### SonarCloud (Integrated)

✅ **Pass criteria:**
- Quality gate passed
- No new bugs introduced
- No new vulnerabilities introduced
- Code coverage maintained or improved

---

## Troubleshooting

### Pre-commit Hook Failures

**Problem:** `ruff` format check fails

```bash
make format
git add .
git commit -m "fix: format code"
```

**Problem:** `mypy` type check fails

```bash
SKIP=mypy git commit -m "fix: skip mypy temporarily"
```

Then fix type issues and commit again.

**Problem:** Commit message format invalid

Follow conventional commit format:
```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(scoring): add location-aware job scoring

Added 15-point location scoring component for remote and Ontario jobs.
```

### CI/CD Failures

**Problem:** Tests fail but no tests exist

Expected - tests need to be written. CI workflow skips test execution gracefully.

**Problem:** Linting fails on PR

Run locally:
```bash
make lint
make format
git add .
git commit -m "fix: address linting issues"
git push
```

**Problem:** Security scan fails

Check artifacts for detailed report:
1. Go to failed workflow run
2. Download "bandit-security-report" or "safety-dependency-report"
3. Review and fix issues
4. Re-run workflow

### SonarCloud Failures

**Problem:** Quality gate failed

1. Go to SonarCloud dashboard
2. Review "New Code" tab for issues introduced
3. Fix bugs, vulnerabilities, or code smells
4. Commit and push

**Problem:** Coverage decreased

Add tests to cover new code. Run locally:
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Next Steps

After setting up quality infrastructure:

1. **Add Tests** - Write unit tests for job scoring, parsers, and scrapers
   - Target: 80% code coverage
   - Use pytest with pytest-mock for mocking

2. **Configure SonarCloud Quality Profile** - Adjust rules for Python best practices
   - Enable additional security rules
   - Set coverage threshold to 80%

3. **Enable Branch Protection** - Require status checks before merging
   - Require CI workflow to pass
   - Require Security workflow to pass
   - Require SonarCloud quality gate to pass

4. **Monitor Quality Metrics** - Track quality trends over time
   - Review SonarCloud dashboard weekly
   - Address security vulnerabilities promptly
   - Maintain or improve code coverage

---

## Resources

- **Ruff**: https://docs.astral.sh/ruff/
- **mypy**: https://mypy.readthedocs.io/
- **pytest**: https://docs.pytest.org/
- **pre-commit**: https://pre-commit.com/
- **SonarCloud**: https://docs.sonarcloud.io/
- **Bandit**: https://bandit.readthedocs.io/
- **Safety**: https://safetycli.com/
