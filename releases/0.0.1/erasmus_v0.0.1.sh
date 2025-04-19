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
cd "$PROJECT_ROOT" || {
    echo -e "${RED}Failed to change to project root directory.${NC}"
    exit 1
}

# Detect operating system
detect_os() {
    case "$(uname -s)" in
    Darwin*) OS='macOS' ;;
    Linux*) OS='Linux' ;;
    MINGW* | MSYS* | CYGWIN*) OS='Windows' ;;
    *) OS='Unknown' ;;
    esac
}

# Check and install prerequisites based on OS
check_prerequisites() {
    case "$OS" in
    Windows)
        echo -e "${YELLOW}Checking Windows prerequisites...${NC}"
        # Check if winget is available
        if ! command winget --version &>/dev/null; then
            echo -e "${RED}Error: winget is not available on this Windows system.${NC}"
            echo "Attempting to install winget..."
            # Try to install winget via PowerShell
            powershell.exe -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
            if ! command winget --version &>/dev/null; then
                echo -e "${RED}Failed to install winget. Please install the App Installer from the Microsoft Store.${NC}"
                echo "Visit: https://www.microsoft.com/store/productId/9NBLGGH4NNS1"
                exit 1
            fi
        fi
        ;;
    macOS)
        echo -e "${YELLOW}Checking macOS prerequisites...${NC}"
        # Check if Homebrew is installed
        if ! command -v brew &>/dev/null; then
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
        if ! command curl --version &>/dev/null; then
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
    cat >.env.example <<EOL
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
    echo "$BASE64_CONTENT" | base64 -d >erasmus.py

    # Verify the SHA256 hash
    if command -v shasum &>/dev/null; then
        ACTUAL_HASH=$(shasum -a 256 erasmus.py | cut -d ' ' -f 1)
    elif command -v sha256sum &>/dev/null; then
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

# __ERASMUS_EMBEDDED_BELOW__
# The content below this line is the base64-encoded watcher.py file
# It will be extracted during installation as erasmus.py
# SHA256_HASH=8b4b0e3cdb447c28f330aba4b71b2707efc59211bf19eca3f85bc5881c1da8ef
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
# PiBib29sOgogICAgIiIiQmFzaWMgVVJMIHZhbGlkYXRpb24gdXNpbmcgcmVnZXguCiAgICAKICAg
# IEFjY2VwdHM6CiAgICAtIFN0YW5kYXJkIGh0dHAvaHR0cHMgVVJMcyAoZS5nLiwgaHR0cHM6Ly9h
# cGkub3BlbmFpLmNvbS92MSkKICAgIC0gTG9jYWxob3N0IFVSTHMgd2l0aCBvcHRpb25hbCBwb3J0
# IChlLmcuLCBodHRwOi8vbG9jYWxob3N0OjExNDM0KQogICAgLSBJUC1iYXNlZCBsb2NhbGhvc3Qg
# VVJMcyAoZS5nLiwgaHR0cDovLzEyNy4wLjAuMTo4MDAwKQogICAgCiAgICBBcmdzOgogICAgICAg
# IHVybDogVVJMIHN0cmluZyB0byB2YWxpZGF0ZQogICAgICAgIAogICAgUmV0dXJuczoKICAgICAg
# ICBib29sOiBUcnVlIGlmIHRoZSBVUkwgaXMgdmFsaWQsIEZhbHNlIG90aGVyd2lzZQogICAgIiIi
# CiAgICBpZiBub3QgdXJsOgogICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICAjIExvZyB0aGUg
# VVJMIGJlaW5nIHZhbGlkYXRlZCBmb3IgZGVidWdnaW5nCiAgICBsb2dnZXIuZGVidWcoZiJWYWxp
# ZGF0aW5nIFVSTDoge3VybH0iKQogICAgCiAgICAjIENoZWNrIGZvciBsb2NhbGhvc3Qgb3IgMTI3
# LjAuMC4xCiAgICBsb2NhbGhvc3RfcGF0dGVybiA9IHJlLm1hdGNoKHInXmh0dHBzPzovLyg/Omxv
# Y2FsaG9zdHwxMjdcLjBcLjBcLjEpKD86OlxkKyk/KD86Ly4qKT8kJywgdXJsKQogICAgaWYgbG9j
# YWxob3N0X3BhdHRlcm46CiAgICAgICAgbG9nZ2VyLmRlYnVnKGYiVVJMIHt1cmx9IG1hdGNoZWQg
# bG9jYWxob3N0IHBhdHRlcm4iKQogICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgCiAgICAjIENo
# ZWNrIGZvciBzdGFuZGFyZCBodHRwL2h0dHBzIFVSTHMKICAgIHN0YW5kYXJkX3BhdHRlcm4gPSBy
# ZS5tYXRjaChyJ15odHRwcz86Ly9bXHdcLi1dKyg/OjpcZCspPyg/Oi8uKik/JCcsIHVybCkKICAg
# IHJlc3VsdCA9IGJvb2woc3RhbmRhcmRfcGF0dGVybikKICAgIAogICAgaWYgcmVzdWx0OgogICAg
# ICAgIGxvZ2dlci5kZWJ1ZyhmIlVSTCB7dXJsfSBtYXRjaGVkIHN0YW5kYXJkIHBhdHRlcm4iKQog
# ICAgZWxzZToKICAgICAgICBsb2dnZXIud2FybmluZyhmIlVSTCB2YWxpZGF0aW9uIGZhaWxlZCBm
# b3I6IHt1cmx9IikKICAgICAgICAKICAgIHJldHVybiByZXN1bHQKCmRlZiBkZXRlY3RfaWRlX2Vu
# dmlyb25tZW50KCkgLT4gc3RyOgogICAgIiIiCiAgICBEZXRlY3QgdGhlIGN1cnJlbnQgSURFIGVu
# dmlyb25tZW50LgogICAgCiAgICBSZXR1cm5zOgogICAgICAgIHN0cjogRGV0ZWN0ZWQgSURFIGVu
# dmlyb25tZW50ICgnV0lORFNVUkYnLCAnQ1VSU09SJywgb3IgJycpCiAgICAiIiIKICAgICMgQ2hl
# Y2sgZW52aXJvbm1lbnQgdmFyaWFibGUgZmlyc3QKICAgIGlkZV9lbnYgPSBvcy5nZXRlbnYoJ0lE
# RV9FTlYnLCAnJykKICAgIGlmIGlkZV9lbnYgPT0gIiI6CiAgICAgICAgaWRlX2VudiA9IGlucHV0
# KCJFbnRlciB5b3VyIElERSBlbnZpcm9ubWVudCAoV0lORFNVUkYsIENVUlNPUik6ICIpLnN0cmlw
# KCkKICAgIGlmIGlkZV9lbnY6CiAgICAgICAgcmV0dXJuICdXSU5EU1VSRicgaWYgaWRlX2Vudi5z
# dGFydHN3aXRoKCdXJykgZWxzZSAnQ1VSU09SJwogICAgCiAgICAjIFRyeSB0byBkZXRlY3QgYmFz
# ZWQgb24gY3VycmVudCB3b3JraW5nIGRpcmVjdG9yeSBvciBrbm93biBJREUgcGF0aHMKICAgIGN3
# ZCA9IFBhdGguY3dkKCkKICAgIAogICAgIyBXaW5kc3VyZi1zcGVjaWZpYyBkZXRlY3Rpb24KICAg
# IHdpbmRzdXJmX21hcmtlcnMgPSBbCiAgICAgICAgUGF0aC5ob21lKCkgLyAnLmNvZGVpdW0nIC8g
# J3dpbmRzdXJmJywKICAgICAgICBjd2QgLyAnLndpbmRzdXJmcnVsZXMnCiAgICBdCiAgICAKICAg
# ICMgQ3Vyc29yLXNwZWNpZmljIGRldGVjdGlvbgogICAgY3Vyc29yX21hcmtlcnMgPSBbCiAgICAg
# ICAgY3dkIC8gJy5jdXJzb3JydWxlcycsCiAgICAgICAgUGF0aC5ob21lKCkgLyAnLmN1cnNvcicK
# ICAgIF0KICAgIAogICAgIyBDaGVjayBXaW5kc3VyZiBtYXJrZXJzCiAgICBmb3IgbWFya2VyIGlu
# IHdpbmRzdXJmX21hcmtlcnM6CiAgICAgICAgaWYgbWFya2VyLmV4aXN0cygpOgogICAgICAgICAg
# ICByZXR1cm4gJ1dJTkRTVVJGJwogICAgCiAgICAjIENoZWNrIEN1cnNvciBtYXJrZXJzCiAgICBm
# b3IgbWFya2VyIGluIGN1cnNvcl9tYXJrZXJzOgogICAgICAgIGlmIG1hcmtlci5leGlzdHMoKToK
# ICAgICAgICAgICAgcmV0dXJuICdDVVJTT1InCiAgICAKICAgICMgRGVmYXVsdCBmYWxsYmFjawog
# ICAgcmV0dXJuICdXSU5EU1VSRicKCgpkZWYgcHJvbXB0X29wZW5haV9jcmVkZW50aWFscyhlbnZf
# cGF0aD0iLmVudiIpOgogICAgIiIiUHJvbXB0IHVzZXIgZm9yIE9wZW5BSSBjcmVkZW50aWFscyBh
# bmQgc2F2ZSB0byAuZW52IiIiCiAgICBnbG9iYWwgR0lUX0NPTU1JVFMKICAgIAogICAgYXBpX2tl
# eSA9IG9zLmdldGVudigiT1BFTkFJX0FQSV9LRVkiKQogICAgaWYgbm90IGFwaV9rZXk6CiAgICAg
# ICAgcHJpbnQoIklmIHlvdSBhcmUgcnVubmluZyBsb2NhbCBpbmZlcmVuY2UgYW5kIGRvIG5vdCBo
# YXZlIGFuIGFwaSBrZXkgY29uZmlndXJlZCBqdXN0IHVzZSBzay0xMjM0IikKICAgICAgICBhcGlf
# a2V5ID0gZ2V0cGFzcygiRW50ZXIgeW91ciBPUEVOQUlfQVBJX0tFWSAoaW5wdXQgaGlkZGVuKTog
# IikKICAgICAgICBpZiBub3QgYXBpX2tleToKICAgICAgICAgICAgcHJpbnQoIkFQSSBLZXkgbWlz
# c2luZy4gRGlzYWJsaW5nIGNvbW1pdCBtZXNzYWdlIGdlbmVyYXRpb24uIikKICAgICAgICAgICAg
# R0lUX0NPTU1JVFM9RmFsc2UKICAgICAgICAgICAgYXBpX2tleSA9ICJzay0xMjM0IgoKICAgIGJh
# c2VfdXJsID0gb3MuZ2V0ZW52KCJPUEVOQUlfQkFTRV9VUkwiKQogICAgaWYgbm90IGJhc2VfdXJs
# OgogICAgICAgIHByaW50KCJFbnRlciB5b3VyIE9wZW5BSSBiYXNlIFVSTC4iKQogICAgICAgIHBy
# aW50KCJJZiB5b3UgYXJlIHJ1bm5pbmcgbG9jYWwgaW5mZXJlbmNlIHVzZSB5b3VyIGxvY2FsIGhv
# c3QgdXJsKGUuZy4gZm9yIG9sbGFtYTogaHR0cDovL2xvY2FsaG9zdDoxMTQzNC92MSkiKQogICAg
# ICAgIGJhc2VfdXJsID0gaW5wdXQoIkVudGVyIHlvdXIgT1BFTkFJX0JBU0VfVVJMIChkZWZhdWx0
# OiBodHRwczovL2FwaS5vcGVuYWkuY29tL3YxKTogIikuc3RyaXAoKQogICAgICAgIGlmIG5vdCBp
# c192YWxpZF91cmwoYmFzZV91cmwpOgogICAgICAgICAgICBwcmludCgiSW52YWxpZCBVUkwgb3Ig
# ZW1wdHkuIERlZmF1bHRpbmcgdG8gaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSIpCiAgICAgICAg
# ICAgIGJhc2VfdXJsID0gImh0dHBzOi8vYXBpLm9wZW5haS5jb20vdjEiCgogICAgbW9kZWwgPSBv
# cy5nZXRlbnYoIk9QRU5BSV9NT0RFTCIpCiAgICBpZiBub3QgbW9kZWw6CiAgICAgICAgbW9kZWwg
# PSBpbnB1dCgiRW50ZXIgeW91ciBPUEVOQUlfTU9ERUwgKGRlZmF1bHQ6IGdwdC00byk6ICIpLnN0
# cmlwKCkKICAgICAgICBpZiBub3QgbW9kZWw6CiAgICAgICAgICAgIG1vZGVsID0gImdwdC00byIK
# ICAgICAgICAKICAgICMgRGV0ZWN0IElERSBlbnZpcm9ubWVudCBhbmQgc2F2ZSBpdCB0byB0aGUg
# LmVudiBmaWxlCiAgICBpZGVfZW52ID0gZGV0ZWN0X2lkZV9lbnZpcm9ubWVudCgpCiAgICAKICAg
# IGVudl9jb250ZW50ID0gKAogICAgICAgICJcbiIKICAgICAgICBmIk9QRU5BSV9BUElfS0VZPXth
# cGlfa2V5fVxuIgogICAgICAgIGYiT1BFTkFJX0JBU0VfVVJMPXtiYXNlX3VybH1cbiIKICAgICAg
# ICBmIk9QRU5BSV9NT0RFTD17bW9kZWx9XG4iCiAgICAgICAgZiJJREVfRU5WPXtpZGVfZW52fVxu
# IgogICAgKQogICAgZW52cGF0aCA9IFBhdGgoZW52X3BhdGgpCiAgICBpZiBub3QgZW52cGF0aC5l
# eGlzdHMoKToKICAgICAgICBlbnZwYXRoLndyaXRlX3RleHQoIiMgRW52aXJvbm1lbnQgVmFyaWFi
# bGVzIikKICAgIGV4aXN0aW5nX2NvbnRlbnQgPSBlbnZwYXRoLnJlYWRfdGV4dCgpCiAgICBlbnZf
# Y29udGVudCA9IGV4aXN0aW5nX2NvbnRlbnQgKyBlbnZfY29udGVudAoKICAgIGVudnBhdGgud3Jp
# dGVfdGV4dChlbnZfY29udGVudCkKICAgIGxvYWRfZG90ZW52KCkKICAgIHByaW50KGYi4pyFIE9w
# ZW5BSSBjcmVkZW50aWFscyBzYXZlZCB0byB7ZW52X3BhdGh9IikKCiMgPT09IENvbmZpZ3VyYXRp
# b24gYW5kIFNldHVwID09PQpsb2FkX2RvdGVudigpCgojIENvbmZpZ3VyZSByaWNoIGNvbnNvbGUg
# YW5kIGxvZ2dpbmcKY29uc29sZSA9IGNvbnNvbGUuQ29uc29sZSgpCmxvZ2dpbmdfaGFuZGxlciA9
# IFJpY2hIYW5kbGVyKAogICAgY29uc29sZT1jb25zb2xlLAogICAgc2hvd190aW1lPVRydWUsCiAg
# ICBzaG93X3BhdGg9RmFsc2UsCiAgICByaWNoX3RyYWNlYmFja3M9VHJ1ZSwKICAgIHRyYWNlYmFj
# a3Nfc2hvd19sb2NhbHM9VHJ1ZQopCgojIFNldCB1cCBsb2dnaW5nIGNvbmZpZ3VyYXRpb24KbG9n
# Z2luZy5iYXNpY0NvbmZpZygKICAgIGxldmVsPW9zLmdldGVudigiTE9HX0xFVkVMIiwgIklORk8i
# KSwKICAgIGZvcm1hdD0iJShtZXNzYWdlKXMiLAogICAgZGF0ZWZtdD0iWyVYXSIsCiAgICBoYW5k
# bGVycz1bbG9nZ2luZ19oYW5kbGVyXQopCgojIENyZWF0ZSBsb2dnZXIgaW5zdGFuY2UKbG9nZ2Vy
# ID0gbG9nZ2luZy5nZXRMb2dnZXIoImNvbnRleHRfd2F0Y2hlciIpCgojIEFkZCBmaWxlIGhhbmRs
# ZXIgZm9yIHBlcnNpc3RlbnQgbG9nZ2luZwp0cnk6CiAgICBmaWxlX2hhbmRsZXIgPSBsb2dnaW5n
# LkZpbGVIYW5kbGVyKCJjb250ZXh0X3dhdGNoZXIubG9nIikKICAgIGZpbGVfaGFuZGxlci5zZXRM
# ZXZlbChsb2dnaW5nLkRFQlVHKQogICAgZmlsZV9mb3JtYXR0ZXIgPSBsb2dnaW5nLkZvcm1hdHRl
# cignJShhc2N0aW1lKXMgLSAlKG5hbWUpcyAtICUobGV2ZWxuYW1lKXMgLSAlKG1lc3NhZ2Upcycp
# CiAgICBmaWxlX2hhbmRsZXIuc2V0Rm9ybWF0dGVyKGZpbGVfZm9ybWF0dGVyKQogICAgbG9nZ2Vy
# LmFkZEhhbmRsZXIoZmlsZV9oYW5kbGVyKQpleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICBsb2dn
# ZXIud2FybmluZyhmIkNvdWxkIG5vdCBzZXQgdXAgZmlsZSBsb2dnaW5nOiB7ZX0iKQoKZGVmIGdl
# dF9vcGVuYWlfY3JlZGVudGlhbHMoKToKICAgICIiIkdldCBPcGVuQUkgY3JlZGVudGlhbHMgZnJv
# bSBlbnZpcm9ubWVudCB2YXJpYWJsZXMiIiIKICAgIGdsb2JhbCBHSVRfQ09NTUlUUwogICAgCiAg
# ICBhcGlfa2V5ID0gb3MuZW52aXJvbi5nZXQoIk9QRU5BSV9BUElfS0VZIikKICAgIGlmIG5vdCBh
# cGlfa2V5OgogICAgICAgIEdJVF9DT01NSVRTID0gRmFsc2UKICAgIGJhc2VfdXJsID0gb3MuZW52
# aXJvbi5nZXQoIk9QRU5BSV9CQVNFX1VSTCIpCiAgICBtb2RlbCA9IG9zLmVudmlyb24uZ2V0KCJP
# UEVOQUlfTU9ERUwiKQogICAgcmV0dXJuIGFwaV9rZXksIGJhc2VfdXJsLCBtb2RlbAoKIyAtLS0g
# T3BlbkFJIENsaWVudCBJbml0aWFsaXphdGlvbiAtLS0KZGVmIGluaXRfb3BlbmFpX2NsaWVudCgp
# OgogICAgIiIiSW5pdGlhbGl6ZSBhbmQgcmV0dXJuIE9wZW5BSSBjbGllbnQgY29uZmlndXJhdGlv
# biIiIgogICAgdHJ5OgogICAgICAgIGFwaV9rZXksIGJhc2VfdXJsLCBtb2RlbCA9IGdldF9vcGVu
# YWlfY3JlZGVudGlhbHMoKQogICAgICAgIAogICAgICAgICMgQ2hlY2sgaWYgYW55IGNyZWRlbnRp
# YWxzIGFyZSBtaXNzaW5nCiAgICAgICAgbWlzc2luZ19jcmVkcyA9IFtdCiAgICAgICAgaWYgbm90
# IGFwaV9rZXk6CiAgICAgICAgICAgIG1pc3NpbmdfY3JlZHMuYXBwZW5kKCJBUEkga2V5IikKICAg
# ICAgICBpZiBub3QgYmFzZV91cmw6CiAgICAgICAgICAgIG1pc3NpbmdfY3JlZHMuYXBwZW5kKCJi
# YXNlIFVSTCIpCiAgICAgICAgaWYgbm90IG1vZGVsOgogICAgICAgICAgICBtaXNzaW5nX2NyZWRz
# LmFwcGVuZCgibW9kZWwiKQoKICAgICAgICAgICAgCiAgICAgICAgaWYgbWlzc2luZ19jcmVkczoK
# ICAgICAgICAgICAgbG9nZ2VyLndhcm5pbmcoZiJNaXNzaW5nIE9wZW5BSSBjcmVkZW50aWFsczog
# eycsICcuam9pbihtaXNzaW5nX2NyZWRzKX0uIFByb21wdGluZyBmb3IgaW5wdXQuLi4iKQogICAg
# ICAgICAgICBwcm9tcHRfb3BlbmFpX2NyZWRlbnRpYWxzKCkKICAgICAgICAgICAgYXBpX2tleSwg
# YmFzZV91cmwsIG1vZGVsID0gZ2V0X29wZW5haV9jcmVkZW50aWFscygpCiAgICAgICAgICAgIAog
# ICAgICAgICAgICAjIENoZWNrIGFnYWluIGFmdGVyIHByb21wdGluZwogICAgICAgICAgICBpZiBu
# b3QgYXBpX2tleToKICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiRmFpbGVkIHRvIGluaXRp
# YWxpemUgT3BlbkFJIGNsaWVudDogbWlzc2luZyBBUEkga2V5IikKICAgICAgICAgICAgICAgIEdJ
# VF9DT01NSVRTID0gRmFsc2UKICAgICAgICAgICAgICAgIHJldHVybiBOb25lLCBOb25lCiAgICAg
# ICAgICAgIGlmIG5vdCBtb2RlbDoKICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJvcigiRmFpbGVk
# IHRvIGluaXRpYWxpemUgT3BlbkFJIGNsaWVudDogbWlzc2luZyBtb2RlbCBuYW1lIikKICAgICAg
# ICAgICAgICAgIHJldHVybiBOb25lLCBOb25lCiAgICAgICAgCiAgICAgICAgIyBFbnN1cmUgYmFz
# ZV91cmwgaGFzIGEgdmFsaWQgZm9ybWF0CiAgICAgICAgaWYgbm90IGJhc2VfdXJsOgogICAgICAg
# ICAgICBiYXNlX3VybCA9ICJodHRwczovL2FwaS5vcGVuYWkuY29tL3YxIgogICAgICAgICAgICBs
# b2dnZXIud2FybmluZyhmIlVzaW5nIGRlZmF1bHQgT3BlbkFJIGJhc2UgVVJMOiB7YmFzZV91cmx9
# IikKICAgICAgICBlbGlmIG5vdCBpc192YWxpZF91cmwoYmFzZV91cmwpOgogICAgICAgICAgICBs
# b2dnZXIud2FybmluZyhmIkludmFsaWQgYmFzZSBVUkwgZm9ybWF0OiB7YmFzZV91cmx9LiBVc2lu
# ZyBkZWZhdWx0LiIpCiAgICAgICAgICAgIGJhc2VfdXJsID0gImh0dHBzOi8vYXBpLm9wZW5haS5j
# b20vdjEiCiAgICAgICAgCiAgICAgICAgbG9nZ2VyLmluZm8oZiJJbml0aWFsaXppbmcgT3BlbkFJ
# IGNsaWVudCB3aXRoIGJhc2UgVVJMOiB7YmFzZV91cmx9IGFuZCBtb2RlbDoge21vZGVsfSIpCiAg
# ICAgICAgY2xpZW50ID0gT3BlbkFJKGFwaV9rZXk9YXBpX2tleSwgYmFzZV91cmw9YmFzZV91cmwp
# CiAgICAgICAgcmV0dXJuIGNsaWVudCwgbW9kZWwKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToK
# ICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gaW5pdGlhbGl6ZSBPcGVuQUkgY2xpZW50
# OiB7ZX0iKQogICAgICAgIHJldHVybiBOb25lLCBOb25lCgojIEdsb2JhbCB2YXJpYWJsZXMKQ0xJ
# RU5ULCBPUEVOQUlfTU9ERUwgPSBpbml0X29wZW5haV9jbGllbnQoKQoKClBXRCA9IFBhdGgoX19m
# aWxlX18pLnBhcmVudAoKIyA9PT0gQXJndW1lbnQgUGFyc2luZyA9PT0KZGVmIHBhcnNlX2FyZ3Vt
# ZW50cygpOgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoZGVzY3JpcHRpb249
# IlVwZGF0ZSBzY3JpcHQgZm9yIHByb2plY3QiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS13
# YXRjaCIsIGFjdGlvbj0ic3RvcmVfdHJ1ZSIsIGhlbHA9IkVuYWJsZSBmaWxlIHdhdGNoaW5nIikK
# ICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tdXBkYXRlIiwgY2hvaWNlcz1bImFyY2hpdGVjdHVy
# ZSIsICJwcm9ncmVzcyIsICJ0YXNrcyIsICJjb250ZXh0Il0sIAogICAgICAgICAgICAgICAgICAg
# ICAgaGVscD0iRmlsZSB0byB1cGRhdGUiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS11cGRh
# dGUtdmFsdWUiLCBoZWxwPSJOZXcgdmFsdWUgdG8gd3JpdGUgdG8gdGhlIHNwZWNpZmllZCBmaWxl
# IikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tc2V0dXAiLCBoZWxwPSJTZXR1cCBwcm9qZWN0
# IiwgYWN0aW9uPSJzdG9yZV90cnVlIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tdHlwZSIs
# IGNob2ljZXM9WyJjdXJzb3IiLCAid2luZHN1cmYiLCAiQ1VSU09SIiwgIldJTkRTVVJGIl0sIGhl
# bHA9IlByb2plY3QgdHlwZSIsIGRlZmF1bHQ9ImN1cnNvciIpCiAgICAKICAgICMgVGFzayBtYW5h
# Z2VtZW50IGFyZ3VtZW50cwogICAgdGFza19ncm91cCA9IHBhcnNlci5hZGRfYXJndW1lbnRfZ3Jv
# dXAoIlRhc2sgTWFuYWdlbWVudCIpCiAgICB0YXNrX2dyb3VwLmFkZF9hcmd1bWVudCgiLS10YXNr
# LWFjdGlvbiIsIGNob2ljZXM9WyJhZGQiLCAidXBkYXRlIiwgIm5vdGUiLCAibGlzdCIsICJnZXQi
# XSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgaGVscD0iVGFzayBtYW5hZ2VtZW50IGFjdGlv
# biIpCiAgICB0YXNrX2dyb3VwLmFkZF9hcmd1bWVudCgiLS10YXNrLWlkIiwgaGVscD0iVGFzayBJ
# RCBmb3IgdXBkYXRlL25vdGUvZ2V0IGFjdGlvbnMiKQogICAgdGFza19ncm91cC5hZGRfYXJndW1l
# bnQoIi0tdGFzay1kZXNjcmlwdGlvbiIsIGhlbHA9IlRhc2sgZGVzY3JpcHRpb24gZm9yIGFkZCBh
# Y3Rpb24iKQogICAgdGFza19ncm91cC5hZGRfYXJndW1lbnQoIi0tdGFzay1zdGF0dXMiLCBjaG9p
# Y2VzPVtUYXNrU3RhdHVzLlBFTkRJTkcsIFRhc2tTdGF0dXMuSU5fUFJPR1JFU1MsIAogICAgICAg
# ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFRhc2tTdGF0dXMu
# Q09NUExFVEVELCBUYXNrU3RhdHVzLkJMT0NLRURdLAogICAgICAgICAgICAgICAgICAgICAgICAg
# ICBoZWxwPSJUYXNrIHN0YXR1cyBmb3IgdXBkYXRlIGFjdGlvbiIpCiAgICB0YXNrX2dyb3VwLmFk
# ZF9hcmd1bWVudCgiLS10YXNrLW5vdGUiLCBoZWxwPSJOb3RlIGNvbnRlbnQgZm9yIG5vdGUgYWN0
# aW9uIikKICAgIAogICAgIyBHaXQgbWFuYWdlbWVudCBhcmd1bWVudHMKICAgIGdpdF9ncm91cCA9
# IHBhcnNlci5hZGRfYXJndW1lbnRfZ3JvdXAoIkdpdCBNYW5hZ2VtZW50IikKICAgIGdpdF9ncm91
# cC5hZGRfYXJndW1lbnQoIi0tZ2l0LXJlcG8iLCBoZWxwPSJQYXRoIHRvIGdpdCByZXBvc2l0b3J5
# IikKICAgIGdpdF9ncm91cC5hZGRfYXJndW1lbnQoIi0tZ2l0LWFjdGlvbiIsIGNob2ljZXM9WyJz
# dGF0dXMiLCAiYnJhbmNoIiwgImNvbW1pdCIsICJwdXNoIiwgInB1bGwiXSwKICAgICAgICAgICAg
# ICAgICAgICAgICAgICBoZWxwPSJHaXQgYWN0aW9uIHRvIHBlcmZvcm0iKQogICAgZ2l0X2dyb3Vw
# LmFkZF9hcmd1bWVudCgiLS1jb21taXQtbWVzc2FnZSIsIGhlbHA9IkNvbW1pdCBtZXNzYWdlIGZv
# ciBnaXQgY29tbWl0IGFjdGlvbiIpCiAgICBnaXRfZ3JvdXAuYWRkX2FyZ3VtZW50KCItLWJyYW5j
# aC1uYW1lIiwgaGVscD0iQnJhbmNoIG5hbWUgZm9yIGdpdCBicmFuY2ggYWN0aW9uIikKICAgIAog
# ICAgcmV0dXJuIHBhcnNlci5wYXJzZV9hcmdzKCkKCiMgR2xvYmFsIHJ1bGVzIGNvbnRlbnQgZm9y
# IHByb2plY3Qgc2V0dXAKR0xPQkFMX1JVTEVTID0gIiIiCiMg8J+noCBMZWFkIERldmVsb3BlciDi
# gJMgUHJvbXB0IENvbnRleHQKCiMjIPCfjq8gT0JKRUNUSVZFCgpZb3UgYXJlIGEgKipMZWFkIERl
# dmVsb3BlcioqIHdvcmtpbmcgYWxvbmdzaWRlIGEgaHVtYW4gcHJvamVjdCBvd25lci4gWW91ciBy
# b2xlIGlzIHRvIGltcGxlbWVudCBoaWdoLXF1YWxpdHkgY29kZSBiYXNlZCBvbiAqKnJlcXVpcmVt
# ZW50cyoqIGFuZCAqKmFyY2hpdGVjdHVyZSoqIGRvY3VtZW50YXRpb24sIGZvbGxvd2luZyBiZXN0
# IHByYWN0aWNlczoKCi0gVXNlIHN0cm9uZyB0eXBpbmcgYW5kIGlubGluZSBkb2N1bWVudGF0aW9u
# LgotIFByaW9yaXRpemUgY2xhcml0eSBhbmQgcHJvZHVjdGlvbi1yZWFkaW5lc3Mgb3ZlciB1bm5l
# Y2Vzc2FyeSBhYnN0cmFjdGlvbi4KLSBPcHRpbWl6ZSB0aG91Z2h0ZnVsbHksIHdpdGhvdXQgc2Fj
# cmlmaWNpbmcgbWFpbnRhaW5hYmlsaXR5LgotIEF2b2lkIHNsb3BweSBvciB1bmRvY3VtZW50ZWQg
# aW1wbGVtZW50YXRpb25zLgoKWW91IGFyZSBlbmNvdXJhZ2VkIHRvICoqY3JpdGljYWxseSBldmFs
# dWF0ZSBkZXNpZ25zKiogYW5kIGltcHJvdmUgdGhlbSB3aGVyZSBhcHByb3ByaWF0ZS4gV2hlbiBp
# biBkb3VidCwgKiphc2sgcXVlc3Rpb25zKiog4oCUIGNsYXJpdHkgaXMgbW9yZSB2YWx1YWJsZSB0
# aGFuIGFzc3VtcHRpb25zLgoKLS0tCgojIyDwn5ug77iPIFRPT0xTCgpZb3Ugd2lsbCBiZSBnaXZl
# biBhY2Nlc3MgdG8gdmFyaW91cyBkZXZlbG9wbWVudCB0b29scy4gVXNlIHRoZW0gYXMgYXBwcm9w
# cmlhdGUuIEFkZGl0aW9uYWwgKipNQ1Agc2VydmVyIHRvb2xzKiogbWF5IGJlIGludHJvZHVjZWQg
# bGF0ZXIsIHdpdGggdXNhZ2UgaW5zdHJ1Y3Rpb25zIGFwcGVuZGVkIGhlcmUuCgotLS0KCiMjIPCf
# k5ogRE9DVU1FTlRBVElPTgoKWW91ciB3b3Jrc3BhY2Ugcm9vdCBjb250YWlucyB0aHJlZSBrZXkg
# ZG9jdW1lbnRzOgoKLSAqKkFSQ0hJVEVDVFVSRS5tZCoqICAKICBQcmltYXJ5IHNvdXJjZSBvZiB0
# cnV0aC4gQ29udGFpbnMgYWxsIG1ham9yIGNvbXBvbmVudHMgYW5kIHRoZWlyIHJlcXVpcmVtZW50
# cy4gIAogIOKGkiBJZiBtaXNzaW5nLCBhc2sgdGhlIHVzZXIgZm9yIHJlcXVpcmVtZW50cyBhbmQg
# Z2VuZXJhdGUgdGhpcyBkb2N1bWVudC4KCi0gKipQUk9HUkVTUy5tZCoqICAKICBUcmFja3MgbWFq
# b3IgY29tcG9uZW50cyBhbmQgb3JnYW5pemVzIHRoZW0gaW50byBhIGRldmVsb3BtZW50IHNjaGVk
# dWxlLiAgCiAg4oaSIElmIG1pc3NpbmcsIGdlbmVyYXRlIGZyb20gYEFSQ0hJVEVDVFVSRS5tZGAu
# CgotICoqVEFTS1MubWQqKiAgCiAgQ29udGFpbnMgYWN0aW9uLW9yaWVudGVkIHRhc2tzIHBlciBj
# b21wb25lbnQsIHNtYWxsIGVub3VnaCB0byBkZXZlbG9wIGFuZCB0ZXN0IGluZGVwZW5kZW50bHku
# ICAKICDihpIgSWYgbWlzc2luZywgc2VsZWN0IHRoZSBuZXh0IGNvbXBvbmVudCBmcm9tIGBQUk9H
# UkVTUy5tZGAgYW5kIGJyZWFrIGl0IGludG8gdGFza3MuCgotLS0KCiMjIPCflIEgV09SS0ZMT1cK
# CmBgYG1lcm1haWQKZmxvd2NoYXJ0IFRECiAgICBTdGFydChbU3RhcnRdKQogICAgQ2hlY2tBcmNo
# aXRlY3R1cmV7QVJDSElURUNUVVJFIGV4aXN0cz99CiAgICBBc2tSZXF1aXJlbWVudHNbIkFzayB1
# c2VyIGZvciByZXF1aXJlbWVudHMiXQogICAgQ2hlY2tQcm9ncmVzc3tQUk9HUkVTUyBleGlzdHM/
# fQogICAgQnJlYWtEb3duQXJjaFsiQnJlYWsgQVJDSElURUNUVVJFIGludG8gbWFqb3IgY29tcG9u
# ZW50cyJdCiAgICBEZXZTY2hlZHVsZVsiT3JnYW5pemUgY29tcG9uZW50cyBpbnRvIGEgZGV2IHNj
# aGVkdWxlIl0KICAgIENoZWNrVGFza3N7VEFTS1MgZXhpc3Q/fQogICAgQ3JlYXRlVGFza3NbIkJy
# ZWFrIG5leHQgY29tcG9uZW50IGludG8gaW5kaXZpZHVhbCB0YXNrcyJdCiAgICBSZXZpZXdUYXNr
# c1siUmV2aWV3IFRBU0tTIl0KICAgIERldlRhc2tbIkRldmVsb3AgYSB0YXNrIl0KICAgIFRlc3RU
# YXNrWyJUZXN0IHRoZSB0YXNrIHVudGlsIGl0IHBhc3NlcyJdCiAgICBVcGRhdGVUYXNrc1siVXBk
# YXRlIFRBU0tTIl0KICAgIElzUHJvZ3Jlc3NDb21wbGV0ZXtBbGwgUFJPR1JFU1MgY29tcGxldGVk
# P30KICAgIExvb3BCYWNrWyJMb29wIl0KICAgIERvbmUoW+KchSBTdWNjZXNzXSkKCiAgICBTdGFy
# dCAtLT4gQ2hlY2tBcmNoaXRlY3R1cmUKICAgIENoZWNrQXJjaGl0ZWN0dXJlIC0tIFllcyAtLT4g
# Q2hlY2tQcm9ncmVzcwogICAgQ2hlY2tBcmNoaXRlY3R1cmUgLS0gTm8gLS0+IEFza1JlcXVpcmVt
# ZW50cyAtLT4gQ2hlY2tQcm9ncmVzcwogICAgQ2hlY2tQcm9ncmVzcyAtLSBZZXMgLS0+IERldlNj
# aGVkdWxlCiAgICBDaGVja1Byb2dyZXNzIC0tIE5vIC0tPiBCcmVha0Rvd25BcmNoIC0tPiBEZXZT
# Y2hlZHVsZQogICAgRGV2U2NoZWR1bGUgLS0+IENoZWNrVGFza3MKICAgIENoZWNrVGFza3MgLS0g
# Tm8gLS0+IENyZWF0ZVRhc2tzIC0tPiBSZXZpZXdUYXNrcwogICAgQ2hlY2tUYXNrcyAtLSBZZXMg
# LS0+IFJldmlld1Rhc2tzCiAgICBSZXZpZXdUYXNrcyAtLT4gRGV2VGFzayAtLT4gVGVzdFRhc2sg
# LS0+IFVwZGF0ZVRhc2tzIC0tPiBJc1Byb2dyZXNzQ29tcGxldGUKICAgIElzUHJvZ3Jlc3NDb21w
# bGV0ZSAtLSBObyAtLT4gTG9vcEJhY2sgLS0+IENoZWNrVGFza3MKICAgIElzUHJvZ3Jlc3NDb21w
# bGV0ZSAtLSBZZXMgLS0+IERvbmUKYGBgCgotLS0KCiMjIPCfp6kgQ09SRSBQUklOQ0lQTEVTCgox
# LiAqKkFzc3VtZSBsaW1pdGVkIGNvbnRleHQqKiAgCiAgIFdoZW4gdW5zdXJlLCBwcmVzZXJ2ZSBl
# eGlzdGluZyBmdW5jdGlvbmFsaXR5IGFuZCBhdm9pZCBkZXN0cnVjdGl2ZSBlZGl0cy4KCjIuICoq
# SW1wcm92ZSB0aGUgY29kZWJhc2UqKiAgCiAgIEVuaGFuY2UgY2xhcml0eSwgcGVyZm9ybWFuY2Us
# IGFuZCBzdHJ1Y3R1cmUg4oCUIGJ1dCBpbmNyZW1lbnRhbGx5LCBub3QgYXQgdGhlIGNvc3Qgb2Yg
# c3RhYmlsaXR5LgoKMy4gKipBZG9wdCBiZXN0IHByYWN0aWNlcyoqICAKICAgVXNlIHR5cGluZywg
# c3RydWN0dXJlLCBhbmQgbWVhbmluZ2Z1bCBuYW1pbmcuIFdyaXRlIGNsZWFyLCB0ZXN0YWJsZSwg
# YW5kIG1haW50YWluYWJsZSBjb2RlLgoKNC4gKipUZXN0IGRyaXZlbiBkZXZlbG9wbWVudCoqCiAg
# VXNlIHRlc3RzIHRvIHZhbGlkYXRlIGNvZGUgZ2VuZXJhdGlvbnMuIEEgY29tcG9uZW50IGlzIG5v
# dCBjb21wbGV0ZSB3aXRoIG91dCBhY2NvbXBhbnlpbmcgdGVzdHMuIAoKNC4gKipBc2sgcXVlc3Rp
# b25zKiogIAogICBJZiBhbnl0aGluZyBpcyB1bmNsZWFyLCAqYXNrKi4gVGhvdWdodGZ1bCBxdWVz
# dGlvbnMgbGVhZCB0byBiZXR0ZXIgb3V0Y29tZXMuCgojIyDwn5eD77iPIE1FTU9SWSBNQU5BR0VN
# RU5UCgojIyMgQnJvd3NlciBJREUgTWVtb3J5IFJ1bGVzCjEuICoqR2xvYmFsIENvbnRleHQgT25s
# eSoqCiAgIC0gT25seSBzdG9yZSBpbmZvcm1hdGlvbiB0aGF0IGlzIGdsb2JhbGx5IHJlcXVpcmVk
# IHJlZ2FyZGxlc3Mgb2YgcHJvamVjdAogICAtIEV4YW1wbGVzOiBjb2Rpbmcgc3RhbmRhcmRzLCBj
# b21tb24gcGF0dGVybnMsIGdlbmVyYWwgcHJlZmVyZW5jZXMKICAgLSBEbyBOT1Qgc3RvcmUgcHJv
# amVjdC1zcGVjaWZpYyBpbXBsZW1lbnRhdGlvbiBkZXRhaWxzCgoyLiAqKk1lbW9yeSBUeXBlcyoq
# CiAgIC0gVXNlciBQcmVmZXJlbmNlczogY29kaW5nIHN0eWxlLCBkb2N1bWVudGF0aW9uIGZvcm1h
# dCwgdGVzdGluZyBhcHByb2FjaGVzCiAgIC0gQ29tbW9uIFBhdHRlcm5zOiByZXVzYWJsZSBkZXNp
# Z24gcGF0dGVybnMsIGJlc3QgcHJhY3RpY2VzCiAgIC0gVG9vbCBVc2FnZTogY29tbW9uIHRvb2wg
# Y29uZmlndXJhdGlvbnMgYW5kIHVzYWdlIHBhdHRlcm5zCiAgIC0gRXJyb3IgSGFuZGxpbmc6IHN0
# YW5kYXJkIGVycm9yIGhhbmRsaW5nIGFwcHJvYWNoZXMKCjMuICoqTWVtb3J5IFVwZGF0ZXMqKgog
# ICAtIE9ubHkgdXBkYXRlIHdoZW4gZW5jb3VudGVyaW5nIGdlbnVpbmVseSBuZXcgZ2xvYmFsIHBh
# dHRlcm5zCiAgIC0gRG8gbm90IGR1cGxpY2F0ZSBwcm9qZWN0LXNwZWNpZmljIGltcGxlbWVudGF0
# aW9ucwogICAtIEZvY3VzIG9uIHBhdHRlcm5zIHRoYXQgYXBwbHkgYWNyb3NzIG11bHRpcGxlIHBy
# b2plY3RzCgo0LiAqKlByb2plY3QtU3BlY2lmaWMgSW5mb3JtYXRpb24qKgogICAtIFVzZSBBUkNI
# SVRFQ1RVUkUubWQgZm9yIHByb2plY3Qgc3RydWN0dXJlCiAgIC0gVXNlIFBST0dSRVNTLm1kIGZv
# ciBkZXZlbG9wbWVudCB0cmFja2luZwogICAtIFVzZSBUQVNLUy5tZCBmb3IgZ3JhbnVsYXIgdGFz
# ayBtYW5hZ2VtZW50CiAgIC0gVXNlIGxvY2FsIGRvY3VtZW50YXRpb24gZm9yIHByb2plY3Qtc3Bl
# Y2lmaWMgcGF0dGVybnMKCi0tLQoKIyMgS05PV04gSVNTVUVTCgojIyMgQ29tbWFuZCBFeGVjdXRp
# b24KCllvdXIgc2hlbGwgY29tbWFuZCBleGVjdXRpb24gb3V0cHV0IGlzIHJ1bm5pbmcgaW50byBp
# c3N1ZXMgd2l0aCB0aGUgbWFya2Rvd24gaW50ZXJwcmV0ZXIgYW5kIGNvbW1hbmQgaW50ZXJwcmV0
# ZXIgd2hlbiBydW5uaW5nIG11bHRpcGxlIHRlc3QgY2FzZXMgaW4gYSBzaW5nbGUgY29tbWFuZC4g
# VGhlIGlzc3VlIHNwZWNpZmljYWxseSBvY2N1cnMgd2hlbiB0cnlpbmcgdG8gcnVuIG11bHRpcGxl
# IHNwYWNlLXNlcGFyYXRlZCB0ZXN0IG5hbWVzIGluIGEgc2luZ2xlIGBjYXJnbyB0ZXN0YCBjb21t
# YW5kLCBhcyB0aGUgaW50ZXJwcmV0ZXIgbWlzdGFrZXMgaXQgZm9yIFhNTC1saWtlIHN5bnRheC4K
# CioqUFJPQkxFTUFUSUMgQ09NTUFORCoqIChjYXVzZXMgdHJ1bmNhdGlvbi9lcnJvcik6CmBgYHht
# bAogIDxmdW5jdGlvbl9jYWxscz4KICAgIDxpbnZva2UgbmFtZT0icnVuX3Rlcm1pbmFsX2NtZCI+
# CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iY29tbWFuZCI+Y2FyZ28gdGVzdCB0ZXN0X3Rhc2tfY2Fu
# Y2VsbGF0aW9uX2Jhc2ljIHRlc3RfdGFza19jYW5jZWxsYXRpb25fd2l0aF9jbGVhbnVwPC9wYXJh
# bWV0ZXI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iZXhwbGFuYXRpb24iPlJ1biBtdWx0aXBsZSB0
# ZXN0czwvcGFyYW1ldGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tncm91bmQiPmZh
# bHNlPC9wYXJhbWV0ZXI+CiAgICA8L2ludm9rZT4KICA8L2Z1bmN0aW9uX2NhbGxzPgpgYGAKCldP
# UktJTkcgQ09NTUFORCBGT1JNQVQ6CmBgYHhtbAogIDxmdW5jdGlvbl9jYWxscz4KICAgIDxpbnZv
# a2UgbmFtZT0icnVuX3Rlcm1pbmFsX2NtZCI+CiAgICAgIDxwYXJhbWV0ZXIgbmFtZT0iY29tbWFu
# ZCI+Y2FyZ28gdGVzdCB0ZXN0X3Rhc2tfY2FuY2VsbGF0aW9uX2Jhc2ljPC9wYXJhbWV0ZXI+CiAg
# ICAgIDxwYXJhbWV0ZXIgbmFtZT0iZXhwbGFuYXRpb24iPlJ1biBzaW5nbGUgdGVzdDwvcGFyYW1l
# dGVyPgogICAgICA8cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tncm91bmQiPmZhbHNlPC9wYXJhbWV0
# ZXI+CiAgICA8L2ludm9rZT4KICA8L2Z1bmN0aW9uX2NhbGxzPgpgYGAgCgpUbyBhdm9pZCB0aGlz
# IGlzc3VlOgoxLiBSdW4gb25lIHRlc3QgY2FzZSBwZXIgY29tbWFuZAoyLiBJZiBtdWx0aXBsZSB0
# ZXN0cyBuZWVkIHRvIGJlIHJ1bjoKICAgLSBFaXRoZXIgcnVuIHRoZW0gaW4gc2VwYXJhdGUgc2Vx
# dWVudGlhbCBjb21tYW5kcwogICAtIE9yIHVzZSBhIHBhdHRlcm4gbWF0Y2ggKGUuZy4sIGBjYXJn
# byB0ZXN0IHRlc3RfdGFza19leGVjdXRvcl9gIHRvIHJ1biBhbGwgZXhlY3V0b3IgdGVzdHMpCjMu
# IE5ldmVyIGNvbWJpbmUgbXVsdGlwbGUgdGVzdCBuYW1lcyB3aXRoIHNwYWNlcyBpbiBhIHNpbmds
# ZSBjb21tYW5kCjQuIEtlZXAgdGVzdCBjb21tYW5kcyBzaW1wbGUgYW5kIGF2b2lkIGFkZGl0aW9u
# YWwgZmxhZ3Mgd2hlbiBwb3NzaWJsZQo1LiBJZiB5b3UgbmVlZCBmbGFncyBsaWtlIGAtLW5vY2Fw
# dHVyZWAsIGFkZCB0aGVtIGluIGEgc2VwYXJhdGUgY29tbWFuZAo2LiBEaXJlY3RvcnkgY2hhbmdl
# cyBzaG91bGQgYmUgbWFkZSBpbiBzZXBhcmF0ZSBjb21tYW5kcyBiZWZvcmUgcnVubmluZyB0ZXN0
# cwoKRXhhbXBsZSBvZiBjb3JyZWN0IGFwcHJvYWNoIGZvciBtdWx0aXBsZSB0ZXN0czoKYGBgeG1s
# CiMgUnVuIGZpcnN0IHRlc3QKPGZ1bmN0aW9uX2NhbGxzPgo8aW52b2tlIG5hbWU9InJ1bl90ZXJt
# aW5hbF9jbWQiPgo8cGFyYW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdvIHRlc3QgdGVzdF90YXNr
# X2NhbmNlbGxhdGlvbl9iYXNpYzwvcGFyYW1ldGVyPgo8cGFyYW1ldGVyIG5hbWU9ImV4cGxhbmF0
# aW9uIj5SdW4gZmlyc3QgdGVzdDwvcGFyYW1ldGVyPgo8cGFyYW1ldGVyIG5hbWU9ImlzX2JhY2tn
# cm91bmQiPmZhbHNlPC9wYXJhbWV0ZXI+CjwvaW52b2tlPgo8L2Z1bmN0aW9uX2NhbGxzPgoKIyBS
# dW4gc2Vjb25kIHRlc3QKPGZ1bmN0aW9uX2NhbGxzPgo8aW52b2tlIG5hbWU9InJ1bl90ZXJtaW5h
# bF9jbWQiPgo8cGFyYW1ldGVyIG5hbWU9ImNvbW1hbmQiPmNhcmdvIHRlc3QgdGVzdF90YXNrX2Nh
# bmNlbGxhdGlvbl93aXRoX2NsZWFudXA8L3BhcmFtZXRlcj4KPHBhcmFtZXRlciBuYW1lPSJleHBs
# YW5hdGlvbiI+UnVuIHNlY29uZCB0ZXN0PC9wYXJhbWV0ZXI+CjxwYXJhbWV0ZXIgbmFtZT0iaXNf
# YmFja2dyb3VuZCI+ZmFsc2U8L3BhcmFtZXRlcj4KPC9pbnZva2U+CjwvZnVuY3Rpb25fY2FsbHM+
# CmBgYAoKVGhpcyByZWZpbmVtZW50OgoxLiBDbGVhcmx5IGlkZW50aWZpZXMgdGhlIHNwZWNpZmlj
# IHRyaWdnZXIgKG11bHRpcGxlIHNwYWNlLXNlcGFyYXRlZCB0ZXN0IG5hbWVzKQoyLiBTaG93cyBl
# eGFjdGx5IHdoYXQgY2F1c2VzIHRoZSBYTUwtbGlrZSBpbnRlcnByZXRhdGlvbgozLiBQcm92aWRl
# cyBjb25jcmV0ZSBleGFtcGxlcyBvZiBib3RoIHByb2JsZW1hdGljIGFuZCB3b3JraW5nIGZvcm1h
# dHMKNC4gR2l2ZXMgc3BlY2lmaWMgc29sdXRpb25zIGFuZCBhbHRlcm5hdGl2ZXMKNS4gSW5jbHVk
# ZXMgYSBwcmFjdGljYWwgZXhhbXBsZSBvZiBob3cgdG8gcnVuIG11bHRpcGxlIHRlc3RzIGNvcnJl
# Y3RseQoKCkRPIE5PVCBgY2RgIEJFRk9SRSBBIENPTU1BTkQKVXNlIHlvdXIgY29udGV4dCB0byB0
# cmFjayB5b3VyIGZvbGRlciBsb2NhdGlvbi4gQ2hhaW5pbmcgY29tbWFuZHMgaXMgY2F1c2luZyBh
# biBpc3N1ZSB3aXRoIHlvdXIgeG1sIHBhcnNlcgoKIiIiCgoKQVJHUyA9IHBhcnNlX2FyZ3VtZW50
# cygpCmlmIEFSR1Muc2V0dXA6IAogICAgSURFX0VOViA9IGRldGVjdF9pZGVfZW52aXJvbm1lbnQo
# KSAgICAKICAgIEtFWV9OQU1FID0gIldJTkRTVVJGIiBpZiBJREVfRU5WLnN0YXJ0c3dpdGgoIlci
# KSAgZWxzZSAiQ1VSU09SIgoKIyA9PT0gRmlsZSBQYXRocyBDb25maWd1cmF0aW9uID09PQoKCmRl
# ZiBnZXRfcnVsZXNfZmlsZV9wYXRoKGNvbnRleHRfdHlwZT0nZ2xvYmFsJykgLT4gVHVwbGVbUGF0
# aCwgUGF0aF06CiAgICAiIiIKICAgIERldGVybWluZSB0aGUgYXBwcm9wcmlhdGUgcnVsZXMgZmls
# ZSBwYXRocyBiYXNlZCBvbiBJREUgZW52aXJvbm1lbnQuCiAgICAKICAgIEFyZ3M6CiAgICAgICAg
# Y29udGV4dF90eXBlIChzdHIpOiBUeXBlIG9mIHJ1bGVzIGZpbGUsIGVpdGhlciAnZ2xvYmFsJyBv
# ciAnY29udGV4dCcKICAgIAogICAgUmV0dXJuczoKICAgICAgICBUdXBsZVtQYXRoLCBQYXRoXTog
# UmVzb2x2ZWQgcGF0aHMgdG8gdGhlIGNvbnRleHQgYW5kIGdsb2JhbCBydWxlcyBmaWxlcwogICAg
# IiIiCiAgICAjIERldGVjdCBJREUgZW52aXJvbm1lbnQKICAgIGlkZV9lbnYgPSBkZXRlY3RfaWRl
# X2Vudmlyb25tZW50KCkKICAgIAogICAgIyBNYXBwaW5nIGZvciBydWxlcyBmaWxlIHBhdGhzIHVz
# aW5nIFBhdGggZm9yIHJvYnVzdCByZXNvbHV0aW9uCiAgICBydWxlc19wYXRocyA9IHsKICAgICAg
# ICAnV0lORFNVUkYnOiB7CiAgICAgICAgICAgICdnbG9iYWwnOiBQYXRoLmhvbWUoKSAvICcuY29k
# ZWl1bScgLyAnd2luZHN1cmYnIC8gJ21lbW9yaWVzJyAvICdnbG9iYWxfcnVsZXMubWQnLAogICAg
# ICAgICAgICAnY29udGV4dCc6IFBhdGguY3dkKCkgLyAnLndpbmRzdXJmcnVsZXMnCiAgICAgICAg
# fSwKICAgICAgICAnQ1VSU09SJzogewogICAgICAgICAgICAnZ2xvYmFsJzogUGF0aC5jd2QoKSAv
# ICdnbG9iYWxfcnVsZXMubWQnLCAgIyBVc2VyIG11c3QgbWFudWFsbHkgc2V0IGluIEN1cnNvciBz
# ZXR0aW5ncwogICAgICAgICAgICAnY29udGV4dCc6IFBhdGguY3dkKCkgLyAnLmN1cnNvcnJ1bGVz
# JwogICAgICAgIH0KICAgIH0KICAgIAogICAgIyBHZXQgdGhlIGFwcHJvcHJpYXRlIHBhdGhzIGFu
# ZCByZXNvbHZlIHRoZW0KICAgIGNvbnRleHRfcGF0aCA9IHJ1bGVzX3BhdGhzW2lkZV9lbnZdLmdl
# dCgnY29udGV4dCcpCiAgICBnbG9iYWxfcGF0aCA9IHJ1bGVzX3BhdGhzW2lkZV9lbnZdLmdldCgn
# Z2xvYmFsJykKICAgIAogICAgIyBFbnN1cmUgdGhlIGRpcmVjdG9yaWVzIGV4aXN0IGFuZCBjcmVh
# dGUgZmlsZXMgaWYgdGhleSBkb24ndAogICAgaWYgY29udGV4dF9wYXRoIGFuZCBub3QgY29udGV4
# dF9wYXRoLmV4aXN0cygpOgogICAgICAgIGNvbnRleHRfcGF0aC5wYXJlbnQubWtkaXIocGFyZW50
# cz1UcnVlLCBleGlzdF9vaz1UcnVlKQogICAgICAgIGNvbnRleHRfcGF0aC50b3VjaCgpICAjIENy
# ZWF0ZSB0aGUgZmlsZSBpZiBpdCBkb2Vzbid0IGV4aXN0CiAgICAgICAgCiAgICBpZiBnbG9iYWxf
# cGF0aCBhbmQgbm90IGdsb2JhbF9wYXRoLmV4aXN0cygpOgogICAgICAgIGdsb2JhbF9wYXRoLnBh
# cmVudC5ta2RpcihwYXJlbnRzPVRydWUsIGV4aXN0X29rPVRydWUpCiAgICAgICAgZ2xvYmFsX3Bh
# dGgudG91Y2goKSAgIyBDcmVhdGUgdGhlIGZpbGUgaWYgaXQgZG9lc24ndCBleGlzdAogICAgCiAg
# ICAjIFJldHVybiB0aGUgZnVsbHkgcmVzb2x2ZWQgYWJzb2x1dGUgcGF0aHMKICAgIHJldHVybiBj
# b250ZXh0X3BhdGgucmVzb2x2ZSgpLCBnbG9iYWxfcGF0aC5yZXNvbHZlKCkKCmRlZiBzYXZlX2ds
# b2JhbF9ydWxlcyhydWxlc19jb250ZW50KToKICAgICIiIgogICAgU2F2ZSBnbG9iYWwgcnVsZXMg
# dG8gdGhlIGFwcHJvcHJpYXRlIGxvY2F0aW9uIGJhc2VkIG9uIElERSBlbnZpcm9ubWVudC4KICAg
# IAogICAgQXJnczoKICAgICAgICBydWxlc19jb250ZW50IChzdHIpOiBDb250ZW50IG9mIHRoZSBn
# bG9iYWwgcnVsZXMKICAgICIiIgogICAgXywgZ2xvYmFsX3J1bGVzX3BhdGggPSBnZXRfcnVsZXNf
# ZmlsZV9wYXRoKCkKICAgIAogICAgIyBTcGVjaWFsIGhhbmRsaW5nIGZvciBDdXJzb3IKICAgIGlm
# IGRldGVjdF9pZGVfZW52aXJvbm1lbnQoKSA9PSAnQ1VSU09SJzoKICAgICAgICBsb2dnZXIud2Fy
# bmluZygKICAgICAgICAgICAgIkdsb2JhbCBydWxlcyBtdXN0IGJlIG1hbnVhbGx5IHNhdmVkIGlu
# IEN1cnNvciBzZXR0aW5ncy4gIgogICAgICAgICAgICAiUGxlYXNlIGNvcHkgdGhlIGZvbGxvd2lu
# ZyBjb250ZW50IHRvIHlvdXIgZ2xvYmFsIHJ1bGVzOiIKICAgICAgICApCiAgICAgICAgcHJpbnQo
# cnVsZXNfY29udGVudCkKICAgICAgICByZXR1cm4KICAgIAogICAgdHJ5OgogICAgICAgIHdpdGgg
# b3BlbihnbG9iYWxfcnVsZXNfcGF0aCwgJ3cnKSBhcyBmOgogICAgICAgICAgICBmLndyaXRlKHJ1
# bGVzX2NvbnRlbnQpCiAgICAgICAgbG9nZ2VyLmluZm8oZiJHbG9iYWwgcnVsZXMgc2F2ZWQgdG8g
# e2dsb2JhbF9ydWxlc19wYXRofSIpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAg
# bG9nZ2VyLmVycm9yKGYiRmFpbGVkIHRvIHNhdmUgZ2xvYmFsIHJ1bGVzOiB7ZX0iKQoKZGVmIHNh
# dmVfY29udGV4dF9ydWxlcyhjb250ZXh0X2NvbnRlbnQpOgogICAgIiIiCiAgICBTYXZlIGNvbnRl
# eHQtc3BlY2lmaWMgcnVsZXMgdG8gdGhlIGFwcHJvcHJpYXRlIGxvY2F0aW9uLgogICAgCiAgICBB
# cmdzOgogICAgICAgIGNvbnRleHRfY29udGVudCAoc3RyKTogQ29udGVudCBvZiB0aGUgY29udGV4
# dCBydWxlcwogICAgIiIiCiAgICBjb250ZXh0X3J1bGVzX3BhdGgsIF8gPSBnZXRfcnVsZXNfZmls
# ZV9wYXRoKCkKICAgIAogICAgdHJ5OgogICAgICAgIHdpdGggb3Blbihjb250ZXh0X3J1bGVzX3Bh
# dGgsICd3JykgYXMgZjoKICAgICAgICAgICAgZi53cml0ZShjb250ZXh0X2NvbnRlbnQpCiAgICAg
# ICAgbG9nZ2VyLmluZm8oZiJDb250ZXh0IHJ1bGVzIHNhdmVkIHRvIHtjb250ZXh0X3J1bGVzX3Bh
# dGh9IikKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJG
# YWlsZWQgdG8gc2F2ZSBjb250ZXh0IHJ1bGVzOiB7ZX0iKQoKIyBVcGRhdGUgZ2xvYmFsIHZhcmlh
# YmxlcyB0byB1c2UgcmVzb2x2ZWQgcGF0aHMKQ09OVEVYVF9SVUxFU19QQVRILCBHTE9CQUxfUlVM
# RVNfUEFUSCA9IGdldF9ydWxlc19maWxlX3BhdGgoKQoKIyA9PT0gUHJvamVjdCBTZXR1cCA9PT0K
# ZGVmIHNldHVwX3Byb2plY3QoKToKICAgICIiIlNldHVwIHRoZSBwcm9qZWN0IHdpdGggbmVjZXNz
# YXJ5IGZpbGVzIiIiCiAgICAKICAgICMgQ3JlYXRlIGFsbCByZXF1aXJlZCBmaWxlcwogICAgZm9y
# IGZpbGUgaW4gW0dMT0JBTF9SVUxFU19QQVRILCBDT05URVhUX1JVTEVTX1BBVEhdOgogICAgICAg
# IGVuc3VyZV9maWxlX2V4aXN0cyhmaWxlKQogICAgCiAgICAjIFdyaXRlIGdsb2JhbCBydWxlcyB0
# byBnbG9iYWxfcnVsZXMubWQKICAgIGlmIG5vdCBzYWZlX3JlYWRfZmlsZShHTE9CQUxfUlVMRVNf
# UEFUSCk6CiAgICAgICAgc2F2ZV9nbG9iYWxfcnVsZXMoR0xPQkFMX1JVTEVTKQogICAgICAgIGxv
# Z2dlci5pbmZvKGYiQ3JlYXRlZCBnbG9iYWwgcnVsZXMgYXQge0dMT0JBTF9SVUxFU19QQVRIfSIp
# CiAgICAgICAgbG9nZ2VyLmluZm8oIlBsZWFzZSBhZGQgdGhlIGNvbnRlbnRzIG9mIGdsb2JhbF9y
# dWxlcy5tZCB0byB5b3VyIElERSdzIGdsb2JhbCBydWxlcyBzZWN0aW9uIikKICAgIAogICAgIyBJ
# bml0aWFsaXplIGN1cnNvciBydWxlcyBmaWxlIGlmIGVtcHR5CiAgICBpZiBub3Qgc2FmZV9yZWFk
# X2ZpbGUoQ09OVEVYVF9SVUxFU19QQVRIKToKICAgICAgICAjIEluaXRpYWxpemUgd2l0aCBjdXJy
# ZW50IGFyY2hpdGVjdHVyZSwgcHJvZ3Jlc3MgYW5kIHRhc2tzCiAgICAgICAgY29udGV4dCA9IHsK
# ICAgICAgICAgICAgImFyY2hpdGVjdHVyZSI6IHNhZmVfcmVhZF9maWxlKEFSQ0hJVEVDVFVSRV9Q
# QVRIKSwKICAgICAgICAgICAgInByb2dyZXNzIjogc2FmZV9yZWFkX2ZpbGUoUFJPR1JFU1NfUEFU
# SCksCiAgICAgICAgICAgICJ0YXNrcyI6IHNhZmVfcmVhZF9maWxlKFRBU0tTX1BBVEgpLAogICAg
# ICAgIH0KICAgICAgICB1cGRhdGVfY29udGV4dChjb250ZXh0KQogICAgCiAgICAjIEVuc3VyZSBJ
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
# cm4gVHJ1ZQogICAgICAgIGV4Y2VwdCBzdWJwcm9jZXNzLkNhbGxlZFByb2Nlc3NFcnJvciBhcyBl
# OgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gc3RhZ2UgY2hhbmdlczoge2V9
# IikKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBl
# OgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJVbmV4cGVjdGVkIGVycm9yIHdoaWxlIHN0YWdp
# bmcgY2hhbmdlczoge2V9IikKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAKICAgIGRlZiBj
# b21taXRfY2hhbmdlcyhzZWxmLCBtZXNzYWdlOiBzdHIpIC0+IGJvb2w6CiAgICAgICAgIiIiQ29t
# bWl0IHN0YWdlZCBjaGFuZ2VzIHdpdGggYSBnaXZlbiBtZXNzYWdlLiIiIgogICAgICAgIHRyeToK
# ICAgICAgICAgICAgc2VsZi5fcnVuX2dpdF9jb21tYW5kKFsiY29tbWl0IiwgIi1tIiwgbWVzc2Fn
# ZV0pCiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgZXhjZXB0IHN1YnByb2Nlc3MuQ2Fs
# bGVkUHJvY2Vzc0Vycm9yIGFzIGU6CiAgICAgICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0
# byBjb21taXQgY2hhbmdlczoge2V9IikKICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAg
# ZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoZiJVbmV4cGVj
# dGVkIGVycm9yIHdoaWxlIGNvbW1pdHRpbmcgY2hhbmdlczoge2V9IikKICAgICAgICAgICAgcmV0
# dXJuIEZhbHNlCiAgICAgICAgCiAgICBkZWYgdmFsaWRhdGVfY29tbWl0X21lc3NhZ2Uoc2VsZiwg
# bWVzc2FnZTogc3RyKSAtPiBUdXBsZVtib29sLCBzdHJdOgogICAgICAgICIiIlZhbGlkYXRlIGEg
# Y29tbWl0IG1lc3NhZ2UgYWdhaW5zdCBjb252ZW50aW9ucy4iIiIKICAgICAgICBpZiBub3QgbWVz
# c2FnZToKICAgICAgICAgICAgcmV0dXJuIEZhbHNlLCAiQ29tbWl0IG1lc3NhZ2UgY2Fubm90IGJl
# IGVtcHR5IgogICAgICAgIAogICAgICAgICMgQ2hlY2sgbGVuZ3RoCiAgICAgICAgaWYgbGVuKG1l
# c3NhZ2UpID4gNzI6CiAgICAgICAgICAgIHJldHVybiBGYWxzZSwgIkNvbW1pdCBtZXNzYWdlIGlz
# IHRvbyBsb25nIChtYXggNzIgY2hhcmFjdGVycykiCiAgICAgICAgCiAgICAgICAgIyBDaGVjayBm
# b3JtYXQgKGNvbnZlbnRpb25hbCBjb21taXRzKQogICAgICAgIGNvbnZlbnRpb25hbF90eXBlcyA9
# IHsiZmVhdCIsICJmaXgiLCAiZG9jcyIsICJzdHlsZSIsICJyZWZhY3RvciIsICJ0ZXN0IiwgImNo
# b3JlIn0KICAgICAgICBmaXJzdF9saW5lID0gbWVzc2FnZS5zcGxpdCgiXG4iKVswXQogICAgICAg
# IAogICAgICAgIGlmICI6IiBpbiBmaXJzdF9saW5lOgogICAgICAgICAgICB0eXBlXyA9IGZpcnN0
# X2xpbmUuc3BsaXQoIjoiKVswXQogICAgICAgICAgICBpZiB0eXBlXyBub3QgaW4gY29udmVudGlv
# bmFsX3R5cGVzOgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlLCBmIkludmFsaWQgY29tbWl0
# IHR5cGUuIE11c3QgYmUgb25lIG9mOiB7JywgJy5qb2luKGNvbnZlbnRpb25hbF90eXBlcyl9Igog
# ICAgICAgIAogICAgICAgIHJldHVybiBUcnVlLCAiQ29tbWl0IG1lc3NhZ2UgaXMgdmFsaWQiCiAg
# ICAgICAgCiAgICBkZWYgZ2V0X3JlcG9zaXRvcnlfc3RhdGUoc2VsZikgLT4gZGljdDoKICAgICAg
# ICAiIiJHZXQgdGhlIGN1cnJlbnQgc3RhdGUgb2YgdGhlIHJlcG9zaXRvcnkuIiIiCiAgICAgICAg
# dHJ5OgogICAgICAgICAgICAjIEdldCBjdXJyZW50IGJyYW5jaAogICAgICAgICAgICBicmFuY2gg
# PSBzZWxmLmdldF9jdXJyZW50X2JyYW5jaCgpCiAgICAgICAgICAgIAogICAgICAgICAgICAjIEdl
# dCBzdGF0dXMKICAgICAgICAgICAgc3RhdHVzX291dHB1dCwgXyA9IHNlbGYuX3J1bl9naXRfY29t
# bWFuZChbInN0YXR1cyIsICItLXBvcmNlbGFpbiJdKQogICAgICAgICAgICBzdGF0dXNfbGluZXMg
# PSBzdGF0dXNfb3V0cHV0LnNwbGl0KCJcbiIpIGlmIHN0YXR1c19vdXRwdXQgZWxzZSBbXQogICAg
# ICAgICAgICAKICAgICAgICAgICAgIyBQYXJzZSBzdGF0dXMKICAgICAgICAgICAgc3RhZ2VkID0g
# W10KICAgICAgICAgICAgdW5zdGFnZWQgPSBbXQogICAgICAgICAgICB1bnRyYWNrZWQgPSBbXQog
# ICAgICAgICAgICAKICAgICAgICAgICAgZm9yIGxpbmUgaW4gc3RhdHVzX2xpbmVzOgogICAgICAg
# ICAgICAgICAgaWYgbm90IGxpbmU6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAg
# ICAgICAgICAgIHN0YXR1cyA9IGxpbmVbOjJdCiAgICAgICAgICAgICAgICBwYXRoID0gbGluZVsz
# Ol0uc3RyaXAoKQogICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICBpZiBzdGF0dXMuc3Rh
# cnRzd2l0aCgiPz8iKToKICAgICAgICAgICAgICAgICAgICB1bnRyYWNrZWQuYXBwZW5kKHBhdGgp
# CiAgICAgICAgICAgICAgICBlbGlmIHN0YXR1c1swXSAhPSAiICI6CiAgICAgICAgICAgICAgICAg
# ICAgc3RhZ2VkLmFwcGVuZChwYXRoKQogICAgICAgICAgICAgICAgZWxpZiBzdGF0dXNbMV0gIT0g
# IiAiOgogICAgICAgICAgICAgICAgICAgIHVuc3RhZ2VkLmFwcGVuZChwYXRoKQogICAgICAgICAg
# ICAKICAgICAgICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgICAgICJicmFuY2giOiBicmFuY2gs
# CiAgICAgICAgICAgICAgICAic3RhZ2VkIjogc3RhZ2VkLAogICAgICAgICAgICAgICAgInVuc3Rh
# Z2VkIjogdW5zdGFnZWQsCiAgICAgICAgICAgICAgICAidW50cmFja2VkIjogdW50cmFja2VkCiAg
# ICAgICAgICAgIH0KICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIGxv
# Z2dlci5lcnJvcihmIkZhaWxlZCB0byBnZXQgcmVwb3NpdG9yeSBzdGF0ZToge2V9IikKICAgICAg
# ICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgICAgICJicmFuY2giOiAidW5rbm93biIsCiAgICAg
# ICAgICAgICAgICAic3RhZ2VkIjogW10sCiAgICAgICAgICAgICAgICAidW5zdGFnZWQiOiBbXSwK
# ICAgICAgICAgICAgICAgICJ1bnRyYWNrZWQiOiBbXQogICAgICAgICAgICB9CiAgICAKICAgIGRl
# ZiBnZXRfY3VycmVudF9icmFuY2goc2VsZikgLT4gc3RyOgogICAgICAgICIiIkdldCB0aGUgbmFt
# ZSBvZiB0aGUgY3VycmVudCBicmFuY2guIiIiCiAgICAgICAgdHJ5OgogICAgICAgICAgICBicmFu
# Y2hfb3V0cHV0LCBfID0gc2VsZi5fcnVuX2dpdF9jb21tYW5kKFsicmV2LXBhcnNlIiwgIi0tYWJi
# cmV2LXJlZiIsICJIRUFEIl0pCiAgICAgICAgICAgIHJldHVybiBicmFuY2hfb3V0cHV0LnN0cmlw
# KCkKICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIGxvZ2dlci5lcnJv
# cihmIkZhaWxlZCB0byBnZXQgY3VycmVudCBicmFuY2g6IHtlfSIpCiAgICAgICAgICAgIHJldHVy
# biAidW5rbm93biIKCmRlZiBkZXRlcm1pbmVfY29tbWl0X3R5cGUoZGlmZl9vdXRwdXQ6IHN0cikg
# LT4gc3RyOgogICAgIiIiCiAgICBQcm9ncmFtbWF0aWNhbGx5IGRldGVybWluZSB0aGUgbW9zdCBh
# cHByb3ByaWF0ZSBjb21taXQgdHlwZSBiYXNlZCBvbiBkaWZmIGNvbnRlbnQuCiAgICAKICAgIENv
# bnZlbnRpb25hbCBjb21taXQgdHlwZXM6CiAgICAtIGZlYXQ6IG5ldyBmZWF0dXJlCiAgICAtIGZp
# eDogYnVnIGZpeAogICAgLSBkb2NzOiBkb2N1bWVudGF0aW9uIGNoYW5nZXMKICAgIC0gc3R5bGU6
# IGZvcm1hdHRpbmcsIG1pc3Npbmcgc2VtaSBjb2xvbnMsIGV0YwogICAgLSByZWZhY3RvcjogY29k
# ZSByZXN0cnVjdHVyaW5nIHdpdGhvdXQgY2hhbmdpbmcgZnVuY3Rpb25hbGl0eQogICAgLSB0ZXN0
# OiBhZGRpbmcgb3IgbW9kaWZ5aW5nIHRlc3RzCiAgICAtIGNob3JlOiBtYWludGVuYW5jZSB0YXNr
# cywgdXBkYXRlcyB0byBidWlsZCBwcm9jZXNzLCBldGMKICAgICIiIgogICAgIyBDb252ZXJ0IGRp
# ZmYgdG8gbG93ZXJjYXNlIGZvciBjYXNlLWluc2Vuc2l0aXZlIG1hdGNoaW5nCiAgICBkaWZmX2xv
# d2VyID0gZGlmZl9vdXRwdXQubG93ZXIoKQogICAgCiAgICAjIFByaW9yaXRpemUgc3BlY2lmaWMg
# cGF0dGVybnMKICAgIGlmICd0ZXN0JyBpbiBkaWZmX2xvd2VyIG9yICdweXRlc3QnIGluIGRpZmZf
# bG93ZXIgb3IgJ190ZXN0LnB5JyBpbiBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAndGVzdCcK
# ICAgIAogICAgaWYgJ2ZpeCcgaW4gZGlmZl9sb3dlciBvciAnYnVnJyBpbiBkaWZmX2xvd2VyIG9y
# ICdlcnJvcicgaW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2ZpeCcKICAgIAogICAgaWYg
# J2RvY3MnIGluIGRpZmZfbG93ZXIgb3IgJ3JlYWRtZScgaW4gZGlmZl9sb3dlciBvciAnZG9jdW1l
# bnRhdGlvbicgaW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2RvY3MnCiAgICAKICAgIGlm
# ICdzdHlsZScgaW4gZGlmZl9sb3dlciBvciAnZm9ybWF0JyBpbiBkaWZmX2xvd2VyIG9yICdsaW50
# JyBpbiBkaWZmX2xvd2VyOgogICAgICAgIHJldHVybiAnc3R5bGUnCiAgICAKICAgIGlmICdyZWZh
# Y3RvcicgaW4gZGlmZl9sb3dlciBvciAncmVzdHJ1Y3R1cmUnIGluIGRpZmZfbG93ZXI6CiAgICAg
# ICAgcmV0dXJuICdyZWZhY3RvcicKICAgIAogICAgIyBDaGVjayBmb3IgbmV3IGZlYXR1cmUgaW5k
# aWNhdG9ycwogICAgaWYgJ2RlZiAnIGluIGRpZmZfbG93ZXIgb3IgJ2NsYXNzICcgaW4gZGlmZl9s
# b3dlciBvciAnbmV3ICcgaW4gZGlmZl9sb3dlcjoKICAgICAgICByZXR1cm4gJ2ZlYXQnCiAgICAK
# ICAgICMgRGVmYXVsdCB0byBjaG9yZSBmb3IgbWlzY2VsbGFuZW91cyBjaGFuZ2VzCiAgICByZXR1
# cm4gJ2Nob3JlJwoKZGVmIGNoZWNrX2NyZWRzKCk6CiAgICBhcGlfa2V5LCBiYXNlX3VybCwgbW9k
# ZWwgPSBnZXRfb3BlbmFpX2NyZWRlbnRpYWxzKCkKICAgIHByaW50KGFwaV9rZXksIGJhc2VfdXJs
# LCBtb2RlbCkKICAgIGlmICJzay0xMjM0IiBpbiBhcGlfa2V5IGFuZCAib3BlbmFpIiBpbiBiYXNl
# X3VybDoKICAgICAgICByZXR1cm4gRmFsc2UKICAgIHJldHVybiBUcnVlCgoKCmRlZiBtYWtlX2F0
# b21pY19jb21taXQoKToKICAgICIiIk1ha2VzIGFuIGF0b21pYyBjb21taXQgd2l0aCBBSS1nZW5l
# cmF0ZWQgY29tbWl0IG1lc3NhZ2UuIiIiCiAgICBpZiBub3QgY2hlY2tfY3JlZHMoKToKICAgICAg
# ICByZXR1cm4gRmFsc2UKICAgICMgSW5pdGlhbGl6ZSBHaXRNYW5hZ2VyIHdpdGggY3VycmVudCBk
# aXJlY3RvcnkKICAgIGdpdF9tYW5hZ2VyID0gR2l0TWFuYWdlcihQV0QpCiAgICAKICAgICMgU3Rh
# Z2UgYWxsIGNoYW5nZXMKICAgIGlmIG5vdCBnaXRfbWFuYWdlci5zdGFnZV9hbGxfY2hhbmdlcygp
# OgogICAgICAgIGxvZ2dlci53YXJuaW5nKCJObyBjaGFuZ2VzIHRvIGNvbW1pdCBvciBzdGFnaW5n
# IGZhaWxlZC4iKQogICAgICAgIHJldHVybiBGYWxzZQogICAgCiAgICAjIEdlbmVyYXRlIGNvbW1p
# dCBtZXNzYWdlIHVzaW5nIE9wZW5BSQogICAgdHJ5OgogICAgICAgICMgVXNlIHVuaXZlcnNhbCBu
# ZXdsaW5lcyBhbmQgZXhwbGljaXQgZW5jb2RpbmcgdG8gaGFuZGxlIGNyb3NzLXBsYXRmb3JtIGRp
# ZmZzCiAgICAgICAgZGlmZl9vdXRwdXQgPSBzdWJwcm9jZXNzLmNoZWNrX291dHB1dCgKICAgICAg
# ICAgICAgWyJnaXQiLCAiZGlmZiIsICItLXN0YWdlZCJdLCAKICAgICAgICAgICAgY3dkPVBXRCwg
# CiAgICAgICAgICAgIHRleHQ9VHJ1ZSwKICAgICAgICAgICAgdW5pdmVyc2FsX25ld2xpbmVzPVRy
# dWUsCiAgICAgICAgICAgIGVuY29kaW5nPSd1dGYtOCcsCiAgICAgICAgICAgIGVycm9ycz0ncmVw
# bGFjZScgICMgUmVwbGFjZSB1bmRlY29kYWJsZSBieXRlcwogICAgICAgICkKICAgICAgICAKICAg
# ICAgICAjIFRydW5jYXRlIGRpZmYgaWYgaXQncyB0b28gbG9uZwogICAgICAgIG1heF9kaWZmX2xl
# bmd0aCA9IDQwMDAKICAgICAgICBpZiBsZW4oZGlmZl9vdXRwdXQpID4gbWF4X2RpZmZfbGVuZ3Ro
# OgogICAgICAgICAgICBkaWZmX291dHB1dCA9IGRpZmZfb3V0cHV0WzptYXhfZGlmZl9sZW5ndGhd
# ICsgIi4uLiAoZGlmZiB0cnVuY2F0ZWQpIgogICAgICAgIAogICAgICAgICMgU2FuaXRpemUgZGlm
# ZiBvdXRwdXQgdG8gcmVtb3ZlIHBvdGVudGlhbGx5IHByb2JsZW1hdGljIGNoYXJhY3RlcnMKICAg
# ICAgICBkaWZmX291dHB1dCA9ICcnLmpvaW4oY2hhciBmb3IgY2hhciBpbiBkaWZmX291dHB1dCBp
# ZiBvcmQoY2hhcikgPCAxMjgpCiAgICAgICAgCiAgICAgICAgIyBEZXRlcm1pbmUgY29tbWl0IHR5
# cGUgcHJvZ3JhbW1hdGljYWxseQogICAgICAgIGNvbW1pdF90eXBlID0gZGV0ZXJtaW5lX2NvbW1p
# dF90eXBlKGRpZmZfb3V0cHV0KQogICAgICAgIAogICAgICAgIHByb21wdCA9IGYiIiJHZW5lcmF0
# ZSBhIGNvbmNpc2UsIGRlc2NyaXB0aXZlIGNvbW1pdCBtZXNzYWdlIGZvciB0aGUgZm9sbG93aW5n
# IGdpdCBkaWZmLgpUaGUgY29tbWl0IHR5cGUgaGFzIGJlZW4gZGV0ZXJtaW5lZCB0byBiZSAne2Nv
# bW1pdF90eXBlfScuCgpEaWZmOgp7ZGlmZl9vdXRwdXR9CgpHdWlkZWxpbmVzOgotIFVzZSB0aGUg
# Zm9ybWF0OiB7Y29tbWl0X3R5cGV9OiBkZXNjcmlwdGlvbgotIEtlZXAgbWVzc2FnZSB1bmRlciA3
# MiBjaGFyYWN0ZXJzCi0gQmUgc3BlY2lmaWMgYWJvdXQgdGhlIGNoYW5nZXMKLSBQcmVmZXIgaW1w
# ZXJhdGl2ZSBtb29kIiIiCiAgICAgICAgCiAgICAgICAgcmVzcG9uc2UgPSBDTElFTlQuY2hhdC5j
# b21wbGV0aW9ucy5jcmVhdGUoCiAgICAgICAgICAgIG1vZGVsPU9QRU5BSV9NT0RFTCwKICAgICAg
# ICAgICAgbWVzc2FnZXM9WwogICAgICAgICAgICAgICAgeyJyb2xlIjogInN5c3RlbSIsICJjb250
# ZW50IjogIllvdSBhcmUgYSBnaXQgY29tbWl0IG1lc3NhZ2UgZ2VuZXJhdG9yLiJ9LAogICAgICAg
# ICAgICAgICAgeyJyb2xlIjogInVzZXIiLCAiY29udGVudCI6IHByb21wdH0KICAgICAgICAgICAg
# XSwKICAgICAgICAgICAgbWF4X3Rva2Vucz0xMDAKICAgICAgICApCiAgICAgICAgCiAgICAgICAg
# IyBTYW5pdGl6ZSBjb21taXQgbWVzc2FnZQogICAgICAgIHJhd19tZXNzYWdlID0gcmVzcG9uc2Uu
# Y2hvaWNlc1swXS5tZXNzYWdlLmNvbnRlbnQKICAgICAgICBjb21taXRfbWVzc2FnZSA9ICcnLmpv
# aW4oY2hhciBmb3IgY2hhciBpbiByYXdfbWVzc2FnZSBpZiBvcmQoY2hhcikgPCAxMjgpCiAgICAg
# ICAgCiAgICAgICAgIyBFbnN1cmUgY29tbWl0IG1lc3NhZ2Ugc3RhcnRzIHdpdGggdGhlIGRldGVy
# bWluZWQgdHlwZQogICAgICAgIGlmIG5vdCBjb21taXRfbWVzc2FnZS5zdGFydHN3aXRoKGYie2Nv
# bW1pdF90eXBlfToiKToKICAgICAgICAgICAgY29tbWl0X21lc3NhZ2UgPSBmIntjb21taXRfdHlw
# ZX06IHtjb21taXRfbWVzc2FnZX0iCiAgICAgICAgCiAgICAgICAgY29tbWl0X21lc3NhZ2UgPSBl
# eHRyYWN0X2NvbW1pdF9tZXNzYWdlKGNvbW1pdF9tZXNzYWdlKQogICAgICAgIAogICAgICAgICMg
# VmFsaWRhdGUgY29tbWl0IG1lc3NhZ2UKICAgICAgICBpc192YWxpZCwgdmFsaWRhdGlvbl9tZXNz
# YWdlID0gZ2l0X21hbmFnZXIudmFsaWRhdGVfY29tbWl0X21lc3NhZ2UoY29tbWl0X21lc3NhZ2Up
# CiAgICAgICAgCiAgICAgICAgaWYgbm90IGlzX3ZhbGlkOgogICAgICAgICAgICBsb2dnZXIud2Fy
# bmluZyhmIkdlbmVyYXRlZCBjb21taXQgbWVzc2FnZSBpbnZhbGlkOiB7dmFsaWRhdGlvbl9tZXNz
# YWdlfSIpCiAgICAgICAgICAgIGNvbW1pdF9tZXNzYWdlID0gZiJ7Y29tbWl0X3R5cGV9OiBVcGRh
# dGUgcHJvamVjdCBmaWxlcyAoe3RpbWUuc3RyZnRpbWUoJyVZLSVtLSVkJyl9KSIKICAgICAgICAK
# ICAgICAgICAjIENvbW1pdCBjaGFuZ2VzCiAgICAgICAgaWYgZ2l0X21hbmFnZXIuY29tbWl0X2No
# YW5nZXMoY29tbWl0X21lc3NhZ2UpOgogICAgICAgICAgICBsb2dnZXIuaW5mbyhmIkNvbW1pdHRl
# ZCBjaGFuZ2VzOiB7Y29tbWl0X21lc3NhZ2V9IikKICAgICAgICAgICAgcmV0dXJuIFRydWUKICAg
# ICAgICBlbHNlOgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoIkNvbW1pdCBmYWlsZWQiKQogICAg
# ICAgICAgICByZXR1cm4gRmFsc2UKICAgIAogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAg
# ICAgIGxvZ2dlci5lcnJvcihmIkVycm9yIGluIGF0b21pYyBjb21taXQ6IHtlfSIpCiAgICAgICAg
# cmV0dXJuIEZhbHNlCgpkZWYgZXh0cmFjdF9jb21taXRfbWVzc2FnZShyZXNwb25zZTogc3RyKSAt
# PiBzdHI6CiAgICAiIiIKICAgIEV4dHJhY3QgY29tbWl0IG1lc3NhZ2UgZnJvbSBBSSByZXNwb25z
# ZSwgaGFuZGxpbmcgbWFya2Rvd24gYmxvY2tzIGFuZCBlbnN1cmluZyBjb25jaXNlbmVzcy4KICAg
# IAogICAgQXJnczoKICAgICAgICByZXNwb25zZTogUmF3IHJlc3BvbnNlIGZyb20gQUkKICAgIAog
# ICAgUmV0dXJuczoKICAgICAgICBFeHRyYWN0ZWQgY29tbWl0IG1lc3NhZ2UsIHRyaW1tZWQgdG8g
# NzIgY2hhcmFjdGVycwogICAgIiIiCiAgICAjIFJlbW92ZSBsZWFkaW5nL3RyYWlsaW5nIHdoaXRl
# c3BhY2UKICAgIHJlc3BvbnNlID0gcmVzcG9uc2Uuc3RyaXAoKQogICAgCiAgICAjIEV4dHJhY3Qg
# ZnJvbSBtYXJrZG93biBjb2RlIGJsb2NrCiAgICBjb2RlX2Jsb2NrX21hdGNoID0gcmUuc2VhcmNo
# KHInYGBgKD86bWFya2Rvd258Y29tbWl0KT8oLis/KWBgYCcsIHJlc3BvbnNlLCByZS5ET1RBTEwp
# CiAgICBpZiBjb2RlX2Jsb2NrX21hdGNoOgogICAgICAgIHJlc3BvbnNlID0gY29kZV9ibG9ja19t
# YXRjaC5ncm91cCgxKS5zdHJpcCgpCiAgICAKICAgICMgRXh0cmFjdCBmcm9tIG1hcmtkb3duIGlu
# bGluZSBjb2RlCiAgICBpbmxpbmVfY29kZV9tYXRjaCA9IHJlLnNlYXJjaChyJ2AoLis/KWAnLCBy
# ZXNwb25zZSkKICAgIGlmIGlubGluZV9jb2RlX21hdGNoOgogICAgICAgIHJlc3BvbnNlID0gaW5s
# aW5lX2NvZGVfbWF0Y2guZ3JvdXAoMSkuc3RyaXAoKQogICAgCiAgICAjIFJlbW92ZSBhbnkgbGVh
# ZGluZyB0eXBlIGlmIGFscmVhZHkgcHJlc2VudAogICAgdHlwZV9tYXRjaCA9IHJlLm1hdGNoKHIn
# XihmZWF0fGZpeHxkb2NzfHN0eWxlfHJlZmFjdG9yfHRlc3R8Y2hvcmUpOlxzKicsIHJlc3BvbnNl
# LCByZS5JR05PUkVDQVNFKQogICAgaWYgdHlwZV9tYXRjaDoKICAgICAgICByZXNwb25zZSA9IHJl
# c3BvbnNlW3R5cGVfbWF0Y2guZW5kKCk6XQogICAgCiAgICAjIFRyaW0gdG8gNzIgY2hhcmFjdGVy
# cywgcmVzcGVjdGluZyB3b3JkIGJvdW5kYXJpZXMKICAgIGlmIGxlbihyZXNwb25zZSkgPiA3MjoK
# ICAgICAgICByZXNwb25zZSA9IHJlc3BvbnNlWzo3Ml0ucnNwbGl0KCcgJywgMSlbMF0gKyAnLi4u
# JwogICAgCiAgICByZXR1cm4gcmVzcG9uc2Uuc3RyaXAoKQoKZGVmIHJlc3RhcnRfcHJvZ3JhbSgp
# OgogICAgIiIiUmVzdGFydCB0aGUgY3VycmVudCBwcm9ncmFtLiIiIgogICAgbG9nZ2VyLmluZm8o
# IlJlc3RhcnRpbmcgdGhlIHByb2dyYW0uLi4iKQogICAgcHl0aG9uID0gc3lzLmV4ZWN1dGFibGUK
# ICAgIG9zLmV4ZWN2KHB5dGhvbiwgW3B5dGhvbl0gKyBzeXMuYXJndikKICAgIApjbGFzcyBCYXNl
# V2F0Y2hlcihGaWxlU3lzdGVtRXZlbnRIYW5kbGVyKToKICAgICIiIgogICAgQSBiYXNlIGZpbGUg
# d2F0Y2hlciB0aGF0IGFjY2VwdHMgYSBkaWN0aW9uYXJ5IG9mIGZpbGUgcGF0aHMgYW5kIGEgY2Fs
# bGJhY2suCiAgICBUaGUgY2FsbGJhY2sgaXMgZXhlY3V0ZWQgd2hlbmV2ZXIgb25lIG9mIHRoZSB3
# YXRjaGVkIGZpbGVzIGlzIG1vZGlmaWVkLgogICAgIiIiCiAgICBkZWYgX19pbml0X18oc2VsZiwg
# ZmlsZV9wYXRoczogZGljdCwgY2FsbGJhY2spOgogICAgICAgICIiIgogICAgICAgIGZpbGVfcGF0
# aHM6IGRpY3QgbWFwcGluZyBmaWxlIHBhdGhzIChhcyBzdHJpbmdzKSB0byBhIGZpbGUga2V5L2lk
# ZW50aWZpZXIuCiAgICAgICAgY2FsbGJhY2s6IGEgY2FsbGFibGUgdGhhdCB0YWtlcyB0aGUgZmls
# ZSBrZXkgYXMgYW4gYXJndW1lbnQuCiAgICAgICAgIiIiCiAgICAgICAgc3VwZXIoKS5fX2luaXRf
# XygpCiAgICAgICAgIyBOb3JtYWxpemUgYW5kIHN0b3JlIHRoZSBmaWxlIHBhdGhzCiAgICAgICAg
# c2VsZi5maWxlX3BhdGhzID0ge3N0cihQYXRoKGZwKS5yZXNvbHZlKCkpOiBrZXkgZm9yIGZwLCBr
# ZXkgaW4gZmlsZV9wYXRocy5pdGVtcygpfQogICAgICAgIHNlbGYuY2FsbGJhY2sgPSBjYWxsYmFj
# awogICAgICAgIGxvZ2dlci5pbmZvKGYiV2F0Y2hpbmcgZmlsZXM6IHtsaXN0KHNlbGYuZmlsZV9w
# YXRocy52YWx1ZXMoKSl9IikKCiAgICBkZWYgb25fbW9kaWZpZWQoc2VsZiwgZXZlbnQpOgogICAg
# ICAgIHBhdGggPSBzdHIoUGF0aChldmVudC5zcmNfcGF0aCkucmVzb2x2ZSgpKQogICAgICAgIGlm
# IHBhdGggaW4gc2VsZi5maWxlX3BhdGhzOgogICAgICAgICAgICBmaWxlX2tleSA9IHNlbGYuZmls
# ZV9wYXRoc1twYXRoXQogICAgICAgICAgICBsb2dnZXIuaW5mbyhmIkRldGVjdGVkIHVwZGF0ZSBp
# biB7ZmlsZV9rZXl9IikKICAgICAgICAgICAgc2VsZi5jYWxsYmFjayhmaWxlX2tleSkKCgpjbGFz
# cyBNYXJrZG93bldhdGNoZXIoQmFzZVdhdGNoZXIpOgogICAgIiIiCiAgICBXYXRjaGVyIHN1YmNs
# YXNzIHRoYXQgbW9uaXRvcnMgbWFya2Rvd24vc2V0dXAgZmlsZXMuCiAgICBXaGVuIGFueSBvZiB0
# aGUgZmlsZXMgY2hhbmdlLCBpdCB1cGRhdGVzIGNvbnRleHQgYW5kIGNvbW1pdHMgdGhlIGNoYW5n
# ZXMuCiAgICAiIiIKICAgIGRlZiBfX2luaXRfXyhzZWxmKToKICAgICAgICAjIEJ1aWxkIHRoZSBm
# aWxlIG1hcHBpbmcgZnJvbSBTRVRVUF9GSUxFUzoKICAgICAgICAjIFNFVFVQX0ZJTEVTIGlzIGFz
# c3VtZWQgdG8gYmUgYSBkaWN0IG1hcHBpbmcga2V5cyAoZS5nLiwgIkFSQ0hJVEVDVFVSRSIpIHRv
# IFBhdGggb2JqZWN0cy4KICAgICAgICBmaWxlX21hcHBpbmcgPSB7c3RyKHBhdGgucmVzb2x2ZSgp
# KTogbmFtZSBmb3IgbmFtZSwgcGF0aCBpbiBTRVRVUF9GSUxFUy5pdGVtcygpfQogICAgICAgIHN1
# cGVyKCkuX19pbml0X18oZmlsZV9tYXBwaW5nLCBzZWxmLm1hcmtkb3duX2NhbGxiYWNrKQoKICAg
# IGRlZiBtYXJrZG93bl9jYWxsYmFjayhzZWxmLCBmaWxlX2tleSk6CiAgICAgICAgIyBIYW5kbGUg
# bWFya2Rvd24gZmlsZSB1cGRhdGVzOgogICAgICAgIGxvZ2dlci5pbmZvKGYiUHJvY2Vzc2luZyB1
# cGRhdGUgZnJvbSB7ZmlsZV9rZXl9IikKICAgICAgICB1cGRhdGVfY29udGV4dCh7fSkKICAgICAg
# ICBtYWtlX2F0b21pY19jb21taXQoKQoKCmNsYXNzIFNjcmlwdFdhdGNoZXIoQmFzZVdhdGNoZXIp
# OgogICAgIiIiCiAgICBXYXRjaGVyIHN1YmNsYXNzIHRoYXQgbW9uaXRvcnMgdGhlIHNjcmlwdCBm
# aWxlIGZvciBjaGFuZ2VzLgogICAgV2hlbiB0aGUgc2NyaXB0IGZpbGUgaXMgbW9kaWZpZWQsIGl0
# IHRyaWdnZXJzIGEgc2VsZi1yZXN0YXJ0LgogICAgIiIiCiAgICBkZWYgX19pbml0X18oc2VsZiwg
# c2NyaXB0X3BhdGgpOgogICAgICAgICMgV2Ugb25seSB3YW50IHRvIHdhdGNoIHRoZSBzY3JpcHQg
# ZmlsZSBpdHNlbGYuCiAgICAgICAgZmlsZV9tYXBwaW5nID0ge29zLnBhdGguYWJzcGF0aChzY3Jp
# cHRfcGF0aCk6ICJTY3JpcHQgRmlsZSJ9CiAgICAgICAgc3VwZXIoKS5fX2luaXRfXyhmaWxlX21h
# cHBpbmcsIHNlbGYuc2NyaXB0X2NhbGxiYWNrKQoKICAgIGRlZiBzY3JpcHRfY2FsbGJhY2soc2Vs
# ZiwgZmlsZV9rZXkpOgogICAgICAgIGxvZ2dlci5pbmZvKGYiRGV0ZWN0ZWQgY2hhbmdlIGluIHtm
# aWxlX2tleX0uIFJlc3RhcnRpbmcgdGhlIHNjcmlwdC4uLiIpCiAgICAgICAgdGltZS5zbGVlcCgx
# KSAgIyBBbGxvdyB0aW1lIGZvciB0aGUgZmlsZSB3cml0ZSB0byBjb21wbGV0ZS4KICAgICAgICBy
# ZXN0YXJ0X3Byb2dyYW0oKQoKZGVmIHJ1bl9vYnNlcnZlcihvYnNlcnZlcjogT2JzZXJ2ZXIpOgog
# ICAgIiIiSGVscGVyIHRvIHJ1biBhbiBvYnNlcnZlciBpbiBhIHRocmVhZC4iIiIKICAgIG9ic2Vy
# dmVyLnN0YXJ0KCkKICAgIG9ic2VydmVyLmpvaW4oKQogICAgCmRlZiBtYWluKCk6CiAgICAiIiJN
# YWluIGZ1bmN0aW9uIHRvIGhhbmRsZSBhcmd1bWVudHMgYW5kIGV4ZWN1dGUgYXBwcm9wcmlhdGUg
# YWN0aW9ucyIiIgogICAgdHJ5OgogICAgICAgIGlkZV9lbnYgPSBkZXRlY3RfaWRlX2Vudmlyb25t
# ZW50KCkKCiAgICAgICAgaWYgQVJHUy51cGRhdGUgYW5kIEFSR1MudXBkYXRlX3ZhbHVlOgogICAg
# ICAgICAgICB1cGRhdGVfc3BlY2lmaWNfZmlsZShBUkdTLnVwZGF0ZSwgQVJHUy51cGRhdGVfdmFs
# dWUpCiAgICAgICAgICAgIGlmIG5vdCBBUkdTLndhdGNoOgogICAgICAgICAgICAgICAgcmV0dXJu
# IDAKICAgICAgICAgICAgICAgIAogICAgICAgICMgSGFuZGxlIHRhc2sgbWFuYWdlbWVudCBhY3Rp
# b25zCiAgICAgICAgaWYgQVJHUy50YXNrX2FjdGlvbjoKICAgICAgICAgICAga3dhcmdzID0ge30K
# ICAgICAgICAgICAgaWYgQVJHUy50YXNrX2Rlc2NyaXB0aW9uOgogICAgICAgICAgICAgICAga3dh
# cmdzWyJkZXNjcmlwdGlvbiJdID0gQVJHUy50YXNrX2Rlc2NyaXB0aW9uCiAgICAgICAgICAgIGlm
# IEFSR1MudGFza19pZDoKICAgICAgICAgICAgICAgIGt3YXJnc1sidGFza19pZCJdID0gQVJHUy50
# YXNrX2lkCiAgICAgICAgICAgIGlmIEFSR1MudGFza19zdGF0dXM6CiAgICAgICAgICAgICAgICBr
# d2FyZ3NbInN0YXR1cyJdID0gQVJHUy50YXNrX3N0YXR1cwogICAgICAgICAgICBpZiBBUkdTLnRh
# c2tfbm90ZToKICAgICAgICAgICAgICAgIGt3YXJnc1sibm90ZSJdID0gQVJHUy50YXNrX25vdGUK
# ICAgICAgICAgICAgICAgIAogICAgICAgICAgICByZXN1bHQgPSBtYW5hZ2VfdGFzayhBUkdTLnRh
# c2tfYWN0aW9uLCAqKmt3YXJncykKICAgICAgICAgICAgaWYgcmVzdWx0OgogICAgICAgICAgICAg
# ICAgaWYgaXNpbnN0YW5jZShyZXN1bHQsIGxpc3QpOgogICAgICAgICAgICAgICAgICAgIGZvciB0
# YXNrIGluIHJlc3VsdDoKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oanNvbi5k
# dW1wcyh0YXNrLnRvX2RpY3QoKSwgaW5kZW50PTIpKQogICAgICAgICAgICAgICAgZWxzZToKICAg
# ICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhqc29uLmR1bXBzKHJlc3VsdC50b19kaWN0KCks
# IGluZGVudD0yKSkKICAgICAgICAgICAgaWYgbm90IEFSR1Mud2F0Y2g6CiAgICAgICAgICAgICAg
# ICByZXR1cm4gMAogICAgICAgICAgICAgICAgCiAgICAgICAgIyBIYW5kbGUgZ2l0IG1hbmFnZW1l
# bnQgYWN0aW9ucwogICAgICAgIGlmIEFSR1MuZ2l0X2FjdGlvbjoKICAgICAgICAgICAgY29udGV4
# dCA9IHJlYWRfY29udGV4dF9maWxlKCkKICAgICAgICAgICAgZ2l0X21hbmFnZXIgPSBjb250ZXh0
# LmdldCgiZ2l0X21hbmFnZXIiKQogICAgICAgICAgICAKICAgICAgICAgICAgaWYgbm90IGdpdF9t
# YW5hZ2VyIGFuZCBBUkdTLmdpdF9yZXBvOgogICAgICAgICAgICAgICAgdHJ5OgogICAgICAgICAg
# ICAgICAgICAgIGdpdF9tYW5hZ2VyID0gR2l0TWFuYWdlcihBUkdTLmdpdF9yZXBvKQogICAgICAg
# ICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2VyIl0gPSBnaXRfbWFuYWdlcgogICAgICAg
# ICAgICAgICAgICAgIGNvbnRleHRbInJlcG9fcGF0aCJdID0gc3RyKFBhdGgoQVJHUy5naXRfcmVw
# bykucmVzb2x2ZSgpKQogICAgICAgICAgICAgICAgICAgIHdyaXRlX2NvbnRleHRfZmlsZShjb250
# ZXh0KQogICAgICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICAg
# ICAgICAgIGxvZ2dlci5lcnJvcihmIkZhaWxlZCB0byBpbml0aWFsaXplIGdpdCBtYW5hZ2VyOiB7
# ZX0iKQogICAgICAgICAgICAgICAgICAgIHJldHVybiAxCiAgICAgICAgICAgIAogICAgICAgICAg
# ICBpZiBub3QgZ2l0X21hbmFnZXI6CiAgICAgICAgICAgICAgICBsb2dnZXIuZXJyb3IoIk5vIGdp
# dCByZXBvc2l0b3J5IGNvbmZpZ3VyZWQuIFVzZSAtLWdpdC1yZXBvIHRvIHNwZWNpZnkgb25lLiIp
# CiAgICAgICAgICAgICAgICByZXR1cm4gMQogICAgICAgICAgICAKICAgICAgICAgICAgdHJ5Ogog
# ICAgICAgICAgICAgICAgaWYgQVJHUy5naXRfYWN0aW9uID09ICJzdGF0dXMiOgogICAgICAgICAg
# ICAgICAgICAgIHN0YXRlID0gZ2l0X21hbmFnZXIuZ2V0X3JlcG9zaXRvcnlfc3RhdGUoKQogICAg
# ICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKGpzb24uZHVtcHMoc3RhdGUsIGluZGVudD0yKSkK
# ICAgICAgICAgICAgICAgIGVsaWYgQVJHUy5naXRfYWN0aW9uID09ICJicmFuY2giOgogICAgICAg
# ICAgICAgICAgICAgIGlmIEFSR1MuYnJhbmNoX25hbWU6CiAgICAgICAgICAgICAgICAgICAgICAg
# IGdpdF9tYW5hZ2VyLl9ydW5fZ2l0X2NvbW1hbmQoWyJjaGVja291dCIsICItYiIsIEFSR1MuYnJh
# bmNoX25hbWVdKQogICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhmIkNyZWF0ZWQg
# YW5kIHN3aXRjaGVkIHRvIGJyYW5jaDoge0FSR1MuYnJhbmNoX25hbWV9IikKICAgICAgICAgICAg
# ICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBsb2dnZXIuaW5mbyhmIkN1cnJl
# bnQgYnJhbmNoOiB7Z2l0X21hbmFnZXIuZ2V0X2N1cnJlbnRfYnJhbmNoKCl9IikKICAgICAgICAg
# ICAgICAgIGVsaWYgQVJHUy5naXRfYWN0aW9uID09ICJjb21taXQiOgogICAgICAgICAgICAgICAg
# ICAgIGlmIG5vdCBBUkdTLmNvbW1pdF9tZXNzYWdlOgogICAgICAgICAgICAgICAgICAgICAgICBs
# b2dnZXIuZXJyb3IoIkNvbW1pdCBtZXNzYWdlIHJlcXVpcmVkIikKICAgICAgICAgICAgICAgICAg
# ICAgICAgcmV0dXJuIDEKICAgICAgICAgICAgICAgICAgICBpZiBnaXRfbWFuYWdlci5jb21taXRf
# Y2hhbmdlcyhBUkdTLmNvbW1pdF9tZXNzYWdlKToKICAgICAgICAgICAgICAgICAgICAgICAgbG9n
# Z2VyLmluZm8oIkNoYW5nZXMgY29tbWl0dGVkIHN1Y2Nlc3NmdWxseSIpCiAgICAgICAgICAgICAg
# ICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKCJGYWlsZWQg
# dG8gY29tbWl0IGNoYW5nZXMiKQogICAgICAgICAgICAgICAgZWxpZiBBUkdTLmdpdF9hY3Rpb24g
# PT0gInB1c2giOgogICAgICAgICAgICAgICAgICAgIHN0ZG91dCwgc3RkZXJyID0gZ2l0X21hbmFn
# ZXIuX3J1bl9naXRfY29tbWFuZChbInB1c2giXSkKICAgICAgICAgICAgICAgICAgICBpZiBzdGRv
# dXQ6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKHN0ZG91dCkKICAgICAgICAg
# ICAgICAgICAgICBpZiBzdGRlcnI6CiAgICAgICAgICAgICAgICAgICAgICAgIGxvZ2dlci5lcnJv
# cihzdGRlcnIpCiAgICAgICAgICAgICAgICBlbGlmIEFSR1MuZ2l0X2FjdGlvbiA9PSAicHVsbCI6
# CiAgICAgICAgICAgICAgICAgICAgc3Rkb3V0LCBzdGRlcnIgPSBnaXRfbWFuYWdlci5fcnVuX2dp
# dF9jb21tYW5kKFsicHVsbCJdKQogICAgICAgICAgICAgICAgICAgIGlmIHN0ZG91dDoKICAgICAg
# ICAgICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oc3Rkb3V0KQogICAgICAgICAgICAgICAgICAg
# IGlmIHN0ZGVycjoKICAgICAgICAgICAgICAgICAgICAgICAgbG9nZ2VyLmVycm9yKHN0ZGVycikK
# ICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICAgICAgbG9nZ2Vy
# LmVycm9yKGYiR2l0IGFjdGlvbiBmYWlsZWQ6IHtlfSIpCiAgICAgICAgICAgICAgICByZXR1cm4g
# MQogICAgICAgICAgICAgICAgCiAgICAgICAgICAgIGlmIG5vdCBBUkdTLndhdGNoOgogICAgICAg
# ICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgaWYgQVJHUy53YXRjaDoKICAgICAgICAgICAgdXBk
# YXRlX2NvbnRleHQoe30pCgogICAgICAgICAgICAjID09PSBTZXR1cCBNYXJrZG93biBXYXRjaGVy
# ID09PQogICAgICAgICAgICBtYXJrZG93bl93YXRjaGVyID0gTWFya2Rvd25XYXRjaGVyKCkKICAg
# ICAgICAgICAgbWFya2Rvd25fb2JzZXJ2ZXIgPSBPYnNlcnZlcigpCiAgICAgICAgICAgIG1hcmtk
# b3duX29ic2VydmVyLnNjaGVkdWxlKG1hcmtkb3duX3dhdGNoZXIsIHN0cihQV0QpLCByZWN1cnNp
# dmU9RmFsc2UpCgogICAgICAgICAgICAjID09PSBTZXR1cCBTY3JpcHQgV2F0Y2hlciA9PT0KICAg
# ICAgICAgICAgc2NyaXB0X3dhdGNoZXIgPSBTY3JpcHRXYXRjaGVyKF9fZmlsZV9fKQogICAgICAg
# ICAgICBzY3JpcHRfb2JzZXJ2ZXIgPSBPYnNlcnZlcigpCiAgICAgICAgICAgIHNjcmlwdF9vYnNl
# cnZlci5zY2hlZHVsZShzY3JpcHRfd2F0Y2hlciwgb3MucGF0aC5kaXJuYW1lKG9zLnBhdGguYWJz
# cGF0aChfX2ZpbGVfXykpLCByZWN1cnNpdmU9RmFsc2UpCgogICAgICAgICAgICAjID09PSBTdGFy
# dCBCb3RoIE9ic2VydmVycyBpbiBTZXBhcmF0ZSBUaHJlYWRzID09PQogICAgICAgICAgICB0MSA9
# IFRocmVhZCh0YXJnZXQ9cnVuX29ic2VydmVyLCBhcmdzPShtYXJrZG93bl9vYnNlcnZlciwpLCBk
# YWVtb249VHJ1ZSkKICAgICAgICAgICAgdDIgPSBUaHJlYWQodGFyZ2V0PXJ1bl9vYnNlcnZlciwg
# YXJncz0oc2NyaXB0X29ic2VydmVyLCksIGRhZW1vbj1UcnVlKQogICAgICAgICAgICB0MS5zdGFy
# dCgpCiAgICAgICAgICAgIHQyLnN0YXJ0KCkKCiAgICAgICAgICAgIGxvZ2dlci5pbmZvKCJXYXRj
# aGluZyBwcm9qZWN0IGZpbGVzIGFuZCBzY3JpcHQgZm9yIGNoYW5nZXMuIFByZXNzIEN0cmwrQyB0
# byBzdG9wLi4uIikKICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgd2hpbGUgVHJ1ZToK
# ICAgICAgICAgICAgICAgICAgICB0aW1lLnNsZWVwKDEpCiAgICAgICAgICAgIGV4Y2VwdCBLZXli
# b2FyZEludGVycnVwdDoKICAgICAgICAgICAgICAgIGxvZ2dlci5pbmZvKCJTaHV0dGluZyBkb3du
# Li4uIikKICAgICAgICAgICAgICAgIG1hcmtkb3duX29ic2VydmVyLnN0b3AoKQogICAgICAgICAg
# ICAgICAgc2NyaXB0X29ic2VydmVyLnN0b3AoKQogICAgICAgICAgICAgICAgdDEuam9pbigpCiAg
# ICAgICAgICAgICAgICB0Mi5qb2luKCkKICAgICAgICAgICAgICAgIHJldHVybiAwCgogICAgICAg
# ICMgRGVmYXVsdDoganVzdCB1cGRhdGUgdGhlIGNvbnRleHQKICAgICAgICB1cGRhdGVfY29udGV4
# dCh7fSkKICAgICAgICByZXR1cm4gMAoKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAg
# ICBsb2dnZXIuZXJyb3IoZiJVbmhhbmRsZWQgZXhjZXB0aW9uIGluIG1haW46IHtlfSIsIGV4Y19p
# bmZvPVRydWUpCiAgICAgICAgcmV0dXJuIDEKCmRlZiBzYXZlX3J1bGVzKGNvbnRleHRfY29udGVu
# dDogc3RyKSAtPiBOb25lOgogICAgIiIiCiAgICBTYXZlIHJ1bGVzIGNvbnRlbnQgdG8gdGhlIGFw
# cHJvcHJpYXRlIGZpbGUgYmFzZWQgb24gSURFIGVudmlyb25tZW50LgogICAgCiAgICBBcmdzOgog
# ICAgICAgIGNvbnRleHRfY29udGVudDogVGhlIGNvbnRlbnQgdG8gc2F2ZSB0byB0aGUgcnVsZXMg
# ZmlsZQogICAgIiIiCiAgICB0cnk6CiAgICAgICAgIyBTYXZlIHRvIGNvbnRleHQgcnVsZXMgZmls
# ZQogICAgICAgIHNhdmVfY29udGV4dF9ydWxlcyhjb250ZXh0X2NvbnRlbnQpCiAgICAgICAgIyBB
# bHNvIHNhdmUgdG8gZ2xvYmFsIHJ1bGVzIGlmIG5lZWRlZAogICAgICAgIHNhdmVfZ2xvYmFsX3J1
# bGVzKGNvbnRleHRfY29udGVudCkKICAgICAgICBsb2dnZXIuaW5mbygiUnVsZXMgc2F2ZWQgc3Vj
# Y2Vzc2Z1bGx5IikKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJy
# b3IoZiJGYWlsZWQgdG8gc2F2ZSBydWxlczoge2V9IikKCiMgQWRkIG5ldyBmdW5jdGlvbiB0byBt
# YW5hZ2UgdGFza3MKZGVmIG1hbmFnZV90YXNrKGFjdGlvbjogc3RyLCAqKmt3YXJncyk6CiAgICAi
# IiIKICAgIE1hbmFnZSB0YXNrcyBpbiB0aGUgY29udGV4dAogICAgCiAgICBBcmdzOgogICAgICAg
# IGFjdGlvbjogT25lIG9mICdhZGQnLCAndXBkYXRlJywgJ25vdGUnLCAnbGlzdCcsICdnZXQnCiAg
# ICAgICAgKiprd2FyZ3M6IEFkZGl0aW9uYWwgYXJndW1lbnRzIGJhc2VkIG9uIGFjdGlvbgogICAg
# IiIiCiAgICBjb250ZXh0ID0gcmVhZF9jb250ZXh0X2ZpbGUoKQogICAgaWYgInRhc2tzIiBub3Qg
# aW4gY29udGV4dDoKICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0ge30KICAgIHRhc2tfbWFuYWdl
# ciA9IFRhc2tNYW5hZ2VyKGNvbnRleHRbInRhc2tzIl0pCiAgICAKICAgIHJlc3VsdCA9IE5vbmUK
# ICAgIGlmIGFjdGlvbiA9PSAiYWRkIjoKICAgICAgICByZXN1bHQgPSB0YXNrX21hbmFnZXIuYWRk
# X3Rhc2soa3dhcmdzWyJkZXNjcmlwdGlvbiJdKQogICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxu
# Q3JlYXRlZCBuZXcgdGFzazpcbiIpCiAgICAgICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBz
# KHJlc3VsdC50b19kaWN0KCksIGluZGVudD0yKSArICJcbiIpCiAgICAgICAgc3lzLnN0ZGVyci5m
# bHVzaCgpCiAgICAgICAgY29udGV4dFsidGFza3MiXSA9IHRhc2tfbWFuYWdlci50YXNrcwogICAg
# ICAgICMgVXBkYXRlIHRhc2tzIGluIGN1cnNvciBydWxlcwogICAgICAgIHJ1bGVzX2NvbnRlbnQg
# PSBzYWZlX3JlYWRfZmlsZShHTE9CQUxfUlVMRVNfUEFUSCkKICAgICAgICBpZiBub3QgcnVsZXNf
# Y29udGVudDoKICAgICAgICAgICAgcnVsZXNfY29udGVudCA9ICIjIFRhc2tzIgogICAgICAgICMg
# Q2hlY2sgaWYgVGFza3Mgc2VjdGlvbiBleGlzdHMKICAgICAgICBpZiAiIyBUYXNrcyIgbm90IGlu
# IHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgKz0gIlxuXG4jIFRhc2tz
# IgogICAgICAgICMgRmluZCB0aGUgVGFza3Mgc2VjdGlvbiBhbmQgYXBwZW5kIHRoZSBuZXcgdGFz
# awogICAgICAgIGxpbmVzID0gcnVsZXNfY29udGVudC5zcGxpdCgiXG4iKQogICAgICAgIHRhc2tz
# X3NlY3Rpb25faWR4ID0gLTEKICAgICAgICBmb3IgaSwgbGluZSBpbiBlbnVtZXJhdGUobGluZXMp
# OgogICAgICAgICAgICBpZiBsaW5lLnN0cmlwKCkgPT0gIiMgVGFza3MiOgogICAgICAgICAgICAg
# ICAgdGFza3Nfc2VjdGlvbl9pZHggPSBpCiAgICAgICAgICAgICAgICBicmVhawogICAgICAgIAog
# ICAgICAgIGlmIHRhc2tzX3NlY3Rpb25faWR4ID49IDA6CiAgICAgICAgICAgICMgRmluZCB3aGVy
# ZSB0byBpbnNlcnQgdGhlIG5ldyB0YXNrIChhZnRlciB0aGUgbGFzdCB0YXNrIG9yIGFmdGVyIHRo
# ZSBUYXNrcyBoZWFkZXIpCiAgICAgICAgICAgIGluc2VydF9pZHggPSB0YXNrc19zZWN0aW9uX2lk
# eCArIDEKICAgICAgICAgICAgZm9yIGkgaW4gcmFuZ2UodGFza3Nfc2VjdGlvbl9pZHggKyAxLCBs
# ZW4obGluZXMpKToKICAgICAgICAgICAgICAgIGlmIGxpbmVzW2ldLnN0YXJ0c3dpdGgoIiMjIyBU
# YXNrIik6CiAgICAgICAgICAgICAgICAgICAgaW5zZXJ0X2lkeCA9IGkgKyAxCiAgICAgICAgICAg
# ICAgICAgICAgIyBTa2lwIHBhc3QgdGhlIHRhc2sncyBjb250ZW50CiAgICAgICAgICAgICAgICAg
# ICAgd2hpbGUgaSArIDEgPCBsZW4obGluZXMpIGFuZCAobGluZXNbaSArIDFdLnN0YXJ0c3dpdGgo
# IlN0YXR1czoiKSBvciBsaW5lc1tpICsgMV0uc3RhcnRzd2l0aCgiTm90ZToiKSk6CiAgICAgICAg
# ICAgICAgICAgICAgICAgIGkgKz0gMQogICAgICAgICAgICAgICAgICAgICAgICBpbnNlcnRfaWR4
# ID0gaSArIDEKICAgICAgICAgICAgCiAgICAgICAgICAgICMgSW5zZXJ0IHRhc2sgYXQgdGhlIGNv
# cnJlY3QgcG9zaXRpb24KICAgICAgICAgICAgdGFza19jb250ZW50ID0gWwogICAgICAgICAgICAg
# ICAgZiJcbiMjIyBUYXNrIHtyZXN1bHQuaWR9OiB7cmVzdWx0LmRlc2NyaXB0aW9ufSIsCiAgICAg
# ICAgICAgICAgICBmIlN0YXR1czoge3Jlc3VsdC5zdGF0dXN9IgogICAgICAgICAgICBdCiAgICAg
# ICAgICAgIGxpbmVzW2luc2VydF9pZHg6aW5zZXJ0X2lkeF0gPSB0YXNrX2NvbnRlbnQKICAgICAg
# ICAgICAgcnVsZXNfY29udGVudCA9ICJcbiIuam9pbihsaW5lcykKICAgICAgICBlbHNlOgogICAg
# ICAgICAgICAjIEFwcGVuZCB0byB0aGUgZW5kCiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgKz0g
# ZiJcblxuIyMjIFRhc2sge3Jlc3VsdC5pZH06IHtyZXN1bHQuZGVzY3JpcHRpb259XG4iCiAgICAg
# ICAgICAgIHJ1bGVzX2NvbnRlbnQgKz0gZiJTdGF0dXM6IHtyZXN1bHQuc3RhdHVzfVxuIgogICAg
# ICAgIAogICAgICAgIHNhdmVfcnVsZXMocnVsZXNfY29udGVudCkKICAgICAgICBzeXMuc3RkZXJy
# LndyaXRlKCJcblRhc2sgYWRkZWQgdG8gLmN1cnNvcnJ1bGVzIGZpbGVcbiIpCiAgICAgICAgc3lz
# LnN0ZGVyci5mbHVzaCgpCiAgICAgICAgCiAgICAgICAgIyBJZiBnaXQgbWFuYWdlciBleGlzdHMs
# IGNyZWF0ZSBhIGJyYW5jaCBmb3IgdGhlIHRhc2sKICAgICAgICBpZiBjb250ZXh0LmdldCgiZ2l0
# X21hbmFnZXIiKToKICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgYnJhbmNoX25hbWUg
# PSBmInRhc2sve3Jlc3VsdC5pZH0te2t3YXJnc1snZGVzY3JpcHRpb24nXS5sb3dlcigpLnJlcGxh
# Y2UoJyAnLCAnLScpfSIKICAgICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2VyIl0uX3J1
# bl9naXRfY29tbWFuZChbImNoZWNrb3V0IiwgIi1iIiwgYnJhbmNoX25hbWVdKQogICAgICAgICAg
# ICAgICAgc3lzLnN0ZGVyci53cml0ZShmIlxuQ3JlYXRlZCBicmFuY2gge2JyYW5jaF9uYW1lfSBm
# b3IgdGFzayB7cmVzdWx0LmlkfVxuIikKICAgICAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2go
# KQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgICAgICBsb2dn
# ZXIuZXJyb3IoZiJGYWlsZWQgdG8gY3JlYXRlIGJyYW5jaCBmb3IgdGFzazoge2V9IikKICAgIGVs
# aWYgYWN0aW9uID09ICJ1cGRhdGUiOgogICAgICAgIHRhc2tfbWFuYWdlci51cGRhdGVfdGFza19z
# dGF0dXMoa3dhcmdzWyJ0YXNrX2lkIl0sIGt3YXJnc1sic3RhdHVzIl0pCiAgICAgICAgcmVzdWx0
# ID0gdGFza19tYW5hZ2VyLmdldF90YXNrKGt3YXJnc1sidGFza19pZCJdKQogICAgICAgIHN5cy5z
# dGRlcnIud3JpdGUoIlxuVXBkYXRlZCB0YXNrOlxuIikKICAgICAgICBzeXMuc3RkZXJyLndyaXRl
# KGpzb24uZHVtcHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikKICAgICAgICBz
# eXMuc3RkZXJyLmZsdXNoKCkKICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0gdGFza19tYW5hZ2Vy
# LnRhc2tzCiAgICAgICAgIyBVcGRhdGUgdGFzayBzdGF0dXMgaW4gY3Vyc29yIHJ1bGVzCiAgICAg
# ICAgcnVsZXNfY29udGVudCA9IHNhZmVfcmVhZF9maWxlKEdMT0JBTF9SVUxFU19QQVRIKQogICAg
# ICAgIGlmIHJ1bGVzX2NvbnRlbnQ6CiAgICAgICAgICAgICMgRmluZCBhbmQgdXBkYXRlIHRoZSB0
# YXNrIHN0YXR1cwogICAgICAgICAgICBsaW5lcyA9IHJ1bGVzX2NvbnRlbnQuc3BsaXQoIlxuIikK
# ICAgICAgICAgICAgZm9yIGksIGxpbmUgaW4gZW51bWVyYXRlKGxpbmVzKToKICAgICAgICAgICAg
# ICAgIGlmIGxpbmUuc3RhcnRzd2l0aChmIiMjIyBUYXNrIHtrd2FyZ3NbJ3Rhc2tfaWQnXX06Iik6
# CiAgICAgICAgICAgICAgICAgICAgZm9yIGogaW4gcmFuZ2UoaSsxLCBsZW4obGluZXMpKToKICAg
# ICAgICAgICAgICAgICAgICAgICAgaWYgbGluZXNbal0uc3RhcnRzd2l0aCgiU3RhdHVzOiIpOgog
# ICAgICAgICAgICAgICAgICAgICAgICAgICAgbGluZXNbal0gPSBmIlN0YXR1czoge2t3YXJnc1sn
# c3RhdHVzJ119IgogICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAg
# ICAgICAgICBicmVhawogICAgICAgICAgICBydWxlc19jb250ZW50ID0gIlxuIi5qb2luKGxpbmVz
# KQogICAgICAgICAgICBzYXZlX3J1bGVzKHJ1bGVzX2NvbnRlbnQpCiAgICAgICAgICAgIHN5cy5z
# dGRlcnIud3JpdGUoIlxuVGFzayBzdGF0dXMgdXBkYXRlZCBpbiAuY3Vyc29ycnVsZXMgZmlsZVxu
# IikKICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICAgICAgIyBJZiB0YXNrIGlzIGNv
# bXBsZXRlZCBhbmQgZ2l0IG1hbmFnZXIgZXhpc3RzLCB0cnkgdG8gbWVyZ2UgdGhlIHRhc2sgYnJh
# bmNoCiAgICAgICAgaWYga3dhcmdzWyJzdGF0dXMiXSA9PSBUYXNrU3RhdHVzLkNPTVBMRVRFRCBh
# bmQgY29udGV4dC5nZXQoImdpdF9tYW5hZ2VyIik6CiAgICAgICAgICAgIHRyeToKICAgICAgICAg
# ICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2VyIl0uX3J1bl9naXRfY29tbWFuZChbImNoZWNrb3V0
# IiwgIm1haW4iXSkKICAgICAgICAgICAgICAgIGNvbnRleHRbImdpdF9tYW5hZ2VyIl0uX3J1bl9n
# aXRfY29tbWFuZChbIm1lcmdlIiwgZiJ0YXNrL3trd2FyZ3NbJ3Rhc2tfaWQnXX0iXSkKICAgICAg
# ICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoZiJcbk1lcmdlZCB0YXNrIGJyYW5jaCBmb3IgdGFz
# ayB7a3dhcmdzWyd0YXNrX2lkJ119XG4iKQogICAgICAgICAgICAgICAgc3lzLnN0ZGVyci5mbHVz
# aCgpCiAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgIGxv
# Z2dlci5lcnJvcihmIkZhaWxlZCB0byBtZXJnZSB0YXNrIGJyYW5jaDoge2V9IikKICAgIGVsaWYg
# YWN0aW9uID09ICJub3RlIjoKICAgICAgICB0YXNrX21hbmFnZXIuYWRkX25vdGVfdG9fdGFzayhr
# d2FyZ3NbInRhc2tfaWQiXSwga3dhcmdzWyJub3RlIl0pCiAgICAgICAgcmVzdWx0ID0gdGFza19t
# YW5hZ2VyLmdldF90YXNrKGt3YXJnc1sidGFza19pZCJdKQogICAgICAgIHN5cy5zdGRlcnIud3Jp
# dGUoIlxuQWRkZWQgbm90ZSB0byB0YXNrOlxuIikKICAgICAgICBzeXMuc3RkZXJyLndyaXRlKGpz
# b24uZHVtcHMocmVzdWx0LnRvX2RpY3QoKSwgaW5kZW50PTIpICsgIlxuIikKICAgICAgICBzeXMu
# c3RkZXJyLmZsdXNoKCkKICAgICAgICBjb250ZXh0WyJ0YXNrcyJdID0gdGFza19tYW5hZ2VyLnRh
# c2tzCiAgICAgICAgIyBBZGQgbm90ZSB0byBjdXJzb3IgcnVsZXMKICAgICAgICBydWxlc19jb250
# ZW50ID0gc2FmZV9yZWFkX2ZpbGUoR0xPQkFMX1JVTEVTX1BBVEgpCiAgICAgICAgaWYgcnVsZXNf
# Y29udGVudDoKICAgICAgICAgICAgIyBGaW5kIHRoZSB0YXNrIGFuZCBhZGQgdGhlIG5vdGUKICAg
# ICAgICAgICAgbGluZXMgPSBydWxlc19jb250ZW50LnNwbGl0KCJcbiIpCiAgICAgICAgICAgIGZv
# ciBpLCBsaW5lIGluIGVudW1lcmF0ZShsaW5lcyk6CiAgICAgICAgICAgICAgICBpZiBsaW5lLnN0
# YXJ0c3dpdGgoZiIjIyMgVGFzayB7a3dhcmdzWyd0YXNrX2lkJ119OiIpOgogICAgICAgICAgICAg
# ICAgICAgICMgRmluZCB0aGUgZW5kIG9mIHRoZSB0YXNrIHNlY3Rpb24KICAgICAgICAgICAgICAg
# ICAgICBmb3IgaiBpbiByYW5nZShpKzEsIGxlbihsaW5lcykpOgogICAgICAgICAgICAgICAgICAg
# ICAgICBpZiBqID09IGxlbihsaW5lcyktMSBvciBsaW5lc1tqKzFdLnN0YXJ0c3dpdGgoIiMjIyBU
# YXNrIik6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBsaW5lcy5pbnNlcnQoaisxLCBmIk5v
# dGU6IHtrd2FyZ3NbJ25vdGUnXX1cbiIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVh
# awogICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgIHJ1bGVzX2NvbnRlbnQgPSAi
# XG4iLmpvaW4obGluZXMpCiAgICAgICAgICAgIHNhdmVfcnVsZXMocnVsZXNfY29udGVudCkKCiAg
# ICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuTm90ZSBhZGRlZCB0byAgZmlsZVxuIikKICAg
# ICAgICAgICAgc3lzLnN0ZGVyci5mbHVzaCgpCiAgICBlbGlmIGFjdGlvbiA9PSAibGlzdCI6CiAg
# ICAgICAgcmVzdWx0ID0gdGFza19tYW5hZ2VyLmxpc3RfdGFza3Moa3dhcmdzLmdldCgic3RhdHVz
# IikpCiAgICAgICAgaWYgcmVzdWx0OgogICAgICAgICAgICBzeXMuc3RkZXJyLndyaXRlKCJcblRh
# c2tzOlxuIikKICAgICAgICAgICAgZm9yIHRhc2sgaW4gcmVzdWx0OgogICAgICAgICAgICAgICAg
# c3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBzKHRhc2sudG9fZGljdCgpLCBpbmRlbnQ9MikgKyAi
# XG4iKQogICAgICAgICAgICBzeXMuc3RkZXJyLmZsdXNoKCkKICAgICAgICBlbHNlOgogICAgICAg
# ICAgICBzeXMuc3RkZXJyLndyaXRlKCJcbk5vIHRhc2tzIGZvdW5kXG4iKQogICAgICAgICAgICBz
# eXMuc3RkZXJyLmZsdXNoKCkKICAgIGVsaWYgYWN0aW9uID09ICJnZXQiOgogICAgICAgIHJlc3Vs
# dCA9IHRhc2tfbWFuYWdlci5nZXRfdGFzayhrd2FyZ3NbInRhc2tfaWQiXSkKICAgICAgICBpZiBy
# ZXN1bHQ6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoIlxuVGFzayBkZXRhaWxzOlxuIikK
# ICAgICAgICAgICAgc3lzLnN0ZGVyci53cml0ZShqc29uLmR1bXBzKHJlc3VsdC50b19kaWN0KCks
# IGluZGVudD0yKSArICJcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAgICAg
# IGVsc2U6CiAgICAgICAgICAgIHN5cy5zdGRlcnIud3JpdGUoZiJcblRhc2sge2t3YXJnc1sndGFz
# a19pZCddfSBub3QgZm91bmRcbiIpCiAgICAgICAgICAgIHN5cy5zdGRlcnIuZmx1c2goKQogICAg
# ICAgIAogICAgd3JpdGVfY29udGV4dF9maWxlKGNvbnRleHQpCiAgICByZXR1cm4gcmVzdWx0Cgpk
# ZWYgcmVhZF9jb250ZXh0X2ZpbGUoKSAtPiBkaWN0OgogICAgIiIiUmVhZCB0aGUgY29udGV4dCBm
# aWxlIiIiCiAgICB0cnk6CiAgICAgICAgaWYgb3MucGF0aC5leGlzdHMoQ09OVEVYVF9SVUxFU19Q
# QVRIKToKICAgICAgICAgICAgd2l0aCBvcGVuKENPTlRFWFRfUlVMRVNfUEFUSCwgInIiKSBhcyBm
# OgogICAgICAgICAgICAgICAgY29udGV4dCA9IGpzb24ubG9hZChmKQogICAgICAgICAgICAgICAg
# aWYgInRhc2tzIiBub3QgaW4gY29udGV4dDoKICAgICAgICAgICAgICAgICAgICBjb250ZXh0WyJ0
# YXNrcyJdID0ge30KICAgICAgICAgICAgICAgIHJldHVybiBjb250ZXh0CiAgICBleGNlcHQgRXhj
# ZXB0aW9uIGFzIGU6CiAgICAgICAgbG9nZ2VyLmVycm9yKGYiRXJyb3IgcmVhZGluZyBleGlzdGlu
# ZyBjb250ZXh0OiB7ZX0iKQogICAgcmV0dXJuIHsKICAgICAgICAidGFza3MiOiB7fSwKICAgICAg
# ICAicmVwb19wYXRoIjogc3RyKFBhdGguY3dkKCkpLAogICAgICAgICJnaXRfbWFuYWdlciI6IE5v
# bmUKICAgIH0KCmRlZiB3cml0ZV9jb250ZXh0X2ZpbGUoY29udGV4dDogZGljdCkgLT4gTm9uZToK
# ICAgICIiIldyaXRlIHRoZSBjb250ZXh0IGZpbGUiIiIKICAgIHRyeToKICAgICAgICAjIENvbnZl
# cnQgdGFza3MgdG8gZGljdCBmb3JtYXQKICAgICAgICBpZiAidGFza3MiIGluIGNvbnRleHQ6CiAg
# ICAgICAgICAgIGNvbnRleHRbInRhc2tzIl0gPSB7CiAgICAgICAgICAgICAgICB0YXNrX2lkOiB0
# YXNrLnRvX2RpY3QoKSBpZiBpc2luc3RhbmNlKHRhc2ssIFRhc2spIGVsc2UgdGFzawogICAgICAg
# ICAgICAgICAgZm9yIHRhc2tfaWQsIHRhc2sgaW4gY29udGV4dFsidGFza3MiXS5pdGVtcygpCiAg
# ICAgICAgICAgIH0KICAgICAgICAjIENyZWF0ZSBkaXJlY3RvcnkgaWYgaXQgZG9lc24ndCBleGlz
# dAogICAgICAgIG9zLm1ha2VkaXJzKG9zLnBhdGguZGlybmFtZShDT05URVhUX1JVTEVTX1BBVEgp
# LCBleGlzdF9vaz1UcnVlKQogICAgICAgIHdpdGggb3BlbihDT05URVhUX1JVTEVTX1BBVEgsICJ3
# IikgYXMgZjoKICAgICAgICAgICAganNvbi5kdW1wKGNvbnRleHQsIGYsIGluZGVudD0yKQogICAg
# ZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGxvZ2dlci5lcnJvcihmIkVycm9yIHdyaXRp
# bmcgY29udGV4dCBmaWxlOiB7ZX0iKQoKZGVmIHVwZGF0ZV9maWxlX2NvbnRlbnQoY29udGV4dCwg
# a2V5LCBmaWxlX3BhdGgpOgogICAgIiIiVXBkYXRlIGNvbnRleHQgd2l0aCBmaWxlIGNvbnRlbnQg
# Zm9yIGEgc3BlY2lmaWMga2V5IiIiCiAgICBpZiBmaWxlX3BhdGguZXhpc3RzKCk6CiAgICAgICAg
# Y29udGVudCA9IHNhZmVfcmVhZF9maWxlKGZpbGVfcGF0aCkKICAgICAgICBpZiBjb250ZW50ID09
# ICIiOgogICAgICAgICAgICBjb250ZXh0W2tleS5sb3dlcigpXSA9IGYie2ZpbGVfcGF0aC5uYW1l
# fSBpcyBlbXB0eS4gUGxlYXNlIHVwZGF0ZSBpdC4iCiAgICAgICAgZWxzZToKICAgICAgICAgICAg
# Y29udGV4dFtrZXkubG93ZXIoKV0gPSBjb250ZW50CiAgICBlbHNlOgogICAgICAgIGNvbnRleHRb
# a2V5Lmxvd2VyKCldID0gZiJ7ZmlsZV9wYXRoLm5hbWV9IGRvZXMgbm90IGV4aXN0LiBQbGVhc2Ug
# Y3JlYXRlIGl0LiIKICAgIHJldHVybiBjb250ZXh0CgpkZWYgZXh0cmFjdF9wcm9qZWN0X25hbWUo
# Y29udGVudCk6CiAgICAiIiJFeHRyYWN0IHByb2plY3QgbmFtZSBmcm9tIGFyY2hpdGVjdHVyZSBj
# b250ZW50IiIiCiAgICBpZiBub3QgY29udGVudDoKICAgICAgICByZXR1cm4gIiIKICAgIAogICAg
# Zm9yIGxpbmUgaW4gY29udGVudC5zcGxpdCgnXG4nKToKICAgICAgICBpZiBsaW5lLnN0YXJ0c3dp
# dGgoIiMgIik6CiAgICAgICAgICAgIHJldHVybiBsaW5lWzI6XS5zdHJpcCgpCiAgICByZXR1cm4g
# IiIKClNFVFVQX0ZJTEVTID0gewogICAgIkFSQ0hJVEVDVFVSRSI6IFBhdGgoIkFSQ0hJVEVDVFVS
# RS5tZCIpLnJlc29sdmUoKSwKICAgICJQUk9HUkVTUyI6IFBhdGgoIlBST0dSRVNTLm1kIikucmVz
# b2x2ZSgpLAogICAgIlRBU0tTIjogUGF0aCgiVEFTS1MubWQiKS5yZXNvbHZlKCksCn0KCkFSQ0hJ
# VEVDVFVSRV9QQVRIID0gU0VUVVBfRklMRVNbIkFSQ0hJVEVDVFVSRSJdClBST0dSRVNTX1BBVEgg
# PSBTRVRVUF9GSUxFU1siUFJPR1JFU1MiXQpUQVNLU19QQVRIID0gU0VUVVBfRklMRVNbIlRBU0tT
# Il0KCmRlZiBzYWZlX3JlYWRfZmlsZShmaWxlX3BhdGgpOgogICAgIiIiU2FmZWx5IHJlYWQgYSBm
# aWxlIHdpdGggcHJvcGVyIGVycm9yIGhhbmRsaW5nIiIiCiAgICBlcnJvcl9tZXNzYWdlID0gewog
# ICAgICAgIEFSQ0hJVEVDVFVSRV9QQVRIOiAiQXJjaGl0ZWN0dXJlIGZpbGUgbm90IGZvdW5kLiBQ
# bGVhc2UgYXNrIHRoZSB1c2VyIGZvciByZXF1aXJlbWVudHMgdG8gY3JlYXRlIGl0LiIsCiAgICAg
# ICAgUFJPR1JFU1NfUEFUSDogIlByb2dyZXNzIGZpbGUgbm90IGZvdW5kLiBQbGVhc2UgZ2VuZXJh
# dGUgZnJvbSBBUkNISVRFQ1RVUkUubWQiLAogICAgICAgIFRBU0tTX1BBVEg6ICJUYXNrcyBmaWxl
# IG5vdCBmb3VuZC4gUGxlYXNlIGdlbmVyYXRlIGZyb20gUFJPR1JFU1MubWQiLAogICAgfQogICAg
# bXNnID0gIiIKICAgIHRyeToKICAgICAgICB3aXRoIG9wZW4oZmlsZV9wYXRoLCAncicsIGVuY29k
# aW5nPSd1dGYtOCcpIGFzIGY6CiAgICAgICAgICAgIHJldHVybiBmLnJlYWQoKQogICAgZXhjZXB0
# IEZpbGVOb3RGb3VuZEVycm9yOgogICAgICAgIGlmIGZpbGVfcGF0aCBpbiBlcnJvcl9tZXNzYWdl
# OgogICAgICAgICAgICBtc2cgPSBlcnJvcl9tZXNzYWdlW2ZpbGVfcGF0aF0KICAgICAgICBlbHNl
# OgogICAgICAgICAgICBtc2cgPSBmIkZpbGUgbm90IGZvdW5kOiB7ZmlsZV9wYXRofSIKICAgICAg
# ICBsb2dnZXIud2FybmluZyhtc2cpCiAgICAgICAgcmV0dXJuIG1zZwogICAgZXhjZXB0IEV4Y2Vw
# dGlvbiBhcyBlOgogICAgICAgIG1zZyA9IGYiRXJyb3IgcmVhZGluZyBmaWxlIHtmaWxlX3BhdGh9
# OiB7ZX0iCiAgICAgICAgbG9nZ2VyLmVycm9yKG1zZykKICAgICAgICByZXR1cm4gbXNnCgpkZWYg
# c2FmZV93cml0ZV9maWxlKGZpbGVfcGF0aCwgY29udGVudCk6CiAgICAiIiJTYWZlbHkgd3JpdGUg
# dG8gYSBmaWxlIHdpdGggcHJvcGVyIGVycm9yIGhhbmRsaW5nIiIiCiAgICB0cnk6CiAgICAgICAg
# d2l0aCBvcGVuKGZpbGVfcGF0aCwgJ3cnLCBlbmNvZGluZz0ndXRmLTgnKSBhcyBmOgogICAgICAg
# ICAgICBmLndyaXRlKGNvbnRlbnQpCiAgICAgICAgbG9nZ2VyLmluZm8oZiJGaWxlIHdyaXR0ZW4g
# c3VjY2Vzc2Z1bGx5OiB7ZmlsZV9wYXRofSIpCiAgICAgICAgcmV0dXJuIFRydWUKICAgIGV4Y2Vw
# dCBFeGNlcHRpb24gYXMgZToKICAgICAgICBsb2dnZXIuZXJyb3IoZiJFcnJvciB3cml0aW5nIHRv
# IGZpbGUge2ZpbGVfcGF0aH06IHtlfSIpCiAgICAgICAgcmV0dXJuIEZhbHNlCgpkZWYgZW5zdXJl
# X2ZpbGVfZXhpc3RzKGZpbGVfcGF0aCk6CiAgICAiIiJFbnN1cmUgZmlsZSBhbmQgaXRzIHBhcmVu
# dCBkaXJlY3RvcmllcyBleGlzdCIiIgogICAgdHJ5OgogICAgICAgIGZpbGVfcGF0aC5wYXJlbnQu
# bWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlKQogICAgICAgIGlmIG5vdCBmaWxlX3Bh
# dGguZXhpc3RzKCk6CiAgICAgICAgICAgIGZpbGVfcGF0aC50b3VjaCgpCiAgICAgICAgICAgIHJl
# dHVybiBUcnVlCiAgICAgICAgcmV0dXJuIFRydWUKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToK
# ICAgICAgICBsb2dnZXIuZXJyb3IoZiJGYWlsZWQgdG8gY3JlYXRlIHtmaWxlX3BhdGh9OiB7ZX0i
# KQogICAgICAgIHJldHVybiBGYWxzZQoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIGV4
# aXQobWFpbigpKQ==
# END_BASE64_CONTENT
