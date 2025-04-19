import re
from pathlib import Path
from typing import Set, List


def inline_module(file: Path, inlined_modules: Set[str]) -> str:
    """
    Read a Python file, remove imports for inlined modules, strip __all__, __version__, docstrings, and any if __name__ == "__main__": block and everything after it. Return cleaned code.
    """
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    code = content
    for mod in inlined_modules:
        code = re.sub(
            rf"^\s*import\s+{re.escape(mod)}(\.[\w\.]+)?(\s+as\s+\w+)?\s*$",
            "",
            code,
            flags=re.MULTILINE,
        )
        code = re.sub(
            rf"^\s*from\s+{re.escape(mod)}(\.[\w\.]+)?\s+import.*$",
            "",
            code,
            flags=re.MULTILINE,
        )
    # Remove __all__ assignment and header docstring if present (robust, anywhere in file)
    code = re.sub(r"(?s)__all__\s*=\s*\[.*?\]", "", code)
    code = re.sub(r'(?s)__version__\s*=\s*["\'][^"\']*["\']', "", code)
    code = re.sub(r'(?s)^\s*""".*?"""\s*', "", code)
    # Remove any if __name__ == "__main__": block and everything after it
    code = re.split(r'^if __name__\s*==\s*["\']__main__["\']:\s*$', code, flags=re.MULTILINE)[0]
    return code


def get_public_symbols(code: str) -> List[str]:
    """
    Extract public function and class names from code.
    """
    public_symbols = []
    for line in code.splitlines():
        match = re.match(r"^def ([a-zA-Z_][a-zA-Z0-9_]*)\(", line)
        if match and not match.group(1).startswith("_"):
            public_symbols.append(match.group(1))
        match = re.match(r"^class ([a-zA-Z_][a-zA-Z0-9_]*)\(", line)
        if match and not match.group(1).startswith("_"):
            public_symbols.append(match.group(1))
    return public_symbols
