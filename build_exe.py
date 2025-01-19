# File: build_exe.py
# Purpose: Build script to create a single executable file for the BNB Portfolio Manager
# This script handles dependency management, resource inclusion, and environment setup

import os
import sys
import shutil
import subprocess
from datetime import datetime

def create_version_file(dist_dir):
    """
    Create a version.txt file containing build information in the distribution directory.
    
    Args:
        dist_dir (str): The distribution directory path where the file will be created
        
    This function creates a version file alongside the executable, making it easier
    to track which version of the application is being used. The file is created
    directly in the distribution directory to keep all build outputs together.
    """
    # Ensure the dist directory exists
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
        
    # Create the full path for version.txt in the dist directory
    version_file_path = os.path.join(dist_dir, 'version.txt')
    
    # Create the version information
    version_info = f"""BNB Portfolio Manager
Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Version: 3.5.0
Copyright: Bear No Bears
"""
    # Write the version file directly to the dist directory
    with open(version_file_path, 'w') as f:
        f.write(version_info)
        
    print(f"Created version file in distribution directory: {version_file_path}")

def check_dependencies():
    """
    Verify all required packages are installed and install them if needed.
    Returns True if all dependencies are satisfied, False otherwise.
    """
    required_packages = [
        'PySide6',
        'yfinance',
        'pandas',
        'numpy',
        'matplotlib',
        'seaborn',
        'pyinstaller',
        'pyyaml'
    ]
    
    print("Checking and installing dependencies...")
    try:
        for package in required_packages:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {str(e)}")
        return False

def cleanup_previous_build():
    """
    Remove previous build artifacts to ensure a clean build.
    Handles all temporary files and build directories.
    """
    print("Cleaning up previous build artifacts...")
    
    # Define items to clean
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec', '*.pyc', '*.pyo', '*.pyd']
    
    # Remove directories
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"Removed directory: {dir_name}")
            except Exception as e:
                print(f"Error removing {dir_name}: {str(e)}")
    
    # Remove files
    for file_pattern in files_to_clean:
        try:
            matching_files = [f for f in os.listdir() if f.endswith(file_pattern[1:])]
            for file in matching_files:
                os.remove(file)
                print(f"Removed file: {file}")
        except Exception as e:
            print(f"Error removing files matching {file_pattern}: {str(e)}")
    
    print("Cleanup completed")

def copy_resources(dist_dir):
    """
    Copy necessary resource files to the distribution directory.
    
    Args:
        dist_dir: The directory where the executable will be created
    """
    resources = [
        'config.yaml',
        'bnb_logo.png',
        'wallpaper.png',
        'version.txt'
    ]
    
    print("Copying resource files...")
    for resource in resources:
        if os.path.exists(resource):
            shutil.copy2(resource, dist_dir)
        else:
            print(f"Warning: Resource file {resource} not found")

def build_executable():
    """
    Build the executable using PyInstaller.
    Creates a single executable file along with all necessary resources, including SQL files.
    """
    print("Building executable...")
    try:
        # Create PyInstaller command
        cmd = [
            'pyinstaller',
            '--noconfirm',
            '--onefile',
            '--windowed',
            '--name=BNB_Portfolio_Manager',
            '--icon=bnb_logo.ico',
            '--add-data=config.yaml;.',
            '--add-data=bnb_logo.png;.',
            '--add-data=wallpaper.png;.',
            '--add-data=database/schema.sql;database',
            '--add-data=database/final_metrics.sql;database',
            '--add-data=BNB_Transaction_Data_Template.xlsx;.',
            '--hidden-import=yfinance',
            '--hidden-import=pandas',
            '--hidden-import=numpy',
            '--hidden-import=matplotlib',
            '--hidden-import=seaborn',
            '--hidden-import=yaml',
            'main.py'
        ]
        
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building executable: {str(e)}")
        return False

def main():
    """
    Main build process coordinator.
    Handles the complete build process from start to finish, ensuring all files
    are created in the correct locations.
    """
    print("Starting BNB Portfolio Manager build process...")
    
    # Clean up previous build artifacts
    cleanup_previous_build()
    
    # Check and install dependencies
    if not check_dependencies():
        print("Failed to install dependencies. Build aborted.")
        return False
    
    # Build the executable
    if not build_executable():
        print("Failed to build executable. Build aborted.")
        return False
    
    # Create version file directly in dist directory
    create_version_file('dist')
    
    # Copy remaining resource files
    copy_resources('dist')
    
    print("\nBuild completed successfully!")
    print("Executable and all supporting files can be found in the 'dist' directory")
    return True

if __name__ == "__main__":
    main()