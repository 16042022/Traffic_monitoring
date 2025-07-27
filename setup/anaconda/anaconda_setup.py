# setup_anaconda.py
"""
Setup script specifically for Anaconda/Miniconda users
Handles conda environments and package management
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print("✅ Success!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def check_conda():
    """Check if conda is available"""
    try:
        result = subprocess.run("conda --version", shell=True, 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Conda found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Conda not found")
            return False
    except:
        print("❌ Conda not found")
        return False

def create_conda_environment():
    """Create conda environment for the project"""
    env_name = "traffic_monitoring"
    
    # Check if environment already exists
    result = subprocess.run(f"conda env list", shell=True, 
                          capture_output=True, text=True)
    
    if env_name in result.stdout:
        print(f"✅ Environment '{env_name}' already exists")
        return True
    
    # Create new environment with Python 3.9
    command = f"conda create -n {env_name} python=3.9 -y"
    return run_command(command, f"Creating conda environment '{env_name}'")

def install_conda_packages():
    """Install packages using conda"""
    env_name = "traffic_monitoring"
    
    # Core packages available in conda
    conda_packages = [
        "numpy=1.24.4",
        "scipy=1.10.1", 
        "matplotlib=3.7.2",
        "pandas=2.0.3",
        "pillow=10.0.1",
        "pyyaml=6.0.1",
        "requests=2.31.0",
        "tqdm=4.66.1",
        "psutil=5.9.5",
        "sqlalchemy=2.0.21",
        "pytest=7.4.2"
    ]
    
    # Install conda packages
    for package in conda_packages:
        command = f"conda install -n {env_name} {package} -y"
        if not run_command(command, f"Installing {package}"):
            print(f"⚠️  Failed to install {package}, will try with pip later")

def install_conda_forge_packages():
    """Install packages from conda-forge channel"""
    env_name = "traffic_monitoring"
    
    conda_forge_packages = [
        "opencv=4.8.1",
        "pytorch=2.0.1", 
        "torchvision=0.15.2",
        "cpuonly"  # Remove this if you want CUDA support
    ]
    
    for package in conda_forge_packages:
        command = f"conda install -n {env_name} -c conda-forge {package} -y"
        if not run_command(command, f"Installing {package} from conda-forge"):
            print(f"⚠️  Failed to install {package}")

def install_pip_packages():
    """Install remaining packages with pip in conda env"""
    env_name = "traffic_monitoring"
    
    # Get conda environment python path
    if platform.system() == "Windows":
        python_path = f"conda run -n {env_name} python"
        pip_path = f"conda run -n {env_name} pip"
    else:
        python_path = f"conda run -n {env_name} python"
        pip_path = f"conda run -n {env_name} pip"
    
    # Packages that need pip
    pip_packages = [
        "PyQt5==5.15.9",
        "ultralytics==8.0.196",
        "alembic==1.12.0", 
        "colorlog==6.7.0",
        "imageio==2.31.3",
        "imageio-ffmpeg==0.4.9",
        "pytest-cov==4.1.0"
    ]
    
    # Install pip packages
    for package in pip_packages:
        command = f"{pip_path} install {package}"
        run_command(command, f"Installing {package} with pip")

def create_environment_yml():
    """Create environment.yml file for easy reproduction"""
    
    yml_content = """name: traffic_monitoring
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - numpy=1.24.4
  - scipy=1.10.1
  - matplotlib=3.7.2
  - pandas=2.0.3
  - pillow=10.0.1
  - pyyaml=6.0.1
  - requests=2.31.0
  - tqdm=4.66.1
  - psutil=5.9.5
  - sqlalchemy=2.0.21
  - pytest=7.4.2
  - opencv=4.8.1
  - pytorch=2.0.1
  - torchvision=0.15.2
  - cpuonly  # Remove for CUDA support
  - pip
  - pip:
    - PyQt5==5.15.9
    - ultralytics==8.0.196
    - alembic==1.12.0
    - colorlog==6.7.0
    - imageio==2.31.3
    - imageio-ffmpeg==0.4.9
    - pytest-cov==4.1.0
"""
    
    with open("environment.yml", "w") as f:
        f.write(yml_content)
    
    print("✅ Created environment.yml file")

def test_installation():
    """Test the conda installation"""
    env_name = "traffic_monitoring"
    
    test_script = '''
import sys
print(f"Python: {sys.version}")

packages_to_test = [
    ("cv2", "OpenCV"),
    ("PyQt5", "PyQt5"), 
    ("torch", "PyTorch"),
    ("torchvision", "TorchVision"),
    ("sqlalchemy", "SQLAlchemy"),
    ("numpy", "NumPy"),
    ("ultralytics", "Ultralytics"),
    ("pandas", "Pandas"),
    ("matplotlib", "Matplotlib")
]

print("\\nTesting package imports:")
for module, name in packages_to_test:
    try:
        __import__(module)
        print(f"✅ {name}")
    except ImportError as e:
        print(f"❌ {name}: {e}")

# Test GPU support
try:
    import torch
    if torch.cuda.is_available():
        print(f"\\n🎮 CUDA available: {torch.cuda.device_count()} GPU(s)")
    else:
        print("\\n💻 CPU-only mode (no CUDA)")
except:
    print("\\n❌ PyTorch not working")
'''
    
    command = f"conda run -n {env_name} python -c \"{test_script}\""
    run_command(command, "Testing installation")

def create_batch_files():
    """Create convenient batch files for Windows users"""
    if platform.system() == "Windows":
        # Activation script
        activate_content = """@echo off
echo Activating traffic_monitoring environment...
call conda activate traffic_monitoring
echo Environment activated! You can now run:
echo   python main_application.py
echo   python verify_installation.py
cmd /k
"""
        with open("activate_env.bat", "w") as f:
            f.write(activate_content)
        
        # Run app script
        run_app_content = """@echo off
call conda activate traffic_monitoring
python main_application.py
pause
"""
        with open("run_app.bat", "w") as f:
            f.write(run_app_content)
        
        print("✅ Created Windows batch files:")
        print("  - activate_env.bat (activate environment)")
        print("  - run_app.bat (run application)")

def create_shell_scripts():
    """Create shell scripts for Linux/Mac users"""
    if platform.system() in ["Linux", "Darwin"]:
        # Activation script
        activate_content = """#!/bin/bash
echo "Activating traffic_monitoring environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate traffic_monitoring
echo "Environment activated! You can now run:"
echo "  python main_application.py"
echo "  python verify_installation.py"
bash
"""
        with open("activate_env.sh", "w") as f:
            f.write(activate_content)
        os.chmod("activate_env.sh", 0o755)
        
        # Run app script
        run_app_content = """#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate traffic_monitoring
python main_application.py
"""
        with open("run_app.sh", "w") as f:
            f.write(run_app_content)
        os.chmod("run_app.sh", 0o755)
        
        print("✅ Created shell scripts:")
        print("  - activate_env.sh (activate environment)")
        print("  - run_app.sh (run application)")

def print_final_instructions():
    """Print final usage instructions"""
    system = platform.system()
    
    print("\n" + "="*60)
    print("🎉 ANACONDA SETUP COMPLETED!")
    print("="*60)
    
    print("\n📖 How to use:")
    
    if system == "Windows":
        print("\nOption 1 - Use batch files:")
        print("  Double-click: activate_env.bat")
        print("  Double-click: run_app.bat")
        
        print("\nOption 2 - Command line:")
        print("  conda activate traffic_monitoring")
        print("  python main_application.py")
        
    else:
        print("\nOption 1 - Use shell scripts:")
        print("  ./activate_env.sh")
        print("  ./run_app.sh")
        
        print("\nOption 2 - Command line:")
        print("  conda activate traffic_monitoring")
        print("  python main_application.py")
    
    print("\n🔧 Useful commands:")
    print("  conda activate traffic_monitoring  # Activate environment")
    print("  conda deactivate                   # Deactivate environment")
    print("  conda env list                     # List environments")
    print("  conda list                         # List installed packages")
    
    print("\n📁 Files created:")
    print("  - environment.yml (reproducible environment)")
    if system == "Windows":
        print("  - activate_env.bat, run_app.bat")
    else:
        print("  - activate_env.sh, run_app.sh")
    
    print("\n🚀 Next steps:")
    print("1. Activate the environment")
    print("2. Run: python main_application.py")
    print("3. Or test: python verify_installation.py")

def main():
    """Main setup function for Anaconda"""
    print("🐍 Traffic Monitoring System - Anaconda Setup")
    print("="*60)
    
    # Check if conda is available
    if not check_conda():
        print("\n❌ Conda not found!")
        print("Please install Anaconda or Miniconda first:")
        print("https://www.anaconda.com/products/distribution")
        return
    
    # Create conda environment
    if not create_conda_environment():
        print("❌ Failed to create conda environment")
        return
    
    # Install conda packages
    install_conda_packages()
    
    # Install conda-forge packages
    install_conda_forge_packages()
    
    # Install pip packages
    install_pip_packages()
    
    # Create environment.yml
    create_environment_yml()
    
    # Test installation
    test_installation()
    
    # Create helper scripts
    create_batch_files()
    create_shell_scripts()
    
    # Print instructions
    print_final_instructions()

if __name__ == "__main__":
    main()
