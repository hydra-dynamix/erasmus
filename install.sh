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
                echo -e "${RED}Error: winget is not available on this Windows system.${NC}"
                echo "Please install the latest App Installer from the Microsoft Store."
                exit 1
            fi
            ;;
        macOS)
            echo -e "${YELLOW}Checking macOS prerequisites...${NC}"
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if [ $? -ne 0 ]; then
                    echo -e "${RED}Failed to install Homebrew. Please install it manually.${NC}"
                    exit 1
                fi
            fi
            ;;
        Linux)
            echo -e "${YELLOW}Checking Linux prerequisites...${NC}"
            # Check if curl is installed
            if ! command -v curl &> /dev/null; then
                echo -e "${RED}Error: curl is not installed.${NC}"
                echo "Please install curl using your distribution's package manager."
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Unsupported operating system: $OS${NC}"
            exit 1
            ;;
    esac
}

# Install uv package manager
install_uv() {
    # Check if uv is already installed
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}uv package manager is already installed.${NC}"
        return 0
    fi

    echo -e "${YELLOW}Installing uv package manager...${NC}"
    
    case "$OS" in
        Windows)
            echo -e "${YELLOW}Installing uv via winget...${NC}"
            winget install astral.uv
            ;;
        macOS)
            echo -e "${YELLOW}Installing uv via Homebrew...${NC}"
            brew install astral/tap/uv
            ;;
        Linux)
            echo -e "${YELLOW}Installing uv via curl...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # Add uv to PATH for the current session
            export PATH="$HOME/.cargo/bin:$PATH"
            ;;
    esac
    
    # Verify uv installation
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Failed to install uv. Please install it manually:${NC}"
        echo "https://github.com/astral/uv#installation"
        exit 1
    fi
    
    echo -e "${GREEN}uv package manager installed successfully!${NC}"
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
    
    # Check if IDE environment is already set via the launcher script
    if [ -n "$ERASMUS_IDE_ENV" ]; then
        IDE_ENV="$ERASMUS_IDE_ENV"
        echo -e "${GREEN}Using IDE environment from launcher: $IDE_ENV${NC}"
    else
        # Prompt for IDE environment
        echo -e "${YELLOW}Please enter your IDE environment (cursor/windsurf):${NC}"
        read -r IDE_ENV
        
        # Convert to uppercase for consistency
        IDE_ENV=$(echo "$IDE_ENV" | tr '[:lower:]' '[:upper:]')
    fi
    
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

# Initialize Erasmus
init_watcher() {
    echo -e "${YELLOW}Initializing Erasmus...${NC}"
    
    # Create erasmus.py from the embedded content
    echo -e "${YELLOW}Extracting erasmus.py...${NC}"
    
    # Extract the base64 content from this script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SCRIPT_PATH="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
    
    # Find the SHA256 hash in the script
    EXPECTED_HASH=$(grep -A 1 "BEGIN_HASH" "$SCRIPT_PATH" | grep -v "BEGIN_HASH" | grep -v "END_HASH" | tr -d '# ')
    
    # If hash is empty, try alternative extraction method
    if [ -z "$EXPECTED_HASH" ]; then
        echo -e "${YELLOW}Trying alternative hash extraction method...${NC}"
        EXPECTED_HASH=$(grep -A 2 "BEGIN_HASH" "$SCRIPT_PATH" | tail -n 1 | tr -d '# ')
    fi
    
    # If still empty, use the hash from the .sha256 file if it exists
    if [ -z "$EXPECTED_HASH" ] && [ -f "$(dirname "$SCRIPT_PATH")/$(basename "$SCRIPT_PATH" .sh).sha256" ]; then
        echo -e "${YELLOW}Using hash from .sha256 file...${NC}"
        EXPECTED_HASH=$(cat "$(dirname "$SCRIPT_PATH")/$(basename "$SCRIPT_PATH" .sh).sha256")
    fi
    
    # Extract the base64 content between markers
    BASE64_CONTENT=$(sed -n '/^# BEGIN_BASE64_CONTENT$/,/^# END_BASE64_CONTENT$/p' "$SCRIPT_PATH" | grep -v "BEGIN_BASE64_CONTENT" | grep -v "END_BASE64_CONTENT" | tr -d '# ')
    
    if [ -z "$BASE64_CONTENT" ]; then
        echo -e "${RED}Error: Could not extract base64 content from installer.${NC}"
        exit 1
    fi
    
    # Decode the base64 content
    echo "$BASE64_CONTENT" | base64 -d > watcher.py
    
    # Verify the SHA256 hash
    if command -v shasum &> /dev/null; then
        ACTUAL_HASH=$(shasum -a 256 watcher.py | cut -d ' ' -f 1)
    elif command -v sha256sum &> /dev/null; then
        ACTUAL_HASH=$(sha256sum watcher.py | cut -d ' ' -f 1)
    else
        echo -e "${YELLOW}Warning: Could not verify SHA256 hash (shasum/sha256sum not available).${NC}"
        ACTUAL_HASH="unknown"
    fi
    
    if [ -z "$EXPECTED_HASH" ] || [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ] || [ "$ACTUAL_HASH" = "unknown" ]; then
        echo -e "${GREEN}Successfully extracted watcher.py${NC}"
        if [ "$ACTUAL_HASH" != "unknown" ]; then
            if [ -z "$EXPECTED_HASH" ]; then
                echo -e "${YELLOW}Warning: No expected hash found. Using actual hash: $ACTUAL_HASH${NC}"
            else
                echo -e "${GREEN}SHA256 hash verified: $ACTUAL_HASH${NC}"
            fi
        fi
    else
        echo -e "${RED}Error: SHA256 hash verification failed!${NC}"
        echo -e "${RED}Expected: $EXPECTED_HASH${NC}"
        echo -e "${RED}Actual: $ACTUAL_HASH${NC}"
        
        # Continue anyway if the user confirms
        echo -e "${YELLOW}Do you want to continue anyway? (y/N)${NC}"
        read -r continue_anyway
        if [ "${continue_anyway,,}" != "y" ]; then
            exit 1
        fi
        echo -e "${YELLOW}Continuing with unverified file...${NC}"
    fi
    
    # Create a virtual environment and install dependencies
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    uv venv
    
    # Activate the virtual environment
    case "$OS" in
        Windows)
            source .venv/Scripts/activate
            ;;
        *)
            source .venv/bin/activate
            ;;
    esac
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    uv pip install -r requirements.txt
    
    # Run the watcher setup with IDE environment
    echo -e "${YELLOW}Running watcher setup...${NC}"
    "$PYTHON_CMD" watcher.py --setup "$IDE_ENV"
    
    echo -e "${GREEN}Erasmus initialized successfully!${NC}"
    echo -e "${YELLOW}To activate the environment in the future, run:${NC}"
    case "$OS" in
        Windows)
            echo -e "    ${GREEN}source .venv/Scripts/activate${NC}"
            ;;
        *)
            echo -e "    ${GREEN}source .venv/bin/activate${NC}"
            ;;
    esac
    echo -e "${YELLOW}To run Erasmus:${NC}"
    echo -e "    ${GREEN}python watcher.py${NC}"
}

# Main installation process
main() {
    echo -e "${YELLOW}Starting Erasmus installation...${NC}"
    
    # Detect the operating system
    detect_os
    echo -e "${GREEN}Detected OS: $OS${NC}"
    
    # Check Python installation
    check_python
    echo -e "${GREEN}Using Python $PYTHON_VERSION${NC}"
    
    # Check and install prerequisites
    check_prerequisites
    
    # Install uv package manager
    install_uv
    
    # Setup environment files
    setup_env
    
    # Initialize watcher
    init_watcher
    
    echo -e "${GREEN}Erasmus installation completed successfully!${NC}"
}

# Run the main installation function
main
