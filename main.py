import sys
import os
import argparse
import traceback
import subprocess
import shutil
from pathlib import Path
from src.script_converter import ScriptConverter
from src.version_manager import VersionManager
from src.build_release import embed_erasmus, convert_to_batch


def convert_scripts(version_str: str) -> int:
    """Convert shell script to batch script and create versioned copies."""
    sys.stderr.write("Starting script conversion...\n")
    sys.stderr.flush()
    
    converter = ScriptConverter()
    
    # Get the project root directory
    project_root = Path.cwd()
    script_dir = project_root / 'scripts'
    release_dir = project_root / 'release'
    version_dir = release_dir / f'v{version_str}'
    
    # Create versioned paths with version-specific directory
    batch_path = version_dir / f'erasmus_v{version_str}.bat'
    versioned_shell_path = version_dir / f'erasmus_v{version_str}.sh'
    
    # Print debug info
    sys.stderr.write(f"Python executable: {sys.executable}\n")
    sys.stderr.write(f"Current directory: {os.getcwd()}\n")
    sys.stderr.write(f"Project root: {project_root}\n")
    sys.stderr.write(f"Script directory: {script_dir}\n")
    sys.stderr.write(f"Function templates in converter:\n")
    for name, template in converter.function_templates.items():
        sys.stderr.write(f"- {name}: {len(template)} bytes\n")
    sys.stderr.write(f"Versioned shell script path: {versioned_shell_path}\n")
    sys.stderr.write(f"Batch script path: {batch_path}\n")
    sys.stderr.flush()
    
    try:
        # Create release directory and version-specific directory
        release_dir.mkdir(parents=True, exist_ok=True)
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # If versioned shell script doesn't exist, create it from install.sh
        if not versioned_shell_path.exists():
            install_sh = project_root / 'install.sh'
            if not install_sh.exists():
                print(f"Error: Neither versioned shell script nor install.sh found")
                return 1
            # Copy install.sh to versioned location
            shutil.copy2(install_sh, versioned_shell_path)
            
        # Read the versioned shell script
        shell_content = versioned_shell_path.read_text(encoding='utf-8')
        print(f"Read {len(shell_content)} bytes from versioned shell script")
        
        # Convert to batch script
        print("Converting shell script to batch script...")
        batch_content = converter.convert_script(shell_content)
        print(f"Generated {len(batch_content)} bytes of batch script")
        
        # Write batch script
        batch_path.write_text(batch_content, encoding='utf-8')
        
        print("Successfully wrote scripts to release directory:")
        print(f"  - {batch_path}")
        print(f"  - {versioned_shell_path}")
        return 0
        
    except Exception as e:
        print(f"Error converting script: {str(e)}")
        traceback.print_exc()
        return 1

def build_release():
    """Build the complete release package."""
    try:
        print("Building complete release package...")
        
        # Step 1: Embed watcher.py into the installer
        result = embed_erasmus()
        if isinstance(result, tuple):
            version, version_dir = result
        else:
            print("Failed to embed watcher.py into the installer")
            return 1
        
        # Step 2: Convert to batch file
        result = convert_to_batch(version, version_dir)
        if result != 0:
            print("Failed to create Windows batch installer")
            return 1
        
        print("\nRelease package built successfully!")
        print(f"Shell installer: release/v{version}/erasmus_v{version}.sh")
        print(f"Windows installer: release/v{version}/erasmus_v{version}.bat")
        print(f"SHA256 hash file: release/v{version}/erasmus_v{version}.sha256")
        
        return 0
    except ImportError:
        print("Error: src/build_release.py not found.", file=sys.stderr)
        print("Please make sure build_release.py is in the src directory.", file=sys.stderr)
        return 1

def run_tests():
    """Run the Docker tests for the installer."""
    try:
        print("Running Docker tests for the installer...")
        
        # Run the test script
        test_script = Path.cwd() / "scripts" / "test" / "test_installer.sh"
        if not test_script.exists():
            print(f"Error: Test script not found at {test_script}")
            return 1
            
        # Make the test script executable
        os.chmod(test_script, 0o755)
        
        # Run the test script with the current environment
        try:
            # Pass the current environment to ensure Docker permissions are preserved
            subprocess.run(["bash", str(test_script)], check=True, env=os.environ.copy())
            print("Tests completed successfully!")
            return 0
        except subprocess.CalledProcessError as e:
            print(f"Tests failed with exit code {e.returncode}")
            return 1
        
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        traceback.print_exc()
        return 1

def main():
    """Main entry point with version management CLI."""
    parser = argparse.ArgumentParser(description="Erasmus script management tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Version commands
    version_parser = subparsers.add_parser("version", help="Version management")
    version_parser.add_argument("action", choices=["get", "major", "minor", "patch"], 
                               help="Version action")
    version_parser.add_argument("--message", "-m", help="Change message for version update")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert installation scripts")
    convert_parser.add_argument("--version", "-v", help="Version to convert (defaults to current version)")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build the complete release package")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run Docker tests for the installer")
    
    args = parser.parse_args()
    vm = VersionManager()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "version":
        if args.action == "get":
            print(f"Current version: {vm.get_current_version()}")
            return 0
        else:
            message = args.message or f"Increment {args.action} version"
            # Only add the change, which will increment the version once
            vm.add_change(message, args.action)
            print(f"Updated to version: {vm.get_current_version()}")
            # Automatically convert scripts on version change
            return convert_scripts(vm.get_current_version())
    
    elif args.command == "convert":
        version = args.version or vm.get_current_version()
        return convert_scripts(version)
    
    elif args.command == "build":
        return build_release()
        
    elif args.command == "test":
        return run_tests()

if __name__ == '__main__':
    main()
