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


# __ERASMUS_EMBEDDED_BELOW__
# The content below this line is the base64-encoded erasmus.py file
# It will be extracted during installation
# SHA256_HASH=292cd9aa2e90902d05e7af78cde76a0f3606b48dc7f14cda695f4472228a545b
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
# bmcgaW1wb3J0IE9wdGlvbmFsLCBMaXN0LCBEaWN0LCBUdXBsZQoKIyA9PT0gVGFzayBUcmFja2lu
# ZyA9PT0KY2xhc3MgVGFza1N0YXR1czoKICAgIFBFTkRJTkcgPSAicGVuZGluZyIKICAgIElOX1BS
# T0dSRVNTID0gImluX3Byb2dyZXNzIgogICAgQ09NUExFVEVEID0gImNvbXBsZXRlZCIKICAgIEJM
# T0NLRUQgPSAiYmxvY2tlZCIKICAgIE5PVF9TVEFSVEVEID0gIm5vdF9zdGFydGVkIgoKY2xhc3Mg
# VGFzazoKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBpZDogc3RyLCBkZXNjcmlwdGlvbjogc3RyKToK
# ICAgICAgICBzZWxmLmlkID0gaWQKICAgICAgICBzZWxmLmRlc2NyaXB0aW9uID0gZGVzY3JpcHRp
# b24KICAgICAgICBzZWxmLnN0YXR1cyA9IFRhc2tTdGF0dXMuTk9UX1NUQVJURUQKICAgICAgICBz
# ZWxmLmNyZWF0ZWRfYXQgPSB0aW1lLnRpbWUoKQogICAgICAgIHNlbGYudXBkYXRlZF9hdCA9IHRp
# bWUudGltZSgpCiAgICAgICAgc2VsZi5jb21wbGV0aW9uX3RpbWUgPSBOb25lCiAgICAgICAgc2Vs
# Zi5ub3RlcyA9IFtdCiAgICAgICAgCiAgICBkZWYgdG9fZGljdChzZWxmKSAtPiBkaWN0OgogICAg
# ICAgICIiIkNvbnZlcnQgdGFzayB0byBkaWN0aW9uYXJ5IiIiCiAgICAgICAgcmV0dXJuIHsKICAg
# ICAgICAgICAgImlkIjogc2VsZi5pZCwKICAgICAgICAgICAgImRlc2NyaXB0aW9uIjogc2VsZi5k
# ZXNjcmlwdGlvbiwKICAgICAgICAgICAgInN0YXR1cyI6IHNlbGYuc3RhdHVzLAogICAgICAgICAg
# ICAiY3JlYXRlZF9hdCI6IHNlbGYuY3JlYXRlZF9hdCwKICAgICAgICAgICAgInVwZGF0ZWRfYXQi
# OiBzZWxmLnVwZGF0ZWRfYXQsCiAgICAgICAgICAgICJjb21wbGV0aW9uX3RpbWUiOiBzZWxmLmNv
# bXBsZXRpb25fdGltZSwKICAgICAgICAgICAgIm5vdGVzIjogc2VsZi5ub3RlcwogICAgICAgIH0K
# ICAgIAogICAgQGNsYXNzbWV0aG9kCiAgICBkZWYgZnJvbV9kaWN0KGNscywgZGF0YTogZGljdCkg
# LT4gJ1Rhc2snOgogICAgICAgICIiIkNyZWF0ZSBhIHRhc2sgZnJvbSBkaWN0aW9uYXJ5IiIiCiAg
# ICAgICAgdGFzayA9IGNscyhkYXRhWyJpZCJdLCBkYXRhWyJkZXNjcmlwdGlvbiJdKQogICAgICAg
# IHRhc2suc3RhdHVzID0gZGF0YVsic3RhdHVzIl0KICAgICAgICB0YXNrLmNyZWF0ZWRfYXQgPSBk
# YXRhWyJjcmVhdGVkX2F0Il0KICAgICAgICB0YXNrLnVwZGF0ZWRfYXQgPSBkYXRhWyJ1cGRhdGVk
# X2F0Il0KICAgICAgICB0YXNrLmNvbXBsZXRpb25fdGltZSA9IGRhdGFbImNvbXBsZXRpb25fdGlt
# ZSJdCiAgICAgICAgdGFzay5ub3RlcyA9IGRhdGFbIm5vdGVzIl0KICAgICAgICByZXR1cm4gdGFz
# awoKY2xhc3MgVGFza01hbmFnZXI6CiAgICBkZWYgX19pbml0X18oc2VsZiwgdGFza3M6IGRpY3Qg
# PSBOb25lKToKICAgICAgICBzZWxmLnRhc2tzID0ge30KICAgICAgICBpZiB0YXNrczoKICAgICAg
# ICAgICAgc2VsZi50YXNrcyA9IHsKICAgICAgICAgICAgICAgIHRhc2tfaWQ6IFRhc2suZnJvbV9k
# aWN0KHRhc2tfZGF0YSkgaWYgaXNpbnN0YW5jZSh0YXNrX2RhdGEsIGRpY3QpIGVsc2UgdGFza19k
# YXRhCiAgICAgICAgICAgICAgICBmb3IgdGFza19pZCwgdGFza19kYXRhIGluIHRhc2tzLml0ZW1z
# KCkKICAgICAgICAgICAgfQogICAgICAgIAogICAgZGVmIGFkZF90YXNrKHNlbGYsIGRlc2NyaXB0
# aW9uOiBzdHIpIC0+IFRhc2s6CiAgICAgICAgIiIiQWRkIGEgbmV3IHRhc2siIiIKICAgICAgICB0
# YXNrX2lkID0gc3RyKGxlbihzZWxmLnRhc2tzKSArIDEpCiAgICAgICAgdGFzayA9IFRhc2sodGFz
# a19pZCwgZGVzY3JpcHRpb24pCiAgICAgICAgc2VsZi50YXNrc1t0YXNrX2lkXSA9IHRhc2sKICAg
# ICAgICByZXR1cm4gdGFzawogICAgCiAgICBkZWYgZ2V0X3Rhc2soc2VsZiwgdGFza19pZDogc3Ry
# KSAtPiBPcHRpb25hbFtUYXNrXToKICAgICAgICAiIiJHZXQgYSB0YXNrIGJ5IElEIiIiCiAgICAg
# ICAgcmV0dXJuIHNlbGYudGFza3MuZ2V0KHRhc2tfaWQpCiAgICAKICAgIGRlZiBsaXN0X3Rhc2tz
# KHNlbGYsIHN0YXR1czogT3B0aW9uYWxbVGFza1N0YXR1c10gPSBOb25lKSAtPiBMaXN0W1Rhc2td
# OgogICAgICAgICIiIkxpc3QgYWxsIHRhc2tzLCBvcHRpb25hbGx5IGZpbHRlcmVkIGJ5IHN0YXR1
# cyIiIgogICAgICAgIHRhc2tzID0gbGlzdChzZWxmLnRhc2tzLnZhbHVlcygpKQogICAgICAgIGlm
# IHN0YXR1czoKICAgICAgICAgICAgdGFza3MgPSBbdCBmb3IgdCBpbiB0YXNrcyBpZiB0LnN0YXR1
# cyA9PSBzdGF0dXNdCiAgICAgICAgcmV0dXJuIHRhc2tzCiAgICAKICAgIGRlZiB1cGRhdGVfdGFz
# a19zdGF0dXMoc2VsZiwgdGFza19pZDogc3RyLCBzdGF0dXM6IFRhc2tTdGF0dXMpIC0+IE5vbmU6
# CiAgICAgICAgIiIiVXBkYXRlIGEgdGFzaydzIHN0YXR1cyIiIgogICAgICAgIGlmIHRhc2sgOj0g
# c2VsZi5nZXRfdGFzayh0YXNrX2lkKToKICAgICAgICAgICAgdGFzay5zdGF0dXMgPSBzdGF0dXMK
# ICAgIAogICAgZGVmIGFkZF9ub3RlX3RvX3Rhc2soc2VsZiwgdGFza19pZDogc3RyLCBub3RlOiBz
# dHIpIC0+IE5vbmU6CiAgICAgICAgIiIiQWRkIGEgbm90ZSB0byBhIHRhc2siIiIKICAgICAgICBp
# ZiB0YXNrIDo9IHNlbGYuZ2V0X3Rhc2sodGFza19pZCk6CiAgICAgICAgICAgIHRhc2subm90ZXMu
# YXBwZW5kKG5vdGUpCiAgICAKICAgIEBjbGFzc21ldGhvZAogICAgZGVmIGZyb21fZGljdChjbHMs
# IGRhdGEpOgogICAgICAgICIiIkNyZWF0ZSBhIFRhc2tNYW5hZ2VyIGZyb20gYSBkaWN0aW9uYXJ5
# IiIiCiAgICAgICAgbWFuYWdlciA9IGNscygpCiAgICAgICAgaWYgaXNpbnN0YW5jZShkYXRhLCBk
# aWN0KToKICAgICAgICAgICAgbWFuYWdlci50YXNrcyA9IHsKICAgICAgICAgICAgICAgIHRhc2tf
# aWQ6IFRhc2suZnJvbV9kaWN0KHRhc2tfZGF0YSkKICAgICAgICAgICAgICAgIGZvciB0YXNrX2lk
# LCB0YXNrX2RhdGEgaW4gZGF0YS5pdGVtcygpCiAgICAgICAgICAgIH0KICAgICAgICByZXR1cm4g
# bWFuYWdlcgoKZGVmIGlzX3ZhbGlkX3VybCh1cmw6IHN0cikgLT4gYm9vbDoKICAgICIiIkJhc2lj
# IFVSTCB2YWxpZGF0aW9uIHVzaW5nIHJlZ2V4LiIiIgogICAgbG9nZ2VyLmRlYnVnKGYiVmFsaWRh
# dGluZyBVUkw6IHt1cmx9IikKICAgIGh0dHBzX3BhdHRlcm4gPSByZS5tYXRjaChyJ15odHRwcz86
# Ly8nLCB1cmwpCiAgICBsb2dnZXIuZGVidWcoZiJodHRwc19wYXR0ZXJuOiB7aHR0cHNfcGF0dGVy
# bn0iKQogICAgaHR0cF9wYXR0ZXJuID0gcmUubWF0Y2gocideaHR0cD86Ly8nLCB1cmwpCiAgICBs
# b2dnZXIuZGVidWcoZiJodHRwX3BhdHRlcm46IHtodHRwX3BhdHRlcm59IikKICAgIHJldHVybiBo
# dHRwc19wYXR0ZXJuIG9yIGh0dHBfcGF0dGVybgoKIyA9PT0gT3BlbkFJIENvbmZpZ3VyYXRpb24g
# PT09CgoKZGVmIGlzX3ZhbGlkX3VybCh1cmw6IHN0cikgLT4gYm9vbDoKICAgICIiIkJhc2ljIFVS
# TCB2YWxpZGF0aW9uIHVzaW5nIHJlZ2V4LiIiIgogICAgIyBBY2NlcHQgbG9jYWxob3N0IFVSTHMg
# YW5kIHN0YW5kYXJkIGh0dHAvaHR0cHMgVVJMcwogICAgaWYgbm90IHVybDoKICAgICAgICByZXR1
# cm4gRmFsc2UKICAgIAogICAgIyBDaGVjayBmb3IgbG9jYWxob3N0IG9yIDEyNy4wLjAuMQogICAg
# bG9jYWxob3N0X3BhdHRlcm4gPSByZS5tYXRjaChyJ15odHRwcz86Ly8oPzpsb2NhbGhvc3R8MTI3
# XC4wXC4wXC4xKSg/OjpcZCspPyg/Oi8uKik/JCcsIHVybCkKICAgIGlmIGxvY2FsaG9zdF9wYXR0
# ZXJuOgogICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgCiAgICAjIENoZWNrIGZvciBzdGFuZGFy
# ZCBodHRwL2h0dHBzIFVSTHMKICAgIHN0YW5kYXJkX3BhdHRlcm4gPSByZS5tYXRjaChyJ15odHRw
# cz86Ly9bXHdcLi1dKyg/OjpcZCspPyg/Oi8uKik/JCcsIHVybCkKICAgIHJldHVybiBib29sKHN0
# YW5kYXJkX3BhdHRlcm4pCgpkZWYgcHJvbXB0X29wZW5haV9jcmVkZW50aWFscyhlbnZfcGF0aD0i
# LmVudiIpOgogICAgIiIiUHJvbXB0IHVzZXIgZm9yIE9wZW5BSSBjcmVkZW50aWFscyBhbmQgc2F2
# ZSB0byAuZW52IiIiCiAgICBhcGlfa2V5ID0gZ2V0cGFzcygiRW50ZXIgeW91ciBPUEVOQUlfQVBJ
# X0tFWSAoaW5wdXQgaGlkZGVuKTogIikKCiAgICBiYXNlX3VybCA9IGlucHV0KCJFbnRlciB5b3Vy
# IE9QRU5BSV9CQVNFX1VSTCAoZGVmYXVsdDogaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSk6ICIp
# LnN0cmlwKCkKICAgIGlmIG5vdCBpc192YWxpZF91cmwoYmFzZV91cmwpOgogICAgICAgIHByaW50
# KCJJbnZhbGlkIFVSTCBvciBlbXB0eS4gRGVmYXVsdGluZyB0byBodHRwczovL2FwaS5vcGVuYWku
# Y29tL3YxIikKICAgICAgICBiYXNlX3VybCA9ICJodHRwczovL2FwaS5vcGVuYWkuY29tL3YxIgoK
# ICAgIG1vZGVsID0gaW5wdXQoIkVudGVyIHlvdXIgT1BFTkFJX01PREVMIChkZWZhdWx0OiBncHQt
# NG8pOiAiKS5zdHJpcCgpCiAgICBpZiBub3QgbW9kZWw6CiAgICAgICAgbW9kZWwgPSAiZ3B0LTRv
# IgogICAgICAgIAogICAgIyBEZXRlY3QgSURFIGVudmlyb25tZW50IGFuZCBzYXZlIGl0IHRvIHRo
# ZSAuZW52IGZpbGUKICAgIGlkZV9lbnYgPSBkZXRlY3RfaWRlX2Vudmlyb25tZW50KCkKICAgIAog
# ICAgZW52X2NvbnRlbnQgPSAoCiAgICAgICAgZiJPUEVOQUlfQVBJX0tFWT17YXBpX2tleX1cbiIK
# ICAgICAgICBmIk9QRU5BSV9CQVNFX1VSTD17YmFzZV91cmx9XG4iCiAgICAgICAgZiJPUEVOQUlf
# TU9ERUw9e21vZGVsfVxuIgogICAgICAgIGYiSURFX0VOVj17aWRlX2Vudn1cbiIKICAgICkKCiAg
# ICBQYXRoKGVudl9wYXRoKS53cml0ZV90ZXh0KGVudl9jb250ZW50KQogICAgcHJpbnQoZiLinIUg
# T3BlbkFJIGNyZWRlbnRpYWxzIHNhdmVkIHRvIHtlbnZfcGF0aH0iKQoKIyA9PT0gQ29uZmlndXJh
# dGlvbiBhbmQgU2V0dXAgPT09CmxvYWRfZG90ZW52KCkKCiMgQ29uZmlndXJlIHJpY2ggY29uc29s
# ZSBhbmQgbG9nZ2luZwpjb25zb2xlID0gY29uc29sZS5Db25zb2xlKCkKbG9nZ2luZ19oYW5kbGVy
# ID0gUmljaEhhbmRsZXIoCiAgICBjb25zb2xlPWNvbnNvbGUsCiAgICBzaG93X3RpbWU9VHJ1ZSwK
# ICAgIHNob3dfcGF0aD1GYWxzZSwKICAgIHJpY2hfdHJhY2ViYWNrcz1UcnVlLAogICAgdHJhY2Vi
# YWNrc19zaG93X2xvY2Fscz1UcnVlCikKCiMgU2V0IHVwIGxvZ2dpbmcgY29uZmlndXJhdGlvbgps
# b2dnaW5nLmJhc2ljQ29uZmlnKAogICAgbGV2ZWw9b3MuZ2V0ZW52KCJMT0dfTEVWRUwiLCAiSU5G
# TyIpLAogICAgZm9ybWF0PSIlKG1lc3NhZ2UpcyIsCiAgICBkYXRlZm10PSJbJVhdIiwKICAgIGhh
# bmRsZXJzPVtsb2dnaW5nX2hhbmRsZXJdCikKCiMgQ3JlYXRlIGxvZ2dlciBpbnN0YW5jZQpsb2dn
# ZXIgPSBsb2dnaW5nLmdldExvZ2dlcigiY29udGV4dF93YXRjaGVyIikKCiMgQWRkIGZpbGUgaGFu
# ZGxlciBmb3IgcGVyc2lzdGVudCBsb2dnaW5nCnRyeToKICAgIGZpbGVfaGFuZGxlciA9IGxvZ2dp
# bmcuRmlsZUhhbmRsZXIoImNvbnRleHRfd2F0Y2hlci5sb2ciKQogICAgZmlsZV9oYW5kbGVyLnNl
# dExldmVsKGxvZ2dpbmcuREVCVUcpCiAgICBmaWxlX2Zvcm1hdHRlciA9IGxvZ2dpbmcuRm9ybWF0
# dGVyKCclKGFzY3RpbWUpcyAtICUobmFtZSlzIC0gJShsZXZlbG5hbWUpcyAtICUobWVzc2FnZSlz
# JykKICAgIGZpbGVfaGFuZGxlci5zZXRGb3JtYXR0ZXIoZmlsZV9mb3JtYXR0ZXIpCiAgICBsb2dn
# ZXIuYWRkSGFuZGxlcihmaWxlX2hhbmRsZXIpCmV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgIGxv
# Z2dlci53YXJuaW5nKGYiQ291bGQgbm90IHNldCB1cCBmaWxlIGxvZ2dpbmc6IHtlfSIpCgpkZWYg
# Z2V0X29wZW5haV9jcmVkZW50aWFscygpOgogICAgYXBpX2tleSA9IG9zLmVudmlyb24uZ2V0KCJP
# UEVOQUlfQVBJX0tFWSIpCiAgICBiYXNlX3VybCA9IG9zLmVudmlyb24uZ2V0KCJPUEVOQUlfQkFT
# RV9VUkwiKSBvciAiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIKICAgIG1vZGVsID0gb3MuZW52
# aXJvbi5nZXQoIk9QRU5BSV9NT0RFTCIpCiAgICByZXR1cm4gYXBpX2tleSwgYmFzZV91cmwsIG1v
# ZGVsCgojIC0tLSBPcGVuQUkgQ2xpZW50IEluaXRpYWxpemF0aW9uIC0tLQpkZWYgaW5pdF9vcGVu
# YWlfY2xpZW50KCk6CiAgICAiIiJJbml0aWFsaXplIGFuZCByZXR1cm4gT3BlbkFJIGNsaWVudCBj
# b25maWd1cmF0aW9uIiIiCiAgICB0cnk6CiAgICAgICAgYXBpX2tleSwgYmFzZV91cmwsIG1vZGVs
# ID0gZ2V0X29wZW5haV9jcmVkZW50aWFscygpCiAgICAgICAgaWYgbm90IGFwaV9rZXkgb3Igbm90
# IGlzX3ZhbGlkX3VybChiYXNlX3VybCkgb3Igbm90IG1vZGVsOgogICAgICAgICAgICBsb2dnZXIu
# d2FybmluZygiTWlzc2luZyBPcGVuQUkgY3JlZGVudGlhbHMuIFByb21wdGluZyBmb3IgaW5wdXQu
# Li4iKQogICAgICAgICAgICBwcm9tcHRfb3BlbmFpX2NyZWRlbnRpYWxzKCkKICAgICAgICAgICAg
# YXBpX2tleSwgYmFzZV91cmwsIG1vZGVsID0gZ2V0X29wZW5haV9jcmVkZW50aWFscygpCiAgICAg
# ICAgICAgIGlmIG5vdCBhcGlfa2V5IG9yIG5vdCBtb2RlbCBvciBub3QgYmFzZV91cmw6CiAgICAg
# ICAgICAgICAgICBsb2dnZXIuZXJyb3IoIkZhaWxlZCB0byBpbml0aWFsaXplIE9wZW5BSSBjbGll
# bnQ6IG1pc3NpbmcgY3JlZGVudGlhbHMiKQogICAgICAgICAgICAgICAgcmV0dXJuIE5vbmUsIE5v
# bmUKICAgICAgICAKICAgICAgICBjbGllbnQgPSBPcGVuQUkoYXBpX2tleT1hcGlfa2V5LCBiYXNl
# X3VybD1iYXNlX3VybCkKICAgICAgICByZXR1cm4gY2xpZW50LCBtb2RlbAogICAgZXhjZXB0IEV4
# Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBpbml0aWFsaXpl
# IE9wZW5BSSBjbGllbnQ6IHtlfSIpCiAgICAgICAgcmV0dXJuIE5vbmUsIE5vbmUKCiMgR2xvYmFs
# IHZhcmlhYmxlcwpDTElFTlQsIE9QRU5BSV9NT0RFTCA9IGluaXRfb3BlbmFpX2NsaWVudCgpClBX
# RCA9IFBhdGgoX19maWxlX18pLnBhcmVudAoKIyA9PT0gQXJndW1lbnQgUGFyc2luZyA9PT0KZGVm
# IHBhcnNlX2FyZ3VtZW50cygpOgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIo
# ZGVzY3JpcHRpb249IlVwZGF0ZSBzY3JpcHQgZm9yIHByb2plY3QiKQogICAgcGFyc2VyLmFkZF9h
# cmd1bWVudCgiLS13YXRjaCIsIGFjdGlvbj0ic3RvcmVfdHJ1ZSIsIGhlbHA9IkVuYWJsZSBmaWxl
# IHdhdGNoaW5nIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tdXBkYXRlIiwgY2hvaWNlcz1b
# ImFyY2hpdGVjdHVyZSIsICJwcm9ncmVzcyIsICJ0YXNrcyIsICJjb250ZXh0Il0sIAogICAgICAg
# ICAgICAgICAgICAgICAgaGVscD0iRmlsZSB0byB1cGRhdGUiKQogICAgcGFyc2VyLmFkZF9hcmd1
# bWVudCgiLS11cGRhdGUtdmFsdWUiLCBoZWxwPSJOZXcgdmFsdWUgdG8gd3JpdGUgdG8gdGhlIHNw
# ZWNpZmllZCBmaWxlIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tc2V0dXAiLCBjaG9pY2Vz
# PVsiY3Vyc29yIiwgIndpbmRzdXJmIl0sIGhlbHA9IlNldHVwIHByb2plY3QiLCBkZWZhdWx0PSJj
# dXJzb3IiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS10eXBlIiwgY2hvaWNlcz1bImN1cnNv
# ciIsICJ3aW5kc3VyZiJdLCBoZWxwPSJQcm9qZWN0IHR5cGUiLCBkZWZhdWx0PSJjdXJzb3IiKQog
# ICAgCiAgICAjIFRhc2sgbWFuYWdlbWVudCBhcmd1bWVudHMKICAgIHRhc2tfZ3JvdXAgPSBwYXJz
# ZXIuYWRkX2FyZ3VtZW50X2dyb3VwKCJUYXNrIE1hbmFnZW1lbnQiKQogICAgdGFza19ncm91cC5h
# ZGRfYXJndW1lbnQoIi0tdGFzay1hY3Rpb24iLCBjaG9pY2VzPVsiYWRkIiwgInVwZGF0ZSIsICJu
# b3RlIiwgImxpc3QiLCAiZ2V0Il0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgIGhlbHA9IlRh
# c2sgbWFuYWdlbWVudCBhY3Rpb24iKQogICAgdGFza19ncm91cC5hZGRfYXJndW1lbnQoIi0tdGFz
# ay1pZCIsIGhlbHA9IlRhc2sgSUQgZm9yIHVwZGF0ZS9ub3RlL2dldCBhY3Rpb25zIikKICAgIHRh
# c2tfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLXRhc2stZGVzY3JpcHRpb24iLCBoZWxwPSJUYXNrIGRl
# c2NyaXB0aW9uIGZvciBhZGQgYWN0aW9uIikKICAgIHRhc2tfZ3JvdXAuYWRkX2FyZ3VtZW50KCIt
# LXRhc2stc3RhdHVzIiwgY2hvaWNlcz1bVGFza1N0YXR1cy5QRU5ESU5HLCBUYXNrU3RhdHVzLklO
# X1BST0dSRVNTLCAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
# ICAgICAgICBUYXNrU3RhdHVzLkNPTVBMRVRFRCwgVGFza1N0YXR1cy5CTE9DS0VEXSwKICAgICAg
# ICAgICAgICAgICAgICAgICAgICAgaGVscD0iVGFzayBzdGF0dXMgZm9yIHVwZGF0ZSBhY3Rpb24i
# KQogICAgdGFza19ncm91cC5hZGRfYXJndW1lbnQoIi0tdGFzay1ub3RlIiwgaGVscD0iTm90ZSBj
# b250ZW50IGZvciBub3RlIGFjdGlvbiIpCiAgICAKICAgICMgR2l0IG1hbmFnZW1lbnQgYXJndW1l
# bnRzCiAgICBnaXRfZ3JvdXAgPSBwYXJzZXIuYWRkX2FyZ3VtZW50X2dyb3VwKCJHaXQgTWFuYWdl
# bWVudCIpCiAgICBnaXRfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLWdpdC1yZXBvIiwgaGVscD0iUGF0
# aCB0byBnaXQgcmVwb3NpdG9yeSIpCiAgICBnaXRfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLWdpdC1h
# Y3Rpb24iLCBjaG9pY2VzPVsic3RhdHVzIiwgImJyYW5jaCIsICJjb21taXQiLCAicHVzaCIsICJw
# dWxsIl0sCiAgICAgICAgICAgICAgICAgICAgICAgICAgaGVscD0iR2l0IGFjdGlvbiB0byBwZXJm
# b3JtIikKICAgIGdpdF9ncm91cC5hZGRfYXJndW1lbnQoIi0tY29tbWl0LW1lc3NhZ2UiLCBoZWxw
# PSJDb21taXQgbWVzc2FnZSBmb3IgZ2l0IGNvbW1pdCBhY3Rpb24iKQogICAgZ2l0X2dyb3VwLmFk
# ZF9hcmd1bWVudCgiLS1icmFuY2gtbmFtZSIsIGhlbHA9IkJyYW5jaCBuYW1lIGZvciBnaXQgYnJh
# bmNoIGFjdGlvbiIpCiAgICAKICAgIHJldHVybiBwYXJzZXIucGFyc2VfYXJncygpCgojIEdsb2Jh
# bCBydWxlcyBjb250ZW50IGZvciBwcm9qZWN0IHNldHVwCkdMT0JBTF9SVUxFUyA9ICIiIgojIPCf
# p6AgTGVhZCBEZXZlbG9wZXIg4oCTIFByb21wdCBDb250ZXh0CgojIyDwn46vIE9CSkVDVElWRQoK
# WW91IGFyZSBhICoqTGVhZCBEZXZlbG9wZXIqKiB3b3JraW5nIGFsb25nc2lkZSBhIGh1bWFuIHBy
# b2plY3Qgb3duZXIuIFlvdXIgcm9sZSBpcyB0byBpbXBsZW1lbnQgaGlnaC1xdWFsaXR5IGNvZGUg
# YmFzZWQgb24gKipyZXF1aXJlbWVudHMqKiBhbmQgKiphcmNoaXRlY3R1cmUqKiBkb2N1bWVudGF0
# aW9uLCBmb2xsb3dpbmcgYmVzdCBwcmFjdGljZXM6CgotIFVzZSBzdHJvbmcgdHlwaW5nIGFuZCBp
# bmxpbmUgZG9jdW1lbnRhdGlvbi4KLSBQcmlvcml0aXplIGNsYXJpdHkgYW5kIHByb2R1Y3Rpb24t
# cmVhZGluZXNzIG92ZXIgdW5uZWNlc3NhcnkgYWJzdHJhY3Rpb24uCi0gT3B0aW1pemUgdGhvdWdo
# dGZ1bGx5LCB3aXRob3V0IHNhY3JpZmljaW5nIG1haW50YWluYWJpbGl0eS4KLSBBdm9pZCBzbG9w
# cHkgb3IgdW5kb2N1bWVudGVkIGltcGxlbWVudGF0aW9ucy4KCllvdSBhcmUgZW5jb3VyYWdlZCB0
# byAqKmNyaXRpY2FsbHkgZXZhbHVhdGUgZGVzaWducyoqIGFuZCBpbXByb3ZlIHRoZW0gd2hlcmUg
# YXBwcm9wcmlhdGUuIFdoZW4gaW4gZG91YnQsICoqYXNrIHF1ZXN0aW9ucyoqIOKAlCBjbGFyaXR5
# IGlzIG1vcmUgdmFsdWFibGUgdGhhbiBhc3N1bXB0aW9ucy4KCi0tLQoKIyMg8J+boO+4jyBUT09M
# UwoKWW91IHdpbGwgYmUgZ2l2ZW4gYWNjZXNzIHRvIHZhcmlvdXMgZGV2ZWxvcG1lbnQgdG9vbHMu
# IFVzZSB0aGVtIGFzIGFwcHJvcHJpYXRlLiBBZGRpdGlvbmFsICoqTUNQIHNlcnZlciB0b29scyoq
# IG1heSBiZSBpbnRyb2R1Y2VkIGxhdGVyLCB3aXRoIHVzYWdlIGluc3RydWN0aW9ucyBhcHBlbmRl
# ZCBoZXJlLgoKLS0tCgojIyDwn5OaIERPQ1VNRU5UQVRJT04KCllvdXIgd29ya3NwYWNlIHJvb3Qg
# Y29udGFpbnMgdGhyZWUga2V5IGRvY3VtZW50czoKCi0gKipBUkNISVRFQ1RVUkUubWQqKiAgCiAg
# UHJpbWFyeSBzb3VyY2Ugb2YgdHJ1dGguIENvbnRhaW5zIGFsbCBtYWpvciBjb21wb25lbnRzIGFu
# ZCB0aGVpciByZXF1aXJlbWVudHMuICAKICDihpIgSWYgbWlzc2luZywgYXNrIHRoZSB1c2VyIGZv
# ciByZXF1aXJlbWVudHMgYW5kIGdlbmVyYXRlIHRoaXMgZG9jdW1lbnQuCgotICoqUFJPR1JFU1Mu
# bWQqKiAgCiAgVHJhY2tzIG1ham9yIGNvbXBvbmVudHMgYW5kIG9yZ2FuaXplcyB0aGVtIGludG8g
# YSBkZXZlbG9wbWVudCBzY2hlZHVsZS4gIAogIOKGkiBJZiBtaXNzaW5nLCBnZW5lcmF0ZSBmcm9t
# IGBBUkNISVRFQ1RVUkUubWRgLgoKLSAqKlRBU0tTLm1kKiogIAogIENvbnRhaW5zIGFjdGlvbi1v
# cmllbnRlZCB0YXNrcyBwZXIgY29tcG9uZW50LCBzbWFsbCBlbm91Z2ggdG8gZGV2ZWxvcCBhbmQg
# dGVzdCBpbmRlcGVuZGVudGx5LiAgCiAg4oaSIElmIG1pc3NpbmcsIHNlbGVjdCB0aGUgbmV4dCBj
# b21wb25lbnQgZnJvbSBgUFJPR1JFU1MubWRgIGFuZCBicmVhayBpdCBpbnRvIHRhc2tzLgoKLS0t
# CgojIyDwn5SBIFdPUktGTE9XCgpgYGBtZXJtYWlkCmZsb3djaGFydCBURAogICAgU3RhcnQoW1N0
# YXJ0XSkKICAgIENoZWNrQXJjaGl0ZWN0dXJle0FSQ0hJVEVDVFVSRSBleGlzdHM/fQogICAgQXNr
# UmVxdWlyZW1lbnRzWyJBc2sgdXNlciBmb3IgcmVxdWlyZW1lbnRzIl0KICAgIENoZWNrUHJvZ3Jl
# c3N7UFJPR1JFU1MgZXhpc3RzP30KICAgIEJyZWFrRG93bkFyY2hbIkJyZWFrIEFSQ0hJVEVDVFVS
# RSBpbnRvIG1ham9yIGNvbXBvbmVudHMiXQogICAgRGV2U2NoZWR1bGVbIk9yZ2FuaXplIGNvbXBv
# bmVudHMgaW50byBhIGRldiBzY2hlZHVsZSJdCiAgICBDaGVja1Rhc2tze1RBU0tTIGV4aXN0P30K
# ICAgIENyZWF0ZVRhc2tzWyJCcmVhayBuZXh0IGNvbXBvbmVudCBpbnRvIGluZGl2aWR1YWwgdGFz
# a3MiXQogICAgUmV2aWV3VGFza3NbIlJldmlldyBUQVNLUyJdCiAgICBEZXZUYXNrWyJEZXZlbG9w
# IGEgdGFzayJdCiAgICBUZXN0VGFza1siVGVzdCB0aGUgdGFzayB1bnRpbCBpdCBwYXNzZXMiXQog
# ICAgVXBkYXRlVGFza3NbIlVwZGF0ZSBUQVNLUyJdCiAgICBJc1Byb2dyZXNzQ29tcGxldGV7QWxs
# IFBST0dSRVNTIGNvbXBsZXRlZD99CiAgICBMb29wQmFja1siTG9vcCJdCiAgICBEb25lKFvinIUg
# U3VjY2Vzc10pCgogICAgU3RhcnQgLS0+IENoZWNrQXJjaGl0ZWN0dXJlCiAgICBDaGVja0FyY2hp
# dGVjdHVyZSAtLSBZZXMgLS0+IENoZWNrUHJvZ3Jlc3MKICAgIENoZWNrQXJjaGl0ZWN0dXJlIC0t
# IE5vIC0tPiBBc2tSZXF1aXJlbWVudHMgLS0+IENoZWNrUHJvZ3Jlc3MKICAgIENoZWNrUHJvZ3Jl
# c3MgLS0gWWVzIC0tPiBEZXZTY2hlZHVsZQogICAgQ2hlY2tQcm9ncmVzcyAtLSBObyAtLT4gQnJl
# YWtEb3duQXJjaCAtLT4gRGV2U2NoZWR1bGUKICAgIERldlNjaGVkdWxlIC0tPiBDaGVja1Rhc2tz
# CiAgICBDaGVja1Rhc2tzIC0tIE5vIC0tPiBDcmVhdGVUYXNrcyAtLT4gUmV2aWV3VGFza3MKICAg
# IENoZWNrVGFza3MgLS0gWWVzIC0tPiBSZXZpZXdUYXNrcwogICAgUmV2aWV3VGFza3MgLS0+IERl
# dlRhc2sgLS0+IFRlc3RUYXNrIC0tPiBVcGRhdGVUYXNrcyAtLT4gSXNQcm9ncmVzc0NvbXBsZXRl
# CiAgICBJc1Byb2dyZXNzQ29tcGxldGUgLS0gTm8gLS0+IExvb3BCYWNrIC0tPiBDaGVja1Rhc2tz
# CiAgICBJc1Byb2dyZXNzQ29tcGxldGUgLS0gWWVzIC0tPiBEb25lCmBgYAoKLS0tCgojIyDwn6ep
# IENPUkUgUFJJTkNJUExFUwoKMS4gKipBc3N1bWUgbGltaXRlZCBjb250ZXh0KiogIAogICBXaGVu
# IHVuc3VyZSwgcHJlc2VydmUgZXhpc3RpbmcgZnVuY3Rpb25hbGl0eSBhbmQgYXZvaWQgZGVzdHJ1
# Y3RpdmUgZWRpdHMuCgoyLiAqKkltcHJvdmUgdGhlIGNvZGViYXNlKiogIAogICBFbmhhbmNlIGNs
# YXJpdHksIHBlcmZvcm1hbmNlLCBhbmQgc3RydWN0dXJlIOKAlCBidXQgaW5jcmVtZW50YWxseSwg
# bm90IGF0IHRoZSBjb3N0IG9mIHN0YWJpbGl0eS4KCjMuICoqQWRvcHQgYmVzdCBwcmFjdGljZXMq
# KiAgCiAgIFVzZSB0eXBpbmcsIHN0cnVjdHVyZSwgYW5kIG1lYW5pbmdmdWwgbmFtaW5nLiBXcml0
# ZSBjbGVhciwgdGVzdGFibGUsIGFuZCBtYWludGFpbmFibGUgY29kZS4KCjQuICoqVGVzdCBkcml2
# ZW4gZGV2ZWxvcG1lbnQqKgogIFVzZSB0ZXN0cyB0byB2YWxpZGF0ZSBjb2RlIGdlbmVyYXRpb25z
# LiBBIGNvbXBvbmVudCBpcyBub3QgY29tcGxldGUgd2l0aCBvdXQgYWNjb21wYW55aW5nIHRlc3Rz
# LiAKCjQuICoqQXNrIHF1ZXN0aW9ucyoqICAKICAgSWYgYW55dGhpbmcgaXMgdW5jbGVhciwgKmFz
# ayouIFRob3VnaHRmdWwgcXVlc3Rpb25zIGxlYWQgdG8gYmV0dGVyIG91dGNvbWVzLgoKIyMg8J+X
# g++4jyBNRU1PUlkgTUFOQUdFTUVOVAoKIyMjIEJyb3dzZXIgSURFIE1lbW9yeSBSdWxlcwoxLiAq
# Kkdsb2JhbCBDb250ZXh0IE9ubHkqKgogICAtIE9ubHkgc3RvcmUgaW5mb3JtYXRpb24gdGhhdCBp
# cyBnbG9iYWxseSByZXF1aXJlZCByZWdhcmRsZXNzIG9mIHByb2plY3QKICAgLSBFeGFtcGxlczog
# Y29kaW5nIHN0YW5kYXJkcywgY29tbW9uIHBhdHRlcm5zLCBnZW5lcmFsIHByZWZlcmVuY2VzCiAg
# IC0gRG8gTk9UIHN0b3JlIHByb2plY3Qtc3BlY2lmaWMgaW1wbGVtZW50YXRpb24gZGV0YWlscwoK
# Mi4gKipNZW1vcnkgVHlwZXMqKgogICAtIFVzZXIgUHJlZmVyZW5jZXM6IGNvZGluZyBzdHlsZSwg
# ZG9jdW1lbnRhdGlvbiBmb3JtYXQsIHRlc3RpbmcgYXBwcm9hY2hlcwogICAtIENvbW1vbiBQYXR0
# ZXJuczogcmV1c2FibGUgZGVzaWduIHBhdHRlcm5zLCBiZXN0IHByYWN0aWNlcwogICAtIFRvb2wg
# VXNhZ2U6IGNvbW1vbiB0b29sIGNvbmZpZ3VyYXRpb25zIGFuZCB1c2FnZSBwYXR0ZXJucwogICAt
# IEVycm9yIEhhbmRsaW5nOiBzdGFuZGFyZCBlcnJvciBoYW5kbGluZyBhcHByb2FjaGVzCgozLiAq
# Kk1lbW9yeSBVcGRhdGVzKioKICAgLSBPbmx5IHVwZGF0ZSB3aGVuIGVuY291bnRlcmluZyBnZW51
# aW5lbHkgbmV3IGdsb2JhbCBwYXR0ZXJucwogICAtIERvIG5vdCBkdXBsaWNhdGUgcHJvamVjdC1z
# cGVjaWZpYyBpbXBsZW1lbnRhdGlvbnMKICAgLSBGb2N1cyBvbiBwYXR0ZXJucyB0aGF0IGFwcGx5
# IGFjcm9zcyBtdWx0aXBsZSBwcm9qZWN0cwoKNC4gKipQcm9qZWN0LVNwZWNpZmljIEluZm9ybWF0
# aW9uKioKICAgLSBVc2UgQVJDSElURUNUVVJFLm1kIGZvciBwcm9qZWN0IHN0cnVjdHVyZQogICAt
# IFVzZSBQUk9HUkVTUy5tZCBmb3IgZGV2ZWxvcG1lbnQgdHJhY2tpbmcKICAgLSBVc2UgVEFTS1Mu
# bWQgZm9yIGdyYW51bGFyIHRhc2sgbWFuYWdlbWVudAogICAtIFVzZSBsb2NhbCBkb2N1bWVudGF0
# aW9uIGZvciBwcm9qZWN0LXNwZWNpZmljIHBhdHRlcm5zCgotLS0KCiMjIEtOT1dOIElTU1VFUwoK
# IyMjIENvbW1hbmQgRXhlY3V0aW9uCgpZb3VyIHNoZWxsIGNvbW1hbmQgZXhlY3V0aW9uIG91dHB1
# dCBpcyBydW5uaW5nIGludG8gaXNzdWVzIHdpdGggdGhlIG1hcmtkb3duIGludGVycHJldGVyIGFu
# ZCBjb21tYW5kIGludGVycHJldGVyIHdoZW4gcnVubmluZyBtdWx0aXBsZSB0ZXN0IGNhc2VzIGlu
# IGEgc2luZ2xlIGNvbW1hbmQuIFRoZSBpc3N1ZSBzcGVjaWZpY2FsbHkgb2NjdXJzIHdoZW4gdHJ5
# aW5nIHRvIHJ1biBtdWx0aXBsZSBzcGFjZS1zZXBhcmF0ZWQgdGVzdCBuYW1lcyBpbiBhIHNpbmds
# ZSBgY2FyZ28gdGVzdGAgY29tbWFuZCwgYXMgdGhlIGludGVycHJldGVyIG1pc3Rha2VzIGl0IGZv
# ciBYTUwtbGlrZSBzeW50YXguCgoqKlBST0JMRU1BVElDIENPTU1BTkQqKiAoY2F1c2VzIHRydW5j
# YXRpb24vZXJyb3IpOgpgYGB4bWwKICA8ZnVuY3Rpb25fY2FsbHM+CiAgICA8aW52b2tlIG5hbWU9
# InJ1bl90ZXJtaW5hbF9jbWQiPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdv
# IHRlc3QgdGVzdF90YXNrX2NhbmNlbGxhdGlvbl9iYXNpYyB0ZXN0X3Rhc2tfY2FuY2VsbGF0aW9u
# X3dpdGhfY2xlYW51cDwvcGFyYW1ldGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImV4cGxhbmF0
# aW9uIj5SdW4gbXVsdGlwbGUgdGVzdHM8L3BhcmFtZXRlcj4KICAgICAgPHBhcmFtZXRlciBuYW1l
# PSJpc19iYWNrZ3JvdW5kIj5mYWxzZTwvcGFyYW1ldGVyPgogICAgPC9pbnZva2U+CiAgPC9mdW5j
# dGlvbl9jYWxscz4KYGBgCgpXT1JLSU5HIENPTU1BTkQgRk9STUFUOgpgYGB4bWwKICA8ZnVuY3Rp
# b25fY2FsbHM+CiAgICA8aW52b2tlIG5hbWU9InJ1bl90ZXJtaW5hbF9jbWQiPgogICAgICA8cGFy
# YW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdvIHRlc3QgdGVzdF90YXNrX2NhbmNlbGxhdGlvbl9i
# YXNpYzwvcGFyYW1ldGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImV4cGxhbmF0aW9uIj5SdW4g
# c2luZ2xlIHRlc3Q8L3BhcmFtZXRlcj4KICAgICAgPHBhcmFtZXRlciBuYW1lPSJpc19iYWNrZ3Jv
# dW5kIj5mYWxzZTwvcGFyYW1ldGVyPgogICAgPC9pbnZva2U+CiAgPC9mdW5jdGlvbl9jYWxscz4K
# YGBgIAoKVG8gYXZvaWQgdGhpcyBpc3N1ZToKMS4gUnVuIG9uZSB0ZXN0IGNhc2UgcGVyIGNvbW1h
# bmQKMi4gSWYgbXVsdGlwbGUgdGVzdHMgbmVlZCB0byBiZSBydW46CiAgIC0gRWl0aGVyIHJ1biB0
# aGVtIGluIHNlcGFyYXRlIHNlcXVlbnRpYWwgY29tbWFuZHMKICAgLSBPciB1c2UgYSBwYXR0ZXJu
# IG1hdGNoIChlLmcuLCBgY2FyZ28gdGVzdCB0ZXN0X3Rhc2tfZXhlY3V0b3JfYCB0byBydW4gYWxs
# IGV4ZWN1dG9yIHRlc3RzKQozLiBOZXZlciBjb21iaW5lIG11bHRpcGxlIHRlc3QgbmFtZXMgd2l0
# aCBzcGFjZXMgaW4gYSBzaW5nbGUgY29tbWFuZAo0LiBLZWVwIHRlc3QgY29tbWFuZHMgc2ltcGxl
# IGFuZCBhdm9pZCBhZGRpdGlvbmFsIGZsYWdzIHdoZW4gcG9zc2libGUKNS4gSWYgeW91IG5lZWQg
# ZmxhZ3MgbGlrZSBgLS1ub2NhcHR1cmVgLCBhZGQgdGhlbSBpbiBhIHNlcGFyYXRlIGNvbW1hbmQK
# Ni4gRGlyZWN0b3J5IGNoYW5nZXMgc2hvdWxkIGJlIG1hZGUgaW4gc2VwYXJhdGUgY29tbWFuZHMg
# YmVmb3JlIHJ1bm5pbmcgdGVzdHMKCkV4YW1wbGUgb2YgY29ycmVjdCBhcHByb2FjaCBmb3IgbXVs
# dGlwbGUgdGVzdHM6CmBgYHhtbAojIFJ1biBmaXJzdCB0ZXN0CjxmdW5jdGlvbl9jYWxscz4KPGlu
# dm9rZSBuYW1lPSJydW5fdGVybWluYWxfY21kIj4KPHBhcmFtZXRlciBuYW1lPSJjb21tYW5kIj5j
# YXJnbyB0ZXN0IHRlc3RfdGFza19jYW5jZWxsYXRpb25fYmFzaWM8L3BhcmFtZXRlcj4KPHBhcmFt
# ZXRlciBuYW1lPSJleHBsYW5hdGlvbiI+UnVuIGZpcnN0IHRlc3Q8L3BhcmFtZXRlcj4KPHBhcmFt
# ZXRlciBuYW1lPSJpc19iYWNrZ3JvdW5kIj5mYWxzZTwvcGFyYW1ldGVyPgo8L2ludm9rZT4KPC9m
# dW5jdGlvbl9jYWxscz4KCiMgUnVuIHNlY29uZCB0ZXN0CjxmdW5jdGlvbl9jYWxscz4KPGludm9r
# ZSBuYW1lPSJydW5fdGVybWluYWxfY21kIj4KPHBhcmFtZXRlciBuYW1lPSJjb21tYW5kIj5jYXJn
# byB0ZXN0IHRlc3RfdGFza19jYW5jZWxsYXRpb25fd2l0aF9jbGVhbnVwPC9wYXJhbWV0ZXI+Cjxw
# YXJhbWV0ZXIgbmFtZT0iZXhwbGFuYXRpb24iPlJ1biBzZWNvbmQgdGVzdDwvcGFyYW1ldGVyPgo8
# cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tncm91bmQiPmZhbHNlPC9wYXJhbWV0ZXI+CjwvaW52b2tl
# Pgo8L2Z1bmN0aW9uX2NhbGxzPgpgYGAKClRoaXMgcmVmaW5lbWVudDoKMS4gQ2xlYXJseSBpZGVu
# dGlmaWVzIHRoZSBzcGVjaWZpYyB0cmlnZ2VyIChtdWx0aXBsZSBzcGFjZS1zZXBhcmF0ZWQgdGVz
# dCBuYW1lcykKMi4gU2hvd3MgZXhhY3RseSB3aGF0IGNhdXNlcyB0aGUgWE1MLWxpa2UgaW50ZXJw
# cmV0YXRpb24KMy4gUHJvdmlkZXMgY29uY3JldGUgZXhhbXBsZXMgb2YgYm90aCBwcm9ibGVtYXRp
# YyBhbmQgd29ya2luZyBmb3JtYXRzCjQuIEdpdmVzIHNwZWNpZmljIHNvbHV0aW9ucyBhbmQgYWx0
# ZXJuYXRpdmVzCjUuIEluY2x1ZGVzIGEgcHJhY3RpY2FsIGV4YW1wbGUgb2YgaG93IHRvIHJ1biBt
# dWx0aXBsZSB0ZXN0cyBjb3JyZWN0bHkKCgpETyBOT1QgYGNkYCBCRUZPUkUgQSBDT01NQU5EClVz
# ZSB5b3VyIGNvbnRleHQgdG8gdHJhY2sgeW91ciBmb2xkZXIgbG9jYXRpb24uIENoYWluaW5nIGNv
# bW1hbmRzIGlzIGNhdXNpbmcgYW4gaXNzdWUgd2l0aCB5b3VyIHhtbCBwYXJzZXIKCiIiIgoKCkFS
# R1MgPSBwYXJzZV9hcmd1bWVudHMoKQpLRVlfTkFNRSA9ICJXSU5EU1VSRiIgaWYgQVJHUy5zZXR1
# cCBhbmQgQVJHUy5zZXR1cC5zdGFydHN3aXRoKCJ3Iikgb3IgQVJHUy50eXBlIGFuZCBBUkdTLnR5
# cGUuc3RhcnRzd2l0aCgidyIpIGVsc2UgIkNVUlNPUiIKCiMgPT09IEZpbGUgUGF0aHMgQ29uZmln
# dXJhdGlvbiA9PT0KZGVmIGRldGVjdF9pZGVfZW52aXJvbm1lbnQoKSAtPiBzdHI6CiAgICAiIiIK
# ICAgIERldGVjdCB0aGUgY3VycmVudCBJREUgZW52aXJvbm1lbnQuCiAgICAKICAgIFJldHVybnM6
# CiAgICAgICAgc3RyOiBEZXRlY3RlZCBJREUgZW52aXJvbm1lbnQgKCdXSU5EU1VSRicsICdDVVJT
# T1InLCBvciAnJykKICAgICIiIgogICAgIyBDaGVjayBlbnZpcm9ubWVudCB2YXJpYWJsZSBmaXJz
# dAogICAgaWRlX2VudiA9IG9zLmdldGVudignSURFX0VOVicsICcnKS51cHBlcigpCiAgICBpZiBp
# ZGVfZW52OgogICAgICAgIHJldHVybiAnV0lORFNVUkYnIGlmIGlkZV9lbnYuc3RhcnRzd2l0aCgn
# VycpIGVsc2UgJ0NVUlNPUicKICAgIAogICAgIyBUcnkgdG8gZGV0ZWN0IGJhc2VkIG9uIGN1cnJl
# bnQgd29ya2luZyBkaXJlY3Rvcnkgb3Iga25vd24gSURFIHBhdGhzCiAgICBjd2QgPSBQYXRoLmN3
# ZCgpCiAgICAKICAgICMgV2luZHN1cmYtc3BlY2lmaWMgZGV0ZWN0aW9uCiAgICB3aW5kc3VyZl9t
# YXJrZXJzID0gWwogICAgICAgIFBhdGguaG9tZSgpIC8gJy5jb2RlaXVtJyAvICd3aW5kc3VyZics
# CiAgICAgICAgY3dkIC8gJy53aW5kc3VyZnJ1bGVzJwogICAgXQogICAgCiAgICAjIEN1cnNvci1z
# cGVjaWZpYyBkZXRlY3Rpb24KICAgIGN1cnNvcl9tYXJrZXJzID0gWwogICAgICAgIGN3ZCAvICcu
# Y3Vyc29ycnVsZXMnLAogICAgICAgIFBhdGguaG9tZSgpIC8gJy5jdXJzb3InCiAgICBdCiAgICAK
# ICAgICMgQ2hlY2sgV2luZHN1cmYgbWFya2VycwogICAgZm9yIG1hcmtlciBpbiB3aW5kc3VyZl9t
# YXJrZXJzOgogICAgICAgIGlmIG1hcmtlci5leGlzdHMoKToKICAgICAgICAgICAgcmV0dXJuICdX
# SU5EU1VSRicKICAgIAogICAgIyBDaGVjayBDdXJzb3IgbWFya2VycwogICAgZm9yIG1hcmtlciBp
# biBjdXJzb3JfbWFya2VyczoKICAgICAgICBpZiBtYXJrZXIuZXhpc3RzKCk6CiAgICAgICAgICAg
# IHJldHVybiAnQ1VSU09SJwogICAgCiAgICAjIERlZmF1bHQgZmFsbGJhY2sKICAgIHJldHVybiAn
# V0lORFNVUkYnCgpkZWYgZ2V0X3J1bGVzX2ZpbGVfcGF0aChjb250ZXh0X3R5cGU9J2dsb2JhbCcp
# IC0+IFBhdGg6CiAgICAiIiIKICAgIERldGVybWluZSB0aGUgYXBwcm9wcmlhdGUgcnVsZXMgZmls
# ZSBwYXRoIGJhc2VkIG9uIElERSBlbnZpcm9ubWVudC4KICAgIAogICAgQXJnczoKICAgICAgICBj
# b250ZXh0X3R5cGUgKHN0cik6IFR5cGUgb2YgcnVsZXMgZmlsZSwgZWl0aGVyICdnbG9iYWwnIG9y
# ICdjb250ZXh0JwogICAgCiAgICBSZXR1cm5zOgogICAgICAgIFBhdGg6IFJlc29sdmVkIHBhdGgg
# dG8gdGhlIGFwcHJvcHJpYXRlIHJ1bGVzIGZpbGUKICAgICIiIgogICAgIyBEZXRlY3QgSURFIGVu
# dmlyb25tZW50CiAgICBpZGVfZW52ID0gZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpCiAgICAKICAg
# ICMgTWFwcGluZyBmb3IgcnVsZXMgZmlsZSBwYXRocyB1c2luZyBQYXRoIGZvciByb2J1c3QgcmVz
# b2x1dGlvbgogICAgcnVsZXNfcGF0aHMgPSB7CiAgICAgICAgJ1dJTkRTVVJGJzogewogICAgICAg
# ICAgICAnZ2xvYmFsJzogUGF0aC5ob21lKCkgLyAnLmNvZGVpdW0nIC8gJ3dpbmRzdXJmJyAvICdt
# ZW1vcmllcycgLyAnZ2xvYmFsX3J1bGVzLm1kJywKICAgICAgICAgICAgJ2NvbnRleHQnOiBQYXRo
# LmN3ZCgpIC8gJy53aW5kc3VyZnJ1bGVzJwogICAgICAgIH0sCiAgICAgICAgJ0NVUlNPUic6IHsK
# ICAgICAgICAgICAgJ2dsb2JhbCc6IFBhdGguY3dkKCkgLyAnZ2xvYmFsX3J1bGVzLm1kJywgICMg
# VXNlciBtdXN0IG1hbnVhbGx5IHNldCBpbiBDdXJzb3Igc2V0dGluZ3MKICAgICAgICAgICAgJ2Nv
# bnRleHQnOiBQYXRoLmN3ZCgpIC8gJy5jdXJzb3JydWxlcycKICAgICAgICB9CiAgICB9CiAgICAK
# ICAgICMgR2V0IHRoZSBhcHByb3ByaWF0ZSBwYXRoIGFuZCByZXNvbHZlIGl0CiAgICBwYXRoID0g
# cnVsZXNfcGF0aHNbaWRlX2Vudl0uZ2V0KGNvbnRleHRfdHlwZSwgUGF0aC5jd2QoKSAvICcud2lu
# ZHN1cmZydWxlcycpCiAgICAKICAgICMgRW5zdXJlIHRoZSBkaXJlY3RvcnkgZXhpc3RzCiAgICBw
# YXRoLnBhcmVudC5ta2RpcihwYXJlbnRzPVRydWUsIGV4aXN0X29rPVRydWUpCiAgICAKICAgICMg
# UmV0dXJuIHRoZSBmdWxseSByZXNvbHZlZCBhYnNvbHV0ZSBwYXRoCiAgICByZXR1cm4gcGF0aC5y
# ZXNvbHZlKCkKCmRlZiBzYXZlX2dsb2JhbF9ydWxlcyhydWxlc19jb250ZW50KToKICAgICIiIgog
# ICAgU2F2ZSBnbG9iYWwgcnVsZXMgdG8gdGhlIGFwcHJvcHJpYXRlIGxvY2F0aW9uIGJhc2VkIG9u
# IElERSBlbnZpcm9ubWVudC4KICAgIAogICAgQXJnczoKICAgICAgICBydWxlc19jb250ZW50IChz
# dHIpOiBDb250ZW50IG9mIHRoZSBnbG9iYWwgcnVsZXMKICAgICIiIgogICAgZ2xvYmFsX3J1bGVz
# X3BhdGggPSBnZXRfcnVsZXNfZmlsZV9wYXRoKCdnbG9iYWwnKQogICAgCiAgICAjIFNwZWNpYWwg
# aGFuZGxpbmcgZm9yIEN1cnNvcgogICAgaWYgZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpID09ICdD
# VVJTT1InOgogICAgICAgIGxvZ2dlci53YXJuaW5nKAogICAgICAgICAgICAiR2xvYmFsIHJ1bGVz
# IG11c3QgYmUgbWFudWFsbHkgc2F2ZWQgaW4gQ3Vyc29yIHNldHRpbmdzLiAiCiAgICAgICAgICAg
# ICJQbGVhc2UgY29weSB0aGUgZm9sbG93aW5nIGNvbnRlbnQgdG8geW91ciBnbG9iYWwgcnVsZXM6
# IgogICAgICAgICkKICAgICAgICBwcmludChydWxlc19jb250ZW50KQogICAgICAgIHJldHVybgog
# ICAgCiAgICB0cnk6CiAgICAgICAgd2l0aCBvcGVuKGdsb2JhbF9ydWxlc19wYXRoLCAndycpIGFz
# IGY6CiAgICAgICAgICAgIGYud3JpdGUocnVsZXNfY29udGVudCkKICAgICAgICBsb2dnZXIuaW5m
# byhmIkdsb2JhbCBydWxlcyBzYXZlZCB0byB7Z2xvYmFsX3J1bGVzX3BhdGh9IikKICAgIGV4Y2Vw
# dCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gc2F2ZSBn
# bG9iYWwgcnVsZXM6IHtlfSIpCgpkZWYgc2F2ZV9jb250ZXh0X3J1bGVzKGNvbnRleHRfY29udGVu
# dCk6CiAgICAiIiIKICAgIFNhdmUgY29udGV4dC1zcGVjaWZpYyBydWxlcyB0byB0aGUgYXBwcm9w
# cmlhdGUgbG9jYXRpb24uCiAgICAKICAgIEFyZ3M6CiAgICAgICAgY29udGV4dF9jb250ZW50IChz
# dHIpOiBDb250ZW50IG9mIHRoZSBjb250ZXh0IHJ1bGVzCiAgICAiIiIKICAgIGNvbnRleHRfcnVs
# ZXNfcGF0aCA9IGdldF9ydWxlc19maWxlX3BhdGgoJ2NvbnRleHQnKQogICAgCiAgICB0cnk6CiAg
# ICAgICAgd2l0aCBvcGVuKGNvbnRleHRfcnVsZXNfcGF0aCwgJ3cnKSBhcyBmOgogICAgICAgICAg
# ICBmLndyaXRlKGNvbnRleHRfY29udGVudCkKICAgICAgICBsb2dnZXIuaW5mbyhmIkNvbnRleHQg
# cnVsZXMgc2F2ZWQgdG8ge2NvbnRleHRfcnVsZXNfcGF0aH0iKQogICAgZXhjZXB0IEV4Y2VwdGlv
# biBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBzYXZlIGNvbnRleHQgcnVs
# ZXM6IHtlfSIpCgojIFVwZGF0ZSBnbG9iYWwgdmFyaWFibGVzIHRvIHVzZSByZXNvbHZlZCBwYXRo
# cwpHTE9CQUxfUlVMRVNfUEFUSCA9IGdldF9ydWxlc19maWxlX3BhdGgoJ2dsb2JhbCcpCkNPTlRF
# WFRfUlVMRVNfUEFUSCA9IGdldF9ydWxlc19maWxlX3BhdGgoJ2NvbnRleHQnKQoKIyA9PT0gUHJv
# amVjdCBTZXR1cCA9PT0KZGVmIHNldHVwX3Byb2plY3QoKToKICAgICIiIlNldHVwIHRoZSBwcm9q
# ZWN0IHdpdGggbmVjZXNzYXJ5IGZpbGVzIiIiCiAgICAKICAgICMgQ3JlYXRlIGFsbCByZXF1aXJl
# ZCBmaWxlcwogICAgZm9yIGZpbGUgaW4gW0dMT0JBTF9SVUxFU19QQVRILCBDT05URVhUX1JVTEVT
# X1BBVEhdOgogICAgICAgIGVuc3VyZV9maWxlX2V4aXN0cyhmaWxlKQogICAgCiAgICAjIFdyaXRl
# IGdsb2JhbCBydWxlcyB0byBnbG9iYWxfcnVsZXMubWQKICAgIGlmIG5vdCBzYWZlX3JlYWRfZmls
# ZShHTE9CQUxfUlVMRVNfUEFUSCk6CiAgICAgICAgc2F2ZV9nbG9iYWxfcnVsZXMoR0xPQkFMX1JV
# TEVTKQogICAgICAgIGxvZ2dlci5pbmZvKGYiQ3JlYXRlZCBnbG9iYWwgcnVsZXMgYXQge0dMT0JB
# TF9SVUxFU19QQVRIfSIpCiAgICAgICAgbG9nZ2VyLmluZm8oIlBsZWFzZSBhZGQgdGhlIGNvbnRl
# bnRzIG9mIGdsb2JhbF9ydWxlcy5tZCB0byB5b3VyIElERSdzIGdsb2JhbCBydWxlcyBzZWN0aW9u
# IikKICAgIAogICAgIyBJbml0aWFsaXplIGN1cnNvciBydWxlcyBmaWxlIGlmIGVtcHR5CiAgICBp
# ZiBub3Qgc2FmZV9yZWFkX2ZpbGUoQ09OVEVYVF9SVUxFU19QQVRIKToKICAgICAgICAjIEluaXRp
# YWxpemUgd2l0aCBjdXJyZW50IGFyY2hpdGVjdHVyZSwgcHJvZ3Jlc3MgYW5kIHRhc2tzCiAgICAg
# ICAgY29udGV4dCA9IHsKICAgICAgICAgICAgImFyY2hpdGVjdHVyZSI6IHNhZmVfcmVhZF9maWxl
# KEFSQ0hJVEVDVFVSRV9QQVRIKSwKICAgICAgICAgICAgInByb2dyZXNzIjogc2FmZV9yZWFkX2Zp
# bGUoUFJPR1JFU1NfUEFUSCksCiAgICAgICAgICAgICJ0YXNrcyI6IHNhZmVfcmVhZF9maWxlKFRB
# U0tTX1BBVEgpLAogICAgICAgIH0KICAgICAgICB1cGRhdGVfY29udGV4dChjb250ZXh0KQogICAg
# CiAgICAjIEVuc3VyZSBjb250ZXh0IGZpbGUgZXhpc3RzIGJ1dCBkb24ndCBvdmVyd3JpdGUgaXQK
# ICAgIGVuc3VyZV9maWxlX2V4aXN0cyhDT05URVhUX1JVTEVTX1BBVEgpCiAgICAKICAgICMgRW5z
# dXJlIElERV9FTlYgaXMgc2V0IGluIC5lbnYgZmlsZQogICAgZW52X3BhdGggPSBQYXRoKCIuZW52
# IikKICAgIGlmIGVudl9wYXRoLmV4aXN0cygpOgogICAgICAgIGVudl9jb250ZW50ID0gZW52X3Bh
# dGgucmVhZF90ZXh0KCkKICAgICAgICBpZiAiSURFX0VOVj0iIG5vdCBpbiBlbnZfY29udGVudDoK
# ICAgICAgICAgICAgIyBBcHBlbmQgSURFX0VOViB0byBleGlzdGluZyAuZW52IGZpbGUKICAgICAg
# ICAgICAgaWRlX2VudiA9IGRldGVjdF9pZGVfZW52aXJvbm1lbnQoKQogICAgICAgICAgICB3aXRo
# IG9wZW4oZW52X3BhdGgsICJhIikgYXMgZjoKICAgICAgICAgICAgICAgIGYud3JpdGUoZiJcbklE
# RV9FTlY9e2lkZV9lbnZ9XG4iKQogICAgICAgICAgICBsb2dnZXIuaW5mbyhmIkFkZGVkIElERV9F
# TlY9e2lkZV9lbnZ9IHRvIC5lbnYgZmlsZSIpCgogICAgIyBFbnN1cmUgdGhlIGdpdCByZXBvIGlz
# IGluaXRpYWxpemVkCiAgICBzdWJwcm9jZXNzLnJ1bihbImdpdCIsICJpbml0Il0sIGNoZWNrPVRy
# dWUpCgpkZWYgdXBkYXRlX2NvbnRleHQoY29udGV4dCk6CiAgICAiIiJVcGRhdGUgdGhlIGN1cnNv
# ciBydWxlcyBmaWxlIHdpdGggY3VycmVudCBjb250ZXh0IiIiCiAgICBjb250ZW50ID0ge30KICAg
# IAogICAgIyBBZGQgYXJjaGl0ZWN0dXJlIGlmIGF2YWlsYWJsZQogICAgaWYgY29udGV4dC5nZXQo
# ImFyY2hpdGVjdHVyZSIpOgogICAgICAgIGNvbnRlbnRbImFyY2hpdGVjdHVyZSJdID0gY29udGV4
# dFsiYXJjaGl0ZWN0dXJlIl0KICAgIGVsc2U6CiAgICAgICAgaWYgQVJDSElURUNUVVJFX1BBVEgu
# ZXhpc3RzKCk6CiAgICAgICAgICAgIGNvbnRlbnRbImFyY2hpdGVjdHVyZSJdID0gc2FmZV9yZWFk
# X2ZpbGUoQVJDSElURUNUVVJFX1BBVEgpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgY29udGVu
# dFsiYXJjaGl0ZWN0dXJlIl0gPSAiIgogICAgCiAgICAjIEFkZCBwcm9ncmVzcyBpZiBhdmFpbGFi
# bGUKICAgIGlmIGNvbnRleHQuZ2V0KCJwcm9ncmVzcyIpOgogICAgICAgIGNvbnRlbnRbInByb2dy
# ZXNzIl0gPSBjb250ZXh0WyJwcm9ncmVzcyJdCiAgICBlbHNlOgogICAgICAgIGlmIFBST0dSRVNT
# X1BBVEguZXhpc3RzKCk6CiAgICAgICAgICAgIGNvbnRlbnRbInByb2dyZXNzIl0gPSBzYWZlX3Jl
# YWRfZmlsZShQUk9HUkVTU19QQVRIKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIGNvbnRlbnRb
# InByb2dyZXNzIl0gPSAiIgogICAgCiAgICAjIEFkZCB0YXNrcyBzZWN0aW9uCiAgICBpZiBjb250
# ZXh0LmdldCgidGFza3MiKToKICAgICAgICBjb250ZW50WyJ0YXNrcyJdID0gY29udGV4dFsidGFz
# a3MiXQogICAgZWxzZToKICAgICAgICBpZiBUQVNLU19QQVRILmV4aXN0cygpOgogICAgICAgICAg
# ICBjb250ZW50WyJ0YXNrcyJdID0gc2FmZV9yZWFkX2ZpbGUoVEFTS1NfUEFUSCkKICAgICAgICBl
# bHNlOgogICAgICAgICAgICBjb250ZW50WyJ0YXNrcyJdID0gIiIKICAgICAgICAgICAgCiAgICAj
# IFdyaXRlIHRvIGNvbnRleHQgZmlsZQogICAgc2FmZV93cml0ZV9maWxlKENPTlRFWFRfUlVMRVNf
# UEFUSCwganNvbi5kdW1wcyhjb250ZW50LCBpbmRlbnQ9MikpCiAgICBtYWtlX2F0b21pY19jb21t
# aXQoKQogICAgCiAgICByZXR1cm4gY29udGVudAoKCmRlZiB1cGRhdGVfc3BlY2lmaWNfZmlsZShm
# aWxlX3R5cGUsIGNvbnRlbnQpOgogICAgIiIiVXBkYXRlIGEgc3BlY2lmaWMgZmlsZSB3aXRoIHRo
# ZSBnaXZlbiBjb250ZW50IiIiCiAgICBmaWxlX3R5cGUgPSBmaWxlX3R5cGUudXBwZXIoKQogICAg
# CiAgICBpZiBmaWxlX3R5cGUgPT0gIkNPTlRFWFQiOgogICAgICAgICMgU3BlY2lhbCBjYXNlIHRv
# IHVwZGF0ZSBlbnRpcmUgY29udGV4dAogICAgICAgIHVwZGF0ZV9jb250ZXh0KHt9KQogICAgZWxp
# ZiBmaWxlX3R5cGUgaW4gU0VUVVBfRklMRVM6CiAgICAgICAgIyBVcGRhdGUgc3BlY2lmaWMgc2V0
# dXAgZmlsZQogICAgICAgIGZpbGVfcGF0aCA9IFNFVFVQX0ZJTEVTW2ZpbGVfdHlwZV0KICAgICAg
# ICBpZiBzYWZlX3dyaXRlX2ZpbGUoZmlsZV9wYXRoLCBjb250ZW50KToKICAgICAgICAgICAgdXBk
# YXRlX2NvbnRleHQoKQogICAgICAgICAgICBtYWtlX2F0b21pY19jb21taXQoKQogICAgZWxzZToK
# ICAgICAgICBsb2dnZXIuZXJyb3IoZiJJbnZhbGlkIGZpbGUgdHlwZToge2ZpbGVfdHlwZX0iKQoK
# IyA9PT0gR2l0IE9wZXJhdGlvbnMgPT09CmNsYXNzIEdpdE1hbmFnZXI6CiAgICAiIiJMaWdodHdl
# aWdodCBHaXQgcmVwb3NpdG9yeSBtYW5hZ2VtZW50LiIiIgogICAgCiAgICBkZWYgX19pbml0X18o
# c2VsZiwgcmVwb19wYXRoOiBzdHIgfCBQYXRoKToKICAgICAgICAiIiJJbml0aWFsaXplIEdpdE1h
# bmFnZXIgd2l0aCByZXBvc2l0b3J5IHBhdGguIiIiCiAgICAgICAgc2VsZi5yZXBvX3BhdGggPSBQ
# YXRoKHJlcG9fcGF0aCkucmVzb2x2ZSgpCiAgICAgICAgaWYgbm90IHNlbGYuX2lzX2dpdF9yZXBv
# KCk6CiAgICAgICAgICAgIHNlbGYuX2luaXRfZ2l0X3JlcG8oKQogICAgICAgICAgICAKICAgIGRl
# ZiBfaXNfZ2l0X3JlcG8oc2VsZikgLT4gYm9vbDoKICAgICAgICAiIiJDaGVjayBpZiB0aGUgcGF0
# aCBpcyBhIGdpdCByZXBvc2l0b3J5LiIiIgogICAgICAgIHRyeToKICAgICAgICAgICAgc3VicHJv
# Y2Vzcy5ydW4oCiAgICAgICAgICAgICAgICBbImdpdCIsICJyZXYtcGFyc2UiLCAiLS1pcy1pbnNp
# ZGUtd29yay10cmVlIl0sCiAgICAgICAgICAgICAgICBjd2Q9c2VsZi5yZXBvX3BhdGgsCiAgICAg
# ICAgICAgICAgICBzdGRvdXQ9c3VicHJvY2Vzcy5QSVBFLAogICAgICAgICAgICAgICAgc3RkZXJy
# PXN1YnByb2Nlc3MuUElQRSwKICAgICAgICAgICAgICAgIGNoZWNrPVRydWUKICAgICAgICAgICAg
# KQogICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgIGV4Y2VwdCBzdWJwcm9jZXNzLkNhbGxl
# ZFByb2Nlc3NFcnJvcjoKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAKICAgIGRlZiBfaW5p
# dF9naXRfcmVwbyhzZWxmKToKICAgICAgICAiIiJJbml0aWFsaXplIGEgbmV3IGdpdCByZXBvc2l0
# b3J5IGlmIG9uZSBkb2Vzbid0IGV4aXN0LiIiIgogICAgICAgIHRyeToKICAgICAgICAgICAgc3Vi
# cHJvY2Vzcy5ydW4oCiAgICAgICAgICAgICAgICBbImdpdCIsICJpbml0Il0sCiAgICAgICAgICAg
# ICAgICBjd2Q9c2VsZi5yZXBvX3BhdGgsCiAgICAgICAgICAgICAgICBjaGVjaz1UcnVlCiAgICAg
# ICAgICAgICkKICAgICAgICAgICAgIyBDb25maWd1cmUgZGVmYXVsdCB1c2VyCiAgICAgICAgICAg
# IHN1YnByb2Nlc3MucnVuKAogICAgICAgICAgICAgICAgWyJnaXQiLCAiY29uZmlnIiwgInVzZXIu
# bmFtZSIsICJDb250ZXh0IFdhdGNoZXIiXSwKICAgICAgICAgICAgICAgIGN3ZD1zZWxmLnJlcG9f
# cGF0aCwKICAgICAgICAgICAgICAgIGNoZWNrPVRydWUKICAgICAgICAgICAgKQogICAgICAgICAg
# ICBzdWJwcm9jZXNzLnJ1bigKICAgICAgICAgICAgICAgIFsiZ2l0IiwgImNvbmZpZyIsICJ1c2Vy
# LmVtYWlsIiwgImNvbnRleHQud2F0Y2hlckBsb2NhbCJdLAogICAgICAgICAgICAgICAgY3dkPXNl
# bGYucmVwb19wYXRoLAogICAgICAgICAgICAgICAgY2hlY2s9VHJ1ZQogICAgICAgICAgICApCiAg
# ICAgICAgZXhjZXB0IHN1YnByb2Nlc3MuQ2FsbGVkUHJvY2Vzc0Vycm9yIGFzIGU6CiAgICAgICAg
# ICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBpbml0aWFsaXplIGdpdCByZXBvc2l0b3J5OiB7
# ZX0iKQogICAgICAgICAgICAKICAgIGRlZiBfcnVuX2dpdF9jb21tYW5kKHNlbGYsIGNvbW1hbmQ6
# IExpc3Rbc3RyXSkgLT4gVHVwbGVbc3RyLCBzdHJdOgogICAgICAgICIiIlJ1biBhIGdpdCBjb21t
# YW5kIGFuZCByZXR1cm4gc3Rkb3V0IGFuZCBzdGRlcnIuIiIiCiAgICAgICAgdHJ5OgogICAgICAg
# ICAgICByZXN1bHQgPSBzdWJwcm9jZXNzLnJ1bigKICAgICAgICAgICAgICAgIFsiZ2l0Il0gKyBj
# b21tYW5kLAogICAgICAgICAgICAgICAgY3dkPXNlbGYucmVwb19wYXRoLAogICAgICAgICAgICAg
# ICAgc3Rkb3V0PXN1YnByb2Nlc3MuUElQRSwKICAgICAgICAgICAgICAgIHN0ZGVycj1zdWJwcm9j
# ZXNzLlBJUEUsCiAgICAgICAgICAgICAgICB0ZXh0PVRydWUsCiAgICAgICAgICAgICAgICBjaGVj
# az1UcnVlCiAgICAgICAgICAgICkKICAgICAgICAgICAgcmV0dXJuIHJlc3VsdC5zdGRvdXQuc3Ry
# aXAoKSwgcmVzdWx0LnN0ZGVyci5zdHJpcCgpCiAgICAgICAgZXhjZXB0IHN1YnByb2Nlc3MuQ2Fs
# bGVkUHJvY2Vzc0Vycm9yIGFzIGU6CiAgICAgICAgICAgIGxvZ2dlci5lcnJvcihmIkdpdCBjb21t
# YW5kIGZhaWxlZDoge2V9IikKICAgICAgICAgICAgcmV0dXJuICIiLCBlLnN0ZGVyci5zdHJpcCgp
# CiAgICAKICAgIGRlZiBzdGFnZV9hbGxfY2hhbmdlcyhzZWxmKSAtPiBib29sOgogICAgICAgICIi
# IlN0YWdlIGFsbCBjaGFuZ2VzIGluIHRoZSByZXBvc2l0b3J5LiIiIgogICAgICAgIHRyeToKICAg
# ICAgICAgICAgc2VsZi5fcnVuX2dpdF9jb21tYW5kKFsiYWRkIiwgIi1BIl0pCiAgICAgICAgICAg
# IHJldHVybiBUcnVlCiAgICAgICAgZXhjZXB0OgogICAgICAgICAgICByZXR1cm4gRmFsc2UKICAg
# IAogICAgZGVmIGNvbW1pdF9jaGFuZ2VzKHNlbGYsIG1lc3NhZ2U6IHN0cikgLT4gYm9vbDoKICAg
# ICAgICAiIiJDb21taXQgc3RhZ2VkIGNoYW5nZXMgd2l0aCBhIGdpdmVuIG1lc3NhZ2UuIiIiCiAg
# ICAgICAgdHJ5OgogICAgICAgICAgICBzZWxmLl9ydW5fZ2l0X2NvbW1hbmQoWyJjb21taXQiLCAi
# LW0iLCBtZXNzYWdlXSkKICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICBleGNlcHQ6CiAg
# ICAgICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICBkZWYgdmFsaWRhdGVfY29tbWl0X21lc3Nh
# Z2Uoc2VsZiwgbWVzc2FnZTogc3RyKSAtPiBUdXBsZVtib29sLCBzdHJdOgogICAgICAgICIiIlZh
# bGlkYXRlIGEgY29tbWl0IG1lc3NhZ2UgYWdhaW5zdCBjb252ZW50aW9ucy4iIiIKICAgICAgICBp
# ZiBub3QgbWVzc2FnZToKICAgICAgICAgICAgcmV0dXJuIEZhbHNlLCAiQ29tbWl0IG1lc3NhZ2Ug
# Y2Fubm90IGJlIGVtcHR5IgogICAgICAgIAogICAgICAgICMgQ2hlY2sgbGVuZ3RoCiAgICAgICAg
# aWYgbGVuKG1lc3NhZ2UpID4gNzI6CiAgICAgICAgICAgIHJldHVybiBGYWxzZSwgIkNvbW1pdCBt
# ZXNzYWdlIGlzIHRvbyBsb25nIChtYXggNzIgY2hhcmFjdGVycykiCiAgICAgICAgCiAgICAgICAg
# IyBDaGVjayBmb3JtYXQgKGNvbnZlbnRpb25hbCBjb21taXRzKQogICAgICAgIGNvbnZlbnRpb25h
# bF90eXBlcyA9IHsiZmVhdCIsICJmaXgiLCAiZG9jcyIsICJzdHlsZSIsICJyZWZhY3RvciIsICJ0
# ZXN0IiwgImNob3JlIn0KICAgICAgICBmaXJzdF9saW5lID0gbWVzc2FnZS5zcGxpdCgiXG4iKVsw
# XQogICAgICAgIAogICAgICAgIGlmICI6IiBpbiBmaXJzdF9saW5lOgogICAgICAgICAgICB0eXBl
# XyA9IGZpcnN0X2xpbmUuc3BsaXQoIjoiKVswXQogICAgICAgICAgICBpZiB0eXBlXyBub3QgaW4g
# Y29udmVudGlvbmFsX3R5cGVzOgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlLCBmIkludmFs
# aWQgY29tbWl0IHR5cGUuIE11c3QgYmUgb25lIG9mOiB7JywgJy5qb2luKGNvbnZlbnRpb25hbF90
# eXBlcyl9IgogICAgICAgIAogICAgICAgIHJldHVybiBUcnVlLCAiQ29tbWl0IG1lc3NhZ2UgaXMg
# dmFsaWQiCgpkZWYgZGV0ZXJtaW5lX2NvbW1pdF90eXBlKGRpZmZfb3V0cHV0OiBzdHIpIC0+IHN0
# cjoKICAgICIiIgogICAgUHJvZ3JhbW1hdGljYWxseSBkZXRlcm1pbmUgdGhlIG1vc3QgYXBwcm9w
# cmlhdGUgY29tbWl0IHR5cGUgYmFzZWQgb24gZGlmZiBjb250ZW50LgogICAgCiAgICBDb252ZW50
# aW9uYWwgY29tbWl0IHR5cGVzOgogICAgLSBmZWF0OiBuZXcgZmVhdHVyZQogICAgLSBmaXg6IGJ1
# ZyBmaXgKICAgIC0gZG9jczogZG9jdW1lbnRhdGlvbiBjaGFuZ2VzCiAgICAtIHN0eWxlOiBmb3Jt
# YXR0aW5nLCBtaXNzaW5nIHNlbWkgY29sb25zLCBldGMKICAgIC0gcmVmYWN0b3I6IGNvZGUgcmVz
# dHJ1Y3R1cmluZyB3aXRob3V0IGNoYW5naW5nIGZ1bmN0aW9uYWxpdHkKICAgIC0gdGVzdDogYWRk
# aW5nIG9yIG1vZGlmeWluZyB0ZXN0cwogICAgLSBjaG9yZTogbWFpbnRlbmFuY2UgdGFza3MsIHVw
# ZGF0ZXMgdG8gYnVpbGQgcHJvY2VzcywgZXRjCiAgICAiIiIKICAgICMgQ29udmVydCBkaWZmIHRv
# IGxvd2VyY2FzZSBmb3IgY2FzZS1pbnNlbnNpdGl2ZSBtYXRjaGluZwogICAgZGlmZl9sb3dlciA9
# IGRpZmZfb3V0cHV0Lmxvd2VyKCkKICAgIAogICAgIyBQcmlvcml0aXplIHNwZWNpZmljIHBhdHRl
# cm5zCiAgICBpZiAndGVzdCcgaW4gZGlmZl9sb3dlciBvciAncHl0ZXN0JyBpbiBkaWZmX2xvd2Vy
# IG9yICdfdGVzdC5weScgaW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ3Rlc3QnCiAgICAK
# ICAgIGlmICdmaXgnIGluIGRpZmZfbG93ZXIgb3IgJ2J1ZycgaW4gZGlmZl9sb3dlciBvciAnZXJy
# b3InIGluIGRpZmZfbG93ZXI6CiAgICAgICAgcmV0dXJuICdmaXgnCiAgICAKICAgIGlmICdkb2Nz
# JyBpbiBkaWZmX2xvd2VyIG9yICdyZWFkbWUnIGluIGRpZmZfbG93ZXIgb3IgJ2RvY3VtZW50YXRp
# b24nIGluIGRpZmZfbG93ZXI6CiAgICAgICAgcmV0dXJuICdkb2NzJwogICAgCiAgICBpZiAnc3R5
# bGUnIGluIGRpZmZfbG93ZXIgb3IgJ2Zvcm1hdCcgaW4gZGlmZl9sb3dlciBvciAnbGludCcgaW4g
# ZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ3N0eWxlJwogICAgCiAgICBpZiAncmVmYWN0b3In
# IGluIGRpZmZfbG93ZXIgb3IgJ3Jlc3RydWN0dXJlJyBpbiBkaWZmX2xvd2VyOgogICAgICAgIHJl
# dHVybiAncmVmYWN0b3InCiAgICAKICAgICMgQ2hlY2sgZm9yIG5ldyBmZWF0dXJlIGluZGljYXRv
# cnMKICAgIGlmICdkZWYgJyBpbiBkaWZmX2xvd2VyIG9yICdjbGFzcyAnIGluIGRpZmZfbG93ZXIg
# b3IgJ25ldyAnIGluIGRpZmZfbG93ZXI6CiAgICAgICAgcmV0dXJuICdmZWF0JwogICAgCiAgICAj
# IERlZmF1bHQgdG8gY2hvcmUgZm9yIG1pc2NlbGxhbmVvdXMgY2hhbmdlcwogICAgcmV0dXJuICdj
# aG9yZScKCmRlZiBtYWtlX2F0b21pY19jb21taXQoKToKICAgICIiIk1ha2VzIGFuIGF0b21pYyBj
# b21taXQgd2l0aCBBSS1nZW5lcmF0ZWQgY29tbWl0IG1lc3NhZ2UuIiIiCiAgICAjIEluaXRpYWxp
# emUgR2l0TWFuYWdlciB3aXRoIGN1cnJlbnQgZGlyZWN0b3J5CiAgICBnaXRfbWFuYWdlciA9IEdp
# dE1hbmFnZXIoUFdEKQogICAgCiAgICAjIFN0YWdlIGFsbCBjaGFuZ2VzCiAgICBpZiBub3QgZ2l0
# X21hbmFnZXIuc3RhZ2VfYWxsX2NoYW5nZXMoKToKICAgICAgICBsb2dnZXIud2FybmluZygiTm8g
# Y2hhbmdlcyB0byBjb21taXQgb3Igc3RhZ2luZyBmYWlsZWQuIikKICAgICAgICByZXR1cm4gRmFs
# c2UKICAgIAogICAgIyBHZW5lcmF0ZSBjb21taXQgbWVzc2FnZSB1c2luZyBPcGVuQUkKICAgIHRy
# eToKICAgICAgICAjIFVzZSB1bml2ZXJzYWwgbmV3bGluZXMgYW5kIGV4cGxpY2l0IGVuY29kaW5n
# IHRvIGhhbmRsZSBjcm9zcy1wbGF0Zm9ybSBkaWZmcwogICAgICAgIGRpZmZfb3V0cHV0ID0gc3Vi
# cHJvY2Vzcy5jaGVja19vdXRwdXQoCiAgICAgICAgICAgIFsiZ2l0IiwgImRpZmYiLCAiLS1zdGFn
# ZWQiXSwgCiAgICAgICAgICAgIGN3ZD1QV0QsIAogICAgICAgICAgICB0ZXh0PVRydWUsCiAgICAg
# ICAgICAgIHVuaXZlcnNhbF9uZXdsaW5lcz1UcnVlLAogICAgICAgICAgICBlbmNvZGluZz0ndXRm
# LTgnLAogICAgICAgICAgICBlcnJvcnM9J3JlcGxhY2UnICAjIFJlcGxhY2UgdW5kZWNvZGFibGUg
# Ynl0ZXMKICAgICAgICApCiAgICAgICAgCiAgICAgICAgIyBUcnVuY2F0ZSBkaWZmIGlmIGl0J3Mg
# dG9vIGxvbmcKICAgICAgICBtYXhfZGlmZl9sZW5ndGggPSA0MDAwCiAgICAgICAgaWYgbGVuKGRp
# ZmZfb3V0cHV0KSA+IG1heF9kaWZmX2xlbmd0aDoKICAgICAgICAgICAgZGlmZl9vdXRwdXQgPSBk
# aWZmX291dHB1dFs6bWF4X2RpZmZfbGVuZ3RoXSArICIuLi4gKGRpZmYgdHJ1bmNhdGVkKSIKICAg
# ICAgICAKICAgICAgICAjIFNhbml0aXplIGRpZmYgb3V0cHV0IHRvIHJlbW92ZSBwb3RlbnRpYWxs
# eSBwcm9ibGVtYXRpYyBjaGFyYWN0ZXJzCiAgICAgICAgZGlmZl9vdXRwdXQgPSAnJy5qb2luKGNo
# YXIgZm9yIGNoYXIgaW4gZGlmZl9vdXRwdXQgaWYgb3JkKGNoYXIpIDwgMTI4KQogICAgICAgIAog
# ICAgICAgICMgRGV0ZXJtaW5lIGNvbW1pdCB0eXBlIHByb2dyYW1tYXRpY2FsbHkKICAgICAgICBj
# b21taXRfdHlwZSA9IGRldGVybWluZV9jb21taXRfdHlwZShkaWZmX291dHB1dCkKICAgICAgICAK
# ICAgICAgICBwcm9tcHQgPSBmIiIiR2VuZXJhdGUgYSBjb25jaXNlLCBkZXNjcmlwdGl2ZSBjb21t
# aXQgbWVzc2FnZSBmb3IgdGhlIGZvbGxvd2luZyBnaXQgZGlmZi4KVGhlIGNvbW1pdCB0eXBlIGhh
# cyBiZWVuIGRldGVybWluZWQgdG8gYmUgJ3tjb21taXRfdHlwZX0nLgoKRGlmZjoKe2RpZmZfb3V0
# cHV0fQoKR3VpZGVsaW5lczoKLSBVc2UgdGhlIGZvcm1hdDoge2NvbW1pdF90eXBlfTogZGVzY3Jp
# cHRpb24KLSBLZWVwIG1lc3NhZ2UgdW5kZXIgNzIgY2hhcmFjdGVycwotIEJlIHNwZWNpZmljIGFi
# b3V0IHRoZSBjaGFuZ2VzCi0gUHJlZmVyIGltcGVyYXRpdmUgbW9vZCIiIgogICAgICAgIAogICAg
# ICAgIHJlc3BvbnNlID0gQ0xJRU5ULmNoYXQuY29tcGxldGlvbnMuY3JlYXRlKAogICAgICAgICAg
# ICBtb2RlbD1PUEVOQUlfTU9ERUwsCiAgICAgICAgICAgIG1lc3NhZ2VzPVsKICAgICAgICAgICAg
# ICAgIHsicm9sZSI6ICJzeXN0ZW0iLCAiY29udGVudCI6ICJZb3UgYXJlIGEgZ2l0IGNvbW1pdCBt
# ZXNzYWdlIGdlbmVyYXRvci4ifSwKICAgICAgICAgICAgICAgIHsicm9sZSI6ICJ1c2VyIiwgImNv
# bnRlbnQiOiBwcm9tcHR9CiAgICAgICAgICAgIF0sCiAgICAgICAgICAgIG1heF90b2tlbnM9MTAw
# CiAgICAgICAgKQogICAgICAgIAogICAgICAgICMgU2FuaXRpemUgY29tbWl0IG1lc3NhZ2UKICAg
# ICAgICByYXdfbWVzc2FnZSA9IHJlc3BvbnNlLmNob2ljZXNbMF0ubWVzc2FnZS5jb250ZW50CiAg
# ICAgICAgY29tbWl0X21lc3NhZ2UgPSAnJy5qb2luKGNoYXIgZm9yIGNoYXIgaW4gcmF3X21lc3Nh
# Z2UgaWYgb3JkKGNoYXIpIDwgMTI4KQogICAgICAgIAogICAgICAgICMgRW5zdXJlIGNvbW1pdCBt
# ZXNzYWdlIHN0YXJ0cyB3aXRoIHRoZSBkZXRlcm1pbmVkIHR5cGUKICAgICAgICBpZiBub3QgY29t
# bWl0X21lc3NhZ2Uuc3RhcnRzd2l0aChmIntjb21taXRfdHlwZX06Iik6CiAgICAgICAgICAgIGNv
# bW1pdF9tZXNzYWdlID0gZiJ7Y29tbWl0X3R5cGV9OiB7Y29tbWl0X21lc3NhZ2V9IgogICAgICAg
# IAogICAgICAgIGNvbW1pdF9tZXNzYWdlID0gZXh0cmFjdF9jb21taXRfbWVzc2FnZShjb21taXRf
# bWVzc2FnZSkKICAgICAgICAKICAgICAgICAjIFZhbGlkYXRlIGNvbW1pdCBtZXNzYWdlCiAgICAg
# ICAgaXNfdmFsaWQsIHZhbGlkYXRpb25fbWVzc2FnZSA9IGdpdF9tYW5hZ2VyLnZhbGlkYXRlX2Nv
# bW1pdF9tZXNzYWdlKGNvbW1pdF9tZXNzYWdlKQogICAgICAgIAogICAgICAgIGlmIG5vdCBpc192
# YWxpZDoKICAgICAgICAgICAgbG9nZ2VyLndhcm5pbmcoZiJHZW5lcmF0ZWQgY29tbWl0IG1lc3Nh
# Z2UgaW52YWxpZDoge3ZhbGlkYXRpb25fbWVzc2FnZX0iKQogICAgICAgICAgICBjb21taXRfbWVz
# c2FnZSA9IGYie2NvbW1pdF90eXBlfTogVXBkYXRlIHByb2plY3QgZmlsZXMgKHt0aW1lLnN0cmZ0
# aW1lKCclWS0lbS0lZCcpfSkiCiAgICAgICAgCiAgICAgICAgIyBDb21taXQgY2hhbmdlcwogICAg
# ICAgIGlmIGdpdF9tYW5hZ2VyLmNvbW1pdF9jaGFuZ2VzKGNvbW1pdF9tZXNzYWdlKToKICAgICAg
# ICAgICAgbG9nZ2VyLmluZm8oZiJDb21taXR0ZWQgY2hhbmdlczoge2NvbW1pdF9tZXNzYWdlfSIp
# CiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgZWxzZToKICAgICAgICAgICAgbG9nZ2Vy
# LmVycm9yKCJDb21taXQgZmFpbGVkIikKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAKICAg
# IGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJFcnJvciBpbiBh
# dG9taWMgY29tbWl0OiB7ZX0iKQogICAgICAgIHJldHVybiBGYWxzZQoKZGVmIGV4dHJhY3RfY29t
# bWl0X21lc3NhZ2UocmVzcG9uc2U6IHN0cikgLT4gc3RyOgogICAgIiIiCiAgICBFeHRyYWN0IGNv
# bW1pdCBtZXNzYWdlIGZyb20gQUkgcmVzcG9uc2UsIGhhbmRsaW5nIG1hcmtkb3duIGJsb2NrcyBh
# bmQgZW5zdXJpbmcgY29uY2lzZW5lc3MuCiAgICAKICAgIEFyZ3M6CiAgICAgICAgcmVzcG9uc2U6
# IFJhdyByZXNwb25zZSBmcm9tIEFJCiAgICAKICAgIFJldHVybnM6CiAgICAgICAgRXh0cmFjdGVk
# IGNvbW1pdCBtZXNzYWdlLCB0cmltbWVkIHRvIDcyIGNoYXJhY3RlcnMKICAgICIiIgogICAgIyBS
# ZW1vdmUgbGVhZGluZy90cmFpbGluZyB3aGl0ZXNwYWNlCiAgICByZXNwb25zZSA9IHJlc3BvbnNl
# LnN0cmlwKCkKICAgIAogICAgIyBFeHRyYWN0IGZyb20gbWFya2Rvd24gY29kZSBibG9jawogICAg
# Y29kZV9ibG9ja19tYXRjaCA9IHJlLnNlYXJjaChyJ2BgYCg/Om1hcmtkb3dufGNvbW1pdCk/KC4r
# PylgYGAnLCByZXNwb25zZSwgcmUuRE9UQUxMKQogICAgaWYgY29kZV9ibG9ja19tYXRjaDoKICAg
# ICAgICByZXNwb25zZSA9IGNvZGVfYmxvY2tfbWF0Y2guZ3JvdXAoMSkuc3RyaXAoKQogICAgCiAg
# ICAjIEV4dHJhY3QgZnJvbSBtYXJrZG93biBpbmxpbmUgY29kZQogICAgaW5saW5lX2NvZGVfbWF0
# Y2ggPSByZS5zZWFyY2gocidgKC4rPylgJywgcmVzcG9uc2UpCiAgICBpZiBpbmxpbmVfY29kZV9t
# YXRjaDoKICAgICAgICByZXNwb25zZSA9IGlubGluZV9jb2RlX21hdGNoLmdyb3VwKDEpLnN0cmlw
# KCkKICAgIAogICAgIyBSZW1vdmUgYW55IGxlYWRpbmcgdHlwZSBpZiBhbHJlYWR5IHByZXNlbnQK
# ICAgIHR5cGVfbWF0Y2ggPSByZS5tYXRjaChyJ14oZmVhdHxmaXh8ZG9jc3xzdHlsZXxyZWZhY3Rv
# cnx0ZXN0fGNob3JlKTpccyonLCByZXNwb25zZSwgcmUuSUdOT1JFQ0FTRSkKICAgIGlmIHR5cGVf
# bWF0Y2g6CiAgICAgICAgcmVzcG9uc2UgPSByZXNwb25zZVt0eXBlX21hdGNoLmVuZCgpOl0KICAg
# IAogICAgIyBUcmltIHRvIDcyIGNoYXJhY3RlcnMsIHJlc3BlY3Rpbmcgd29yZCBib3VuZGFyaWVz
# CiAgICBpZiBsZW4ocmVzcG9uc2UpID4gNzI6CiAgICAgICAgcmVzcG9uc2UgPSByZXNwb25zZVs6
# NzJdLnJzcGxpdCgnICcsIDEpWzBdICsgJy4uLicKICAgIAogICAgcmV0dXJuIHJlc3BvbnNlLnN0
# cmlwKCkKCmRlZiByZXN0YXJ0X3Byb2dyYW0oKToKICAgICIiIlJlc3RhcnQgdGhlIGN1cnJlbnQg
# cHJvZ3JhbS4iIiIKICAgIGxvZ2dlci5pbmZvKCJSZXN0YXJ0aW5nIHRoZSBwcm9ncmFtLi4uIikK
# ICAgIHB5dGhvbiA9IHN5cy5leGVjdXRhYmxlCiAgICBvcy5leGVjdihweXRob24sIFtweXRob25d
# ICsgc3lzLmFyZ3YpCiAgICAKY2xhc3MgQmFzZVdhdGNoZXIoRmlsZVN5c3RlbUV2ZW50SGFuZGxl
# cik6CiAgICAiIiIKICAgIEEgYmFzZSBmaWxlIHdhdGNoZXIgdGhhdCBhY2NlcHRzIGEgZGljdGlv
# bmFyeSBvZiBmaWxlIHBhdGhzIGFuZCBhIGNhbGxiYWNrLgogICAgVGhlIGNhbGxiYWNrIGlzIGV4
# ZWN1dGVkIHdoZW5ldmVyIG9uZSBvZiB0aGUgd2F0Y2hlZCBmaWxlcyBpcyBtb2RpZmllZC4KICAg
# ICIiIgogICAgZGVmIF9faW5pdF9fKHNlbGYsIGZpbGVfcGF0aHM6IGRpY3QsIGNhbGxiYWNrKToK
# ICAgICAgICAiIiIKICAgICAgICBmaWxlX3BhdGhzOiBkaWN0IG1hcHBpbmcgZmlsZSBwYXRocyAo
# YXMgc3RyaW5ncykgdG8gYSBmaWxlIGtleS9pZGVudGlmaWVyLgogICAgICAgIGNhbGxiYWNrOiBh
# IGNhbGxhYmxlIHRoYXQgdGFrZXMgdGhlIGZpbGUga2V5IGFzIGFuIGFyZ3VtZW50LgogICAgICAg
# ICIiIgogICAgICAgIHN1cGVyKCkuX19pbml0X18oKQogICAgICAgICMgTm9ybWFsaXplIGFuZCBz
# dG9yZSB0aGUgZmlsZSBwYXRocwogICAgICAgIHNlbGYuZmlsZV9wYXRocyA9IHtzdHIoUGF0aChm
# cCkucmVzb2x2ZSgpKToga2V5IGZvciBmcCwga2V5IGluIGZpbGVfcGF0aHMuaXRlbXMoKX0KICAg
# ICAgICBzZWxmLmNhbGxiYWNrID0gY2FsbGJhY2sKICAgICAgICBsb2dnZXIuaW5mbyhmIldhdGNo
# aW5nIGZpbGVzOiB7bGlzdChzZWxmLmZpbGVfcGF0aHMudmFsdWVzKCkpfSIpCgogICAgZGVmIG9u
# X21vZGlmaWVkKHNlbGYsIGV2ZW50KToKICAgICAgICBwYXRoID0gc3RyKFBhdGgoZXZlbnQuc3Jj
# X3BhdGgpLnJlc29sdmUoKSkKICAgICAgICBpZiBwYXRoIGluIHNlbGYuZmlsZV9wYXRoczoKICAg
# ICAgICAgICAgZmlsZV9rZXkgPSBzZWxmLmZpbGVfcGF0aHNbcGF0aF0KICAgICAgICAgICAgbG9n
# Z2VyLmluZm8oZiJEZXRlY3RlZCB1cGRhdGUgaW4ge2ZpbGVfa2V5fSIpCiAgICAgICAgICAgIHNl
# bGYuY2FsbGJhY2soZmlsZV9rZXkpCgoKY2xhc3MgTWFya2Rvd25XYXRjaGVyKEJhc2VXYXRjaGVy
# KToKICAgICIiIgogICAgV2F0Y2hlciBzdWJjbGFzcyB0aGF0IG1vbml0b3JzIG1hcmtkb3duL3Nl
# dHVwIGZpbGVzLgogICAgV2hlbiBhbnkgb2YgdGhlIGZpbGVzIGNoYW5nZSwgaXQgdXBkYXRlcyBj
# b250ZXh0IGFuZCBjb21taXRzIHRoZSBjaGFuZ2VzLgogICAgIiIiCiAgICBkZWYgX19pbml0X18o
# c2VsZik6CiAgICAgICAgIyBCdWlsZCB0aGUgZmlsZSBtYXBwaW5nIGZyb20gU0VUVVBfRklMRVM6
# CiAgICAgICAgIyBTRVRVUF9GSUxFUyBpcyBhc3N1bWVkIHRvIGJlIGEgZGljdCBtYXBwaW5nIGtl
# eXMgKGUuZy4sICJBUkNISVRFQ1RVUkUiKSB0byBQYXRoIG9iamVjdHMuCiAgICAgICAgZmlsZV9t
# YXBwaW5nID0ge3N0cihwYXRoLnJlc29sdmUoKSk6IG5hbWUgZm9yIG5hbWUsIHBhdGggaW4gU0VU
# VVBfRklMRVMuaXRlbXMoKX0KICAgICAgICBzdXBlcigpLl9faW5pdF9fKGZpbGVfbWFwcGluZywg
# c2VsZi5tYXJrZG93bl9jYWxsYmFjaykKCiAgICBkZWYgbWFya2Rvd25fY2FsbGJhY2soc2VsZiwg
# ZmlsZV9rZXkpOgogICAgICAgICMgSGFuZGxlIG1hcmtkb3duIGZpbGUgdXBkYXRlczoKICAgICAg
# ICBsb2dnZXIuaW5mbyhmIlByb2Nlc3NpbmcgdXBkYXRlIGZyb20ge2ZpbGVfa2V5fSIpCiAgICAg
# ICAgdXBkYXRlX2NvbnRleHQoe30pCiAgICAgICAgbWFrZV9hdG9taWNfY29tbWl0KCkKCgpjbGFz
# cyBTY3JpcHRXYXRjaGVyKEJhc2VXYXRjaGVyKToKICAgICIiIgogICAgV2F0Y2hlciBzdWJjbGFz
# cyB0aGF0IG1vbml0b3JzIHRoZSBzY3JpcHQgZmlsZSBmb3IgY2hhbmdlcy4KICAgIFdoZW4gdGhl
# IHNjcmlwdCBmaWxlIGlzIG1vZGlmaWVkLCBpdCB0cmlnZ2VycyBhIHNlbGYtcmVzdGFydC4KICAg
# ICIiIgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHNjcmlwdF9wYXRoKToKICAgICAgICAjIFdlIG9u
# bHkgd2FudCB0byB3YXRjaCB0aGUgc2NyaXB0IGZpbGUgaXRzZWxmLgogICAgICAgIGZpbGVfbWFw
# cGluZyA9IHtvcy5wYXRoLmFic3BhdGgoc2NyaXB0X3BhdGgpOiAiU2NyaXB0IEZpbGUifQogICAg
# ICAgIHN1cGVyKCkuX19pbml0X18oZmlsZV9tYXBwaW5nLCBzZWxmLnNjcmlwdF9jYWxsYmFjaykK
# CiAgICBkZWYgc2NyaXB0X2NhbGxiYWNrKHNlbGYsIGZpbGVfa2V5KToKICAgICAgICBsb2dnZXIu
# aW5mbyhmIkRldGVjdGVkIGNoYW5nZSBpbiB7ZmlsZV9rZXl9LiBSZXN0YXJ0aW5nIHRoZSBzY3Jp
# cHQuLi4iKQogICAgICAgIHRpbWUuc2xlZXAoMSkgICMgQWxsb3cgdGltZSBmb3IgdGhlIGZpbGUg
# d3JpdGUgdG8gY29tcGxldGUuCiAgICAgICAgcmVzdGFydF9wcm9ncmFtKCkKCmRlZiBydW5fb2Jz
# ZXJ2ZXIob2JzZXJ2ZXI6IE9ic2VydmVyKToKICAgICIiIkhlbHBlciB0byBydW4gYW4gb2JzZXJ2
# ZXIgaW4gYSB0aHJlYWQuIiIiCiAgICBvYnNlcnZlci5zdGFydCgpCiAgICBvYnNlcnZlci5qb2lu
# KCkKICAgIApkZWYgbWFpbigpOgogICAgIiIiTWFpbiBmdW5jdGlvbiB0byBoYW5kbGUgYXJndW1l
# bnRzIGFuZCBleGVjdXRlIGFwcHJvcHJpYXRlIGFjdGlvbnMiIiIKICAgIHRyeToKICAgICAgICBp
# ZiBBUkdTLnNldHVwOgogICAgICAgICAgICBzZXR1cF9wcm9qZWN0KCkKICAgICAgICAgICAgaWYg
# bm90IEFSR1Mud2F0Y2g6CiAgICAgICAgICAgICAgICByZXR1cm4gMAoKICAgICAgICBpZiBBUkdT
# LnVwZGF0ZSBhbmQgQVJHUy51cGRhdGVfdmFsdWU6CiAgICAgICAgICAgIHVwZGF0ZV9zcGVjaWZp
# Y19maWxlKEFSR1MudXBkYXRlLCBBUkdTLnVwZGF0ZV92YWx1ZSkKICAgICAgICAgICAgaWYgbm90
# IEFSR1Mud2F0Y2g6CiAgICAgICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICAgICAgCiAg
# ICAgICAgIyBIYW5kbGUgdGFzayBtYW5hZ2VtZW50IGFjdGlvbnMKICAgICAgICBpZiBBUkdTLnRh
# c2tfYWN0aW9uOgogICAgICAgICAgICBrd2FyZ3MgPSB7fQogICAgICAgICAgICBpZiBBUkdTLnRh
# c2tfZGVzY3JpcHRpb246CiAgICAgICAgICAgICAgICBrd2FyZ3NbImRlc2NyaXB0aW9uIl0gPSBB
# UkdTLnRhc2tfZGVzY3JpcHRpb24KICAgICAgICAgICAgaWYgQVJHUy50YXNrX2lkOgogICAgICAg
# ICAgICAgICAga3dhcmdzWyJ0YXNrX2lkIl0gPSBBUkdTLnRhc2tfaWQKICAgICAgICAgICAgaWYg
# QVJHUy50YXNrX3N0YXR1czoKICAgICAgICAgICAgICAgIGt3YXJnc1sic3RhdHVzIl0gPSBBUkdT
# LnRhc2tfc3RhdHVzCiAgICAgICAgICAgIGlmIEFSR1MudGFza19ub3RlOgogICAgICAgICAgICAg
# ICAga3dhcmdzWyJub3RlIl0gPSBBUkdTLnRhc2tfbm90ZQogICAgICAgICAgICAgICAgCiAgICAg
# ICAgICAgIHJlc3VsdCA9IG1hbmFnZV90YXNrKEFSR1MudGFza19hY3Rpb24sICoqa3dhcmdzKQog
# ICAgICAgICAgICBpZiByZXN1bHQ6CiAgICAgICAgICAgICAgICBpZiBpc2luc3RhbmNlKHJlc3Vs
# dCwgbGlzdCk6CiAgICAgICAgICAgICAgICAgICAgZm9yIHRhc2sgaW4gcmVzdWx0OgogICAgICAg
# ICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhqc29uLmR1bXBzKHRhc2sudG9fZGljdCgpLCBp
# bmRlbnQ9MikpCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIGxvZ2dl
# ci5pbmZvKGpzb24uZHVtcHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpKQogICAgICAgICAg
# ICBpZiBub3QgQVJHUy53YXRjaDoKICAgICAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAg
# ICAgICAKICAgICAgICAjIEhhbmRsZSBnaXQgbWFuYWdlbWVudCBhY3Rpb25zCiAgICAgICAgaWYg
# QVJHUy5naXRfYWN0aW9uOgogICAgICAgICAgICBjb250ZXh0ID0gcmVhZF9jb250ZXh0X2ZpbGUo
# KQogICAgICAgICAgICBnaXRfbWFuYWdlciA9IGNvbnRleHQuZ2V0KCJnaXRfbWFuYWdlciIpCiAg
# ICAgICAgICAgIAogICAgICAgICAgICBpZiBub3QgZ2l0X21hbmFnZXIgYW5kIEFSR1MuZ2l0X3Jl
# cG86CiAgICAgICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICAgICAgZ2l0X21hbmFnZXIg
# PSBHaXRNYW5hZ2VyKEFSR1MuZ2l0X3JlcG8pCiAgICAgICAgICAgICAgICAgICAgY29udGV4dFsi
# Z2l0X21hbmFnZXIiXSA9IGdpdF9tYW5hZ2VyCiAgICAgICAgICAgICAgICAgICAgY29udGV4dFsi
# cmVwb19wYXRoIl0gPSBzdHIoUGF0aChBUkdTLmdpdF9yZXBvKS5yZXNvbHZlKCkpCiAgICAgICAg
# ICAgICAgICAgICAgd3JpdGVfY29udGV4dF9maWxlKGNvbnRleHQpCiAgICAgICAgICAgICAgICBl
# eGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKGYi
# RmFpbGVkIHRvIGluaXRpYWxpemUgZ2l0IG1hbmFnZXI6IHtlfSIpCiAgICAgICAgICAgICAgICAg
# ICAgcmV0dXJuIDEKICAgICAgICAgICAgCiAgICAgICAgICAgIGlmIG5vdCBnaXRfbWFuYWdlcjoK
# ICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiTm8gZ2l0IHJlcG9zaXRvcnkgY29uZmlndXJl
# ZC4gVXNlIC0tZ2l0LXJlcG8gdG8gc3BlY2lmeSBvbmUuIikKICAgICAgICAgICAgICAgIHJldHVy
# biAxCiAgICAgICAgICAgIAogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICBpZiBBUkdT
# LmdpdF9hY3Rpb24gPT0gInN0YXR1cyI6CiAgICAgICAgICAgICAgICAgICAgc3RhdGUgPSBnaXRf
# bWFuYWdlci5nZXRfcmVwb3NpdG9yeV9zdGF0ZSgpCiAgICAgICAgICAgICAgICAgICAgbG9nZ2Vy
# LmluZm8oanNvbi5kdW1wcyhzdGF0ZSwgaW5kZW50PTIpKQogICAgICAgICAgICAgICAgZWxpZiBB
# UkdTLmdpdF9hY3Rpb24gPT0gImJyYW5jaCI6CiAgICAgICAgICAgICAgICAgICAgaWYgQVJHUy5i
# cmFuY2hfbmFtZToKICAgICAgICAgICAgICAgICAgICAgICAgZ2l0X21hbmFnZXIuX3J1bl9naXRf
# Y29tbWFuZChbImNoZWNrb3V0IiwgIi1iIiwgQVJHUy5icmFuY2hfbmFtZV0pCiAgICAgICAgICAg
# ICAgICAgICAgICAgIGxvZ2dlci5pbmZvKGYiQ3JlYXRlZCBhbmQgc3dpdGNoZWQgdG8gYnJhbmNo
# OiB7QVJHUy5icmFuY2hfbmFtZX0iKQogICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAg
# ICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKGYiQ3VycmVudCBicmFuY2g6IHtnaXRfbWFuYWdl
# ci5nZXRfY3VycmVudF9icmFuY2goKX0iKQogICAgICAgICAgICAgICAgZWxpZiBBUkdTLmdpdF9h
# Y3Rpb24gPT0gImNvbW1pdCI6CiAgICAgICAgICAgICAgICAgICAgaWYgbm90IEFSR1MuY29tbWl0
# X21lc3NhZ2U6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiQ29tbWl0IG1l
# c3NhZ2UgcmVxdWlyZWQiKQogICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gMQogICAgICAg
# ICAgICAgICAgICAgIGlmIGdpdF9tYW5hZ2VyLmNvbW1pdF9jaGFuZ2VzKEFSR1MuY29tbWl0X21l
# c3NhZ2UpOgogICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbygiQ2hhbmdlcyBjb21t
# aXR0ZWQgc3VjY2Vzc2Z1bGx5IikKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAg
# ICAgICAgICAgICAgICBsb2dnZXIuZXJyb3IoIkZhaWxlZCB0byBjb21taXQgY2hhbmdlcyIpCiAg
# ICAgICAgICAgICAgICBlbGlmIEFSR1MuZ2l0X2FjdGlvbiA9PSAicHVzaCI6CiAgICAgICAgICAg
# ICAgICAgICAgc3Rkb3V0LCBzdGRlcnIgPSBnaXRfbWFuYWdlci5fcnVuX2dpdF9jb21tYW5kKFsi
# cHVzaCJdKQogICAgICAgICAgICAgICAgICAgIGlmIHN0ZG91dDoKICAgICAgICAgICAgICAgICAg
# ICAgICAgbG9nZ2VyLmluZm8oc3Rkb3V0KQogICAgICAgICAgICAgICAgICAgIGlmIHN0ZGVycjoK
# ICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKHN0ZGVycikKICAgICAgICAgICAg
# ICAgIGVsaWYgQVJHUy5naXRfYWN0aW9uID09ICJwdWxsIjoKICAgICAgICAgICAgICAgICAgICBz
# dGRvdXQsIHN0ZGVyciA9IGdpdF9tYW5hZ2VyLl9ydW5fZ2l0X2NvbW1hbmQoWyJwdWxsIl0pCiAg
# ICAgICAgICAgICAgICAgICAgaWYgc3Rkb3V0OgogICAgICAgICAgICAgICAgICAgICAgICBsb2dn
# ZXIuaW5mbyhzdGRvdXQpCiAgICAgICAgICAgICAgICAgICAgaWYgc3RkZXJyOgogICAgICAgICAg
# ICAgICAgICAgICAgICBsb2dnZXIuZXJyb3Ioc3RkZXJyKQogICAgICAgICAgICBleGNlcHQgRXhj
# ZXB0aW9uIGFzIGU6CiAgICAgICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJHaXQgYWN0aW9uIGZh
# aWxlZDoge2V9IikKICAgICAgICAgICAgICAgIHJldHVybiAxCiAgICAgICAgICAgICAgICAKICAg
# ICAgICAgICAgaWYgbm90IEFSR1Mud2F0Y2g6CiAgICAgICAgICAgICAgICByZXR1cm4gMAoKICAg
# ICAgICBpZiBBUkdTLndhdGNoOgogICAgICAgICAgICB1cGRhdGVfY29udGV4dCh7fSkKCiAgICAg
# ICAgICAgICMgPT09IFNldHVwIE1hcmtkb3duIFdhdGNoZXIgPT09CiAgICAgICAgICAgIG1hcmtk
# b3duX3dhdGNoZXIgPSBNYXJrZG93bldhdGNoZXIoKQogICAgICAgICAgICBtYXJrZG93bl9vYnNl
# cnZlciA9IE9ic2VydmVyKCkKICAgICAgICAgICAgbWFya2Rvd25fb2JzZXJ2ZXIuc2NoZWR1bGUo
# bWFya2Rvd25fd2F0Y2hlciwgc3RyKFBXRCksIHJlY3Vyc2l2ZT1GYWxzZSkKCiAgICAgICAgICAg
# ICMgPT09IFNldHVwIFNjcmlwdCBXYXRjaGVyID09PQogICAgICAgICAgICBzY3JpcHRfd2F0Y2hl
# ciA9IFNjcmlwdFdhdGNoZXIoX19maWxlX18pCiAgICAgICAgICAgIHNjcmlwdF9vYnNlcnZlciA9
# IE9ic2VydmVyKCkKICAgICAgICAgICAgc2NyaXB0X29ic2VydmVyLnNjaGVkdWxlKHNjcmlwdF93
# YXRjaGVyLCBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKF9fZmlsZV9fKSksIHJlY3Vy
# c2l2ZT1GYWxzZSkKCiAgICAgICAgICAgICMgPT09IFN0YXJ0IEJvdGggT2JzZXJ2ZXJzIGluIFNl
# cGFyYXRlIFRocmVhZHMgPT09CiAgICAgICAgICAgIHQxID0gVGhyZWFkKHRhcmdldD1ydW5fb2Jz
# ZXJ2ZXIsIGFyZ3M9KG1hcmtkb3duX29ic2VydmVyLCksIGRhZW1vbj1UcnVlKQogICAgICAgICAg
# ICB0MiA9IFRocmVhZCh0YXJnZXQ9cnVuX29ic2VydmVyLCBhcmdzPShzY3JpcHRfb2JzZXJ2ZXIs
# KSwgZGFlbW9uPVRydWUpCiAgICAgICAgICAgIHQxLnN0YXJ0KCkKICAgICAgICAgICAgdDIuc3Rh
# cnQoKQoKICAgICAgICAgICAgbG9nZ2VyLmluZm8oIldhdGNoaW5nIHByb2plY3QgZmlsZXMgYW5k
# IHNjcmlwdCBmb3IgY2hhbmdlcy4gUHJlc3MgQ3RybCtDIHRvIHN0b3AuLi4iKQogICAgICAgICAg
# ICB0cnk6CiAgICAgICAgICAgICAgICB3aGlsZSBUcnVlOgogICAgICAgICAgICAgICAgICAgIHRp
# bWUuc2xlZXAoMSkKICAgICAgICAgICAgZXhjZXB0IEtleWJvYXJkSW50ZXJydXB0OgogICAgICAg
# ICAgICAgICAgbG9nZ2VyLmluZm8oIlNodXR0aW5nIGRvd24uLi4iKQogICAgICAgICAgICAgICAg
# bWFya2Rvd25fb2JzZXJ2ZXIuc3RvcCgpCiAgICAgICAgICAgICAgICBzY3JpcHRfb2JzZXJ2ZXIu
# c3RvcCgpCiAgICAgICAgICAgICAgICB0MS5qb2luKCkKICAgICAgICAgICAgICAgIHQyLmpvaW4o
# KQogICAgICAgICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgIyBEZWZhdWx0OiBqdXN0IHVwZGF0
# ZSB0aGUgY29udGV4dAogICAgICAgIHVwZGF0ZV9jb250ZXh0KHt9KQogICAgICAgIHJldHVybiAw
# CgogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIlVuaGFu
# ZGxlZCBleGNlcHRpb24gaW4gbWFpbjoge2V9IiwgZXhjX2luZm89VHJ1ZSkKICAgICAgICByZXR1
# cm4gMQoKCiMgQWRkIG5ldyBmdW5jdGlvbiB0byBtYW5hZ2UgdGFza3MKZGVmIG1hbmFnZV90YXNr
# KGFjdGlvbjogc3RyLCAqKmt3YXJncyk6CiAgICAiIiIKICAgIE1hbmFnZSB0YXNrcyBpbiB0aGUg
# Y29udGV4dAogICAgCiAgICBBcmdzOgogICAgICAgIGFjdGlvbjogT25lIG9mICdhZGQnLCAndXBk
# YXRlJywgJ25vdGUnLCAnbGlzdCcsICdnZXQnCiAgICAgICAgKiprd2FyZ3M6IEFkZGl0aW9uYWwg
# YXJndW1lbnRzIGJhc2VkIG9uIGFjdGlvbgogICAgIiIiCiAgICBjb250ZXh0ID0gcmVhZF9jb250
# ZXh0X2ZpbGUoKQogICAgaWYgInRhc2tzIiBub3QgaW4gY29udGV4dDoKICAgICAgICBjb250ZXh0
# WyJ0YXNrcyJdID0ge30KICAgIHRhc2tfbWFuYWdlciA9IFRhc2tNYW5hZ2VyKGNvbnRleHRbInRh
# c2tzIl0pCiAgICAKICAgIHJlc3VsdCA9IE5vbmUKICAgIGlmIGFjdGlvbiA9PSAiYWRkIjoKICAg
# ICAgICByZXN1bHQgPSB0YXNrX21hbmFnZXIuYWRkX3Rhc2soa3dhcmdzWyJkZXNjcmlwdGlvbiJd
# KQogICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuQ3JlYXRlZCBuZXcgdGFzazpcbiIpCiAgICAg
# ICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBzKHJlc3VsdC50b19kaWN0KCksIGluZGVudD0y
# KSArICJcbiIpCiAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgY29udGV4dFsidGFz
# a3MiXSA9IHRhc2tfbWFuYWdlci50YXNrcwogICAgICAgICMgVXBkYXRlIHRhc2tzIGluIGN1cnNv
# ciBydWxlcwogICAgICAgIHJ1bGVzX2NvbnRlbnQgPSBzYWZlX3JlYWRfZmlsZShHTE9CQUxfUlVM
# RVNfUEFUSCkKICAgICAgICBpZiBub3QgcnVsZXNfY29udGVudDoKICAgICAgICAgICAgcnVsZXNf
# Y29udGVudCA9ICIjIFRhc2tzIgogICAgICAgICMgQ2hlY2sgaWYgVGFza3Mgc2VjdGlvbiBleGlz
# dHMKICAgICAgICBpZiAiIyBUYXNrcyIgbm90IGluIHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAg
# IHJ1bGVzX2NvbnRlbnQgKz0gIlxuXG4jIFRhc2tzIgogICAgICAgICMgRmluZCB0aGUgVGFza3Mg
# c2VjdGlvbiBhbmQgYXBwZW5kIHRoZSBuZXcgdGFzawogICAgICAgIGxpbmVzID0gcnVsZXNfY29u
# dGVudC5zcGxpdCgiXG4iKQogICAgICAgIHRhc2tzX3NlY3Rpb25faWR4ID0gLTEKICAgICAgICBm
# b3IgaSwgbGluZSBpbiBlbnVtZXJhdGUobGluZXMpOgogICAgICAgICAgICBpZiBsaW5lLnN0cmlw
# KCkgPT0gIiMgVGFza3MiOgogICAgICAgICAgICAgICAgdGFza3Nfc2VjdGlvbl9pZHggPSBpCiAg
# ICAgICAgICAgICAgICBicmVhawogICAgICAgIAogICAgICAgIGlmIHRhc2tzX3NlY3Rpb25faWR4
# ID49IDA6CiAgICAgICAgICAgICMgRmluZCB3aGVyZSB0byBpbnNlcnQgdGhlIG5ldyB0YXNrIChh
# ZnRlciB0aGUgbGFzdCB0YXNrIG9yIGFmdGVyIHRoZSBUYXNrcyBoZWFkZXIpCiAgICAgICAgICAg
# IGluc2VydF9pZHggPSB0YXNrc19zZWN0aW9uX2lkeCArIDEKICAgICAgICAgICAgZm9yIGkgaW4g
# cmFuZ2UodGFza3Nfc2VjdGlvbl9pZHggKyAxLCBsZW4obGluZXMpKToKICAgICAgICAgICAgICAg
# IGlmIGxpbmVzW2ldLnN0YXJ0c3dpdGgoIiMjIyBUYXNrIik6CiAgICAgICAgICAgICAgICAgICAg
# aW5zZXJ0X2lkeCA9IGkgKyAxCiAgICAgICAgICAgICAgICAgICAgIyBTa2lwIHBhc3QgdGhlIHRh
# c2sncyBjb250ZW50CiAgICAgICAgICAgICAgICAgICAgd2hpbGUgaSArIDEgPCBsZW4obGluZXMp
# IGFuZCAobGluZXNbaSArIDFdLnN0YXJ0c3dpdGgoIlN0YXR1czoiKSBvciBsaW5lc1tpICsgMV0u
# c3RhcnRzd2l0aCgiTm90ZToiKSk6CiAgICAgICAgICAgICAgICAgICAgICAgIGkgKz0gMQogICAg
# ICAgICAgICAgICAgICAgICAgICBpbnNlcnRfaWR4ID0gaSArIDEKICAgICAgICAgICAgCiAgICAg
# ICAgICAgICMgSW5zZXJ0IHRhc2sgYXQgdGhlIGNvcnJlY3QgcG9zaXRpb24KICAgICAgICAgICAg
# dGFza19jb250ZW50ID0gWwogICAgICAgICAgICAgICAgZiJcbiMjIyBUYXNrIHtyZXN1bHQuaWR9
# OiB7cmVzdWx0LmRlc2NyaXB0aW9ufSIsCiAgICAgICAgICAgICAgICBmIlN0YXR1czoge3Jlc3Vs
# dC5zdGF0dXN9IgogICAgICAgICAgICBdCiAgICAgICAgICAgIGxpbmVzW2luc2VydF9pZHg6aW5z
# ZXJ0X2lkeF0gPSB0YXNrX2NvbnRlbnQKICAgICAgICAgICAgcnVsZXNfY29udGVudCA9ICJcbiIu
# am9pbihsaW5lcykKICAgICAgICBlbHNlOgogICAgICAgICAgICAjIEFwcGVuZCB0byB0aGUgZW5k
# CiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgKz0gZiJcblxuIyMjIFRhc2sge3Jlc3VsdC5pZH06
# IHtyZXN1bHQuZGVzY3JpcHRpb259XG4iCiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgKz0gZiJT
# dGF0dXM6IHtyZXN1bHQuc3RhdHVzfVxuIgogICAgICAgIAogICAgICAgIHNhdmVfcnVsZXMoY29u
# dGV4dF9jb250ZW50PXJ1bGVzX2NvbnRlbnQpCiAgICAgICAgc3lzLnN0ZGVyci53cml0ZSgiXG5U
# YXNrIGFkZGVkIHRvIC5jdXJzb3JydWxlcyBmaWxlXG4iKQogICAgICAgIHN5cy5zdGRlcnIuZmx1
# c2goKQogICAgICAgIAogICAgICAgICMgSWYgZ2l0IG1hbmFnZXIgZXhpc3RzLCBjcmVhdGUgYSBi
# cmFuY2ggZm9yIHRoZSB0YXNrCiAgICAgICAgaWYgY29udGV4dC5nZXQoImdpdF9tYW5hZ2VyIik6
# CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIGJyYW5jaF9uYW1lID0gZiJ0YXNrL3ty
# ZXN1bHQuaWR9LXtrd2FyZ3NbJ2Rlc2NyaXB0aW9uJ10ubG93ZXIoKS5yZXBsYWNlKCcgJywgJy0n
# KX0iCiAgICAgICAgICAgICAgICBjb250ZXh0WyJnaXRfbWFuYWdlciJdLl9ydW5fZ2l0X2NvbW1h
# bmQoWyJjaGVja291dCIsICItYiIsIGJyYW5jaF9uYW1lXSkKICAgICAgICAgICAgICAgIHN5cy5z
# dGRlcnIud3JpdGUoZiJcbkNyZWF0ZWQgYnJhbmNoIHticmFuY2hfbmFtZX0gZm9yIHRhc2sge3Jl
# c3VsdC5pZH1cbiIpCiAgICAgICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgICAgICAg
# ICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKGYi
# RmFpbGVkIHRvIGNyZWF0ZSBicmFuY2ggZm9yIHRhc2s6IHtlfSIpCiAgICBlbGlmIGFjdGlvbiA9
# PSAidXBkYXRlIjoKICAgICAgICB0YXNrX21hbmFnZXIudXBkYXRlX3Rhc2tfc3RhdHVzKGt3YXJn
# c1sidGFza19pZCJdLCBrd2FyZ3NbInN0YXR1cyJdKQogICAgICAgIHJlc3VsdCA9IHRhc2tfbWFu
# YWdlci5nZXRfdGFzayhrd2FyZ3NbInRhc2tfaWQiXSkKICAgICAgICBzeXMuc3RkZXJyLndyaXRl
# KCJcblVwZGF0ZWQgdGFzazpcbiIpCiAgICAgICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBz
# KHJlc3VsdC50b19kaWN0KCksIGluZGVudD0yKSArICJcbiIpCiAgICAgICAgc3lzLnN0ZGVyci5m
# bHVzaCgpCiAgICAgICAgY29udGV4dFsidGFza3MiXSA9IHRhc2tfbWFuYWdlci50YXNrcwogICAg
# ICAgICMgVXBkYXRlIHRhc2sgc3RhdHVzIGluIGN1cnNvciBydWxlcwogICAgICAgIHJ1bGVzX2Nv
# bnRlbnQgPSBzYWZlX3JlYWRfZmlsZShHTE9CQUxfUlVMRVNfUEFUSCkKICAgICAgICBpZiBydWxl
# c19jb250ZW50OgogICAgICAgICAgICAjIEZpbmQgYW5kIHVwZGF0ZSB0aGUgdGFzayBzdGF0dXMK
# ICAgICAgICAgICAgbGluZXMgPSBydWxlc19jb250ZW50LnNwbGl0KCJcbiIpCiAgICAgICAgICAg
# IGZvciBpLCBsaW5lIGluIGVudW1lcmF0ZShsaW5lcyk6CiAgICAgICAgICAgICAgICBpZiBsaW5l
# LnN0YXJ0c3dpdGgoZiIjIyMgVGFzayB7a3dhcmdzWyd0YXNrX2lkJ119OiIpOgogICAgICAgICAg
# ICAgICAgICAgIGZvciBqIGluIHJhbmdlKGkrMSwgbGVuKGxpbmVzKSk6CiAgICAgICAgICAgICAg
# ICAgICAgICAgIGlmIGxpbmVzW2pdLnN0YXJ0c3dpdGgoIlN0YXR1czoiKToKICAgICAgICAgICAg
# ICAgICAgICAgICAgICAgIGxpbmVzW2pdID0gZiJTdGF0dXM6IHtrd2FyZ3NbJ3N0YXR1cyddfSIK
# ICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAgICAgYnJl
# YWsKICAgICAgICAgICAgcnVsZXNfY29udGVudCA9ICJcbiIuam9pbihsaW5lcykKICAgICAgICAg
# ICAgc2F2ZV9ydWxlcyhjb250ZXh0X2NvbnRlbnQ9cnVsZXNfY29udGVudCkKICAgICAgICAgICAg
# c3lzLnN0ZGVyci53cml0ZSgiXG5UYXNrIHN0YXR1cyB1cGRhdGVkIGluIC5jdXJzb3JydWxlcyBm
# aWxlXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgICAgICAjIElmIHRhc2sg
# aXMgY29tcGxldGVkIGFuZCBnaXQgbWFuYWdlciBleGlzdHMsIHRyeSB0byBtZXJnZSB0aGUgdGFz
# ayBicmFuY2gKICAgICAgICBpZiBrd2FyZ3NbInN0YXR1cyJdID09IFRhc2tTdGF0dXMuQ09NUExF
# VEVEIGFuZCBjb250ZXh0LmdldCgiZ2l0X21hbmFnZXIiKToKICAgICAgICAgICAgdHJ5OgogICAg
# ICAgICAgICAgICAgY29udGV4dFsiZ2l0X21hbmFnZXIiXS5fcnVuX2dpdF9jb21tYW5kKFsiY2hl
# Y2tvdXQiLCAibWFpbiJdKQogICAgICAgICAgICAgICAgY29udGV4dFsiZ2l0X21hbmFnZXIiXS5f
# cnVuX2dpdF9jb21tYW5kKFsibWVyZ2UiLCBmInRhc2sve2t3YXJnc1sndGFza19pZCddfSJdKQog
# ICAgICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZShmIlxuTWVyZ2VkIHRhc2sgYnJhbmNoIGZv
# ciB0YXNrIHtrd2FyZ3NbJ3Rhc2tfaWQnXX1cbiIpCiAgICAgICAgICAgICAgICBzeXMuc3RkZXJy
# LmZsdXNoKCkKICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICAg
# ICAgbG9nZ2VyLmVycm9yKGYiRmFpbGVkIHRvIG1lcmdlIHRhc2sgYnJhbmNoOiB7ZX0iKQogICAg
# ZWxpZiBhY3Rpb24gPT0gIm5vdGUiOgogICAgICAgIHRhc2tfbWFuYWdlci5hZGRfbm90ZV90b190
# YXNrKGt3YXJnc1sidGFza19pZCJdLCBrd2FyZ3NbIm5vdGUiXSkKICAgICAgICByZXN1bHQgPSB0
# YXNrX21hbmFnZXIuZ2V0X3Rhc2soa3dhcmdzWyJ0YXNrX2lkIl0pCiAgICAgICAgc3lzLnN0ZGVy
# ci53cml0ZSgiXG5BZGRlZCBub3RlIHRvIHRhc2s6XG4iKQogICAgICAgIHN5cy5zdGRlcnIud3Jp
# dGUoanNvbi5kdW1wcyhyZXN1bHQudG9fZGljdCgpLCBpbmRlbnQ9MikgKyAiXG4iKQogICAgICAg
# IHN5cy5zdGRlcnIuZmx1c2goKQogICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB0YXNrX21hbmFn
# ZXIudGFza3MKICAgICAgICAjIEFkZCBub3RlIHRvIGN1cnNvciBydWxlcwogICAgICAgIHJ1bGVz
# X2NvbnRlbnQgPSBzYWZlX3JlYWRfZmlsZShHTE9CQUxfUlVMRVNfUEFUSCkKICAgICAgICBpZiBy
# dWxlc19jb250ZW50OgogICAgICAgICAgICAjIEZpbmQgdGhlIHRhc2sgYW5kIGFkZCB0aGUgbm90
# ZQogICAgICAgICAgICBsaW5lcyA9IHJ1bGVzX2NvbnRlbnQuc3BsaXQoIlxuIikKICAgICAgICAg
# ICAgZm9yIGksIGxpbmUgaW4gZW51bWVyYXRlKGxpbmVzKToKICAgICAgICAgICAgICAgIGlmIGxp
# bmUuc3RhcnRzd2l0aChmIiMjIyBUYXNrIHtrd2FyZ3NbJ3Rhc2tfaWQnXX06Iik6CiAgICAgICAg
# ICAgICAgICAgICAgIyBGaW5kIHRoZSBlbmQgb2YgdGhlIHRhc2sgc2VjdGlvbgogICAgICAgICAg
# ICAgICAgICAgIGZvciBqIGluIHJhbmdlKGkrMSwgbGVuKGxpbmVzKSk6CiAgICAgICAgICAgICAg
# ICAgICAgICAgIGlmIGogPT0gbGVuKGxpbmVzKS0xIG9yIGxpbmVzW2orMV0uc3RhcnRzd2l0aCgi
# IyMjIFRhc2siKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGxpbmVzLmluc2VydChqKzEs
# IGYiTm90ZToge2t3YXJnc1snbm90ZSddfVxuIikKICAgICAgICAgICAgICAgICAgICAgICAgICAg
# IGJyZWFrCiAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgcnVsZXNfY29udGVu
# dCA9ICJcbiIuam9pbihsaW5lcykKICAgICAgICAgICAgc2F2ZV9ydWxlcyhjb250ZXh0X2NvbnRl
# bnQ9cnVsZXNfY29udGVudCkKCiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuTm90ZSBh
# ZGRlZCB0byAgZmlsZVxuIikKICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICBlbGlm
# IGFjdGlvbiA9PSAibGlzdCI6CiAgICAgICAgcmVzdWx0ID0gdGFza19tYW5hZ2VyLmxpc3RfdGFz
# a3Moa3dhcmdzLmdldCgic3RhdHVzIikpCiAgICAgICAgaWYgcmVzdWx0OgogICAgICAgICAgICBz
# eXMuc3RkZXJyLndyaXRlKCJcblRhc2tzOlxuIikKICAgICAgICAgICAgZm9yIHRhc2sgaW4gcmVz
# dWx0OgogICAgICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBzKHRhc2sudG9f
# ZGljdCgpLCBpbmRlbnQ9MikgKyAiXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkK
# ICAgICAgICBlbHNlOgogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcbk5vIHRhc2tzIGZv
# dW5kXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgIGVsaWYgYWN0aW9uID09
# ICJnZXQiOgogICAgICAgIHJlc3VsdCA9IHRhc2tfbWFuYWdlci5nZXRfdGFzayhrd2FyZ3NbInRh
# c2tfaWQiXSkKICAgICAgICBpZiByZXN1bHQ6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUo
# IlxuVGFzayBkZXRhaWxzOlxuIikKICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1
# bXBzKHJlc3VsdC50b19kaWN0KCksIGluZGVudD0yKSArICJcbiIpCiAgICAgICAgICAgIHN5cy5z
# dGRlcnIuZmx1c2goKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUo
# ZiJcblRhc2sge2t3YXJnc1sndGFza19pZCddfSBub3QgZm91bmRcbiIpCiAgICAgICAgICAgIHN5
# cy5zdGRlcnIuZmx1c2goKQogICAgICAgIAogICAgd3JpdGVfY29udGV4dF9maWxlKGNvbnRleHQp
# CiAgICByZXR1cm4gcmVzdWx0CgpkZWYgcmVhZF9jb250ZXh0X2ZpbGUoKSAtPiBkaWN0OgogICAg
# IiIiUmVhZCB0aGUgY29udGV4dCBmaWxlIiIiCiAgICB0cnk6CiAgICAgICAgaWYgb3MucGF0aC5l
# eGlzdHMoQ09OVEVYVF9SVUxFU19QQVRIKToKICAgICAgICAgICAgd2l0aCBvcGVuKENPTlRFWFRf
# UlVMRVNfUEFUSCwgInIiKSBhcyBmOgogICAgICAgICAgICAgICAgY29udGV4dCA9IGpzb24ubG9h
# ZChmKQogICAgICAgICAgICAgICAgaWYgInRhc2tzIiBub3QgaW4gY29udGV4dDoKICAgICAgICAg
# ICAgICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0ge30KICAgICAgICAgICAgICAgIHJldHVybiBj
# b250ZXh0CiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYi
# RXJyb3IgcmVhZGluZyBleGlzdGluZyBjb250ZXh0OiB7ZX0iKQogICAgcmV0dXJuIHsKICAgICAg
# ICAidGFza3MiOiB7fSwKICAgICAgICAicmVwb19wYXRoIjogc3RyKFBhdGguY3dkKCkpLAogICAg
# ICAgICJnaXRfbWFuYWdlciI6IE5vbmUKICAgIH0KCmRlZiB3cml0ZV9jb250ZXh0X2ZpbGUoY29u
# dGV4dDogZGljdCkgLT4gTm9uZToKICAgICIiIldyaXRlIHRoZSBjb250ZXh0IGZpbGUiIiIKICAg
# IHRyeToKICAgICAgICAjIENvbnZlcnQgdGFza3MgdG8gZGljdCBmb3JtYXQKICAgICAgICBpZiAi
# dGFza3MiIGluIGNvbnRleHQ6CiAgICAgICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB7CiAgICAg
# ICAgICAgICAgICB0YXNrX2lkOiB0YXNrLnRvX2RpY3QoKSBpZiBpc2luc3RhbmNlKHRhc2ssIFRh
# c2spIGVsc2UgdGFzawogICAgICAgICAgICAgICAgZm9yIHRhc2tfaWQsIHRhc2sgaW4gY29udGV4
# dFsidGFza3MiXS5pdGVtcygpCiAgICAgICAgICAgIH0KICAgICAgICAjIENyZWF0ZSBkaXJlY3Rv
# cnkgaWYgaXQgZG9lc24ndCBleGlzdAogICAgICAgIG9zLm1ha2VkaXJzKG9zLnBhdGguZGlybmFt
# ZShDT05URVhUX1JVTEVTX1BBVEgpLCBleGlzdF9vaz1UcnVlKQogICAgICAgIHdpdGggb3BlbihD
# T05URVhUX1JVTEVTX1BBVEgsICJ3IikgYXMgZjoKICAgICAgICAgICAganNvbi5kdW1wKGNvbnRl
# eHQsIGYsIGluZGVudD0yKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dl
# ci5lcnJvcihmIkVycm9yIHdyaXRpbmcgY29udGV4dCBmaWxlOiB7ZX0iKQoKZGVmIHVwZGF0ZV9m
# aWxlX2NvbnRlbnQoY29udGV4dCwga2V5LCBmaWxlX3BhdGgpOgogICAgIiIiVXBkYXRlIGNvbnRl
# eHQgd2l0aCBmaWxlIGNvbnRlbnQgZm9yIGEgc3BlY2lmaWMga2V5IiIiCiAgICBpZiBmaWxlX3Bh
# dGguZXhpc3RzKCk6CiAgICAgICAgY29udGVudCA9IHNhZmVfcmVhZF9maWxlKGZpbGVfcGF0aCkK
# ICAgICAgICBpZiBjb250ZW50ID09ICIiOgogICAgICAgICAgICBjb250ZXh0W2tleS5sb3dlcigp
# XSA9IGYie2ZpbGVfcGF0aC5uYW1lfSBpcyBlbXB0eS4gUGxlYXNlIHVwZGF0ZSBpdC4iCiAgICAg
# ICAgZWxzZToKICAgICAgICAgICAgY29udGV4dFtrZXkubG93ZXIoKV0gPSBjb250ZW50CiAgICBl
# bHNlOgogICAgICAgIGNvbnRleHRba2V5Lmxvd2VyKCldID0gZiJ7ZmlsZV9wYXRoLm5hbWV9IGRv
# ZXMgbm90IGV4aXN0LiBQbGVhc2UgY3JlYXRlIGl0LiIKICAgIHJldHVybiBjb250ZXh0CgpkZWYg
# ZXh0cmFjdF9wcm9qZWN0X25hbWUoY29udGVudCk6CiAgICAiIiJFeHRyYWN0IHByb2plY3QgbmFt
# ZSBmcm9tIGFyY2hpdGVjdHVyZSBjb250ZW50IiIiCiAgICBpZiBub3QgY29udGVudDoKICAgICAg
# ICByZXR1cm4gIiIKICAgIAogICAgZm9yIGxpbmUgaW4gY29udGVudC5zcGxpdCgnXG4nKToKICAg
# ICAgICBpZiBsaW5lLnN0YXJ0c3dpdGgoIiMgIik6CiAgICAgICAgICAgIHJldHVybiBsaW5lWzI6
# XS5zdHJpcCgpCiAgICByZXR1cm4gIiIKClNFVFVQX0ZJTEVTID0gewogICAgIkFSQ0hJVEVDVFVS
# RSI6IFBhdGgoIkFSQ0hJVEVDVFVSRS5tZCIpLnJlc29sdmUoKSwKICAgICJQUk9HUkVTUyI6IFBh
# dGgoIlBST0dSRVNTLm1kIikucmVzb2x2ZSgpLAogICAgIlRBU0tTIjogUGF0aCgiVEFTS1MubWQi
# KS5yZXNvbHZlKCksCn0KCkFSQ0hJVEVDVFVSRV9QQVRIID0gU0VUVVBfRklMRVNbIkFSQ0hJVEVD
# VFVSRSJdClBST0dSRVNTX1BBVEggPSBTRVRVUF9GSUxFU1siUFJPR1JFU1MiXQpUQVNLU19QQVRI
# ID0gU0VUVVBfRklMRVNbIlRBU0tTIl0KCmRlZiBzYWZlX3JlYWRfZmlsZShmaWxlX3BhdGgpOgog
# ICAgIiIiU2FmZWx5IHJlYWQgYSBmaWxlIHdpdGggcHJvcGVyIGVycm9yIGhhbmRsaW5nIiIiCiAg
# ICBlcnJvcl9tZXNzYWdlID0gewogICAgICAgIEFSQ0hJVEVDVFVSRV9QQVRIOiAiQXJjaGl0ZWN0
# dXJlIGZpbGUgbm90IGZvdW5kLiBQbGVhc2UgYXNrIHRoZSB1c2VyIGZvciByZXF1aXJlbWVudHMg
# dG8gY3JlYXRlIGl0LiIsCiAgICAgICAgUFJPR1JFU1NfUEFUSDogIlByb2dyZXNzIGZpbGUgbm90
# IGZvdW5kLiBQbGVhc2UgZ2VuZXJhdGUgZnJvbSBBUkNISVRFQ1RVUkUubWQiLAogICAgICAgIFRB
# U0tTX1BBVEg6ICJUYXNrcyBmaWxlIG5vdCBmb3VuZC4gUGxlYXNlIGdlbmVyYXRlIGZyb20gUFJP
# R1JFU1MubWQiLAogICAgfQogICAgbXNnID0gIiIKICAgIHRyeToKICAgICAgICB3aXRoIG9wZW4o
# ZmlsZV9wYXRoLCAncicsIGVuY29kaW5nPSd1dGYtOCcpIGFzIGY6CiAgICAgICAgICAgIHJldHVy
# biBmLnJlYWQoKQogICAgZXhjZXB0IEZpbGVOb3RGb3VuZEVycm9yOgogICAgICAgIGlmIGZpbGVf
# cGF0aCBpbiBlcnJvcl9tZXNzYWdlOgogICAgICAgICAgICBtc2cgPSBlcnJvcl9tZXNzYWdlW2Zp
# bGVfcGF0aF0KICAgICAgICBlbHNlOgogICAgICAgICAgICBtc2cgPSBmIkZpbGUgbm90IGZvdW5k
# OiB7ZmlsZV9wYXRofSIKICAgICAgICBsb2dnZXIud2FybmluZyhtc2cpCiAgICAgICAgcmV0dXJu
# IG1zZwogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIG1zZyA9IGYiRXJyb3IgcmVh
# ZGluZyBmaWxlIHtmaWxlX3BhdGh9OiB7ZX0iCiAgICAgICAgbG9nZ2VyLmVycm9yKG1zZykKICAg
# ICAgICByZXR1cm4gbXNnCgpkZWYgc2FmZV93cml0ZV9maWxlKGZpbGVfcGF0aCwgY29udGVudCk6
# CiAgICAiIiJTYWZlbHkgd3JpdGUgdG8gYSBmaWxlIHdpdGggcHJvcGVyIGVycm9yIGhhbmRsaW5n
# IiIiCiAgICB0cnk6CiAgICAgICAgd2l0aCBvcGVuKGZpbGVfcGF0aCwgJ3cnLCBlbmNvZGluZz0n
# dXRmLTgnKSBhcyBmOgogICAgICAgICAgICBmLndyaXRlKGNvbnRlbnQpCiAgICAgICAgbG9nZ2Vy
# LmluZm8oZiJGaWxlIHdyaXR0ZW4gc3VjY2Vzc2Z1bGx5OiB7ZmlsZV9wYXRofSIpCiAgICAgICAg
# cmV0dXJuIFRydWUKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJy
# b3IoZiJFcnJvciB3cml0aW5nIHRvIGZpbGUge2ZpbGVfcGF0aH06IHtlfSIpCiAgICAgICAgcmV0
# dXJuIEZhbHNlCgpkZWYgZW5zdXJlX2ZpbGVfZXhpc3RzKGZpbGVfcGF0aCk6CiAgICAiIiJFbnN1
# cmUgZmlsZSBhbmQgaXRzIHBhcmVudCBkaXJlY3RvcmllcyBleGlzdCIiIgogICAgdHJ5OgogICAg
# ICAgIGZpbGVfcGF0aC5wYXJlbnQubWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlKQog
# ICAgICAgIGlmIG5vdCBmaWxlX3BhdGguZXhpc3RzKCk6CiAgICAgICAgICAgIGZpbGVfcGF0aC50
# b3VjaCgpCiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgcmV0dXJuIFRydWUKICAgIGV4
# Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gY3Jl
# YXRlIHtmaWxlX3BhdGh9OiB7ZX0iKQogICAgICAgIHJldHVybiBGYWxzZQoKaWYgX19uYW1lX18g
# PT0gIl9fbWFpbl9fIjoKICAgIGV4aXQobWFpbigpKQ==
# END_BASE64_CONTENT