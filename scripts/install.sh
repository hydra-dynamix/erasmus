#!/usr/bin/env bash

# Universal Installer for Watcher Project
# Supports Windows (via Git Bash/WSL), macOS, and Linux

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to the project root directory
PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT" || { echo -e "${RED}Failed to change to project root directory.${NC}"; exit 1; }

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)    OS='macOS' ;;
        Linux*)    OS='Linux' ;;
        MINGW*|MSYS*|CYGWIN*) OS='Windows' ;;
        *)         OS='Unknown' ;;
    esac
}


# Check and install prerequisites based on OS
check_prerequisites() {
    case "$OS" in
        Windows)
            echo -e "${YELLOW}Checking Windows prerequisites...${NC}"
            # Check if winget is available
            if ! command winget --version &> /dev/null; then
                echo -e "${RED}Error: winget is not available on this Windows system.${NC}"
                echo "Attempting to install winget..."
                # Try to install winget via PowerShell
                powershell.exe -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
                if ! command winget --version &> /dev/null; then
                    echo -e "${RED}Failed to install winget. Please install the App Installer from the Microsoft Store.${NC}"
                    echo "Visit: https://www.microsoft.com/store/productId/9NBLGGH4NNS1"
                    exit 1
                fi
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
            if ! command curl --version &> /dev/null; then
                echo -e "${RED}Error: curl is not installed.${NC}"
                echo "Installing curl..."
                sudo apt-get install curl -y
                if [ $? -ne 0 ]; then
                    echo -e "${RED}Failed to install curl. Please install it manually.${NC}"
                    exit 1
                fi
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
    UV_PATH="$HOME/.local/bin/uv"
    
    # Check if uv already exists at common location
    if [ -f "$UV_PATH" ]; then
        echo -e "${GREEN}uv package manager already exists.${NC}"
        export PATH="$HOME/.local/bin:$PATH"
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
            export PATH="$HOME/.local/bin:$PATH"
            ;;
    esac
    
    # Just export the PATH and move on
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}uv installation completed, continuing with setup...${NC}"
}

# Setup environment files
setup_env() {
    # Create .env.example with empty values
    cat > .env.example << EOL
IDE_ENV=cursor
GIT_TOKEN=sk-1234
OPENAI_API_KEY=sk-1234
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
EOL
    
    echo -e "${GREEN}Environment files created successfully for $IDE_ENV${NC}"
}

# Initialize Erasmus
init_watcher() {
    echo -e "${YELLOW}Initializing Erasmus...${NC}"
    
    # Create erasmus.py from the embedded content
    echo -e "${YELLOW}Extracting erasmus.py from watcher.py...${NC}"
    
    # Extract the base64 content from this script
    SCRIPT_PATH="$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}")"
    
    # Find the SHA256 hash in the script
    EXPECTED_HASH=$(grep -A 1 "BEGIN_HASH" "$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}")" | grep -v "BEGIN_HASH" | grep -v "END_HASH" | tr -d '# ')
    
    # If hash is empty, try alternative extraction method
    if [ -z "$EXPECTED_HASH" ]; then
        echo -e "${YELLOW}Trying alternative hash extraction method...${NC}"
        EXPECTED_HASH=$(grep -A 2 "BEGIN_HASH" "$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}")" | tail -n 1 | tr -d '# ')
    fi
    
    # If still empty, use the hash from the .sha256 file if it exists
    if [ -z "$EXPECTED_HASH" ] && [ -f "$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}" .sh).sha256" ]; then
        echo -e "${YELLOW}Using hash from .sha256 file...${NC}"
        EXPECTED_HASH=$(cat "$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}" .sh).sha256")
    fi
    
    # Extract the base64 content between markers
    BASE64_CONTENT=$(sed -n '/^# BEGIN_BASE64_CONTENT$/,/^# END_BASE64_CONTENT$/p' "$PROJECT_ROOT/$(basename "${BASH_SOURCE[0]}")" | grep -v "BEGIN_BASE64_CONTENT" | grep -v "END_BASE64_CONTENT" | tr -d '# ')
    
    if [ -z "$BASE64_CONTENT" ]; then
        echo -e "${RED}Error: Could not extract base64 content from installer.${NC}"
        exit 1
    fi
    
    # Decode the base64 content and save as erasmus.py
    echo "$BASE64_CONTENT" | base64 -d > erasmus.py
    
    # Verify the SHA256 hash
    if command -v shasum &> /dev/null; then
        ACTUAL_HASH=$(shasum -a 256 erasmus.py | cut -d ' ' -f 1)
    elif command -v sha256sum &> /dev/null; then
        ACTUAL_HASH=$(sha256sum erasmus.py | cut -d ' ' -f 1)
    else
        echo -e "${YELLOW}Warning: Could not verify SHA256 hash (shasum/sha256sum not available).${NC}"
        ACTUAL_HASH="unknown"
    fi
    
    if [ -z "$EXPECTED_HASH" ] || [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ] || [ "$ACTUAL_HASH" = "unknown" ]; then
        echo -e "${GREEN}Successfully extracted erasmus.py from watcher.py${NC}"
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
    
    # Run the erasmus setup with IDE environment
    echo -e "${YELLOW}Running erasmus setup...${NC}"
    uv run erasmus.py --setup "$IDE_ENV"
    
    echo -e "${GREEN}Erasmus initialized successfully!${NC}"
    echo -e "${YELLOW}To run Erasmus:${NC}"
    echo -e "    ${GREEN}uv run erasmus.py --watch${NC}"
}

# Main installation process
main() {
    echo -e "${YELLOW}Starting Erasmus installation...${NC}"
    
    # Detect the operating system
    detect_os
    echo -e "${GREEN}Detected OS: $OS${NC}"
    
    # Check and install prerequisites
    check_prerequisites
    
    # Install uv package manager
    install_uv
    
    # Setup environment files
    setup_env
    
    # Initialize Erasmus
    init_watcher
        
    echo -e "${GREEN}Erasmus installation completed successfully!${NC}"

    echo -e "Run \`uv run erasmus.py --setup\` to setup erasmus and \`uv run erasmus.py --watch\` to run the context overseer."
}

# Run the main installation function
main
