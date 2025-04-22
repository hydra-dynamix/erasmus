import pytest
from erasmus.context import ContextManager
import time
from pathlib import Path


def test_get_default_content_error():
    cm = ContextManager()
    with pytest.raises(ValueError) as excinfo:
        cm.get_default_content("unsupported")
    assert "Unsupported file type" in str(excinfo.value)


def test_get_default_content_valid_types():
    cm = ContextManager()
    for file_type in [
        "architecture",
        "progress",
        "tasks",
        "protocol",
        "meta_agent",
        "meta_rules",
    ]:
        content = cm.get_default_content(file_type)
        assert isinstance(content, str)
        assert len(content) > 0


def test_context_file_operations(tmp_path):
    """Test context file operations with proper cleanup."""
    cm = ContextManager(base_path=str(tmp_path))
    context_name = "testctx"

    # Create context
    cm.create_context(context_name)

    try:
        # Verify context directory exists
        context_dir = tmp_path / context_name
        assert context_dir.exists()

        # Update files
        test_arch = "<test>architecture</test>"
        test_prog = "<test>progress</test>"
        test_tasks = "<test>tasks</test>"

        cm.update_architecture(context_name, test_arch)
        cm.update_progress(context_name, test_prog)
        cm.update_tasks(context_name, test_tasks)

        # Verify files exist
        assert (context_dir / ".ctx.architecture.xml").exists()
        assert (context_dir / ".ctx.progress.xml").exists()
        assert (context_dir / ".ctx.tasks.xml").exists()

        # Read back and verify content
        assert cm.load_context_file(context_name, ".ctx.architecture.xml") == test_arch
        assert cm.load_context_file(context_name, ".ctx.progress.xml") == test_prog
        assert cm.load_context_file(context_name, ".ctx.tasks.xml") == test_tasks

        # Test file listing
        files = cm.list_context_files(context_name)
        assert len(files) == 3
        assert ".ctx.architecture.xml" in files
        assert ".ctx.progress.xml" in files
        assert ".ctx.tasks.xml" in files

    finally:
        # Clean up
        if context_dir.exists():
            cm.delete_context(context_name)
            assert not context_dir.exists()
