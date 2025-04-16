import asyncio
import time
from pathlib import Path

import pytest
import pytest_asyncio

from erasmus.sync.file_sync import FileSynchronizer

SYNC_ALL_THRESHOLD = 2.0
CONCURRENT_SYNC_THRESHOLD = 3.0
CONCURRENT_SYNC_PER_FILE_THRESHOLD = 0.5
STATUS_CHECK_THRESHOLD = 0.5

@pytest_asyncio.fixture
async def bench_env(tmp_path) -> tuple[Path, Path, FileSynchronizer]:
    """Create a test environment with workspace and rules directories."""
    workspace = tmp_path / "workspace"
    rules_dir = workspace / ".cursorrules"
    workspace.mkdir()
    # Add required context files
    erasmus_dir = workspace / ".erasmus"
    erasmus_dir.mkdir(exist_ok=True)
    (erasmus_dir / ".architecture.md").write_text("# architecture\nTest content")
    (erasmus_dir / ".progress.md").write_text("# progress\nTest content")
    (erasmus_dir / ".tasks.md").write_text("# tasks\nTest content")

    # Create test files
    for filename in FileSynchronizer.TRACKED_FILES:
        file_path = workspace / filename
        file_path.write_text(f"Test content for {filename}")

    # Create synchronizer
    syncer = FileSynchronizer(workspace, rules_dir)
    await syncer.start()

    yield workspace, rules_dir, syncer

    # Cleanup
    await syncer.stop()


async def measure_operation_time(operation) -> float:
    """Measure the time taken for an async operation."""
    start_time = time.perf_counter()
    await operation
    end_time = time.perf_counter()
    return end_time - start_time


@pytest.mark.asyncio
async def test_sync_single_file_performance(bench_env):
    """Benchmark synchronizing a single file."""
    workspace, rules_dir, syncer = bench_env

    # Measure initial sync time
    sync_time = await measure_operation_time(
        syncer.sync_file(".erasmus/.architecture.md"),
    )

    # Measure sync time after modification
    (workspace / ".erasmus/.architecture.md").write_text("Modified content")
    modified_sync_time = await measure_operation_time(
        syncer.sync_file(".erasmus/.architecture.md"),
    )

    # Print benchmark results
    print("\nSingle File Sync Performance:")
    print(f"Initial sync time: {sync_time:.4f}s")
    print(f"Modified sync time: {modified_sync_time:.4f}s")

    # Verify reasonable performance
    assert sync_time < 1.0, "Initial sync took too long"
    assert modified_sync_time < 1.0, "Modified sync took too long"


@pytest.mark.asyncio
async def test_sync_all_files_performance(bench_env):
    """Benchmark synchronizing all files."""
    workspace, rules_dir, syncer = bench_env

    # Measure initial sync all time
    sync_time = await measure_operation_time(syncer.sync_all())

    # Modify all files
    for filename in FileSynchronizer.TRACKED_FILES:
        (workspace / filename).write_text(f"Modified content for {filename}")

    # Measure sync time after modification
    modified_sync_time = await measure_operation_time(syncer.sync_all())

    # Print benchmark results
    print("\nAll Files Sync Performance:")
    print(f"Initial sync time: {sync_time:.4f}s")
    print(f"Modified sync time: {modified_sync_time:.4f}s")
    print(f"Average time per file: {modified_sync_time / len(FileSynchronizer.TRACKED_FILES):.4f}s")

    # Verify reasonable performance
    assert sync_time < SYNC_ALL_THRESHOLD, "Initial sync_all took too long"
    assert modified_sync_time < SYNC_ALL_THRESHOLD, "Modified sync_all took too long"


@pytest.mark.asyncio
async def test_concurrent_sync_performance(bench_env):
    """Benchmark concurrent file synchronization."""
    workspace, rules_dir, syncer = bench_env

    # Use tracked files
    test_files = list(FileSynchronizer.TRACKED_FILES.keys())

    # Modify all files with new content
    for filename in test_files:
        file_path = workspace / filename
        file_path.write_text(f"Modified content for concurrent test in {filename}")

    # Measure concurrent sync time
    start_time = time.perf_counter()
    tasks = [syncer.sync_file(filename) for filename in test_files]
    await asyncio.gather(*tasks)
    end_time = time.perf_counter()
    concurrent_sync_time = end_time - start_time

    # Print benchmark results
    print("\nConcurrent Sync Performance:")
    print(f"Total time for {len(test_files)} files: {concurrent_sync_time:.4f}s")
    print(f"Average time per file: {concurrent_sync_time / len(test_files):.4f}s")

    # Verify reasonable performance
    assert concurrent_sync_time < CONCURRENT_SYNC_THRESHOLD, "Concurrent sync took too long"
    assert concurrent_sync_time / len(test_files) < CONCURRENT_SYNC_PER_FILE_THRESHOLD, (
        "Average concurrent sync time per file too high"
    )


@pytest.mark.asyncio
async def test_status_check_performance(bench_env):
    """Benchmark status check operations."""
    workspace, rules_dir, syncer = bench_env

    # Initial sync
    await syncer.sync_all()

    # Measure status check time
    status_time = await measure_operation_time(syncer.get_sync_status())

    # Print benchmark results
    print("\nStatus Check Performance:")
    print(f"Status check time: {status_time:.4f}s")

    # Verify reasonable performance
    assert status_time < STATUS_CHECK_THRESHOLD, "Status check took too long"
