#!/usr/bin/env python3
"""
Script to embed the watcher.py file into the installer script as erasmus.py.
This creates a self-extracting installer that contains the erasmus.py file.
"""

import base64
import hashlib
import json
import os
import sys
from pathlib import Path


def main():
    """Main function to embed watcher.py into the installer as erasmus.py."""
    # Get project root directory
    project_root = Path.cwd()

    # Define paths
    watcher_path = project_root / 'watcher.py'
    install_path = project_root / 'scripts' / 'install.sh'
    version_path = project_root / 'version.json'
    release_dir = project_root / 'scripts' / 'release'

    # Create release directory if it doesn't exist
    release_dir.mkdir(parents=True, exist_ok=True)

    # Check if required files exist
    if not watcher_path.exists():
        print(f"Error: {watcher_path} not found")
        print("\nTo fix this error:")
        print("1. Create your main Python script as 'watcher.py' in the project root")
        print("2. Then run this script again to build the installer")
        return 1

    if not install_path.exists():
        print(f"Error: {install_path} not found")
        print("\nTo fix this error:")
        print("1. Make sure you're running this script from the project root directory")
        print("2. Ensure the scripts directory contains install.sh")
        return 1

    if not version_path.exists():
        print(f"Error: {version_path} not found")
        print("\nTo fix this error:")
        print("1. Make sure you're running this script from the project root directory")
        print("2. Create a version.json file with a 'version' field")
        print("   Example: {\"version\": \"0.1.0\"}")
        return 1

    # Get version from version.json
    with open(version_path) as f:
        version_data = json.load(f)
        version = version_data.get('version', '0.0.0')

    print(f"Building installer for version {version}")

    # Create version-specific directory
    version_dir = release_dir / f'v{version}'
    version_dir.mkdir(parents=True, exist_ok=True)

    # Read the installer script
    with open(install_path) as f:
        installer_content = f.read()

    # Read the watcher.py file and encode it as base64
    with open(watcher_path, 'rb') as f:
        watcher_content = f.read()
        # Calculate SHA-256 hash for verification
        watcher_hash = hashlib.sha256(watcher_content).hexdigest()
        encoded_content = base64.b64encode(watcher_content).decode('utf-8')

    print(f"Generated SHA-256 hash: {watcher_hash}")

    # Save the hash to a file in the version directory
    hash_file_path = version_dir / f'erasmus_v{version}.sha256'
    with open(hash_file_path, 'w') as hash_file:
        hash_file.write(f"{watcher_hash}  erasmus_v{version}.sh\n")
    print(f"Saved hash to: {hash_file_path}")

    # Create the combined installer
    output_path = version_dir / f'erasmus_v{version}.sh'

    with open(output_path, 'w') as f:
        # Write the installer script
        f.write(installer_content)

        # Add the marker line and hash information
        f.write("\n\n# __ERASMUS_EMBEDDED_BELOW__\n")
        f.write("# The content below this line is the base64-encoded watcher.py file\n")
        f.write("# It will be extracted during installation as erasmus.py\n")
        f.write(f"# SHA256_HASH={watcher_hash}\n")

        # Add exit command to prevent the shell from trying to execute the base64 content
        f.write("exit 0\n\n")

        # Add the base64-encoded content with a comment character to prevent execution
        f.write("# BEGIN_BASE64_CONTENT\n")

        # Split the encoded content into lines to ensure each line starts with a comment character
        encoded_lines = [encoded_content[i:i+76] for i in range(0, len(encoded_content), 76)]
        for line in encoded_lines:
            f.write(f"# {line}\n")

        f.write("# END_BASE64_CONTENT")

    # Make the installer executable
    os.chmod(output_path, 0o755)

    print(f"Successfully created installer: {output_path}")
    print("This installer will extract watcher.py as erasmus.py during installation")
    return 0

if __name__ == "__main__":
    sys.exit(main())
