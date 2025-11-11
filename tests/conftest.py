"""
Pytest configuration for job-agent tests.

This conftest.py adds the project root to sys.path to ensure
that tests can import from the src package correctly.
"""

import sys
from pathlib import Path

# Add project root to Python path so tests can import src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
