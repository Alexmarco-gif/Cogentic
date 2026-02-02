"""Pytest configuration for backend tests"""

import sys
from pathlib import Path

# Add project root to Python path so 'backend' module can be imported
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
