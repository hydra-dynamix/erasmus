import json
import logging
from unittest.mock import patch

import pytest
import pytest_asyncio

from erasmus.sync.file_sync import FileSynchronizer


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with mock project files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create mock project files
    (workspace / "architecture.md").write_text("# architecture\nTest content")
    (workspace / "tasks.md").write_text("# tasks\nTest content")
    (workspace / "progress.md").write_text("# progress\nTest content")

    return workspace

@pytest.fixture
def temp_rules_dir(tmp_path):
    """Create a temporary rules directory."""
    rules_dir = tmp_path / ".cursorrules"
    rules_dir.mkdir()
    return rules_dir

@pytest_asyncio.fixture
async def file_sync(temp_workspace, temp_rules_dir):
    """Create a FileSynchronizer instance with test directories."""
    syncer = FileSynchronizer(
        workspace_path=temp_workspace,
        rules_dir=temp_rules_dir,
    )
    await syncer.start()
    yield syncer
    await syncer.stop()

@pytest.mark.asyncio
async def test_sync_all_files(file_sync, temp_workspace, temp_rules_dir):
    """Test synchronizing all project files to rules directory."""
    # Sync all files
    await file_sync.sync_all()

    # Check that rules.json exists and contains correct content
    rules_file = temp_rules_dir / "rules.json"
    assert rules_file.exists()

    # Verify content was copied correctly
    rules = json.loads(rules_file.read_text())
    for filename, key in FileSynchronizer.TRACKED_FILES.items():
        source_content = (temp_workspace / filename).read_text()
        assert rules[key] == source_content

@pytest.mark.asyncio
async def test_sync_single_file(file_sync, temp_rules_dir):
    """Test synchronizing a single file to rules directory."""
    # Sync only architecture.md
    await file_sync.sync_file("architecture.md")

    # Check that rules.json exists and contains correct content
    rules_file = temp_rules_dir / "rules.json"
    assert rules_file.exists()

    # Verify content
    rules = json.loads(rules_file.read_text())
    assert rules["architecture"] == "# architecture\nTest content"
    assert "tasks" not in rules
    assert "progress" not in rules

@pytest.mark.asyncio
async def test_handle_missing_source_file(file_sync):
    """Test handling of missing source files."""
    # Try to sync a non-existent file
    with pytest.raises(FileNotFoundError):
        await file_sync.sync_file("NONEXISTENT.md")

@pytest.mark.asyncio
async def test_handle_permission_error(file_sync):
    """Test handling of permission errors during sync."""
    # Make rules directory read-only
    temp_rules_dir.chmod(0o444)

    # Try to sync files to read-only directory
    with pytest.raises(PermissionError):
        await file_sync.sync_all()

@pytest.mark.asyncio
async def test_auto_create_rules_dir(temp_workspace, tmp_path):
    """Test automatic creation of rules directory if it doesn't exist."""
    rules_dir = tmp_path / ".cursorrules"

    # Create synchronizer without existing rules directory
    syncer = FileSynchronizer(
        workspace_path=temp_workspace,
        rules_dir=rules_dir,
    )
    await syncer.start()

    try:
        # Sync files
        await syncer.sync_all()

        # Check that rules directory was created
        assert rules_dir.exists()
        assert rules_dir.is_dir()
    finally:
        await syncer.stop()

@pytest.mark.asyncio
async def test_update_existing_file(file_sync, temp_workspace, temp_rules_dir):
    """Test updating an existing file in rules directory."""
    # Initial sync
    await file_sync.sync_file("architecture.md")

    # Modify source file
    new_content = "# architecture\nUpdated content"
    (temp_workspace / "architecture.md").write_text(new_content)

    # Sync again
    await file_sync.sync_file("architecture.md")

    # Verify content was updated
    rules_file = temp_rules_dir / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert rules["architecture"] == new_content

@pytest.mark.asyncio
async def test_cleanup_removed_files(file_sync, temp_workspace, temp_rules_dir):
    """Test cleanup of files that no longer exist in workspace."""
    # Initial sync
    await file_sync.sync_all()

    # Remove a file from workspace
    (temp_workspace / "tasks.md").unlink()

    # Run cleanup
    await file_sync.cleanup()

    # Check that file was removed from rules
    rules_file = temp_rules_dir / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert "tasks" not in rules

@pytest.mark.asyncio
async def test_sync_file_runtime_error(file_sync):
    """Test handling of runtime errors during file sync."""
    # Create a mock that raises a runtime error
    with patch('erasmus.sync.file_sync.safe_write_file', side_effect=RuntimeError("Mock error")):
        with pytest.raises(RuntimeError) as exc_info:
            await file_sync.sync_file("architecture.md")
        assert "Failed to sync file" in str(exc_info.value)

@pytest.mark.asyncio
async def test_cleanup_error_handling(file_sync, temp_workspace, caplog):
    """Test error handling during cleanup."""
    # Set up logging capture
    caplog.set_level(logging.WARNING)

    # Initial sync
    await file_sync.sync_all()

    # Remove workspace file
    (temp_workspace / "tasks.md").unlink()

    # Mock safe_write_file to raise an error
    with patch('erasmus.sync.file_sync.safe_write_file', side_effect=Exception("Mock error")):
        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            await file_sync.cleanup()
        assert "Failed to clean up rules: Mock error" in str(exc_info.value)
        assert "Error during cleanup" in caplog.text

@pytest.mark.asyncio
async def test_get_sync_status(file_sync, temp_workspace):
    """Test getting synchronization status for all files."""
    # Initial state - no files in rules directory
    status = await file_sync.get_sync_status()
    assert len(status) == len(FileSynchronizer.TRACKED_FILES)

    # Check initial status
    for _, info in status.items():
        assert info["exists"] is True
        assert info["synced"] is False
        assert info["last_sync"] is None

    # Sync one file
    await file_sync.sync_file("architecture.md")
    status = await file_sync.get_sync_status()

    # Check status after sync
    assert status["architecture.md"]["exists"] is True
    assert status["architecture.md"]["synced"] is True
    assert status["architecture.md"]["last_sync"] is not None

    # Modify file in workspace
    (temp_workspace / "architecture.md").write_text("Modified content")
    status = await file_sync.get_sync_status()
    assert status["architecture.md"]["synced"] is False

@pytest.mark.asyncio
async def test_get_sync_status_with_errors(file_sync, temp_workspace):
    """Test sync status handling when file operations fail."""
    # Initial sync
    await file_sync.sync_all()

    # Remove a file to simulate error
    (temp_workspace / "tasks.md").unlink()

    # Get status
    status = await file_sync.get_sync_status()

    # Check error status
    assert status["tasks.md"]["exists"] is False
    assert status["tasks.md"]["synced"] is False
    assert status["tasks.md"]["last_sync"] is None
