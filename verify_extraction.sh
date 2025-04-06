#!/bin/bash

# Script to verify the extraction part of the installer works correctly
# This only tests the extraction of the base64 content, not the full installer

set -e  # Exit on error

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Copy the installer to the temporary directory
cp release/v0.0.2/erasmus_v0.0.2.sh "$TEMP_DIR/"
echo "Copied installer to temporary directory"

# Change to the temporary directory
cd "$TEMP_DIR"

# Use a more reliable approach - extract the content between markers using awk
echo "Extracting base64 content using awk..."
awk '/^# BEGIN_BASE64_CONTENT$/,/^# END_BASE64_CONTENT$/ { if (!/^# BEGIN_BASE64_CONTENT$/ && !/^# END_BASE64_CONTENT$/) print }' erasmus_v0.0.2.sh | sed 's/^# //' > erasmus.py.b64

# Check if the extracted content is valid
if [ ! -s erasmus.py.b64 ]; then
    echo "Error: Failed to extract base64 content"
    exit 1
fi

# Show a sample of the extracted content
echo "Sample of extracted base64 content:"
head -n 3 erasmus.py.b64

# Decode the base64 content
echo "Decoding base64 content..."
base64 -d erasmus.py.b64 > erasmus.py 2>/dev/null || {
    echo "Error: Failed to decode base64 content"
    exit 1
}

# Check if erasmus.py was created successfully
if [ -f "erasmus.py" ] && [ -s "erasmus.py" ]; then
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
    echo "Error: erasmus.py was not created or is empty"
    exit 1
fi

# Clean up
echo "Cleaning up temporary directory"
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo "Verification completed successfully"
exit 0
