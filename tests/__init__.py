# tests/__init__.py
"""
Unit tests for Traffic Monitoring System
"""
import sys
from pathlib import Path

# Add parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import test modules only when needed to avoid circular imports