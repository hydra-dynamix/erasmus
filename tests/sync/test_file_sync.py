"""Tests for file synchronization functionality."""

import asyncio
import json
import os
import pytest
import pytest_asyncio
from pathlib import Path

from erasmus.sync.file_sync import FileSynchronizer
from erasmus.utils.paths import SetupPaths


@pytest.fixture
def setup_paths(tmp_path):
    """Create a SetupPaths instance for testing."""
    return SetupPaths(project_root=tmp_path)


@pytest_asyncio.fixture
async def sync_env(tmp_path, setup_paths):
    """Set up test environment with workspace and rules directories."""
    # Create test files
    for file in FileSynchronizer.TRACKED_FILES:
        test_file = tmp_path / file
        test_file.write_text(f"Test content for {file}")

    # Initialize synchronizer
    sync = FileSynchronizer(setup_paths)
    await sync.start()

    yield sync
    await sync.stop()


@pytest.mark.asyncio
async def test_initialization(sync_env, setup_paths):
    """Test that the synchronizer initializes correctly."""
    assert os.path.exists(setup_paths.rules_file)
    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    assert isinstance(rules, dict)


@pytest.mark.asyncio
async def test_sync_file(sync_env, setup_paths):
    """Test syncing a single file."""
    test_file = os.path.join(setup_paths.project_root, ".architecture.md")
    await sync_env.sync_file(test_file)

    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    assert rules["architecture"] == "Test content for .architecture.md"


@pytest.mark.asyncio
async def test_sync_all(sync_env, setup_paths):
    """Test syncing all tracked files."""
    await sync_env.sync_all()

    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    for file in FileSynchronizer.TRACKED_FILES:
        key = (
            file[1:-3] if file.startswith(".") else file[:-3]
        )  # Remove leading dot and .md extension
        assert rules[key] == f"Test content for {file}"


@pytest.mark.asyncio
async def test_missing_file(sync_env, setup_paths):
    """Test handling of missing files."""
    missing_file = os.path.join(setup_paths.project_root, "missing.md")
    with pytest.raises(FileNotFoundError):
        await sync_env.sync_file(missing_file)
    status = sync_env.get_status()
    assert missing_file in status["errors"]
    assert "File not found" in status["errors"][missing_file]


@pytest.mark.asyncio
async def test_invalid_rules_file(sync_env, setup_paths):
    """Test handling of invalid JSON in rules file."""
    # Write invalid JSON to rules file
    with open(setup_paths.rules_file, "w") as f:
        f.write("invalid json")

    # Attempt to sync should raise JSONDecodeError
    test_file = os.path.join(setup_paths.project_root, ".architecture.md")
    with pytest.raises(json.JSONDecodeError):
        await sync_env._update_rules_file()  # Test directly on _update_rules_file


@pytest.mark.asyncio
async def test_file_update(sync_env, setup_paths):
    """Test updating an existing file."""
    test_file = os.path.join(setup_paths.project_root, ".architecture.md")

    # Initial sync
    await sync_env.sync_file(test_file)

    # Update file
    with open(test_file, "w") as f:
        f.write("Updated content")
    await sync_env.sync_file(test_file)

    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    assert rules["architecture"] == "Updated content"


@pytest.mark.asyncio
async def test_sync_status(sync_env, setup_paths):
    """Test tracking sync status."""
    test_file = os.path.join(setup_paths.project_root, ".architecture.md")
    with open(test_file, "w") as f:
        f.write("New content")

    await sync_env.sync_file(test_file)
    assert sync_env.content_cache[test_file] == "New content"


@pytest.mark.asyncio
async def test_error_recovery(sync_env, setup_paths):
    """Test recovery from sync errors."""
    test_file = os.path.join(setup_paths.project_root, ".architecture.md")

    # Create test content
    with open(test_file, "w") as f:
        f.write("Test content")

    # Create invalid rules file
    with open(setup_paths.rules_file, "w") as f:
        f.write("invalid json")

    # Attempt sync should raise an error
    with pytest.raises(json.JSONDecodeError):
        await sync_env._update_rules_file()

    # Fix rules file and retry
    await sync_env.create_rules_file()
    await sync_env.sync_file(test_file)

    # Verify sync succeeded
    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    assert "architecture" in rules
    assert rules["architecture"] == "Test content"


@pytest.mark.asyncio
async def test_handle_permission_error(sync_env, setup_paths):
    """Test handling of permission errors."""
    # Ensure rules file exists and is writable
    os.makedirs(os.path.dirname(setup_paths.rules_file), exist_ok=True)
    with open(setup_paths.rules_file, "w") as f:
        f.write("{}")

    # Make rules file read-only
    os.chmod(setup_paths.rules_file, 0o444)

    # Attempt to write should raise PermissionError
    with pytest.raises(PermissionError):
        await sync_env._update_rules_file()  # Test directly on _update_rules_file

    status = sync_env.get_status()
    assert setup_paths.rules_file in status["errors"]


@pytest.mark.asyncio
async def test_update_existing_file(sync_env, setup_paths):
    """Test updating an already synchronized file."""
    file_path = os.path.join(setup_paths.project_root, ".architecture.md")

    # Initial sync
    await sync_env.sync_file(file_path)

    # Update content
    new_content = "Updated content"
    with open(file_path, "w") as f:
        f.write(new_content)

    # Sync again
    await sync_env.sync_file(file_path)

    with open(setup_paths.rules_file) as f:
        rules = json.load(f)
    assert rules["architecture"] == new_content


@pytest.mark.asyncio
async def test_sync_file_runtime_error(sync_env, setup_paths):
    """Test handling of runtime errors during sync."""
    file_path = os.path.join(setup_paths.project_root, ".architecture.md")

    # Ensure file exists before making it unreadable
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write("test")

    # Make file unreadable
    os.chmod(file_path, 0o000)

    with pytest.raises(PermissionError):
        await sync_env.sync_file(file_path)

    status = sync_env.get_status()
    assert file_path in status["errors"]


@pytest.mark.asyncio
async def test_get_status(sync_env):
    """Test status reporting."""
    status = sync_env.get_status()
    assert "running" in status
    assert "errors" in status
    assert "pending_syncs" in status
    assert "last_sync" in status
    assert isinstance(status["errors"], dict)
    assert isinstance(status["pending_syncs"], list)
    assert isinstance(status["last_sync"], dict)
