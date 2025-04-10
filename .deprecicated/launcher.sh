#!/bin/bash
# Erasmus Launcher Script
# This script downloads the Erasmus installer and runs it interactively

set -e  # Exit on error

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Erasmus Interactive Installer${NC}"
echo -e "${YELLOW}============================${NC}"

# Prompt for IDE environment first
echo -e "${YELLOW}Please enter your IDE environment:${NC}"
echo -e "1) cursor (default)"
echo -e "2) windsurf"
read -p "Select option [1-2]: " ide_option

# Set IDE_ENV based on selection
case $ide_option in
    2)
        IDE_ENV="windsurf"
        ;;
    *)
        IDE_ENV="cursor"
        ;;
esac

echo -e "${GREEN}Selected IDE environment: ${IDE_ENV}${NC}"

# Download the latest installer
echo -e "${YELLOW}Downloading Erasmus installer...${NC}"
curl -fsSL https://raw.githubusercontent.com/Bakobiibizo/erasmus/main/release/v0.0.1/erasmus_v0.0.1.sh -o erasmus_install.sh

# Make it executable
chmod +x erasmus_install.sh

# Run it with the selected IDE environment
echo -e "${YELLOW}Starting installation with ${IDE_ENV} environment...${NC}"
export ERASMUS_IDE_ENV="$IDE_ENV"
exec ./erasmus_install.sh

# Note: exec replaces the current process with the installer
# This ensures proper TTY handling for interactive prompts
