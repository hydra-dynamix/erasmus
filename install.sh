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
    fi

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

# Setup environment files
setup_env() {
    # Create .env.example with empty values
    cat > .env.example << EOL
IDE_ENV=
GIT_TOKEN=
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
EOL
    
    # Prompt for IDE environment
    echo -e "${YELLOW}Please enter your IDE environment (cursor/windsurf):${NC}"
    read -r IDE_ENV
    
    # Convert to uppercase for consistency
    IDE_ENV=$(echo "$IDE_ENV" | tr '[:lower:]' '[:upper:]')
    
    # Validate IDE environment
    if [ "$IDE_ENV" != "CURSOR" ] && [ "$IDE_ENV" != "WINDSURF" ]; then
        echo -e "${YELLOW}Warning: Unknown IDE environment. Defaulting to CURSOR.${NC}"
        IDE_ENV="CURSOR"
    fi
    
    # Create .env with provided IDE_ENV
    cat > .env << EOL
IDE_ENV=$IDE_ENV
GIT_TOKEN=
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
EOL
    
    echo -e "${GREEN}Environment files created successfully for $IDE_ENV${NC}"
}

# Initialize watcher
init_watcher() {
    echo -e "${YELLOW}Initializing watcher...${NC}"
    
    # Extract watcher.py if it's embedded in the installer
    if [ -f watcher.py.gz ]; then
        gunzip -f watcher.py.gz
    fi
    
    # Run watcher setup using environment variable
    if [ -f watcher.py ]; then
        # Create project directory structure if it doesn't exist
        mkdir -p .git
        
        # Initialize watcher with the specified IDE environment
        IDE_ENV=$(grep IDE_ENV .env | cut -d= -f2)
        uv run watcher.py --setup "$IDE_ENV"
    else
        echo -e "${RED}Error: watcher.py not found${NC}"
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
    setup_env
    init_watcher

    echo -e "${GREEN}Installation complete!${NC}"
    echo "Watcher has been initialized with your IDE environment: $IDE_ENV"
}

# Run the main installation function
main
