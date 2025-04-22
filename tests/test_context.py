import os
import pytest
import shutil
from erasmus.context import ContextManager, ContextError, ContextFileError


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up any existing test contexts before each test."""
    yield
    # Clean up after each test
    test_contexts = ["test_context", "custom_context", "duplicate_context", "invalid_context"]
    manager = ContextManager()
    for context in test_contexts:
        context_dir = manager.path_manager.get_context_dir() / context
        if context_dir.exists():
            shutil.rmtree(context_dir)


@pytest.fixture
def context_manager(tmp_path):
    """Create a ContextManager instance for testing."""
    manager = ContextManager(base_dir=tmp_path)
    yield manager


@pytest.fixture
def sample_context_files(context_manager):
    """Create sample context files for testing."""
    context_dir = context_manager.path_manager.get_context_dir() / "test_context"
    context_dir.mkdir(parents=True, exist_ok=True)

    # Create sample architecture file
    arch_file = context_dir / ".ctx.architecture.xml"
    arch_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<Architecture>
    <Overview>
        <Description>Test architecture</Description>
    </Overview>
</Architecture>""")

    # Create sample progress file
    progress_file = context_dir / ".ctx.progress.xml"
    progress_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<Progress>
    <Phase name="Test Phase">
        <Status>In Progress</Status>
    </Phase>
</Progress>""")

    # Create sample tasks file
    tasks_file = context_dir / ".ctx.tasks.xml"
    tasks_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<Tasks>
    <CurrentTasks>
        <Task name="Test Task">
            <Status>Pending</Status>
        </Task>
    </CurrentTasks>
</Tasks>""")

    return context_dir


def test_create_context(context_manager):
    """Test creating a new context."""
    context_name = "test_context"
    context_manager.create_context(context_name)

    # Verify context directory was created
    context_dir = context_manager.path_manager.get_context_dir() / context_name
    assert context_dir.exists()

    # Verify all required files were created
    assert (context_dir / ".ctx.architecture.xml").exists()
    assert (context_dir / ".ctx.progress.xml").exists()
    assert (context_dir / ".ctx.tasks.xml").exists()


def test_create_context_with_custom_content(context_manager):
    """Test creating a context with custom content."""
    context_name = "custom_context"
    custom_arch = """<?xml version="1.0" encoding="UTF-8"?>
<Architecture>
    <Overview>
        <Description>Custom architecture</Description>
    </Overview>
</Architecture>"""

    context_manager.create_context(context_name, architecture_content=custom_arch)

    # Verify custom content was used
    context_dir = context_manager.path_manager.get_context_dir() / context_name
    arch_content = (context_dir / ".ctx.architecture.xml").read_text()
    assert "Custom architecture" in arch_content


def test_create_duplicate_context(context_manager):
    """Test creating a context with a name that already exists."""
    context_name = "duplicate_context"
    context_manager.create_context(context_name)

    with pytest.raises(ContextError):
        context_manager.create_context(context_name)


def test_delete_context(context_manager, sample_context_files):
    """Test deleting a context."""
    context_name = "test_context"
    context_manager.delete_context(context_name)

    # Verify context was deleted
    context_dir = context_manager.path_manager.get_context_dir() / context_name
    assert not context_dir.exists()


def test_delete_nonexistent_context(context_manager):
    """Test deleting a context that doesn't exist."""
    with pytest.raises(ContextError):
        context_manager.delete_context("nonexistent_context")


def test_list_contexts(context_manager, sample_context_files):
    """Test listing available contexts."""
    contexts = context_manager.list_contexts()
    assert "test_context" in contexts


def test_select_context(context_manager, sample_context_files):
    """Test selecting a context."""
    context_name = "test_context"
    context_manager.select_context(context_name)

    # Verify context was loaded
    assert context_manager.current_context == context_name
    assert context_manager.architecture is not None
    assert context_manager.progress is not None
    assert context_manager.tasks is not None


def test_select_nonexistent_context(context_manager):
    """Test selecting a context that doesn't exist."""
    with pytest.raises(ContextError):
        context_manager.select_context("nonexistent_context")


def test_update_architecture(context_manager, sample_context_files):
    """Test updating architecture content."""
    context_name = "test_context"
    context_manager.select_context(context_name)

    new_content = """<?xml version="1.0" encoding="UTF-8"?>
<Architecture>
    <Overview>
        <Description>Updated architecture</Description>
    </Overview>
</Architecture>"""

    context_manager.update_architecture(content=new_content)
    arch_file = sample_context_files / ".ctx.architecture.xml"
    assert "Updated architecture" in arch_file.read_text()


def test_update_progress(context_manager, sample_context_files):
    """Test updating progress content."""
    context_name = "test_context"
    context_manager.select_context(context_name)

    new_content = """<?xml version="1.0" encoding="UTF-8"?>
<Progress>
    <Phase name="Updated Phase">
        <Status>Completed</Status>
    </Phase>
</Progress>"""

    context_manager.update_progress(content=new_content)
    progress_file = sample_context_files / ".ctx.progress.xml"
    assert "Updated Phase" in progress_file.read_text()


def test_update_tasks(context_manager, sample_context_files):
    """Test updating tasks content."""
    context_name = "test_context"
    context_manager.select_context(context_name)

    new_content = """<?xml version="1.0" encoding="UTF-8"?>
<Tasks>
    <CurrentTasks>
        <Task name="Updated Task">
            <Status>In Progress</Status>
        </Task>
    </CurrentTasks>
</Tasks>"""

    context_manager.update_tasks(content=new_content)
    tasks_file = sample_context_files / ".ctx.tasks.xml"
    assert "Updated Task" in tasks_file.read_text()


def test_sanitize_name(context_manager):
    """Test context name sanitization."""
    # Test various invalid characters
    assert context_manager._sanitize_name("test/context") == "test_context"
    assert context_manager._sanitize_name("test\\context") == "test_context"
    assert context_manager._sanitize_name("test:context") == "test_context"
    assert context_manager._sanitize_name("test*context") == "test_context"

    # Test valid name
    assert context_manager._sanitize_name("valid_context") == "valid_context"


def test_invalid_xml_content(context_manager):
    """Test handling of invalid XML content."""
    context_name = "invalid_context"
    invalid_xml = "This is not valid XML"

    with pytest.raises(ValueError, match="Invalid XML content"):
        context_manager.create_context(context_name, architecture_content=invalid_xml)
