#!/usr/bin/env python3
"""
Script to embed the erasmus.py file (previously watcher.py) into the installer script.
This creates a self-extracting installer that contains the erasmus.py file.
"""

import os
import sys
import base64
import json
import hashlib
from pathlib import Path

def main():
    """Main function to embed erasmus.py into the installer."""
    # Get current directory
    script_dir = Path.cwd()
    
    # Define paths
    watcher_path = script_dir / 'watcher.py'
    install_path = script_dir / 'install.sh'
    version_path = script_dir / 'version.json'
    release_dir = script_dir / 'release'
    
    # Create release directory if it doesn't exist
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if required files exist
    if not watcher_path.exists():
        print(f"Error: {watcher_path} not found")
        return 1
    
    if not install_path.exists():
        print(f"Error: {install_path} not found")
        return 1
    
    if not version_path.exists():
        print(f"Error: {version_path} not found")
        return 1
    
    # Get version from version.json
    with open(version_path, 'r') as f:
        version_data = json.load(f)
        version = version_data.get('version', '0.0.0')
    
    print(f"Building installer for version {version}")
    
    # Create version-specific directory
    version_dir = release_dir / f'v{version}'
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Read the installer script
    with open(install_path, 'r') as f:
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
        f.write("# The content below this line is the base64-encoded erasmus.py file\n")
        f.write("# It will be extracted during installation\n")
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
    return 0

if __name__ == "__main__":
    sys.exit(main())
