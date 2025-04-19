"""Test script to inspect import types."""

import enum
from enum import Enum
import importlib
from pathlib import Path
from typing import List


def inspect_import(module_name: str, item_name: str = None):
    """Inspect an import and print its type information."""
    print(f"\nInspecting: {module_name}" + (f".{item_name}" if item_name else ""))

    # Test direct module import
    module = __import__(module_name)
    print(f"Type of {module_name}: {type(module)}")
    print(f"Module.__file__: {getattr(module, '__file__', 'N/A')}")

    # If we have a specific item, inspect it too
    if item_name:
        item = getattr(module, item_name)
        print(f"Type of {module_name}.{item_name}: {type(item)}")
        print(f"MRO: {getattr(item, '__mro__', 'N/A')}")


# Test cases
print("=== Testing Standard Library Imports ===")

inspect_import("enum")
inspect_import("enum", "Enum")

inspect_import("pathlib")
inspect_import("pathlib", "Path")

inspect_import("typing")
inspect_import("typing", "List")

# Also test the imports directly
print("\n=== Testing Direct Variable Access ===")
print(f"Type of imported Enum: {type(Enum)}")
print(f"Type of imported Path: {type(Path)}")
print(f"Type of imported List: {type(List)}")

if __name__ == "__main__":
    print("\nTest complete.")
