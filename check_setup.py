import sys
import os

print("Python version:", sys.version)
print("Python path:", sys.executable)
print("Current directory:", os.getcwd())
print("\nChecking imports:")

try:
    import cv2
    print("✓ OpenCV imported")
except ImportError:
    print("✗ OpenCV not found")

try:
    import torch
    print("✓ PyTorch imported")
except ImportError:
    print("✗ PyTorch not found")

try:
    import PyQt5
    print("✓ PyQt5 imported")
except ImportError:
    print("✗ PyQt5 not found")

print("\nChecking project structure:")
for folder in ['models', 'views', 'controllers', 'dal', 'utils', 'tests']:
    if os.path.exists(folder):
        print(f"✓ {folder}/ exists")
    else:
        print(f"✗ {folder}/ not found")