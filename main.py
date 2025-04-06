import sys
import os
import argparse
import traceback
from pathlib import Path
from src.script_converter import ScriptConverter
from src.version_manager import VersionManager
from embed_erasmus import main as embed

def convert_scripts(version_str: str) -> int:
    """Convert shell script to batch script and create versioned copies."""
    sys.stderr.write("Starting script conversion...\n")
    sys.stderr.flush()
    embed()
    converter = ScriptConverter()
    script_dir = Path.cwd()
    release_dir = script_dir / 'release'
    version_dir = release_dir / f'v{version_str}'
    
    # Create versioned paths with version-specific directory
    batch_path = version_dir / f'erasmus_v{version_str}.bat'
    versioned_shell_path = version_dir / f'erasmus_v{version_str}.sh'
    
    # Print debug info
    sys.stderr.write(f"Python executable: {sys.executable}\n")
    sys.stderr.write(f"Current directory: {os.getcwd()}\n")
    sys.stderr.write(f"Function templates in converter:\n")
    for name, template in converter.function_templates.items():
        sys.stderr.write(f"- {name}: {len(template)} bytes\n")
    sys.stderr.write(f"Versioned shell script path: {versioned_shell_path}\n")
    sys.stderr.write(f"Batch script path: {batch_path}\n")
    sys.stderr.flush()
    
    try:
        # No need to check for shell_path anymore as we're using the versioned shell script
            
        # Check if the versioned shell script exists
        if not versioned_shell_path.exists():
            print(f"Error: Versioned shell script not found at: {versioned_shell_path}")
            return 1
            
        # Read the versioned shell script that already has the embedded content
        shell_content = versioned_shell_path.read_text(encoding='utf-8')
        print(f"Read {len(shell_content)} bytes from versioned shell script")
        
        # Convert to batch script
        print("Converting shell script to batch script...")
        batch_content = converter.convert_script(shell_content)
        print(f"Generated {len(batch_content)} bytes of batch script")
        
        # Create release directory and version-specific directory
        release_dir.mkdir(parents=True, exist_ok=True)
        version_dir.mkdir(parents=True, exist_ok=True)
        
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
            new_version = vm.increment_version(args.action)
            vm.add_change(message, args.action)
            print(f"Updated to version: {new_version}")
            # Automatically convert scripts on version change
            return convert_scripts(new_version)
    
    elif args.command == "convert":
        return convert_scripts(vm.get_current_version())
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    main()
