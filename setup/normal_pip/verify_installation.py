# verify_installation.py
"""
Quick verification script to check if all dependencies are working
Run this after installing requirements.txt
"""

import sys
import importlib
import platform
from pathlib import Path

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name or module_name}")
        return True
    except ImportError as e:
        print(f"❌ {package_name or module_name}: {e}")
        return False

def check_versions():
    """Check versions of critical packages"""
    print("\n📋 Package Versions:")
    print("-" * 30)
    
    packages = [
        ('cv2', 'OpenCV'),
        ('PyQt5', 'PyQt5'),
        ('torch', 'PyTorch'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('numpy', 'NumPy'),
        ('ultralytics', 'Ultralytics')
    ]
    
    for module, name in packages:
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, '__version__', 'Unknown')
            print(f"  {name}: {version}")
        except ImportError:
            print(f"  {name}: Not installed")

def check_system_info():
    """Display system information"""
    print("🖥️  System Information:")
    print("-" * 30)
    print(f"  Platform: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version}")
    print(f"  Architecture: {platform.architecture()[0]}")

def check_gpu_support():
    """Check if GPU support is available"""
    print("\n🎮 GPU Support:")
    print("-" * 30)
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✅ CUDA available: {torch.cuda.device_count()} GPU(s)")
            for i in range(torch.cuda.device_count()):
                print(f"    GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("  ⚠️  CUDA not available (CPU only)")
    except ImportError:
        print("  ❌ PyTorch not installed")

def check_project_structure():
    """Check if project structure exists"""
    print("\n📁 Project Structure:")
    print("-" * 30)
    
    required_dirs = [
        "dal", "models", "views", "controllers", 
        "utils", "tests", "logs"
    ]
    
    for directory in required_dirs:
        path = Path(directory)
        if path.exists():
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ {directory}/ (missing)")

def check_config_files():
    """Check if configuration files exist"""
    print("\n⚙️  Configuration Files:")
    print("-" * 30)
    
    config_files = [
        "config.json",
        "requirements.txt"
    ]
    
    for file_name in config_files:
        path = Path(file_name)
        if path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} (missing)")

def test_critical_functionality():
    """Test critical functionality"""
    print("\n🧪 Functionality Tests:")
    print("-" * 30)
    
    # Test OpenCV
    try:
        import cv2
        import numpy as np
        # Create a simple test image
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.circle(test_img, (50, 50), 20, (255, 255, 255), -1)
        print("  ✅ OpenCV basic operations work")
    except Exception as e:
        print(f"  ❌ OpenCV test failed: {e}")
    
    # Test PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication([])
        print("  ✅ PyQt5 GUI framework works")
        app.quit()
    except Exception as e:
        print(f"  ❌ PyQt5 test failed: {e}")
    
    # Test database
    try:
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///:memory:")
        print("  ✅ SQLAlchemy database works")
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
    
    # Test YOLO model loading
    try:
        from ultralytics import YOLO
        # This will download the model if not present
        model = YOLO('yolov8n.pt')
        print("  ✅ YOLO model loading works")
    except Exception as e:
        print(f"  ⚠️  YOLO model test: {e}")

def main():
    """Main verification function"""
    print("🔍 Traffic Monitoring System - Installation Verification")
    print("=" * 60)
    
    # System info
    check_system_info()
    
    # Check imports
    print("\n📦 Package Imports:")
    print("-" * 30)
    
    critical_packages = [
        ('cv2', 'OpenCV'),
        ('PyQt5', 'PyQt5'),
        ('PyQt5.QtWidgets', 'PyQt5 Widgets'),
        ('torch', 'PyTorch'),
        ('torchvision', 'TorchVision'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('numpy', 'NumPy'),
        ('PIL', 'Pillow'),
        ('matplotlib', 'Matplotlib'),
        ('scipy', 'SciPy'),
        ('ultralytics', 'Ultralytics'),
        ('pandas', 'Pandas'),
        ('yaml', 'PyYAML'),
        ('pytest', 'Pytest (optional)')
    ]
    
    success_count = 0
    for module, name in critical_packages:
        if check_import(module, name):
            success_count += 1
    
    # Check versions
    check_versions()
    
    # Check GPU support
    check_gpu_support()
    
    # Check project structure
    check_project_structure()
    
    # Check config files
    check_config_files()
    
    # Test functionality
    test_critical_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    total_packages = len(critical_packages)
    success_rate = (success_count / total_packages) * 100
    
    print(f"Package imports: {success_count}/{total_packages} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 Excellent! All critical components are working.")
        print("\nYou can now run the application:")
        print("  python main_application.py")
    elif success_rate >= 70:
        print("⚠️  Most components work, but some issues detected.")
        print("Check the failed imports above and reinstall if needed.")
    else:
        print("❌ Many components are missing or broken.")
        print("Please reinstall using: pip install -r requirements.txt")
    
    print("\nIf you encounter issues:")
    print("1. Make sure you're in the virtual environment")
    print("2. Try: pip install --upgrade pip")
    print("3. Try: pip install -r requirements.txt --force-reinstall")

if __name__ == "__main__":
    main()