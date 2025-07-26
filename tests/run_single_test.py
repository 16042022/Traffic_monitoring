# tests/run_single_test.py
"""
Simple script to run tests with proper path setup
"""
import sys
import os
from pathlib import Path

# Setup Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Print debug info
print(f"Python path: {sys.path[0]}")
print(f"Current directory: {os.getcwd()}")
print(f"Project root: {project_root}")

# Check if modules exist
print("\nChecking module structure:")
for module in ['dal', 'models', 'utils']:
    module_path = project_root / module
    if module_path.exists():
        print(f"✓ {module}/ exists")
        # Check for __init__.py
        init_file = module_path / '__init__.py'
        if init_file.exists():
            print(f"  ✓ {module}/__init__.py exists")
        else:
            print(f"  ✗ {module}/__init__.py missing")
    else:
        print(f"✗ {module}/ not found")

# Try imports
print("\nTesting imports:")
try:
    from dal.database import db_manager, Base
    print("✓ Successfully imported dal.database")
except ImportError as e:
    print(f"✗ Failed to import dal.database: {e}")

try:
    from models.components.vehicle_tracker import VehicleTracker
    print("✓ Successfully imported VehicleTracker")
except ImportError as e:
    print(f"✗ Failed to import VehicleTracker: {e}")

# Run a simple test
print("\nRunning a simple test...")
import unittest

# Import test after path is set up
from test_vehicle_tracker import TestVehicleTracker

# Run one test
suite = unittest.TestLoader().loadTestsFromTestCase(TestVehicleTracker)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)