"""Tests for the tree-sitter based Python parser."""

import pytest
from packager.tree_sitter_parser import parse_imports, extract_code_body, ImportSet


def test_parse_imports_basic():
    """Test basic import parsing."""
    code = """
import os
import sys
from pathlib import Path
from typing import List, Dict
"""
    import_set, errors = parse_imports(code)
    assert not errors
    assert 'os' in import_set.stdlib
    assert 'sys' in import_set.stdlib
    assert 'pathlib' in import_set.stdlib
    assert 'typing' in import_set.stdlib


def test_parse_imports_local():
    """Test parsing local imports."""
    code = """
from . import utils
from .models import User
from erasmus.core import Context
"""
    import_set, errors = parse_imports(code)
    assert not errors
    assert 'utils' in import_set.local
    assert 'models' in import_set.local
    assert 'erasmus.core' in import_set.local


def test_parse_imports_third_party():
    """Test parsing third-party imports."""
    code = """
import numpy as np
from pandas import DataFrame
import requests
"""
    import_set, errors = parse_imports(code)
    assert not errors
    assert 'numpy' in import_set.third_party
    assert 'pandas' in import_set.third_party
    assert 'requests' in import_set.third_party


def test_extract_code_body():
    """Test code body extraction and normalization."""
    code = """
def process_data(items):
    \"\"\"Process a list of items.\"\"\"
    processed = []
    for item in items:
        # Process each item
        result = (item
                 .strip()
                 .lower())
        processed.append(result)
    
    return processed

def log_error(message):
    console_logger.error(
        "Error occurred: "
        f"{message}"
    )
"""
    normalized = extract_code_body(code)
    assert 'def process_data(items):' in normalized
    assert 'def log_error(message):' in normalized
    assert '    console_logger.error(' in normalized
    assert '        "Error occurred: "' in normalized
    assert '        f"{message}"' in normalized
    assert '    )' in normalized
