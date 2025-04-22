import os
import json
import pytest
from scripts.update_readme import update_readme_curl_command


@pytest.fixture
def setup_test_files(tmp_path):
    # Create a temporary version.json
    version_data = {"version": "1.2.3"}
    version_file = tmp_path / "version.json"
    version_file.write_text(json.dumps(version_data))

    # Create a temporary README.md with the install block
    readme_content = """# Test README
Some content here

## Installation
```bash
curl -sSL https://raw.githubusercontent.com/hydra-dynamix/erasmus/refs/heads/main/releases/install.sh | bash -s -- 1.0.0
```

More content here
"""
    readme_file = tmp_path / "README.md"
    readme_file.write_text(readme_content)

    return version_file, readme_file


def test_update_readme_curl_command(setup_test_files, monkeypatch):
    version_file, readme_file = setup_test_files

    # Patch the file paths to use our temporary files
    monkeypatch.setattr("scripts.update_readme.VERSION_FILE", str(version_file))
    monkeypatch.setattr("scripts.update_readme.README_FILE", str(readme_file))

    # Run the update function
    update_readme_curl_command()

    # Read the updated README content
    updated_content = readme_file.read_text()

    # Check that the version was updated correctly
    expected_curl = "curl -sSL https://raw.githubusercontent.com/hydra-dynamix/erasmus/refs/heads/main/releases/install.sh | bash -s -- 1.2.3"
    assert expected_curl in updated_content


def test_no_update_needed(setup_test_files, monkeypatch):
    version_file, readme_file = setup_test_files

    # First update to get to the latest version
    monkeypatch.setattr("scripts.update_readme.VERSION_FILE", str(version_file))
    monkeypatch.setattr("scripts.update_readme.README_FILE", str(readme_file))
    update_readme_curl_command()

    # Get the content after first update
    content_after_first = readme_file.read_text()

    # Run update again
    update_readme_curl_command()
    content_after_second = readme_file.read_text()

    # Content should be identical since no update was needed
    assert content_after_first == content_after_second


def test_missing_version_file(tmp_path, monkeypatch):
    # Point to a non-existent version file
    non_existent = tmp_path / "non_existent.json"
    monkeypatch.setattr("scripts.update_readme.VERSION_FILE", str(non_existent))

    with pytest.raises(FileNotFoundError):
        update_readme_curl_command()


def test_missing_readme_file(setup_test_files, tmp_path, monkeypatch):
    version_file, _ = setup_test_files
    non_existent = tmp_path / "non_existent.md"

    monkeypatch.setattr("scripts.update_readme.VERSION_FILE", str(version_file))
    monkeypatch.setattr("scripts.update_readme.README_FILE", str(non_existent))

    with pytest.raises(FileNotFoundError):
        update_readme_curl_command()
