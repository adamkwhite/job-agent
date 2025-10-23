.PHONY: help install install-dev test lint format typecheck clean security pre-commit all run-pipeline

# Python venv
VENV := job-agent-venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

# Default target - show help
help:
	@echo "Job Agent - Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Format code with ruff"
	@echo "  make typecheck     - Run mypy type checker"
	@echo "  make security      - Run security scans (bandit + safety)"
	@echo "  make pre-commit    - Run pre-commit hooks on all files"
	@echo "  make all           - Run lint, typecheck, and test"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run tests with coverage"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Remove cache and build artifacts"
	@echo ""
	@echo "Run Pipeline:"
	@echo "  make run-pipeline  - Run full job processing pipeline"

# Install production dependencies
install:
	$(PIP) install -r requirements.txt

# Install development dependencies
install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install

# Run tests with coverage
test:
	@if find tests/ -name "test_*.py" -type f | grep -q .; then \
		$(PYTEST) tests/ -v \
			--cov=src \
			--cov-report=term-missing:skip-covered \
			--cov-report=html \
			--cov-report=xml \
			--html=test-report.html \
			--self-contained-html; \
	else \
		echo "⚠️  No test files found in tests/ directory"; \
		echo "Tests need to be written for this project"; \
		exit 1; \
	fi

# Run linter
lint:
	$(VENV)/bin/ruff check .

# Format code
format:
	$(VENV)/bin/ruff format .

# Run type checker
typecheck:
	$(VENV)/bin/mypy src/ --config-file=pyproject.toml

# Run security scans
security:
	@echo "Running Bandit security scan..."
	@$(VENV)/bin/bandit -r src/ -c pyproject.toml || true
	@echo ""
	@echo "Running Safety dependency check..."
	@$(VENV)/bin/safety check --file requirements.txt || true

# Run pre-commit hooks on all files
pre-commit:
	$(VENV)/bin/pre-commit run --all-files

# Clean up cache and build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml test-report.html
	rm -rf dist/ build/

# Run all checks (lint, typecheck, test)
all: lint typecheck
	@echo ""
	@echo "✅ All quality checks passed!"
	@echo ""
	@echo "⚠️  Note: Tests not yet implemented for this project"

# Run the full job processing pipeline
run-pipeline:
	@echo "Running job agent master pipeline..."
	$(PYTHON) src/processor_master.py
