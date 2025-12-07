#!/bin/bash
# Interactive TUI for Job Agent Pipeline
# Allows selecting profiles, sources, and running jobs/digests

cd "$(dirname "$0")"
./job-agent-venv/bin/python src/tui.py
