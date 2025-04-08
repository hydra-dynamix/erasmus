#!/bin/bash

# Script to build the installer with embedded erasmus.py

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || { echo "Failed to change to project root directory."; exit 1; }
echo "Changed to project root directory: $PROJECT_ROOT"

# Check if install.sh exists
if [ ! -f "scripts/install.sh" ]; then
    echo "Error: scripts/install.sh not found"
    exit 1
fi

# Check if erasmus.py exists
if [ ! -f "erasmus.py" ]; then
    echo "Error: erasmus.py not found"
    exit 1
fi

# Get version from version.json
VERSION=$(grep -o '"version": "[^"]*' version.json | cut -d'"' -f4)
echo "Building installer for version $VERSION"

# Run the embed_erasmus.py script to create the combined installer
echo "Creating combined installer using embed_erasmus.py..."
python3 src/embed_erasmus.py

# Verify the installer was created successfully
if [ ! -f "release/v${VERSION}/erasmus_v${VERSION}.sh" ]; then
    echo "Error: Failed to create installer"
    exit 1
fi

# Make the installer executable (in case it's not already)
chmod +x "release/v${VERSION}/erasmus_v${VERSION}.sh"

echo "Successfully created installer: release/v${VERSION}/erasmus_v${VERSION}.sh"

# Now run the script converter to create the batch file
echo "Running script converter to create batch file..."
uv run main.py convert

# Move the batch file to the version directory if it exists
if [ -f "release/erasmus_v${VERSION}.bat" ]; then
    mv "release/erasmus_v${VERSION}.bat" "release/v${VERSION}/"
    echo "Moved batch file to: release/v${VERSION}/erasmus_v${VERSION}.bat"
fi

echo "Build complete!"
