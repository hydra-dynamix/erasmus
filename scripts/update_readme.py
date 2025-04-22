#!/usr/bin/env python3
from pathlib import Path
import json
import re

def update_readme_curl_command():
    # Resolve paths using pathlib
    base_path = Path(__file__).resolve().parent.parent
    version_file = base_path / 'version.json'
    readme_path = base_path / 'README.md'

    # Read version from version.json using pathlib
    version_data = json.loads(version_file.read_text())
    version = version_data['version']

    # Read README.md using pathlib
    readme_content = readme_path.read_text()

    # Update curl command with current version
    def replace_version(match):
        return match.group(1) + version

    curl_pattern = r'(curl -L https://raw.githubusercontent.com/Bakobiibizo/Erasmus/main/install\.sh \| bash -s -- v)\d+\.\d+\.\d+'
    updated_readme = re.sub(
        curl_pattern,
        replace_version,
        readme_content,
        flags=re.MULTILINE
    )

    # Write back to README.md if changes were made
    if updated_readme != readme_content:
        readme_path.write_text(updated_readme)
        print(f"Updated README.md with version {version}")
    else:
        print("No updates needed to README.md")

if __name__ == '__main__':
    update_readme_curl_command()