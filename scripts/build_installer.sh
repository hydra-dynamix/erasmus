#!/bin/bash

# Script to build the installer with embedded erasmus.py

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || {
    echo "Failed to change to project root directory."
    exit 1
}
echo "Changed to project root directory: $PROJECT_ROOT"

# Find the latest erasmus_v*.py in releases
echo "Locating latest erasmus_v*.py bundle..."
LATEST_BUNDLE=$(ls -t releases/*/erasmus_v*.py 2>/dev/null | head -n1)
if [ -z "$LATEST_BUNDLE" ]; then
    echo "Error: No erasmus_v*.py found in releases directory"
    exit 1
fi

# Extract version and release dir
RELEASE_DIR=$(dirname "$LATEST_BUNDLE")
VERSION=$(basename "$RELEASE_DIR" | sed 's/^v//')
INSTALLER="$RELEASE_DIR/erasmus_v${VERSION}.sh"

echo "Bundling $LATEST_BUNDLE into $INSTALLER"

# Run the embed script to create the self-extracting installer
python3 scripts/embed_erasmus.py "$LATEST_BUNDLE" "$INSTALLER"

# Make the installer executable
chmod +x "$INSTALLER"

echo "Successfully created installer: $INSTALLER"

echo "Build complete!"
