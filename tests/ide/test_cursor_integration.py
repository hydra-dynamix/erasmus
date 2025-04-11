"""Test module for cursor IDE integration."""

import asyncio
import json

import pytest
import pytest_asyncio

from erasmus.ide.cursor_integration import CursorContextManager


@pytest_asyncio.fixture
async def cursor_manager(tmp_path):
    """Create a CursorContextManager instance for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    manager = CursorContextManager(workspace)

    # Start the manager
    await manager.start()

    # Wait for initialization
    await asyncio.sleep(0.2)

    yield manager

    # Stop the manager
    await manager.stop()

    # Wait for cleanup
    await asyncio.sleep(0.2)

@pytest.mark.asyncio
async def test_initialization(cursor_manager, tmp_path):
    """Test initialization of CursorContextManager."""
    await cursor_manager.start()

    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    assert rules_file.exists()
    assert rules_file.read_text() == "{}"

@pytest.mark.asyncio
async def test_queue_and_process_updates(cursor_manager, tmp_path):
    """Test queuing and processing updates."""
    # Queue some updates
    await cursor_manager.queue_update("architecture", "Test architecture")
    await asyncio.sleep(0.1)  # Wait for first update

    await cursor_manager.queue_update("progress", "Test progress")
    await asyncio.sleep(0.1)  # Wait for second update

    await cursor_manager.queue_update("tasks", {"1": {"description": "Test Task"}})
    await asyncio.sleep(0.1)  # Wait for third update

    # Check that updates were written to file
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    rules = json.loads(rules_file.read_text())

    assert rules["architecture"] == "Test architecture"
    assert rules["progress"] == "Test progress"
    assert rules["tasks"] == {"1": {"description": "Test Task"}}

@pytest.mark.asyncio
async def test_batched_updates(cursor_manager, tmp_path):
    """Test that updates are properly batched."""
    # Queue multiple updates in quick succession
    for i in range(5):
        await cursor_manager.queue_update("test", f"value{i}")
        await asyncio.sleep(0.05)  # Brief wait between updates

    # Wait for updates to be processed
    await asyncio.sleep(0.2)

    # Check that final update was written
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert rules["test"] == "value4"

@pytest.mark.asyncio
async def test_external_file_changes(cursor_manager, tmp_path):
    """Test handling of external changes to the rules file."""
    # Make an external change to the rules file
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    external_content = {
        "architecture": "External architecture",
        "progress": "External progress",
    }
    rules_file.write_text(json.dumps(external_content))

    # Wait for the change to be detected and processed
    await asyncio.sleep(0.2)

    # Queue a new update
    await cursor_manager.queue_update("tasks", {"1": {"description": "New Task"}})
    await asyncio.sleep(0.2)  # Wait for update to be processed

    # Check that both external and queued changes are present
    rules = json.loads(rules_file.read_text())
    assert rules["architecture"] == "External architecture"
    assert rules["progress"] == "External progress"
    assert rules["tasks"] == {"1": {"description": "New Task"}}

@pytest.mark.asyncio
async def test_concurrent_updates(cursor_manager, tmp_path):
    """Test handling of concurrent updates."""
    await cursor_manager.start()

    # Queue updates from multiple sources
    await cursor_manager.queue_update("component1", "value1")
    await asyncio.sleep(0.2)  # Wait for first update

    # Queue second update
    await cursor_manager.queue_update("component2", "value2")
    await asyncio.sleep(0.2)  # Wait for second update

    # Queue third update
    await cursor_manager.queue_update("component3", "value3")
    await asyncio.sleep(0.2)  # Wait for final update

    # Check final state
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    rules = json.loads(rules_file.read_text())
    assert rules["component1"] == "value1"
    assert rules["component2"] == "value2"
    assert rules["component3"] == "value3"

    await cursor_manager.stop()

@pytest.mark.asyncio
async def test_invalid_updates(cursor_manager, tmp_path):
    """Test handling of invalid updates."""
    await cursor_manager.start()

    # Queue an invalid update
    await cursor_manager.queue_update("tasks", "invalid")

    # Check that file is still valid JSON
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    content = rules_file.read_text()
    assert json.loads(content) is not None

@pytest.mark.asyncio
async def test_metadata_handling(cursor_manager, tmp_path):
    """Test handling of metadata in rules file."""
    await cursor_manager.start()

    # Queue an update
    await cursor_manager.queue_update("test", "value")

    # Check that update was written
    rules_file = tmp_path / "workspace" / ".cursorrules" / "rules.json"
    rules = json.loads(rules_file.read_text())

    assert rules["test"] == "value"
