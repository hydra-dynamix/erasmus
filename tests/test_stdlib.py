"""Tests for the stdlib module."""

import pytest
from typing import Set
from packager.stdlib import is_stdlib_module, filter_stdlib_imports


@pytest.fixture
def sample_imports() -> Set[str]:
    """Sample imports for testing."""
    return {
        "os",  # stdlib
        "sys",  # stdlib
        "pathlib",  # stdlib
        "numpy",  # third-party
        "pandas",  # third-party
        "json",  # stdlib
        "collections",  # stdlib
        "requests",  # third-party
    }


def test_is_stdlib_module_basic():
    """Test basic stdlib module detection."""
    assert is_stdlib_module("os")
    assert is_stdlib_module("sys")
    assert is_stdlib_module("json")
    assert not is_stdlib_module("numpy")
    assert not is_stdlib_module("pandas")
    assert not is_stdlib_module("requests")


def test_is_stdlib_module_submodules():
    """Test stdlib submodule detection."""
    assert is_stdlib_module("os.path")
    assert is_stdlib_module("json.decoder")
    assert is_stdlib_module("xml.etree")
    assert not is_stdlib_module("numpy.array")
    assert not is_stdlib_module("pandas.DataFrame")


def test_is_stdlib_module_case_sensitivity():
    """Test case sensitivity in module names."""
    assert is_stdlib_module("JSON") == is_stdlib_module("json")
    assert is_stdlib_module("Os") == is_stdlib_module("os")
    assert is_stdlib_module("SYS") == is_stdlib_module("sys")


def test_is_stdlib_module_nonexistent():
    """Test handling of nonexistent modules."""
    assert not is_stdlib_module("nonexistent_module")
    assert not is_stdlib_module("")
    assert not is_stdlib_module("fake_module")


def test_filter_stdlib_imports(sample_imports):
    """Test filtering of stdlib imports."""
    third_party = filter_stdlib_imports(sample_imports)
    assert third_party == {"numpy", "pandas", "requests"}
    assert "os" not in third_party
    assert "sys" not in third_party
    assert "json" not in third_party


def test_filter_stdlib_imports_empty():
    """Test filtering empty import set."""
    assert filter_stdlib_imports(set()) == set()


def test_filter_stdlib_imports_all_stdlib():
    """Test filtering when all imports are stdlib."""
    stdlib_only = {"os", "sys", "json", "pathlib"}
    assert filter_stdlib_imports(stdlib_only) == set()


def test_filter_stdlib_imports_all_third_party():
    """Test filtering when all imports are third-party."""
    third_party_only = {"numpy", "pandas", "requests", "django"}
    filtered = filter_stdlib_imports(third_party_only)
    assert filtered == third_party_only


def test_filter_stdlib_imports_with_submodules():
    """Test filtering with submodules."""
    imports = {
        "os.path",
        "json.decoder",
        "numpy.array",
        "pandas.DataFrame",
    }
    filtered = filter_stdlib_imports(imports)
    assert filtered == {"numpy.array", "pandas.DataFrame"}
    assert "os.path" not in filtered
    assert "json.decoder" not in filtered


def test_stdlib_version_compatibility():
    """Test compatibility with different Python versions."""
    # These modules should be stdlib in all supported Python versions
    common_stdlib = {
        "abc",
        "argparse",
        "asyncio",
        "base64",
        "collections",
        "datetime",
        "decimal",
        "functools",
        "itertools",
        "math",
        "random",
        "re",
        "string",
        "time",
        "typing",
        "uuid",
    }

    for module in common_stdlib:
        assert is_stdlib_module(module), f"{module} should be recognized as stdlib"

    filtered = filter_stdlib_imports(common_stdlib)
    assert not filtered, "All common stdlib modules should be filtered out"
