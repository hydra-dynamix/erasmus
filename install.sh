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
    # Check if uv is already installed
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version | head -n 1)
        echo -e "${GREEN}UV package manager is already installed: $UV_VERSION${NC}"
        return 0
    fi
    
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
    
    UV_VERSION=$(uv --version | head -n 1)
    echo -e "${GREEN}Successfully installed UV package manager: $UV_VERSION${NC}"
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

# Initialize Erasmus
init_watcher() {
    echo -e "${YELLOW}Initializing Erasmus...${NC}"
    
    # Create erasmus.py from the embedded content
    echo -e "${YELLOW}Extracting erasmus.py...${NC}"
    
    # Copy the watcher.py content to erasmus.py
    if [ -f watcher.py ]; then
        cp watcher.py erasmus.py
    elif [ -f "$0" ]; then
        # Extract embedded erasmus.py from this script if it exists
        EXTRACT_MARKER="__ERASMUS_EMBEDDED_BELOW__"
        LINE_NUM=$(grep -n "$EXTRACT_MARKER" "$0" | cut -d: -f1)
        
        if [ -n "$LINE_NUM" ]; then
            # Extract the expected hash from the script - search for the SHA256_HASH line
            EXPECTED_HASH=$(grep -A 5 "$EXTRACT_MARKER" "$0" | grep 'SHA256_HASH=' | grep -o '[a-f0-9]\{64\}')
            
            if [ -z "$EXPECTED_HASH" ]; then
                echo -e "${YELLOW}Warning: No hash found for verification${NC}"
            else
                echo -e "${YELLOW}Found hash for verification: $EXPECTED_HASH${NC}"
            fi
            
            # Extract and decode the base64 content using awk
            echo -e "${YELLOW}Extracting base64 content...${NC}"
            
            # Use awk to extract content between markers, removing the leading '# '
            awk '/^# BEGIN_BASE64_CONTENT$/,/^# END_BASE64_CONTENT$/ { if (!/^# BEGIN_BASE64_CONTENT$/ && !/^# END_BASE64_CONTENT$/) print }' "$0" | sed 's/^# //' > erasmus.py.b64
            
            # Check if the extracted content is valid
            if [ ! -s erasmus.py.b64 ]; then
                echo -e "${RED}Error: Failed to extract base64 content${NC}"
                # Fall back to the old method if extraction failed
                echo -e "${YELLOW}Using legacy extraction method${NC}"
                tail -n +$((LINE_NUM + 5)) "$0" > erasmus.py.b64
            fi
            
            # Decode the base64 content
            echo -e "${YELLOW}Decoding base64 content...${NC}"
            base64 -d erasmus.py.b64 > erasmus.py 2>/dev/null || {
                echo -e "${RED}Error: Failed to decode base64 content${NC}"
                cat erasmus.py.b64 | head -n 3
                exit 1
            }
            
            # Check if the file is empty or very small (likely an error)
            if [ ! -s erasmus.py ] || [ $(wc -c < erasmus.py) -lt 100 ]; then
                echo -e "${RED}Error: Extracted file is empty or too small${NC}"
                cat erasmus.py.b64 | head -n 5
                exit 1
            fi
            
            # Clean up the temporary file
            rm erasmus.py.b64
            
            # Verify the hash if an expected hash was found
            if [ -n "$EXPECTED_HASH" ]; then
                # Make sure the expected hash is valid
                if ! [[ "$EXPECTED_HASH" =~ ^[0-9a-f]{64}$ ]]; then
                    echo -e "${YELLOW}Warning: Invalid expected hash format: $EXPECTED_HASH${NC}"
                    EXPECTED_HASH=""
                else
                    echo -e "${YELLOW}Expected hash: $EXPECTED_HASH${NC}"
                    
                    if command -v shasum &> /dev/null; then
                        ACTUAL_HASH=$(shasum -a 256 erasmus.py | cut -d' ' -f1)
                    elif command -v sha256sum &> /dev/null; then
                        ACTUAL_HASH=$(sha256sum erasmus.py | cut -d' ' -f1)
                    else
                        echo -e "${YELLOW}Warning: No hash verification tool found (shasum or sha256sum)${NC}"
                        ACTUAL_HASH=""
                    fi
                    
                    echo -e "${YELLOW}Actual hash: $ACTUAL_HASH${NC}"
                    
                    if [ -n "$ACTUAL_HASH" ]; then
                        if [ "$EXPECTED_HASH" = "$ACTUAL_HASH" ]; then
                            echo -e "${GREEN}Hash verification successful!${NC}"
                        else
                            echo -e "${RED}Error: Hash verification failed!${NC}"
                            echo -e "${RED}Expected: $EXPECTED_HASH${NC}"
                            echo -e "${RED}Actual: $ACTUAL_HASH${NC}"
                            echo -e "${RED}The extracted file may have been tampered with or corrupted.${NC}"
                            rm erasmus.py
                            exit 1
                        fi
                    fi
                fi
            fi
            echo -e "${GREEN}Successfully extracted erasmus.py${NC}"
        else
            echo -e "${RED}Error: Could not extract erasmus.py from installer${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: Could not find erasmus.py or extract it from installer${NC}"
        exit 1
    fi
    
    # Verify erasmus.py exists
    if [ ! -f erasmus.py ]; then
        echo -e "${RED}Error: erasmus.py not found after extraction attempt${NC}"
        exit 1
    fi
    
    # Create project directory structure if it doesn't exist
    mkdir -p .git
    
    # Initialize erasmus with the specified IDE environment
    IDE_ENV=$(grep IDE_ENV .env | cut -d= -f2)
    echo -e "${GREEN}Running erasmus.py with IDE environment: $IDE_ENV${NC}"
    uv run erasmus.py --setup "$IDE_ENV"
}

# Main installation process
main() {
    echo -e "${GREEN}=== Erasmus Installation ====${NC}"
    echo -e "A context-aware development environment for AI-assisted coding"
    echo ""
    
    detect_os
    echo -e "${GREEN}Detected OS: $OS${NC}"

    check_prerequisites
    check_python
    install_uv
    setup_env
    init_watcher

    echo -e "${GREEN}Installation complete!${NC}"
    echo "Erasmus has been initialized with your IDE environment: $IDE_ENV"
    echo ""
    echo "To start using Erasmus, run: uv run erasmus.py"
}

# Run the main installation function
main
