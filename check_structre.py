# check_structure.py
"""
Script to check and fix project structure
Place this in your project root directory
"""
import os
from pathlib import Path

def check_and_create_init_files():
    """Check and create missing __init__.py files"""
    
    # Define required directories and their __init__.py content
    required_structure = {
        'dal': 'from .database import db_manager, Base',
        'dal/models': 'from .video import Video\nfrom .detection_event import DetectionEvent\nfrom .traffic_data import TrafficData\nfrom .anomaly_event import AnomalyEvent',
        'models': '',
        'models/entities': '',
        'models/components': '',
        'models/repositories': '',
        'views': '',
        'controllers': '',
        'utils': '',
        'tests': ''
    }
    
    current_dir = Path.cwd()
    print(f"Checking project structure in: {current_dir}")
    print("=" * 50)
    
    for dir_path, init_content in required_structure.items():
        full_path = current_dir / dir_path
        init_file = full_path / '__init__.py'
        
        # Check if directory exists
        if not full_path.exists():
            print(f"✗ Directory missing: {dir_path}/")
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  → Created directory: {dir_path}/")
        
        # Check if __init__.py exists
        if not init_file.exists():
            print(f"✗ Missing: {dir_path}/__init__.py")
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_content)
            print(f"  → Created: {dir_path}/__init__.py")
        else:
            print(f"✓ Found: {dir_path}/__init__.py")
    
    print("\n" + "=" * 50)
    print("Structure check complete!")
    
    # Additional check for key files
    print("\nChecking key files:")
    key_files = [
        'dal/database.py',
        'models/components/vehicle_tracker.py',
        'models/components/traffic_monitor.py',
        'models/components/anomaly_detector.py'
    ]
    
    for file_path in key_files:
        full_path = current_dir / file_path
        if full_path.exists():
            print(f"✓ Found: {file_path}")
        else:
            print(f"✗ Missing: {file_path}")

if __name__ == "__main__":
    check_and_create_init_files()
    
    print("\nTo run tests, use:")
    print("python -m pytest tests/  # if you have pytest")
    print("python -m unittest discover tests/  # with unittest")
    print("python tests/run_single_test.py  # to test setup")