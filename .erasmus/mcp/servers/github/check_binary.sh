#!/bin/bash

# Path to the GitHub MCP server binary
BINARY_PATH="$PWD/.erasmus/mcp/servers/github/server"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if binary exists
if [ ! -f "$BINARY_PATH" ]; then
    echo -e "${RED}Error: Binary not found at $BINARY_PATH${NC}"
    exit 1
fi

# Function to handle verbose output based on ERASMUS_DEBUG
erasmus_verbose() {
    if [ "$ERASMUS_DEBUG" = "true" ]; then
        echo "$1"
    fi
}

# Function to run commands with output suppression when not in debug mode
run_command() {
    if [ "$ERASMUS_DEBUG" = "true" ]; then
        "$@"
    else
        "$@" > /dev/null 2>&1
    fi
}

erasmus_verbose "Binary Path: $BINARY_PATH"

# Check binary type
erasmus_verbose "Binary Type:"
run_command file "$BINARY_PATH"
RESULT=$?

# Check permissions
erasmus_verbose "Permissions:"
if [ $RESULT -eq 0 ]; then
    run_command ls -l "$BINARY_PATH"
    RESULT=$?
else
    erasmus_verbose "Failed to get permissions for $BINARY_PATH"
fi

# Check library dependencies
erasmus_verbose "Library Dependencies:"
if [ $RESULT -eq 0 ]; then
    run_command ldd "$BINARY_PATH"
    RESULT=$?
else
    erasmus_verbose "Failed to get library dependencies for $BINARY_PATH"
fi

# Test binary execution
erasmus_verbose "Binary Execution Test:"
if [ $RESULT -eq 0 ]; then
    run_command "$BINARY_PATH" --help
    RESULT=$?
else
    erasmus_verbose "Failed to execute $BINARY_PATH"
fi

# Final status
if [ $? -eq 0 ]; then
    erasmus_verbose "✔ Binary appears to be compatible and executable"
else
    erasmus_verbose "✖ Binary failed execution test"
fi
