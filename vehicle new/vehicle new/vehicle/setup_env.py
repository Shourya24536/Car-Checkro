import os
import sys
import shutil
import subprocess
import platform

def main():
    print("==================================================")
    # Detect platform details
    os_name = platform.system()
    machine = platform.machine().upper()
    print(f" Detected OS: {os_name}")
    print(f" Detected Architecture: {machine}")
    print("==================================================")

    # We only care about Windows migration for this task
    if os_name != "Windows":
        print(f"Warning: This script is configured for Windows systems. Current OS: {os_name}")

    is_arm64 = "ARM64" in machine

    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(project_root, ".venv")

    # Determine which base python interpreter to use
    if is_arm64:
        # Search for the native python.exe on qcwor's system
        python_candidates = [
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"),
            sys.executable,
        ]
    else:
        python_candidates = [sys.executable]

    base_python = None
    for candidate in python_candidates:
        if os.path.exists(candidate):
            base_python = candidate
            break

    if not base_python:
        print("Error: Could not locate base Python interpreter!")
        sys.exit(1)

    print(f"Using base Python interpreter: {base_python}")

    # Recreate the virtual environment
    if os.path.exists(venv_dir):
        print(f"Removing existing/broken virtual environment at: {venv_dir}")
        try:
            shutil.rmtree(venv_dir)
        except Exception as e:
            print(f"Failed to remove .venv directory: {e}")
            print("Please close any processes using the virtual environment and try again.")
            sys.exit(1)

    # Initialize venv command
    venv_cmd = [base_python, "-m", "venv", venv_dir]
    if is_arm64:
        # Crucial for ARM64: inherit the native system-installed packages (open3d, torch, numpy, opencv)
        print("Configuring virtual environment with --system-site-packages for ARM64 compatibility...")
        venv_cmd.append("--system-site-packages")
    else:
        print("Configuring clean virtual environment for x64...")

    # Create the virtual environment
    print(f"Creating virtual environment at: {venv_dir}...")
    try:
        subprocess.run(venv_cmd, check=True)
        print("[+] Virtual environment created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        sys.exit(1)

    # Find virtual environment pip and python executables
    venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")

    if not os.path.exists(venv_python) or not os.path.exists(venv_pip):
        print("Error: Virtual environment executables not found!")
        sys.exit(1)

    # Upgrade pip in the virtual environment
    print("Upgrading pip inside virtual environment...")
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to upgrade pip: {e}")

    # Install dependencies
    dependencies = [
        "ultralytics>=8.3.0",
        "roboflow>=1.1.0",
        "matplotlib>=3.7.0",
        "tqdm>=4.65.0",
        "pyyaml>=6.0",
        "onnx>=1.14.0",
        "onnxruntime>=1.15.0",
    ]

    print("Installing python packages inside the virtual environment...")
    install_cmd = [venv_pip, "install"] + dependencies
    try:
        subprocess.run(install_cmd, check=True)
        print("[+] All dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

    # For Windows ARM64, make sure opencv-python-headless doesn't shadow the system opencv-python
    if is_arm64:
        print("Ensuring opencv-python-headless does not shadow the system opencv-python...")
        try:
            subprocess.run([venv_pip, "uninstall", "opencv-python-headless", "-y"], check=False)
        except Exception:
            pass

    print("==================================================")
    print("   Migration/Setup Completed Successfully!        ")
    print(f"   Architecture: {machine}")
    print("==================================================")

if __name__ == "__main__":
    main()
