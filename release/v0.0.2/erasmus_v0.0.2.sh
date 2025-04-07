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
    echo "To start using Erasmus, run: uv run erasmus.py --watch"
}

# Run the main installation function
main


# __ERASMUS_EMBEDDED_BELOW__
# The content below this line is the base64-encoded erasmus.py file
# It will be extracted during installation
# SHA256_HASH=f962a9d7f05d1a76ce30ed4a245b70e0f309a33a8d110383bc62b6168ac590ff
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
# TCB2YWxpZGF0aW9uIHVzaW5nIHJlZ2V4LgogICAgCiAgICBBY2NlcHRzOgogICAgLSBTdGFuZGFy
# ZCBodHRwL2h0dHBzIFVSTHMgKGUuZy4sIGh0dHBzOi8vYXBpLm9wZW5haS5jb20vdjEpCiAgICAt
# IExvY2FsaG9zdCBVUkxzIHdpdGggb3B0aW9uYWwgcG9ydCAoZS5nLiwgaHR0cDovL2xvY2FsaG9z
# dDoxMTQzNCkKICAgIC0gSVAtYmFzZWQgbG9jYWxob3N0IFVSTHMgKGUuZy4sIGh0dHA6Ly8xMjcu
# MC4wLjE6ODAwMCkKICAgIAogICAgQXJnczoKICAgICAgICB1cmw6IFVSTCBzdHJpbmcgdG8gdmFs
# aWRhdGUKICAgICAgICAKICAgIFJldHVybnM6CiAgICAgICAgYm9vbDogVHJ1ZSBpZiB0aGUgVVJM
# IGlzIHZhbGlkLCBGYWxzZSBvdGhlcndpc2UKICAgICIiIgogICAgaWYgbm90IHVybDoKICAgICAg
# ICByZXR1cm4gRmFsc2UKICAgIAogICAgIyBMb2cgdGhlIFVSTCBiZWluZyB2YWxpZGF0ZWQgZm9y
# IGRlYnVnZ2luZwogICAgbG9nZ2VyLmRlYnVnKGYiVmFsaWRhdGluZyBVUkw6IHt1cmx9IikKICAg
# IAogICAgIyBDaGVjayBmb3IgbG9jYWxob3N0IG9yIDEyNy4wLjAuMQogICAgbG9jYWxob3N0X3Bh
# dHRlcm4gPSByZS5tYXRjaChyJ15odHRwcz86Ly8oPzpsb2NhbGhvc3R8MTI3XC4wXC4wXC4xKSg/
# OjpcZCspPyg/Oi8uKik/JCcsIHVybCkKICAgIGlmIGxvY2FsaG9zdF9wYXR0ZXJuOgogICAgICAg
# IGxvZ2dlci5kZWJ1ZyhmIlVSTCB7dXJsfSBtYXRjaGVkIGxvY2FsaG9zdCBwYXR0ZXJuIikKICAg
# ICAgICByZXR1cm4gVHJ1ZQogICAgICAgIAogICAgIyBDaGVjayBmb3Igc3RhbmRhcmQgaHR0cC9o
# dHRwcyBVUkxzCiAgICBzdGFuZGFyZF9wYXR0ZXJuID0gcmUubWF0Y2gocideaHR0cHM/Oi8vW1x3
# XC4tXSsoPzo6XGQrKT8oPzovLiopPyQnLCB1cmwpCiAgICByZXN1bHQgPSBib29sKHN0YW5kYXJk
# X3BhdHRlcm4pCiAgICAKICAgIGlmIHJlc3VsdDoKICAgICAgICBsb2dnZXIuZGVidWcoZiJVUkwg
# e3VybH0gbWF0Y2hlZCBzdGFuZGFyZCBwYXR0ZXJuIikKICAgIGVsc2U6CiAgICAgICAgbG9nZ2Vy
# Lndhcm5pbmcoZiJVUkwgdmFsaWRhdGlvbiBmYWlsZWQgZm9yOiB7dXJsfSIpCiAgICAgICAgCiAg
# ICByZXR1cm4gcmVzdWx0CgpkZWYgZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpIC0+IHN0cjoKICAg
# ICIiIgogICAgRGV0ZWN0IHRoZSBjdXJyZW50IElERSBlbnZpcm9ubWVudC4KICAgIAogICAgUmV0
# dXJuczoKICAgICAgICBzdHI6IERldGVjdGVkIElERSBlbnZpcm9ubWVudCAoJ1dJTkRTVVJGJywg
# J0NVUlNPUicsIG9yICcnKQogICAgIiIiCiAgICAjIENoZWNrIGVudmlyb25tZW50IHZhcmlhYmxl
# IGZpcnN0CiAgICBpZGVfZW52ID0gb3MuZ2V0ZW52KCdJREVfRU5WJywgJycpLnVwcGVyKCkKICAg
# IGlmIGlkZV9lbnY6CiAgICAgICAgcmV0dXJuICdXSU5EU1VSRicgaWYgaWRlX2Vudi5zdGFydHN3
# aXRoKCdXJykgZWxzZSAnQ1VSU09SJwogICAgCiAgICAjIFRyeSB0byBkZXRlY3QgYmFzZWQgb24g
# Y3VycmVudCB3b3JraW5nIGRpcmVjdG9yeSBvciBrbm93biBJREUgcGF0aHMKICAgIGN3ZCA9IFBh
# dGguY3dkKCkKICAgIAogICAgIyBXaW5kc3VyZi1zcGVjaWZpYyBkZXRlY3Rpb24KICAgIHdpbmRz
# dXJmX21hcmtlcnMgPSBbCiAgICAgICAgUGF0aC5ob21lKCkgLyAnLmNvZGVpdW0nIC8gJ3dpbmRz
# dXJmJywKICAgICAgICBjd2QgLyAnLndpbmRzdXJmcnVsZXMnCiAgICBdCiAgICAKICAgICMgQ3Vy
# c29yLXNwZWNpZmljIGRldGVjdGlvbgogICAgY3Vyc29yX21hcmtlcnMgPSBbCiAgICAgICAgY3dk
# IC8gJy5jdXJzb3JydWxlcycsCiAgICAgICAgUGF0aC5ob21lKCkgLyAnLmN1cnNvcicKICAgIF0K
# ICAgIAogICAgIyBDaGVjayBXaW5kc3VyZiBtYXJrZXJzCiAgICBmb3IgbWFya2VyIGluIHdpbmRz
# dXJmX21hcmtlcnM6CiAgICAgICAgaWYgbWFya2VyLmV4aXN0cygpOgogICAgICAgICAgICByZXR1
# cm4gJ1dJTkRTVVJGJwogICAgCiAgICAjIENoZWNrIEN1cnNvciBtYXJrZXJzCiAgICBmb3IgbWFy
# a2VyIGluIGN1cnNvcl9tYXJrZXJzOgogICAgICAgIGlmIG1hcmtlci5leGlzdHMoKToKICAgICAg
# ICAgICAgcmV0dXJuICdDVVJTT1InCiAgICAKICAgICMgRGVmYXVsdCBmYWxsYmFjawogICAgcmV0
# dXJuICdXSU5EU1VSRicKCgpkZWYgcHJvbXB0X29wZW5haV9jcmVkZW50aWFscyhlbnZfcGF0aD0i
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
# Z2V0X29wZW5haV9jcmVkZW50aWFscygpOgogICAgIiIiR2V0IE9wZW5BSSBjcmVkZW50aWFscyBm
# cm9tIGVudmlyb25tZW50IHZhcmlhYmxlcyIiIgogICAgYXBpX2tleSA9IG9zLmVudmlyb24uZ2V0
# KCJPUEVOQUlfQVBJX0tFWSIpCiAgICBiYXNlX3VybCA9IG9zLmVudmlyb24uZ2V0KCJPUEVOQUlf
# QkFTRV9VUkwiKQogICAgaWYgbm90IGJhc2VfdXJsOgogICAgICAgIGJhc2VfdXJsID0gImh0dHBz
# Oi8vYXBpLm9wZW5haS5jb20vdjEiCiAgICBtb2RlbCA9IG9zLmVudmlyb24uZ2V0KCJPUEVOQUlf
# TU9ERUwiKQogICAgcmV0dXJuIGFwaV9rZXksIGJhc2VfdXJsLCBtb2RlbAoKIyAtLS0gT3BlbkFJ
# IENsaWVudCBJbml0aWFsaXphdGlvbiAtLS0KZGVmIGluaXRfb3BlbmFpX2NsaWVudCgpOgogICAg
# IiIiSW5pdGlhbGl6ZSBhbmQgcmV0dXJuIE9wZW5BSSBjbGllbnQgY29uZmlndXJhdGlvbiIiIgog
# ICAgdHJ5OgogICAgICAgIGFwaV9rZXksIGJhc2VfdXJsLCBtb2RlbCA9IGdldF9vcGVuYWlfY3Jl
# ZGVudGlhbHMoKQogICAgICAgIAogICAgICAgICMgQ2hlY2sgaWYgYW55IGNyZWRlbnRpYWxzIGFy
# ZSBtaXNzaW5nCiAgICAgICAgbWlzc2luZ19jcmVkcyA9IFtdCiAgICAgICAgaWYgbm90IGFwaV9r
# ZXk6CiAgICAgICAgICAgIG1pc3NpbmdfY3JlZHMuYXBwZW5kKCJBUEkga2V5IikKICAgICAgICBp
# ZiBub3QgYmFzZV91cmw6CiAgICAgICAgICAgIG1pc3NpbmdfY3JlZHMuYXBwZW5kKCJiYXNlIFVS
# TCIpCiAgICAgICAgaWYgbm90IG1vZGVsOgogICAgICAgICAgICBtaXNzaW5nX2NyZWRzLmFwcGVu
# ZCgibW9kZWwiKQogICAgICAgICAgICAKICAgICAgICBpZiBtaXNzaW5nX2NyZWRzOgogICAgICAg
# ICAgICBsb2dnZXIud2FybmluZyhmIk1pc3NpbmcgT3BlbkFJIGNyZWRlbnRpYWxzOiB7JywgJy5q
# b2luKG1pc3NpbmdfY3JlZHMpfS4gUHJvbXB0aW5nIGZvciBpbnB1dC4uLiIpCiAgICAgICAgICAg
# IHByb21wdF9vcGVuYWlfY3JlZGVudGlhbHMoKQogICAgICAgICAgICBhcGlfa2V5LCBiYXNlX3Vy
# bCwgbW9kZWwgPSBnZXRfb3BlbmFpX2NyZWRlbnRpYWxzKCkKICAgICAgICAgICAgCiAgICAgICAg
# ICAgICMgQ2hlY2sgYWdhaW4gYWZ0ZXIgcHJvbXB0aW5nCiAgICAgICAgICAgIGlmIG5vdCBhcGlf
# a2V5OgogICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKCJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBP
# cGVuQUkgY2xpZW50OiBtaXNzaW5nIEFQSSBrZXkiKQogICAgICAgICAgICAgICAgcmV0dXJuIE5v
# bmUsIE5vbmUKICAgICAgICAgICAgaWYgbm90IG1vZGVsOgogICAgICAgICAgICAgICAgbG9nZ2Vy
# LmVycm9yKCJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBPcGVuQUkgY2xpZW50OiBtaXNzaW5nIG1vZGVs
# IG5hbWUiKQogICAgICAgICAgICAgICAgcmV0dXJuIE5vbmUsIE5vbmUKICAgICAgICAKICAgICAg
# ICAjIEVuc3VyZSBiYXNlX3VybCBoYXMgYSB2YWxpZCBmb3JtYXQKICAgICAgICBpZiBub3QgYmFz
# ZV91cmw6CiAgICAgICAgICAgIGJhc2VfdXJsID0gImh0dHBzOi8vYXBpLm9wZW5haS5jb20vdjEi
# CiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKGYiVXNpbmcgZGVmYXVsdCBPcGVuQUkgYmFzZSBV
# Ukw6IHtiYXNlX3VybH0iKQogICAgICAgIGVsaWYgbm90IGlzX3ZhbGlkX3VybChiYXNlX3VybCk6
# CiAgICAgICAgICAgIGxvZ2dlci53YXJuaW5nKGYiSW52YWxpZCBiYXNlIFVSTCBmb3JtYXQ6IHti
# YXNlX3VybH0uIFVzaW5nIGRlZmF1bHQuIikKICAgICAgICAgICAgYmFzZV91cmwgPSAiaHR0cHM6
# Ly9hcGkub3BlbmFpLmNvbS92MSIKICAgICAgICAKICAgICAgICBsb2dnZXIuaW5mbyhmIkluaXRp
# YWxpemluZyBPcGVuQUkgY2xpZW50IHdpdGggYmFzZSBVUkw6IHtiYXNlX3VybH0gYW5kIG1vZGVs
# OiB7bW9kZWx9IikKICAgICAgICBjbGllbnQgPSBPcGVuQUkoYXBpX2tleT1hcGlfa2V5LCBiYXNl
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
# PVsiY3Vyc29yIiwgIndpbmRzdXJmIiwgIkNVUlNPUiIsICJXSU5EU1VSRiJdLCBoZWxwPSJTZXR1
# cCBwcm9qZWN0IiwgZGVmYXVsdD0iY3Vyc29yIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0t
# dHlwZSIsIGNob2ljZXM9WyJjdXJzb3IiLCAid2luZHN1cmYiLCAiQ1VSU09SIiwgIldJTkRTVVJG
# Il0sIGhlbHA9IlByb2plY3QgdHlwZSIsIGRlZmF1bHQ9ImN1cnNvciIpCiAgICAKICAgICMgVGFz
# ayBtYW5hZ2VtZW50IGFyZ3VtZW50cwogICAgdGFza19ncm91cCA9IHBhcnNlci5hZGRfYXJndW1l
# bnRfZ3JvdXAoIlRhc2sgTWFuYWdlbWVudCIpCiAgICB0YXNrX2dyb3VwLmFkZF9hcmd1bWVudCgi
# LS10YXNrLWFjdGlvbiIsIGNob2ljZXM9WyJhZGQiLCAidXBkYXRlIiwgIm5vdGUiLCAibGlzdCIs
# ICJnZXQiXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgaGVscD0iVGFzayBtYW5hZ2VtZW50
# IGFjdGlvbiIpCiAgICB0YXNrX2dyb3VwLmFkZF9hcmd1bWVudCgiLS10YXNrLWlkIiwgaGVscD0i
# VGFzayBJRCBmb3IgdXBkYXRlL25vdGUvZ2V0IGFjdGlvbnMiKQogICAgdGFza19ncm91cC5hZGRf
# YXJndW1lbnQoIi0tdGFzay1kZXNjcmlwdGlvbiIsIGhlbHA9IlRhc2sgZGVzY3JpcHRpb24gZm9y
# IGFkZCBhY3Rpb24iKQogICAgdGFza19ncm91cC5hZGRfYXJndW1lbnQoIi0tdGFzay1zdGF0dXMi
# LCBjaG9pY2VzPVtUYXNrU3RhdHVzLlBFTkRJTkcsIFRhc2tTdGF0dXMuSU5fUFJPR1JFU1MsIAog
# ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFRhc2tT
# dGF0dXMuQ09NUExFVEVELCBUYXNrU3RhdHVzLkJMT0NLRURdLAogICAgICAgICAgICAgICAgICAg
# ICAgICAgICBoZWxwPSJUYXNrIHN0YXR1cyBmb3IgdXBkYXRlIGFjdGlvbiIpCiAgICB0YXNrX2dy
# b3VwLmFkZF9hcmd1bWVudCgiLS10YXNrLW5vdGUiLCBoZWxwPSJOb3RlIGNvbnRlbnQgZm9yIG5v
# dGUgYWN0aW9uIikKICAgIAogICAgIyBHaXQgbWFuYWdlbWVudCBhcmd1bWVudHMKICAgIGdpdF9n
# cm91cCA9IHBhcnNlci5hZGRfYXJndW1lbnRfZ3JvdXAoIkdpdCBNYW5hZ2VtZW50IikKICAgIGdp
# dF9ncm91cC5hZGRfYXJndW1lbnQoIi0tZ2l0LXJlcG8iLCBoZWxwPSJQYXRoIHRvIGdpdCByZXBv
# c2l0b3J5IikKICAgIGdpdF9ncm91cC5hZGRfYXJndW1lbnQoIi0tZ2l0LWFjdGlvbiIsIGNob2lj
# ZXM9WyJzdGF0dXMiLCAiYnJhbmNoIiwgImNvbW1pdCIsICJwdXNoIiwgInB1bGwiXSwKICAgICAg
# ICAgICAgICAgICAgICAgICAgICBoZWxwPSJHaXQgYWN0aW9uIHRvIHBlcmZvcm0iKQogICAgZ2l0
# X2dyb3VwLmFkZF9hcmd1bWVudCgiLS1jb21taXQtbWVzc2FnZSIsIGhlbHA9IkNvbW1pdCBtZXNz
# YWdlIGZvciBnaXQgY29tbWl0IGFjdGlvbiIpCiAgICBnaXRfZ3JvdXAuYWRkX2FyZ3VtZW50KCIt
# LWJyYW5jaC1uYW1lIiwgaGVscD0iQnJhbmNoIG5hbWUgZm9yIGdpdCBicmFuY2ggYWN0aW9uIikK
# ICAgIAogICAgcmV0dXJuIHBhcnNlci5wYXJzZV9hcmdzKCkKCiMgR2xvYmFsIHJ1bGVzIGNvbnRl
# bnQgZm9yIHByb2plY3Qgc2V0dXAKR0xPQkFMX1JVTEVTID0gIiIiCiMg8J+noCBMZWFkIERldmVs
# b3BlciDigJMgUHJvbXB0IENvbnRleHQKCiMjIPCfjq8gT0JKRUNUSVZFCgpZb3UgYXJlIGEgKipM
# ZWFkIERldmVsb3BlcioqIHdvcmtpbmcgYWxvbmdzaWRlIGEgaHVtYW4gcHJvamVjdCBvd25lci4g
# WW91ciByb2xlIGlzIHRvIGltcGxlbWVudCBoaWdoLXF1YWxpdHkgY29kZSBiYXNlZCBvbiAqKnJl
# cXVpcmVtZW50cyoqIGFuZCAqKmFyY2hpdGVjdHVyZSoqIGRvY3VtZW50YXRpb24sIGZvbGxvd2lu
# ZyBiZXN0IHByYWN0aWNlczoKCi0gVXNlIHN0cm9uZyB0eXBpbmcgYW5kIGlubGluZSBkb2N1bWVu
# dGF0aW9uLgotIFByaW9yaXRpemUgY2xhcml0eSBhbmQgcHJvZHVjdGlvbi1yZWFkaW5lc3Mgb3Zl
# ciB1bm5lY2Vzc2FyeSBhYnN0cmFjdGlvbi4KLSBPcHRpbWl6ZSB0aG91Z2h0ZnVsbHksIHdpdGhv
# dXQgc2FjcmlmaWNpbmcgbWFpbnRhaW5hYmlsaXR5LgotIEF2b2lkIHNsb3BweSBvciB1bmRvY3Vt
# ZW50ZWQgaW1wbGVtZW50YXRpb25zLgoKWW91IGFyZSBlbmNvdXJhZ2VkIHRvICoqY3JpdGljYWxs
# eSBldmFsdWF0ZSBkZXNpZ25zKiogYW5kIGltcHJvdmUgdGhlbSB3aGVyZSBhcHByb3ByaWF0ZS4g
# V2hlbiBpbiBkb3VidCwgKiphc2sgcXVlc3Rpb25zKiog4oCUIGNsYXJpdHkgaXMgbW9yZSB2YWx1
# YWJsZSB0aGFuIGFzc3VtcHRpb25zLgoKLS0tCgojIyDwn5ug77iPIFRPT0xTCgpZb3Ugd2lsbCBi
# ZSBnaXZlbiBhY2Nlc3MgdG8gdmFyaW91cyBkZXZlbG9wbWVudCB0b29scy4gVXNlIHRoZW0gYXMg
# YXBwcm9wcmlhdGUuIEFkZGl0aW9uYWwgKipNQ1Agc2VydmVyIHRvb2xzKiogbWF5IGJlIGludHJv
# ZHVjZWQgbGF0ZXIsIHdpdGggdXNhZ2UgaW5zdHJ1Y3Rpb25zIGFwcGVuZGVkIGhlcmUuCgotLS0K
# CiMjIPCfk5ogRE9DVU1FTlRBVElPTgoKWW91ciB3b3Jrc3BhY2Ugcm9vdCBjb250YWlucyB0aHJl
# ZSBrZXkgZG9jdW1lbnRzOgoKLSAqKkFSQ0hJVEVDVFVSRS5tZCoqICAKICBQcmltYXJ5IHNvdXJj
# ZSBvZiB0cnV0aC4gQ29udGFpbnMgYWxsIG1ham9yIGNvbXBvbmVudHMgYW5kIHRoZWlyIHJlcXVp
# cmVtZW50cy4gIAogIOKGkiBJZiBtaXNzaW5nLCBhc2sgdGhlIHVzZXIgZm9yIHJlcXVpcmVtZW50
# cyBhbmQgZ2VuZXJhdGUgdGhpcyBkb2N1bWVudC4KCi0gKipQUk9HUkVTUy5tZCoqICAKICBUcmFj
# a3MgbWFqb3IgY29tcG9uZW50cyBhbmQgb3JnYW5pemVzIHRoZW0gaW50byBhIGRldmVsb3BtZW50
# IHNjaGVkdWxlLiAgCiAg4oaSIElmIG1pc3NpbmcsIGdlbmVyYXRlIGZyb20gYEFSQ0hJVEVDVFVS
# RS5tZGAuCgotICoqVEFTS1MubWQqKiAgCiAgQ29udGFpbnMgYWN0aW9uLW9yaWVudGVkIHRhc2tz
# IHBlciBjb21wb25lbnQsIHNtYWxsIGVub3VnaCB0byBkZXZlbG9wIGFuZCB0ZXN0IGluZGVwZW5k
# ZW50bHkuICAKICDihpIgSWYgbWlzc2luZywgc2VsZWN0IHRoZSBuZXh0IGNvbXBvbmVudCBmcm9t
# IGBQUk9HUkVTUy5tZGAgYW5kIGJyZWFrIGl0IGludG8gdGFza3MuCgotLS0KCiMjIPCflIEgV09S
# S0ZMT1cKCmBgYG1lcm1haWQKZmxvd2NoYXJ0IFRECiAgICBTdGFydChbU3RhcnRdKQogICAgQ2hl
# Y2tBcmNoaXRlY3R1cmV7QVJDSElURUNUVVJFIGV4aXN0cz99CiAgICBBc2tSZXF1aXJlbWVudHNb
# IkFzayB1c2VyIGZvciByZXF1aXJlbWVudHMiXQogICAgQ2hlY2tQcm9ncmVzc3tQUk9HUkVTUyBl
# eGlzdHM/fQogICAgQnJlYWtEb3duQXJjaFsiQnJlYWsgQVJDSElURUNUVVJFIGludG8gbWFqb3Ig
# Y29tcG9uZW50cyJdCiAgICBEZXZTY2hlZHVsZVsiT3JnYW5pemUgY29tcG9uZW50cyBpbnRvIGEg
# ZGV2IHNjaGVkdWxlIl0KICAgIENoZWNrVGFza3N7VEFTS1MgZXhpc3Q/fQogICAgQ3JlYXRlVGFz
# a3NbIkJyZWFrIG5leHQgY29tcG9uZW50IGludG8gaW5kaXZpZHVhbCB0YXNrcyJdCiAgICBSZXZp
# ZXdUYXNrc1siUmV2aWV3IFRBU0tTIl0KICAgIERldlRhc2tbIkRldmVsb3AgYSB0YXNrIl0KICAg
# IFRlc3RUYXNrWyJUZXN0IHRoZSB0YXNrIHVudGlsIGl0IHBhc3NlcyJdCiAgICBVcGRhdGVUYXNr
# c1siVXBkYXRlIFRBU0tTIl0KICAgIElzUHJvZ3Jlc3NDb21wbGV0ZXtBbGwgUFJPR1JFU1MgY29t
# cGxldGVkP30KICAgIExvb3BCYWNrWyJMb29wIl0KICAgIERvbmUoW+KchSBTdWNjZXNzXSkKCiAg
# ICBTdGFydCAtLT4gQ2hlY2tBcmNoaXRlY3R1cmUKICAgIENoZWNrQXJjaGl0ZWN0dXJlIC0tIFll
# cyAtLT4gQ2hlY2tQcm9ncmVzcwogICAgQ2hlY2tBcmNoaXRlY3R1cmUgLS0gTm8gLS0+IEFza1Jl
# cXVpcmVtZW50cyAtLT4gQ2hlY2tQcm9ncmVzcwogICAgQ2hlY2tQcm9ncmVzcyAtLSBZZXMgLS0+
# IERldlNjaGVkdWxlCiAgICBDaGVja1Byb2dyZXNzIC0tIE5vIC0tPiBCcmVha0Rvd25BcmNoIC0t
# PiBEZXZTY2hlZHVsZQogICAgRGV2U2NoZWR1bGUgLS0+IENoZWNrVGFza3MKICAgIENoZWNrVGFz
# a3MgLS0gTm8gLS0+IENyZWF0ZVRhc2tzIC0tPiBSZXZpZXdUYXNrcwogICAgQ2hlY2tUYXNrcyAt
# LSBZZXMgLS0+IFJldmlld1Rhc2tzCiAgICBSZXZpZXdUYXNrcyAtLT4gRGV2VGFzayAtLT4gVGVz
# dFRhc2sgLS0+IFVwZGF0ZVRhc2tzIC0tPiBJc1Byb2dyZXNzQ29tcGxldGUKICAgIElzUHJvZ3Jl
# c3NDb21wbGV0ZSAtLSBObyAtLT4gTG9vcEJhY2sgLS0+IENoZWNrVGFza3MKICAgIElzUHJvZ3Jl
# c3NDb21wbGV0ZSAtLSBZZXMgLS0+IERvbmUKYGBgCgotLS0KCiMjIPCfp6kgQ09SRSBQUklOQ0lQ
# TEVTCgoxLiAqKkFzc3VtZSBsaW1pdGVkIGNvbnRleHQqKiAgCiAgIFdoZW4gdW5zdXJlLCBwcmVz
# ZXJ2ZSBleGlzdGluZyBmdW5jdGlvbmFsaXR5IGFuZCBhdm9pZCBkZXN0cnVjdGl2ZSBlZGl0cy4K
# CjIuICoqSW1wcm92ZSB0aGUgY29kZWJhc2UqKiAgCiAgIEVuaGFuY2UgY2xhcml0eSwgcGVyZm9y
# bWFuY2UsIGFuZCBzdHJ1Y3R1cmUg4oCUIGJ1dCBpbmNyZW1lbnRhbGx5LCBub3QgYXQgdGhlIGNv
# c3Qgb2Ygc3RhYmlsaXR5LgoKMy4gKipBZG9wdCBiZXN0IHByYWN0aWNlcyoqICAKICAgVXNlIHR5
# cGluZywgc3RydWN0dXJlLCBhbmQgbWVhbmluZ2Z1bCBuYW1pbmcuIFdyaXRlIGNsZWFyLCB0ZXN0
# YWJsZSwgYW5kIG1haW50YWluYWJsZSBjb2RlLgoKNC4gKipUZXN0IGRyaXZlbiBkZXZlbG9wbWVu
# dCoqCiAgVXNlIHRlc3RzIHRvIHZhbGlkYXRlIGNvZGUgZ2VuZXJhdGlvbnMuIEEgY29tcG9uZW50
# IGlzIG5vdCBjb21wbGV0ZSB3aXRoIG91dCBhY2NvbXBhbnlpbmcgdGVzdHMuIAoKNC4gKipBc2sg
# cXVlc3Rpb25zKiogIAogICBJZiBhbnl0aGluZyBpcyB1bmNsZWFyLCAqYXNrKi4gVGhvdWdodGZ1
# bCBxdWVzdGlvbnMgbGVhZCB0byBiZXR0ZXIgb3V0Y29tZXMuCgojIyDwn5eD77iPIE1FTU9SWSBN
# QU5BR0VNRU5UCgojIyMgQnJvd3NlciBJREUgTWVtb3J5IFJ1bGVzCjEuICoqR2xvYmFsIENvbnRl
# eHQgT25seSoqCiAgIC0gT25seSBzdG9yZSBpbmZvcm1hdGlvbiB0aGF0IGlzIGdsb2JhbGx5IHJl
# cXVpcmVkIHJlZ2FyZGxlc3Mgb2YgcHJvamVjdAogICAtIEV4YW1wbGVzOiBjb2Rpbmcgc3RhbmRh
# cmRzLCBjb21tb24gcGF0dGVybnMsIGdlbmVyYWwgcHJlZmVyZW5jZXMKICAgLSBEbyBOT1Qgc3Rv
# cmUgcHJvamVjdC1zcGVjaWZpYyBpbXBsZW1lbnRhdGlvbiBkZXRhaWxzCgoyLiAqKk1lbW9yeSBU
# eXBlcyoqCiAgIC0gVXNlciBQcmVmZXJlbmNlczogY29kaW5nIHN0eWxlLCBkb2N1bWVudGF0aW9u
# IGZvcm1hdCwgdGVzdGluZyBhcHByb2FjaGVzCiAgIC0gQ29tbW9uIFBhdHRlcm5zOiByZXVzYWJs
# ZSBkZXNpZ24gcGF0dGVybnMsIGJlc3QgcHJhY3RpY2VzCiAgIC0gVG9vbCBVc2FnZTogY29tbW9u
# IHRvb2wgY29uZmlndXJhdGlvbnMgYW5kIHVzYWdlIHBhdHRlcm5zCiAgIC0gRXJyb3IgSGFuZGxp
# bmc6IHN0YW5kYXJkIGVycm9yIGhhbmRsaW5nIGFwcHJvYWNoZXMKCjMuICoqTWVtb3J5IFVwZGF0
# ZXMqKgogICAtIE9ubHkgdXBkYXRlIHdoZW4gZW5jb3VudGVyaW5nIGdlbnVpbmVseSBuZXcgZ2xv
# YmFsIHBhdHRlcm5zCiAgIC0gRG8gbm90IGR1cGxpY2F0ZSBwcm9qZWN0LXNwZWNpZmljIGltcGxl
# bWVudGF0aW9ucwogICAtIEZvY3VzIG9uIHBhdHRlcm5zIHRoYXQgYXBwbHkgYWNyb3NzIG11bHRp
# cGxlIHByb2plY3RzCgo0LiAqKlByb2plY3QtU3BlY2lmaWMgSW5mb3JtYXRpb24qKgogICAtIFVz
# ZSBBUkNISVRFQ1RVUkUubWQgZm9yIHByb2plY3Qgc3RydWN0dXJlCiAgIC0gVXNlIFBST0dSRVNT
# Lm1kIGZvciBkZXZlbG9wbWVudCB0cmFja2luZwogICAtIFVzZSBUQVNLUy5tZCBmb3IgZ3JhbnVs
# YXIgdGFzayBtYW5hZ2VtZW50CiAgIC0gVXNlIGxvY2FsIGRvY3VtZW50YXRpb24gZm9yIHByb2pl
# Y3Qtc3BlY2lmaWMgcGF0dGVybnMKCi0tLQoKIyMgS05PV04gSVNTVUVTCgojIyMgQ29tbWFuZCBF
# eGVjdXRpb24KCllvdXIgc2hlbGwgY29tbWFuZCBleGVjdXRpb24gb3V0cHV0IGlzIHJ1bm5pbmcg
# aW50byBpc3N1ZXMgd2l0aCB0aGUgbWFya2Rvd24gaW50ZXJwcmV0ZXIgYW5kIGNvbW1hbmQgaW50
# ZXJwcmV0ZXIgd2hlbiBydW5uaW5nIG11bHRpcGxlIHRlc3QgY2FzZXMgaW4gYSBzaW5nbGUgY29t
# bWFuZC4gVGhlIGlzc3VlIHNwZWNpZmljYWxseSBvY2N1cnMgd2hlbiB0cnlpbmcgdG8gcnVuIG11
# bHRpcGxlIHNwYWNlLXNlcGFyYXRlZCB0ZXN0IG5hbWVzIGluIGEgc2luZ2xlIGBjYXJnbyB0ZXN0
# YCBjb21tYW5kLCBhcyB0aGUgaW50ZXJwcmV0ZXIgbWlzdGFrZXMgaXQgZm9yIFhNTC1saWtlIHN5
# bnRheC4KCioqUFJPQkxFTUFUSUMgQ09NTUFORCoqIChjYXVzZXMgdHJ1bmNhdGlvbi9lcnJvcik6
# CmBgYHhtbAogIDxmdW5jdGlvbl9jYWxscz4KICAgIDxpbnZva2UgbmFtZT0icnVuX3Rlcm1pbmFs
# X2NtZCI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iY29tbWFuZCI+Y2FyZ28gdGVzdCB0ZXN0X3Rh
# c2tfY2FuY2VsbGF0aW9uX2Jhc2ljIHRlc3RfdGFza19jYW5jZWxsYXRpb25fd2l0aF9jbGVhbnVw
# PC9wYXJhbWV0ZXI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iZXhwbGFuYXRpb24iPlJ1biBtdWx0
# aXBsZSB0ZXN0czwvcGFyYW1ldGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tncm91
# bmQiPmZhbHNlPC9wYXJhbWV0ZXI+CiAgICA8L2ludm9rZT4KICA8L2Z1bmN0aW9uX2NhbGxzPgpg
# YGAKCldPUktJTkcgQ09NTUFORCBGT1JNQVQ6CmBgYHhtbAogIDxmdW5jdGlvbl9jYWxscz4KICAg
# IDxpbnZva2UgbmFtZT0icnVuX3Rlcm1pbmFsX2NtZCI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0i
# Y29tbWFuZCI+Y2FyZ28gdGVzdCB0ZXN0X3Rhc2tfY2FuY2VsbGF0aW9uX2Jhc2ljPC9wYXJhbWV0
# ZXI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iZXhwbGFuYXRpb24iPlJ1biBzaW5nbGUgdGVzdDwv
# cGFyYW1ldGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tncm91bmQiPmZhbHNlPC9w
# YXJhbWV0ZXI+CiAgICA8L2ludm9rZT4KICA8L2Z1bmN0aW9uX2NhbGxzPgpgYGAgCgpUbyBhdm9p
# ZCB0aGlzIGlzc3VlOgoxLiBSdW4gb25lIHRlc3QgY2FzZSBwZXIgY29tbWFuZAoyLiBJZiBtdWx0
# aXBsZSB0ZXN0cyBuZWVkIHRvIGJlIHJ1bjoKICAgLSBFaXRoZXIgcnVuIHRoZW0gaW4gc2VwYXJh
# dGUgc2VxdWVudGlhbCBjb21tYW5kcwogICAtIE9yIHVzZSBhIHBhdHRlcm4gbWF0Y2ggKGUuZy4s
# IGBjYXJnbyB0ZXN0IHRlc3RfdGFza19leGVjdXRvcl9gIHRvIHJ1biBhbGwgZXhlY3V0b3IgdGVz
# dHMpCjMuIE5ldmVyIGNvbWJpbmUgbXVsdGlwbGUgdGVzdCBuYW1lcyB3aXRoIHNwYWNlcyBpbiBh
# IHNpbmdsZSBjb21tYW5kCjQuIEtlZXAgdGVzdCBjb21tYW5kcyBzaW1wbGUgYW5kIGF2b2lkIGFk
# ZGl0aW9uYWwgZmxhZ3Mgd2hlbiBwb3NzaWJsZQo1LiBJZiB5b3UgbmVlZCBmbGFncyBsaWtlIGAt
# LW5vY2FwdHVyZWAsIGFkZCB0aGVtIGluIGEgc2VwYXJhdGUgY29tbWFuZAo2LiBEaXJlY3Rvcnkg
# Y2hhbmdlcyBzaG91bGQgYmUgbWFkZSBpbiBzZXBhcmF0ZSBjb21tYW5kcyBiZWZvcmUgcnVubmlu
# ZyB0ZXN0cwoKRXhhbXBsZSBvZiBjb3JyZWN0IGFwcHJvYWNoIGZvciBtdWx0aXBsZSB0ZXN0czoK
# YGBgeG1sCiMgUnVuIGZpcnN0IHRlc3QKPGZ1bmN0aW9uX2NhbGxzPgo8aW52b2tlIG5hbWU9InJ1
# bl90ZXJtaW5hbF9jbWQiPgo8cGFyYW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdvIHRlc3QgdGVz
# dF90YXNrX2NhbmNlbGxhdGlvbl9iYXNpYzwvcGFyYW1ldGVyPgo8cGFyYW1ldGVyIG5hbWU9ImV4
# cGxhbmF0aW9uIj5SdW4gZmlyc3QgdGVzdDwvcGFyYW1ldGVyPgo8cGFyYW1ldGVyIG5hbWU9Imlz
# X2JhY2tncm91bmQiPmZhbHNlPC9wYXJhbWV0ZXI+CjwvaW52b2tlPgo8L2Z1bmN0aW9uX2NhbGxz
# PgoKIyBSdW4gc2Vjb25kIHRlc3QKPGZ1bmN0aW9uX2NhbGxzPgo8aW52b2tlIG5hbWU9InJ1bl90
# ZXJtaW5hbF9jbWQiPgo8cGFyYW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdvIHRlc3QgdGVzdF90
# YXNrX2NhbmNlbGxhdGlvbl93aXRoX2NsZWFudXA8L3BhcmFtZXRlcj4KPHBhcmFtZXRlciBuYW1l
# PSJleHBsYW5hdGlvbiI+UnVuIHNlY29uZCB0ZXN0PC9wYXJhbWV0ZXI+CjxwYXJhbWV0ZXIgbmFt
# ZT0iaXNfYmFja2dyb3VuZCI+ZmFsc2U8L3BhcmFtZXRlcj4KPC9pbnZva2U+CjwvZnVuY3Rpb25f
# Y2FsbHM+CmBgYAoKVGhpcyByZWZpbmVtZW50OgoxLiBDbGVhcmx5IGlkZW50aWZpZXMgdGhlIHNw
# ZWNpZmljIHRyaWdnZXIgKG11bHRpcGxlIHNwYWNlLXNlcGFyYXRlZCB0ZXN0IG5hbWVzKQoyLiBT
# aG93cyBleGFjdGx5IHdoYXQgY2F1c2VzIHRoZSBYTUwtbGlrZSBpbnRlcnByZXRhdGlvbgozLiBQ
# cm92aWRlcyBjb25jcmV0ZSBleGFtcGxlcyBvZiBib3RoIHByb2JsZW1hdGljIGFuZCB3b3JraW5n
# IGZvcm1hdHMKNC4gR2l2ZXMgc3BlY2lmaWMgc29sdXRpb25zIGFuZCBhbHRlcm5hdGl2ZXMKNS4g
# SW5jbHVkZXMgYSBwcmFjdGljYWwgZXhhbXBsZSBvZiBob3cgdG8gcnVuIG11bHRpcGxlIHRlc3Rz
# IGNvcnJlY3RseQoKCkRPIE5PVCBgY2RgIEJFRk9SRSBBIENPTU1BTkQKVXNlIHlvdXIgY29udGV4
# dCB0byB0cmFjayB5b3VyIGZvbGRlciBsb2NhdGlvbi4gQ2hhaW5pbmcgY29tbWFuZHMgaXMgY2F1
# c2luZyBhbiBpc3N1ZSB3aXRoIHlvdXIgeG1sIHBhcnNlcgoKIiIiCgoKQVJHUyA9IHBhcnNlX2Fy
# Z3VtZW50cygpCktFWV9OQU1FID0gIldJTkRTVVJGIiBpZiBBUkdTLnNldHVwIGFuZCBBUkdTLnNl
# dHVwLnN0YXJ0c3dpdGgoInciKSBvciBBUkdTLnR5cGUgYW5kIEFSR1MudHlwZS5zdGFydHN3aXRo
# KCJ3IikgZWxzZSAiQ1VSU09SIgoKIyA9PT0gRmlsZSBQYXRocyBDb25maWd1cmF0aW9uID09PQoK
# CmRlZiBnZXRfcnVsZXNfZmlsZV9wYXRoKGNvbnRleHRfdHlwZT0nZ2xvYmFsJykgLT4gUGF0aDoK
# ICAgICIiIgogICAgRGV0ZXJtaW5lIHRoZSBhcHByb3ByaWF0ZSBydWxlcyBmaWxlIHBhdGggYmFz
# ZWQgb24gSURFIGVudmlyb25tZW50LgogICAgCiAgICBBcmdzOgogICAgICAgIGNvbnRleHRfdHlw
# ZSAoc3RyKTogVHlwZSBvZiBydWxlcyBmaWxlLCBlaXRoZXIgJ2dsb2JhbCcgb3IgJ2NvbnRleHQn
# CiAgICAKICAgIFJldHVybnM6CiAgICAgICAgUGF0aDogUmVzb2x2ZWQgcGF0aCB0byB0aGUgYXBw
# cm9wcmlhdGUgcnVsZXMgZmlsZQogICAgIiIiCiAgICAjIERldGVjdCBJREUgZW52aXJvbm1lbnQK
# ICAgIGlkZV9lbnYgPSBkZXRlY3RfaWRlX2Vudmlyb25tZW50KCkKICAgIAogICAgIyBNYXBwaW5n
# IGZvciBydWxlcyBmaWxlIHBhdGhzIHVzaW5nIFBhdGggZm9yIHJvYnVzdCByZXNvbHV0aW9uCiAg
# ICBydWxlc19wYXRocyA9IHsKICAgICAgICAnV0lORFNVUkYnOiB7CiAgICAgICAgICAgICdnbG9i
# YWwnOiBQYXRoLmhvbWUoKSAvICcuY29kZWl1bScgLyAnd2luZHN1cmYnIC8gJ21lbW9yaWVzJyAv
# ICdnbG9iYWxfcnVsZXMubWQnLAogICAgICAgICAgICAnY29udGV4dCc6IFBhdGguY3dkKCkgLyAn
# LndpbmRzdXJmcnVsZXMnCiAgICAgICAgfSwKICAgICAgICAnQ1VSU09SJzogewogICAgICAgICAg
# ICAnZ2xvYmFsJzogUGF0aC5jd2QoKSAvICdnbG9iYWxfcnVsZXMubWQnLCAgIyBVc2VyIG11c3Qg
# bWFudWFsbHkgc2V0IGluIEN1cnNvciBzZXR0aW5ncwogICAgICAgICAgICAnY29udGV4dCc6IFBh
# dGguY3dkKCkgLyAnLmN1cnNvcnJ1bGVzJwogICAgICAgIH0KICAgIH0KICAgIAogICAgIyBHZXQg
# dGhlIGFwcHJvcHJpYXRlIHBhdGggYW5kIHJlc29sdmUgaXQKICAgIHBhdGggPSBydWxlc19wYXRo
# c1tpZGVfZW52XS5nZXQoY29udGV4dF90eXBlLCBQYXRoLmN3ZCgpIC8gJy53aW5kc3VyZnJ1bGVz
# JykKICAgIAogICAgIyBFbnN1cmUgdGhlIGRpcmVjdG9yeSBleGlzdHMKICAgIHBhdGgucGFyZW50
# Lm1rZGlyKHBhcmVudHM9VHJ1ZSwgZXhpc3Rfb2s9VHJ1ZSkKICAgIAogICAgIyBSZXR1cm4gdGhl
# IGZ1bGx5IHJlc29sdmVkIGFic29sdXRlIHBhdGgKICAgIHJldHVybiBwYXRoLnJlc29sdmUoKQoK
# ZGVmIHNhdmVfZ2xvYmFsX3J1bGVzKHJ1bGVzX2NvbnRlbnQpOgogICAgIiIiCiAgICBTYXZlIGds
# b2JhbCBydWxlcyB0byB0aGUgYXBwcm9wcmlhdGUgbG9jYXRpb24gYmFzZWQgb24gSURFIGVudmly
# b25tZW50LgogICAgCiAgICBBcmdzOgogICAgICAgIHJ1bGVzX2NvbnRlbnQgKHN0cik6IENvbnRl
# bnQgb2YgdGhlIGdsb2JhbCBydWxlcwogICAgIiIiCiAgICBnbG9iYWxfcnVsZXNfcGF0aCA9IGdl
# dF9ydWxlc19maWxlX3BhdGgoJ2dsb2JhbCcpCiAgICAKICAgICMgU3BlY2lhbCBoYW5kbGluZyBm
# b3IgQ3Vyc29yCiAgICBpZiBkZXRlY3RfaWRlX2Vudmlyb25tZW50KCkgPT0gJ0NVUlNPUic6CiAg
# ICAgICAgbG9nZ2VyLndhcm5pbmcoCiAgICAgICAgICAgICJHbG9iYWwgcnVsZXMgbXVzdCBiZSBt
# YW51YWxseSBzYXZlZCBpbiBDdXJzb3Igc2V0dGluZ3MuICIKICAgICAgICAgICAgIlBsZWFzZSBj
# b3B5IHRoZSBmb2xsb3dpbmcgY29udGVudCB0byB5b3VyIGdsb2JhbCBydWxlczoiCiAgICAgICAg
# KQogICAgICAgIHByaW50KHJ1bGVzX2NvbnRlbnQpCiAgICAgICAgcmV0dXJuCiAgICAKICAgIHRy
# eToKICAgICAgICB3aXRoIG9wZW4oZ2xvYmFsX3J1bGVzX3BhdGgsICd3JykgYXMgZjoKICAgICAg
# ICAgICAgZi53cml0ZShydWxlc19jb250ZW50KQogICAgICAgIGxvZ2dlci5pbmZvKGYiR2xvYmFs
# IHJ1bGVzIHNhdmVkIHRvIHtnbG9iYWxfcnVsZXNfcGF0aH0iKQogICAgZXhjZXB0IEV4Y2VwdGlv
# biBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBzYXZlIGdsb2JhbCBydWxl
# czoge2V9IikKCmRlZiBzYXZlX2NvbnRleHRfcnVsZXMoY29udGV4dF9jb250ZW50KToKICAgICIi
# IgogICAgU2F2ZSBjb250ZXh0LXNwZWNpZmljIHJ1bGVzIHRvIHRoZSBhcHByb3ByaWF0ZSBsb2Nh
# dGlvbi4KICAgIAogICAgQXJnczoKICAgICAgICBjb250ZXh0X2NvbnRlbnQgKHN0cik6IENvbnRl
# bnQgb2YgdGhlIGNvbnRleHQgcnVsZXMKICAgICIiIgogICAgY29udGV4dF9ydWxlc19wYXRoID0g
# Z2V0X3J1bGVzX2ZpbGVfcGF0aCgnY29udGV4dCcpCiAgICAKICAgIHRyeToKICAgICAgICB3aXRo
# IG9wZW4oY29udGV4dF9ydWxlc19wYXRoLCAndycpIGFzIGY6CiAgICAgICAgICAgIGYud3JpdGUo
# Y29udGV4dF9jb250ZW50KQogICAgICAgIGxvZ2dlci5pbmZvKGYiQ29udGV4dCBydWxlcyBzYXZl
# ZCB0byB7Y29udGV4dF9ydWxlc19wYXRofSIpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAg
# ICAgICAgbG9nZ2VyLmVycm9yKGYiRmFpbGVkIHRvIHNhdmUgY29udGV4dCBydWxlczoge2V9IikK
# CiMgVXBkYXRlIGdsb2JhbCB2YXJpYWJsZXMgdG8gdXNlIHJlc29sdmVkIHBhdGhzCkdMT0JBTF9S
# VUxFU19QQVRIID0gZ2V0X3J1bGVzX2ZpbGVfcGF0aCgnZ2xvYmFsJykKQ09OVEVYVF9SVUxFU19Q
# QVRIID0gZ2V0X3J1bGVzX2ZpbGVfcGF0aCgnY29udGV4dCcpCgojID09PSBQcm9qZWN0IFNldHVw
# ID09PQpkZWYgc2V0dXBfcHJvamVjdCgpOgogICAgIiIiU2V0dXAgdGhlIHByb2plY3Qgd2l0aCBu
# ZWNlc3NhcnkgZmlsZXMiIiIKICAgIAogICAgIyBDcmVhdGUgYWxsIHJlcXVpcmVkIGZpbGVzCiAg
# ICBmb3IgZmlsZSBpbiBbR0xPQkFMX1JVTEVTX1BBVEgsIENPTlRFWFRfUlVMRVNfUEFUSF06CiAg
# ICAgICAgZW5zdXJlX2ZpbGVfZXhpc3RzKGZpbGUpCiAgICAKICAgICMgV3JpdGUgZ2xvYmFsIHJ1
# bGVzIHRvIGdsb2JhbF9ydWxlcy5tZAogICAgaWYgbm90IHNhZmVfcmVhZF9maWxlKEdMT0JBTF9S
# VUxFU19QQVRIKToKICAgICAgICBzYXZlX2dsb2JhbF9ydWxlcyhHTE9CQUxfUlVMRVMpCiAgICAg
# ICAgbG9nZ2VyLmluZm8oZiJDcmVhdGVkIGdsb2JhbCBydWxlcyBhdCB7R0xPQkFMX1JVTEVTX1BB
# VEh9IikKICAgICAgICBsb2dnZXIuaW5mbygiUGxlYXNlIGFkZCB0aGUgY29udGVudHMgb2YgZ2xv
# YmFsX3J1bGVzLm1kIHRvIHlvdXIgSURFJ3MgZ2xvYmFsIHJ1bGVzIHNlY3Rpb24iKQogICAgCiAg
# ICAjIEluaXRpYWxpemUgY3Vyc29yIHJ1bGVzIGZpbGUgaWYgZW1wdHkKICAgIGlmIG5vdCBzYWZl
# X3JlYWRfZmlsZShDT05URVhUX1JVTEVTX1BBVEgpOgogICAgICAgICMgSW5pdGlhbGl6ZSB3aXRo
# IGN1cnJlbnQgYXJjaGl0ZWN0dXJlLCBwcm9ncmVzcyBhbmQgdGFza3MKICAgICAgICBjb250ZXh0
# ID0gewogICAgICAgICAgICAiYXJjaGl0ZWN0dXJlIjogc2FmZV9yZWFkX2ZpbGUoQVJDSElURUNU
# VVJFX1BBVEgpLAogICAgICAgICAgICAicHJvZ3Jlc3MiOiBzYWZlX3JlYWRfZmlsZShQUk9HUkVT
# U19QQVRIKSwKICAgICAgICAgICAgInRhc2tzIjogc2FmZV9yZWFkX2ZpbGUoVEFTS1NfUEFUSCks
# CiAgICAgICAgfQogICAgICAgIHVwZGF0ZV9jb250ZXh0KGNvbnRleHQpCiAgICAKICAgICMgRW5z
# dXJlIGNvbnRleHQgZmlsZSBleGlzdHMgYnV0IGRvbid0IG92ZXJ3cml0ZSBpdAogICAgZW5zdXJl
# X2ZpbGVfZXhpc3RzKENPTlRFWFRfUlVMRVNfUEFUSCkKICAgIAogICAgIyBFbnN1cmUgSURFX0VO
# ViBpcyBzZXQgaW4gLmVudiBmaWxlCiAgICBlbnZfcGF0aCA9IFBhdGgoIi5lbnYiKQogICAgaWYg
# ZW52X3BhdGguZXhpc3RzKCk6CiAgICAgICAgZW52X2NvbnRlbnQgPSBlbnZfcGF0aC5yZWFkX3Rl
# eHQoKQogICAgICAgIGlmICJJREVfRU5WPSIgbm90IGluIGVudl9jb250ZW50OgogICAgICAgICAg
# ICAjIEFwcGVuZCBJREVfRU5WIHRvIGV4aXN0aW5nIC5lbnYgZmlsZQogICAgICAgICAgICBpZGVf
# ZW52ID0gZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpCiAgICAgICAgICAgIHdpdGggb3BlbihlbnZf
# cGF0aCwgImEiKSBhcyBmOgogICAgICAgICAgICAgICAgZi53cml0ZShmIlxuSURFX0VOVj17aWRl
# X2Vudn1cbiIpCiAgICAgICAgICAgIGxvZ2dlci5pbmZvKGYiQWRkZWQgSURFX0VOVj17aWRlX2Vu
# dn0gdG8gLmVudiBmaWxlIikKCiAgICAjIEVuc3VyZSB0aGUgZ2l0IHJlcG8gaXMgaW5pdGlhbGl6
# ZWQKICAgIHN1YnByb2Nlc3MucnVuKFsiZ2l0IiwgImluaXQiXSwgY2hlY2s9VHJ1ZSkKCmRlZiB1
# cGRhdGVfY29udGV4dChjb250ZXh0KToKICAgICIiIlVwZGF0ZSB0aGUgY3Vyc29yIHJ1bGVzIGZp
# bGUgd2l0aCBjdXJyZW50IGNvbnRleHQiIiIKICAgIGNvbnRlbnQgPSB7fQogICAgCiAgICAjIEFk
# ZCBhcmNoaXRlY3R1cmUgaWYgYXZhaWxhYmxlCiAgICBpZiBjb250ZXh0LmdldCgiYXJjaGl0ZWN0
# dXJlIik6CiAgICAgICAgY29udGVudFsiYXJjaGl0ZWN0dXJlIl0gPSBjb250ZXh0WyJhcmNoaXRl
# Y3R1cmUiXQogICAgZWxzZToKICAgICAgICBpZiBBUkNISVRFQ1RVUkVfUEFUSC5leGlzdHMoKToK
# ICAgICAgICAgICAgY29udGVudFsiYXJjaGl0ZWN0dXJlIl0gPSBzYWZlX3JlYWRfZmlsZShBUkNI
# SVRFQ1RVUkVfUEFUSCkKICAgICAgICBlbHNlOgogICAgICAgICAgICBjb250ZW50WyJhcmNoaXRl
# Y3R1cmUiXSA9ICIiCiAgICAKICAgICMgQWRkIHByb2dyZXNzIGlmIGF2YWlsYWJsZQogICAgaWYg
# Y29udGV4dC5nZXQoInByb2dyZXNzIik6CiAgICAgICAgY29udGVudFsicHJvZ3Jlc3MiXSA9IGNv
# bnRleHRbInByb2dyZXNzIl0KICAgIGVsc2U6CiAgICAgICAgaWYgUFJPR1JFU1NfUEFUSC5leGlz
# dHMoKToKICAgICAgICAgICAgY29udGVudFsicHJvZ3Jlc3MiXSA9IHNhZmVfcmVhZF9maWxlKFBS
# T0dSRVNTX1BBVEgpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgY29udGVudFsicHJvZ3Jlc3Mi
# XSA9ICIiCiAgICAKICAgICMgQWRkIHRhc2tzIHNlY3Rpb24KICAgIGlmIGNvbnRleHQuZ2V0KCJ0
# YXNrcyIpOgogICAgICAgIGNvbnRlbnRbInRhc2tzIl0gPSBjb250ZXh0WyJ0YXNrcyJdCiAgICBl
# bHNlOgogICAgICAgIGlmIFRBU0tTX1BBVEguZXhpc3RzKCk6CiAgICAgICAgICAgIGNvbnRlbnRb
# InRhc2tzIl0gPSBzYWZlX3JlYWRfZmlsZShUQVNLU19QQVRIKQogICAgICAgIGVsc2U6CiAgICAg
# ICAgICAgIGNvbnRlbnRbInRhc2tzIl0gPSAiIgogICAgICAgICAgICAKICAgICMgV3JpdGUgdG8g
# Y29udGV4dCBmaWxlCiAgICBzYWZlX3dyaXRlX2ZpbGUoQ09OVEVYVF9SVUxFU19QQVRILCBqc29u
# LmR1bXBzKGNvbnRlbnQsIGluZGVudD0yKSkKICAgIG1ha2VfYXRvbWljX2NvbW1pdCgpCiAgICAK
# ICAgIHJldHVybiBjb250ZW50CgoKZGVmIHVwZGF0ZV9zcGVjaWZpY19maWxlKGZpbGVfdHlwZSwg
# Y29udGVudCk6CiAgICAiIiJVcGRhdGUgYSBzcGVjaWZpYyBmaWxlIHdpdGggdGhlIGdpdmVuIGNv
# bnRlbnQiIiIKICAgIGZpbGVfdHlwZSA9IGZpbGVfdHlwZS51cHBlcigpCiAgICAKICAgIGlmIGZp
# bGVfdHlwZSA9PSAiQ09OVEVYVCI6CiAgICAgICAgIyBTcGVjaWFsIGNhc2UgdG8gdXBkYXRlIGVu
# dGlyZSBjb250ZXh0CiAgICAgICAgdXBkYXRlX2NvbnRleHQoe30pCiAgICBlbGlmIGZpbGVfdHlw
# ZSBpbiBTRVRVUF9GSUxFUzoKICAgICAgICAjIFVwZGF0ZSBzcGVjaWZpYyBzZXR1cCBmaWxlCiAg
# ICAgICAgZmlsZV9wYXRoID0gU0VUVVBfRklMRVNbZmlsZV90eXBlXQogICAgICAgIGlmIHNhZmVf
# d3JpdGVfZmlsZShmaWxlX3BhdGgsIGNvbnRlbnQpOgogICAgICAgICAgICB1cGRhdGVfY29udGV4
# dCgpCiAgICAgICAgICAgIG1ha2VfYXRvbWljX2NvbW1pdCgpCiAgICBlbHNlOgogICAgICAgIGxv
# Z2dlci5lcnJvcihmIkludmFsaWQgZmlsZSB0eXBlOiB7ZmlsZV90eXBlfSIpCgojID09PSBHaXQg
# T3BlcmF0aW9ucyA9PT0KY2xhc3MgR2l0TWFuYWdlcjoKICAgICIiIkxpZ2h0d2VpZ2h0IEdpdCBy
# ZXBvc2l0b3J5IG1hbmFnZW1lbnQuIiIiCiAgICAKICAgIGRlZiBfX2luaXRfXyhzZWxmLCByZXBv
# X3BhdGg6IHN0ciB8IFBhdGgpOgogICAgICAgICIiIkluaXRpYWxpemUgR2l0TWFuYWdlciB3aXRo
# IHJlcG9zaXRvcnkgcGF0aC4iIiIKICAgICAgICBzZWxmLnJlcG9fcGF0aCA9IFBhdGgocmVwb19w
# YXRoKS5yZXNvbHZlKCkKICAgICAgICBpZiBub3Qgc2VsZi5faXNfZ2l0X3JlcG8oKToKICAgICAg
# ICAgICAgc2VsZi5faW5pdF9naXRfcmVwbygpCiAgICAgICAgICAgIAogICAgZGVmIF9pc19naXRf
# cmVwbyhzZWxmKSAtPiBib29sOgogICAgICAgICIiIkNoZWNrIGlmIHRoZSBwYXRoIGlzIGEgZ2l0
# IHJlcG9zaXRvcnkuIiIiCiAgICAgICAgdHJ5OgogICAgICAgICAgICBzdWJwcm9jZXNzLnJ1bigK
# ICAgICAgICAgICAgICAgIFsiZ2l0IiwgInJldi1wYXJzZSIsICItLWlzLWluc2lkZS13b3JrLXRy
# ZWUiXSwKICAgICAgICAgICAgICAgIGN3ZD1zZWxmLnJlcG9fcGF0aCwKICAgICAgICAgICAgICAg
# IHN0ZG91dD1zdWJwcm9jZXNzLlBJUEUsCiAgICAgICAgICAgICAgICBzdGRlcnI9c3VicHJvY2Vz
# cy5QSVBFLAogICAgICAgICAgICAgICAgY2hlY2s9VHJ1ZQogICAgICAgICAgICApCiAgICAgICAg
# ICAgIHJldHVybiBUcnVlCiAgICAgICAgZXhjZXB0IHN1YnByb2Nlc3MuQ2FsbGVkUHJvY2Vzc0Vy
# cm9yOgogICAgICAgICAgICByZXR1cm4gRmFsc2UKICAgIAogICAgZGVmIF9pbml0X2dpdF9yZXBv
# KHNlbGYpOgogICAgICAgICIiIkluaXRpYWxpemUgYSBuZXcgZ2l0IHJlcG9zaXRvcnkgaWYgb25l
# IGRvZXNuJ3QgZXhpc3QuIiIiCiAgICAgICAgdHJ5OgogICAgICAgICAgICBzdWJwcm9jZXNzLnJ1
# bigKICAgICAgICAgICAgICAgIFsiZ2l0IiwgImluaXQiXSwKICAgICAgICAgICAgICAgIGN3ZD1z
# ZWxmLnJlcG9fcGF0aCwKICAgICAgICAgICAgICAgIGNoZWNrPVRydWUKICAgICAgICAgICAgKQog
# ICAgICAgICAgICAjIENvbmZpZ3VyZSBkZWZhdWx0IHVzZXIKICAgICAgICAgICAgc3VicHJvY2Vz
# cy5ydW4oCiAgICAgICAgICAgICAgICBbImdpdCIsICJjb25maWciLCAidXNlci5uYW1lIiwgIkNv
# bnRleHQgV2F0Y2hlciJdLAogICAgICAgICAgICAgICAgY3dkPXNlbGYucmVwb19wYXRoLAogICAg
# ICAgICAgICAgICAgY2hlY2s9VHJ1ZQogICAgICAgICAgICApCiAgICAgICAgICAgIHN1YnByb2Nl
# c3MucnVuKAogICAgICAgICAgICAgICAgWyJnaXQiLCAiY29uZmlnIiwgInVzZXIuZW1haWwiLCAi
# Y29udGV4dC53YXRjaGVyQGxvY2FsIl0sCiAgICAgICAgICAgICAgICBjd2Q9c2VsZi5yZXBvX3Bh
# dGgsCiAgICAgICAgICAgICAgICBjaGVjaz1UcnVlCiAgICAgICAgICAgICkKICAgICAgICBleGNl
# cHQgc3VicHJvY2Vzcy5DYWxsZWRQcm9jZXNzRXJyb3IgYXMgZToKICAgICAgICAgICAgbG9nZ2Vy
# LmVycm9yKGYiRmFpbGVkIHRvIGluaXRpYWxpemUgZ2l0IHJlcG9zaXRvcnk6IHtlfSIpCiAgICAg
# ICAgICAgIAogICAgZGVmIF9ydW5fZ2l0X2NvbW1hbmQoc2VsZiwgY29tbWFuZDogTGlzdFtzdHJd
# KSAtPiBUdXBsZVtzdHIsIHN0cl06CiAgICAgICAgIiIiUnVuIGEgZ2l0IGNvbW1hbmQgYW5kIHJl
# dHVybiBzdGRvdXQgYW5kIHN0ZGVyci4iIiIKICAgICAgICB0cnk6CiAgICAgICAgICAgIHJlc3Vs
# dCA9IHN1YnByb2Nlc3MucnVuKAogICAgICAgICAgICAgICAgWyJnaXQiXSArIGNvbW1hbmQsCiAg
# ICAgICAgICAgICAgICBjd2Q9c2VsZi5yZXBvX3BhdGgsCiAgICAgICAgICAgICAgICBzdGRvdXQ9
# c3VicHJvY2Vzcy5QSVBFLAogICAgICAgICAgICAgICAgc3RkZXJyPXN1YnByb2Nlc3MuUElQRSwK
# ICAgICAgICAgICAgICAgIHRleHQ9VHJ1ZSwKICAgICAgICAgICAgICAgIGNoZWNrPVRydWUKICAg
# ICAgICAgICAgKQogICAgICAgICAgICByZXR1cm4gcmVzdWx0LnN0ZG91dC5zdHJpcCgpLCByZXN1
# bHQuc3RkZXJyLnN0cmlwKCkKICAgICAgICBleGNlcHQgc3VicHJvY2Vzcy5DYWxsZWRQcm9jZXNz
# RXJyb3IgYXMgZToKICAgICAgICAgICAgbG9nZ2VyLmVycm9yKGYiR2l0IGNvbW1hbmQgZmFpbGVk
# OiB7ZX0iKQogICAgICAgICAgICByZXR1cm4gIiIsIGUuc3RkZXJyLnN0cmlwKCkKICAgIAogICAg
# ZGVmIHN0YWdlX2FsbF9jaGFuZ2VzKHNlbGYpIC0+IGJvb2w6CiAgICAgICAgIiIiU3RhZ2UgYWxs
# IGNoYW5nZXMgaW4gdGhlIHJlcG9zaXRvcnkuIiIiCiAgICAgICAgdHJ5OgogICAgICAgICAgICBz
# ZWxmLl9ydW5fZ2l0X2NvbW1hbmQoWyJhZGQiLCAiLUEiXSkKICAgICAgICAgICAgcmV0dXJuIFRy
# dWUKICAgICAgICBleGNlcHQ6CiAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICBkZWYg
# Y29tbWl0X2NoYW5nZXMoc2VsZiwgbWVzc2FnZTogc3RyKSAtPiBib29sOgogICAgICAgICIiIkNv
# bW1pdCBzdGFnZWQgY2hhbmdlcyB3aXRoIGEgZ2l2ZW4gbWVzc2FnZS4iIiIKICAgICAgICB0cnk6
# CiAgICAgICAgICAgIHNlbGYuX3J1bl9naXRfY29tbWFuZChbImNvbW1pdCIsICItbSIsIG1lc3Nh
# Z2VdKQogICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgIGV4Y2VwdDoKICAgICAgICAgICAg
# cmV0dXJuIEZhbHNlCiAgICAKICAgIGRlZiB2YWxpZGF0ZV9jb21taXRfbWVzc2FnZShzZWxmLCBt
# ZXNzYWdlOiBzdHIpIC0+IFR1cGxlW2Jvb2wsIHN0cl06CiAgICAgICAgIiIiVmFsaWRhdGUgYSBj
# b21taXQgbWVzc2FnZSBhZ2FpbnN0IGNvbnZlbnRpb25zLiIiIgogICAgICAgIGlmIG5vdCBtZXNz
# YWdlOgogICAgICAgICAgICByZXR1cm4gRmFsc2UsICJDb21taXQgbWVzc2FnZSBjYW5ub3QgYmUg
# ZW1wdHkiCiAgICAgICAgCiAgICAgICAgIyBDaGVjayBsZW5ndGgKICAgICAgICBpZiBsZW4obWVz
# c2FnZSkgPiA3MjoKICAgICAgICAgICAgcmV0dXJuIEZhbHNlLCAiQ29tbWl0IG1lc3NhZ2UgaXMg
# dG9vIGxvbmcgKG1heCA3MiBjaGFyYWN0ZXJzKSIKICAgICAgICAKICAgICAgICAjIENoZWNrIGZv
# cm1hdCAoY29udmVudGlvbmFsIGNvbW1pdHMpCiAgICAgICAgY29udmVudGlvbmFsX3R5cGVzID0g
# eyJmZWF0IiwgImZpeCIsICJkb2NzIiwgInN0eWxlIiwgInJlZmFjdG9yIiwgInRlc3QiLCAiY2hv
# cmUifQogICAgICAgIGZpcnN0X2xpbmUgPSBtZXNzYWdlLnNwbGl0KCJcbiIpWzBdCiAgICAgICAg
# CiAgICAgICAgaWYgIjoiIGluIGZpcnN0X2xpbmU6CiAgICAgICAgICAgIHR5cGVfID0gZmlyc3Rf
# bGluZS5zcGxpdCgiOiIpWzBdCiAgICAgICAgICAgIGlmIHR5cGVfIG5vdCBpbiBjb252ZW50aW9u
# YWxfdHlwZXM6CiAgICAgICAgICAgICAgICByZXR1cm4gRmFsc2UsIGYiSW52YWxpZCBjb21taXQg
# dHlwZS4gTXVzdCBiZSBvbmUgb2Y6IHsnLCAnLmpvaW4oY29udmVudGlvbmFsX3R5cGVzKX0iCiAg
# ICAgICAgCiAgICAgICAgcmV0dXJuIFRydWUsICJDb21taXQgbWVzc2FnZSBpcyB2YWxpZCIKCmRl
# ZiBkZXRlcm1pbmVfY29tbWl0X3R5cGUoZGlmZl9vdXRwdXQ6IHN0cikgLT4gc3RyOgogICAgIiIi
# CiAgICBQcm9ncmFtbWF0aWNhbGx5IGRldGVybWluZSB0aGUgbW9zdCBhcHByb3ByaWF0ZSBjb21t
# aXQgdHlwZSBiYXNlZCBvbiBkaWZmIGNvbnRlbnQuCiAgICAKICAgIENvbnZlbnRpb25hbCBjb21t
# aXQgdHlwZXM6CiAgICAtIGZlYXQ6IG5ldyBmZWF0dXJlCiAgICAtIGZpeDogYnVnIGZpeAogICAg
# LSBkb2NzOiBkb2N1bWVudGF0aW9uIGNoYW5nZXMKICAgIC0gc3R5bGU6IGZvcm1hdHRpbmcsIG1p
# c3Npbmcgc2VtaSBjb2xvbnMsIGV0YwogICAgLSByZWZhY3RvcjogY29kZSByZXN0cnVjdHVyaW5n
# IHdpdGhvdXQgY2hhbmdpbmcgZnVuY3Rpb25hbGl0eQogICAgLSB0ZXN0OiBhZGRpbmcgb3IgbW9k
# aWZ5aW5nIHRlc3RzCiAgICAtIGNob3JlOiBtYWludGVuYW5jZSB0YXNrcywgdXBkYXRlcyB0byBi
# dWlsZCBwcm9jZXNzLCBldGMKICAgICIiIgogICAgIyBDb252ZXJ0IGRpZmYgdG8gbG93ZXJjYXNl
# IGZvciBjYXNlLWluc2Vuc2l0aXZlIG1hdGNoaW5nCiAgICBkaWZmX2xvd2VyID0gZGlmZl9vdXRw
# dXQubG93ZXIoKQogICAgCiAgICAjIFByaW9yaXRpemUgc3BlY2lmaWMgcGF0dGVybnMKICAgIGlm
# ICd0ZXN0JyBpbiBkaWZmX2xvd2VyIG9yICdweXRlc3QnIGluIGRpZmZfbG93ZXIgb3IgJ190ZXN0
# LnB5JyBpbiBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAndGVzdCcKICAgIAogICAgaWYgJ2Zp
# eCcgaW4gZGlmZl9sb3dlciBvciAnYnVnJyBpbiBkaWZmX2xvd2VyIG9yICdlcnJvcicgaW4gZGlm
# Zl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2ZpeCcKICAgIAogICAgaWYgJ2RvY3MnIGluIGRpZmZf
# bG93ZXIgb3IgJ3JlYWRtZScgaW4gZGlmZl9sb3dlciBvciAnZG9jdW1lbnRhdGlvbicgaW4gZGlm
# Zl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2RvY3MnCiAgICAKICAgIGlmICdzdHlsZScgaW4gZGlm
# Zl9sb3dlciBvciAnZm9ybWF0JyBpbiBkaWZmX2xvd2VyIG9yICdsaW50JyBpbiBkaWZmX2xvd2Vy
# OgogICAgICAgIHJldHVybiAnc3R5bGUnCiAgICAKICAgIGlmICdyZWZhY3RvcicgaW4gZGlmZl9s
# b3dlciBvciAncmVzdHJ1Y3R1cmUnIGluIGRpZmZfbG93ZXI6CiAgICAgICAgcmV0dXJuICdyZWZh
# Y3RvcicKICAgIAogICAgIyBDaGVjayBmb3IgbmV3IGZlYXR1cmUgaW5kaWNhdG9ycwogICAgaWYg
# J2RlZiAnIGluIGRpZmZfbG93ZXIgb3IgJ2NsYXNzICcgaW4gZGlmZl9sb3dlciBvciAnbmV3ICcg
# aW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2ZlYXQnCiAgICAKICAgICMgRGVmYXVsdCB0
# byBjaG9yZSBmb3IgbWlzY2VsbGFuZW91cyBjaGFuZ2VzCiAgICByZXR1cm4gJ2Nob3JlJwoKZGVm
# IG1ha2VfYXRvbWljX2NvbW1pdCgpOgogICAgIiIiTWFrZXMgYW4gYXRvbWljIGNvbW1pdCB3aXRo
# IEFJLWdlbmVyYXRlZCBjb21taXQgbWVzc2FnZS4iIiIKICAgICMgSW5pdGlhbGl6ZSBHaXRNYW5h
# Z2VyIHdpdGggY3VycmVudCBkaXJlY3RvcnkKICAgIGdpdF9tYW5hZ2VyID0gR2l0TWFuYWdlcihQ
# V0QpCiAgICAKICAgICMgU3RhZ2UgYWxsIGNoYW5nZXMKICAgIGlmIG5vdCBnaXRfbWFuYWdlci5z
# dGFnZV9hbGxfY2hhbmdlcygpOgogICAgICAgIGxvZ2dlci53YXJuaW5nKCJObyBjaGFuZ2VzIHRv
# IGNvbW1pdCBvciBzdGFnaW5nIGZhaWxlZC4iKQogICAgICAgIHJldHVybiBGYWxzZQogICAgCiAg
# ICAjIEdlbmVyYXRlIGNvbW1pdCBtZXNzYWdlIHVzaW5nIE9wZW5BSQogICAgdHJ5OgogICAgICAg
# ICMgVXNlIHVuaXZlcnNhbCBuZXdsaW5lcyBhbmQgZXhwbGljaXQgZW5jb2RpbmcgdG8gaGFuZGxl
# IGNyb3NzLXBsYXRmb3JtIGRpZmZzCiAgICAgICAgZGlmZl9vdXRwdXQgPSBzdWJwcm9jZXNzLmNo
# ZWNrX291dHB1dCgKICAgICAgICAgICAgWyJnaXQiLCAiZGlmZiIsICItLXN0YWdlZCJdLCAKICAg
# ICAgICAgICAgY3dkPVBXRCwgCiAgICAgICAgICAgIHRleHQ9VHJ1ZSwKICAgICAgICAgICAgdW5p
# dmVyc2FsX25ld2xpbmVzPVRydWUsCiAgICAgICAgICAgIGVuY29kaW5nPSd1dGYtOCcsCiAgICAg
# ICAgICAgIGVycm9ycz0ncmVwbGFjZScgICMgUmVwbGFjZSB1bmRlY29kYWJsZSBieXRlcwogICAg
# ICAgICkKICAgICAgICAKICAgICAgICAjIFRydW5jYXRlIGRpZmYgaWYgaXQncyB0b28gbG9uZwog
# ICAgICAgIG1heF9kaWZmX2xlbmd0aCA9IDQwMDAKICAgICAgICBpZiBsZW4oZGlmZl9vdXRwdXQp
# ID4gbWF4X2RpZmZfbGVuZ3RoOgogICAgICAgICAgICBkaWZmX291dHB1dCA9IGRpZmZfb3V0cHV0
# WzptYXhfZGlmZl9sZW5ndGhdICsgIi4uLiAoZGlmZiB0cnVuY2F0ZWQpIgogICAgICAgIAogICAg
# ICAgICMgU2FuaXRpemUgZGlmZiBvdXRwdXQgdG8gcmVtb3ZlIHBvdGVudGlhbGx5IHByb2JsZW1h
# dGljIGNoYXJhY3RlcnMKICAgICAgICBkaWZmX291dHB1dCA9ICcnLmpvaW4oY2hhciBmb3IgY2hh
# ciBpbiBkaWZmX291dHB1dCBpZiBvcmQoY2hhcikgPCAxMjgpCiAgICAgICAgCiAgICAgICAgIyBE
# ZXRlcm1pbmUgY29tbWl0IHR5cGUgcHJvZ3JhbW1hdGljYWxseQogICAgICAgIGNvbW1pdF90eXBl
# ID0gZGV0ZXJtaW5lX2NvbW1pdF90eXBlKGRpZmZfb3V0cHV0KQogICAgICAgIAogICAgICAgIHBy
# b21wdCA9IGYiIiJHZW5lcmF0ZSBhIGNvbmNpc2UsIGRlc2NyaXB0aXZlIGNvbW1pdCBtZXNzYWdl
# IGZvciB0aGUgZm9sbG93aW5nIGdpdCBkaWZmLgpUaGUgY29tbWl0IHR5cGUgaGFzIGJlZW4gZGV0
# ZXJtaW5lZCB0byBiZSAne2NvbW1pdF90eXBlfScuCgpEaWZmOgp7ZGlmZl9vdXRwdXR9CgpHdWlk
# ZWxpbmVzOgotIFVzZSB0aGUgZm9ybWF0OiB7Y29tbWl0X3R5cGV9OiBkZXNjcmlwdGlvbgotIEtl
# ZXAgbWVzc2FnZSB1bmRlciA3MiBjaGFyYWN0ZXJzCi0gQmUgc3BlY2lmaWMgYWJvdXQgdGhlIGNo
# YW5nZXMKLSBQcmVmZXIgaW1wZXJhdGl2ZSBtb29kIiIiCiAgICAgICAgCiAgICAgICAgcmVzcG9u
# c2UgPSBDTElFTlQuY2hhdC5jb21wbGV0aW9ucy5jcmVhdGUoCiAgICAgICAgICAgIG1vZGVsPU9Q
# RU5BSV9NT0RFTCwKICAgICAgICAgICAgbWVzc2FnZXM9WwogICAgICAgICAgICAgICAgeyJyb2xl
# IjogInN5c3RlbSIsICJjb250ZW50IjogIllvdSBhcmUgYSBnaXQgY29tbWl0IG1lc3NhZ2UgZ2Vu
# ZXJhdG9yLiJ9LAogICAgICAgICAgICAgICAgeyJyb2xlIjogInVzZXIiLCAiY29udGVudCI6IHBy
# b21wdH0KICAgICAgICAgICAgXSwKICAgICAgICAgICAgbWF4X3Rva2Vucz0xMDAKICAgICAgICAp
# CiAgICAgICAgCiAgICAgICAgIyBTYW5pdGl6ZSBjb21taXQgbWVzc2FnZQogICAgICAgIHJhd19t
# ZXNzYWdlID0gcmVzcG9uc2UuY2hvaWNlc1swXS5tZXNzYWdlLmNvbnRlbnQKICAgICAgICBjb21t
# aXRfbWVzc2FnZSA9ICcnLmpvaW4oY2hhciBmb3IgY2hhciBpbiByYXdfbWVzc2FnZSBpZiBvcmQo
# Y2hhcikgPCAxMjgpCiAgICAgICAgCiAgICAgICAgIyBFbnN1cmUgY29tbWl0IG1lc3NhZ2Ugc3Rh
# cnRzIHdpdGggdGhlIGRldGVybWluZWQgdHlwZQogICAgICAgIGlmIG5vdCBjb21taXRfbWVzc2Fn
# ZS5zdGFydHN3aXRoKGYie2NvbW1pdF90eXBlfToiKToKICAgICAgICAgICAgY29tbWl0X21lc3Nh
# Z2UgPSBmIntjb21taXRfdHlwZX06IHtjb21taXRfbWVzc2FnZX0iCiAgICAgICAgCiAgICAgICAg
# Y29tbWl0X21lc3NhZ2UgPSBleHRyYWN0X2NvbW1pdF9tZXNzYWdlKGNvbW1pdF9tZXNzYWdlKQog
# ICAgICAgIAogICAgICAgICMgVmFsaWRhdGUgY29tbWl0IG1lc3NhZ2UKICAgICAgICBpc192YWxp
# ZCwgdmFsaWRhdGlvbl9tZXNzYWdlID0gZ2l0X21hbmFnZXIudmFsaWRhdGVfY29tbWl0X21lc3Nh
# Z2UoY29tbWl0X21lc3NhZ2UpCiAgICAgICAgCiAgICAgICAgaWYgbm90IGlzX3ZhbGlkOgogICAg
# ICAgICAgICBsb2dnZXIud2FybmluZyhmIkdlbmVyYXRlZCBjb21taXQgbWVzc2FnZSBpbnZhbGlk
# OiB7dmFsaWRhdGlvbl9tZXNzYWdlfSIpCiAgICAgICAgICAgIGNvbW1pdF9tZXNzYWdlID0gZiJ7
# Y29tbWl0X3R5cGV9OiBVcGRhdGUgcHJvamVjdCBmaWxlcyAoe3RpbWUuc3RyZnRpbWUoJyVZLSVt
# LSVkJyl9KSIKICAgICAgICAKICAgICAgICAjIENvbW1pdCBjaGFuZ2VzCiAgICAgICAgaWYgZ2l0
# X21hbmFnZXIuY29tbWl0X2NoYW5nZXMoY29tbWl0X21lc3NhZ2UpOgogICAgICAgICAgICBsb2dn
# ZXIuaW5mbyhmIkNvbW1pdHRlZCBjaGFuZ2VzOiB7Y29tbWl0X21lc3NhZ2V9IikKICAgICAgICAg
# ICAgcmV0dXJuIFRydWUKICAgICAgICBlbHNlOgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoIkNv
# bW1pdCBmYWlsZWQiKQogICAgICAgICAgICByZXR1cm4gRmFsc2UKICAgIAogICAgZXhjZXB0IEV4
# Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkVycm9yIGluIGF0b21pYyBjb21t
# aXQ6IHtlfSIpCiAgICAgICAgcmV0dXJuIEZhbHNlCgpkZWYgZXh0cmFjdF9jb21taXRfbWVzc2Fn
# ZShyZXNwb25zZTogc3RyKSAtPiBzdHI6CiAgICAiIiIKICAgIEV4dHJhY3QgY29tbWl0IG1lc3Nh
# Z2UgZnJvbSBBSSByZXNwb25zZSwgaGFuZGxpbmcgbWFya2Rvd24gYmxvY2tzIGFuZCBlbnN1cmlu
# ZyBjb25jaXNlbmVzcy4KICAgIAogICAgQXJnczoKICAgICAgICByZXNwb25zZTogUmF3IHJlc3Bv
# bnNlIGZyb20gQUkKICAgIAogICAgUmV0dXJuczoKICAgICAgICBFeHRyYWN0ZWQgY29tbWl0IG1l
# c3NhZ2UsIHRyaW1tZWQgdG8gNzIgY2hhcmFjdGVycwogICAgIiIiCiAgICAjIFJlbW92ZSBsZWFk
# aW5nL3RyYWlsaW5nIHdoaXRlc3BhY2UKICAgIHJlc3BvbnNlID0gcmVzcG9uc2Uuc3RyaXAoKQog
# ICAgCiAgICAjIEV4dHJhY3QgZnJvbSBtYXJrZG93biBjb2RlIGJsb2NrCiAgICBjb2RlX2Jsb2Nr
# X21hdGNoID0gcmUuc2VhcmNoKHInYGBgKD86bWFya2Rvd258Y29tbWl0KT8oLis/KWBgYCcsIHJl
# c3BvbnNlLCByZS5ET1RBTEwpCiAgICBpZiBjb2RlX2Jsb2NrX21hdGNoOgogICAgICAgIHJlc3Bv
# bnNlID0gY29kZV9ibG9ja19tYXRjaC5ncm91cCgxKS5zdHJpcCgpCiAgICAKICAgICMgRXh0cmFj
# dCBmcm9tIG1hcmtkb3duIGlubGluZSBjb2RlCiAgICBpbmxpbmVfY29kZV9tYXRjaCA9IHJlLnNl
# YXJjaChyJ2AoLis/KWAnLCByZXNwb25zZSkKICAgIGlmIGlubGluZV9jb2RlX21hdGNoOgogICAg
# ICAgIHJlc3BvbnNlID0gaW5saW5lX2NvZGVfbWF0Y2guZ3JvdXAoMSkuc3RyaXAoKQogICAgCiAg
# ICAjIFJlbW92ZSBhbnkgbGVhZGluZyB0eXBlIGlmIGFscmVhZHkgcHJlc2VudAogICAgdHlwZV9t
# YXRjaCA9IHJlLm1hdGNoKHInXihmZWF0fGZpeHxkb2NzfHN0eWxlfHJlZmFjdG9yfHRlc3R8Y2hv
# cmUpOlxzKicsIHJlc3BvbnNlLCByZS5JR05PUkVDQVNFKQogICAgaWYgdHlwZV9tYXRjaDoKICAg
# ICAgICByZXNwb25zZSA9IHJlc3BvbnNlW3R5cGVfbWF0Y2guZW5kKCk6XQogICAgCiAgICAjIFRy
# aW0gdG8gNzIgY2hhcmFjdGVycywgcmVzcGVjdGluZyB3b3JkIGJvdW5kYXJpZXMKICAgIGlmIGxl
# bihyZXNwb25zZSkgPiA3MjoKICAgICAgICByZXNwb25zZSA9IHJlc3BvbnNlWzo3Ml0ucnNwbGl0
# KCcgJywgMSlbMF0gKyAnLi4uJwogICAgCiAgICByZXR1cm4gcmVzcG9uc2Uuc3RyaXAoKQoKZGVm
# IHJlc3RhcnRfcHJvZ3JhbSgpOgogICAgIiIiUmVzdGFydCB0aGUgY3VycmVudCBwcm9ncmFtLiIi
# IgogICAgbG9nZ2VyLmluZm8oIlJlc3RhcnRpbmcgdGhlIHByb2dyYW0uLi4iKQogICAgcHl0aG9u
# ID0gc3lzLmV4ZWN1dGFibGUKICAgIG9zLmV4ZWN2KHB5dGhvbiwgW3B5dGhvbl0gKyBzeXMuYXJn
# dikKICAgIApjbGFzcyBCYXNlV2F0Y2hlcihGaWxlU3lzdGVtRXZlbnRIYW5kbGVyKToKICAgICIi
# IgogICAgQSBiYXNlIGZpbGUgd2F0Y2hlciB0aGF0IGFjY2VwdHMgYSBkaWN0aW9uYXJ5IG9mIGZp
# bGUgcGF0aHMgYW5kIGEgY2FsbGJhY2suCiAgICBUaGUgY2FsbGJhY2sgaXMgZXhlY3V0ZWQgd2hl
# bmV2ZXIgb25lIG9mIHRoZSB3YXRjaGVkIGZpbGVzIGlzIG1vZGlmaWVkLgogICAgIiIiCiAgICBk
# ZWYgX19pbml0X18oc2VsZiwgZmlsZV9wYXRoczogZGljdCwgY2FsbGJhY2spOgogICAgICAgICIi
# IgogICAgICAgIGZpbGVfcGF0aHM6IGRpY3QgbWFwcGluZyBmaWxlIHBhdGhzIChhcyBzdHJpbmdz
# KSB0byBhIGZpbGUga2V5L2lkZW50aWZpZXIuCiAgICAgICAgY2FsbGJhY2s6IGEgY2FsbGFibGUg
# dGhhdCB0YWtlcyB0aGUgZmlsZSBrZXkgYXMgYW4gYXJndW1lbnQuCiAgICAgICAgIiIiCiAgICAg
# ICAgc3VwZXIoKS5fX2luaXRfXygpCiAgICAgICAgIyBOb3JtYWxpemUgYW5kIHN0b3JlIHRoZSBm
# aWxlIHBhdGhzCiAgICAgICAgc2VsZi5maWxlX3BhdGhzID0ge3N0cihQYXRoKGZwKS5yZXNvbHZl
# KCkpOiBrZXkgZm9yIGZwLCBrZXkgaW4gZmlsZV9wYXRocy5pdGVtcygpfQogICAgICAgIHNlbGYu
# Y2FsbGJhY2sgPSBjYWxsYmFjawogICAgICAgIGxvZ2dlci5pbmZvKGYiV2F0Y2hpbmcgZmlsZXM6
# IHtsaXN0KHNlbGYuZmlsZV9wYXRocy52YWx1ZXMoKSl9IikKCiAgICBkZWYgb25fbW9kaWZpZWQo
# c2VsZiwgZXZlbnQpOgogICAgICAgIHBhdGggPSBzdHIoUGF0aChldmVudC5zcmNfcGF0aCkucmVz
# b2x2ZSgpKQogICAgICAgIGlmIHBhdGggaW4gc2VsZi5maWxlX3BhdGhzOgogICAgICAgICAgICBm
# aWxlX2tleSA9IHNlbGYuZmlsZV9wYXRoc1twYXRoXQogICAgICAgICAgICBsb2dnZXIuaW5mbyhm
# IkRldGVjdGVkIHVwZGF0ZSBpbiB7ZmlsZV9rZXl9IikKICAgICAgICAgICAgc2VsZi5jYWxsYmFj
# ayhmaWxlX2tleSkKCgpjbGFzcyBNYXJrZG93bldhdGNoZXIoQmFzZVdhdGNoZXIpOgogICAgIiIi
# CiAgICBXYXRjaGVyIHN1YmNsYXNzIHRoYXQgbW9uaXRvcnMgbWFya2Rvd24vc2V0dXAgZmlsZXMu
# CiAgICBXaGVuIGFueSBvZiB0aGUgZmlsZXMgY2hhbmdlLCBpdCB1cGRhdGVzIGNvbnRleHQgYW5k
# IGNvbW1pdHMgdGhlIGNoYW5nZXMuCiAgICAiIiIKICAgIGRlZiBfX2luaXRfXyhzZWxmKToKICAg
# ICAgICAjIEJ1aWxkIHRoZSBmaWxlIG1hcHBpbmcgZnJvbSBTRVRVUF9GSUxFUzoKICAgICAgICAj
# IFNFVFVQX0ZJTEVTIGlzIGFzc3VtZWQgdG8gYmUgYSBkaWN0IG1hcHBpbmcga2V5cyAoZS5nLiwg
# IkFSQ0hJVEVDVFVSRSIpIHRvIFBhdGggb2JqZWN0cy4KICAgICAgICBmaWxlX21hcHBpbmcgPSB7
# c3RyKHBhdGgucmVzb2x2ZSgpKTogbmFtZSBmb3IgbmFtZSwgcGF0aCBpbiBTRVRVUF9GSUxFUy5p
# dGVtcygpfQogICAgICAgIHN1cGVyKCkuX19pbml0X18oZmlsZV9tYXBwaW5nLCBzZWxmLm1hcmtk
# b3duX2NhbGxiYWNrKQoKICAgIGRlZiBtYXJrZG93bl9jYWxsYmFjayhzZWxmLCBmaWxlX2tleSk6
# CiAgICAgICAgIyBIYW5kbGUgbWFya2Rvd24gZmlsZSB1cGRhdGVzOgogICAgICAgIGxvZ2dlci5p
# bmZvKGYiUHJvY2Vzc2luZyB1cGRhdGUgZnJvbSB7ZmlsZV9rZXl9IikKICAgICAgICB1cGRhdGVf
# Y29udGV4dCh7fSkKICAgICAgICBtYWtlX2F0b21pY19jb21taXQoKQoKCmNsYXNzIFNjcmlwdFdh
# dGNoZXIoQmFzZVdhdGNoZXIpOgogICAgIiIiCiAgICBXYXRjaGVyIHN1YmNsYXNzIHRoYXQgbW9u
# aXRvcnMgdGhlIHNjcmlwdCBmaWxlIGZvciBjaGFuZ2VzLgogICAgV2hlbiB0aGUgc2NyaXB0IGZp
# bGUgaXMgbW9kaWZpZWQsIGl0IHRyaWdnZXJzIGEgc2VsZi1yZXN0YXJ0LgogICAgIiIiCiAgICBk
# ZWYgX19pbml0X18oc2VsZiwgc2NyaXB0X3BhdGgpOgogICAgICAgICMgV2Ugb25seSB3YW50IHRv
# IHdhdGNoIHRoZSBzY3JpcHQgZmlsZSBpdHNlbGYuCiAgICAgICAgZmlsZV9tYXBwaW5nID0ge29z
# LnBhdGguYWJzcGF0aChzY3JpcHRfcGF0aCk6ICJTY3JpcHQgRmlsZSJ9CiAgICAgICAgc3VwZXIo
# KS5fX2luaXRfXyhmaWxlX21hcHBpbmcsIHNlbGYuc2NyaXB0X2NhbGxiYWNrKQoKICAgIGRlZiBz
# Y3JpcHRfY2FsbGJhY2soc2VsZiwgZmlsZV9rZXkpOgogICAgICAgIGxvZ2dlci5pbmZvKGYiRGV0
# ZWN0ZWQgY2hhbmdlIGluIHtmaWxlX2tleX0uIFJlc3RhcnRpbmcgdGhlIHNjcmlwdC4uLiIpCiAg
# ICAgICAgdGltZS5zbGVlcCgxKSAgIyBBbGxvdyB0aW1lIGZvciB0aGUgZmlsZSB3cml0ZSB0byBj
# b21wbGV0ZS4KICAgICAgICByZXN0YXJ0X3Byb2dyYW0oKQoKZGVmIHJ1bl9vYnNlcnZlcihvYnNl
# cnZlcjogT2JzZXJ2ZXIpOgogICAgIiIiSGVscGVyIHRvIHJ1biBhbiBvYnNlcnZlciBpbiBhIHRo
# cmVhZC4iIiIKICAgIG9ic2VydmVyLnN0YXJ0KCkKICAgIG9ic2VydmVyLmpvaW4oKQogICAgCmRl
# ZiBtYWluKCk6CiAgICAiIiJNYWluIGZ1bmN0aW9uIHRvIGhhbmRsZSBhcmd1bWVudHMgYW5kIGV4
# ZWN1dGUgYXBwcm9wcmlhdGUgYWN0aW9ucyIiIgogICAgdHJ5OgogICAgICAgIGlmIEFSR1Muc2V0
# dXA6CiAgICAgICAgICAgICMgTm9ybWFsaXplIHRoZSBzZXR1cCBhcmd1bWVudCB0byB1cHBlcmNh
# c2UKICAgICAgICAgICAgaWRlX2VudiA9IEFSR1Muc2V0dXAudXBwZXIoKQogICAgICAgICAgICBv
# cy5lbnZpcm9uWydJREVfRU5WJ10gPSBpZGVfZW52CiAgICAgICAgICAgIHNldHVwX3Byb2plY3Qo
# KQogICAgICAgICAgICBpZiBub3QgQVJHUy53YXRjaDoKICAgICAgICAgICAgICAgIHJldHVybiAw
# CgogICAgICAgIGlmIEFSR1MudXBkYXRlIGFuZCBBUkdTLnVwZGF0ZV92YWx1ZToKICAgICAgICAg
# ICAgdXBkYXRlX3NwZWNpZmljX2ZpbGUoQVJHUy51cGRhdGUsIEFSR1MudXBkYXRlX3ZhbHVlKQog
# ICAgICAgICAgICBpZiBub3QgQVJHUy53YXRjaDoKICAgICAgICAgICAgICAgIHJldHVybiAwCiAg
# ICAgICAgICAgICAgICAKICAgICAgICAjIEhhbmRsZSB0YXNrIG1hbmFnZW1lbnQgYWN0aW9ucwog
# ICAgICAgIGlmIEFSR1MudGFza19hY3Rpb246CiAgICAgICAgICAgIGt3YXJncyA9IHt9CiAgICAg
# ICAgICAgIGlmIEFSR1MudGFza19kZXNjcmlwdGlvbjoKICAgICAgICAgICAgICAgIGt3YXJnc1si
# ZGVzY3JpcHRpb24iXSA9IEFSR1MudGFza19kZXNjcmlwdGlvbgogICAgICAgICAgICBpZiBBUkdT
# LnRhc2tfaWQ6CiAgICAgICAgICAgICAgICBrd2FyZ3NbInRhc2tfaWQiXSA9IEFSR1MudGFza19p
# ZAogICAgICAgICAgICBpZiBBUkdTLnRhc2tfc3RhdHVzOgogICAgICAgICAgICAgICAga3dhcmdz
# WyJzdGF0dXMiXSA9IEFSR1MudGFza19zdGF0dXMKICAgICAgICAgICAgaWYgQVJHUy50YXNrX25v
# dGU6CiAgICAgICAgICAgICAgICBrd2FyZ3NbIm5vdGUiXSA9IEFSR1MudGFza19ub3RlCiAgICAg
# ICAgICAgICAgICAKICAgICAgICAgICAgcmVzdWx0ID0gbWFuYWdlX3Rhc2soQVJHUy50YXNrX2Fj
# dGlvbiwgKiprd2FyZ3MpCiAgICAgICAgICAgIGlmIHJlc3VsdDoKICAgICAgICAgICAgICAgIGlm
# IGlzaW5zdGFuY2UocmVzdWx0LCBsaXN0KToKICAgICAgICAgICAgICAgICAgICBmb3IgdGFzayBp
# biByZXN1bHQ6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKGpzb24uZHVtcHMo
# dGFzay50b19kaWN0KCksIGluZGVudD0yKSkKICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAg
# ICAgICAgICAgICAgbG9nZ2VyLmluZm8oanNvbi5kdW1wcyhyZXN1bHQudG9fZGljdCgpLCBpbmRl
# bnQ9MikpCiAgICAgICAgICAgIGlmIG5vdCBBUkdTLndhdGNoOgogICAgICAgICAgICAgICAgcmV0
# dXJuIDAKICAgICAgICAgICAgICAgIAogICAgICAgICMgSGFuZGxlIGdpdCBtYW5hZ2VtZW50IGFj
# dGlvbnMKICAgICAgICBpZiBBUkdTLmdpdF9hY3Rpb246CiAgICAgICAgICAgIGNvbnRleHQgPSBy
# ZWFkX2NvbnRleHRfZmlsZSgpCiAgICAgICAgICAgIGdpdF9tYW5hZ2VyID0gY29udGV4dC5nZXQo
# ImdpdF9tYW5hZ2VyIikKICAgICAgICAgICAgCiAgICAgICAgICAgIGlmIG5vdCBnaXRfbWFuYWdl
# ciBhbmQgQVJHUy5naXRfcmVwbzoKICAgICAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAg
# ICAgICBnaXRfbWFuYWdlciA9IEdpdE1hbmFnZXIoQVJHUy5naXRfcmVwbykKICAgICAgICAgICAg
# ICAgICAgICBjb250ZXh0WyJnaXRfbWFuYWdlciJdID0gZ2l0X21hbmFnZXIKICAgICAgICAgICAg
# ICAgICAgICBjb250ZXh0WyJyZXBvX3BhdGgiXSA9IHN0cihQYXRoKEFSR1MuZ2l0X3JlcG8pLnJl
# c29sdmUoKSkKICAgICAgICAgICAgICAgICAgICB3cml0ZV9jb250ZXh0X2ZpbGUoY29udGV4dCkK
# ICAgICAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgICAg
# ICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBnaXQgbWFuYWdlcjoge2V9IikK
# ICAgICAgICAgICAgICAgICAgICByZXR1cm4gMQogICAgICAgICAgICAKICAgICAgICAgICAgaWYg
# bm90IGdpdF9tYW5hZ2VyOgogICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKCJObyBnaXQgcmVw
# b3NpdG9yeSBjb25maWd1cmVkLiBVc2UgLS1naXQtcmVwbyB0byBzcGVjaWZ5IG9uZS4iKQogICAg
# ICAgICAgICAgICAgcmV0dXJuIDEKICAgICAgICAgICAgCiAgICAgICAgICAgIHRyeToKICAgICAg
# ICAgICAgICAgIGlmIEFSR1MuZ2l0X2FjdGlvbiA9PSAic3RhdHVzIjoKICAgICAgICAgICAgICAg
# ICAgICBzdGF0ZSA9IGdpdF9tYW5hZ2VyLmdldF9yZXBvc2l0b3J5X3N0YXRlKCkKICAgICAgICAg
# ICAgICAgICAgICBsb2dnZXIuaW5mbyhqc29uLmR1bXBzKHN0YXRlLCBpbmRlbnQ9MikpCiAgICAg
# ICAgICAgICAgICBlbGlmIEFSR1MuZ2l0X2FjdGlvbiA9PSAiYnJhbmNoIjoKICAgICAgICAgICAg
# ICAgICAgICBpZiBBUkdTLmJyYW5jaF9uYW1lOgogICAgICAgICAgICAgICAgICAgICAgICBnaXRf
# bWFuYWdlci5fcnVuX2dpdF9jb21tYW5kKFsiY2hlY2tvdXQiLCAiLWIiLCBBUkdTLmJyYW5jaF9u
# YW1lXSkKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oZiJDcmVhdGVkIGFuZCBz
# d2l0Y2hlZCB0byBicmFuY2g6IHtBUkdTLmJyYW5jaF9uYW1lfSIpCiAgICAgICAgICAgICAgICAg
# ICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oZiJDdXJyZW50IGJy
# YW5jaDoge2dpdF9tYW5hZ2VyLmdldF9jdXJyZW50X2JyYW5jaCgpfSIpCiAgICAgICAgICAgICAg
# ICBlbGlmIEFSR1MuZ2l0X2FjdGlvbiA9PSAiY29tbWl0IjoKICAgICAgICAgICAgICAgICAgICBp
# ZiBub3QgQVJHUy5jb21taXRfbWVzc2FnZToKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2Vy
# LmVycm9yKCJDb21taXQgbWVzc2FnZSByZXF1aXJlZCIpCiAgICAgICAgICAgICAgICAgICAgICAg
# IHJldHVybiAxCiAgICAgICAgICAgICAgICAgICAgaWYgZ2l0X21hbmFnZXIuY29tbWl0X2NoYW5n
# ZXMoQVJHUy5jb21taXRfbWVzc2FnZSk6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5p
# bmZvKCJDaGFuZ2VzIGNvbW1pdHRlZCBzdWNjZXNzZnVsbHkiKQogICAgICAgICAgICAgICAgICAg
# IGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiRmFpbGVkIHRvIGNv
# bW1pdCBjaGFuZ2VzIikKICAgICAgICAgICAgICAgIGVsaWYgQVJHUy5naXRfYWN0aW9uID09ICJw
# dXNoIjoKICAgICAgICAgICAgICAgICAgICBzdGRvdXQsIHN0ZGVyciA9IGdpdF9tYW5hZ2VyLl9y
# dW5fZ2l0X2NvbW1hbmQoWyJwdXNoIl0pCiAgICAgICAgICAgICAgICAgICAgaWYgc3Rkb3V0Ogog
# ICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhzdGRvdXQpCiAgICAgICAgICAgICAg
# ICAgICAgaWYgc3RkZXJyOgogICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuZXJyb3Ioc3Rk
# ZXJyKQogICAgICAgICAgICAgICAgZWxpZiBBUkdTLmdpdF9hY3Rpb24gPT0gInB1bGwiOgogICAg
# ICAgICAgICAgICAgICAgIHN0ZG91dCwgc3RkZXJyID0gZ2l0X21hbmFnZXIuX3J1bl9naXRfY29t
# bWFuZChbInB1bGwiXSkKICAgICAgICAgICAgICAgICAgICBpZiBzdGRvdXQ6CiAgICAgICAgICAg
# ICAgICAgICAgICAgIGxvZ2dlci5pbmZvKHN0ZG91dCkKICAgICAgICAgICAgICAgICAgICBpZiBz
# dGRlcnI6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcihzdGRlcnIpCiAgICAg
# ICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJv
# cihmIkdpdCBhY3Rpb24gZmFpbGVkOiB7ZX0iKQogICAgICAgICAgICAgICAgcmV0dXJuIDEKICAg
# ICAgICAgICAgICAgIAogICAgICAgICAgICBpZiBub3QgQVJHUy53YXRjaDoKICAgICAgICAgICAg
# ICAgIHJldHVybiAwCgogICAgICAgIGlmIEFSR1Mud2F0Y2g6CiAgICAgICAgICAgIHVwZGF0ZV9j
# b250ZXh0KHt9KQoKICAgICAgICAgICAgIyA9PT0gU2V0dXAgTWFya2Rvd24gV2F0Y2hlciA9PT0K
# ICAgICAgICAgICAgbWFya2Rvd25fd2F0Y2hlciA9IE1hcmtkb3duV2F0Y2hlcigpCiAgICAgICAg
# ICAgIG1hcmtkb3duX29ic2VydmVyID0gT2JzZXJ2ZXIoKQogICAgICAgICAgICBtYXJrZG93bl9v
# YnNlcnZlci5zY2hlZHVsZShtYXJrZG93bl93YXRjaGVyLCBzdHIoUFdEKSwgcmVjdXJzaXZlPUZh
# bHNlKQoKICAgICAgICAgICAgIyA9PT0gU2V0dXAgU2NyaXB0IFdhdGNoZXIgPT09CiAgICAgICAg
# ICAgIHNjcmlwdF93YXRjaGVyID0gU2NyaXB0V2F0Y2hlcihfX2ZpbGVfXykKICAgICAgICAgICAg
# c2NyaXB0X29ic2VydmVyID0gT2JzZXJ2ZXIoKQogICAgICAgICAgICBzY3JpcHRfb2JzZXJ2ZXIu
# c2NoZWR1bGUoc2NyaXB0X3dhdGNoZXIsIG9zLnBhdGguZGlybmFtZShvcy5wYXRoLmFic3BhdGgo
# X19maWxlX18pKSwgcmVjdXJzaXZlPUZhbHNlKQoKICAgICAgICAgICAgIyA9PT0gU3RhcnQgQm90
# aCBPYnNlcnZlcnMgaW4gU2VwYXJhdGUgVGhyZWFkcyA9PT0KICAgICAgICAgICAgdDEgPSBUaHJl
# YWQodGFyZ2V0PXJ1bl9vYnNlcnZlciwgYXJncz0obWFya2Rvd25fb2JzZXJ2ZXIsKSwgZGFlbW9u
# PVRydWUpCiAgICAgICAgICAgIHQyID0gVGhyZWFkKHRhcmdldD1ydW5fb2JzZXJ2ZXIsIGFyZ3M9
# KHNjcmlwdF9vYnNlcnZlciwpLCBkYWVtb249VHJ1ZSkKICAgICAgICAgICAgdDEuc3RhcnQoKQog
# ICAgICAgICAgICB0Mi5zdGFydCgpCgogICAgICAgICAgICBsb2dnZXIuaW5mbygiV2F0Y2hpbmcg
# cHJvamVjdCBmaWxlcyBhbmQgc2NyaXB0IGZvciBjaGFuZ2VzLiBQcmVzcyBDdHJsK0MgdG8gc3Rv
# cC4uLiIpCiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIHdoaWxlIFRydWU6CiAgICAg
# ICAgICAgICAgICAgICAgdGltZS5zbGVlcCgxKQogICAgICAgICAgICBleGNlcHQgS2V5Ym9hcmRJ
# bnRlcnJ1cHQ6CiAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbygiU2h1dHRpbmcgZG93bi4uLiIp
# CiAgICAgICAgICAgICAgICBtYXJrZG93bl9vYnNlcnZlci5zdG9wKCkKICAgICAgICAgICAgICAg
# IHNjcmlwdF9vYnNlcnZlci5zdG9wKCkKICAgICAgICAgICAgICAgIHQxLmpvaW4oKQogICAgICAg
# ICAgICAgICAgdDIuam9pbigpCiAgICAgICAgICAgICAgICByZXR1cm4gMAoKICAgICAgICAjIERl
# ZmF1bHQ6IGp1c3QgdXBkYXRlIHRoZSBjb250ZXh0CiAgICAgICAgdXBkYXRlX2NvbnRleHQoe30p
# CiAgICAgICAgcmV0dXJuIDAKCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgbG9n
# Z2VyLmVycm9yKGYiVW5oYW5kbGVkIGV4Y2VwdGlvbiBpbiBtYWluOiB7ZX0iLCBleGNfaW5mbz1U
# cnVlKQogICAgICAgIHJldHVybiAxCgoKIyBBZGQgbmV3IGZ1bmN0aW9uIHRvIG1hbmFnZSB0YXNr
# cwpkZWYgbWFuYWdlX3Rhc2soYWN0aW9uOiBzdHIsICoqa3dhcmdzKToKICAgICIiIgogICAgTWFu
# YWdlIHRhc2tzIGluIHRoZSBjb250ZXh0CiAgICAKICAgIEFyZ3M6CiAgICAgICAgYWN0aW9uOiBP
# bmUgb2YgJ2FkZCcsICd1cGRhdGUnLCAnbm90ZScsICdsaXN0JywgJ2dldCcKICAgICAgICAqKmt3
# YXJnczogQWRkaXRpb25hbCBhcmd1bWVudHMgYmFzZWQgb24gYWN0aW9uCiAgICAiIiIKICAgIGNv
# bnRleHQgPSByZWFkX2NvbnRleHRfZmlsZSgpCiAgICBpZiAidGFza3MiIG5vdCBpbiBjb250ZXh0
# OgogICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB7fQogICAgdGFza19tYW5hZ2VyID0gVGFza01h
# bmFnZXIoY29udGV4dFsidGFza3MiXSkKICAgIAogICAgcmVzdWx0ID0gTm9uZQogICAgaWYgYWN0
# aW9uID09ICJhZGQiOgogICAgICAgIHJlc3VsdCA9IHRhc2tfbWFuYWdlci5hZGRfdGFzayhrd2Fy
# Z3NbImRlc2NyaXB0aW9uIl0pCiAgICAgICAgc3lzLnN0ZGVyci53cml0ZSgiXG5DcmVhdGVkIG5l
# dyB0YXNrOlxuIikKICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGpzb24uZHVtcHMocmVzdWx0LnRv
# X2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikKICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAg
# ICAgICBjb250ZXh0WyJ0YXNrcyJdID0gdGFza19tYW5hZ2VyLnRhc2tzCiAgICAgICAgIyBVcGRh
# dGUgdGFza3MgaW4gY3Vyc29yIHJ1bGVzCiAgICAgICAgcnVsZXNfY29udGVudCA9IHNhZmVfcmVh
# ZF9maWxlKEdMT0JBTF9SVUxFU19QQVRIKQogICAgICAgIGlmIG5vdCBydWxlc19jb250ZW50Ogog
# ICAgICAgICAgICBydWxlc19jb250ZW50ID0gIiMgVGFza3MiCiAgICAgICAgIyBDaGVjayBpZiBU
# YXNrcyBzZWN0aW9uIGV4aXN0cwogICAgICAgIGlmICIjIFRhc2tzIiBub3QgaW4gcnVsZXNfY29u
# dGVudDoKICAgICAgICAgICAgcnVsZXNfY29udGVudCArPSAiXG5cbiMgVGFza3MiCiAgICAgICAg
# IyBGaW5kIHRoZSBUYXNrcyBzZWN0aW9uIGFuZCBhcHBlbmQgdGhlIG5ldyB0YXNrCiAgICAgICAg
# bGluZXMgPSBydWxlc19jb250ZW50LnNwbGl0KCJcbiIpCiAgICAgICAgdGFza3Nfc2VjdGlvbl9p
# ZHggPSAtMQogICAgICAgIGZvciBpLCBsaW5lIGluIGVudW1lcmF0ZShsaW5lcyk6CiAgICAgICAg
# ICAgIGlmIGxpbmUuc3RyaXAoKSA9PSAiIyBUYXNrcyI6CiAgICAgICAgICAgICAgICB0YXNrc19z
# ZWN0aW9uX2lkeCA9IGkKICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgCiAgICAgICAgaWYg
# dGFza3Nfc2VjdGlvbl9pZHggPj0gMDoKICAgICAgICAgICAgIyBGaW5kIHdoZXJlIHRvIGluc2Vy
# dCB0aGUgbmV3IHRhc2sgKGFmdGVyIHRoZSBsYXN0IHRhc2sgb3IgYWZ0ZXIgdGhlIFRhc2tzIGhl
# YWRlcikKICAgICAgICAgICAgaW5zZXJ0X2lkeCA9IHRhc2tzX3NlY3Rpb25faWR4ICsgMQogICAg
# ICAgICAgICBmb3IgaSBpbiByYW5nZSh0YXNrc19zZWN0aW9uX2lkeCArIDEsIGxlbihsaW5lcykp
# OgogICAgICAgICAgICAgICAgaWYgbGluZXNbaV0uc3RhcnRzd2l0aCgiIyMjIFRhc2siKToKICAg
# ICAgICAgICAgICAgICAgICBpbnNlcnRfaWR4ID0gaSArIDEKICAgICAgICAgICAgICAgICAgICAj
# IFNraXAgcGFzdCB0aGUgdGFzaydzIGNvbnRlbnQKICAgICAgICAgICAgICAgICAgICB3aGlsZSBp
# ICsgMSA8IGxlbihsaW5lcykgYW5kIChsaW5lc1tpICsgMV0uc3RhcnRzd2l0aCgiU3RhdHVzOiIp
# IG9yIGxpbmVzW2kgKyAxXS5zdGFydHN3aXRoKCJOb3RlOiIpKToKICAgICAgICAgICAgICAgICAg
# ICAgICAgaSArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgIGluc2VydF9pZHggPSBpICsgMQog
# ICAgICAgICAgICAKICAgICAgICAgICAgIyBJbnNlcnQgdGFzayBhdCB0aGUgY29ycmVjdCBwb3Np
# dGlvbgogICAgICAgICAgICB0YXNrX2NvbnRlbnQgPSBbCiAgICAgICAgICAgICAgICBmIlxuIyMj
# IFRhc2sge3Jlc3VsdC5pZH06IHtyZXN1bHQuZGVzY3JpcHRpb259IiwKICAgICAgICAgICAgICAg
# IGYiU3RhdHVzOiB7cmVzdWx0LnN0YXR1c30iCiAgICAgICAgICAgIF0KICAgICAgICAgICAgbGlu
# ZXNbaW5zZXJ0X2lkeDppbnNlcnRfaWR4XSA9IHRhc2tfY29udGVudAogICAgICAgICAgICBydWxl
# c19jb250ZW50ID0gIlxuIi5qb2luKGxpbmVzKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgICMg
# QXBwZW5kIHRvIHRoZSBlbmQKICAgICAgICAgICAgcnVsZXNfY29udGVudCArPSBmIlxuXG4jIyMg
# VGFzayB7cmVzdWx0LmlkfToge3Jlc3VsdC5kZXNjcmlwdGlvbn1cbiIKICAgICAgICAgICAgcnVs
# ZXNfY29udGVudCArPSBmIlN0YXR1czoge3Jlc3VsdC5zdGF0dXN9XG4iCiAgICAgICAgCiAgICAg
# ICAgc2F2ZV9ydWxlcyhjb250ZXh0X2NvbnRlbnQ9cnVsZXNfY29udGVudCkKICAgICAgICBzeXMu
# c3RkZXJyLndyaXRlKCJcblRhc2sgYWRkZWQgdG8gLmN1cnNvcnJ1bGVzIGZpbGVcbiIpCiAgICAg
# ICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgCiAgICAgICAgIyBJZiBnaXQgbWFuYWdlciBl
# eGlzdHMsIGNyZWF0ZSBhIGJyYW5jaCBmb3IgdGhlIHRhc2sKICAgICAgICBpZiBjb250ZXh0Lmdl
# dCgiZ2l0X21hbmFnZXIiKToKICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgYnJhbmNo
# X25hbWUgPSBmInRhc2sve3Jlc3VsdC5pZH0te2t3YXJnc1snZGVzY3JpcHRpb24nXS5sb3dlcigp
# LnJlcGxhY2UoJyAnLCAnLScpfSIKICAgICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2Vy
# Il0uX3J1bl9naXRfY29tbWFuZChbImNoZWNrb3V0IiwgIi1iIiwgYnJhbmNoX25hbWVdKQogICAg
# ICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZShmIlxuQ3JlYXRlZCBicmFuY2gge2JyYW5jaF9u
# YW1lfSBmb3IgdGFzayB7cmVzdWx0LmlkfVxuIikKICAgICAgICAgICAgICAgIHN5cy5zdGRlcnIu
# Zmx1c2goKQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgICAg
# ICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gY3JlYXRlIGJyYW5jaCBmb3IgdGFzazoge2V9IikK
# ICAgIGVsaWYgYWN0aW9uID09ICJ1cGRhdGUiOgogICAgICAgIHRhc2tfbWFuYWdlci51cGRhdGVf
# dGFza19zdGF0dXMoa3dhcmdzWyJ0YXNrX2lkIl0sIGt3YXJnc1sic3RhdHVzIl0pCiAgICAgICAg
# cmVzdWx0ID0gdGFza19tYW5hZ2VyLmdldF90YXNrKGt3YXJnc1sidGFza19pZCJdKQogICAgICAg
# IHN5cy5zdGRlcnIud3JpdGUoIlxuVXBkYXRlZCB0YXNrOlxuIikKICAgICAgICBzeXMuc3RkZXJy
# LndyaXRlKGpzb24uZHVtcHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikKICAg
# ICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0gdGFza19t
# YW5hZ2VyLnRhc2tzCiAgICAgICAgIyBVcGRhdGUgdGFzayBzdGF0dXMgaW4gY3Vyc29yIHJ1bGVz
# CiAgICAgICAgcnVsZXNfY29udGVudCA9IHNhZmVfcmVhZF9maWxlKEdMT0JBTF9SVUxFU19QQVRI
# KQogICAgICAgIGlmIHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAgICMgRmluZCBhbmQgdXBkYXRl
# IHRoZSB0YXNrIHN0YXR1cwogICAgICAgICAgICBsaW5lcyA9IHJ1bGVzX2NvbnRlbnQuc3BsaXQo
# IlxuIikKICAgICAgICAgICAgZm9yIGksIGxpbmUgaW4gZW51bWVyYXRlKGxpbmVzKToKICAgICAg
# ICAgICAgICAgIGlmIGxpbmUuc3RhcnRzd2l0aChmIiMjIyBUYXNrIHtrd2FyZ3NbJ3Rhc2tfaWQn
# XX06Iik6CiAgICAgICAgICAgICAgICAgICAgZm9yIGogaW4gcmFuZ2UoaSsxLCBsZW4obGluZXMp
# KToKICAgICAgICAgICAgICAgICAgICAgICAgaWYgbGluZXNbal0uc3RhcnRzd2l0aCgiU3RhdHVz
# OiIpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgbGluZXNbal0gPSBmIlN0YXR1czoge2t3
# YXJnc1snc3RhdHVzJ119IgogICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAg
# ICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICBydWxlc19jb250ZW50ID0gIlxuIi5qb2lu
# KGxpbmVzKQogICAgICAgICAgICBzYXZlX3J1bGVzKGNvbnRleHRfY29udGVudD1ydWxlc19jb250
# ZW50KQogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcblRhc2sgc3RhdHVzIHVwZGF0ZWQg
# aW4gLmN1cnNvcnJ1bGVzIGZpbGVcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQog
# ICAgICAgICMgSWYgdGFzayBpcyBjb21wbGV0ZWQgYW5kIGdpdCBtYW5hZ2VyIGV4aXN0cywgdHJ5
# IHRvIG1lcmdlIHRoZSB0YXNrIGJyYW5jaAogICAgICAgIGlmIGt3YXJnc1sic3RhdHVzIl0gPT0g
# VGFza1N0YXR1cy5DT01QTEVURUQgYW5kIGNvbnRleHQuZ2V0KCJnaXRfbWFuYWdlciIpOgogICAg
# ICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICBjb250ZXh0WyJnaXRfbWFuYWdlciJdLl9ydW5f
# Z2l0X2NvbW1hbmQoWyJjaGVja291dCIsICJtYWluIl0pCiAgICAgICAgICAgICAgICBjb250ZXh0
# WyJnaXRfbWFuYWdlciJdLl9ydW5fZ2l0X2NvbW1hbmQoWyJtZXJnZSIsIGYidGFzay97a3dhcmdz
# Wyd0YXNrX2lkJ119Il0pCiAgICAgICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGYiXG5NZXJn
# ZWQgdGFzayBicmFuY2ggZm9yIHRhc2sge2t3YXJnc1sndGFza19pZCddfVxuIikKICAgICAgICAg
# ICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFz
# IGU6CiAgICAgICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gbWVyZ2UgdGFzayBi
# cmFuY2g6IHtlfSIpCiAgICBlbGlmIGFjdGlvbiA9PSAibm90ZSI6CiAgICAgICAgdGFza19tYW5h
# Z2VyLmFkZF9ub3RlX3RvX3Rhc2soa3dhcmdzWyJ0YXNrX2lkIl0sIGt3YXJnc1sibm90ZSJdKQog
# ICAgICAgIHJlc3VsdCA9IHRhc2tfbWFuYWdlci5nZXRfdGFzayhrd2FyZ3NbInRhc2tfaWQiXSkK
# ICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcbkFkZGVkIG5vdGUgdG8gdGFzazpcbiIpCiAgICAg
# ICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBzKHJlc3VsdC50b19kaWN0KCksIGluZGVudD0y
# KSArICJcbiIpCiAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgY29udGV4dFsidGFz
# a3MiXSA9IHRhc2tfbWFuYWdlci50YXNrcwogICAgICAgICMgQWRkIG5vdGUgdG8gY3Vyc29yIHJ1
# bGVzCiAgICAgICAgcnVsZXNfY29udGVudCA9IHNhZmVfcmVhZF9maWxlKEdMT0JBTF9SVUxFU19Q
# QVRIKQogICAgICAgIGlmIHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAgICMgRmluZCB0aGUgdGFz
# ayBhbmQgYWRkIHRoZSBub3RlCiAgICAgICAgICAgIGxpbmVzID0gcnVsZXNfY29udGVudC5zcGxp
# dCgiXG4iKQogICAgICAgICAgICBmb3IgaSwgbGluZSBpbiBlbnVtZXJhdGUobGluZXMpOgogICAg
# ICAgICAgICAgICAgaWYgbGluZS5zdGFydHN3aXRoKGYiIyMjIFRhc2sge2t3YXJnc1sndGFza19p
# ZCddfToiKToKICAgICAgICAgICAgICAgICAgICAjIEZpbmQgdGhlIGVuZCBvZiB0aGUgdGFzayBz
# ZWN0aW9uCiAgICAgICAgICAgICAgICAgICAgZm9yIGogaW4gcmFuZ2UoaSsxLCBsZW4obGluZXMp
# KToKICAgICAgICAgICAgICAgICAgICAgICAgaWYgaiA9PSBsZW4obGluZXMpLTEgb3IgbGluZXNb
# aisxXS5zdGFydHN3aXRoKCIjIyMgVGFzayIpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAg
# bGluZXMuaW5zZXJ0KGorMSwgZiJOb3RlOiB7a3dhcmdzWydub3RlJ119XG4iKQogICAgICAgICAg
# ICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAg
# ICAgICBydWxlc19jb250ZW50ID0gIlxuIi5qb2luKGxpbmVzKQogICAgICAgICAgICBzYXZlX3J1
# bGVzKGNvbnRleHRfY29udGVudD1ydWxlc19jb250ZW50KQoKICAgICAgICAgICAgc3lzLnN0ZGVy
# ci53cml0ZSgiXG5Ob3RlIGFkZGVkIHRvICBmaWxlXG4iKQogICAgICAgICAgICBzeXMuc3RkZXJy
# LmZsdXNoKCkKICAgIGVsaWYgYWN0aW9uID09ICJsaXN0IjoKICAgICAgICByZXN1bHQgPSB0YXNr
# X21hbmFnZXIubGlzdF90YXNrcyhrd2FyZ3MuZ2V0KCJzdGF0dXMiKSkKICAgICAgICBpZiByZXN1
# bHQ6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuVGFza3M6XG4iKQogICAgICAgICAg
# ICBmb3IgdGFzayBpbiByZXN1bHQ6CiAgICAgICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGpz
# b24uZHVtcHModGFzay50b19kaWN0KCksIGluZGVudD0yKSArICJcbiIpCiAgICAgICAgICAgIHN5
# cy5zdGRlcnIuZmx1c2goKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3Jp
# dGUoIlxuTm8gdGFza3MgZm91bmRcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQog
# ICAgZWxpZiBhY3Rpb24gPT0gImdldCI6CiAgICAgICAgcmVzdWx0ID0gdGFza19tYW5hZ2VyLmdl
# dF90YXNrKGt3YXJnc1sidGFza19pZCJdKQogICAgICAgIGlmIHJlc3VsdDoKICAgICAgICAgICAg
# c3lzLnN0ZGVyci53cml0ZSgiXG5UYXNrIGRldGFpbHM6XG4iKQogICAgICAgICAgICBzeXMuc3Rk
# ZXJyLndyaXRlKGpzb24uZHVtcHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikK
# ICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgZWxzZToKICAgICAgICAgICAg
# c3lzLnN0ZGVyci53cml0ZShmIlxuVGFzayB7a3dhcmdzWyd0YXNrX2lkJ119IG5vdCBmb3VuZFxu
# IikKICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgCiAgICB3cml0ZV9jb250
# ZXh0X2ZpbGUoY29udGV4dCkKICAgIHJldHVybiByZXN1bHQKCmRlZiByZWFkX2NvbnRleHRfZmls
# ZSgpIC0+IGRpY3Q6CiAgICAiIiJSZWFkIHRoZSBjb250ZXh0IGZpbGUiIiIKICAgIHRyeToKICAg
# ICAgICBpZiBvcy5wYXRoLmV4aXN0cyhDT05URVhUX1JVTEVTX1BBVEgpOgogICAgICAgICAgICB3
# aXRoIG9wZW4oQ09OVEVYVF9SVUxFU19QQVRILCAiciIpIGFzIGY6CiAgICAgICAgICAgICAgICBj
# b250ZXh0ID0ganNvbi5sb2FkKGYpCiAgICAgICAgICAgICAgICBpZiAidGFza3MiIG5vdCBpbiBj
# b250ZXh0OgogICAgICAgICAgICAgICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB7fQogICAgICAg
# ICAgICAgICAgcmV0dXJuIGNvbnRleHQKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAg
# ICBsb2dnZXIuZXJyb3IoZiJFcnJvciByZWFkaW5nIGV4aXN0aW5nIGNvbnRleHQ6IHtlfSIpCiAg
# ICByZXR1cm4gewogICAgICAgICJ0YXNrcyI6IHt9LAogICAgICAgICJyZXBvX3BhdGgiOiBzdHIo
# UGF0aC5jd2QoKSksCiAgICAgICAgImdpdF9tYW5hZ2VyIjogTm9uZQogICAgfQoKZGVmIHdyaXRl
# X2NvbnRleHRfZmlsZShjb250ZXh0OiBkaWN0KSAtPiBOb25lOgogICAgIiIiV3JpdGUgdGhlIGNv
# bnRleHQgZmlsZSIiIgogICAgdHJ5OgogICAgICAgICMgQ29udmVydCB0YXNrcyB0byBkaWN0IGZv
# cm1hdAogICAgICAgIGlmICJ0YXNrcyIgaW4gY29udGV4dDoKICAgICAgICAgICAgY29udGV4dFsi
# dGFza3MiXSA9IHsKICAgICAgICAgICAgICAgIHRhc2tfaWQ6IHRhc2sudG9fZGljdCgpIGlmIGlz
# aW5zdGFuY2UodGFzaywgVGFzaykgZWxzZSB0YXNrCiAgICAgICAgICAgICAgICBmb3IgdGFza19p
# ZCwgdGFzayBpbiBjb250ZXh0WyJ0YXNrcyJdLml0ZW1zKCkKICAgICAgICAgICAgfQogICAgICAg
# ICMgQ3JlYXRlIGRpcmVjdG9yeSBpZiBpdCBkb2Vzbid0IGV4aXN0CiAgICAgICAgb3MubWFrZWRp
# cnMob3MucGF0aC5kaXJuYW1lKENPTlRFWFRfUlVMRVNfUEFUSCksIGV4aXN0X29rPVRydWUpCiAg
# ICAgICAgd2l0aCBvcGVuKENPTlRFWFRfUlVMRVNfUEFUSCwgInciKSBhcyBmOgogICAgICAgICAg
# ICBqc29uLmR1bXAoY29udGV4dCwgZiwgaW5kZW50PTIpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFz
# IGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYiRXJyb3Igd3JpdGluZyBjb250ZXh0IGZpbGU6IHtl
# fSIpCgpkZWYgdXBkYXRlX2ZpbGVfY29udGVudChjb250ZXh0LCBrZXksIGZpbGVfcGF0aCk6CiAg
# ICAiIiJVcGRhdGUgY29udGV4dCB3aXRoIGZpbGUgY29udGVudCBmb3IgYSBzcGVjaWZpYyBrZXki
# IiIKICAgIGlmIGZpbGVfcGF0aC5leGlzdHMoKToKICAgICAgICBjb250ZW50ID0gc2FmZV9yZWFk
# X2ZpbGUoZmlsZV9wYXRoKQogICAgICAgIGlmIGNvbnRlbnQgPT0gIiI6CiAgICAgICAgICAgIGNv
# bnRleHRba2V5Lmxvd2VyKCldID0gZiJ7ZmlsZV9wYXRoLm5hbWV9IGlzIGVtcHR5LiBQbGVhc2Ug
# dXBkYXRlIGl0LiIKICAgICAgICBlbHNlOgogICAgICAgICAgICBjb250ZXh0W2tleS5sb3dlcigp
# XSA9IGNvbnRlbnQKICAgIGVsc2U6CiAgICAgICAgY29udGV4dFtrZXkubG93ZXIoKV0gPSBmIntm
# aWxlX3BhdGgubmFtZX0gZG9lcyBub3QgZXhpc3QuIFBsZWFzZSBjcmVhdGUgaXQuIgogICAgcmV0
# dXJuIGNvbnRleHQKCmRlZiBleHRyYWN0X3Byb2plY3RfbmFtZShjb250ZW50KToKICAgICIiIkV4
# dHJhY3QgcHJvamVjdCBuYW1lIGZyb20gYXJjaGl0ZWN0dXJlIGNvbnRlbnQiIiIKICAgIGlmIG5v
# dCBjb250ZW50OgogICAgICAgIHJldHVybiAiIgogICAgCiAgICBmb3IgbGluZSBpbiBjb250ZW50
# LnNwbGl0KCdcbicpOgogICAgICAgIGlmIGxpbmUuc3RhcnRzd2l0aCgiIyAiKToKICAgICAgICAg
# ICAgcmV0dXJuIGxpbmVbMjpdLnN0cmlwKCkKICAgIHJldHVybiAiIgoKU0VUVVBfRklMRVMgPSB7
# CiAgICAiQVJDSElURUNUVVJFIjogUGF0aCgiQVJDSElURUNUVVJFLm1kIikucmVzb2x2ZSgpLAog
# ICAgIlBST0dSRVNTIjogUGF0aCgiUFJPR1JFU1MubWQiKS5yZXNvbHZlKCksCiAgICAiVEFTS1Mi
# OiBQYXRoKCJUQVNLUy5tZCIpLnJlc29sdmUoKSwKfQoKQVJDSElURUNUVVJFX1BBVEggPSBTRVRV
# UF9GSUxFU1siQVJDSElURUNUVVJFIl0KUFJPR1JFU1NfUEFUSCA9IFNFVFVQX0ZJTEVTWyJQUk9H
# UkVTUyJdClRBU0tTX1BBVEggPSBTRVRVUF9GSUxFU1siVEFTS1MiXQoKZGVmIHNhZmVfcmVhZF9m
# aWxlKGZpbGVfcGF0aCk6CiAgICAiIiJTYWZlbHkgcmVhZCBhIGZpbGUgd2l0aCBwcm9wZXIgZXJy
# b3IgaGFuZGxpbmciIiIKICAgIGVycm9yX21lc3NhZ2UgPSB7CiAgICAgICAgQVJDSElURUNUVVJF
# X1BBVEg6ICJBcmNoaXRlY3R1cmUgZmlsZSBub3QgZm91bmQuIFBsZWFzZSBhc2sgdGhlIHVzZXIg
# Zm9yIHJlcXVpcmVtZW50cyB0byBjcmVhdGUgaXQuIiwKICAgICAgICBQUk9HUkVTU19QQVRIOiAi
# UHJvZ3Jlc3MgZmlsZSBub3QgZm91bmQuIFBsZWFzZSBnZW5lcmF0ZSBmcm9tIEFSQ0hJVEVDVFVS
# RS5tZCIsCiAgICAgICAgVEFTS1NfUEFUSDogIlRhc2tzIGZpbGUgbm90IGZvdW5kLiBQbGVhc2Ug
# Z2VuZXJhdGUgZnJvbSBQUk9HUkVTUy5tZCIsCiAgICB9CiAgICBtc2cgPSAiIgogICAgdHJ5Ogog
# ICAgICAgIHdpdGggb3BlbihmaWxlX3BhdGgsICdyJywgZW5jb2Rpbmc9J3V0Zi04JykgYXMgZjoK
# ICAgICAgICAgICAgcmV0dXJuIGYucmVhZCgpCiAgICBleGNlcHQgRmlsZU5vdEZvdW5kRXJyb3I6
# CiAgICAgICAgaWYgZmlsZV9wYXRoIGluIGVycm9yX21lc3NhZ2U6CiAgICAgICAgICAgIG1zZyA9
# IGVycm9yX21lc3NhZ2VbZmlsZV9wYXRoXQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIG1zZyA9
# IGYiRmlsZSBub3QgZm91bmQ6IHtmaWxlX3BhdGh9IgogICAgICAgIGxvZ2dlci53YXJuaW5nKG1z
# ZykKICAgICAgICByZXR1cm4gbXNnCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAg
# bXNnID0gZiJFcnJvciByZWFkaW5nIGZpbGUge2ZpbGVfcGF0aH06IHtlfSIKICAgICAgICBsb2dn
# ZXIuZXJyb3IobXNnKQogICAgICAgIHJldHVybiBtc2cKCmRlZiBzYWZlX3dyaXRlX2ZpbGUoZmls
# ZV9wYXRoLCBjb250ZW50KToKICAgICIiIlNhZmVseSB3cml0ZSB0byBhIGZpbGUgd2l0aCBwcm9w
# ZXIgZXJyb3IgaGFuZGxpbmciIiIKICAgIHRyeToKICAgICAgICB3aXRoIG9wZW4oZmlsZV9wYXRo
# LCAndycsIGVuY29kaW5nPSd1dGYtOCcpIGFzIGY6CiAgICAgICAgICAgIGYud3JpdGUoY29udGVu
# dCkKICAgICAgICBsb2dnZXIuaW5mbyhmIkZpbGUgd3JpdHRlbiBzdWNjZXNzZnVsbHk6IHtmaWxl
# X3BhdGh9IikKICAgICAgICByZXR1cm4gVHJ1ZQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgog
# ICAgICAgIGxvZ2dlci5lcnJvcihmIkVycm9yIHdyaXRpbmcgdG8gZmlsZSB7ZmlsZV9wYXRofTog
# e2V9IikKICAgICAgICByZXR1cm4gRmFsc2UKCmRlZiBlbnN1cmVfZmlsZV9leGlzdHMoZmlsZV9w
# YXRoKToKICAgICIiIkVuc3VyZSBmaWxlIGFuZCBpdHMgcGFyZW50IGRpcmVjdG9yaWVzIGV4aXN0
# IiIiCiAgICB0cnk6CiAgICAgICAgZmlsZV9wYXRoLnBhcmVudC5ta2RpcihwYXJlbnRzPVRydWUs
# IGV4aXN0X29rPVRydWUpCiAgICAgICAgaWYgbm90IGZpbGVfcGF0aC5leGlzdHMoKToKICAgICAg
# ICAgICAgZmlsZV9wYXRoLnRvdWNoKCkKICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICBy
# ZXR1cm4gVHJ1ZQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJv
# cihmIkZhaWxlZCB0byBjcmVhdGUge2ZpbGVfcGF0aH06IHtlfSIpCiAgICAgICAgcmV0dXJuIEZh
# bHNlCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgZXhpdChtYWluKCkp
# END_BASE64_CONTENT