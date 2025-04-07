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


# __ERASMUS_EMBEDDED_BELOW__
# The content below this line is the base64-encoded erasmus.py file
# It will be extracted during installation
# SHA256_HASH=ba5c248edc0e28f45ae2815a63039757e56faab51971a862313cd7f7aac3c41b
exit 0

# BEGIN_BASE64_CONTENT
# IyEvdXNyL2Jpbi91diBydW4gLVMgCiMgLy8vIHNjcmlwdAojIHJlcXVpcmVzLXB5dGhvbiA9ICI+
# PTMuMTAiCiMgZGVwZW5kZW5jaWVzID0gWwojICAgICAib3BlbmFpIiwKIyAgICAgInB5dGhvbi1k
# b3RlbnYiLAojICAgICAicmljaCIsCiMgICAgICJ3YXRjaGRvZyIsCiMgXQojIC8vLwoKaW1wb3J0
# IG9zCmltcG9ydCBqc29uCmltcG9ydCB0aW1lCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgc3VicHJv
# Y2VzcwppbXBvcnQgcmUKaW1wb3J0IHN5cwpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKZnJvbSBy
# aWNoIGltcG9ydCBjb25zb2xlCmZyb20gcmljaC5sb2dnaW5nIGltcG9ydCBSaWNoSGFuZGxlcgpm
# cm9tIHdhdGNoZG9nLm9ic2VydmVycyBpbXBvcnQgT2JzZXJ2ZXIKZnJvbSB3YXRjaGRvZy5ldmVu
# dHMgaW1wb3J0IEZpbGVTeXN0ZW1FdmVudEhhbmRsZXIKZnJvbSB0aHJlYWRpbmcgaW1wb3J0IFRo
# cmVhZApmcm9tIG9wZW5haSBpbXBvcnQgT3BlbkFJCmZyb20gZG90ZW52IGltcG9ydCBsb2FkX2Rv
# dGVudgpmcm9tIGdldHBhc3MgaW1wb3J0IGdldHBhc3MKaW1wb3J0IGxvZ2dpbmcKZnJvbSB0eXBp
# bmcgaW1wb3J0IE9wdGlvbmFsLCBMaXN0LCBEaWN0LCBUdXBsZQoKR0lUX0NPTU1JVFMgPSBUcnVl
# CgojID09PSBUYXNrIFRyYWNraW5nID09PQpjbGFzcyBUYXNrU3RhdHVzOgogICAgUEVORElORyA9
# ICJwZW5kaW5nIgogICAgSU5fUFJPR1JFU1MgPSAiaW5fcHJvZ3Jlc3MiCiAgICBDT01QTEVURUQg
# PSAiY29tcGxldGVkIgogICAgQkxPQ0tFRCA9ICJibG9ja2VkIgogICAgTk9UX1NUQVJURUQgPSAi
# bm90X3N0YXJ0ZWQiCgpjbGFzcyBUYXNrOgogICAgZGVmIF9faW5pdF9fKHNlbGYsIGlkOiBzdHIs
# IGRlc2NyaXB0aW9uOiBzdHIpOgogICAgICAgIHNlbGYuaWQgPSBpZAogICAgICAgIHNlbGYuZGVz
# Y3JpcHRpb24gPSBkZXNjcmlwdGlvbgogICAgICAgIHNlbGYuc3RhdHVzID0gVGFza1N0YXR1cy5O
# T1RfU1RBUlRFRAogICAgICAgIHNlbGYuY3JlYXRlZF9hdCA9IHRpbWUudGltZSgpCiAgICAgICAg
# c2VsZi51cGRhdGVkX2F0ID0gdGltZS50aW1lKCkKICAgICAgICBzZWxmLmNvbXBsZXRpb25fdGlt
# ZSA9IE5vbmUKICAgICAgICBzZWxmLm5vdGVzID0gW10KICAgICAgICAKICAgIGRlZiB0b19kaWN0
# KHNlbGYpIC0+IGRpY3Q6CiAgICAgICAgIiIiQ29udmVydCB0YXNrIHRvIGRpY3Rpb25hcnkiIiIK
# ICAgICAgICByZXR1cm4gewogICAgICAgICAgICAiaWQiOiBzZWxmLmlkLAogICAgICAgICAgICAi
# ZGVzY3JpcHRpb24iOiBzZWxmLmRlc2NyaXB0aW9uLAogICAgICAgICAgICAic3RhdHVzIjogc2Vs
# Zi5zdGF0dXMsCiAgICAgICAgICAgICJjcmVhdGVkX2F0Ijogc2VsZi5jcmVhdGVkX2F0LAogICAg
# ICAgICAgICAidXBkYXRlZF9hdCI6IHNlbGYudXBkYXRlZF9hdCwKICAgICAgICAgICAgImNvbXBs
# ZXRpb25fdGltZSI6IHNlbGYuY29tcGxldGlvbl90aW1lLAogICAgICAgICAgICAibm90ZXMiOiBz
# ZWxmLm5vdGVzCiAgICAgICAgfQogICAgCiAgICBAY2xhc3NtZXRob2QKICAgIGRlZiBmcm9tX2Rp
# Y3QoY2xzLCBkYXRhOiBkaWN0KSAtPiAnVGFzayc6CiAgICAgICAgIiIiQ3JlYXRlIGEgdGFzayBm
# cm9tIGRpY3Rpb25hcnkiIiIKICAgICAgICB0YXNrID0gY2xzKGRhdGFbImlkIl0sIGRhdGFbImRl
# c2NyaXB0aW9uIl0pCiAgICAgICAgdGFzay5zdGF0dXMgPSBkYXRhWyJzdGF0dXMiXQogICAgICAg
# IHRhc2suY3JlYXRlZF9hdCA9IGRhdGFbImNyZWF0ZWRfYXQiXQogICAgICAgIHRhc2sudXBkYXRl
# ZF9hdCA9IGRhdGFbInVwZGF0ZWRfYXQiXQogICAgICAgIHRhc2suY29tcGxldGlvbl90aW1lID0g
# ZGF0YVsiY29tcGxldGlvbl90aW1lIl0KICAgICAgICB0YXNrLm5vdGVzID0gZGF0YVsibm90ZXMi
# XQogICAgICAgIHJldHVybiB0YXNrCgpjbGFzcyBUYXNrTWFuYWdlcjoKICAgIGRlZiBfX2luaXRf
# XyhzZWxmLCB0YXNrczogZGljdCA9IE5vbmUpOgogICAgICAgIHNlbGYudGFza3MgPSB7fQogICAg
# ICAgIGlmIHRhc2tzOgogICAgICAgICAgICBzZWxmLnRhc2tzID0gewogICAgICAgICAgICAgICAg
# dGFza19pZDogVGFzay5mcm9tX2RpY3QodGFza19kYXRhKSBpZiBpc2luc3RhbmNlKHRhc2tfZGF0
# YSwgZGljdCkgZWxzZSB0YXNrX2RhdGEKICAgICAgICAgICAgICAgIGZvciB0YXNrX2lkLCB0YXNr
# X2RhdGEgaW4gdGFza3MuaXRlbXMoKQogICAgICAgICAgICB9CiAgICAgICAgCiAgICBkZWYgYWRk
# X3Rhc2soc2VsZiwgZGVzY3JpcHRpb246IHN0cikgLT4gVGFzazoKICAgICAgICAiIiJBZGQgYSBu
# ZXcgdGFzayIiIgogICAgICAgIHRhc2tfaWQgPSBzdHIobGVuKHNlbGYudGFza3MpICsgMSkKICAg
# ICAgICB0YXNrID0gVGFzayh0YXNrX2lkLCBkZXNjcmlwdGlvbikKICAgICAgICBzZWxmLnRhc2tz
# W3Rhc2tfaWRdID0gdGFzawogICAgICAgIHJldHVybiB0YXNrCiAgICAKICAgIGRlZiBnZXRfdGFz
# ayhzZWxmLCB0YXNrX2lkOiBzdHIpIC0+IE9wdGlvbmFsW1Rhc2tdOgogICAgICAgICIiIkdldCBh
# IHRhc2sgYnkgSUQiIiIKICAgICAgICByZXR1cm4gc2VsZi50YXNrcy5nZXQodGFza19pZCkKICAg
# IAogICAgZGVmIGxpc3RfdGFza3Moc2VsZiwgc3RhdHVzOiBPcHRpb25hbFtUYXNrU3RhdHVzXSA9
# IE5vbmUpIC0+IExpc3RbVGFza106CiAgICAgICAgIiIiTGlzdCBhbGwgdGFza3MsIG9wdGlvbmFs
# bHkgZmlsdGVyZWQgYnkgc3RhdHVzIiIiCiAgICAgICAgdGFza3MgPSBsaXN0KHNlbGYudGFza3Mu
# dmFsdWVzKCkpCiAgICAgICAgaWYgc3RhdHVzOgogICAgICAgICAgICB0YXNrcyA9IFt0IGZvciB0
# IGluIHRhc2tzIGlmIHQuc3RhdHVzID09IHN0YXR1c10KICAgICAgICByZXR1cm4gdGFza3MKICAg
# IAogICAgZGVmIHVwZGF0ZV90YXNrX3N0YXR1cyhzZWxmLCB0YXNrX2lkOiBzdHIsIHN0YXR1czog
# VGFza1N0YXR1cykgLT4gTm9uZToKICAgICAgICAiIiJVcGRhdGUgYSB0YXNrJ3Mgc3RhdHVzIiIi
# CiAgICAgICAgaWYgdGFzayA6PSBzZWxmLmdldF90YXNrKHRhc2tfaWQpOgogICAgICAgICAgICB0
# YXNrLnN0YXR1cyA9IHN0YXR1cwogICAgCiAgICBkZWYgYWRkX25vdGVfdG9fdGFzayhzZWxmLCB0
# YXNrX2lkOiBzdHIsIG5vdGU6IHN0cikgLT4gTm9uZToKICAgICAgICAiIiJBZGQgYSBub3RlIHRv
# IGEgdGFzayIiIgogICAgICAgIGlmIHRhc2sgOj0gc2VsZi5nZXRfdGFzayh0YXNrX2lkKToKICAg
# ICAgICAgICAgdGFzay5ub3Rlcy5hcHBlbmQobm90ZSkKICAgIAogICAgQGNsYXNzbWV0aG9kCiAg
# ICBkZWYgZnJvbV9kaWN0KGNscywgZGF0YSk6CiAgICAgICAgIiIiQ3JlYXRlIGEgVGFza01hbmFn
# ZXIgZnJvbSBhIGRpY3Rpb25hcnkiIiIKICAgICAgICBtYW5hZ2VyID0gY2xzKCkKICAgICAgICBp
# ZiBpc2luc3RhbmNlKGRhdGEsIGRpY3QpOgogICAgICAgICAgICBtYW5hZ2VyLnRhc2tzID0gewog
# ICAgICAgICAgICAgICAgdGFza19pZDogVGFzay5mcm9tX2RpY3QodGFza19kYXRhKQogICAgICAg
# ICAgICAgICAgZm9yIHRhc2tfaWQsIHRhc2tfZGF0YSBpbiBkYXRhLml0ZW1zKCkKICAgICAgICAg
# ICAgfQogICAgICAgIHJldHVybiBtYW5hZ2VyCgpkZWYgaXNfdmFsaWRfdXJsKHVybDogc3RyKSAt
# PiBib29sOgogICAgIiIiQmFzaWMgVVJMIHZhbGlkYXRpb24gdXNpbmcgcmVnZXguIiIiCiAgICBs
# b2dnZXIuZGVidWcoZiJWYWxpZGF0aW5nIFVSTDoge3VybH0iKQogICAgaHR0cHNfcGF0dGVybiA9
# IHJlLm1hdGNoKHInXmh0dHBzPzovLycsIHVybCkKICAgIGxvZ2dlci5kZWJ1ZyhmImh0dHBzX3Bh
# dHRlcm46IHtodHRwc19wYXR0ZXJufSIpCiAgICBodHRwX3BhdHRlcm4gPSByZS5tYXRjaChyJ15o
# dHRwPzovLycsIHVybCkKICAgIGxvZ2dlci5kZWJ1ZyhmImh0dHBfcGF0dGVybjoge2h0dHBfcGF0
# dGVybn0iKQogICAgcmV0dXJuIGh0dHBzX3BhdHRlcm4gb3IgaHR0cF9wYXR0ZXJuCgojID09PSBP
# cGVuQUkgQ29uZmlndXJhdGlvbiA9PT0KCgpkZWYgaXNfdmFsaWRfdXJsKHVybDogc3RyKSAtPiBi
# b29sOgogICAgIiIiQmFzaWMgVVJMIHZhbGlkYXRpb24gdXNpbmcgcmVnZXguCiAgICAKICAgIEFj
# Y2VwdHM6CiAgICAtIFN0YW5kYXJkIGh0dHAvaHR0cHMgVVJMcyAoZS5nLiwgaHR0cHM6Ly9hcGku
# b3BlbmFpLmNvbS92MSkKICAgIC0gTG9jYWxob3N0IFVSTHMgd2l0aCBvcHRpb25hbCBwb3J0IChl
# LmcuLCBodHRwOi8vbG9jYWxob3N0OjExNDM0KQogICAgLSBJUC1iYXNlZCBsb2NhbGhvc3QgVVJM
# cyAoZS5nLiwgaHR0cDovLzEyNy4wLjAuMTo4MDAwKQogICAgCiAgICBBcmdzOgogICAgICAgIHVy
# bDogVVJMIHN0cmluZyB0byB2YWxpZGF0ZQogICAgICAgIAogICAgUmV0dXJuczoKICAgICAgICBi
# b29sOiBUcnVlIGlmIHRoZSBVUkwgaXMgdmFsaWQsIEZhbHNlIG90aGVyd2lzZQogICAgIiIiCiAg
# ICBpZiBub3QgdXJsOgogICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICAjIExvZyB0aGUgVVJM
# IGJlaW5nIHZhbGlkYXRlZCBmb3IgZGVidWdnaW5nCiAgICBsb2dnZXIuZGVidWcoZiJWYWxpZGF0
# aW5nIFVSTDoge3VybH0iKQogICAgCiAgICAjIENoZWNrIGZvciBsb2NhbGhvc3Qgb3IgMTI3LjAu
# MC4xCiAgICBsb2NhbGhvc3RfcGF0dGVybiA9IHJlLm1hdGNoKHInXmh0dHBzPzovLyg/OmxvY2Fs
# aG9zdHwxMjdcLjBcLjBcLjEpKD86OlxkKyk/KD86Ly4qKT8kJywgdXJsKQogICAgaWYgbG9jYWxo
# b3N0X3BhdHRlcm46CiAgICAgICAgbG9nZ2VyLmRlYnVnKGYiVVJMIHt1cmx9IG1hdGNoZWQgbG9j
# YWxob3N0IHBhdHRlcm4iKQogICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgCiAgICAjIENoZWNr
# IGZvciBzdGFuZGFyZCBodHRwL2h0dHBzIFVSTHMKICAgIHN0YW5kYXJkX3BhdHRlcm4gPSByZS5t
# YXRjaChyJ15odHRwcz86Ly9bXHdcLi1dKyg/OjpcZCspPyg/Oi8uKik/JCcsIHVybCkKICAgIHJl
# c3VsdCA9IGJvb2woc3RhbmRhcmRfcGF0dGVybikKICAgIAogICAgaWYgcmVzdWx0OgogICAgICAg
# IGxvZ2dlci5kZWJ1ZyhmIlVSTCB7dXJsfSBtYXRjaGVkIHN0YW5kYXJkIHBhdHRlcm4iKQogICAg
# ZWxzZToKICAgICAgICBsb2dnZXIud2FybmluZyhmIlVSTCB2YWxpZGF0aW9uIGZhaWxlZCBmb3I6
# IHt1cmx9IikKICAgICAgICAKICAgIHJldHVybiByZXN1bHQKCmRlZiBkZXRlY3RfaWRlX2Vudmly
# b25tZW50KCkgLT4gc3RyOgogICAgIiIiCiAgICBEZXRlY3QgdGhlIGN1cnJlbnQgSURFIGVudmly
# b25tZW50LgogICAgCiAgICBSZXR1cm5zOgogICAgICAgIHN0cjogRGV0ZWN0ZWQgSURFIGVudmly
# b25tZW50ICgnV0lORFNVUkYnLCAnQ1VSU09SJywgb3IgJycpCiAgICAiIiIKICAgICMgQ2hlY2sg
# ZW52aXJvbm1lbnQgdmFyaWFibGUgZmlyc3QKICAgIGlkZV9lbnYgPSBvcy5nZXRlbnYoJ0lERV9F
# TlYnLCAnJykudXBwZXIoKQogICAgaWYgaWRlX2VudjoKICAgICAgICByZXR1cm4gJ1dJTkRTVVJG
# JyBpZiBpZGVfZW52LnN0YXJ0c3dpdGgoJ1cnKSBlbHNlICdDVVJTT1InCiAgICAKICAgICMgVHJ5
# IHRvIGRldGVjdCBiYXNlZCBvbiBjdXJyZW50IHdvcmtpbmcgZGlyZWN0b3J5IG9yIGtub3duIElE
# RSBwYXRocwogICAgY3dkID0gUGF0aC5jd2QoKQogICAgCiAgICAjIFdpbmRzdXJmLXNwZWNpZmlj
# IGRldGVjdGlvbgogICAgd2luZHN1cmZfbWFya2VycyA9IFsKICAgICAgICBQYXRoLmhvbWUoKSAv
# ICcuY29kZWl1bScgLyAnd2luZHN1cmYnLAogICAgICAgIGN3ZCAvICcud2luZHN1cmZydWxlcycK
# ICAgIF0KICAgIAogICAgIyBDdXJzb3Itc3BlY2lmaWMgZGV0ZWN0aW9uCiAgICBjdXJzb3JfbWFy
# a2VycyA9IFsKICAgICAgICBjd2QgLyAnLmN1cnNvcnJ1bGVzJywKICAgICAgICBQYXRoLmhvbWUo
# KSAvICcuY3Vyc29yJwogICAgXQogICAgCiAgICAjIENoZWNrIFdpbmRzdXJmIG1hcmtlcnMKICAg
# IGZvciBtYXJrZXIgaW4gd2luZHN1cmZfbWFya2VyczoKICAgICAgICBpZiBtYXJrZXIuZXhpc3Rz
# KCk6CiAgICAgICAgICAgIHJldHVybiAnV0lORFNVUkYnCiAgICAKICAgICMgQ2hlY2sgQ3Vyc29y
# IG1hcmtlcnMKICAgIGZvciBtYXJrZXIgaW4gY3Vyc29yX21hcmtlcnM6CiAgICAgICAgaWYgbWFy
# a2VyLmV4aXN0cygpOgogICAgICAgICAgICByZXR1cm4gJ0NVUlNPUicKICAgIAogICAgIyBEZWZh
# dWx0IGZhbGxiYWNrCiAgICByZXR1cm4gJ1dJTkRTVVJGJwoKCmRlZiBwcm9tcHRfb3BlbmFpX2Ny
# ZWRlbnRpYWxzKGVudl9wYXRoPSIuZW52Iik6CiAgICAiIiJQcm9tcHQgdXNlciBmb3IgT3BlbkFJ
# IGNyZWRlbnRpYWxzIGFuZCBzYXZlIHRvIC5lbnYiIiIKICAgIAogICAgYXBpX2tleSA9IG9zLmdl
# dGVudigiT1BFTkFJX0FQSV9LRVkiKQogICAgaWYgbm90IGFwaV9rZXk6CiAgICAgICAgcHJpbnQo
# IklmIHlvdSBhcmUgcnVubmluZyBsb2NhbCBpbmZlcmVuY2UgYW5kIGRvIG5vdCBoYXZlIGFuIGFw
# aSBrZXkgY29uZmlndXJlZCBqdXN0IHVzZSBzay0xMjM0IikKICAgICAgICBhcGlfa2V5ID0gZ2V0
# cGFzcygiRW50ZXIgeW91ciBPUEVOQUlfQVBJX0tFWSAoaW5wdXQgaGlkZGVuKTogIikKICAgICAg
# ICBpZiBub3QgYXBpX2tleToKICAgICAgICAgICAgcHJpbnQoIkFQSSBLZXkgbWlzc2luZy4gRGlz
# YWJsaW5nIGNvbW1pdCBtZXNzYWdlIGdlbmVyYXRpb24uIikKICAgICAgICAgICAgR0lUX0NPTU1J
# VFM9RmFsc2UKICAgICAgICAgICAgYXBpX2tleSA9ICJzay0xMjM0IgoKICAgIGJhc2VfdXJsID0g
# b3MuZ2V0ZW52KCJPUEVOQUlfQkFTRV9VUkwiKQogICAgaWYgbm90IGJhc2VfdXJsOgogICAgICAg
# IHByaW50KCJFbnRlciB5b3VyIE9wZW5BSSBiYXNlIFVSTC4iKQogICAgICAgIHByaW50KCJJZiB5
# b3UgYXJlIHJ1bm5pbmcgbG9jYWwgaW5mZXJlbmNlIHVzZSB5b3VyIGxvY2FsIGhvc3QgdXJsKGUu
# Zy4gZm9yIG9sbGFtYTogaHR0cDovL2xvY2FsaG9zdDoxMTQzNCkiKQogICAgICAgIGJhc2VfdXJs
# ID0gaW5wdXQoIkVudGVyIHlvdXIgT1BFTkFJX0JBU0VfVVJMIChkZWZhdWx0OiBodHRwczovL2Fw
# aS5vcGVuYWkuY29tL3YxKTogIikuc3RyaXAoKQogICAgICAgIGlmIG5vdCBpc192YWxpZF91cmwo
# YmFzZV91cmwpOgogICAgICAgICAgICBwcmludCgiSW52YWxpZCBVUkwgb3IgZW1wdHkuIERlZmF1
# bHRpbmcgdG8gaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIpCiAgICAgICAgICAgIGJhc2VfdXJs
# ID0gImh0dHBzOi8vYXBpLm9wZW5haS5jb20vdjEiCgogICAgbW9kZWwgPSBvcy5nZXRlbnYoIk9Q
# RU5BSV9NT0RFTCIpCiAgICBpZiBub3QgbW9kZWw6CiAgICAgICAgbW9kZWwgPSBpbnB1dCgiRW50
# ZXIgeW91ciBPUEVOQUlfTU9ERUwgKGRlZmF1bHQ6IGdwdC00byk6ICIpLnN0cmlwKCkKICAgICAg
# ICBpZiBub3QgbW9kZWw6CiAgICAgICAgICAgIG1vZGVsID0gImdwdC00byIKICAgICAgICAKICAg
# ICMgRGV0ZWN0IElERSBlbnZpcm9ubWVudCBhbmQgc2F2ZSBpdCB0byB0aGUgLmVudiBmaWxlCiAg
# ICBpZGVfZW52ID0gZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpCiAgICAKICAgIGVudl9jb250ZW50
# ID0gKAogICAgICAgICJcbiIKICAgICAgICBmIk9QRU5BSV9BUElfS0VZPXthcGlfa2V5fVxuIgog
# ICAgICAgIGYiT1BFTkFJX0JBU0VfVVJMPXtiYXNlX3VybH1cbiIKICAgICAgICBmIk9QRU5BSV9N
# T0RFTD17bW9kZWx9XG4iCiAgICAgICAgZiJJREVfRU5WPXtpZGVfZW52fVxuIgogICAgKQogICAg
# ZW52cGF0aCA9IFBhdGgoZW52X3BhdGgpCiAgICBpZiBub3QgZW52cGF0aC5leGlzdHMoKToKICAg
# ICAgICBlbnZwYXRoLndyaXRlX3RleHQoIiMgRW52aXJvbm1lbnQgVmFyaWFibGVzIikKICAgIGV4
# aXN0aW5nX2NvbnRlbnQgPSBlbnZwYXRoLnJlYWRfdGV4dCgpCiAgICBlbnZfY29udGVudCA9IGV4
# aXN0aW5nX2NvbnRlbnQgKyBlbnZfY29udGVudAoKICAgIGVudnBhdGgud3JpdGVfdGV4dChlbnZf
# Y29udGVudCkKICAgIGxvYWRfZG90ZW52KCkKICAgIHByaW50KGYi4pyFIE9wZW5BSSBjcmVkZW50
# aWFscyBzYXZlZCB0byB7ZW52X3BhdGh9IikKCiMgPT09IENvbmZpZ3VyYXRpb24gYW5kIFNldHVw
# ID09PQpsb2FkX2RvdGVudigpCgojIENvbmZpZ3VyZSByaWNoIGNvbnNvbGUgYW5kIGxvZ2dpbmcK
# Y29uc29sZSA9IGNvbnNvbGUuQ29uc29sZSgpCmxvZ2dpbmdfaGFuZGxlciA9IFJpY2hIYW5kbGVy
# KAogICAgY29uc29sZT1jb25zb2xlLAogICAgc2hvd190aW1lPVRydWUsCiAgICBzaG93X3BhdGg9
# RmFsc2UsCiAgICByaWNoX3RyYWNlYmFja3M9VHJ1ZSwKICAgIHRyYWNlYmFja3Nfc2hvd19sb2Nh
# bHM9VHJ1ZQopCgojIFNldCB1cCBsb2dnaW5nIGNvbmZpZ3VyYXRpb24KbG9nZ2luZy5iYXNpY0Nv
# bmZpZygKICAgIGxldmVsPW9zLmdldGVudigiTE9HX0xFVkVMIiwgIklORk8iKSwKICAgIGZvcm1h
# dD0iJShtZXNzYWdlKXMiLAogICAgZGF0ZWZtdD0iWyVYXSIsCiAgICBoYW5kbGVycz1bbG9nZ2lu
# Z19oYW5kbGVyXQopCgojIENyZWF0ZSBsb2dnZXIgaW5zdGFuY2UKbG9nZ2VyID0gbG9nZ2luZy5n
# ZXRMb2dnZXIoImNvbnRleHRfd2F0Y2hlciIpCgojIEFkZCBmaWxlIGhhbmRsZXIgZm9yIHBlcnNp
# c3RlbnQgbG9nZ2luZwp0cnk6CiAgICBmaWxlX2hhbmRsZXIgPSBsb2dnaW5nLkZpbGVIYW5kbGVy
# KCJjb250ZXh0X3dhdGNoZXIubG9nIikKICAgIGZpbGVfaGFuZGxlci5zZXRMZXZlbChsb2dnaW5n
# LkRFQlVHKQogICAgZmlsZV9mb3JtYXR0ZXIgPSBsb2dnaW5nLkZvcm1hdHRlcignJShhc2N0aW1l
# KXMgLSAlKG5hbWUpcyAtICUobGV2ZWxuYW1lKXMgLSAlKG1lc3NhZ2UpcycpCiAgICBmaWxlX2hh
# bmRsZXIuc2V0Rm9ybWF0dGVyKGZpbGVfZm9ybWF0dGVyKQogICAgbG9nZ2VyLmFkZEhhbmRsZXIo
# ZmlsZV9oYW5kbGVyKQpleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICBsb2dnZXIud2FybmluZyhm
# IkNvdWxkIG5vdCBzZXQgdXAgZmlsZSBsb2dnaW5nOiB7ZX0iKQoKZGVmIGdldF9vcGVuYWlfY3Jl
# ZGVudGlhbHMoKToKICAgICIiIkdldCBPcGVuQUkgY3JlZGVudGlhbHMgZnJvbSBlbnZpcm9ubWVu
# dCB2YXJpYWJsZXMiIiIKICAgIGFwaV9rZXkgPSBvcy5lbnZpcm9uLmdldCgiT1BFTkFJX0FQSV9L
# RVkiKQogICAgaWYgbm90IGFwaV9rZXk6CiAgICAgICAgR0lUX0NPTU1JVFMgPSBGYWxzZQogICAg
# YmFzZV91cmwgPSBvcy5lbnZpcm9uLmdldCgiT1BFTkFJX0JBU0VfVVJMIikKICAgIG1vZGVsID0g
# b3MuZW52aXJvbi5nZXQoIk9QRU5BSV9NT0RFTCIpCiAgICByZXR1cm4gYXBpX2tleSwgYmFzZV91
# cmwsIG1vZGVsCgojIC0tLSBPcGVuQUkgQ2xpZW50IEluaXRpYWxpemF0aW9uIC0tLQpkZWYgaW5p
# dF9vcGVuYWlfY2xpZW50KCk6CiAgICAiIiJJbml0aWFsaXplIGFuZCByZXR1cm4gT3BlbkFJIGNs
# aWVudCBjb25maWd1cmF0aW9uIiIiCiAgICB0cnk6CiAgICAgICAgYXBpX2tleSwgYmFzZV91cmws
# IG1vZGVsID0gZ2V0X29wZW5haV9jcmVkZW50aWFscygpCiAgICAgICAgCiAgICAgICAgIyBDaGVj
# ayBpZiBhbnkgY3JlZGVudGlhbHMgYXJlIG1pc3NpbmcKICAgICAgICBtaXNzaW5nX2NyZWRzID0g
# W10KICAgICAgICBpZiBub3QgYXBpX2tleToKICAgICAgICAgICAgbWlzc2luZ19jcmVkcy5hcHBl
# bmQoIkFQSSBrZXkiKQogICAgICAgIGlmIG5vdCBiYXNlX3VybDoKICAgICAgICAgICAgbWlzc2lu
# Z19jcmVkcy5hcHBlbmQoImJhc2UgVVJMIikKICAgICAgICBpZiBub3QgbW9kZWw6CiAgICAgICAg
# ICAgIG1pc3NpbmdfY3JlZHMuYXBwZW5kKCJtb2RlbCIpCgogICAgICAgICAgICAKICAgICAgICBp
# ZiBtaXNzaW5nX2NyZWRzOgogICAgICAgICAgICBsb2dnZXIud2FybmluZyhmIk1pc3NpbmcgT3Bl
# bkFJIGNyZWRlbnRpYWxzOiB7JywgJy5qb2luKG1pc3NpbmdfY3JlZHMpfS4gUHJvbXB0aW5nIGZv
# ciBpbnB1dC4uLiIpCiAgICAgICAgICAgIHByb21wdF9vcGVuYWlfY3JlZGVudGlhbHMoKQogICAg
# ICAgICAgICBhcGlfa2V5LCBiYXNlX3VybCwgbW9kZWwgPSBnZXRfb3BlbmFpX2NyZWRlbnRpYWxz
# KCkKICAgICAgICAgICAgCiAgICAgICAgICAgICMgQ2hlY2sgYWdhaW4gYWZ0ZXIgcHJvbXB0aW5n
# CiAgICAgICAgICAgIGlmIG5vdCBhcGlfa2V5OgogICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9y
# KCJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBPcGVuQUkgY2xpZW50OiBtaXNzaW5nIEFQSSBrZXkiKQog
# ICAgICAgICAgICAgICAgR0lUX0NPTU1JVFMgPSBGYWxzZQogICAgICAgICAgICAgICAgcmV0dXJu
# IE5vbmUsIE5vbmUKICAgICAgICAgICAgaWYgbm90IG1vZGVsOgogICAgICAgICAgICAgICAgbG9n
# Z2VyLmVycm9yKCJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBPcGVuQUkgY2xpZW50OiBtaXNzaW5nIG1v
# ZGVsIG5hbWUiKQogICAgICAgICAgICAgICAgcmV0dXJuIE5vbmUsIE5vbmUKICAgICAgICAKICAg
# ICAgICAjIEVuc3VyZSBiYXNlX3VybCBoYXMgYSB2YWxpZCBmb3JtYXQKICAgICAgICBpZiBub3Qg
# YmFzZV91cmw6CiAgICAgICAgICAgIGJhc2VfdXJsID0gImh0dHBzOi8vYXBpLm9wZW5haS5jb20v
# djEiCiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKGYiVXNpbmcgZGVmYXVsdCBPcGVuQUkgYmFz
# ZSBVUkw6IHtiYXNlX3VybH0iKQogICAgICAgIGVsaWYgbm90IGlzX3ZhbGlkX3VybChiYXNlX3Vy
# bCk6CiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKGYiSW52YWxpZCBiYXNlIFVSTCBmb3JtYXQ6
# IHtiYXNlX3VybH0uIFVzaW5nIGRlZmF1bHQuIikKICAgICAgICAgICAgYmFzZV91cmwgPSAiaHR0
# cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIKICAgICAgICAKICAgICAgICBsb2dnZXIuaW5mbyhmIklu
# aXRpYWxpemluZyBPcGVuQUkgY2xpZW50IHdpdGggYmFzZSBVUkw6IHtiYXNlX3VybH0gYW5kIG1v
# ZGVsOiB7bW9kZWx9IikKICAgICAgICBjbGllbnQgPSBPcGVuQUkoYXBpX2tleT1hcGlfa2V5LCBi
# YXNlX3VybD1iYXNlX3VybCkKICAgICAgICByZXR1cm4gY2xpZW50LCBtb2RlbAogICAgZXhjZXB0
# IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBpbml0aWFs
# aXplIE9wZW5BSSBjbGllbnQ6IHtlfSIpCiAgICAgICAgcmV0dXJuIE5vbmUsIE5vbmUKCiMgR2xv
# YmFsIHZhcmlhYmxlcwpDTElFTlQsIE9QRU5BSV9NT0RFTCA9IGluaXRfb3BlbmFpX2NsaWVudCgp
# CgoKUFdEID0gUGF0aChfX2ZpbGVfXykucGFyZW50CgojID09PSBBcmd1bWVudCBQYXJzaW5nID09
# PQpkZWYgcGFyc2VfYXJndW1lbnRzKCk6CiAgICBwYXJzZXIgPSBhcmdwYXJzZS5Bcmd1bWVudFBh
# cnNlcihkZXNjcmlwdGlvbj0iVXBkYXRlIHNjcmlwdCBmb3IgcHJvamVjdCIpCiAgICBwYXJzZXIu
# YWRkX2FyZ3VtZW50KCItLXdhdGNoIiwgYWN0aW9uPSJzdG9yZV90cnVlIiwgaGVscD0iRW5hYmxl
# IGZpbGUgd2F0Y2hpbmciKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS11cGRhdGUiLCBjaG9p
# Y2VzPVsiYXJjaGl0ZWN0dXJlIiwgInByb2dyZXNzIiwgInRhc2tzIiwgImNvbnRleHQiXSwgCiAg
# ICAgICAgICAgICAgICAgICAgICBoZWxwPSJGaWxlIHRvIHVwZGF0ZSIpCiAgICBwYXJzZXIuYWRk
# X2FyZ3VtZW50KCItLXVwZGF0ZS12YWx1ZSIsIGhlbHA9Ik5ldyB2YWx1ZSB0byB3cml0ZSB0byB0
# aGUgc3BlY2lmaWVkIGZpbGUiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1zZXR1cCIsIGNo
# b2ljZXM9WyJjdXJzb3IiLCAid2luZHN1cmYiLCAiQ1VSU09SIiwgIldJTkRTVVJGIl0sIGhlbHA9
# IlNldHVwIHByb2plY3QiLCBkZWZhdWx0PSJjdXJzb3IiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVu
# dCgiLS10eXBlIiwgY2hvaWNlcz1bImN1cnNvciIsICJ3aW5kc3VyZiIsICJDVVJTT1IiLCAiV0lO
# RFNVUkYiXSwgaGVscD0iUHJvamVjdCB0eXBlIiwgZGVmYXVsdD0iY3Vyc29yIikKICAgIAogICAg
# IyBUYXNrIG1hbmFnZW1lbnQgYXJndW1lbnRzCiAgICB0YXNrX2dyb3VwID0gcGFyc2VyLmFkZF9h
# cmd1bWVudF9ncm91cCgiVGFzayBNYW5hZ2VtZW50IikKICAgIHRhc2tfZ3JvdXAuYWRkX2FyZ3Vt
# ZW50KCItLXRhc2stYWN0aW9uIiwgY2hvaWNlcz1bImFkZCIsICJ1cGRhdGUiLCAibm90ZSIsICJs
# aXN0IiwgImdldCJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICBoZWxwPSJUYXNrIG1hbmFn
# ZW1lbnQgYWN0aW9uIikKICAgIHRhc2tfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLXRhc2staWQiLCBo
# ZWxwPSJUYXNrIElEIGZvciB1cGRhdGUvbm90ZS9nZXQgYWN0aW9ucyIpCiAgICB0YXNrX2dyb3Vw
# LmFkZF9hcmd1bWVudCgiLS10YXNrLWRlc2NyaXB0aW9uIiwgaGVscD0iVGFzayBkZXNjcmlwdGlv
# biBmb3IgYWRkIGFjdGlvbiIpCiAgICB0YXNrX2dyb3VwLmFkZF9hcmd1bWVudCgiLS10YXNrLXN0
# YXR1cyIsIGNob2ljZXM9W1Rhc2tTdGF0dXMuUEVORElORywgVGFza1N0YXR1cy5JTl9QUk9HUkVT
# UywgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
# VGFza1N0YXR1cy5DT01QTEVURUQsIFRhc2tTdGF0dXMuQkxPQ0tFRF0sCiAgICAgICAgICAgICAg
# ICAgICAgICAgICAgIGhlbHA9IlRhc2sgc3RhdHVzIGZvciB1cGRhdGUgYWN0aW9uIikKICAgIHRh
# c2tfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLXRhc2stbm90ZSIsIGhlbHA9Ik5vdGUgY29udGVudCBm
# b3Igbm90ZSBhY3Rpb24iKQogICAgCiAgICAjIEdpdCBtYW5hZ2VtZW50IGFyZ3VtZW50cwogICAg
# Z2l0X2dyb3VwID0gcGFyc2VyLmFkZF9hcmd1bWVudF9ncm91cCgiR2l0IE1hbmFnZW1lbnQiKQog
# ICAgZ2l0X2dyb3VwLmFkZF9hcmd1bWVudCgiLS1naXQtcmVwbyIsIGhlbHA9IlBhdGggdG8gZ2l0
# IHJlcG9zaXRvcnkiKQogICAgZ2l0X2dyb3VwLmFkZF9hcmd1bWVudCgiLS1naXQtYWN0aW9uIiwg
# Y2hvaWNlcz1bInN0YXR1cyIsICJicmFuY2giLCAiY29tbWl0IiwgInB1c2giLCAicHVsbCJdLAog
# ICAgICAgICAgICAgICAgICAgICAgICAgIGhlbHA9IkdpdCBhY3Rpb24gdG8gcGVyZm9ybSIpCiAg
# ICBnaXRfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLWNvbW1pdC1tZXNzYWdlIiwgaGVscD0iQ29tbWl0
# IG1lc3NhZ2UgZm9yIGdpdCBjb21taXQgYWN0aW9uIikKICAgIGdpdF9ncm91cC5hZGRfYXJndW1l
# bnQoIi0tYnJhbmNoLW5hbWUiLCBoZWxwPSJCcmFuY2ggbmFtZSBmb3IgZ2l0IGJyYW5jaCBhY3Rp
# b24iKQogICAgCiAgICByZXR1cm4gcGFyc2VyLnBhcnNlX2FyZ3MoKQoKIyBHbG9iYWwgcnVsZXMg
# Y29udGVudCBmb3IgcHJvamVjdCBzZXR1cApHTE9CQUxfUlVMRVMgPSAiIiIKIyDwn6egIExlYWQg
# RGV2ZWxvcGVyIOKAkyBQcm9tcHQgQ29udGV4dAoKIyMg8J+OryBPQkpFQ1RJVkUKCllvdSBhcmUg
# YSAqKkxlYWQgRGV2ZWxvcGVyKiogd29ya2luZyBhbG9uZ3NpZGUgYSBodW1hbiBwcm9qZWN0IG93
# bmVyLiBZb3VyIHJvbGUgaXMgdG8gaW1wbGVtZW50IGhpZ2gtcXVhbGl0eSBjb2RlIGJhc2VkIG9u
# ICoqcmVxdWlyZW1lbnRzKiogYW5kICoqYXJjaGl0ZWN0dXJlKiogZG9jdW1lbnRhdGlvbiwgZm9s
# bG93aW5nIGJlc3QgcHJhY3RpY2VzOgoKLSBVc2Ugc3Ryb25nIHR5cGluZyBhbmQgaW5saW5lIGRv
# Y3VtZW50YXRpb24uCi0gUHJpb3JpdGl6ZSBjbGFyaXR5IGFuZCBwcm9kdWN0aW9uLXJlYWRpbmVz
# cyBvdmVyIHVubmVjZXNzYXJ5IGFic3RyYWN0aW9uLgotIE9wdGltaXplIHRob3VnaHRmdWxseSwg
# d2l0aG91dCBzYWNyaWZpY2luZyBtYWludGFpbmFiaWxpdHkuCi0gQXZvaWQgc2xvcHB5IG9yIHVu
# ZG9jdW1lbnRlZCBpbXBsZW1lbnRhdGlvbnMuCgpZb3UgYXJlIGVuY291cmFnZWQgdG8gKipjcml0
# aWNhbGx5IGV2YWx1YXRlIGRlc2lnbnMqKiBhbmQgaW1wcm92ZSB0aGVtIHdoZXJlIGFwcHJvcHJp
# YXRlLiBXaGVuIGluIGRvdWJ0LCAqKmFzayBxdWVzdGlvbnMqKiDigJQgY2xhcml0eSBpcyBtb3Jl
# IHZhbHVhYmxlIHRoYW4gYXNzdW1wdGlvbnMuCgotLS0KCiMjIPCfm6DvuI8gVE9PTFMKCllvdSB3
# aWxsIGJlIGdpdmVuIGFjY2VzcyB0byB2YXJpb3VzIGRldmVsb3BtZW50IHRvb2xzLiBVc2UgdGhl
# bSBhcyBhcHByb3ByaWF0ZS4gQWRkaXRpb25hbCAqKk1DUCBzZXJ2ZXIgdG9vbHMqKiBtYXkgYmUg
# aW50cm9kdWNlZCBsYXRlciwgd2l0aCB1c2FnZSBpbnN0cnVjdGlvbnMgYXBwZW5kZWQgaGVyZS4K
# Ci0tLQoKIyMg8J+TmiBET0NVTUVOVEFUSU9OCgpZb3VyIHdvcmtzcGFjZSByb290IGNvbnRhaW5z
# IHRocmVlIGtleSBkb2N1bWVudHM6CgotICoqQVJDSElURUNUVVJFLm1kKiogIAogIFByaW1hcnkg
# c291cmNlIG9mIHRydXRoLiBDb250YWlucyBhbGwgbWFqb3IgY29tcG9uZW50cyBhbmQgdGhlaXIg
# cmVxdWlyZW1lbnRzLiAgCiAg4oaSIElmIG1pc3NpbmcsIGFzayB0aGUgdXNlciBmb3IgcmVxdWly
# ZW1lbnRzIGFuZCBnZW5lcmF0ZSB0aGlzIGRvY3VtZW50LgoKLSAqKlBST0dSRVNTLm1kKiogIAog
# IFRyYWNrcyBtYWpvciBjb21wb25lbnRzIGFuZCBvcmdhbml6ZXMgdGhlbSBpbnRvIGEgZGV2ZWxv
# cG1lbnQgc2NoZWR1bGUuICAKICDihpIgSWYgbWlzc2luZywgZ2VuZXJhdGUgZnJvbSBgQVJDSElU
# RUNUVVJFLm1kYC4KCi0gKipUQVNLUy5tZCoqICAKICBDb250YWlucyBhY3Rpb24tb3JpZW50ZWQg
# dGFza3MgcGVyIGNvbXBvbmVudCwgc21hbGwgZW5vdWdoIHRvIGRldmVsb3AgYW5kIHRlc3QgaW5k
# ZXBlbmRlbnRseS4gIAogIOKGkiBJZiBtaXNzaW5nLCBzZWxlY3QgdGhlIG5leHQgY29tcG9uZW50
# IGZyb20gYFBST0dSRVNTLm1kYCBhbmQgYnJlYWsgaXQgaW50byB0YXNrcy4KCi0tLQoKIyMg8J+U
# gSBXT1JLRkxPVwoKYGBgbWVybWFpZApmbG93Y2hhcnQgVEQKICAgIFN0YXJ0KFtTdGFydF0pCiAg
# ICBDaGVja0FyY2hpdGVjdHVyZXtBUkNISVRFQ1RVUkUgZXhpc3RzP30KICAgIEFza1JlcXVpcmVt
# ZW50c1siQXNrIHVzZXIgZm9yIHJlcXVpcmVtZW50cyJdCiAgICBDaGVja1Byb2dyZXNze1BST0dS
# RVNTIGV4aXN0cz99CiAgICBCcmVha0Rvd25BcmNoWyJCcmVhayBBUkNISVRFQ1RVUkUgaW50byBt
# YWpvciBjb21wb25lbnRzIl0KICAgIERldlNjaGVkdWxlWyJPcmdhbml6ZSBjb21wb25lbnRzIGlu
# dG8gYSBkZXYgc2NoZWR1bGUiXQogICAgQ2hlY2tUYXNrc3tUQVNLUyBleGlzdD99CiAgICBDcmVh
# dGVUYXNrc1siQnJlYWsgbmV4dCBjb21wb25lbnQgaW50byBpbmRpdmlkdWFsIHRhc2tzIl0KICAg
# IFJldmlld1Rhc2tzWyJSZXZpZXcgVEFTS1MiXQogICAgRGV2VGFza1siRGV2ZWxvcCBhIHRhc2si
# XQogICAgVGVzdFRhc2tbIlRlc3QgdGhlIHRhc2sgdW50aWwgaXQgcGFzc2VzIl0KICAgIFVwZGF0
# ZVRhc2tzWyJVcGRhdGUgVEFTS1MiXQogICAgSXNQcm9ncmVzc0NvbXBsZXRle0FsbCBQUk9HUkVT
# UyBjb21wbGV0ZWQ/fQogICAgTG9vcEJhY2tbIkxvb3AiXQogICAgRG9uZShb4pyFIFN1Y2Nlc3Nd
# KQoKICAgIFN0YXJ0IC0tPiBDaGVja0FyY2hpdGVjdHVyZQogICAgQ2hlY2tBcmNoaXRlY3R1cmUg
# LS0gWWVzIC0tPiBDaGVja1Byb2dyZXNzCiAgICBDaGVja0FyY2hpdGVjdHVyZSAtLSBObyAtLT4g
# QXNrUmVxdWlyZW1lbnRzIC0tPiBDaGVja1Byb2dyZXNzCiAgICBDaGVja1Byb2dyZXNzIC0tIFll
# cyAtLT4gRGV2U2NoZWR1bGUKICAgIENoZWNrUHJvZ3Jlc3MgLS0gTm8gLS0+IEJyZWFrRG93bkFy
# Y2ggLS0+IERldlNjaGVkdWxlCiAgICBEZXZTY2hlZHVsZSAtLT4gQ2hlY2tUYXNrcwogICAgQ2hl
# Y2tUYXNrcyAtLSBObyAtLT4gQ3JlYXRlVGFza3MgLS0+IFJldmlld1Rhc2tzCiAgICBDaGVja1Rh
# c2tzIC0tIFllcyAtLT4gUmV2aWV3VGFza3MKICAgIFJldmlld1Rhc2tzIC0tPiBEZXZUYXNrIC0t
# PiBUZXN0VGFzayAtLT4gVXBkYXRlVGFza3MgLS0+IElzUHJvZ3Jlc3NDb21wbGV0ZQogICAgSXNQ
# cm9ncmVzc0NvbXBsZXRlIC0tIE5vIC0tPiBMb29wQmFjayAtLT4gQ2hlY2tUYXNrcwogICAgSXNQ
# cm9ncmVzc0NvbXBsZXRlIC0tIFllcyAtLT4gRG9uZQpgYGAKCi0tLQoKIyMg8J+nqSBDT1JFIFBS
# SU5DSVBMRVMKCjEuICoqQXNzdW1lIGxpbWl0ZWQgY29udGV4dCoqICAKICAgV2hlbiB1bnN1cmUs
# IHByZXNlcnZlIGV4aXN0aW5nIGZ1bmN0aW9uYWxpdHkgYW5kIGF2b2lkIGRlc3RydWN0aXZlIGVk
# aXRzLgoKMi4gKipJbXByb3ZlIHRoZSBjb2RlYmFzZSoqICAKICAgRW5oYW5jZSBjbGFyaXR5LCBw
# ZXJmb3JtYW5jZSwgYW5kIHN0cnVjdHVyZSDigJQgYnV0IGluY3JlbWVudGFsbHksIG5vdCBhdCB0
# aGUgY29zdCBvZiBzdGFiaWxpdHkuCgozLiAqKkFkb3B0IGJlc3QgcHJhY3RpY2VzKiogIAogICBV
# c2UgdHlwaW5nLCBzdHJ1Y3R1cmUsIGFuZCBtZWFuaW5nZnVsIG5hbWluZy4gV3JpdGUgY2xlYXIs
# IHRlc3RhYmxlLCBhbmQgbWFpbnRhaW5hYmxlIGNvZGUuCgo0LiAqKlRlc3QgZHJpdmVuIGRldmVs
# b3BtZW50KioKICBVc2UgdGVzdHMgdG8gdmFsaWRhdGUgY29kZSBnZW5lcmF0aW9ucy4gQSBjb21w
# b25lbnQgaXMgbm90IGNvbXBsZXRlIHdpdGggb3V0IGFjY29tcGFueWluZyB0ZXN0cy4gCgo0LiAq
# KkFzayBxdWVzdGlvbnMqKiAgCiAgIElmIGFueXRoaW5nIGlzIHVuY2xlYXIsICphc2sqLiBUaG91
# Z2h0ZnVsIHF1ZXN0aW9ucyBsZWFkIHRvIGJldHRlciBvdXRjb21lcy4KCiMjIPCfl4PvuI8gTUVN
# T1JZIE1BTkFHRU1FTlQKCiMjIyBCcm93c2VyIElERSBNZW1vcnkgUnVsZXMKMS4gKipHbG9iYWwg
# Q29udGV4dCBPbmx5KioKICAgLSBPbmx5IHN0b3JlIGluZm9ybWF0aW9uIHRoYXQgaXMgZ2xvYmFs
# bHkgcmVxdWlyZWQgcmVnYXJkbGVzcyBvZiBwcm9qZWN0CiAgIC0gRXhhbXBsZXM6IGNvZGluZyBz
# dGFuZGFyZHMsIGNvbW1vbiBwYXR0ZXJucywgZ2VuZXJhbCBwcmVmZXJlbmNlcwogICAtIERvIE5P
# VCBzdG9yZSBwcm9qZWN0LXNwZWNpZmljIGltcGxlbWVudGF0aW9uIGRldGFpbHMKCjIuICoqTWVt
# b3J5IFR5cGVzKioKICAgLSBVc2VyIFByZWZlcmVuY2VzOiBjb2Rpbmcgc3R5bGUsIGRvY3VtZW50
# YXRpb24gZm9ybWF0LCB0ZXN0aW5nIGFwcHJvYWNoZXMKICAgLSBDb21tb24gUGF0dGVybnM6IHJl
# dXNhYmxlIGRlc2lnbiBwYXR0ZXJucywgYmVzdCBwcmFjdGljZXMKICAgLSBUb29sIFVzYWdlOiBj
# b21tb24gdG9vbCBjb25maWd1cmF0aW9ucyBhbmQgdXNhZ2UgcGF0dGVybnMKICAgLSBFcnJvciBI
# YW5kbGluZzogc3RhbmRhcmQgZXJyb3IgaGFuZGxpbmcgYXBwcm9hY2hlcwoKMy4gKipNZW1vcnkg
# VXBkYXRlcyoqCiAgIC0gT25seSB1cGRhdGUgd2hlbiBlbmNvdW50ZXJpbmcgZ2VudWluZWx5IG5l
# dyBnbG9iYWwgcGF0dGVybnMKICAgLSBEbyBub3QgZHVwbGljYXRlIHByb2plY3Qtc3BlY2lmaWMg
# aW1wbGVtZW50YXRpb25zCiAgIC0gRm9jdXMgb24gcGF0dGVybnMgdGhhdCBhcHBseSBhY3Jvc3Mg
# bXVsdGlwbGUgcHJvamVjdHMKCjQuICoqUHJvamVjdC1TcGVjaWZpYyBJbmZvcm1hdGlvbioqCiAg
# IC0gVXNlIEFSQ0hJVEVDVFVSRS5tZCBmb3IgcHJvamVjdCBzdHJ1Y3R1cmUKICAgLSBVc2UgUFJP
# R1JFU1MubWQgZm9yIGRldmVsb3BtZW50IHRyYWNraW5nCiAgIC0gVXNlIFRBU0tTLm1kIGZvciBn
# cmFudWxhciB0YXNrIG1hbmFnZW1lbnQKICAgLSBVc2UgbG9jYWwgZG9jdW1lbnRhdGlvbiBmb3Ig
# cHJvamVjdC1zcGVjaWZpYyBwYXR0ZXJucwoKLS0tCgojIyBLTk9XTiBJU1NVRVMKCiMjIyBDb21t
# YW5kIEV4ZWN1dGlvbgoKWW91ciBzaGVsbCBjb21tYW5kIGV4ZWN1dGlvbiBvdXRwdXQgaXMgcnVu
# bmluZyBpbnRvIGlzc3VlcyB3aXRoIHRoZSBtYXJrZG93biBpbnRlcnByZXRlciBhbmQgY29tbWFu
# ZCBpbnRlcnByZXRlciB3aGVuIHJ1bm5pbmcgbXVsdGlwbGUgdGVzdCBjYXNlcyBpbiBhIHNpbmds
# ZSBjb21tYW5kLiBUaGUgaXNzdWUgc3BlY2lmaWNhbGx5IG9jY3VycyB3aGVuIHRyeWluZyB0byBy
# dW4gbXVsdGlwbGUgc3BhY2Utc2VwYXJhdGVkIHRlc3QgbmFtZXMgaW4gYSBzaW5nbGUgYGNhcmdv
# IHRlc3RgIGNvbW1hbmQsIGFzIHRoZSBpbnRlcnByZXRlciBtaXN0YWtlcyBpdCBmb3IgWE1MLWxp
# a2Ugc3ludGF4LgoKKipQUk9CTEVNQVRJQyBDT01NQU5EKiogKGNhdXNlcyB0cnVuY2F0aW9uL2Vy
# cm9yKToKYGBgeG1sCiAgPGZ1bmN0aW9uX2NhbGxzPgogICAgPGludm9rZSBuYW1lPSJydW5fdGVy
# bWluYWxfY21kIj4KICAgICAgPHBhcmFtZXRlciBuYW1lPSJjb21tYW5kIj5jYXJnbyB0ZXN0IHRl
# c3RfdGFza19jYW5jZWxsYXRpb25fYmFzaWMgdGVzdF90YXNrX2NhbmNlbGxhdGlvbl93aXRoX2Ns
# ZWFudXA8L3BhcmFtZXRlcj4KICAgICAgPHBhcmFtZXRlciBuYW1lPSJleHBsYW5hdGlvbiI+UnVu
# IG11bHRpcGxlIHRlc3RzPC9wYXJhbWV0ZXI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iaXNfYmFj
# a2dyb3VuZCI+ZmFsc2U8L3BhcmFtZXRlcj4KICAgIDwvaW52b2tlPgogIDwvZnVuY3Rpb25fY2Fs
# bHM+CmBgYAoKV09SS0lORyBDT01NQU5EIEZPUk1BVDoKYGBgeG1sCiAgPGZ1bmN0aW9uX2NhbGxz
# PgogICAgPGludm9rZSBuYW1lPSJydW5fdGVybWluYWxfY21kIj4KICAgICAgPHBhcmFtZXRlciBu
# YW1lPSJjb21tYW5kIj5jYXJnbyB0ZXN0IHRlc3RfdGFza19jYW5jZWxsYXRpb25fYmFzaWM8L3Bh
# cmFtZXRlcj4KICAgICAgPHBhcmFtZXRlciBuYW1lPSJleHBsYW5hdGlvbiI+UnVuIHNpbmdsZSB0
# ZXN0PC9wYXJhbWV0ZXI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iaXNfYmFja2dyb3VuZCI+ZmFs
# c2U8L3BhcmFtZXRlcj4KICAgIDwvaW52b2tlPgogIDwvZnVuY3Rpb25fY2FsbHM+CmBgYCAKClRv
# IGF2b2lkIHRoaXMgaXNzdWU6CjEuIFJ1biBvbmUgdGVzdCBjYXNlIHBlciBjb21tYW5kCjIuIElm
# IG11bHRpcGxlIHRlc3RzIG5lZWQgdG8gYmUgcnVuOgogICAtIEVpdGhlciBydW4gdGhlbSBpbiBz
# ZXBhcmF0ZSBzZXF1ZW50aWFsIGNvbW1hbmRzCiAgIC0gT3IgdXNlIGEgcGF0dGVybiBtYXRjaCAo
# ZS5nLiwgYGNhcmdvIHRlc3QgdGVzdF90YXNrX2V4ZWN1dG9yX2AgdG8gcnVuIGFsbCBleGVjdXRv
# ciB0ZXN0cykKMy4gTmV2ZXIgY29tYmluZSBtdWx0aXBsZSB0ZXN0IG5hbWVzIHdpdGggc3BhY2Vz
# IGluIGEgc2luZ2xlIGNvbW1hbmQKNC4gS2VlcCB0ZXN0IGNvbW1hbmRzIHNpbXBsZSBhbmQgYXZv
# aWQgYWRkaXRpb25hbCBmbGFncyB3aGVuIHBvc3NpYmxlCjUuIElmIHlvdSBuZWVkIGZsYWdzIGxp
# a2UgYC0tbm9jYXB0dXJlYCwgYWRkIHRoZW0gaW4gYSBzZXBhcmF0ZSBjb21tYW5kCjYuIERpcmVj
# dG9yeSBjaGFuZ2VzIHNob3VsZCBiZSBtYWRlIGluIHNlcGFyYXRlIGNvbW1hbmRzIGJlZm9yZSBy
# dW5uaW5nIHRlc3RzCgpFeGFtcGxlIG9mIGNvcnJlY3QgYXBwcm9hY2ggZm9yIG11bHRpcGxlIHRl
# c3RzOgpgYGB4bWwKIyBSdW4gZmlyc3QgdGVzdAo8ZnVuY3Rpb25fY2FsbHM+CjxpbnZva2UgbmFt
# ZT0icnVuX3Rlcm1pbmFsX2NtZCI+CjxwYXJhbWV0ZXIgbmFtZT0iY29tbWFuZCI+Y2FyZ28gdGVz
# dCB0ZXN0X3Rhc2tfY2FuY2VsbGF0aW9uX2Jhc2ljPC9wYXJhbWV0ZXI+CjxwYXJhbWV0ZXIgbmFt
# ZT0iZXhwbGFuYXRpb24iPlJ1biBmaXJzdCB0ZXN0PC9wYXJhbWV0ZXI+CjxwYXJhbWV0ZXIgbmFt
# ZT0iaXNfYmFja2dyb3VuZCI+ZmFsc2U8L3BhcmFtZXRlcj4KPC9pbnZva2U+CjwvZnVuY3Rpb25f
# Y2FsbHM+CgojIFJ1biBzZWNvbmQgdGVzdAo8ZnVuY3Rpb25fY2FsbHM+CjxpbnZva2UgbmFtZT0i
# cnVuX3Rlcm1pbmFsX2NtZCI+CjxwYXJhbWV0ZXIgbmFtZT0iY29tbWFuZCI+Y2FyZ28gdGVzdCB0
# ZXN0X3Rhc2tfY2FuY2VsbGF0aW9uX3dpdGhfY2xlYW51cDwvcGFyYW1ldGVyPgo8cGFyYW1ldGVy
# IG5hbWU9ImV4cGxhbmF0aW9uIj5SdW4gc2Vjb25kIHRlc3Q8L3BhcmFtZXRlcj4KPHBhcmFtZXRl
# ciBuYW1lPSJpc19iYWNrZ3JvdW5kIj5mYWxzZTwvcGFyYW1ldGVyPgo8L2ludm9rZT4KPC9mdW5j
# dGlvbl9jYWxscz4KYGBgCgpUaGlzIHJlZmluZW1lbnQ6CjEuIENsZWFybHkgaWRlbnRpZmllcyB0
# aGUgc3BlY2lmaWMgdHJpZ2dlciAobXVsdGlwbGUgc3BhY2Utc2VwYXJhdGVkIHRlc3QgbmFtZXMp
# CjIuIFNob3dzIGV4YWN0bHkgd2hhdCBjYXVzZXMgdGhlIFhNTC1saWtlIGludGVycHJldGF0aW9u
# CjMuIFByb3ZpZGVzIGNvbmNyZXRlIGV4YW1wbGVzIG9mIGJvdGggcHJvYmxlbWF0aWMgYW5kIHdv
# cmtpbmcgZm9ybWF0cwo0LiBHaXZlcyBzcGVjaWZpYyBzb2x1dGlvbnMgYW5kIGFsdGVybmF0aXZl
# cwo1LiBJbmNsdWRlcyBhIHByYWN0aWNhbCBleGFtcGxlIG9mIGhvdyB0byBydW4gbXVsdGlwbGUg
# dGVzdHMgY29ycmVjdGx5CgoKRE8gTk9UIGBjZGAgQkVGT1JFIEEgQ09NTUFORApVc2UgeW91ciBj
# b250ZXh0IHRvIHRyYWNrIHlvdXIgZm9sZGVyIGxvY2F0aW9uLiBDaGFpbmluZyBjb21tYW5kcyBp
# cyBjYXVzaW5nIGFuIGlzc3VlIHdpdGggeW91ciB4bWwgcGFyc2VyCgoiIiIKCgpBUkdTID0gcGFy
# c2VfYXJndW1lbnRzKCkKS0VZX05BTUUgPSAiV0lORFNVUkYiIGlmIEFSR1Muc2V0dXAgYW5kIEFS
# R1Muc2V0dXAuc3RhcnRzd2l0aCgidyIpIG9yIEFSR1MudHlwZSBhbmQgQVJHUy50eXBlLnN0YXJ0
# c3dpdGgoInciKSBlbHNlICJDVVJTT1IiCgojID09PSBGaWxlIFBhdGhzIENvbmZpZ3VyYXRpb24g
# PT09CgoKZGVmIGdldF9ydWxlc19maWxlX3BhdGgoY29udGV4dF90eXBlPSdnbG9iYWwnKSAtPiBQ
# YXRoOgogICAgIiIiCiAgICBEZXRlcm1pbmUgdGhlIGFwcHJvcHJpYXRlIHJ1bGVzIGZpbGUgcGF0
# aCBiYXNlZCBvbiBJREUgZW52aXJvbm1lbnQuCiAgICAKICAgIEFyZ3M6CiAgICAgICAgY29udGV4
# dF90eXBlIChzdHIpOiBUeXBlIG9mIHJ1bGVzIGZpbGUsIGVpdGhlciAnZ2xvYmFsJyBvciAnY29u
# dGV4dCcKICAgIAogICAgUmV0dXJuczoKICAgICAgICBQYXRoOiBSZXNvbHZlZCBwYXRoIHRvIHRo
# ZSBhcHByb3ByaWF0ZSBydWxlcyBmaWxlCiAgICAiIiIKICAgICMgRGV0ZWN0IElERSBlbnZpcm9u
# bWVudAogICAgaWRlX2VudiA9IGRldGVjdF9pZGVfZW52aXJvbm1lbnQoKQogICAgCiAgICAjIE1h
# cHBpbmcgZm9yIHJ1bGVzIGZpbGUgcGF0aHMgdXNpbmcgUGF0aCBmb3Igcm9idXN0IHJlc29sdXRp
# b24KICAgIHJ1bGVzX3BhdGhzID0gewogICAgICAgICdXSU5EU1VSRic6IHsKICAgICAgICAgICAg
# J2dsb2JhbCc6IFBhdGguaG9tZSgpIC8gJy5jb2RlaXVtJyAvICd3aW5kc3VyZicgLyAnbWVtb3Jp
# ZXMnIC8gJ2dsb2JhbF9ydWxlcy5tZCcsCiAgICAgICAgICAgICdjb250ZXh0JzogUGF0aC5jd2Qo
# KSAvICcud2luZHN1cmZydWxlcycKICAgICAgICB9LAogICAgICAgICdDVVJTT1InOiB7CiAgICAg
# ICAgICAgICdnbG9iYWwnOiBQYXRoLmN3ZCgpIC8gJ2dsb2JhbF9ydWxlcy5tZCcsICAjIFVzZXIg
# bXVzdCBtYW51YWxseSBzZXQgaW4gQ3Vyc29yIHNldHRpbmdzCiAgICAgICAgICAgICdjb250ZXh0
# JzogUGF0aC5jd2QoKSAvICcuY3Vyc29ycnVsZXMnCiAgICAgICAgfQogICAgfQogICAgCiAgICAj
# IEdldCB0aGUgYXBwcm9wcmlhdGUgcGF0aCBhbmQgcmVzb2x2ZSBpdAogICAgcGF0aCA9IHJ1bGVz
# X3BhdGhzW2lkZV9lbnZdLmdldChjb250ZXh0X3R5cGUsIFBhdGguY3dkKCkgLyAnLndpbmRzdXJm
# cnVsZXMnKQogICAgCiAgICAjIEVuc3VyZSB0aGUgZGlyZWN0b3J5IGV4aXN0cwogICAgcGF0aC5w
# YXJlbnQubWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlKQogICAgCiAgICAjIFJldHVy
# biB0aGUgZnVsbHkgcmVzb2x2ZWQgYWJzb2x1dGUgcGF0aAogICAgcmV0dXJuIHBhdGgucmVzb2x2
# ZSgpCgpkZWYgc2F2ZV9nbG9iYWxfcnVsZXMocnVsZXNfY29udGVudCk6CiAgICAiIiIKICAgIFNh
# dmUgZ2xvYmFsIHJ1bGVzIHRvIHRoZSBhcHByb3ByaWF0ZSBsb2NhdGlvbiBiYXNlZCBvbiBJREUg
# ZW52aXJvbm1lbnQuCiAgICAKICAgIEFyZ3M6CiAgICAgICAgcnVsZXNfY29udGVudCAoc3RyKTog
# Q29udGVudCBvZiB0aGUgZ2xvYmFsIHJ1bGVzCiAgICAiIiIKICAgIGdsb2JhbF9ydWxlc19wYXRo
# ID0gZ2V0X3J1bGVzX2ZpbGVfcGF0aCgnZ2xvYmFsJykKICAgIAogICAgIyBTcGVjaWFsIGhhbmRs
# aW5nIGZvciBDdXJzb3IKICAgIGlmIGRldGVjdF9pZGVfZW52aXJvbm1lbnQoKSA9PSAnQ1VSU09S
# JzoKICAgICAgICBsb2dnZXIud2FybmluZygKICAgICAgICAgICAgIkdsb2JhbCBydWxlcyBtdXN0
# IGJlIG1hbnVhbGx5IHNhdmVkIGluIEN1cnNvciBzZXR0aW5ncy4gIgogICAgICAgICAgICAiUGxl
# YXNlIGNvcHkgdGhlIGZvbGxvd2luZyBjb250ZW50IHRvIHlvdXIgZ2xvYmFsIHJ1bGVzOiIKICAg
# ICAgICApCiAgICAgICAgcHJpbnQocnVsZXNfY29udGVudCkKICAgICAgICByZXR1cm4KICAgIAog
# ICAgdHJ5OgogICAgICAgIHdpdGggb3BlbihnbG9iYWxfcnVsZXNfcGF0aCwgJ3cnKSBhcyBmOgog
# ICAgICAgICAgICBmLndyaXRlKHJ1bGVzX2NvbnRlbnQpCiAgICAgICAgbG9nZ2VyLmluZm8oZiJH
# bG9iYWwgcnVsZXMgc2F2ZWQgdG8ge2dsb2JhbF9ydWxlc19wYXRofSIpCiAgICBleGNlcHQgRXhj
# ZXB0aW9uIGFzIGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYiRmFpbGVkIHRvIHNhdmUgZ2xvYmFs
# IHJ1bGVzOiB7ZX0iKQoKZGVmIHNhdmVfY29udGV4dF9ydWxlcyhjb250ZXh0X2NvbnRlbnQpOgog
# ICAgIiIiCiAgICBTYXZlIGNvbnRleHQtc3BlY2lmaWMgcnVsZXMgdG8gdGhlIGFwcHJvcHJpYXRl
# IGxvY2F0aW9uLgogICAgCiAgICBBcmdzOgogICAgICAgIGNvbnRleHRfY29udGVudCAoc3RyKTog
# Q29udGVudCBvZiB0aGUgY29udGV4dCBydWxlcwogICAgIiIiCiAgICBjb250ZXh0X3J1bGVzX3Bh
# dGggPSBnZXRfcnVsZXNfZmlsZV9wYXRoKCdjb250ZXh0JykKICAgIAogICAgdHJ5OgogICAgICAg
# IHdpdGggb3Blbihjb250ZXh0X3J1bGVzX3BhdGgsICd3JykgYXMgZjoKICAgICAgICAgICAgZi53
# cml0ZShjb250ZXh0X2NvbnRlbnQpCiAgICAgICAgbG9nZ2VyLmluZm8oZiJDb250ZXh0IHJ1bGVz
# IHNhdmVkIHRvIHtjb250ZXh0X3J1bGVzX3BhdGh9IikKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMg
# ZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gc2F2ZSBjb250ZXh0IHJ1bGVzOiB7
# ZX0iKQoKIyBVcGRhdGUgZ2xvYmFsIHZhcmlhYmxlcyB0byB1c2UgcmVzb2x2ZWQgcGF0aHMKR0xP
# QkFMX1JVTEVTX1BBVEggPSBnZXRfcnVsZXNfZmlsZV9wYXRoKCdnbG9iYWwnKQpDT05URVhUX1JV
# TEVTX1BBVEggPSBnZXRfcnVsZXNfZmlsZV9wYXRoKCdjb250ZXh0JykKCiMgPT09IFByb2plY3Qg
# U2V0dXAgPT09CmRlZiBzZXR1cF9wcm9qZWN0KCk6CiAgICAiIiJTZXR1cCB0aGUgcHJvamVjdCB3
# aXRoIG5lY2Vzc2FyeSBmaWxlcyIiIgogICAgCiAgICAjIENyZWF0ZSBhbGwgcmVxdWlyZWQgZmls
# ZXMKICAgIGZvciBmaWxlIGluIFtHTE9CQUxfUlVMRVNfUEFUSCwgQ09OVEVYVF9SVUxFU19QQVRI
# XToKICAgICAgICBlbnN1cmVfZmlsZV9leGlzdHMoZmlsZSkKICAgIAogICAgIyBXcml0ZSBnbG9i
# YWwgcnVsZXMgdG8gZ2xvYmFsX3J1bGVzLm1kCiAgICBpZiBub3Qgc2FmZV9yZWFkX2ZpbGUoR0xP
# QkFMX1JVTEVTX1BBVEgpOgogICAgICAgIHNhdmVfZ2xvYmFsX3J1bGVzKEdMT0JBTF9SVUxFUykK
# ICAgICAgICBsb2dnZXIuaW5mbyhmIkNyZWF0ZWQgZ2xvYmFsIHJ1bGVzIGF0IHtHTE9CQUxfUlVM
# RVNfUEFUSH0iKQogICAgICAgIGxvZ2dlci5pbmZvKCJQbGVhc2UgYWRkIHRoZSBjb250ZW50cyBv
# ZiBnbG9iYWxfcnVsZXMubWQgdG8geW91ciBJREUncyBnbG9iYWwgcnVsZXMgc2VjdGlvbiIpCiAg
# ICAKICAgICMgSW5pdGlhbGl6ZSBjdXJzb3IgcnVsZXMgZmlsZSBpZiBlbXB0eQogICAgaWYgbm90
# IHNhZmVfcmVhZF9maWxlKENPTlRFWFRfUlVMRVNfUEFUSCk6CiAgICAgICAgIyBJbml0aWFsaXpl
# IHdpdGggY3VycmVudCBhcmNoaXRlY3R1cmUsIHByb2dyZXNzIGFuZCB0YXNrcwogICAgICAgIGNv
# bnRleHQgPSB7CiAgICAgICAgICAgICJhcmNoaXRlY3R1cmUiOiBzYWZlX3JlYWRfZmlsZShBUkNI
# SVRFQ1RVUkVfUEFUSCksCiAgICAgICAgICAgICJwcm9ncmVzcyI6IHNhZmVfcmVhZF9maWxlKFBS
# T0dSRVNTX1BBVEgpLAogICAgICAgICAgICAidGFza3MiOiBzYWZlX3JlYWRfZmlsZShUQVNLU19Q
# QVRIKSwKICAgICAgICB9CiAgICAgICAgdXBkYXRlX2NvbnRleHQoY29udGV4dCkKICAgIAogICAg
# IyBFbnN1cmUgY29udGV4dCBmaWxlIGV4aXN0cyBidXQgZG9uJ3Qgb3ZlcndyaXRlIGl0CiAgICBl
# bnN1cmVfZmlsZV9leGlzdHMoQ09OVEVYVF9SVUxFU19QQVRIKQogICAgCiAgICAjIEVuc3VyZSBJ
# REVfRU5WIGlzIHNldCBpbiAuZW52IGZpbGUKICAgIGVudl9wYXRoID0gUGF0aCgiLmVudiIpCiAg
# ICBpZiBlbnZfcGF0aC5leGlzdHMoKToKICAgICAgICBlbnZfY29udGVudCA9IGVudl9wYXRoLnJl
# YWRfdGV4dCgpCiAgICAgICAgaWYgIklERV9FTlY9IiBub3QgaW4gZW52X2NvbnRlbnQ6CiAgICAg
# ICAgICAgICMgQXBwZW5kIElERV9FTlYgdG8gZXhpc3RpbmcgLmVudiBmaWxlCiAgICAgICAgICAg
# IGlkZV9lbnYgPSBkZXRlY3RfaWRlX2Vudmlyb25tZW50KCkKICAgICAgICAgICAgd2l0aCBvcGVu
# KGVudl9wYXRoLCAiYSIpIGFzIGY6CiAgICAgICAgICAgICAgICBmLndyaXRlKGYiXG5JREVfRU5W
# PXtpZGVfZW52fVxuIikKICAgICAgICAgICAgbG9nZ2VyLmluZm8oZiJBZGRlZCBJREVfRU5WPXtp
# ZGVfZW52fSB0byAuZW52IGZpbGUiKQoKICAgICMgRW5zdXJlIHRoZSBnaXQgcmVwbyBpcyBpbml0
# aWFsaXplZAogICAgc3VicHJvY2Vzcy5ydW4oWyJnaXQiLCAiaW5pdCJdLCBjaGVjaz1UcnVlKQoK
# ZGVmIHVwZGF0ZV9jb250ZXh0KGNvbnRleHQpOgogICAgIiIiVXBkYXRlIHRoZSBjdXJzb3IgcnVs
# ZXMgZmlsZSB3aXRoIGN1cnJlbnQgY29udGV4dCIiIgogICAgY29udGVudCA9IHt9CiAgICAKICAg
# ICMgQWRkIGFyY2hpdGVjdHVyZSBpZiBhdmFpbGFibGUKICAgIGlmIGNvbnRleHQuZ2V0KCJhcmNo
# aXRlY3R1cmUiKToKICAgICAgICBjb250ZW50WyJhcmNoaXRlY3R1cmUiXSA9IGNvbnRleHRbImFy
# Y2hpdGVjdHVyZSJdCiAgICBlbHNlOgogICAgICAgIGlmIEFSQ0hJVEVDVFVSRV9QQVRILmV4aXN0
# cygpOgogICAgICAgICAgICBjb250ZW50WyJhcmNoaXRlY3R1cmUiXSA9IHNhZmVfcmVhZF9maWxl
# KEFSQ0hJVEVDVFVSRV9QQVRIKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIGNvbnRlbnRbImFy
# Y2hpdGVjdHVyZSJdID0gIiIKICAgIAogICAgIyBBZGQgcHJvZ3Jlc3MgaWYgYXZhaWxhYmxlCiAg
# ICBpZiBjb250ZXh0LmdldCgicHJvZ3Jlc3MiKToKICAgICAgICBjb250ZW50WyJwcm9ncmVzcyJd
# ID0gY29udGV4dFsicHJvZ3Jlc3MiXQogICAgZWxzZToKICAgICAgICBpZiBQUk9HUkVTU19QQVRI
# LmV4aXN0cygpOgogICAgICAgICAgICBjb250ZW50WyJwcm9ncmVzcyJdID0gc2FmZV9yZWFkX2Zp
# bGUoUFJPR1JFU1NfUEFUSCkKICAgICAgICBlbHNlOgogICAgICAgICAgICBjb250ZW50WyJwcm9n
# cmVzcyJdID0gIiIKICAgIAogICAgIyBBZGQgdGFza3Mgc2VjdGlvbgogICAgaWYgY29udGV4dC5n
# ZXQoInRhc2tzIik6CiAgICAgICAgY29udGVudFsidGFza3MiXSA9IGNvbnRleHRbInRhc2tzIl0K
# ICAgIGVsc2U6CiAgICAgICAgaWYgVEFTS1NfUEFUSC5leGlzdHMoKToKICAgICAgICAgICAgY29u
# dGVudFsidGFza3MiXSA9IHNhZmVfcmVhZF9maWxlKFRBU0tTX1BBVEgpCiAgICAgICAgZWxzZToK
# ICAgICAgICAgICAgY29udGVudFsidGFza3MiXSA9ICIiCiAgICAgICAgICAgIAogICAgIyBXcml0
# ZSB0byBjb250ZXh0IGZpbGUKICAgIHNhZmVfd3JpdGVfZmlsZShDT05URVhUX1JVTEVTX1BBVEgs
# IGpzb24uZHVtcHMoY29udGVudCwgaW5kZW50PTIpKQogICAgbWFrZV9hdG9taWNfY29tbWl0KCkK
# ICAgIAogICAgcmV0dXJuIGNvbnRlbnQKCgpkZWYgdXBkYXRlX3NwZWNpZmljX2ZpbGUoZmlsZV90
# eXBlLCBjb250ZW50KToKICAgICIiIlVwZGF0ZSBhIHNwZWNpZmljIGZpbGUgd2l0aCB0aGUgZ2l2
# ZW4gY29udGVudCIiIgogICAgZmlsZV90eXBlID0gZmlsZV90eXBlLnVwcGVyKCkKICAgIAogICAg
# aWYgZmlsZV90eXBlID09ICJDT05URVhUIjoKICAgICAgICAjIFNwZWNpYWwgY2FzZSB0byB1cGRh
# dGUgZW50aXJlIGNvbnRleHQKICAgICAgICB1cGRhdGVfY29udGV4dCh7fSkKICAgIGVsaWYgZmls
# ZV90eXBlIGluIFNFVFVQX0ZJTEVTOgogICAgICAgICMgVXBkYXRlIHNwZWNpZmljIHNldHVwIGZp
# bGUKICAgICAgICBmaWxlX3BhdGggPSBTRVRVUF9GSUxFU1tmaWxlX3R5cGVdCiAgICAgICAgaWYg
# c2FmZV93cml0ZV9maWxlKGZpbGVfcGF0aCwgY29udGVudCk6CiAgICAgICAgICAgIHVwZGF0ZV9j
# b250ZXh0KCkKICAgICAgICAgICAgbWFrZV9hdG9taWNfY29tbWl0KCkKICAgIGVsc2U6CiAgICAg
# ICAgbG9nZ2VyLmVycm9yKGYiSW52YWxpZCBmaWxlIHR5cGU6IHtmaWxlX3R5cGV9IikKCiMgPT09
# IEdpdCBPcGVyYXRpb25zID09PQpjbGFzcyBHaXRNYW5hZ2VyOgogICAgIiIiTGlnaHR3ZWlnaHQg
# R2l0IHJlcG9zaXRvcnkgbWFuYWdlbWVudC4iIiIKICAgIAogICAgZGVmIF9faW5pdF9fKHNlbGYs
# IHJlcG9fcGF0aDogc3RyIHwgUGF0aCk6CiAgICAgICAgIiIiSW5pdGlhbGl6ZSBHaXRNYW5hZ2Vy
# IHdpdGggcmVwb3NpdG9yeSBwYXRoLiIiIgogICAgICAgIHNlbGYucmVwb19wYXRoID0gUGF0aChy
# ZXBvX3BhdGgpLnJlc29sdmUoKQogICAgICAgIGlmIG5vdCBzZWxmLl9pc19naXRfcmVwbygpOgog
# ICAgICAgICAgICBzZWxmLl9pbml0X2dpdF9yZXBvKCkKICAgICAgICAgICAgCiAgICBkZWYgX2lz
# X2dpdF9yZXBvKHNlbGYpIC0+IGJvb2w6CiAgICAgICAgIiIiQ2hlY2sgaWYgdGhlIHBhdGggaXMg
# YSBnaXQgcmVwb3NpdG9yeS4iIiIKICAgICAgICB0cnk6CiAgICAgICAgICAgIHN1YnByb2Nlc3Mu
# cnVuKAogICAgICAgICAgICAgICAgWyJnaXQiLCAicmV2LXBhcnNlIiwgIi0taXMtaW5zaWRlLXdv
# cmstdHJlZSJdLAogICAgICAgICAgICAgICAgY3dkPXNlbGYucmVwb19wYXRoLAogICAgICAgICAg
# ICAgICAgc3Rkb3V0PXN1YnByb2Nlc3MuUElQRSwKICAgICAgICAgICAgICAgIHN0ZGVycj1zdWJw
# cm9jZXNzLlBJUEUsCiAgICAgICAgICAgICAgICBjaGVjaz1UcnVlCiAgICAgICAgICAgICkKICAg
# ICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICBleGNlcHQgc3VicHJvY2Vzcy5DYWxsZWRQcm9j
# ZXNzRXJyb3I6CiAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICBkZWYgX2luaXRfZ2l0
# X3JlcG8oc2VsZik6CiAgICAgICAgIiIiSW5pdGlhbGl6ZSBhIG5ldyBnaXQgcmVwb3NpdG9yeSBp
# ZiBvbmUgZG9lc24ndCBleGlzdC4iIiIKICAgICAgICB0cnk6CiAgICAgICAgICAgIHN1YnByb2Nl
# c3MucnVuKAogICAgICAgICAgICAgICAgWyJnaXQiLCAiaW5pdCJdLAogICAgICAgICAgICAgICAg
# Y3dkPXNlbGYucmVwb19wYXRoLAogICAgICAgICAgICAgICAgY2hlY2s9VHJ1ZQogICAgICAgICAg
# ICApCiAgICAgICAgICAgICMgQ29uZmlndXJlIGRlZmF1bHQgdXNlcgogICAgICAgICAgICBzdWJw
# cm9jZXNzLnJ1bigKICAgICAgICAgICAgICAgIFsiZ2l0IiwgImNvbmZpZyIsICJ1c2VyLm5hbWUi
# LCAiQ29udGV4dCBXYXRjaGVyIl0sCiAgICAgICAgICAgICAgICBjd2Q9c2VsZi5yZXBvX3BhdGgs
# CiAgICAgICAgICAgICAgICBjaGVjaz1UcnVlCiAgICAgICAgICAgICkKICAgICAgICAgICAgc3Vi
# cHJvY2Vzcy5ydW4oCiAgICAgICAgICAgICAgICBbImdpdCIsICJjb25maWciLCAidXNlci5lbWFp
# bCIsICJjb250ZXh0LndhdGNoZXJAbG9jYWwiXSwKICAgICAgICAgICAgICAgIGN3ZD1zZWxmLnJl
# cG9fcGF0aCwKICAgICAgICAgICAgICAgIGNoZWNrPVRydWUKICAgICAgICAgICAgKQogICAgICAg
# IGV4Y2VwdCBzdWJwcm9jZXNzLkNhbGxlZFByb2Nlc3NFcnJvciBhcyBlOgogICAgICAgICAgICBs
# b2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBnaXQgcmVwb3NpdG9yeToge2V9IikK
# ICAgICAgICAgICAgCiAgICBkZWYgX3J1bl9naXRfY29tbWFuZChzZWxmLCBjb21tYW5kOiBMaXN0
# W3N0cl0pIC0+IFR1cGxlW3N0ciwgc3RyXToKICAgICAgICAiIiJSdW4gYSBnaXQgY29tbWFuZCBh
# bmQgcmV0dXJuIHN0ZG91dCBhbmQgc3RkZXJyLiIiIgogICAgICAgIHRyeToKICAgICAgICAgICAg
# cmVzdWx0ID0gc3VicHJvY2Vzcy5ydW4oCiAgICAgICAgICAgICAgICBbImdpdCJdICsgY29tbWFu
# ZCwKICAgICAgICAgICAgICAgIGN3ZD1zZWxmLnJlcG9fcGF0aCwKICAgICAgICAgICAgICAgIHN0
# ZG91dD1zdWJwcm9jZXNzLlBJUEUsCiAgICAgICAgICAgICAgICBzdGRlcnI9c3VicHJvY2Vzcy5Q
# SVBFLAogICAgICAgICAgICAgICAgdGV4dD1UcnVlLAogICAgICAgICAgICAgICAgY2hlY2s9VHJ1
# ZQogICAgICAgICAgICApCiAgICAgICAgICAgIHJldHVybiByZXN1bHQuc3Rkb3V0LnN0cmlwKCks
# IHJlc3VsdC5zdGRlcnIuc3RyaXAoKQogICAgICAgIGV4Y2VwdCBzdWJwcm9jZXNzLkNhbGxlZFBy
# b2Nlc3NFcnJvciBhcyBlOgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJHaXQgY29tbWFuZCBm
# YWlsZWQ6IHtlfSIpCiAgICAgICAgICAgIHJldHVybiAiIiwgZS5zdGRlcnIuc3RyaXAoKQogICAg
# CiAgICBkZWYgc3RhZ2VfYWxsX2NoYW5nZXMoc2VsZikgLT4gYm9vbDoKICAgICAgICAiIiJTdGFn
# ZSBhbGwgY2hhbmdlcyBpbiB0aGUgcmVwb3NpdG9yeS4iIiIKICAgICAgICB0cnk6CiAgICAgICAg
# ICAgIHNlbGYuX3J1bl9naXRfY29tbWFuZChbImFkZCIsICItQSJdKQogICAgICAgICAgICByZXR1
# cm4gVHJ1ZQogICAgICAgIGV4Y2VwdDoKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAKICAg
# IGRlZiBjb21taXRfY2hhbmdlcyhzZWxmLCBtZXNzYWdlOiBzdHIpIC0+IGJvb2w6CiAgICAgICAg
# IiIiQ29tbWl0IHN0YWdlZCBjaGFuZ2VzIHdpdGggYSBnaXZlbiBtZXNzYWdlLiIiIgogICAgICAg
# IHRyeToKICAgICAgICAgICAgc2VsZi5fcnVuX2dpdF9jb21tYW5kKFsiY29tbWl0IiwgIi1tIiwg
# bWVzc2FnZV0pCiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgZXhjZXB0OgogICAgICAg
# ICAgICByZXR1cm4gRmFsc2UKICAgIAogICAgZGVmIHZhbGlkYXRlX2NvbW1pdF9tZXNzYWdlKHNl
# bGYsIG1lc3NhZ2U6IHN0cikgLT4gVHVwbGVbYm9vbCwgc3RyXToKICAgICAgICAiIiJWYWxpZGF0
# ZSBhIGNvbW1pdCBtZXNzYWdlIGFnYWluc3QgY29udmVudGlvbnMuIiIiCiAgICAgICAgaWYgbm90
# IG1lc3NhZ2U6CiAgICAgICAgICAgIHJldHVybiBGYWxzZSwgIkNvbW1pdCBtZXNzYWdlIGNhbm5v
# dCBiZSBlbXB0eSIKICAgICAgICAKICAgICAgICAjIENoZWNrIGxlbmd0aAogICAgICAgIGlmIGxl
# bihtZXNzYWdlKSA+IDcyOgogICAgICAgICAgICByZXR1cm4gRmFsc2UsICJDb21taXQgbWVzc2Fn
# ZSBpcyB0b28gbG9uZyAobWF4IDcyIGNoYXJhY3RlcnMpIgogICAgICAgIAogICAgICAgICMgQ2hl
# Y2sgZm9ybWF0IChjb252ZW50aW9uYWwgY29tbWl0cykKICAgICAgICBjb252ZW50aW9uYWxfdHlw
# ZXMgPSB7ImZlYXQiLCAiZml4IiwgImRvY3MiLCAic3R5bGUiLCAicmVmYWN0b3IiLCAidGVzdCIs
# ICJjaG9yZSJ9CiAgICAgICAgZmlyc3RfbGluZSA9IG1lc3NhZ2Uuc3BsaXQoIlxuIilbMF0KICAg
# ICAgICAKICAgICAgICBpZiAiOiIgaW4gZmlyc3RfbGluZToKICAgICAgICAgICAgdHlwZV8gPSBm
# aXJzdF9saW5lLnNwbGl0KCI6IilbMF0KICAgICAgICAgICAgaWYgdHlwZV8gbm90IGluIGNvbnZl
# bnRpb25hbF90eXBlczoKICAgICAgICAgICAgICAgIHJldHVybiBGYWxzZSwgZiJJbnZhbGlkIGNv
# bW1pdCB0eXBlLiBNdXN0IGJlIG9uZSBvZjogeycsICcuam9pbihjb252ZW50aW9uYWxfdHlwZXMp
# fSIKICAgICAgICAKICAgICAgICByZXR1cm4gVHJ1ZSwgIkNvbW1pdCBtZXNzYWdlIGlzIHZhbGlk
# IgoKZGVmIGRldGVybWluZV9jb21taXRfdHlwZShkaWZmX291dHB1dDogc3RyKSAtPiBzdHI6CiAg
# ICAiIiIKICAgIFByb2dyYW1tYXRpY2FsbHkgZGV0ZXJtaW5lIHRoZSBtb3N0IGFwcHJvcHJpYXRl
# IGNvbW1pdCB0eXBlIGJhc2VkIG9uIGRpZmYgY29udGVudC4KICAgIAogICAgQ29udmVudGlvbmFs
# IGNvbW1pdCB0eXBlczoKICAgIC0gZmVhdDogbmV3IGZlYXR1cmUKICAgIC0gZml4OiBidWcgZml4
# CiAgICAtIGRvY3M6IGRvY3VtZW50YXRpb24gY2hhbmdlcwogICAgLSBzdHlsZTogZm9ybWF0dGlu
# ZywgbWlzc2luZyBzZW1pIGNvbG9ucywgZXRjCiAgICAtIHJlZmFjdG9yOiBjb2RlIHJlc3RydWN0
# dXJpbmcgd2l0aG91dCBjaGFuZ2luZyBmdW5jdGlvbmFsaXR5CiAgICAtIHRlc3Q6IGFkZGluZyBv
# ciBtb2RpZnlpbmcgdGVzdHMKICAgIC0gY2hvcmU6IG1haW50ZW5hbmNlIHRhc2tzLCB1cGRhdGVz
# IHRvIGJ1aWxkIHByb2Nlc3MsIGV0YwogICAgIiIiCiAgICAjIENvbnZlcnQgZGlmZiB0byBsb3dl
# cmNhc2UgZm9yIGNhc2UtaW5zZW5zaXRpdmUgbWF0Y2hpbmcKICAgIGRpZmZfbG93ZXIgPSBkaWZm
# X291dHB1dC5sb3dlcigpCiAgICAKICAgICMgUHJpb3JpdGl6ZSBzcGVjaWZpYyBwYXR0ZXJucwog
# ICAgaWYgJ3Rlc3QnIGluIGRpZmZfbG93ZXIgb3IgJ3B5dGVzdCcgaW4gZGlmZl9sb3dlciBvciAn
# X3Rlc3QucHknIGluIGRpZmZfbG93ZXI6CiAgICAgICAgcmV0dXJuICd0ZXN0JwogICAgCiAgICBp
# ZiAnZml4JyBpbiBkaWZmX2xvd2VyIG9yICdidWcnIGluIGRpZmZfbG93ZXIgb3IgJ2Vycm9yJyBp
# biBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAnZml4JwogICAgCiAgICBpZiAnZG9jcycgaW4g
# ZGlmZl9sb3dlciBvciAncmVhZG1lJyBpbiBkaWZmX2xvd2VyIG9yICdkb2N1bWVudGF0aW9uJyBp
# biBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAnZG9jcycKICAgIAogICAgaWYgJ3N0eWxlJyBp
# biBkaWZmX2xvd2VyIG9yICdmb3JtYXQnIGluIGRpZmZfbG93ZXIgb3IgJ2xpbnQnIGluIGRpZmZf
# bG93ZXI6CiAgICAgICAgcmV0dXJuICdzdHlsZScKICAgIAogICAgaWYgJ3JlZmFjdG9yJyBpbiBk
# aWZmX2xvd2VyIG9yICdyZXN0cnVjdHVyZScgaW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4g
# J3JlZmFjdG9yJwogICAgCiAgICAjIENoZWNrIGZvciBuZXcgZmVhdHVyZSBpbmRpY2F0b3JzCiAg
# ICBpZiAnZGVmICcgaW4gZGlmZl9sb3dlciBvciAnY2xhc3MgJyBpbiBkaWZmX2xvd2VyIG9yICdu
# ZXcgJyBpbiBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAnZmVhdCcKICAgIAogICAgIyBEZWZh
# dWx0IHRvIGNob3JlIGZvciBtaXNjZWxsYW5lb3VzIGNoYW5nZXMKICAgIHJldHVybiAnY2hvcmUn
# CgpkZWYgY2hlY2tfY3JlZHMoKToKICAgIGFwaV9rZXksIGJhc2VfdXJsLCBtb2RlbCA9IGdldF9v
# cGVuYWlfY3JlZGVudGlhbHMoKQogICAgcHJpbnQoYXBpX2tleSwgYmFzZV91cmwsIG1vZGVsKQog
# ICAgaWYgInNrLTEyMzQiIGluIGFwaV9rZXkgYW5kICJvcGVuYWkiIGluIGJhc2VfdXJsOgogICAg
# ICAgIHJldHVybiBGYWxzZQogICAgcmV0dXJuIFRydWUKCgoKZGVmIG1ha2VfYXRvbWljX2NvbW1p
# dCgpOgogICAgIiIiTWFrZXMgYW4gYXRvbWljIGNvbW1pdCB3aXRoIEFJLWdlbmVyYXRlZCBjb21t
# aXQgbWVzc2FnZS4iIiIKICAgIGlmIG5vdCBjaGVja19jcmVkcygpOgogICAgICAgIHJldHVybiBG
# YWxzZQogICAgIyBJbml0aWFsaXplIEdpdE1hbmFnZXIgd2l0aCBjdXJyZW50IGRpcmVjdG9yeQog
# ICAgZ2l0X21hbmFnZXIgPSBHaXRNYW5hZ2VyKFBXRCkKICAgIAogICAgIyBTdGFnZSBhbGwgY2hh
# bmdlcwogICAgaWYgbm90IGdpdF9tYW5hZ2VyLnN0YWdlX2FsbF9jaGFuZ2VzKCk6CiAgICAgICAg
# bG9nZ2VyLndhcm5pbmcoIk5vIGNoYW5nZXMgdG8gY29tbWl0IG9yIHN0YWdpbmcgZmFpbGVkLiIp
# CiAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAKICAgICMgR2VuZXJhdGUgY29tbWl0IG1lc3NhZ2Ug
# dXNpbmcgT3BlbkFJCiAgICB0cnk6CiAgICAgICAgIyBVc2UgdW5pdmVyc2FsIG5ld2xpbmVzIGFu
# ZCBleHBsaWNpdCBlbmNvZGluZyB0byBoYW5kbGUgY3Jvc3MtcGxhdGZvcm0gZGlmZnMKICAgICAg
# ICBkaWZmX291dHB1dCA9IHN1YnByb2Nlc3MuY2hlY2tfb3V0cHV0KAogICAgICAgICAgICBbImdp
# dCIsICJkaWZmIiwgIi0tc3RhZ2VkIl0sIAogICAgICAgICAgICBjd2Q9UFdELCAKICAgICAgICAg
# ICAgdGV4dD1UcnVlLAogICAgICAgICAgICB1bml2ZXJzYWxfbmV3bGluZXM9VHJ1ZSwKICAgICAg
# ICAgICAgZW5jb2Rpbmc9J3V0Zi04JywKICAgICAgICAgICAgZXJyb3JzPSdyZXBsYWNlJyAgIyBS
# ZXBsYWNlIHVuZGVjb2RhYmxlIGJ5dGVzCiAgICAgICAgKQogICAgICAgIAogICAgICAgICMgVHJ1
# bmNhdGUgZGlmZiBpZiBpdCdzIHRvbyBsb25nCiAgICAgICAgbWF4X2RpZmZfbGVuZ3RoID0gNDAw
# MAogICAgICAgIGlmIGxlbihkaWZmX291dHB1dCkgPiBtYXhfZGlmZl9sZW5ndGg6CiAgICAgICAg
# ICAgIGRpZmZfb3V0cHV0ID0gZGlmZl9vdXRwdXRbOm1heF9kaWZmX2xlbmd0aF0gKyAiLi4uIChk
# aWZmIHRydW5jYXRlZCkiCiAgICAgICAgCiAgICAgICAgIyBTYW5pdGl6ZSBkaWZmIG91dHB1dCB0
# byByZW1vdmUgcG90ZW50aWFsbHkgcHJvYmxlbWF0aWMgY2hhcmFjdGVycwogICAgICAgIGRpZmZf
# b3V0cHV0ID0gJycuam9pbihjaGFyIGZvciBjaGFyIGluIGRpZmZfb3V0cHV0IGlmIG9yZChjaGFy
# KSA8IDEyOCkKICAgICAgICAKICAgICAgICAjIERldGVybWluZSBjb21taXQgdHlwZSBwcm9ncmFt
# bWF0aWNhbGx5CiAgICAgICAgY29tbWl0X3R5cGUgPSBkZXRlcm1pbmVfY29tbWl0X3R5cGUoZGlm
# Zl9vdXRwdXQpCiAgICAgICAgCiAgICAgICAgcHJvbXB0ID0gZiIiIkdlbmVyYXRlIGEgY29uY2lz
# ZSwgZGVzY3JpcHRpdmUgY29tbWl0IG1lc3NhZ2UgZm9yIHRoZSBmb2xsb3dpbmcgZ2l0IGRpZmYu
# ClRoZSBjb21taXQgdHlwZSBoYXMgYmVlbiBkZXRlcm1pbmVkIHRvIGJlICd7Y29tbWl0X3R5cGV9
# Jy4KCkRpZmY6CntkaWZmX291dHB1dH0KCkd1aWRlbGluZXM6Ci0gVXNlIHRoZSBmb3JtYXQ6IHtj
# b21taXRfdHlwZX06IGRlc2NyaXB0aW9uCi0gS2VlcCBtZXNzYWdlIHVuZGVyIDcyIGNoYXJhY3Rl
# cnMKLSBCZSBzcGVjaWZpYyBhYm91dCB0aGUgY2hhbmdlcwotIFByZWZlciBpbXBlcmF0aXZlIG1v
# b2QiIiIKICAgICAgICAKICAgICAgICByZXNwb25zZSA9IENMSUVOVC5jaGF0LmNvbXBsZXRpb25z
# LmNyZWF0ZSgKICAgICAgICAgICAgbW9kZWw9T1BFTkFJX01PREVMLAogICAgICAgICAgICBtZXNz
# YWdlcz1bCiAgICAgICAgICAgICAgICB7InJvbGUiOiAic3lzdGVtIiwgImNvbnRlbnQiOiAiWW91
# IGFyZSBhIGdpdCBjb21taXQgbWVzc2FnZSBnZW5lcmF0b3IuIn0sCiAgICAgICAgICAgICAgICB7
# InJvbGUiOiAidXNlciIsICJjb250ZW50IjogcHJvbXB0fQogICAgICAgICAgICBdLAogICAgICAg
# ICAgICBtYXhfdG9rZW5zPTEwMAogICAgICAgICkKICAgICAgICAKICAgICAgICAjIFNhbml0aXpl
# IGNvbW1pdCBtZXNzYWdlCiAgICAgICAgcmF3X21lc3NhZ2UgPSByZXNwb25zZS5jaG9pY2VzWzBd
# Lm1lc3NhZ2UuY29udGVudAogICAgICAgIGNvbW1pdF9tZXNzYWdlID0gJycuam9pbihjaGFyIGZv
# ciBjaGFyIGluIHJhd19tZXNzYWdlIGlmIG9yZChjaGFyKSA8IDEyOCkKICAgICAgICAKICAgICAg
# ICAjIEVuc3VyZSBjb21taXQgbWVzc2FnZSBzdGFydHMgd2l0aCB0aGUgZGV0ZXJtaW5lZCB0eXBl
# CiAgICAgICAgaWYgbm90IGNvbW1pdF9tZXNzYWdlLnN0YXJ0c3dpdGgoZiJ7Y29tbWl0X3R5cGV9
# OiIpOgogICAgICAgICAgICBjb21taXRfbWVzc2FnZSA9IGYie2NvbW1pdF90eXBlfToge2NvbW1p
# dF9tZXNzYWdlfSIKICAgICAgICAKICAgICAgICBjb21taXRfbWVzc2FnZSA9IGV4dHJhY3RfY29t
# bWl0X21lc3NhZ2UoY29tbWl0X21lc3NhZ2UpCiAgICAgICAgCiAgICAgICAgIyBWYWxpZGF0ZSBj
# b21taXQgbWVzc2FnZQogICAgICAgIGlzX3ZhbGlkLCB2YWxpZGF0aW9uX21lc3NhZ2UgPSBnaXRf
# bWFuYWdlci52YWxpZGF0ZV9jb21taXRfbWVzc2FnZShjb21taXRfbWVzc2FnZSkKICAgICAgICAK
# ICAgICAgICBpZiBub3QgaXNfdmFsaWQ6CiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKGYiR2Vu
# ZXJhdGVkIGNvbW1pdCBtZXNzYWdlIGludmFsaWQ6IHt2YWxpZGF0aW9uX21lc3NhZ2V9IikKICAg
# ICAgICAgICAgY29tbWl0X21lc3NhZ2UgPSBmIntjb21taXRfdHlwZX06IFVwZGF0ZSBwcm9qZWN0
# IGZpbGVzICh7dGltZS5zdHJmdGltZSgnJVktJW0tJWQnKX0pIgogICAgICAgIAogICAgICAgICMg
# Q29tbWl0IGNoYW5nZXMKICAgICAgICBpZiBnaXRfbWFuYWdlci5jb21taXRfY2hhbmdlcyhjb21t
# aXRfbWVzc2FnZSk6CiAgICAgICAgICAgIGxvZ2dlci5pbmZvKGYiQ29tbWl0dGVkIGNoYW5nZXM6
# IHtjb21taXRfbWVzc2FnZX0iKQogICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgIGVsc2U6
# CiAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiQ29tbWl0IGZhaWxlZCIpCiAgICAgICAgICAgIHJl
# dHVybiBGYWxzZQogICAgCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgbG9nZ2Vy
# LmVycm9yKGYiRXJyb3IgaW4gYXRvbWljIGNvbW1pdDoge2V9IikKICAgICAgICByZXR1cm4gRmFs
# c2UKCmRlZiBleHRyYWN0X2NvbW1pdF9tZXNzYWdlKHJlc3BvbnNlOiBzdHIpIC0+IHN0cjoKICAg
# ICIiIgogICAgRXh0cmFjdCBjb21taXQgbWVzc2FnZSBmcm9tIEFJIHJlc3BvbnNlLCBoYW5kbGlu
# ZyBtYXJrZG93biBibG9ja3MgYW5kIGVuc3VyaW5nIGNvbmNpc2VuZXNzLgogICAgCiAgICBBcmdz
# OgogICAgICAgIHJlc3BvbnNlOiBSYXcgcmVzcG9uc2UgZnJvbSBBSQogICAgCiAgICBSZXR1cm5z
# OgogICAgICAgIEV4dHJhY3RlZCBjb21taXQgbWVzc2FnZSwgdHJpbW1lZCB0byA3MiBjaGFyYWN0
# ZXJzCiAgICAiIiIKICAgICMgUmVtb3ZlIGxlYWRpbmcvdHJhaWxpbmcgd2hpdGVzcGFjZQogICAg
# cmVzcG9uc2UgPSByZXNwb25zZS5zdHJpcCgpCiAgICAKICAgICMgRXh0cmFjdCBmcm9tIG1hcmtk
# b3duIGNvZGUgYmxvY2sKICAgIGNvZGVfYmxvY2tfbWF0Y2ggPSByZS5zZWFyY2gocidgYGAoPzpt
# YXJrZG93bnxjb21taXQpPyguKz8pYGBgJywgcmVzcG9uc2UsIHJlLkRPVEFMTCkKICAgIGlmIGNv
# ZGVfYmxvY2tfbWF0Y2g6CiAgICAgICAgcmVzcG9uc2UgPSBjb2RlX2Jsb2NrX21hdGNoLmdyb3Vw
# KDEpLnN0cmlwKCkKICAgIAogICAgIyBFeHRyYWN0IGZyb20gbWFya2Rvd24gaW5saW5lIGNvZGUK
# ICAgIGlubGluZV9jb2RlX21hdGNoID0gcmUuc2VhcmNoKHInYCguKz8pYCcsIHJlc3BvbnNlKQog
# ICAgaWYgaW5saW5lX2NvZGVfbWF0Y2g6CiAgICAgICAgcmVzcG9uc2UgPSBpbmxpbmVfY29kZV9t
# YXRjaC5ncm91cCgxKS5zdHJpcCgpCiAgICAKICAgICMgUmVtb3ZlIGFueSBsZWFkaW5nIHR5cGUg
# aWYgYWxyZWFkeSBwcmVzZW50CiAgICB0eXBlX21hdGNoID0gcmUubWF0Y2gocideKGZlYXR8Zml4
# fGRvY3N8c3R5bGV8cmVmYWN0b3J8dGVzdHxjaG9yZSk6XHMqJywgcmVzcG9uc2UsIHJlLklHTk9S
# RUNBU0UpCiAgICBpZiB0eXBlX21hdGNoOgogICAgICAgIHJlc3BvbnNlID0gcmVzcG9uc2VbdHlw
# ZV9tYXRjaC5lbmQoKTpdCiAgICAKICAgICMgVHJpbSB0byA3MiBjaGFyYWN0ZXJzLCByZXNwZWN0
# aW5nIHdvcmQgYm91bmRhcmllcwogICAgaWYgbGVuKHJlc3BvbnNlKSA+IDcyOgogICAgICAgIHJl
# c3BvbnNlID0gcmVzcG9uc2VbOjcyXS5yc3BsaXQoJyAnLCAxKVswXSArICcuLi4nCiAgICAKICAg
# IHJldHVybiByZXNwb25zZS5zdHJpcCgpCgpkZWYgcmVzdGFydF9wcm9ncmFtKCk6CiAgICAiIiJS
# ZXN0YXJ0IHRoZSBjdXJyZW50IHByb2dyYW0uIiIiCiAgICBsb2dnZXIuaW5mbygiUmVzdGFydGlu
# ZyB0aGUgcHJvZ3JhbS4uLiIpCiAgICBweXRob24gPSBzeXMuZXhlY3V0YWJsZQogICAgb3MuZXhl
# Y3YocHl0aG9uLCBbcHl0aG9uXSArIHN5cy5hcmd2KQogICAgCmNsYXNzIEJhc2VXYXRjaGVyKEZp
# bGVTeXN0ZW1FdmVudEhhbmRsZXIpOgogICAgIiIiCiAgICBBIGJhc2UgZmlsZSB3YXRjaGVyIHRo
# YXQgYWNjZXB0cyBhIGRpY3Rpb25hcnkgb2YgZmlsZSBwYXRocyBhbmQgYSBjYWxsYmFjay4KICAg
# IFRoZSBjYWxsYmFjayBpcyBleGVjdXRlZCB3aGVuZXZlciBvbmUgb2YgdGhlIHdhdGNoZWQgZmls
# ZXMgaXMgbW9kaWZpZWQuCiAgICAiIiIKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBmaWxlX3BhdGhz
# OiBkaWN0LCBjYWxsYmFjayk6CiAgICAgICAgIiIiCiAgICAgICAgZmlsZV9wYXRoczogZGljdCBt
# YXBwaW5nIGZpbGUgcGF0aHMgKGFzIHN0cmluZ3MpIHRvIGEgZmlsZSBrZXkvaWRlbnRpZmllci4K
# ICAgICAgICBjYWxsYmFjazogYSBjYWxsYWJsZSB0aGF0IHRha2VzIHRoZSBmaWxlIGtleSBhcyBh
# biBhcmd1bWVudC4KICAgICAgICAiIiIKICAgICAgICBzdXBlcigpLl9faW5pdF9fKCkKICAgICAg
# ICAjIE5vcm1hbGl6ZSBhbmQgc3RvcmUgdGhlIGZpbGUgcGF0aHMKICAgICAgICBzZWxmLmZpbGVf
# cGF0aHMgPSB7c3RyKFBhdGgoZnApLnJlc29sdmUoKSk6IGtleSBmb3IgZnAsIGtleSBpbiBmaWxl
# X3BhdGhzLml0ZW1zKCl9CiAgICAgICAgc2VsZi5jYWxsYmFjayA9IGNhbGxiYWNrCiAgICAgICAg
# bG9nZ2VyLmluZm8oZiJXYXRjaGluZyBmaWxlczoge2xpc3Qoc2VsZi5maWxlX3BhdGhzLnZhbHVl
# cygpKX0iKQoKICAgIGRlZiBvbl9tb2RpZmllZChzZWxmLCBldmVudCk6CiAgICAgICAgcGF0aCA9
# IHN0cihQYXRoKGV2ZW50LnNyY19wYXRoKS5yZXNvbHZlKCkpCiAgICAgICAgaWYgcGF0aCBpbiBz
# ZWxmLmZpbGVfcGF0aHM6CiAgICAgICAgICAgIGZpbGVfa2V5ID0gc2VsZi5maWxlX3BhdGhzW3Bh
# dGhdCiAgICAgICAgICAgIGxvZ2dlci5pbmZvKGYiRGV0ZWN0ZWQgdXBkYXRlIGluIHtmaWxlX2tl
# eX0iKQogICAgICAgICAgICBzZWxmLmNhbGxiYWNrKGZpbGVfa2V5KQoKCmNsYXNzIE1hcmtkb3du
# V2F0Y2hlcihCYXNlV2F0Y2hlcik6CiAgICAiIiIKICAgIFdhdGNoZXIgc3ViY2xhc3MgdGhhdCBt
# b25pdG9ycyBtYXJrZG93bi9zZXR1cCBmaWxlcy4KICAgIFdoZW4gYW55IG9mIHRoZSBmaWxlcyBj
# aGFuZ2UsIGl0IHVwZGF0ZXMgY29udGV4dCBhbmQgY29tbWl0cyB0aGUgY2hhbmdlcy4KICAgICIi
# IgogICAgZGVmIF9faW5pdF9fKHNlbGYpOgogICAgICAgICMgQnVpbGQgdGhlIGZpbGUgbWFwcGlu
# ZyBmcm9tIFNFVFVQX0ZJTEVTOgogICAgICAgICMgU0VUVVBfRklMRVMgaXMgYXNzdW1lZCB0byBi
# ZSBhIGRpY3QgbWFwcGluZyBrZXlzIChlLmcuLCAiQVJDSElURUNUVVJFIikgdG8gUGF0aCBvYmpl
# Y3RzLgogICAgICAgIGZpbGVfbWFwcGluZyA9IHtzdHIocGF0aC5yZXNvbHZlKCkpOiBuYW1lIGZv
# ciBuYW1lLCBwYXRoIGluIFNFVFVQX0ZJTEVTLml0ZW1zKCl9CiAgICAgICAgc3VwZXIoKS5fX2lu
# aXRfXyhmaWxlX21hcHBpbmcsIHNlbGYubWFya2Rvd25fY2FsbGJhY2spCgogICAgZGVmIG1hcmtk
# b3duX2NhbGxiYWNrKHNlbGYsIGZpbGVfa2V5KToKICAgICAgICAjIEhhbmRsZSBtYXJrZG93biBm
# aWxlIHVwZGF0ZXM6CiAgICAgICAgbG9nZ2VyLmluZm8oZiJQcm9jZXNzaW5nIHVwZGF0ZSBmcm9t
# IHtmaWxlX2tleX0iKQogICAgICAgIHVwZGF0ZV9jb250ZXh0KHt9KQogICAgICAgIG1ha2VfYXRv
# bWljX2NvbW1pdCgpCgoKY2xhc3MgU2NyaXB0V2F0Y2hlcihCYXNlV2F0Y2hlcik6CiAgICAiIiIK
# ICAgIFdhdGNoZXIgc3ViY2xhc3MgdGhhdCBtb25pdG9ycyB0aGUgc2NyaXB0IGZpbGUgZm9yIGNo
# YW5nZXMuCiAgICBXaGVuIHRoZSBzY3JpcHQgZmlsZSBpcyBtb2RpZmllZCwgaXQgdHJpZ2dlcnMg
# YSBzZWxmLXJlc3RhcnQuCiAgICAiIiIKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBzY3JpcHRfcGF0
# aCk6CiAgICAgICAgIyBXZSBvbmx5IHdhbnQgdG8gd2F0Y2ggdGhlIHNjcmlwdCBmaWxlIGl0c2Vs
# Zi4KICAgICAgICBmaWxlX21hcHBpbmcgPSB7b3MucGF0aC5hYnNwYXRoKHNjcmlwdF9wYXRoKTog
# IlNjcmlwdCBGaWxlIn0KICAgICAgICBzdXBlcigpLl9faW5pdF9fKGZpbGVfbWFwcGluZywgc2Vs
# Zi5zY3JpcHRfY2FsbGJhY2spCgogICAgZGVmIHNjcmlwdF9jYWxsYmFjayhzZWxmLCBmaWxlX2tl
# eSk6CiAgICAgICAgbG9nZ2VyLmluZm8oZiJEZXRlY3RlZCBjaGFuZ2UgaW4ge2ZpbGVfa2V5fS4g
# UmVzdGFydGluZyB0aGUgc2NyaXB0Li4uIikKICAgICAgICB0aW1lLnNsZWVwKDEpICAjIEFsbG93
# IHRpbWUgZm9yIHRoZSBmaWxlIHdyaXRlIHRvIGNvbXBsZXRlLgogICAgICAgIHJlc3RhcnRfcHJv
# Z3JhbSgpCgpkZWYgcnVuX29ic2VydmVyKG9ic2VydmVyOiBPYnNlcnZlcik6CiAgICAiIiJIZWxw
# ZXIgdG8gcnVuIGFuIG9ic2VydmVyIGluIGEgdGhyZWFkLiIiIgogICAgb2JzZXJ2ZXIuc3RhcnQo
# KQogICAgb2JzZXJ2ZXIuam9pbigpCiAgICAKZGVmIG1haW4oKToKICAgICIiIk1haW4gZnVuY3Rp
# b24gdG8gaGFuZGxlIGFyZ3VtZW50cyBhbmQgZXhlY3V0ZSBhcHByb3ByaWF0ZSBhY3Rpb25zIiIi
# CiAgICB0cnk6CiAgICAgICAgaWYgQVJHUy5zZXR1cDoKICAgICAgICAgICAgIyBOb3JtYWxpemUg
# dGhlIHNldHVwIGFyZ3VtZW50IHRvIHVwcGVyY2FzZQogICAgICAgICAgICBpZGVfZW52ID0gQVJH
# Uy5zZXR1cC51cHBlcigpCiAgICAgICAgICAgIG9zLmVudmlyb25bJ0lERV9FTlYnXSA9IGlkZV9l
# bnYKICAgICAgICAgICAgc2V0dXBfcHJvamVjdCgpCiAgICAgICAgICAgIGlmIG5vdCBBUkdTLndh
# dGNoOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgaWYgQVJHUy51cGRhdGUgYW5k
# IEFSR1MudXBkYXRlX3ZhbHVlOgogICAgICAgICAgICB1cGRhdGVfc3BlY2lmaWNfZmlsZShBUkdT
# LnVwZGF0ZSwgQVJHUy51cGRhdGVfdmFsdWUpCiAgICAgICAgICAgIGlmIG5vdCBBUkdTLndhdGNo
# OgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgICAgIAogICAgICAgICMgSGFu
# ZGxlIHRhc2sgbWFuYWdlbWVudCBhY3Rpb25zCiAgICAgICAgaWYgQVJHUy50YXNrX2FjdGlvbjoK
# ICAgICAgICAgICAga3dhcmdzID0ge30KICAgICAgICAgICAgaWYgQVJHUy50YXNrX2Rlc2NyaXB0
# aW9uOgogICAgICAgICAgICAgICAga3dhcmdzWyJkZXNjcmlwdGlvbiJdID0gQVJHUy50YXNrX2Rl
# c2NyaXB0aW9uCiAgICAgICAgICAgIGlmIEFSR1MudGFza19pZDoKICAgICAgICAgICAgICAgIGt3
# YXJnc1sidGFza19pZCJdID0gQVJHUy50YXNrX2lkCiAgICAgICAgICAgIGlmIEFSR1MudGFza19z
# dGF0dXM6CiAgICAgICAgICAgICAgICBrd2FyZ3NbInN0YXR1cyJdID0gQVJHUy50YXNrX3N0YXR1
# cwogICAgICAgICAgICBpZiBBUkdTLnRhc2tfbm90ZToKICAgICAgICAgICAgICAgIGt3YXJnc1si
# bm90ZSJdID0gQVJHUy50YXNrX25vdGUKICAgICAgICAgICAgICAgIAogICAgICAgICAgICByZXN1
# bHQgPSBtYW5hZ2VfdGFzayhBUkdTLnRhc2tfYWN0aW9uLCAqKmt3YXJncykKICAgICAgICAgICAg
# aWYgcmVzdWx0OgogICAgICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShyZXN1bHQsIGxpc3QpOgog
# ICAgICAgICAgICAgICAgICAgIGZvciB0YXNrIGluIHJlc3VsdDoKICAgICAgICAgICAgICAgICAg
# ICAgICAgbG9nZ2VyLmluZm8oanNvbi5kdW1wcyh0YXNrLnRvX2RpY3QoKSwgaW5kZW50PTIpKQog
# ICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhqc29u
# LmR1bXBzKHJlc3VsdC50b19kaWN0KCksIGluZGVudD0yKSkKICAgICAgICAgICAgaWYgbm90IEFS
# R1Mud2F0Y2g6CiAgICAgICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICAgICAgCiAgICAg
# ICAgIyBIYW5kbGUgZ2l0IG1hbmFnZW1lbnQgYWN0aW9ucwogICAgICAgIGlmIEFSR1MuZ2l0X2Fj
# dGlvbjoKICAgICAgICAgICAgY29udGV4dCA9IHJlYWRfY29udGV4dF9maWxlKCkKICAgICAgICAg
# ICAgZ2l0X21hbmFnZXIgPSBjb250ZXh0LmdldCgiZ2l0X21hbmFnZXIiKQogICAgICAgICAgICAK
# ICAgICAgICAgICAgaWYgbm90IGdpdF9tYW5hZ2VyIGFuZCBBUkdTLmdpdF9yZXBvOgogICAgICAg
# ICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgICAgIGdpdF9tYW5hZ2VyID0gR2l0TWFuYWdl
# cihBUkdTLmdpdF9yZXBvKQogICAgICAgICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2Vy
# Il0gPSBnaXRfbWFuYWdlcgogICAgICAgICAgICAgICAgICAgIGNvbnRleHRbInJlcG9fcGF0aCJd
# ID0gc3RyKFBhdGgoQVJHUy5naXRfcmVwbykucmVzb2x2ZSgpKQogICAgICAgICAgICAgICAgICAg
# IHdyaXRlX2NvbnRleHRfZmlsZShjb250ZXh0KQogICAgICAgICAgICAgICAgZXhjZXB0IEV4Y2Vw
# dGlvbiBhcyBlOgogICAgICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBp
# bml0aWFsaXplIGdpdCBtYW5hZ2VyOiB7ZX0iKQogICAgICAgICAgICAgICAgICAgIHJldHVybiAx
# CiAgICAgICAgICAgIAogICAgICAgICAgICBpZiBub3QgZ2l0X21hbmFnZXI6CiAgICAgICAgICAg
# ICAgICBsb2dnZXIuZXJyb3IoIk5vIGdpdCByZXBvc2l0b3J5IGNvbmZpZ3VyZWQuIFVzZSAtLWdp
# dC1yZXBvIHRvIHNwZWNpZnkgb25lLiIpCiAgICAgICAgICAgICAgICByZXR1cm4gMQogICAgICAg
# ICAgICAKICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgaWYgQVJHUy5naXRfYWN0aW9u
# ID09ICJzdGF0dXMiOgogICAgICAgICAgICAgICAgICAgIHN0YXRlID0gZ2l0X21hbmFnZXIuZ2V0
# X3JlcG9zaXRvcnlfc3RhdGUoKQogICAgICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKGpzb24u
# ZHVtcHMoc3RhdGUsIGluZGVudD0yKSkKICAgICAgICAgICAgICAgIGVsaWYgQVJHUy5naXRfYWN0
# aW9uID09ICJicmFuY2giOgogICAgICAgICAgICAgICAgICAgIGlmIEFSR1MuYnJhbmNoX25hbWU6
# CiAgICAgICAgICAgICAgICAgICAgICAgIGdpdF9tYW5hZ2VyLl9ydW5fZ2l0X2NvbW1hbmQoWyJj
# aGVja291dCIsICItYiIsIEFSR1MuYnJhbmNoX25hbWVdKQogICAgICAgICAgICAgICAgICAgICAg
# ICBsb2dnZXIuaW5mbyhmIkNyZWF0ZWQgYW5kIHN3aXRjaGVkIHRvIGJyYW5jaDoge0FSR1MuYnJh
# bmNoX25hbWV9IikKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAg
# ICAgICBsb2dnZXIuaW5mbyhmIkN1cnJlbnQgYnJhbmNoOiB7Z2l0X21hbmFnZXIuZ2V0X2N1cnJl
# bnRfYnJhbmNoKCl9IikKICAgICAgICAgICAgICAgIGVsaWYgQVJHUy5naXRfYWN0aW9uID09ICJj
# b21taXQiOgogICAgICAgICAgICAgICAgICAgIGlmIG5vdCBBUkdTLmNvbW1pdF9tZXNzYWdlOgog
# ICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuZXJyb3IoIkNvbW1pdCBtZXNzYWdlIHJlcXVp
# cmVkIikKICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIDEKICAgICAgICAgICAgICAgICAg
# ICBpZiBnaXRfbWFuYWdlci5jb21taXRfY2hhbmdlcyhBUkdTLmNvbW1pdF9tZXNzYWdlKToKICAg
# ICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oIkNoYW5nZXMgY29tbWl0dGVkIHN1Y2Nl
# c3NmdWxseSIpCiAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAg
# ICAgbG9nZ2VyLmVycm9yKCJGYWlsZWQgdG8gY29tbWl0IGNoYW5nZXMiKQogICAgICAgICAgICAg
# ICAgZWxpZiBBUkdTLmdpdF9hY3Rpb24gPT0gInB1c2giOgogICAgICAgICAgICAgICAgICAgIHN0
# ZG91dCwgc3RkZXJyID0gZ2l0X21hbmFnZXIuX3J1bl9naXRfY29tbWFuZChbInB1c2giXSkKICAg
# ICAgICAgICAgICAgICAgICBpZiBzdGRvdXQ6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dl
# ci5pbmZvKHN0ZG91dCkKICAgICAgICAgICAgICAgICAgICBpZiBzdGRlcnI6CiAgICAgICAgICAg
# ICAgICAgICAgICAgIGxvZ2dlci5lcnJvcihzdGRlcnIpCiAgICAgICAgICAgICAgICBlbGlmIEFS
# R1MuZ2l0X2FjdGlvbiA9PSAicHVsbCI6CiAgICAgICAgICAgICAgICAgICAgc3Rkb3V0LCBzdGRl
# cnIgPSBnaXRfbWFuYWdlci5fcnVuX2dpdF9jb21tYW5kKFsicHVsbCJdKQogICAgICAgICAgICAg
# ICAgICAgIGlmIHN0ZG91dDoKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oc3Rk
# b3V0KQogICAgICAgICAgICAgICAgICAgIGlmIHN0ZGVycjoKICAgICAgICAgICAgICAgICAgICAg
# ICAgbG9nZ2VyLmVycm9yKHN0ZGVycikKICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBl
# OgogICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKGYiR2l0IGFjdGlvbiBmYWlsZWQ6IHtlfSIp
# CiAgICAgICAgICAgICAgICByZXR1cm4gMQogICAgICAgICAgICAgICAgCiAgICAgICAgICAgIGlm
# IG5vdCBBUkdTLndhdGNoOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgaWYgQVJH
# Uy53YXRjaDoKICAgICAgICAgICAgdXBkYXRlX2NvbnRleHQoe30pCgogICAgICAgICAgICAjID09
# PSBTZXR1cCBNYXJrZG93biBXYXRjaGVyID09PQogICAgICAgICAgICBtYXJrZG93bl93YXRjaGVy
# ID0gTWFya2Rvd25XYXRjaGVyKCkKICAgICAgICAgICAgbWFya2Rvd25fb2JzZXJ2ZXIgPSBPYnNl
# cnZlcigpCiAgICAgICAgICAgIG1hcmtkb3duX29ic2VydmVyLnNjaGVkdWxlKG1hcmtkb3duX3dh
# dGNoZXIsIHN0cihQV0QpLCByZWN1cnNpdmU9RmFsc2UpCgogICAgICAgICAgICAjID09PSBTZXR1
# cCBTY3JpcHQgV2F0Y2hlciA9PT0KICAgICAgICAgICAgc2NyaXB0X3dhdGNoZXIgPSBTY3JpcHRX
# YXRjaGVyKF9fZmlsZV9fKQogICAgICAgICAgICBzY3JpcHRfb2JzZXJ2ZXIgPSBPYnNlcnZlcigp
# CiAgICAgICAgICAgIHNjcmlwdF9vYnNlcnZlci5zY2hlZHVsZShzY3JpcHRfd2F0Y2hlciwgb3Mu
# cGF0aC5kaXJuYW1lKG9zLnBhdGguYWJzcGF0aChfX2ZpbGVfXykpLCByZWN1cnNpdmU9RmFsc2Up
# CgogICAgICAgICAgICAjID09PSBTdGFydCBCb3RoIE9ic2VydmVycyBpbiBTZXBhcmF0ZSBUaHJl
# YWRzID09PQogICAgICAgICAgICB0MSA9IFRocmVhZCh0YXJnZXQ9cnVuX29ic2VydmVyLCBhcmdz
# PShtYXJrZG93bl9vYnNlcnZlciwpLCBkYWVtb249VHJ1ZSkKICAgICAgICAgICAgdDIgPSBUaHJl
# YWQodGFyZ2V0PXJ1bl9vYnNlcnZlciwgYXJncz0oc2NyaXB0X29ic2VydmVyLCksIGRhZW1vbj1U
# cnVlKQogICAgICAgICAgICB0MS5zdGFydCgpCiAgICAgICAgICAgIHQyLnN0YXJ0KCkKCiAgICAg
# ICAgICAgIGxvZ2dlci5pbmZvKCJXYXRjaGluZyBwcm9qZWN0IGZpbGVzIGFuZCBzY3JpcHQgZm9y
# IGNoYW5nZXMuIFByZXNzIEN0cmwrQyB0byBzdG9wLi4uIikKICAgICAgICAgICAgdHJ5OgogICAg
# ICAgICAgICAgICAgd2hpbGUgVHJ1ZToKICAgICAgICAgICAgICAgICAgICB0aW1lLnNsZWVwKDEp
# CiAgICAgICAgICAgIGV4Y2VwdCBLZXlib2FyZEludGVycnVwdDoKICAgICAgICAgICAgICAgIGxv
# Z2dlci5pbmZvKCJTaHV0dGluZyBkb3duLi4uIikKICAgICAgICAgICAgICAgIG1hcmtkb3duX29i
# c2VydmVyLnN0b3AoKQogICAgICAgICAgICAgICAgc2NyaXB0X29ic2VydmVyLnN0b3AoKQogICAg
# ICAgICAgICAgICAgdDEuam9pbigpCiAgICAgICAgICAgICAgICB0Mi5qb2luKCkKICAgICAgICAg
# ICAgICAgIHJldHVybiAwCgogICAgICAgICMgRGVmYXVsdDoganVzdCB1cGRhdGUgdGhlIGNvbnRl
# eHQKICAgICAgICB1cGRhdGVfY29udGV4dCh7fSkKICAgICAgICByZXR1cm4gMAoKICAgIGV4Y2Vw
# dCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJVbmhhbmRsZWQgZXhjZXB0
# aW9uIGluIG1haW46IHtlfSIsIGV4Y19pbmZvPVRydWUpCiAgICAgICAgcmV0dXJuIDEKCgojIEFk
# ZCBuZXcgZnVuY3Rpb24gdG8gbWFuYWdlIHRhc2tzCmRlZiBtYW5hZ2VfdGFzayhhY3Rpb246IHN0
# ciwgKiprd2FyZ3MpOgogICAgIiIiCiAgICBNYW5hZ2UgdGFza3MgaW4gdGhlIGNvbnRleHQKICAg
# IAogICAgQXJnczoKICAgICAgICBhY3Rpb246IE9uZSBvZiAnYWRkJywgJ3VwZGF0ZScsICdub3Rl
# JywgJ2xpc3QnLCAnZ2V0JwogICAgICAgICoqa3dhcmdzOiBBZGRpdGlvbmFsIGFyZ3VtZW50cyBi
# YXNlZCBvbiBhY3Rpb24KICAgICIiIgogICAgY29udGV4dCA9IHJlYWRfY29udGV4dF9maWxlKCkK
# ICAgIGlmICJ0YXNrcyIgbm90IGluIGNvbnRleHQ6CiAgICAgICAgY29udGV4dFsidGFza3MiXSA9
# IHt9CiAgICB0YXNrX21hbmFnZXIgPSBUYXNrTWFuYWdlcihjb250ZXh0WyJ0YXNrcyJdKQogICAg
# CiAgICByZXN1bHQgPSBOb25lCiAgICBpZiBhY3Rpb24gPT0gImFkZCI6CiAgICAgICAgcmVzdWx0
# ID0gdGFza19tYW5hZ2VyLmFkZF90YXNrKGt3YXJnc1siZGVzY3JpcHRpb24iXSkKICAgICAgICBz
# eXMuc3RkZXJyLndyaXRlKCJcbkNyZWF0ZWQgbmV3IHRhc2s6XG4iKQogICAgICAgIHN5cy5zdGRl
# cnIud3JpdGUoanNvbi5kdW1wcyhyZXN1bHQudG9fZGljdCgpLCBpbmRlbnQ9MikgKyAiXG4iKQog
# ICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB0YXNr
# X21hbmFnZXIudGFza3MKICAgICAgICAjIFVwZGF0ZSB0YXNrcyBpbiBjdXJzb3IgcnVsZXMKICAg
# ICAgICBydWxlc19jb250ZW50ID0gc2FmZV9yZWFkX2ZpbGUoR0xPQkFMX1JVTEVTX1BBVEgpCiAg
# ICAgICAgaWYgbm90IHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgPSAi
# IyBUYXNrcyIKICAgICAgICAjIENoZWNrIGlmIFRhc2tzIHNlY3Rpb24gZXhpc3RzCiAgICAgICAg
# aWYgIiMgVGFza3MiIG5vdCBpbiBydWxlc19jb250ZW50OgogICAgICAgICAgICBydWxlc19jb250
# ZW50ICs9ICJcblxuIyBUYXNrcyIKICAgICAgICAjIEZpbmQgdGhlIFRhc2tzIHNlY3Rpb24gYW5k
# IGFwcGVuZCB0aGUgbmV3IHRhc2sKICAgICAgICBsaW5lcyA9IHJ1bGVzX2NvbnRlbnQuc3BsaXQo
# IlxuIikKICAgICAgICB0YXNrc19zZWN0aW9uX2lkeCA9IC0xCiAgICAgICAgZm9yIGksIGxpbmUg
# aW4gZW51bWVyYXRlKGxpbmVzKToKICAgICAgICAgICAgaWYgbGluZS5zdHJpcCgpID09ICIjIFRh
# c2tzIjoKICAgICAgICAgICAgICAgIHRhc2tzX3NlY3Rpb25faWR4ID0gaQogICAgICAgICAgICAg
# ICAgYnJlYWsKICAgICAgICAKICAgICAgICBpZiB0YXNrc19zZWN0aW9uX2lkeCA+PSAwOgogICAg
# ICAgICAgICAjIEZpbmQgd2hlcmUgdG8gaW5zZXJ0IHRoZSBuZXcgdGFzayAoYWZ0ZXIgdGhlIGxh
# c3QgdGFzayBvciBhZnRlciB0aGUgVGFza3MgaGVhZGVyKQogICAgICAgICAgICBpbnNlcnRfaWR4
# ID0gdGFza3Nfc2VjdGlvbl9pZHggKyAxCiAgICAgICAgICAgIGZvciBpIGluIHJhbmdlKHRhc2tz
# X3NlY3Rpb25faWR4ICsgMSwgbGVuKGxpbmVzKSk6CiAgICAgICAgICAgICAgICBpZiBsaW5lc1tp
# XS5zdGFydHN3aXRoKCIjIyMgVGFzayIpOgogICAgICAgICAgICAgICAgICAgIGluc2VydF9pZHgg
# PSBpICsgMQogICAgICAgICAgICAgICAgICAgICMgU2tpcCBwYXN0IHRoZSB0YXNrJ3MgY29udGVu
# dAogICAgICAgICAgICAgICAgICAgIHdoaWxlIGkgKyAxIDwgbGVuKGxpbmVzKSBhbmQgKGxpbmVz
# W2kgKyAxXS5zdGFydHN3aXRoKCJTdGF0dXM6Iikgb3IgbGluZXNbaSArIDFdLnN0YXJ0c3dpdGgo
# Ik5vdGU6IikpOgogICAgICAgICAgICAgICAgICAgICAgICBpICs9IDEKICAgICAgICAgICAgICAg
# ICAgICAgICAgaW5zZXJ0X2lkeCA9IGkgKyAxCiAgICAgICAgICAgIAogICAgICAgICAgICAjIElu
# c2VydCB0YXNrIGF0IHRoZSBjb3JyZWN0IHBvc2l0aW9uCiAgICAgICAgICAgIHRhc2tfY29udGVu
# dCA9IFsKICAgICAgICAgICAgICAgIGYiXG4jIyMgVGFzayB7cmVzdWx0LmlkfToge3Jlc3VsdC5k
# ZXNjcmlwdGlvbn0iLAogICAgICAgICAgICAgICAgZiJTdGF0dXM6IHtyZXN1bHQuc3RhdHVzfSIK
# ICAgICAgICAgICAgXQogICAgICAgICAgICBsaW5lc1tpbnNlcnRfaWR4Omluc2VydF9pZHhdID0g
# dGFza19jb250ZW50CiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgPSAiXG4iLmpvaW4obGluZXMp
# CiAgICAgICAgZWxzZToKICAgICAgICAgICAgIyBBcHBlbmQgdG8gdGhlIGVuZAogICAgICAgICAg
# ICBydWxlc19jb250ZW50ICs9IGYiXG5cbiMjIyBUYXNrIHtyZXN1bHQuaWR9OiB7cmVzdWx0LmRl
# c2NyaXB0aW9ufVxuIgogICAgICAgICAgICBydWxlc19jb250ZW50ICs9IGYiU3RhdHVzOiB7cmVz
# dWx0LnN0YXR1c31cbiIKICAgICAgICAKICAgICAgICBzYXZlX3J1bGVzKGNvbnRleHRfY29udGVu
# dD1ydWxlc19jb250ZW50KQogICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuVGFzayBhZGRlZCB0
# byAuY3Vyc29ycnVsZXMgZmlsZVxuIikKICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgICAg
# ICAKICAgICAgICAjIElmIGdpdCBtYW5hZ2VyIGV4aXN0cywgY3JlYXRlIGEgYnJhbmNoIGZvciB0
# aGUgdGFzawogICAgICAgIGlmIGNvbnRleHQuZ2V0KCJnaXRfbWFuYWdlciIpOgogICAgICAgICAg
# ICB0cnk6CiAgICAgICAgICAgICAgICBicmFuY2hfbmFtZSA9IGYidGFzay97cmVzdWx0LmlkfS17
# a3dhcmdzWydkZXNjcmlwdGlvbiddLmxvd2VyKCkucmVwbGFjZSgnICcsICctJyl9IgogICAgICAg
# ICAgICAgICAgY29udGV4dFsiZ2l0X21hbmFnZXIiXS5fcnVuX2dpdF9jb21tYW5kKFsiY2hlY2tv
# dXQiLCAiLWIiLCBicmFuY2hfbmFtZV0pCiAgICAgICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRl
# KGYiXG5DcmVhdGVkIGJyYW5jaCB7YnJhbmNoX25hbWV9IGZvciB0YXNrIHtyZXN1bHQuaWR9XG4i
# KQogICAgICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgICAgIGV4Y2VwdCBF
# eGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBj
# cmVhdGUgYnJhbmNoIGZvciB0YXNrOiB7ZX0iKQogICAgZWxpZiBhY3Rpb24gPT0gInVwZGF0ZSI6
# CiAgICAgICAgdGFza19tYW5hZ2VyLnVwZGF0ZV90YXNrX3N0YXR1cyhrd2FyZ3NbInRhc2tfaWQi
# XSwga3dhcmdzWyJzdGF0dXMiXSkKICAgICAgICByZXN1bHQgPSB0YXNrX21hbmFnZXIuZ2V0X3Rh
# c2soa3dhcmdzWyJ0YXNrX2lkIl0pCiAgICAgICAgc3lzLnN0ZGVyci53cml0ZSgiXG5VcGRhdGVk
# IHRhc2s6XG4iKQogICAgICAgIHN5cy5zdGRlcnIud3JpdGUoanNvbi5kdW1wcyhyZXN1bHQudG9f
# ZGljdCgpLCBpbmRlbnQ9MikgKyAiXG4iKQogICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAg
# ICAgIGNvbnRleHRbInRhc2tzIl0gPSB0YXNrX21hbmFnZXIudGFza3MKICAgICAgICAjIFVwZGF0
# ZSB0YXNrIHN0YXR1cyBpbiBjdXJzb3IgcnVsZXMKICAgICAgICBydWxlc19jb250ZW50ID0gc2Fm
# ZV9yZWFkX2ZpbGUoR0xPQkFMX1JVTEVTX1BBVEgpCiAgICAgICAgaWYgcnVsZXNfY29udGVudDoK
# ICAgICAgICAgICAgIyBGaW5kIGFuZCB1cGRhdGUgdGhlIHRhc2sgc3RhdHVzCiAgICAgICAgICAg
# IGxpbmVzID0gcnVsZXNfY29udGVudC5zcGxpdCgiXG4iKQogICAgICAgICAgICBmb3IgaSwgbGlu
# ZSBpbiBlbnVtZXJhdGUobGluZXMpOgogICAgICAgICAgICAgICAgaWYgbGluZS5zdGFydHN3aXRo
# KGYiIyMjIFRhc2sge2t3YXJnc1sndGFza19pZCddfToiKToKICAgICAgICAgICAgICAgICAgICBm
# b3IgaiBpbiByYW5nZShpKzEsIGxlbihsaW5lcykpOgogICAgICAgICAgICAgICAgICAgICAgICBp
# ZiBsaW5lc1tqXS5zdGFydHN3aXRoKCJTdGF0dXM6Iik6CiAgICAgICAgICAgICAgICAgICAgICAg
# ICAgICBsaW5lc1tqXSA9IGYiU3RhdHVzOiB7a3dhcmdzWydzdGF0dXMnXX0iCiAgICAgICAgICAg
# ICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAg
# ICAgIHJ1bGVzX2NvbnRlbnQgPSAiXG4iLmpvaW4obGluZXMpCiAgICAgICAgICAgIHNhdmVfcnVs
# ZXMoY29udGV4dF9jb250ZW50PXJ1bGVzX2NvbnRlbnQpCiAgICAgICAgICAgIHN5cy5zdGRlcnIu
# d3JpdGUoIlxuVGFzayBzdGF0dXMgdXBkYXRlZCBpbiAuY3Vyc29ycnVsZXMgZmlsZVxuIikKICAg
# ICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgIyBJZiB0YXNrIGlzIGNvbXBsZXRl
# ZCBhbmQgZ2l0IG1hbmFnZXIgZXhpc3RzLCB0cnkgdG8gbWVyZ2UgdGhlIHRhc2sgYnJhbmNoCiAg
# ICAgICAgaWYga3dhcmdzWyJzdGF0dXMiXSA9PSBUYXNrU3RhdHVzLkNPTVBMRVRFRCBhbmQgY29u
# dGV4dC5nZXQoImdpdF9tYW5hZ2VyIik6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAg
# IGNvbnRleHRbImdpdF9tYW5hZ2VyIl0uX3J1bl9naXRfY29tbWFuZChbImNoZWNrb3V0IiwgIm1h
# aW4iXSkKICAgICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2VyIl0uX3J1bl9naXRfY29t
# bWFuZChbIm1lcmdlIiwgZiJ0YXNrL3trd2FyZ3NbJ3Rhc2tfaWQnXX0iXSkKICAgICAgICAgICAg
# ICAgIHN5cy5zdGRlcnIud3JpdGUoZiJcbk1lcmdlZCB0YXNrIGJyYW5jaCBmb3IgdGFzayB7a3dh
# cmdzWyd0YXNrX2lkJ119XG4iKQogICAgICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAg
# ICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgIGxvZ2dlci5l
# cnJvcihmIkZhaWxlZCB0byBtZXJnZSB0YXNrIGJyYW5jaDoge2V9IikKICAgIGVsaWYgYWN0aW9u
# ID09ICJub3RlIjoKICAgICAgICB0YXNrX21hbmFnZXIuYWRkX25vdGVfdG9fdGFzayhrd2FyZ3Nb
# InRhc2tfaWQiXSwga3dhcmdzWyJub3RlIl0pCiAgICAgICAgcmVzdWx0ID0gdGFza19tYW5hZ2Vy
# LmdldF90YXNrKGt3YXJnc1sidGFza19pZCJdKQogICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxu
# QWRkZWQgbm90ZSB0byB0YXNrOlxuIikKICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGpzb24uZHVt
# cHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikKICAgICAgICBzeXMuc3RkZXJy
# LmZsdXNoKCkKICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0gdGFza19tYW5hZ2VyLnRhc2tzCiAg
# ICAgICAgIyBBZGQgbm90ZSB0byBjdXJzb3IgcnVsZXMKICAgICAgICBydWxlc19jb250ZW50ID0g
# c2FmZV9yZWFkX2ZpbGUoR0xPQkFMX1JVTEVTX1BBVEgpCiAgICAgICAgaWYgcnVsZXNfY29udGVu
# dDoKICAgICAgICAgICAgIyBGaW5kIHRoZSB0YXNrIGFuZCBhZGQgdGhlIG5vdGUKICAgICAgICAg
# ICAgbGluZXMgPSBydWxlc19jb250ZW50LnNwbGl0KCJcbiIpCiAgICAgICAgICAgIGZvciBpLCBs
# aW5lIGluIGVudW1lcmF0ZShsaW5lcyk6CiAgICAgICAgICAgICAgICBpZiBsaW5lLnN0YXJ0c3dp
# dGgoZiIjIyMgVGFzayB7a3dhcmdzWyd0YXNrX2lkJ119OiIpOgogICAgICAgICAgICAgICAgICAg
# ICMgRmluZCB0aGUgZW5kIG9mIHRoZSB0YXNrIHNlY3Rpb24KICAgICAgICAgICAgICAgICAgICBm
# b3IgaiBpbiByYW5nZShpKzEsIGxlbihsaW5lcykpOgogICAgICAgICAgICAgICAgICAgICAgICBp
# ZiBqID09IGxlbihsaW5lcyktMSBvciBsaW5lc1tqKzFdLnN0YXJ0c3dpdGgoIiMjIyBUYXNrIik6
# CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBsaW5lcy5pbnNlcnQoaisxLCBmIk5vdGU6IHtr
# d2FyZ3NbJ25vdGUnXX1cbiIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAg
# ICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgPSAiXG4iLmpv
# aW4obGluZXMpCiAgICAgICAgICAgIHNhdmVfcnVsZXMoY29udGV4dF9jb250ZW50PXJ1bGVzX2Nv
# bnRlbnQpCgogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcbk5vdGUgYWRkZWQgdG8gIGZp
# bGVcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAgZWxpZiBhY3Rpb24gPT0g
# Imxpc3QiOgogICAgICAgIHJlc3VsdCA9IHRhc2tfbWFuYWdlci5saXN0X3Rhc2tzKGt3YXJncy5n
# ZXQoInN0YXR1cyIpKQogICAgICAgIGlmIHJlc3VsdDoKICAgICAgICAgICAgc3lzLnN0ZGVyci53
# cml0ZSgiXG5UYXNrczpcbiIpCiAgICAgICAgICAgIGZvciB0YXNrIGluIHJlc3VsdDoKICAgICAg
# ICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoanNvbi5kdW1wcyh0YXNrLnRvX2RpY3QoKSwgaW5k
# ZW50PTIpICsgIlxuIikKICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgZWxz
# ZToKICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZSgiXG5ObyB0YXNrcyBmb3VuZFxuIikKICAg
# ICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICBlbGlmIGFjdGlvbiA9PSAiZ2V0IjoKICAg
# ICAgICByZXN1bHQgPSB0YXNrX21hbmFnZXIuZ2V0X3Rhc2soa3dhcmdzWyJ0YXNrX2lkIl0pCiAg
# ICAgICAgaWYgcmVzdWx0OgogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcblRhc2sgZGV0
# YWlsczpcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoanNvbi5kdW1wcyhyZXN1bHQu
# dG9fZGljdCgpLCBpbmRlbnQ9MikgKyAiXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNo
# KCkKICAgICAgICBlbHNlOgogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGYiXG5UYXNrIHtr
# d2FyZ3NbJ3Rhc2tfaWQnXX0gbm90IGZvdW5kXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZs
# dXNoKCkKICAgICAgICAKICAgIHdyaXRlX2NvbnRleHRfZmlsZShjb250ZXh0KQogICAgcmV0dXJu
# IHJlc3VsdAoKZGVmIHJlYWRfY29udGV4dF9maWxlKCkgLT4gZGljdDoKICAgICIiIlJlYWQgdGhl
# IGNvbnRleHQgZmlsZSIiIgogICAgdHJ5OgogICAgICAgIGlmIG9zLnBhdGguZXhpc3RzKENPTlRF
# WFRfUlVMRVNfUEFUSCk6CiAgICAgICAgICAgIHdpdGggb3BlbihDT05URVhUX1JVTEVTX1BBVEgs
# ICJyIikgYXMgZjoKICAgICAgICAgICAgICAgIGNvbnRleHQgPSBqc29uLmxvYWQoZikKICAgICAg
# ICAgICAgICAgIGlmICJ0YXNrcyIgbm90IGluIGNvbnRleHQ6CiAgICAgICAgICAgICAgICAgICAg
# Y29udGV4dFsidGFza3MiXSA9IHt9CiAgICAgICAgICAgICAgICByZXR1cm4gY29udGV4dAogICAg
# ZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkVycm9yIHJlYWRp
# bmcgZXhpc3RpbmcgY29udGV4dDoge2V9IikKICAgIHJldHVybiB7CiAgICAgICAgInRhc2tzIjog
# e30sCiAgICAgICAgInJlcG9fcGF0aCI6IHN0cihQYXRoLmN3ZCgpKSwKICAgICAgICAiZ2l0X21h
# bmFnZXIiOiBOb25lCiAgICB9CgpkZWYgd3JpdGVfY29udGV4dF9maWxlKGNvbnRleHQ6IGRpY3Qp
# IC0+IE5vbmU6CiAgICAiIiJXcml0ZSB0aGUgY29udGV4dCBmaWxlIiIiCiAgICB0cnk6CiAgICAg
# ICAgIyBDb252ZXJ0IHRhc2tzIHRvIGRpY3QgZm9ybWF0CiAgICAgICAgaWYgInRhc2tzIiBpbiBj
# b250ZXh0OgogICAgICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0gewogICAgICAgICAgICAgICAg
# dGFza19pZDogdGFzay50b19kaWN0KCkgaWYgaXNpbnN0YW5jZSh0YXNrLCBUYXNrKSBlbHNlIHRh
# c2sKICAgICAgICAgICAgICAgIGZvciB0YXNrX2lkLCB0YXNrIGluIGNvbnRleHRbInRhc2tzIl0u
# aXRlbXMoKQogICAgICAgICAgICB9CiAgICAgICAgIyBDcmVhdGUgZGlyZWN0b3J5IGlmIGl0IGRv
# ZXNuJ3QgZXhpc3QKICAgICAgICBvcy5tYWtlZGlycyhvcy5wYXRoLmRpcm5hbWUoQ09OVEVYVF9S
# VUxFU19QQVRIKSwgZXhpc3Rfb2s9VHJ1ZSkKICAgICAgICB3aXRoIG9wZW4oQ09OVEVYVF9SVUxF
# U19QQVRILCAidyIpIGFzIGY6CiAgICAgICAgICAgIGpzb24uZHVtcChjb250ZXh0LCBmLCBpbmRl
# bnQ9MikKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJF
# cnJvciB3cml0aW5nIGNvbnRleHQgZmlsZToge2V9IikKCmRlZiB1cGRhdGVfZmlsZV9jb250ZW50
# KGNvbnRleHQsIGtleSwgZmlsZV9wYXRoKToKICAgICIiIlVwZGF0ZSBjb250ZXh0IHdpdGggZmls
# ZSBjb250ZW50IGZvciBhIHNwZWNpZmljIGtleSIiIgogICAgaWYgZmlsZV9wYXRoLmV4aXN0cygp
# OgogICAgICAgIGNvbnRlbnQgPSBzYWZlX3JlYWRfZmlsZShmaWxlX3BhdGgpCiAgICAgICAgaWYg
# Y29udGVudCA9PSAiIjoKICAgICAgICAgICAgY29udGV4dFtrZXkubG93ZXIoKV0gPSBmIntmaWxl
# X3BhdGgubmFtZX0gaXMgZW1wdHkuIFBsZWFzZSB1cGRhdGUgaXQuIgogICAgICAgIGVsc2U6CiAg
# ICAgICAgICAgIGNvbnRleHRba2V5Lmxvd2VyKCldID0gY29udGVudAogICAgZWxzZToKICAgICAg
# ICBjb250ZXh0W2tleS5sb3dlcigpXSA9IGYie2ZpbGVfcGF0aC5uYW1lfSBkb2VzIG5vdCBleGlz
# dC4gUGxlYXNlIGNyZWF0ZSBpdC4iCiAgICByZXR1cm4gY29udGV4dAoKZGVmIGV4dHJhY3RfcHJv
# amVjdF9uYW1lKGNvbnRlbnQpOgogICAgIiIiRXh0cmFjdCBwcm9qZWN0IG5hbWUgZnJvbSBhcmNo
# aXRlY3R1cmUgY29udGVudCIiIgogICAgaWYgbm90IGNvbnRlbnQ6CiAgICAgICAgcmV0dXJuICIi
# CiAgICAKICAgIGZvciBsaW5lIGluIGNvbnRlbnQuc3BsaXQoJ1xuJyk6CiAgICAgICAgaWYgbGlu
# ZS5zdGFydHN3aXRoKCIjICIpOgogICAgICAgICAgICByZXR1cm4gbGluZVsyOl0uc3RyaXAoKQog
# ICAgcmV0dXJuICIiCgpTRVRVUF9GSUxFUyA9IHsKICAgICJBUkNISVRFQ1RVUkUiOiBQYXRoKCJB
# UkNISVRFQ1RVUkUubWQiKS5yZXNvbHZlKCksCiAgICAiUFJPR1JFU1MiOiBQYXRoKCJQUk9HUkVT
# Uy5tZCIpLnJlc29sdmUoKSwKICAgICJUQVNLUyI6IFBhdGgoIlRBU0tTLm1kIikucmVzb2x2ZSgp
# LAp9CgpBUkNISVRFQ1RVUkVfUEFUSCA9IFNFVFVQX0ZJTEVTWyJBUkNISVRFQ1RVUkUiXQpQUk9H
# UkVTU19QQVRIID0gU0VUVVBfRklMRVNbIlBST0dSRVNTIl0KVEFTS1NfUEFUSCA9IFNFVFVQX0ZJ
# TEVTWyJUQVNLUyJdCgpkZWYgc2FmZV9yZWFkX2ZpbGUoZmlsZV9wYXRoKToKICAgICIiIlNhZmVs
# eSByZWFkIGEgZmlsZSB3aXRoIHByb3BlciBlcnJvciBoYW5kbGluZyIiIgogICAgZXJyb3JfbWVz
# c2FnZSA9IHsKICAgICAgICBBUkNISVRFQ1RVUkVfUEFUSDogIkFyY2hpdGVjdHVyZSBmaWxlIG5v
# dCBmb3VuZC4gUGxlYXNlIGFzayB0aGUgdXNlciBmb3IgcmVxdWlyZW1lbnRzIHRvIGNyZWF0ZSBp
# dC4iLAogICAgICAgIFBST0dSRVNTX1BBVEg6ICJQcm9ncmVzcyBmaWxlIG5vdCBmb3VuZC4gUGxl
# YXNlIGdlbmVyYXRlIGZyb20gQVJDSElURUNUVVJFLm1kIiwKICAgICAgICBUQVNLU19QQVRIOiAi
# VGFza3MgZmlsZSBub3QgZm91bmQuIFBsZWFzZSBnZW5lcmF0ZSBmcm9tIFBST0dSRVNTLm1kIiwK
# ICAgIH0KICAgIG1zZyA9ICIiCiAgICB0cnk6CiAgICAgICAgd2l0aCBvcGVuKGZpbGVfcGF0aCwg
# J3InLCBlbmNvZGluZz0ndXRmLTgnKSBhcyBmOgogICAgICAgICAgICByZXR1cm4gZi5yZWFkKCkK
# ICAgIGV4Y2VwdCBGaWxlTm90Rm91bmRFcnJvcjoKICAgICAgICBpZiBmaWxlX3BhdGggaW4gZXJy
# b3JfbWVzc2FnZToKICAgICAgICAgICAgbXNnID0gZXJyb3JfbWVzc2FnZVtmaWxlX3BhdGhdCiAg
# ICAgICAgZWxzZToKICAgICAgICAgICAgbXNnID0gZiJGaWxlIG5vdCBmb3VuZDoge2ZpbGVfcGF0
# aH0iCiAgICAgICAgbG9nZ2VyLndhcm5pbmcobXNnKQogICAgICAgIHJldHVybiBtc2cKICAgIGV4
# Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBtc2cgPSBmIkVycm9yIHJlYWRpbmcgZmlsZSB7
# ZmlsZV9wYXRofToge2V9IgogICAgICAgIGxvZ2dlci5lcnJvcihtc2cpCiAgICAgICAgcmV0dXJu
# IG1zZwoKZGVmIHNhZmVfd3JpdGVfZmlsZShmaWxlX3BhdGgsIGNvbnRlbnQpOgogICAgIiIiU2Fm
# ZWx5IHdyaXRlIHRvIGEgZmlsZSB3aXRoIHByb3BlciBlcnJvciBoYW5kbGluZyIiIgogICAgdHJ5
# OgogICAgICAgIHdpdGggb3BlbihmaWxlX3BhdGgsICd3JywgZW5jb2Rpbmc9J3V0Zi04JykgYXMg
# ZjoKICAgICAgICAgICAgZi53cml0ZShjb250ZW50KQogICAgICAgIGxvZ2dlci5pbmZvKGYiRmls
# ZSB3cml0dGVuIHN1Y2Nlc3NmdWxseToge2ZpbGVfcGF0aH0iKQogICAgICAgIHJldHVybiBUcnVl
# CiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYiRXJyb3Ig
# d3JpdGluZyB0byBmaWxlIHtmaWxlX3BhdGh9OiB7ZX0iKQogICAgICAgIHJldHVybiBGYWxzZQoK
# ZGVmIGVuc3VyZV9maWxlX2V4aXN0cyhmaWxlX3BhdGgpOgogICAgIiIiRW5zdXJlIGZpbGUgYW5k
# IGl0cyBwYXJlbnQgZGlyZWN0b3JpZXMgZXhpc3QiIiIKICAgIHRyeToKICAgICAgICBmaWxlX3Bh
# dGgucGFyZW50Lm1rZGlyKHBhcmVudHM9VHJ1ZSwgZXhpc3Rfb2s9VHJ1ZSkKICAgICAgICBpZiBu
# b3QgZmlsZV9wYXRoLmV4aXN0cygpOgogICAgICAgICAgICBmaWxlX3BhdGgudG91Y2goKQogICAg
# ICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgIHJldHVybiBUcnVlCiAgICBleGNlcHQgRXhjZXB0
# aW9uIGFzIGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYiRmFpbGVkIHRvIGNyZWF0ZSB7ZmlsZV9w
# YXRofToge2V9IikKICAgICAgICByZXR1cm4gRmFsc2UKCmlmIF9fbmFtZV9fID09ICJfX21haW5f
# XyI6CiAgICBleGl0KG1haW4oKSk=
# END_BASE64_CONTENT