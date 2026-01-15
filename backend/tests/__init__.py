"""
Tests Package
Unit, integration, and API tests
"""

import sys
from pathlib import Path

# Add backend to path for tests
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
