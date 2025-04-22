#!/usr/bin/env python3
from pathlib import Path
import json
import re


def update_readme_curl_command():
    # Resolve paths using pathlib
    base_path = Path.cwd()
    version_file = base_path / "version.json"
    readme_path = base_path / "README.md"

    target_one = "### Quick Install\n\n```bash\ncurl -L https://raw.githubusercontent.com/bakobiibizo/erasmus/main/releases/erasmus/"
    target_two = "/erasmus_v"

    # Get version
    version = json.loads(version_file.read_text())["version"]

    # Read README
    readme_content = readme_path.read_text()

    # Regex to match the install block
    pattern = re.compile(
        re.escape(target_one) + r"[^/]+" + re.escape(target_two) + r"(\d+\.\d+\.\d+)[^`]*```",
        re.MULTILINE,
    )

    # Replacement string
    replacement = f"{target_one}erasmus{target_two}{version}\n```"

    # Replace the block
    new_content, count = pattern.subn(replacement, readme_content)
    if count > 0:
        readme_path.write_text(new_content)
        print(f"Updated README.md with version {version}")
    else:
        print("No install block found or no update needed.")


if __name__ == "__main__":
    update_readme_curl_command()
