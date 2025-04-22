import pytest
from erasmus.context import ContextManager


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
    cm = ContextManager()
    context_name = "testctx"
    # Create context
    cm.create_context(context_name)
    # Update files
    cm.update_architecture(context_name, "<Architecture><Title>Test</Title></Architecture>")
    cm.update_progress(context_name, "<Progress></Progress>")
    cm.update_tasks(context_name, "<Tasks></Tasks>")
    # Read files
    arch = cm.load_context_file(context_name, "ctx.architecture.xml")
    prog = cm.load_context_file(context_name, "ctx.progress.xml")
    tasks = cm.load_context_file(context_name, "ctx.tasks.xml")
    assert "<Architecture>" in arch
    assert "<Progress>" in prog
    assert "<Tasks>" in tasks
    # Delete files
    cm.delete_context_file(context_name, "ctx.architecture.xml")
    assert cm.load_context_file(context_name, "ctx.architecture.xml") == ""
