"""Tests for file synchronization functionality."""

import json
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from erasmus.sync.file_sync import FileSynchronizer

@pytest_asyncio.fixture
async def sync_env(tmp_path):
    """Create a test environment with workspace and rules directories."""
    workspace = tmp_path / "workspace"
    rules_dir = workspace / ".cursorrules"
    workspace.mkdir()
    
    # Create test files
    for filename in FileSynchronizer.TRACKED_FILES:
        file_path = workspace / filename
        file_path.write_text(f"Test content for {filename}")
    
    # Create synchronizer
    syncer = FileSynchronizer(workspace, rules_dir)
    await syncer.start()
    await syncer.sync_all()
    
    yield workspace, rules_dir, syncer
    
    # Cleanup
    await syncer.stop()

@pytest.mark.asyncio
async def test_initial_sync(sync_env):
    """Test initial synchronization of files."""
    workspace, rules_dir, syncer = sync_env
    
    # Check that rules.json was created
    rules_file = rules_dir / "rules.json"
    assert rules_file.exists()
    
    # Verify content
    rules = json.loads(rules_file.read_text())
    for filename, key in FileSynchronizer.TRACKED_FILES.items():
        assert key in rules
        assert rules[key] == f"Test content for {filename}"

@pytest.mark.asyncio
async def test_file_change_detection(sync_env):
    """Test detection and synchronization of file changes."""
    workspace, rules_dir, syncer = sync_env
    
    # Modify a file
    test_file = workspace / "TASKS.md"
    test_file.write_text("Updated content")
    
    # Wait for sync
    await asyncio.sleep(1.0)
    
    # Verify update
    rules_file = rules_dir / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert rules["tasks"] == "Updated content"

@pytest.mark.asyncio
async def test_multiple_rapid_updates(sync_env):
    """Test handling of multiple rapid file updates."""
    workspace, rules_dir, syncer = sync_env
    
    # Make multiple rapid changes
    test_file = workspace / "PROGRESS.md"
    for i in range(5):
        test_file.write_text(f"Update {i}")
        await asyncio.sleep(0.1)
    
    # Wait for final sync
    await asyncio.sleep(1.0)
    
    # Verify only last update was saved
    rules_file = rules_dir / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert rules["progress"] == "Update 4"

@pytest.mark.asyncio
async def test_missing_file_handling(sync_env):
    """Test handling of missing source files."""
    workspace, rules_dir, syncer = sync_env
    
    # First sync the file
    await syncer.sync_file("ARCHITECTURE.md")
    
    # Delete a source file
    test_file = workspace / "ARCHITECTURE.md"
    test_file.unlink()
    
    # Try to sync the file again
    with pytest.raises(FileNotFoundError):
        await syncer.sync_file("ARCHITECTURE.md")
    
    # Verify rules were cleaned up
    rules_file = rules_dir / "rules.json"
    assert rules_file.exists()
    rules = json.loads(rules_file.read_text())
    assert "architecture" not in rules

@pytest.mark.asyncio
async def test_sync_status(tmp_path):
    """Test sync status reporting."""
    # Create a new environment without initial sync
    workspace = tmp_path / "workspace"
    rules_dir = workspace / ".cursorrules"
    workspace.mkdir()
    
    # Create test files
    for filename in FileSynchronizer.TRACKED_FILES:
        file_path = workspace / filename
        file_path.write_text(f"Test content for {filename}")
    
    # Create synchronizer
    syncer = FileSynchronizer(workspace, rules_dir)
    await syncer.start()
    
    # Get initial status
    status = await syncer.get_sync_status()
    assert all(info['exists'] for info in status.values())
    assert not any(info['synced'] for info in status.values())
    
    # Sync a file
    await syncer.sync_file("TASKS.md")
    
    # Check updated status
    new_status = await syncer.get_sync_status()
    assert new_status["TASKS.md"]["exists"]
    assert new_status["TASKS.md"]["synced"]
    assert new_status["TASKS.md"]["last_sync"] is not None
    
    # Cleanup
    await syncer.stop()

@pytest.mark.asyncio
async def test_concurrent_updates(sync_env):
    """Test handling of concurrent file updates."""
    workspace, rules_dir, syncer = sync_env
    
    # Update multiple files concurrently
    files = ["ARCHITECTURE.md", "TASKS.md", "PROGRESS.md"]
    for i, filename in enumerate(files):
        file_path = workspace / filename
        file_path.write_text(f"Concurrent update {i}")
    
    # Wait for syncs to complete
    await asyncio.sleep(1.0)
    
    # Verify all updates were processed
    rules_file = rules_dir / "rules.json"
    rules = json.loads(rules_file.read_text())
    for i, (filename, key) in enumerate(FileSynchronizer.TRACKED_FILES.items()):
        assert rules[key] == f"Concurrent update {i}"

@pytest.mark.asyncio
async def test_error_recovery(sync_env):
    """Test recovery from errors during sync."""
    workspace, rules_dir, syncer = sync_env
    
    # Create an invalid rules file
    rules_file = rules_dir / "rules.json"
    rules_file.write_text("invalid json")
    
    # Update a file
    test_file = workspace / "TASKS.md"
    test_file.write_text("Test recovery")
    
    # Wait for sync
    await asyncio.sleep(1.0)
    
    # Verify recovery
    rules = json.loads(rules_file.read_text())
    assert rules["tasks"] == "Test recovery" 