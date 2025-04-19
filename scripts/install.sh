#!/usr/bin/env bash

# Universal Installer for Watcher Project
# Supports Windows (via Git Bash/WSL), macOS, and Linux

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect operating system
OS="Unknown"
case "$(uname -s)" in
Darwin*) OS='macOS' ;;
Linux*) OS='Linux' ;;
MINGW* | MSYS* | CYGWIN*) OS='Windows' ;;
*) OS='Unknown' ;;
esac

# Unpack erasmus.py from this script (self-extracting)
SCRIPT_PATH="$0"
EMBED_MARKER="# BEGIN_BASE64_CONTENT"
END_MARKER="# END_BASE64_CONTENT"

BASE64_CONTENT=$(awk "/$EMBED_MARKER/{flag=1;next}/$END_MARKER/{flag=0}flag" "$SCRIPT_PATH" | tr -d '# ')
if [ -z "$BASE64_CONTENT" ]; then
    echo -e "${RED}Error: Could not extract embedded erasmus.py${NC}"
    exit 1
fi

echo "$BASE64_CONTENT" | base64 -d >erasmus.py

# Install uv if needed
if ! command -v uv &>/dev/null; then
    echo -e "${YELLOW}Installing uv...${NC}"
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
        export PATH="$HOME/.local/bin:$PATH"
        ;;
    esac
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run erasmus.py with uv
uv run erasmus.py "$@"
