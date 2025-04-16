import os
import pytest
import pytest_asyncio
import tracemalloc
from pathlib import Path
from erasmus.sync.file_sync import FileSynchronizer
from erasmus.utils.paths import PathManager


@pytest_asyncio.fixture
async def memory_test_env(tmp_path) -> tuple[Path, FileSynchronizer]:
    """Create a test environment with workspace and rules directories."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create test files with varying sizes
    file_sizes = {
        "small.txt": 1024,  # 1 KB
        "medium.txt": 1024 * 1024,  # 1 MB
        "large.txt": 1024 * 1024 * 10,  # 10 MB
    }

    for filename, size in file_sizes.items():
        file_path = workspace / filename
        file_path.write_text("x" * size)

    # Create PathManager and initialize rules file
    path_manager = PathManager(project_root=workspace)
    path_manager.rules_file = workspace / ".cursorrules" / "rules.json"

    # Create rules file with tracked files
    os.makedirs(os.path.dirname(str(path_manager.rules_file)), exist_ok=True)
    with open(path_manager.rules_file, "w") as f:
        f.write(
            "{" + ", ".join([f'"{filename}": "test_component"' for filename in file_sizes]) + "}"
        )

    # Create synchronizer
    syncer = FileSynchronizer(path_manager)
    await syncer.start()

    yield workspace, syncer

    # Cleanup
    await syncer.stop()


@pytest.mark.asyncio
async def test_initial_sync_memory(memory_test_env):
    """Test memory usage during initial file synchronization."""
    workspace, syncer = memory_test_env

    # Start memory tracing
    tracemalloc.start()

    # Perform initial sync
    await syncer.sync_all()

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Print memory usage
    print("\nInitial Sync Memory Usage:")
    print(f"Current memory usage: {current / 10**6:.2f} MB")
    print(f"Peak memory usage: {peak / 10**6:.2f} MB")

    # Assert memory usage is within reasonable limits
    assert peak < 50 * 10**6, f"Memory usage spike too high: {peak / 10**6} MB"


@pytest.mark.asyncio
async def test_repeated_sync_memory(memory_test_env):
    """Test memory usage during repeated file synchronizations."""
    workspace, syncer = memory_test_env

    # Initial sync
    await syncer.sync_all()

    # Modify files
    for filename in os.listdir(workspace):
        if filename != ".cursorrules":
            file_path = workspace / filename
            file_path.write_text(file_path.read_text() + " Modified")

    # Start memory tracing
    tracemalloc.start()

    # Sync again
    await syncer.sync_all()

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Print memory usage
    print("\nRepeated Sync Memory Usage:")
    print(f"Current memory usage: {current / 10**6:.2f} MB")
    print(f"Peak memory usage: {peak / 10**6:.2f} MB")

    # Assert memory usage is within reasonable limits
    assert peak < 50 * 10**6, f"Memory usage spike too high: {peak / 10**6} MB"


@pytest.mark.asyncio
async def test_status_check_memory(memory_test_env):
    """Test memory usage during sync status checks."""
    workspace, syncer = memory_test_env

    # Initial sync
    await syncer.sync_all()

    # Start memory tracing
    tracemalloc.start()

    # Multiple status checks
    for _ in range(10):
        status = syncer.get_status()

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Print memory usage
    print("\nStatus Check Memory Usage:")
    print(f"Current memory usage: {current / 10**6:.2f} MB")
    print(f"Peak memory usage: {peak / 10**6:.2f} MB")

    # Assert memory usage is within reasonable limits
    assert peak < 50 * 10**6, f"Memory usage spike too high: {peak / 10**6} MB"


@pytest.mark.asyncio
async def test_large_number_of_files_memory(tmp_path):
    """Test memory usage when handling a large number of files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create many small files
    num_files = 1000
    for i in range(num_files):
        file_path = workspace / f"file_{i}.txt"
        file_path.write_text(f"Content for file {i}")

    # Create PathManager and initialize rules file
    path_manager = PathManager(project_root=workspace)
    path_manager.rules_file = workspace / ".cursorrules" / "rules.json"

    # Create rules file with tracked files
    os.makedirs(os.path.dirname(str(path_manager.rules_file)), exist_ok=True)
    with open(path_manager.rules_file, "w") as f:
        f.write(
            "{" + ", ".join([f'"file_{i}.txt": "test_component"' for i in range(num_files)]) + "}"
        )

    # Create synchronizer
    syncer = FileSynchronizer(path_manager)
    await syncer.start()

    # Start memory tracing
    tracemalloc.start()

    # Sync all files
    await syncer.sync_all()

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Print memory usage
    print("\nLarge Number of Files Sync Memory Usage:")
    print(f"Current memory usage: {current / 10**6:.2f} MB")
    print(f"Peak memory usage: {peak / 10**6:.2f} MB")

    # Assert memory usage is within reasonable limits
    assert peak < 50 * 10**6, f"Memory usage spike too high: {peak / 10**6} MB"

    # Cleanup
    await syncer.stop()
