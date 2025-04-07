#!/bin/bash
# Erasmus Launcher Script
# This script downloads the Erasmus installer and runs it interactively

set -e  # Exit on error

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Erasmus Interactive Installer${NC}"
echo -e "${YELLOW}============================${NC}"

# Download the latest installer
echo -e "${YELLOW}Downloading Erasmus installer...${NC}"
curl -fsSL https://raw.githubusercontent.com/Bakobiibizo/erasmus/main/release/v0.0.1/erasmus_v0.0.1.sh -o erasmus_install.sh

# Make it executable
chmod +x erasmus_install.sh

# Run it interactively with a proper TTY
echo -e "${YELLOW}Starting interactive installation...${NC}"
exec ./erasmus_install.sh

# Note: exec replaces the current process with the installer
# This ensures proper TTY handling for interactive prompts
