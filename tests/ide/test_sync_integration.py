"""Test module for synchronization integration."""

import asyncio
import json

import pytest
import pytest_asyncio

from erasmus.ide.cursor_integration import CursorContextManager
from erasmus.utils.file import safe_read_file


@pytest_asyncio.fixture
async def sync_setup(tmp_path):
    """Create a test environment with necessary files and managers."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create source files
    (workspace / ".erasmus/architecture.md").write_text("# Test architecture")
    (workspace / "progress.md").write_text("# Test progress")
    (workspace / "tasks.md").write_text("# Test tasks")

    # Create rules directory
    rules_dir = workspace / ".cursorrules"
    rules_dir.mkdir()
    (rules_dir / "rules.json").write_text("{}")

    # Initialize managers
    context_manager = CursorContextManager(workspace)

    # Start the manager and wait for initialization
    await context_manager.start()
    await asyncio.sleep(0.5)  # Wait for initial sync to complete

    yield workspace, context_manager

    # Stop the manager and wait for cleanup
    await context_manager.stop()
    await asyncio.sleep(0.2)  # Wait for cleanup to complete


@pytest.mark.asyncio
async def test_initial_sync(sync_setup):
    """Test initial synchronization of files."""
    workspace, context_manager = sync_setup

    # Check rules file content
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)

    assert "architecture" in rules
    assert rules["architecture"] == "# Test architecture"
    assert "progress" in rules
    assert rules["progress"] == "# Test progress"
    assert "tasks" in rules
    assert rules["tasks"] == "# Test tasks"


@pytest.mark.asyncio
async def test_file_change_sync(sync_setup):
    """Test synchronization when source files change."""
    workspace, context_manager = sync_setup

    # Modify a source file
    (workspace / ".erasmus/architecture.md").write_text("# Updated architecture")

    # Wait for sync
    await asyncio.sleep(0.5)

    # Check rules file was updated
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)

    # Wait additional time to ensure file system sync
    await asyncio.sleep(0.2)

    assert rules["architecture"] == "# Updated architecture"


@pytest.mark.asyncio
async def test_context_change_sync(sync_setup):
    """Test synchronization when context changes."""
    workspace, context_manager = sync_setup

    # Queue an update through context manager
    await context_manager.queue_update("architecture", "# Changed via Context")

    # Wait for sync
    await asyncio.sleep(0.5)

    # Check source file was updated
    architecture_content = safe_read_file(workspace / ".erasmus/architecture.md")
    assert architecture_content == "# Changed via Context"


@pytest.mark.asyncio
async def test_concurrent_changes(sync_setup):
    """Test handling of concurrent changes from multiple sources."""
    workspace, context_manager = sync_setup

    # Create multiple concurrent changes
    (workspace / "progress.md").write_text("# progress Update 1")
    await context_manager.queue_update("tasks", "# tasks Update 1")
    (workspace / ".erasmus/architecture.md").write_text("# architecture Update 1")

    # Wait for all changes to sync
    await asyncio.sleep(1.0)

    # Additional wait to ensure file system sync
    await asyncio.sleep(0.2)

    # Verify final state
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)

    assert rules["progress"] == "# progress Update 1"
    assert rules["tasks"] == "# tasks Update 1"
    assert rules["architecture"] == "# architecture Update 1"

    # Verify source files
    assert safe_read_file(workspace / "progress.md") == "# progress Update 1"
    assert safe_read_file(workspace / "tasks.md") == "# tasks Update 1"
    assert safe_read_file(workspace / ".erasmus/architecture.md") == "# architecture Update 1"


@pytest.mark.asyncio
async def test_error_handling(sync_setup):
    """Test error handling during synchronization."""
    workspace, context_manager = sync_setup

    # Create an invalid JSON in rules file
    (workspace / ".cursorrules" / "rules.json").write_text("{invalid json")

    # Try to sync changes
    (workspace / ".erasmus/architecture.md").write_text("# Should Still Work")

    # Wait for recovery
    await asyncio.sleep(0.5)

    # Wait for recovery and additional sync time
    await asyncio.sleep(1.0)

    # Verify system recovered and sync still works
    await context_manager.queue_update("architecture", "# Recovery Test")
    await asyncio.sleep(0.5)

    # Check both files
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)
    assert rules["architecture"] == "# Recovery Test"

    architecture_content = safe_read_file(workspace / ".erasmus/architecture.md")
    assert architecture_content == "# Recovery Test"
