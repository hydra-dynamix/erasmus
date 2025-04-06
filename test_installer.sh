#!/bin/bash

# Test script to verify the installer works correctly
# This creates a temporary directory and tests the installer there

set -e  # Exit on error

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Copy the installer to the temporary directory
cp release/v0.0.2/erasmus_v0.0.2.sh "$TEMP_DIR/"
echo "Copied installer to temporary directory"

# Change to the temporary directory
cd "$TEMP_DIR"

# Make the installer executable
chmod +x erasmus_v0.0.2.sh

# Run the installer with a timeout to prevent it from hanging
echo "Running installer..."
timeout 30s ./erasmus_v0.0.2.sh || { echo "Installer timed out or failed"; exit 1; }

# Check if erasmus.py was created
if [ -f "erasmus.py" ]; then
    echo "Success: erasmus.py was created"
    # Check the size of the file
    SIZE=$(wc -c < erasmus.py)
    echo "File size: $SIZE bytes"
    
    # Check if the file starts with the expected shebang
    if head -n 1 erasmus.py | grep -q "#!/usr/bin/uv run"; then
        echo "Success: erasmus.py has the correct shebang"
    else
        echo "Error: erasmus.py does not have the correct shebang"
        head -n 1 erasmus.py
    fi
else
    echo "Error: erasmus.py was not created"
    ls -la
fi

# Clean up
echo "Cleaning up temporary directory"
cd -
rm -rf "$TEMP_DIR"

echo "Test completed"
