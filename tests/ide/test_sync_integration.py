import pytest
import pytest_asyncio
import json
import asyncio

from erasmus.utils.context import ContextManager
from erasmus.utils.paths import SetupPaths
from erasmus.utils.file_ops import safe_read_file


@pytest_asyncio.fixture
async def sync_setup(tmp_path):
    """Create a test environment with necessary files and managers."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # Add required context files
    erasmus_dir = workspace / ".erasmus"
    erasmus_dir.mkdir(exist_ok=True)
    (erasmus_dir / ".architecture.md").write_text("# architecture\nTest content")
    (erasmus_dir / ".progress.md").write_text("# progress\nTest content")
    (erasmus_dir / ".tasks.md").write_text(json.dumps({"1": "Test content"}))

    # Create source files
    (workspace / ".erasmus/.architecture.md").write_text("# Test architecture")
    (workspace / ".progress.md").write_text("# Test progress")
    (workspace / ".tasks.md").write_text(json.dumps({"1": "Test tasks"}))

    # Create rules directory (ensure it's not a file)
    setup_paths = SetupPaths.with_project_root(workspace)
    rules_path = setup_paths.rules_file
    if rules_path.exists() and not rules_path.parent.is_dir():
        rules_path.parent.unlink()  # Remove file so we can create dir
    rules_path.parent.mkdir(exist_ok=True)
    initial_rules = {"architecture": "# Test architecture", "progress": "# Test progress", "tasks": {}}
    rules_path.write_text(json.dumps(initial_rules))


    # Initialize managers
    print("[DEBUG] workspace path:", workspace)
    print("[DEBUG] .erasmus/.architecture.md path:", workspace / ".erasmus/.architecture.md")
    context_manager = ContextManager(workspace_root=workspace)

    # Start the manager and wait for initialization
    await context_manager.initialize()
    await asyncio.sleep(0.5)  # Wait for initial sync to complete

    yield workspace, context_manager

    await asyncio.sleep(0.2)  # Wait for cleanup to complete


@pytest.mark.asyncio
async def test_initial_sync(sync_setup):
    """Test initial synchronization of files."""
    workspace, context_manager = sync_setup

    # Check rules file content
    setup_paths = SetupPaths.with_project_root(workspace)
    rules_content = safe_read_file(setup_paths.rules_file)
    rules = json.loads(rules_content)
    if "tasks" in rules and not isinstance(rules["tasks"], dict):
        try:
            parsed = json.loads(rules["tasks"]) if isinstance(rules["tasks"], str) else rules["tasks"]
            if isinstance(parsed, dict):
                rules["tasks"] = parsed
            else:
                rules["tasks"] = {}
        except Exception:
            rules["tasks"] = {}

    assert "architecture" in rules
    assert rules["architecture"] == "# Test architecture"
    assert "progress" in rules
    assert rules["progress"] == "# Test progress"
    assert "tasks" in rules
    assert isinstance(rules["tasks"], dict)
    # Optionally check dict content if needed


@pytest.mark.asyncio
async def test_file_change_sync(sync_setup):
    """Test synchronization when source files change."""
    workspace, context_manager = sync_setup

    # Modify a source file
    (workspace / ".erasmus/.architecture.md").write_text("# Updated architecture")
    print("[DEBUG] .erasmus/.architecture.md after write:", (workspace / ".erasmus/.architecture.md").read_text())

    # Force a manual sync of all tracked files
    await context_manager.file_synchronizer.sync_all()
    setup_paths = SetupPaths.with_project_root(workspace)
    print("[DEBUG] rules file after sync_all:", safe_read_file(setup_paths.rules_file))

    # Wait for sync
    await asyncio.sleep(0.5)

    # Check rules file was updated
    rules_content = safe_read_file(setup_paths.rules_file)
    rules = json.loads(rules_content)
    if "tasks" in rules and not isinstance(rules["tasks"], dict):
        try:
            parsed = json.loads(rules["tasks"]) if isinstance(rules["tasks"], str) else rules["tasks"]
            if isinstance(parsed, dict):
                rules["tasks"] = parsed
            else:
                rules["tasks"] = {}
        except Exception:
            rules["tasks"] = {}

    # Wait additional time to ensure file system sync
    await asyncio.sleep(0.2)

    assert rules["architecture"] == "# Updated architecture"


@pytest.mark.asyncio
async def test_context_change_sync(sync_setup):
    """Test synchronization when context changes."""
    workspace, context_manager = sync_setup

    # Queue an update through context manager
    await context_manager.update_context("tasks", {"1": "# Changed via Context"})
    await context_manager.update_context("architecture", "# Changed via Context")

    # Wait for sync
    await asyncio.sleep(0.5)

    # Check rules file was updated
    setup_paths = SetupPaths.with_project_root(workspace)
    rules_content = safe_read_file(setup_paths.rules_file)
    rules = json.loads(rules_content)
    if "tasks" in rules and not isinstance(rules["tasks"], dict):
        try:
            parsed = json.loads(rules["tasks"]) if isinstance(rules["tasks"], str) else rules["tasks"]
            if isinstance(parsed, dict):
                rules["tasks"] = parsed
            else:
                rules["tasks"] = {}
        except Exception:
            rules["tasks"] = {}
    assert rules["architecture"] == "# Changed via Context"
    assert rules["tasks"] == {"1": "# Changed via Context"}

    # Check source file was updated
    architecture_content = safe_read_file(workspace / ".erasmus/.architecture.md")
    assert architecture_content == "# Changed via Context"


@pytest.mark.asyncio
async def test_concurrent_changes(sync_setup):
    """Test handling of concurrent changes from multiple sources."""
    workspace, context_manager = sync_setup

    # Create multiple concurrent changes
    (workspace / ".progress.md").write_text("# progress Update 1")
    await context_manager.update_context("tasks", {"1": "# tasks Update 1"})
    (workspace / ".erasmus/.architecture.md").write_text("# architecture Update 1")

    # Wait for all changes to sync
    await asyncio.sleep(1.0)

    # Additional wait to ensure file system sync
    await asyncio.sleep(0.2)

    # Verify final state
    setup_paths = SetupPaths.with_project_root(workspace)
    rules_content = safe_read_file(setup_paths.rules_file)
    rules = json.loads(rules_content)
    if "tasks" in rules and not isinstance(rules["tasks"], dict):
        try:
            parsed = json.loads(rules["tasks"]) if isinstance(rules["tasks"], str) else rules["tasks"]
            if isinstance(parsed, dict):
                rules["tasks"] = parsed
            else:
                rules["tasks"] = {}
        except Exception:
            rules["tasks"] = {}

    assert rules["progress"] == "# progress Update 1"
    assert rules["tasks"] == {"1": "# tasks Update 1"}
    assert rules["architecture"] == "# architecture Update 1"

    # Verify source files
    assert safe_read_file(workspace / ".progress.md") == "# progress Update 1"
    # The tasks file should contain the value from the dict
    assert safe_read_file(workspace / ".tasks.md") == "# tasks Update 1"
    assert safe_read_file(workspace / ".erasmus/.architecture.md") == "# architecture Update 1"


@pytest.mark.asyncio
async def test_error_handling(sync_setup):
    """Test error handling during synchronization."""
    workspace, context_manager = sync_setup

    # Create an invalid JSON in rules file
    setup_paths = SetupPaths.with_project_root(workspace)
    setup_paths.rules_file.write_text("{invalid json")

    # Try to sync changes
    (workspace / ".erasmus/.architecture.md").write_text("# Should Still Work")

    # Wait for recovery
    await asyncio.sleep(0.5)

    # Wait for recovery and additional sync time
    await asyncio.sleep(1.0)

    # Verify system recovered and sync still works
    await context_manager.update_context("tasks", {"1": "# Recovery Test"})
    await context_manager.update_context("architecture", "# Recovery Test")
    await asyncio.sleep(0.5)

    # Check both files
    setup_paths = SetupPaths.with_project_root(workspace)
    rules_content = safe_read_file(setup_paths.rules_file)
    rules = json.loads(rules_content)
    if "tasks" in rules and not isinstance(rules["tasks"], dict):
        try:
            parsed = json.loads(rules["tasks"]) if isinstance(rules["tasks"], str) else rules["tasks"]
            if isinstance(parsed, dict):
                rules["tasks"] = parsed
            else:
                rules["tasks"] = {}
        except Exception:
            rules["tasks"] = {}
    assert rules["architecture"] == "# Recovery Test"
    assert rules["tasks"] == {"1": "# Recovery Test"}

    architecture_content = safe_read_file(workspace / ".erasmus/.architecture.md")
    assert architecture_content == "# Recovery Test"
    # The tasks file should contain the value from the dict
    assert safe_read_file(workspace / ".tasks.md") == "# Recovery Test"
