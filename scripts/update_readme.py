#!/usr/bin/env python3
import os
import json
import re

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(PROJECT_ROOT, "version.json")
README_FILE = os.path.join(PROJECT_ROOT, "README.md")


def update_readme_curl_command():
    """
    Updates the curl command in README.md with the latest version from version.json.
    The curl command is expected to be in the format:
    curl -sSL https://raw.githubusercontent.com/hydra-dynamix/erasmus/refs/heads/main/releases/install.sh | bash -s -- 0.2.1
    """
    # Read version from version.json
    if not os.path.exists(VERSION_FILE):
        raise FileNotFoundError(f"Version file not found: {VERSION_FILE}")

    with open(VERSION_FILE, "r") as f:
        version_data = json.load(f)
        version = version_data.get("version")
        if not version:
            raise ValueError("No version found in version.json")

    # Read README.md
    if not os.path.exists(README_FILE):
        raise FileNotFoundError(f"README file not found: {README_FILE}")

    with open(README_FILE, "r") as f:
        readme_lines = f.readlines()
    # Find and update the curl command line
    curl_pattern = f"curl -sSL https://raw.githubusercontent.com/bakobiibizo/erasmus/refs/heads/main/releases/erasmus/{version}/erasmus_v{version}.sh -o erasmus.sh && bash erasmus.sh\n"
    updated = False

    for i, line in enumerate(readme_lines):
        if "curl -sSL https://raw.githubusercontent.com/" in line:
            readme_lines[i] = curl_pattern
            updated = True
            break
            
    if updated:
        with open(README_FILE, "w") as f:
            f.writelines(readme_lines)
        print(f"Updated README.md with version {version}")
    else:
        print("Could not find the expected curl command pattern in README.md")
        print(f"Expected pattern: {curl_pattern} X.Y.Z")


if __name__ == "__main__":
    update_readme_curl_command()
