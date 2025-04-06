#!/usr/bin/env bash

# Universal Installer for Watcher Project
# Supports Windows (via Git Bash/WSL), macOS, and Linux

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)    OS='macOS' ;;
        Linux*)    OS='Linux' ;;
        MINGW*|MSYS*|CYGWIN*) OS='Windows' ;;
        *)         OS='Unknown' ;;
    esac
}

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD='python3'
    elif command -v python &> /dev/null; then
        PYTHON_CMD='python'
    else
        echo -e "${RED}Error: Python is not installed!${NC}"
        echo "Please install Python 3.8+ before proceeding."
        exit 1
    }

    # Verify Python version
    PYTHON_VERSION=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        echo -e "${RED}Error: Python 3.8+ is required. Current version: $PYTHON_VERSION${NC}"
        exit 1
    fi
}

# Install uv package manager
install_uv() {
    echo -e "${YELLOW}Installing uv package manager...${NC}"
    
    # Try pip first
    if command -v pip &> /dev/null; then
        pip install uv
    elif command -v pip3 &> /dev/null; then
        pip3 install uv
    else
        # Fallback to Python's built-in method
        "$PYTHON_CMD" -m ensurepip --upgrade
        "$PYTHON_CMD" -m pip install uv
    fi

    # Verify uv installation
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Failed to install uv package manager!${NC}"
        exit 1
    fi
}

# Main installation process
main() {
    detect_os
    echo -e "${GREEN}Detected OS: $OS${NC}"

    check_python
    install_uv

    echo -e "${GREEN}Installation complete!${NC}"
    echo "You can now run the watcher script directly using:"
    echo "uv run watcher.py"
}

# Run the main installation function
main
