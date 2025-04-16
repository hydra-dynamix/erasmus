"""Test cursor integration functionality."""

import pytest
import pytest_asyncio
import json
from pathlib import Path
from erasmus.ide.cursor_integration import CursorContextManager
from erasmus.utils.paths import SetupPaths
import asyncio


@pytest.fixture
def setup_paths(tmp_path):
    """Create a test environment with SetupPaths."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return SetupPaths.with_project_root(workspace)


@pytest_asyncio.fixture
async def context_manager(setup_paths):
    """Create a test environment with a CursorContextManager."""
    # Create test files
    for file in [".architecture.md", ".progress.md", ".tasks.md"]:
        path = setup_paths.project_root / file
        path.write_text(f"Test content for {file}")

    # Initialize context manager
    manager = CursorContextManager(setup_paths.project_root)
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_initialization(context_manager, setup_paths):
    """Test context manager initialization."""
    assert setup_paths.rules_file.exists()
    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules == {}  # Initial state should be empty


@pytest.mark.asyncio
async def test_queue_single_update(context_manager, setup_paths):
    """Test queuing and processing a single update."""
    await context_manager.queue_update("context", "Test update")
    await context_manager.process_updates()  # Explicitly process updates

    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules["context"] == "Test update"


@pytest.mark.asyncio
async def test_queue_multiple_updates(context_manager, setup_paths):
    """Test queuing and processing multiple updates."""
    updates = ["Update 1", "Update 2", "Update 3"]
    for update in updates:
        await context_manager.queue_update("context", update)
    await context_manager.process_updates()

    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules["context"] == updates[-1]  # Should keep last update


@pytest.mark.asyncio
async def test_file_change_handling(context_manager, setup_paths):
    """Test handling of file changes."""
    file = ".tasks.md"
    new_content = "Updated tasks content"

    # Update file
    (setup_paths.project_root / file).write_text(new_content)
    await context_manager.handle_file_change(file)
    await context_manager.process_updates()

    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules[file] == new_content


@pytest.mark.asyncio
async def test_error_handling(context_manager, setup_paths):
    """Test error handling during updates."""
    # Create invalid rules file
    setup_paths.rules_file.write_text("invalid json")

    # Queue update and process
    await context_manager.queue_update("context", "Test update")
    await context_manager.process_updates()

    # Should recover and write valid JSON
    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules["context"] == "Test update"


@pytest.mark.asyncio
async def test_concurrent_updates(context_manager, setup_paths):
    """Test handling of concurrent updates."""
    # Queue multiple updates concurrently
    await asyncio.gather(
        *[context_manager.queue_update("context", f"Update {i}") for i in range(5)]
    )
    await context_manager.process_updates()

    rules = json.loads(setup_paths.rules_file.read_text())
    assert rules["context"] == "Update 4"  # Should keep last update


@pytest.mark.asyncio
async def test_get_status(context_manager):
    """Test getting context manager status."""
    status = context_manager.get_status()
    assert status["is_running"] is True
    assert status["has_errors"] is False
    assert not status["pending_updates"]
    assert not status["errors"]
    assert isinstance(status["last_update"], dict)
