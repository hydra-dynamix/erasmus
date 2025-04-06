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

# Check and install prerequisites based on OS
check_prerequisites() {
    case "$OS" in
        Windows)
            echo -e "${YELLOW}Checking Windows prerequisites...${NC}"
            # Check if winget is available
            if ! command -v winget &> /dev/null; then
                echo -e "${YELLOW}Installing winget...${NC}"
                powershell.exe -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
                if ! command -v winget &> /dev/null; then
                    echo -e "${RED}Failed to install winget. Please install it manually from the Microsoft Store.${NC}"
                    exit 1
                fi
            fi
            ;;
        macOS)
            echo -e "${YELLOW}Checking macOS prerequisites...${NC}"
            # Check if brew is available
            if ! command -v brew &> /dev/null; then
                echo -e "${RED}Homebrew is required but not installed.${NC}"
                echo "Please install Homebrew first: https://brew.sh"
                exit 1
            fi
            ;;
        Linux)
            echo -e "${YELLOW}Checking Linux prerequisites...${NC}"
            # Check if curl is available
            if ! command -v curl &> /dev/null; then
                echo -e "${YELLOW}Installing curl...${NC}"
                if command -v apt-get &> /dev/null; then
                    sudo apt-get update && sudo apt-get install -y curl
                elif command -v yum &> /dev/null; then
                    sudo yum install -y curl
                else
                    echo -e "${RED}Could not install curl. Please install it manually.${NC}"
                    exit 1
                fi
            fi
            ;;
    esac
}

# Install uv package manager
install_uv() {
    echo -e "${YELLOW}Installing uv package manager...${NC}"
    
    case "$OS" in
        Windows)
            winget install --id=astral-sh.uv -e
            ;;
        macOS)
            brew install uv
            ;;
        Linux)
            curl -LsSf https://astral.sh/uv/install.sh | sh
            ;;
        *)
            echo -e "${RED}Unsupported operating system: $OS${NC}"
            exit 1
            ;;
    esac

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

    check_prerequisites
    check_python
    install_uv

    echo -e "${GREEN}Installation complete!${NC}"
    echo "You can now run the watcher script directly using:"
    echo "uv run watcher.py"
}

# Run the main installation function
main
