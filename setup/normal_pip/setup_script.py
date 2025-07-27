# setup.py
"""
Automatic setup script for Traffic Monitoring System
Run this to automatically set up the entire project
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8+ is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def create_virtual_environment():
    """Create virtual environment if not exists"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    try:
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def get_pip_executable():
    """Get pip executable path for current platform"""
    if platform.system() == "Windows":
        return Path("venv/Scripts/pip.exe")
    else:
        return Path("venv/bin/pip")

def install_requirements():
    """Install requirements using pip"""
    pip_exe = get_pip_executable()
    
    if not pip_exe.exists():
        print("❌ Pip not found in virtual environment")
        return False
    
    try:
        print("📦 Installing requirements...")
        subprocess.run([
            str(pip_exe), "install", "-r", "requirements.txt"
        ], check=True)
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def create_project_structure():
    """Create necessary project directories"""
    directories = [
        "dal", "dal/models", "dal/migrations",
        "models", "models/entities", "models/components", "models/repositories",
        "views", "controllers", "utils", "tests", "logs", "data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py files
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.touch()
    
    print("✅ Project structure created")

def create_config_file():
    """Create default config.json"""
    config_content = """{
    "model_type": "yolov8n",
    "confidence_threshold": 0.5,
    "stop_time_threshold": 20.0,
    "virtual_line": {
        "start_point": [100, 300],
        "end_point": [500, 300],
        "direction": "horizontal"
    },
    "paths": {
        "model_path": "./models/yolov8n.pt",
        "log_path": "./logs/",
        "database_url": "sqlite:///traffic_monitoring.db"
    },
    "gui": {
        "window_width": 1400,
        "window_height": 900,
        "theme": "light"
    }
}"""
    
    config_file = Path("config.json")
    if not config_file.exists():
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✅ Default config.json created")

def test_installation():
    """Test if installation was successful"""
    pip_exe = get_pip_executable()
    
    try:
        # Test critical imports
        test_script = """
import sys
sys.path.insert(0, '.')

try:
    import cv2
    print("✅ OpenCV imported successfully")
except ImportError as e:
    print(f"❌ OpenCV import failed: {e}")

try:
    import PyQt5
    print("✅ PyQt5 imported successfully")
except ImportError as e:
    print(f"❌ PyQt5 import failed: {e}")

try:
    import torch
    print("✅ PyTorch imported successfully")
except ImportError as e:
    print(f"❌ PyTorch import failed: {e}")

try:
    import sqlalchemy
    print("✅ SQLAlchemy imported successfully")
except ImportError as e:
    print(f"❌ SQLAlchemy import failed: {e}")

try:
    from ultralytics import YOLO
    print("✅ Ultralytics imported successfully")
except ImportError as e:
    print(f"❌ Ultralytics import failed: {e}")
"""
        
        python_exe = get_pip_executable().parent / ("python.exe" if platform.system() == "Windows" else "python")
        result = subprocess.run([
            str(python_exe), "-c", test_script
        ], capture_output=True, text=True)
        
        print("\n" + "="*50)
        print("INSTALLATION TEST RESULTS")
        print("="*50)
        print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def print_next_steps():
    """Print instructions for next steps"""
    activate_cmd = "venv\\Scripts\\activate" if platform.system() == "Windows" else "source venv/bin/activate"
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    print(f"   {activate_cmd}")
    print("\n2. Run the application:")
    print("   python main_application.py")
    print("\n3. Or initialize the database first:")
    print("   python dal/migrations/init_db.py")
    print("\n4. Run tests to verify everything works:")
    print("   python -m unittest discover tests/")
    print("\nProject structure created with all necessary directories.")
    print("Default config.json created - you can modify settings as needed.")

def main():
    """Main setup function"""
    print("🚀 Traffic Monitoring System Setup")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create project structure
    create_project_structure()
    
    # Create config file
    create_config_file()
    
    # Test installation
    if test_installation():
        print_next_steps()
    else:
        print("\n❌ Some components failed to install properly.")
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()