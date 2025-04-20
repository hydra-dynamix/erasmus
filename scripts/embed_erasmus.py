#!/usr/bin/env python3
import sys
import base64
import os

BANNER = """#!/usr/bin/env bash
# Erasmus Self-Extracting Installer
# Usage: bash thisfile.sh

# Universal Installer for Erasmus
# This script will extract the embedded erasmus.py and run it with uv
"""

INSTALLER_BODY = """
# Unpack erasmus.py from this script (self-extracting)
SCRIPT_PATH="$0"
EMBED_MARKER="# BEGIN_BASE64_CONTENT"
END_MARKER="# END_BASE64_CONTENT"

BASE64_CONTENT=$(awk "/$EMBED_MARKER/{flag=1;next}/$END_MARKER/{flag=0}flag" "$SCRIPT_PATH" | tr -d '# ')
if [ -z "$BASE64_CONTENT" ]; then
    echo "Error: Could not extract embedded erasmus.py"
    exit 1
fi

echo "$BASE64_CONTENT" | base64 -d > erasmus.py

# Install uv if needed
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    if command -v brew &>/dev/null; then
        brew install astral/tap/uv
    elif command -v apt-get &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v winget &>/dev/null; then
        winget install astral.uv
    else
        echo "Please install uv manually: https://astral.sh/uv"
        exit 1
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

export PATH="$HOME/.local/bin:$PATH"

# Run erasmus.py setup with uv
uv run erasmus.py setup

echo "Erasmus setup complete. Restart your shell and run `erasmus setup` to start."

exit 0
"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 embed_erasmus.py <input_py_file> <output_sh_file>")
        sys.exit(1)
    input_py = sys.argv[1]
    output_sh = sys.argv[2]
    if not os.path.isfile(input_py):
        print(f"Error: {input_py} not found")
        sys.exit(1)
    with open(input_py, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    with open(output_sh, "w") as out:
        out.write(BANNER)
        out.write(INSTALLER_BODY)
        out.write("\n# BEGIN_BASE64_CONTENT\n")
        # Write base64, 76 chars per line
        for i in range(0, len(encoded), 76):
            out.write(f"# {encoded[i : i + 76]}\n")
        out.write("# END_BASE64_CONTENT\n")
    os.chmod(output_sh, 0o755)
    print(f"Installer created: {output_sh}")
