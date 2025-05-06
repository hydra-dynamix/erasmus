#!/bin/bash

# Path to the GitHub MCP server binary
BINARY_PATH="$PWD/.erasmus/servers/github/github-mcp-server"

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

# Check binary type
echo -e "${YELLOW}Binary Type:${NC}"
file "$BINARY_PATH"

# Check executable permissions
echo -e "\n${YELLOW}Permissions:${NC}"
ls -l "$BINARY_PATH"

# Check library dependencies
echo -e "\n${YELLOW}Library Dependencies:${NC}"
ldd "$BINARY_PATH" || echo -e "${RED}Unable to check library dependencies${NC}"

# Check if it runs
echo -e "\n${YELLOW}Binary Execution Test:${NC}"
"$BINARY_PATH" --help

# Final status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✔ Binary appears to be compatible and executable${NC}"
else
    echo -e "\n${RED}✖ Binary failed execution test${NC}"
fi
