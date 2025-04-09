"""Test module for synchronization integration."""

import json
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio
from erasmus.ide.cursor_integration import CursorContextManager
from erasmus.ide.sync_integration import SyncIntegration
from erasmus.utils.file import safe_read_file, safe_write_file

@pytest_asyncio.fixture
async def sync_setup(tmp_path):
    """Create a test environment with necessary files and managers."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create source files
    (workspace / "ARCHITECTURE.md").write_text("# Test Architecture")
    (workspace / "PROGRESS.md").write_text("# Test Progress")
    (workspace / "TASKS.md").write_text("# Test Tasks")
    
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
    assert rules["architecture"] == "# Test Architecture"
    assert "progress" in rules
    assert rules["progress"] == "# Test Progress"
    assert "tasks" in rules
    assert rules["tasks"] == "# Test Tasks"

@pytest.mark.asyncio
async def test_file_change_sync(sync_setup):
    """Test synchronization when source files change."""
    workspace, context_manager = sync_setup
    
    # Modify a source file
    (workspace / "ARCHITECTURE.md").write_text("# Updated Architecture")
    
    # Wait for sync
    await asyncio.sleep(0.5)
    
    # Check rules file was updated
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)
    
    # Wait additional time to ensure file system sync
    await asyncio.sleep(0.2)
    
    assert rules["architecture"] == "# Updated Architecture"

@pytest.mark.asyncio
async def test_context_change_sync(sync_setup):
    """Test synchronization when context changes."""
    workspace, context_manager = sync_setup
    
    # Queue an update through context manager
    await context_manager.queue_update("architecture", "# Changed via Context")
    
    # Wait for sync
    await asyncio.sleep(0.5)
    
    # Check source file was updated
    arch_content = safe_read_file(workspace / "ARCHITECTURE.md")
    assert arch_content == "# Changed via Context"

@pytest.mark.asyncio
async def test_concurrent_changes(sync_setup):
    """Test handling of concurrent changes from multiple sources."""
    workspace, context_manager = sync_setup
    
    # Create multiple concurrent changes
    (workspace / "PROGRESS.md").write_text("# Progress Update 1")
    await context_manager.queue_update("tasks", "# Tasks Update 1")
    (workspace / "ARCHITECTURE.md").write_text("# Architecture Update 1")
    
    # Wait for all changes to sync
    await asyncio.sleep(1.0)
    
    # Additional wait to ensure file system sync
    await asyncio.sleep(0.2)
    
    # Verify final state
    rules_content = safe_read_file(workspace / ".cursorrules" / "rules.json")
    rules = json.loads(rules_content)
    
    assert rules["progress"] == "# Progress Update 1"
    assert rules["tasks"] == "# Tasks Update 1"
    assert rules["architecture"] == "# Architecture Update 1"
    
    # Verify source files
    assert safe_read_file(workspace / "PROGRESS.md") == "# Progress Update 1"
    assert safe_read_file(workspace / "TASKS.md") == "# Tasks Update 1"
    assert safe_read_file(workspace / "ARCHITECTURE.md") == "# Architecture Update 1"

@pytest.mark.asyncio
async def test_error_handling(sync_setup):
    """Test error handling during synchronization."""
    workspace, context_manager = sync_setup
    
    # Create an invalid JSON in rules file
    (workspace / ".cursorrules" / "rules.json").write_text("{invalid json")
    
    # Try to sync changes
    (workspace / "ARCHITECTURE.md").write_text("# Should Still Work")
    
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
    
    arch_content = safe_read_file(workspace / "ARCHITECTURE.md")
    assert arch_content == "# Recovery Test" 