#!/usr/bin/env python3
"""
Bootstrap script for Claude Capture Portable
This script ensures all necessary dependencies are available and runs the capture tool.
"""

import sys
import subprocess
import os
import importlib.util
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()

# Required packages for optional features
OPTIONAL_PACKAGES = {
    'pyautogui': 'pyautogui>=0.9.50',  # For timeout handling
}

def check_python_version():
    """Check if Python version is sufficient"""
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required")
        sys.exit(1)

def is_package_installed(package_name):
    """Check if a package is installed"""
    return importlib.util.find_spec(package_name) is not None

def install_package(package_spec):
    """Install a package using pip"""
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '--user', package_spec
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def setup_environment():
    """Setup the environment with optional dependencies"""
    print("Checking dependencies...")
    
    missing_packages = []
    for package_name, package_spec in OPTIONAL_PACKAGES.items():
        if not is_package_installed(package_name):
            missing_packages.append((package_name, package_spec))
    
    if missing_packages:
        print(f"Found {len(missing_packages)} optional packages to install:")
        for name, spec in missing_packages:
            print(f"  - {name}: needed for enhanced functionality")
        
        try:
            try_install = input("Install optional packages? (y/N): ").lower().strip()
        except (EOFError, KeyboardInterrupt):
            try_install = 'n'
            print("n")
            
        if try_install in ['y', 'yes']:
            for name, spec in missing_packages:
                print(f"Installing {name}...")
                if install_package(spec):
                    print(f"  [OK] {name} installed successfully")
                else:
                    print(f"  [WARNING] Failed to install {name} (functionality will be limited)")
        else:
            print("Continuing without optional packages (some features will be limited)")
    else:
        print("All optional dependencies are available")

def run_claude_capture(args):
    """Run the main claude capture script"""
    # Add the script directory to Python path
    sys.path.insert(0, str(SCRIPT_DIR))
    
    # Import and run the main script
    try:
        from claude_capture_portable import main
        
        # Set up argv as if we called the script directly
        sys.argv = ['claude_capture_portable.py'] + args
        main()
    except ImportError as e:
        print(f"Error importing claude_capture_portable: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running claude capture: {e}")
        sys.exit(1)

def create_launcher_script():
    """Create a simple launcher script in the current directory"""
    launcher_content = f'''#!/usr/bin/env python3
"""
Simple launcher for Claude Capture Portable
Run this from any directory to use claude capture.
"""
import sys
import subprocess
from pathlib import Path

# Path to the portable claude capture directory
CLAUDE_CAPTURE_DIR = Path("{SCRIPT_DIR}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_capture.py \\"Your prompt here\\"")
        print()
        print("Example:")
        print('  python claude_capture.py "Create a hello world script"')
        sys.exit(1)
    
    # Run the bootstrap script with arguments
    try:
        subprocess.run([
            sys.executable, 
            str(CLAUDE_CAPTURE_DIR / "run_claude_capture.py"),
            "--no-setup"
        ] + sys.argv[1:], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Error: Claude capture directory not found at {{CLAUDE_CAPTURE_DIR}}")
        print("Please check the installation path.")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    launcher_path = Path.cwd() / "claude_capture.py"
    try:
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        print(f"Created launcher script: {launcher_path}")
        print("You can now run: python claude_capture.py \"Your prompt here\"")
        return True
    except Exception as e:
        print(f"Warning: Could not create launcher script: {e}")
        return False

def cleanup_zone_files():
    """Remove Windows Zone.Identifier files"""
    removed_count = 0
    try:
        # Use os.walk instead of rglob to avoid Windows path issues with colons
        for root, dirs, files in os.walk(SCRIPT_DIR):
            for filename in files:
                if filename.endswith(':Zone.Identifier'):
                    file_path = Path(root) / filename
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except Exception:
                        pass  # Ignore errors, just try to clean up
    except Exception:
        pass  # Ignore all errors in cleanup
    return removed_count

def main():
    """Main bootstrap function"""
    check_python_version()
    
    # Auto-cleanup Zone.Identifier files
    cleanup_zone_files()
    
    # Parse arguments
    args = sys.argv[1:]
    skip_setup = '--no-setup' in args
    if skip_setup:
        args.remove('--no-setup')
    
    create_launcher = '--create-launcher' in args
    if create_launcher:
        args.remove('--create-launcher')
        create_launcher_script()
        return
    
    # Check if we have arguments to run
    if not args:
        print("Claude Capture Portable - Bootstrap Script")
        print("=" * 50)
        print()
        print("This tool allows you to run Claude Code with role-based prompts")
        print("from any directory without requiring installation.")
        print()
        print("Usage:")
        print(f"  python {Path(__file__).name} \"Your prompt here\"")
        print()
        print("Options:")
        print("  --create-launcher  Create a launcher script in current directory")
        print("  --no-setup        Skip dependency setup (for internal use)")
        print()
        print("Examples:")
        print('  python run_claude_capture.py "Create a hello world script"')
        print('  python run_claude_capture.py "Review this code for security issues"')
        print()
        if not skip_setup:
            create_launcher_choice = input("Create launcher script in current directory? (y/N): ").lower().strip()
            if create_launcher_choice in ['y', 'yes']:
                create_launcher_script()
        return
    
    # Setup environment if not skipped
    if not skip_setup:
        setup_environment()
        print()
    
    # Run the main script
    print("Starting Claude Capture...")
    run_claude_capture(args)
    
    # Final cleanup
    cleanup_zone_files()

if __name__ == "__main__":
    main()
