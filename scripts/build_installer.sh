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

# Check if a bundle path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_packaged_py>"
    exit 1
fi
BUNDLE_PATH="$1"
if [ ! -f "$BUNDLE_PATH" ]; then
    echo "Error: Could not find bundle to package: $BUNDLE_PATH"
    exit 1
fi

# Extract version and release dir
RELEASE_DIR=$(dirname "$BUNDLE_PATH")
VERSION=$(basename "$RELEASE_DIR" | sed 's/^v//')
INSTALLER="$RELEASE_DIR/erasmus_v${VERSION}.sh"

echo "Bundling $BUNDLE_PATH into $INSTALLER"

# Run the embed script to create the self-extracting installer
python3 scripts/embed_erasmus.py "$BUNDLE_PATH" "$INSTALLER"

# Check that the installer was created
if [ ! -f "$INSTALLER" ]; then
    echo "Error: Failed to create installer $INSTALLER"
    exit 1
fi

chmod +x "$INSTALLER"
echo "Successfully created installer: $INSTALLER"
echo "Build complete!"
