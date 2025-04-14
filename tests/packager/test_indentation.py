import pytest
from packager.builder import normalize_indentation


def test_empty_lines():
    """Test handling of empty lines."""
    input_lines = ["def func():", "", "    pass", "", "    return None"]
    expected = ["def func():", "", "    pass", "", "    return None"]
    assert normalize_indentation(input_lines) == expected


def test_top_level_function():
    """Test indentation of top-level function."""
    input_lines = ["def func():", "    pass"]
    expected = ["def func():", "    pass"]
    assert normalize_indentation(input_lines) == expected


def test_nested_function():
    """Test indentation of nested function."""
    input_lines = ["def outer():", "    def inner():", "        pass", "    return inner"]
    expected = ["def outer():", "    def inner():", "        pass", "    return inner"]
    assert normalize_indentation(input_lines) == expected


def test_multiple_nested_functions():
    """Test indentation of multiple nested functions."""
    input_lines = [
        "def level1():",
        "    def level2():",
        "        def level3():",
        "            pass",
        "        return level3",
        "    return level2",
        "return level1",
    ]
    expected = [
        "def level1():",
        "    def level2():",
        "        def level3():",
        "            pass",
        "        return level3",
        "    return level2",
        "return level1",
    ]
    assert normalize_indentation(input_lines) == expected


def test_class_with_methods():
    """Test indentation of class with methods."""
    input_lines = [
        "class MyClass:",
        "    def method1(self):",
        "        pass",
        "",
        "    def method2(self):",
        "        return self.method1()",
    ]
    expected = [
        "class MyClass:",
        "    def method1(self):",
        "        pass",
        "",
        "    def method2(self):",
        "        return self.method1()",
    ]
    assert normalize_indentation(input_lines) == expected


def test_nested_class():
    """Test indentation of nested class."""
    input_lines = [
        "class Outer:",
        "    class Inner:",
        "        def method(self):",
        "            pass",
        "    def outer_method(self):",
        "        return self.Inner()",
    ]
    expected = [
        "class Outer:",
        "    class Inner:",
        "        def method(self):",
        "            pass",
        "    def outer_method(self):",
        "        return self.Inner()",
    ]
    assert normalize_indentation(input_lines) == expected


def test_control_structures():
    """Test indentation of control structures."""
    input_lines = [
        "def func():",
        "    if True:",
        "        for i in range(10):",
        "            while i > 0:",
        "                try:",
        "                    pass",
        "                except:",
        "                    pass",
        "                finally:",
        "                    pass",
        "    return None",
    ]
    expected = [
        "def func():",
        "    if True:",
        "        for i in range(10):",
        "            while i > 0:",
        "                try:",
        "                    pass",
        "                except:",
        "                    pass",
        "                finally:",
        "                    pass",
        "    return None",
    ]
    assert normalize_indentation(input_lines) == expected


def test_docstrings():
    """Test indentation of docstrings."""
    input_lines = [
        "def func():",
        '    """This is a docstring.',
        "    It spans multiple lines.",
        '    """',
        "    pass",
    ]
    expected = [
        "def func():",
        '    """This is a docstring.',
        "    It spans multiple lines.",
        '    """',
        "    pass",
    ]
    assert normalize_indentation(input_lines) == expected


def test_comments():
    """Test indentation of comments."""
    input_lines = [
        "# Top level comment",
        "def func():",
        "    # Function level comment",
        "    def inner():",
        "        # Inner function comment",
        "        pass",
    ]
    expected = [
        "# Top level comment",
        "def func():",
        "    # Function level comment",
        "    def inner():",
        "        # Inner function comment",
        "        pass",
    ]
    assert normalize_indentation(input_lines) == expected


def test_mixed_content():
    """Test indentation of mixed content (functions, classes, control structures, comments, docstrings)."""
    input_lines = [
        "# Module level comment",
        "",
        "def outer():",
        '    """Outer function docstring."""',
        "    class Inner:",
        "        def method(self):",
        "            if True:",
        "                # Inner comment",
        "                for i in range(10):",
        "                    while i > 0:",
        "                        try:",
        "                            pass",
        "                        except:",
        "                            pass",
        "    return Inner()",
    ]
    expected = [
        "# Module level comment",
        "",
        "def outer():",
        '    """Outer function docstring."""',
        "    class Inner:",
        "        def method(self):",
        "            if True:",
        "                # Inner comment",
        "                for i in range(10):",
        "                    while i > 0:",
        "                        try:",
        "                            pass",
        "                        except:",
        "                            pass",
        "    return Inner()",
    ]
    assert normalize_indentation(input_lines) == expected


def test_invalid_indentation():
    """Test handling of invalid indentation."""
    input_lines = [
        "def func():",
        "pass  # Missing indentation",
        "",
        "def another_func():",
        "    return None",  # Correct indentation
    ]
    expected = [
        "def func():",
        "    pass  # Fixed indentation",
        "",
        "def another_func():",
        "    return None",
    ]
    assert normalize_indentation(input_lines) == expected


def test_mixed_spaces_and_tabs():
    """Test handling of mixed spaces and tabs."""
    input_lines = [
        "def func():",
        "\tpass",  # Tab indentation
        "    return None",  # Space indentation
    ]
    expected = [
        "def func():",
        "    pass",  # Normalized to spaces
        "    return None",
    ]
    assert normalize_indentation(input_lines) == expected
