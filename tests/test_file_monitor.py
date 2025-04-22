"""Tests for file monitoring functionality."""

import os
import time
import pytest
from pathlib import Path
from watchdog.events import FileSystemEvent
from erasmus.file_monitor import ContextFileMonitor, ContextFileHandler
from erasmus.environment import is_debug_enabled


def wait_for_event(timeout: float = 1.0, interval: float = 0.1) -> None:
    """Wait for file system events to be processed."""
    time.sleep(timeout)


class BaseMockPathManager:
    """Base mock path manager with all required properties."""

    def __init__(self, root_dir, ide=None):
        self.root_dir = root_dir

    def get_architecture_file(self):
        return self.root_dir / ".ctx.architecture.xml"

    def get_rules_file(self):
        return self.root_dir / ".rules"

    def get_progress_file(self):
        return self.root_dir / ".ctx.progress.xml"

    def get_tasks_file(self):
        return self.root_dir / ".ctx.tasks.xml"

    @property
    def template_dir(self):
        return self.root_dir / "templates"

    @property
    def protocol_dir(self):
        return self.root_dir / "protocols"

    @property
    def erasmus_dir(self):
        return self.root_dir / ".erasmus"


@pytest.fixture
def mock_path_manager(monkeypatch, tmp_path):
    """Mock path manager to use temporary directory."""
    ctx_dir = tmp_path / "context"
    ctx_dir.mkdir(parents=True, exist_ok=True)

    # Create template directory and meta_rules.xml
    template_dir = ctx_dir / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "meta_rules.xml").write_text("<MetaRules></MetaRules>")

    class MockPathManager(BaseMockPathManager):
        def __init__(self, ide=None):
            super().__init__(ctx_dir, ide)

    monkeypatch.setattr(
        "erasmus.file_monitor.get_path_manager", lambda ide=None: MockPathManager(ide)
    )
    monkeypatch.setattr("erasmus.utils.paths.detect_ide_from_env", lambda: None)
    return ctx_dir


@pytest.fixture
def mock_merge(monkeypatch):
    """Mock the merge_rules_file function."""

    def mock_merge_func():
        mock_merge_func.called = True
        mock_merge_func.count += 1
        if getattr(mock_merge_func, "side_effect", None):
            raise mock_merge_func.side_effect

    mock_merge_func.called = False
    mock_merge_func.count = 0
    mock_merge_func.side_effect = None

    monkeypatch.setattr("erasmus.file_monitor._merge_rules_file", mock_merge_func)
    return mock_merge_func


@pytest.fixture
def ctx_files(mock_path_manager):
    """Create temporary context files."""
    arch_file = mock_path_manager / ".ctx.architecture.xml"
    prog_file = mock_path_manager / ".ctx.progress.xml"
    tasks_file = mock_path_manager / ".ctx.tasks.xml"

    arch_file.write_text("<Architecture></Architecture>")
    prog_file.write_text("<Progress></Progress>")
    tasks_file.write_text("<Tasks></Tasks>")

    return arch_file, prog_file, tasks_file


def test_context_file_modified(mock_path_manager, mock_merge, ctx_files):
    """Test that modifying a context file triggers rules merge."""
    arch_file, _, _ = ctx_files

    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count
        # Modify architecture file
        arch_file.write_text("<Architecture><Test/></Architecture>")
        wait_for_event()

        assert mock_merge.count > initial_count, "Rules merge was not triggered"


def test_non_context_file_ignored(mock_path_manager, mock_merge):
    """Test that non-context files are ignored."""
    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count
        # Create a non-context file
        other_file = mock_path_manager / "other.txt"
        other_file.write_text("test")
        wait_for_event()

        assert mock_merge.count == initial_count, "Rules merge was triggered for non-context file"


def test_context_file_debounce(mock_path_manager, mock_merge, ctx_files):
    """Test that rapid context file changes are debounced."""
    arch_file, _, _ = ctx_files

    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count
        # Modify file multiple times rapidly
        for i in range(5):
            arch_file.write_text(f"<Architecture><Test>{i}</Test></Architecture>")
            time.sleep(0.1)  # Small delay between writes

        wait_for_event()

        # Should be debounced to fewer calls than total changes (5) plus initial merge
        final_count = mock_merge.count - initial_count
        assert final_count <= 3, f"Debouncing did not reduce number of merges: {final_count}"


def test_monitor_cleanup(mock_path_manager, mock_merge, ctx_files):
    """Test that the monitor cleans up properly."""
    monitor = ContextFileMonitor()
    monitor.start()
    assert monitor.observer.is_alive()

    monitor.stop()
    assert not monitor.observer.is_alive()


def test_initial_merge(mock_path_manager, mock_merge, ctx_files):
    """Test that initial merge is performed on start."""
    with ContextFileMonitor() as monitor:
        assert mock_merge.called, "Initial rules merge was not performed"


def test_all_context_files_trigger_merge(mock_path_manager, mock_merge, ctx_files):
    """Test that changes to any context file triggers a merge."""
    arch_file, prog_file, tasks_file = ctx_files

    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count

        # Modify each file with enough delay to avoid debouncing
        arch_file.write_text("<Architecture><Test/></Architecture>")
        wait_for_event(2.0)  # Longer wait to ensure debounce period passes

        prog_file.write_text("<Progress><Test/></Progress>")
        wait_for_event(2.0)

        tasks_file.write_text("<Tasks><Test/></Tasks>")
        wait_for_event(2.0)

        # Should have some merges after initial
        assert mock_merge.count > initial_count, "No merges triggered for file changes"


def test_error_handling_missing_dir(monkeypatch, tmp_path):
    """Test handling of missing context directory."""
    nonexistent = tmp_path / "nonexistent"

    class MockPathManager(BaseMockPathManager):
        def __init__(self, ide=None):
            super().__init__(nonexistent, ide)

    monkeypatch.setattr(
        "erasmus.file_monitor.get_path_manager", lambda ide=None: MockPathManager(ide)
    )
    monkeypatch.setattr("erasmus.utils.paths.detect_ide_from_env", lambda: None)

    with ContextFileMonitor() as monitor:
        assert nonexistent.exists(), "Context directory was not created"
        assert nonexistent.is_dir(), "Context path is not a directory"


def test_error_handling_merge_failure(mock_path_manager, mock_merge, ctx_files):
    """Test handling of merge failures."""
    mock_merge.side_effect = Exception("Test merge error")

    with pytest.raises(Exception, match="Test merge error"):
        with ContextFileMonitor():
            pass  # Exception should be raised during start


def test_debug_logging(monkeypatch, mock_path_manager, mock_merge, ctx_files):
    """Test debug logging behavior."""
    arch_file, _, _ = ctx_files
    debug_logs = []

    def mock_debug_log(msg):
        debug_logs.append(str(msg))

    # Enable debug mode and capture debug logs
    monkeypatch.setattr("erasmus.file_monitor.is_debug_enabled", lambda: True)
    monkeypatch.setattr("loguru.logger.debug", mock_debug_log)

    with ContextFileMonitor() as monitor:
        arch_file.write_text("<Architecture><Test/></Architecture>")
        wait_for_event()

        assert any("Received modified event" in log for log in debug_logs), (
            "Debug log not generated for file modification"
        )


def test_monitor_restart(mock_path_manager, mock_merge, ctx_files):
    """Test stopping and restarting the monitor."""
    arch_file, _, _ = ctx_files
    monitor = ContextFileMonitor()

    # First start
    monitor.start()
    initial_count = mock_merge.count
    arch_file.write_text("<Architecture><Test1/></Architecture>")
    wait_for_event()
    monitor.stop()

    # Second start
    monitor.start()  # Should work now that we create a new observer
    arch_file.write_text("<Architecture><Test2/></Architecture>")
    wait_for_event()
    monitor.stop()

    # Should have some merges after initial
    assert mock_merge.count > initial_count, (
        f"Unexpected merge count after restart: {mock_merge.count}"
    )


def test_non_xml_content_handled(mock_path_manager, mock_merge, ctx_files):
    """Test that non-XML content in context files is still processed."""
    arch_file, _, _ = ctx_files

    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count
        # Write non-XML content to architecture file
        arch_file.write_text("This is not XML but should still trigger a merge")
        wait_for_event()

        assert mock_merge.count > initial_count, "Rules merge was not triggered for non-XML content"


def test_only_context_files_trigger_merge(mock_path_manager, mock_merge):
    """Test that only specific context files trigger merges."""
    with ContextFileMonitor() as monitor:
        initial_count = mock_merge.count

        # Create files with similar names but not context files
        other_xml = mock_path_manager / "other.xml"
        other_xml.write_text("<xml>Test</xml>")
        wait_for_event()

        ctx_file = mock_path_manager / "ctx.architecture.xml"  # missing dot
        ctx_file.write_text("<Architecture></Architecture>")
        wait_for_event()

        assert mock_merge.count == initial_count, "Merge triggered for non-context files"

        # Now create a real context file
        arch_file = mock_path_manager / ".ctx.architecture.xml"
        arch_file.write_text("Any content")
        wait_for_event()

        assert mock_merge.count > initial_count, "Merge not triggered for context file"
