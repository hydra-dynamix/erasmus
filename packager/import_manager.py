import importlib.util
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, Any, Deque
from collections import deque
from dotenv import load_dotenv

from utils.rich_console import get_console_logger

load_dotenv()

console = get_console_logger()
verbose = os.getenv("ERASMUS_DEBUG", "false").lower() in ("true", "1", "t")

class ImportManager:
    """Handles the parsing, merging, and generation of Python import statements."""
    
    # Map of module import names to package names
    PACKAGE_NAME_MAP = {
        "dotenv": "python-dotenv",
        "yaml": "pyyaml",
        "bs4": "beautifulsoup4",
        "PIL": "pillow",
        "sklearn": "scikit-learn",
        "cv2": "opencv-python",
        "matplotlib.pyplot": "matplotlib",
        "numpy": "numpy",
        "pandas": "pandas",
        "flask": "flask",
        "requests": "requests",
        "django": "django",
        "sqlalchemy": "sqlalchemy",
        "pytest": "pytest",
        "tornado": "tornado",
        "aiohttp": "aiohttp",
        "fastapi": "fastapi",
    }
    
    # Standard library modules (Python 3.8+) - this is not exhaustive but covers common ones
    STDLIB_MODULES = {
        "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins", "calendar",
        "cmath", "collections", "concurrent", "contextlib", "copy", "csv", "dataclasses",
        "datetime", "decimal", "difflib", "email", "enum", "errno", "fnmatch", "fractions",
        "functools", "gc", "getopt", "getpass", "glob", "gzip", "hashlib", "heapq",
        "hmac", "html", "http", "importlib", "inspect", "io", "itertools", "json",
        "logging", "math", "multiprocessing", "operator", "os", "pathlib", "pickle",
        "pprint", "queue", "random", "re", "shutil", "signal", "socket", "sqlite3",
        "statistics", "string", "struct", "subprocess", "sys", "tempfile", "textwrap",
        "threading", "time", "timeit", "tkinter", "traceback", "typing", "types", "typing-extensions", "unittest",
        "urllib", "uuid", "warnings", "weakref", "xml", "zipfile", "zlib"
    }
    IMPORT_LINES = [
        "import",
        "from"
    ]
    
    def __init__(self, target_path: Optional[Path] = None):
        # Format: {module_name: {symbols}}
        self.from_imports: Dict[str, Set[str]] = {}
        # Format: {module_name}
        self.direct_imports: Set[str] = set()
        # Import object for sorting
        self.import_object = {}
        # Target package name (for local import detection)
        self.target_package = target_path.name if target_path else None
        
        
    def _add_to_import_object(self, line: str) -> None:
        """Add an import line to the import object.
        
        Args:
            line: The import line to process
        """
        def create_nested_dict(parts: List[str], value: Any) -> Dict:
            """Recursively create a nested dictionary from parts.
            
            Args:
                parts: List of module name parts
                value: Value to store at the deepest level
                
            Returns:
                Nested dictionary structure
            """
            if not parts:
                return value
            return {parts[0]: create_nested_dict(parts[1:], value)}

        def merge_dicts(d1: Dict, d2: Dict) -> Dict:
            """Merge two dictionaries recursively.
            
            Args:
                d1: First dictionary
                d2: Second dictionary
                
            Returns:
                Merged dictionary
            """
            result = d1.copy()
            for key, value in d2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                elif key in result and isinstance(result[key], set) and isinstance(value, set):
                    result[key].update(value)
                else:
                    result[key] = value
            return result

        try:
            if verbose:
                console.print(f"[dim]Processing import line: {line}[/]")
            if line.startswith("from "):
                # Handle "from x import y" format
                parts = line.split(" import ")
                if len(parts) != 2:
                    console.print(f"[warning]Invalid from import format: {line}[/]")
                    return
                module_part = parts[0].replace("from ", "").strip()
                imports_part = parts[1].strip()
                
                # Clean up imports (remove parentheses, split by commas)
                imports_part = imports_part.replace("(", "").replace(")", "").strip()
                imported_items = {item.strip() for item in imports_part.split(",") if item.strip()}
                
                # Create nested structure for the module
                module_parts = module_part.split(".")
                nested_dict = create_nested_dict(module_parts, imported_items)
                self.import_object = merge_dicts(self.import_object, nested_dict)
                # console.print(f"[dim]Added from import: {module_part} -> {imported_items}[/]")
                # console.print(f"[dim]Current import object: {self.import_object}[/]")
                
            elif line.startswith("import "):
                # Handle "import x" format
                module_part = line.replace("import ", "").strip()
                # Handle multiple imports on one line
                imported_items = set()
                for module_entry in module_part.split(","):
                    module_entry = module_entry.strip()
                    if not module_entry:
                        continue
                        
                    # Handle aliases (import x as y)
                    if ' as ' in module_entry:
                        module_name = module_entry.split(' as ')[0].strip()
                        alias = module_entry.split(' as ')[1].strip()
                        # Store the module name and alias
                        imported_items.add(f"{module_name} as {alias}")
                    else:
                        module_name = module_entry
                        # Store just the module name
                        imported_items.add(module_name)
                
                # Special handling for typing imports
                typing_imports = {item for item in imported_items if item in {'Any', 'Dict', 'List', 'Set', 'Tuple', 'Union', 'Optional', 'Callable', 'Pattern', 'NamedTuple', 'UnionType', 'NoneType'}}
                if typing_imports:
                    if 'typing' not in self.import_object:
                        self.import_object['typing'] = set()
                    self.import_object['typing'].update(typing_imports)
                    imported_items -= typing_imports
                
                # Handle remaining imports
                if imported_items:
                    # Group imports by their root module
                    for item in imported_items:
                        module_parts = item.split('.')
                        if len(module_parts) > 1:
                            # This is a submodule import (e.g., importlib.metadata)
                            root_module = module_parts[0]
                            if root_module not in self.import_object:
                                self.import_object[root_module] = set()
                            if isinstance(self.import_object[root_module], dict):
                                self.import_object[root_module][item] = set()
                            else:
                                self.import_object[root_module].add(item)
                        else:
                            # This is a direct module import
                            if item not in self.import_object:
                                self.import_object[item] = set()
                            if isinstance(self.import_object[item], dict):
                                self.import_object[item][item] = set()
                            else:
                                self.import_object[item].add(item)
                
                # console.print(f"[dim]Added imports: {imported_items}[/]")
                # console.print(f"[dim]Current import object: {self.import_object}[/]")
                    
        except Exception as e:
            console.print(f"[warning]Error processing import line: {line} - {e}")
    
    def add_import_line(self, line: str) -> None:
        """Parse and add an import line to the appropriate collection."""
        # Skip empty lines
        if not line or line.isspace():
            return
            
        # Remove comments from the line
        if '#' in line:
            line = line.split('#', 1)[0].strip()
        
        line = line.strip()
        if not line:  # Skip if line is empty after stripping
            return
        
        if line.startswith("from ") and " import " in line:
            # Handle "from x import y" format
            try:
                module_part, symbols_part = line.split(" import ", 1)
                module_name = module_part.replace("from ", "").strip()
                
                # Handle multi-line imports and imports with parentheses
                symbols_part = symbols_part.replace("(", "").replace(")", "").strip()
                
                # Clean up symbols and remove duplicates
                symbols = []
                for symbol in symbols_part.split(","):
                    # Clean each symbol
                    symbol = symbol.strip()
                    # Skip empty symbols
                    if not symbol:
                        continue
                    # Handle 'as' aliases
                    if ' as ' in symbol:
                        symbol = symbol.split(' as ')[0].strip()
                    # Add to list if not already present
                    if symbol not in symbols:
                        symbols.append(symbol)
                
                if module_name not in self.from_imports:
                    self.from_imports[module_name] = set()
                self.from_imports[module_name].update(symbols)
            except Exception as e:
                console.print(f"[warning]Error parsing 'from' import: {line} - {e}")
        
        elif line.startswith("import "):
            # Handle "import x" format
            modules = line.replace("import ", "").strip()
            
            # Handle multiple imports on a single line
            for module_entry in modules.split(","):
                module_entry = module_entry.strip()
                if not module_entry:
                    continue
                    
                # Handle aliases (import x as y)
                if ' as ' in module_entry:
                    module_name = module_entry.split(' as ')[0].strip()
                    # Store the full entry including the alias
                    self.direct_imports.add(module_entry)
                else:
                    self.direct_imports.add(module_entry)
    
    def is_local_import(self, module_name: str) -> bool:
        """Check if a module import is a local import."""
        if not module_name:
            return False
            
        return any([
            module_name.startswith("."),  # Relative import
            self.target_package and module_name == self.target_package,  # Direct import of target package
            self.target_package and module_name.startswith(f"{self.target_package}.")  # Import from target package
        ])
    
    def is_local_import_line(self, import_line: str) -> bool:
        """Check if an import line is for a local module."""
        if import_line.startswith("from "):
            try:
                module = import_line.split(" import ")[0].replace("from ", "").strip()
                return self.is_local_import(module)
            except IndexError:
                return False
        elif import_line.startswith("import "):
            modules = import_line.replace("import ", "").strip().split(",")
            return any(self.is_local_import(m.strip().split(" as ")[0] if " as " in m else m.strip()) for m in modules)
        return False
    
    def filter_local_imports(self, code: str) -> str:
        """Remove local imports from the code."""
        lines = code.splitlines()
        cleaned_lines = []
        
        # Skip mode for multiline imports
        skip_mode = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                cleaned_lines.append(line)
                continue
            
            # Handle multi-line imports
            if skip_mode:
                if ")" in stripped:
                    skip_mode = False
                continue
            
            # Check if this is a local import
            if stripped.startswith("from ") and " import " in stripped:
                module_part = stripped.split(" import ")[0].replace("from ", "").strip()
                
                # Check if it's a local import
                if self.is_local_import(module_part):
                    if "(" in stripped and ")" not in stripped:
                        skip_mode = True
                    continue
            
            # Check direct imports of local modules
            elif stripped.startswith("import "):
                modules = stripped.replace("import ", "").strip()
                
                # Check each module in case of multiple imports on one line
                skip_this_line = False
                for module in modules.split(","):
                    module = module.strip()
                    if " as " in module:
                        module = module.split(" as ")[0].strip()
                    
                    if self.is_local_import(module):
                        if "(" in stripped and ")" not in stripped:
                            skip_mode = True
                        skip_this_line = True
                        break
                
                if skip_this_line:
                    continue
            
            cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)
    def extract_imports_from_code(self, code: str, add_to_manager: bool = True) -> str:
        """Extract all imports from code and optionally add them to the import manager.
        
        Args:
            code: The code to process
            add_to_manager: Whether to add the imports to this ImportManager instance
            
        Returns:
            Code with local imports removed and third-party imports processed
        """
        lines = code.splitlines()
        extracted_imports = []
        
        # Track multi-line imports
        is_multi_line_import = False
        multi_line_import = []
        cleaned_code = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_code += line + "\n"
                continue
            if is_multi_line_import:
                if ")" in stripped:
                    is_multi_line_import = False
                    last_line = line.split(")")[0]
                    if last_line.strip():
                        multi_line_import.append(last_line)
                    extracted_imports.append(" ".join(multi_line_import))
                    multi_line_import = []
                    continue
                else:
                    multi_line_import.append(line.strip())
                    continue
            if any(stripped.startswith(import_line) for import_line in self.IMPORT_LINES):
                if "(" in stripped and ")" not in stripped:
                    is_multi_line_import = True
                    multi_line_import.append(line.split("(")[0].strip())
                    continue
                else:
                    if "#" in stripped:
                        line = line.split("#", 1)[0]
                    if stripped:
                        extracted_imports.append(line)
                        continue

            cleaned_code += line + "\n"

        for import_line in extracted_imports:

            self.add_import_line(import_line)
            self._add_to_import_object(import_line)
        return cleaned_code, extracted_imports

    def generate_import_statements(self, exclude_package: Optional[str] = None) -> List[str]:
        """Generate consolidated import statements from the stored imports.
        
        Args:
            exclude_package: Optional package name to exclude from the generated imports
            
        Returns:
            List of import statements
        """
        imports = []
        
        # Process "from x import y" imports
        for module, symbols in sorted(self.from_imports.items()):
            # Skip excluded package
            if exclude_package and (module == exclude_package or module.startswith(f"{exclude_package}.")):
                continue
                
            symbols_str = ", ".join(sorted(symbols))
            imports.append(f"from {module} import {symbols_str}")
        
        # Process "import x" imports
        # Group modules without aliases for cleaner output
        simple_modules = []
        aliased_modules = []
        
        for module in sorted(self.direct_imports):
            # Skip excluded package
            module_name = module.split(" as ")[0].strip() if " as " in module else module
            if exclude_package and (module_name == exclude_package or module_name.startswith(f"{exclude_package}.")):
                continue
                
            if ' as ' in module:
                # Keep aliased imports separate
                aliased_modules.append(module)
            else:
                simple_modules.append(module)
        
        # Add simple imports grouped together
        if simple_modules:
            imports.append(f"import {', '.join(simple_modules)}")
        
        # Add aliased imports separately
        for module in aliased_modules:
            imports.append(f"import {module}")
        
        return imports
    
    def _reconstruct_imports(self, import_dict: Dict, current_path: List[str] = None) -> List[str]:
        """Reconstruct import statements from the nested dictionary structure.
        
        Args:
            import_dict: The nested dictionary of imports
            current_path: Current module path being processed
            
        Returns:
            List of reconstructed import statements
        """
        if current_path is None:
            current_path = []
            
        import_statements = []
        console.print(f"[dim]Reconstructing imports for path: {current_path}[/]")
        console.print(f"[dim]Import dict: {import_dict}[/]")
        
        # Group imports by type
        typing_imports = set()
        stdlib_imports = {}  # Dict to group stdlib imports by module
        third_party_imports = {}  # Dict to group third-party imports by module
        
        # Standard library module mappings
        stdlib_mappings = {
            'BaseModel': 'pydantic',
            'ConfigDict': 'pydantic',
            'Enum': 'enum',
            'Field': 'pydantic',
            'PIPE': 'subprocess',
            'Path': 'pathlib',
            'TextIOWrapper': 'io',
            'UsageError': 'click',
        }
        
        for module, value in import_dict.items():
            # Skip local imports (those starting with . or matching target package)
            if module.startswith('.') or (self.target_package and module == self.target_package):
                console.print(f"[dim]Skipping local module: {module}[/]")
                continue
                
            if isinstance(value, dict):
                # Recursively process submodules
                new_path = current_path + [module]
                sub_imports = self._reconstruct_imports(value, new_path)
                import_statements.extend(sub_imports)
            elif isinstance(value, set):
                # We've reached a leaf node with imported items
                if current_path:
                    module_path = ".".join(current_path)
                    # Skip if this is a local import
                    if module_path.startswith('.') or (self.target_package and module_path.startswith(self.target_package)):
                        console.print(f"[dim]Skipping local path: {module_path}[/]")
                        continue
                        
                    if value:
                        # For direct imports, use the stored import line
                        if all(' as ' in item for item in value):
                            # Handle aliased imports
                            for item in sorted(value):
                                import_statements.append(f"import {item}")
                            console.print(f"[dim]Added aliased imports for {module_path}: {value}[/]")
                        else:
                            # Handle "from" imports
                            imports_str = ", ".join(sorted(value))
                            import_statements.append(f"from {module_path} import {imports_str}")
                            console.print(f"[dim]Added from import: from {module_path} import {imports_str}[/]")
                else:
                    # Handle direct imports
                    for item in sorted(value):
                        # Check if this is a typing import
                        if item in {'Any', 'Dict', 'List', 'Set', 'Tuple', 'Union', 'Optional', 'Callable', 'Pattern', 'NamedTuple', 'UnionType', 'NoneType'}:
                            typing_imports.add(item)
                        # Check if this is a known stdlib import
                        elif item in stdlib_mappings:
                            module_name = stdlib_mappings[item]
                            if module_name not in stdlib_imports:
                                stdlib_imports[module_name] = set()
                            stdlib_imports[module_name].add(item)
                        # Check if this is a standard library module
                        elif self.is_stdlib_module(item):
                            if item not in stdlib_imports:
                                stdlib_imports[item] = set()
                            stdlib_imports[item].add(item)
                        else:
                            # Handle third-party imports
                            if item not in third_party_imports:
                                third_party_imports[item] = set()
                            third_party_imports[item].add(item)
                    console.print(f"[dim]Added direct imports: {value}[/]")
        
        # Add typing imports at the beginning
        if typing_imports:
            typing_imports_str = ", ".join(sorted(typing_imports))
            import_statements.insert(0, f"from typing import {typing_imports_str}")
            console.print(f"[dim]Added typing imports: {typing_imports_str}[/]")
            
        # Add stdlib imports
        for module, imports in sorted(stdlib_imports.items()):
            # Group submodule imports
            submodules = {imp for imp in imports if '.' in imp}
            direct_imports = imports - submodules
            
            if direct_imports:
                imports_str = ", ".join(sorted(direct_imports))
                import_statements.append(f"from {module} import {imports_str}")
            
            if submodules:
                for submodule in sorted(submodules):
                    import_statements.append(f"import {submodule}")
                
        # Add third-party imports
        for module, imports in sorted(third_party_imports.items()):
            # Group submodule imports
            submodules = {imp for imp in imports if '.' in imp}
            direct_imports = imports - submodules
            
            if direct_imports:
                imports_str = ", ".join(sorted(direct_imports))
                import_statements.append(f"from {module} import {imports_str}")
            
            if submodules:
                for submodule in sorted(submodules):
                    import_statements.append(f"import {submodule}")
                        
        return import_statements

    def get_consolidated_imports(self, exclude_package: Optional[str] = None) -> str:
        """Get all imports as a single string, optionally excluding a package.
        
        Args:
            exclude_package: Optional package name to exclude from the generated imports
            
        Returns:
            String of import statements
        """
        # Filter out excluded package if specified
        filtered_imports = self.import_object
        if exclude_package and exclude_package in filtered_imports:
            filtered_imports = {k: v for k, v in filtered_imports.items() if k != exclude_package}
            
        # Reconstruct import statements
        import_lines = self._reconstruct_imports(filtered_imports)
        
        # Sort imports by type (stdlib first, then third-party)
        stdlib_imports = []
        third_party_imports = []
        
        for line in import_lines:
            try:
                # Extract the module name from the import line
                if line.startswith("from "):
                    # Handle "from x import y" format
                    module = line.split(" import ")[0].replace("from ", "").strip()
                else:
                    # Handle "import x" format
                    module = line.replace("import ", "").strip()
                    # Handle aliases (import x as y)
                    if ' as ' in module:
                        module = module.split(' as ')[0].strip()
                    
                # Get the root module name (first part before any dots)
                root_module = module.split('.')[0]
                
                if self.is_stdlib_module(root_module):
                    stdlib_imports.append(line)
                else:
                    third_party_imports.append(line)
            except Exception as e:
                console.print(f"[warning]Error processing import line: {line} - {e}")
                continue
                
        # Combine and return
        all_imports = sorted(stdlib_imports) + sorted(third_party_imports)
        return "\n".join(all_imports) if all_imports else ""
    
    @staticmethod
    def is_stdlib_module(module_name: str) -> bool:
        """Check if a module is part of the Python standard library."""
        root_module = module_name.split(".")[0]
        return root_module in ImportManager.STDLIB_MODULES
    
    def is_third_party(self, module_name: str) -> bool:
        """Check if a module is a third-party library (not stdlib and not local)."""
        if not module_name:
            return False
            
        # First check if it's a local import
        if self.is_local_import(module_name):
            return False
            
        # Then check if it's in standard library
        if self.is_stdlib_module(module_name):
            return False
            
        # Try to find the module
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or not spec.origin:
                return False
            # Check if the module is installed in a Python package directory
            # This avoids hard-coding specific directory names like 'site-packages'
            if not spec.origin:
                return False
            # Check if it's in a Python installation directory but not a standard library
            python_path = os.path.dirname(os.__file__)
            return python_path in spec.origin and not self.is_stdlib_module(module_name)
        except Exception:
            return False
    
    def get_third_party_packages(self) -> Set[str]:
        """Return a set of third-party package names based on the imports."""
        packages = set()
        
        # Process modules from "from x import y" imports
        for module in self.from_imports:
            if not self.is_stdlib_module(module) and not self.is_local_import(module):
                root_module = module.split(".")[0]
                if root_module in self.PACKAGE_NAME_MAP:
                    packages.add(self.PACKAGE_NAME_MAP[root_module])
                else:
                    packages.add(root_module)
        
        # Process "import x" imports
        for module_entry in self.direct_imports:
            # Handle aliases (import x as y)
            if ' as ' in module_entry:
                module = module_entry.split(' as ')[0].strip()
            else:
                module = module_entry
                
            if not self.is_stdlib_module(module) and not self.is_local_import(module):
                root_module = module.split(".")[0]
                if root_module in self.PACKAGE_NAME_MAP:
                    packages.add(self.PACKAGE_NAME_MAP[root_module])
                else:
                    packages.add(root_module)
        
        return packages
    
    def resolve_local_module(self, importing_file: str, module_name: str, target_path: Optional[Path] = None) -> Optional[str]:
        """Resolve a local module name to its file path.
        
        Args:
            importing_file: The file that contains the import
            module_name: The module being imported
            target_path: Optional target path for the project root
            
        Returns:
            Resolved file path or None if not found
        """
        importing_dir = Path(importing_file).parent
        
        if module_name.startswith("."):
            # Handle relative imports
            level = 0
            for char in module_name:
                if char == ".":
                    level += 1
                else:
                    break
            
            # Remove the dots from the module name
            module_path = module_name[level:]
            
            # Navigate up by 'level' directories
            current_dir = importing_dir
            for _ in range(level - 1):  # -1 because first dot is current dir
                current_dir = current_dir.parent
            
            # Construct the potential file path
            if module_path:
                module_file = current_dir / f"{module_path.replace('.', os.sep)}.py"
            else:
                # Handle "from . import x" case - look for __init__.py
                module_file = current_dir / "__init__.py"
                
            # Convert to string for consistency
            return str(module_file) if module_file.exists() else None
        
        elif target_path and self.target_package and module_name.startswith(self.target_package):
            # Handle absolute imports within the project
            # This assumes all absolute imports are from the project root
            rel_module = module_name[len(self.target_package) + 1:]
            module_file = target_path / f"{rel_module.replace('.', os.sep)}.py"
            return str(module_file) if module_file.exists() else None
        
        return None


class DependencyManager:
    """Manages dependency relationships between Python modules.
    
    This class is responsible for building a dependency graph of local modules
    and performing topological sorting to determine the order in which modules
    should be processed.
    """
    
    def __init__(self, import_manager: ImportManager, target_path: Optional[Path] = None, entry_point: Optional[Path] = None):
        """Initialize the DependencyManager.
        
        Args:
            import_manager: An instance of ImportManager to use for import resolution
            target_path: The base path of the project (optional)
        """
        self.import_manager = import_manager
        self.target_path = target_path
        self.entry_point = None
        # Graph representation: {module_path: {dependencies}}
        self.dependency_graph: Dict[str, Set[str]] = {}
        # Modules that have been processed
        self.processed_modules: Set[str] = set()
        # Module name to file path mapping
        self.module_map: Dict[str, str] = {}
        
    def add_module(self, module_path: str) -> None:
        """Add a module to the dependency graph.
        
        Args:
            module_path: The file path to the module
        """
        if module_path not in self.dependency_graph:
            self.dependency_graph[module_path] = set()
            
            # Add to module map for easier lookup
            module_name = Path(module_path).stem
            self.module_map[module_name] = module_path
            
    def add_dependency(self, module_path: str, dependency_path: str) -> None:
        """Add a dependency relationship between modules.
        
        Args:
            module_path: The file path to the module that has the dependency
            dependency_path: The file path to the module that is being depended on
        """
        # Ensure both modules are in the graph
        self.add_module(module_path)
        self.add_module(dependency_path)
        
        # Add the dependency relationship
        if module_path != dependency_path:  # Avoid self-dependencies
            self.dependency_graph[module_path].add(dependency_path)
    
    def build_dependency_graph(self, entry_point: str) -> Dict[str, Set[str]]:
        """Build a dependency graph starting from an entry point file.
        
        Args:
            entry_point: The file path to the entry point module
            
        Returns:
            A dictionary representing the dependency graph
        """
        # Reset the graph and processed modules
        self.dependency_graph = {}
        self.processed_modules = set()
        self.module_map = {}
        
        # Process the entry point and its dependencies recursively
        self._process_module_dependencies(entry_point)
        
        return self.dependency_graph
    
    def _find_module_file(self, importing_dir: Path, module_name: str) -> Optional[str]:
        """Find a module file based on its name and the importing directory.
        
        Args:
            importing_dir: Directory of the importing module
            module_name: Name of the module to find
            
        Returns:
            Path to the module file or None if not found
        """
        # Check if it's a direct file reference
        module_file = importing_dir / f"{module_name}.py"
        if module_file.exists():
            return str(module_file)
            
        # Check if it's a package (has __init__.py)
        init_file = importing_dir / module_name / "__init__.py"
        if init_file.exists():
            return str(init_file)
            
        return None
    
    def _resolve_relative_import(self, importing_file: str, module_name: str) -> List[str]:
        """Resolve a relative import to a list of possible file paths.
        
        Args:
            importing_file: Path to the file containing the import
            module_name: The module name being imported
            
        Returns:
            List of possible file paths for the import
        """
        importing_path = Path(importing_file)
        importing_dir = importing_path.parent
        
        # Count leading dots for relative imports
        dots = 0
        for char in module_name:
            if char == '.':
                dots += 1
            else:
                break
                
        # Remove dots from module name
        clean_module = module_name[dots:]
        
        # Navigate up directories based on dot count
        current_dir = importing_dir
        for _ in range(dots - 1):  # -1 because first dot is current directory
            if current_dir.name:  # Make sure we're not at root
                current_dir = current_dir.parent
        
        resolved_paths = []
        
        # If no module specified after dots (e.g., "from . import x")
        # We'll skip __init__.py files as they're not actual module dependencies
        if not clean_module:
            return resolved_paths
            
        # Handle module with submodules (e.g., "from .submodule import x")
        parts = clean_module.split('.')
        
        # Try to find the module
        for i in range(len(parts)):
            # Build the path incrementally
            partial_path = current_dir
            for part in parts[:i+1]:
                partial_path = partial_path / part
                
            # Check for .py file
            py_file = partial_path.with_suffix('.py')
            if py_file.exists() and not py_file.name == '__init__.py':
                resolved_paths.append(str(py_file))
                
            # Skip __init__.py files as they're not actual module dependencies
        
        return resolved_paths
    
    def _process_module_dependencies(self, module_path: str) -> None:
        """Process a module's dependencies and add them to the graph.
        
        Args:
            module_path: The file path to the module to process
        """
        if module_path in self.processed_modules:
            return
            
        self.processed_modules.add(module_path)
        self.add_module(module_path)
        
        try:
            # Read the module content
            with open(module_path, 'r') as f:
                code = f.read()
                
            # Extract imports
            temp_import_manager = ImportManager(target_path=self.target_path)
            temp_import_manager.extract_imports_from_code(code)
            
            module_dir = Path(module_path).parent
            
            # Debug output for this module
            module_rel_path = Path(module_path).relative_to(self.target_path) if self.target_path and self.target_path in Path(module_path).parents else Path(module_path).name
            if temp_import_manager.from_imports or temp_import_manager.direct_imports:
                if verbose:
                    console.print(f"[dim]Processing imports for [cyan]{module_rel_path}[/dim]")

            
            # Process "from x import y" imports
            for module_name in temp_import_manager.from_imports.keys():
                # Debug output
                if verbose:
                    console.print(f"[dim]  - from {module_name} import ...[/]")
                self._process_import(module_path, module_name)
                
            # Process "import x" imports
            for module_entry in temp_import_manager.direct_imports:
                # Handle aliases (import x as y)
                if ' as ' in module_entry:
                    module_name = module_entry.split(' as ')[0].strip()
                else:
                    module_name = module_entry
                    
                # Debug output
                if verbose:
                    console.print(f"[dim]  - import {module_name}[/dim]")
                self._process_import(module_path, module_name)
                
        except Exception as e:
            console.print(f"[warning]Error processing dependencies for {module_path}: {e}")
            
    def _process_import(self, importing_file: str, module_name: str) -> None:
        """Process an import statement and add dependencies to the graph.
        
        Args:
            importing_file: The file containing the import
            module_name: The module being imported
        """
        # Skip standard library and third-party imports
        if ImportManager.is_stdlib_module(module_name) or not self.import_manager.is_local_import(module_name):
            return
            
        dependency_paths = []
        
        # Handle relative imports
        if module_name.startswith('.'):
            dependency_paths.extend(self._resolve_relative_import(importing_file, module_name))
        else:
            # Handle absolute imports
            if self.target_path:
                # Special handling for project structure with top-level package
                # For imports like 'from erasmus.context import ...'
                parts = module_name.split('.')
                
                # If the first part matches a top-level package in the project
                top_level_package = parts[0]
                package_dir = self.target_path / top_level_package
                
                if package_dir.exists() and (package_dir / "__init__.py").exists():
                    # This is a top-level package
                    if len(parts) > 1:
                        # Try to resolve the module within the package
                        module_path = os.path.join(*parts[1:])
                        py_file = package_dir / f"{module_path}.py"
                        
                        if py_file.exists():
                            if verbose:
                                console.print(f"[dim]  Found module in top-level package: {py_file.relative_to(self.target_path)}[/dim]")
                            dependency_paths.append(str(py_file))
                        else:
                            # Try as a package path
                            sub_package_path = package_dir
                            for part in parts[1:-1]:  # Skip the last part which should be a module
                                sub_package_path = sub_package_path / part
                                if not (sub_package_path.exists() and (sub_package_path / "__init__.py").exists()):
                                    break
                            
                            # Check if the last part is a module
                            if sub_package_path.exists():
                                py_file = sub_package_path / f"{parts[-1]}.py"
                                if py_file.exists():
                                    if verbose:
                                        console.print(f"[dim]  Found module in subpackage: {py_file.relative_to(self.target_path)}[/dim]")
                                    dependency_paths.append(str(py_file))
                                    
                                    # Also look for modules in this package
                                    self._find_modules_in_package(sub_package_path, dependency_paths)
                else:
                    # Try different resolution strategies
                    dependency_paths.extend(self._resolve_absolute_import(parts))
                    
                    # If no dependencies found, try with the target package prefix
                    if not dependency_paths and self.import_manager.target_package:
                        # Try with target package prefix
                        if not module_name.startswith(self.import_manager.target_package):
                            prefixed_module = f"{self.import_manager.target_package}.{module_name}"
                            prefixed_parts = prefixed_module.split('.')
                            dependency_paths.extend(self._resolve_absolute_import(prefixed_parts))
        
        # Add all found dependencies to the graph, skipping __init__.py files
        for dependency_path in dependency_paths:
            if os.path.exists(dependency_path) and not dependency_path.endswith('__init__.py'):
                self.add_dependency(importing_file, dependency_path)
                # Recursively process this dependency's dependencies
                self._process_module_dependencies(dependency_path)
                
    def _resolve_absolute_import(self, parts: List[str]) -> List[str]:
        """Resolve an absolute import path to file paths.
        
        Args:
            parts: The parts of the module path
            
        Returns:
            List of resolved file paths
        """
        dependency_paths = []
        
        if not self.target_path:
            return dependency_paths
        
        # Debug output
        module_path_str = '.'.join(parts)
        if verbose:
            console.print(f"[dim]Resolving absolute import: {module_path_str}[/]")
        
        # Check if this is a package-style import where the first part is the package name
        target_package_name = self.target_path.name
        
        # Strategy 0: Handle package-style imports (e.g., 'package_name.module')
        if parts and parts[0] == target_package_name:
            # This is an import from the current package
            # Remove the package name from the parts and resolve from the base path
            if len(parts) > 1:
                # For imports like 'package_name.submodule'
                remaining_parts = parts[1:]
                module_path = os.path.join(*remaining_parts)
                py_file = self.target_path / f"{module_path}.py"
                if py_file.exists():
                    if verbose:
                        console.print(f"[dim]  Found package module: {py_file.relative_to(self.target_path)}[/]")
                    dependency_paths.append(str(py_file))
                    return dependency_paths
                
                # Try traversing through subdirectories
                current_path = self.target_path
                for i, part in enumerate(remaining_parts):
                    # Check if this is a file
                    py_file = current_path / f"{part}.py"
                    if py_file.exists():
                        if verbose:
                            console.print(f"[dim]  Found package module file: {py_file.relative_to(self.target_path)}[/]")
                        dependency_paths.append(str(py_file))
                        return dependency_paths
                    
                    # Check if this is a package
                    package_dir = current_path / part
                    init_file = package_dir / "__init__.py"
                    if init_file.exists():
                        if verbose:
                            console.print(f"[dim]  Found package directory: {package_dir.relative_to(self.target_path)}[/]")
                        current_path = package_dir
                        
                        # If this is the last part, add the __init__.py file
                        if i == len(remaining_parts) - 1:
                            dependency_paths.append(str(init_file))
                            return dependency_paths
                        
                        continue
                    
                    # If we can't find the module, break
                    break
            
        # Strategy 1: Direct module path
        module_path = os.path.join(*parts)
        py_file = self.target_path / f"{module_path}.py"
        if py_file.exists():
            if verbose:
                console.print(f"[dim]  Found direct module: {py_file.relative_to(self.target_path)}[/]")
            dependency_paths.append(str(py_file))
            
        # Strategy 2: Traverse the path parts
        current_path = self.target_path
        for i, part in enumerate(parts):
            # Check if this is a file
            py_file = current_path / f"{part}.py"
            if py_file.exists():
                if verbose:
                    console.print(f"[dim]  Found module file: {py_file.relative_to(self.target_path)}[/]")
                dependency_paths.append(str(py_file))
                break
                
            # Check if this is a package
            package_dir = current_path / part
            init_file = package_dir / "__init__.py"
            if init_file.exists():
                if verbose:
                    console.print(f"[dim]  Found package: {package_dir.relative_to(self.target_path)}[/]")
                current_path = package_dir
                
                # If this is the last part, we might want the __init__.py
                if i == len(parts) - 1:
                    dependency_paths.append(str(init_file))
                    
                # If we've processed all parts, look for modules inside this package
                if i == len(parts) - 1:
                    # Look for modules in this package that match the last part
                    self._find_modules_in_package(package_dir, dependency_paths)
                    
                continue
                
            # If we can't find the module, break
            break
            
        # Strategy 3: Try to find the module in common module directories
        for common_dir in ['modules', 'lib', 'core', 'utils', 'api', 'services', 'models']:
            if (self.target_path / common_dir).exists():
                # Try as a direct module in the common directory
                module_path = os.path.join(*parts)
                py_file = self.target_path / common_dir / f"{module_path}.py"
                if py_file.exists():
                    if verbose:
                        console.print(f"[dim]  Found in common dir: {py_file.relative_to(self.target_path)}[/]")
                    dependency_paths.append(str(py_file))
                
                # Try as a package in the common directory
                package_dir = self.target_path / common_dir / parts[0]
                if package_dir.exists() and (package_dir / "__init__.py").exists():
                    # This is a package, try to find the module inside
                    if len(parts) > 1:
                        sub_module_path = os.path.join(*parts[1:])
                        py_file = package_dir / f"{sub_module_path}.py"
                        if py_file.exists():
                            if verbose:
                                console.print(f"[dim]  Found in package in common dir: {py_file.relative_to(self.target_path)}[/]")
                            dependency_paths.append(str(py_file))
        
        # Strategy 4: Try all top-level packages
        # This handles imports like 'package.subpackage.module'
        if len(parts) > 1 and not dependency_paths:
            # Find all top-level packages
            for item in self.target_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    # This is a package, check if it matches the first part
                    if item.name == parts[0]:
                        # Try to find the module inside this package
                        sub_module_path = os.path.join(*parts[1:])
                        py_file = item / f"{sub_module_path}.py"
                        if py_file.exists():
                            if verbose:
                                console.print(f"[dim]  Found in top-level package: {py_file.relative_to(self.target_path)}[/]")
                            dependency_paths.append(str(py_file))
        
        if not dependency_paths:
            if verbose:
                console.print(f"[dim]  No modules found for {module_path_str}[/]")
            
        return dependency_paths
        
    def _find_modules_in_package(self, package_dir: Path, dependency_paths: List[str]) -> None:
        """Find Python modules in a package directory.
        
        Args:
            package_dir: The package directory to search
            dependency_paths: List to append found module paths to
        """
        # Look for Python files in the package
        for item in package_dir.glob("*.py"):
            if item.name != "__init__.py":
                if verbose:
                    console.print(f"[dim]  Found module in package: {item.relative_to(self.target_path)}[/]")
                dependency_paths.append(str(item))
                
        # Look for subpackages
        for item in package_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                # This is a subpackage, look for modules inside
                self._find_modules_in_package(item, dependency_paths)
    
    def topological_sort(self) -> List[str]:
        """Perform a topological sort of the modules in the dependency graph.
        
        Returns:
            A list of module paths in topological order (dependencies first)
        """
        # Create a reversed graph (edges point from dependencies to dependents)
        reversed_graph: Dict[str, Set[str]] = {node: set() for node in self.dependency_graph}
        for node, deps in self.dependency_graph.items():
            for dep in deps:
                if dep in reversed_graph:
                    reversed_graph[dep].add(node)
                else:
                    reversed_graph[dep] = {node}
        
        # Find nodes with no dependencies (leaf nodes)
        no_deps = [node for node, deps in self.dependency_graph.items() if not deps]
        
        # Queue for processing
        queue: Deque[str] = deque(no_deps)
        
        # Result list (dependencies first)
        sorted_nodes: List[str] = []
        visited: Set[str] = set()
        
        # Process nodes
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
                
            # Add to result
            sorted_nodes.append(node)
            visited.add(node)
            
            # Add dependents to queue
            for dependent in reversed_graph.get(node, set()):
                # Check if all dependencies of this dependent are visited
                if all(dep in visited for dep in self.dependency_graph.get(dependent, set())):
                    queue.append(dependent)
        
        # Check for cycles or unreachable nodes
        if len(sorted_nodes) != len(self.dependency_graph):
            if verbose:
                console.print("[warning]Dependency graph may contain cycles or unreachable nodes!")
            # Try to add remaining nodes
            for node in self.dependency_graph:
                if node not in sorted_nodes:
                    sorted_nodes.append(node)
        
        return sorted_nodes
    
    def visualize_graph(self) -> None:
        """Visualize the dependency graph as a text representation.
        
        In the future, this could be enhanced to generate a visual representation
        using libraries like networkx and matplotlib.
        """
        if not self.dependency_graph:
            if verbose:
                console.print("[yellow]No dependency graph to visualize. Build the graph first.[/]")
            return
            
        # Get base path for relative path display
        target_path = self.target_path if self.target_path else None
        
        # Sort modules by name for consistent output
        sorted_modules = sorted(self.dependency_graph.keys(), 
                               key=lambda m: Path(m).name if target_path is None else str(Path(m).relative_to(target_path) if target_path in Path(m).parents else Path(m).name))
        
        # Find the maximum depth of the dependency tree
        max_depth = 0
        visited = set()
        
        def get_depth(module, current_depth=0):
            nonlocal max_depth
            if current_depth > max_depth:
                max_depth = current_depth
            if module in visited:
                return
            visited.add(module)
            for dep in self.dependency_graph.get(module, set()):
                get_depth(dep, current_depth + 1)
                
        for module in sorted_modules:
            get_depth(module)
            
        # Print header
        if verbose:
            console.print(f"[bold]Found {len(self.dependency_graph)} modules with maximum dependency depth of {max_depth}[/]")
        
        # Print each module and its dependencies
        for module in sorted_modules:
            # Format the module name (use relative path if possible)
            if target_path and target_path in Path(module).parents:
                module_display = f"[cyan]{Path(module).relative_to(target_path)}[/]"
            else:
                module_display = f"[cyan]{Path(module).name}[/]"
                
            # Get dependencies
            deps = self.dependency_graph.get(module, set())
            
            if deps:
                # Format dependencies
                dep_displays = []
                for dep in sorted(deps, key=lambda d: Path(d).name):
                    if target_path and target_path in Path(dep).parents:
                        dep_displays.append(f"[green]{Path(dep).relative_to(target_path)}[/]")
                    else:
                        dep_displays.append(f"[green]{Path(dep).name}[/]")
                        
                if verbose:
                    console.print(f"{module_display} → {', '.join(dep_displays)}")
            else:
                if verbose:
                    console.print(f"{module_display} [dim](no dependencies)[/]")
                
        # Print summary statistics
        dependency_counts = {module: len(deps) for module, deps in self.dependency_graph.items()}
        dependent_counts = {}
        
        # Count how many modules depend on each module
        for module, deps in self.dependency_graph.items():
            for dep in deps:
                dependent_counts[dep] = dependent_counts.get(dep, 0) + 1
                
        # Find modules with most dependencies and most dependents
        if dependency_counts:
            most_dependencies = max(dependency_counts.items(), key=lambda x: x[1])
            console.print(f"\n[bold]Module with most dependencies:[/] "
                         f"[cyan]{Path(most_dependencies[0]).name}[/] "
                         f"({most_dependencies[1]} dependencies)")
                         
        if dependent_counts:
            most_dependents = max(dependent_counts.items(), key=lambda x: x[1])
            console.print(f"[bold]Most depended upon module:[/] "
                         f"[cyan]{Path(most_dependents[0]).name}[/] "
                         f"(used by {most_dependents[1]} modules)")
                         


    def resolve_dependency_graph(
            self, target_path: Path,
            entry_point: Path,
            verbose: bool = False
        ) -> List[str]:
        """Resolve the dependency graph for a given entry point and return modules in topological order.
        
        Args:
            entry_point: Path to the entry point file
            verbose: Whether to print detailed output
            
        Returns:
            List of module paths in topological order (dependencies first)
        """
        target_path = Path(target_path) or self.target_path
        entry_point = Path(entry_point) or self.entry_point
        verbose = verbose or os.getenv("ERASMUS_DEBUG", "false").lower() == "true"
        if not target_path:
            raise ValueError("Base path is required")
        if not entry_point:
            raise ValueError("Entry point path is required")
        self.target_path = Path.cwd() / target_path
        self.entry_point = target_path / entry_point
        if not target_path.exists():
            if verbose:
                console.print(f"[bold red]Error: Base path {self.target_path} does not exist![/]")
            return []
        
        # Check if the entry point exists
        if not self.entry_point.exists():
            if verbose:
                console.print(f"[bold red]Error: Entry point {self.entry_point} does not exist![/]")
            return []
        
        # Use the target_path as the project root if provided
        if self.target_path:
            project_root = self.target_path
        
        if verbose:
            console.print(f"[bold green]Building dependency graph[/]")
            console.print(f"Project root: [cyan]{project_root}[/]")
            console.print(f"Entry point: [cyan]{self.entry_point}[/]\n")
        
        
        # Build the dependency graph
        if verbose:
            console.print("[bold]Building dependency graph...[/]")
        
        dependency_graph = self.build_dependency_graph(str(self.entry_point))
        
        if verbose:
            console.print(f"Found [bold cyan]{len(dependency_graph)}[/] modules in the dependency graph.\n")
        
        # Perform topological sorting
        if verbose:
            console.print("[bold]Performing topological sort...[/]")
        
        sorted_modules = self.topological_sort()
        
        if verbose:
            # Print the sorted modules
            console.print("\n[bold green]Modules in Topological Order (dependencies first):[/]")
            for i, module in enumerate(sorted_modules, 1):
                # Show relative path from project root
                try:
                    rel_path = Path(module).relative_to(project_root)
                    console.print(f"  {i}. [cyan]{rel_path}[/]")
                except ValueError:
                    # If not relative to project root, show the full path
                    console.print(f"  {i}. {Path(module).name}")
            
            # Visualize the graph
            console.print("\n[bold green]Dependency Graph Visualization:[/]")
            self.visualize_graph()
        
        return sorted_modules

    


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Resolve dependencies for a given entry point")
    parser.add_argument("target_path", type=str, help="Path to the base directory of the project")
    parser.add_argument("entry_point", type=str, help="Path to the entry point file in relation to the target_path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    target_path = Path(args.target_path)
    entry_point = Path(args.entry_point)
    import_manager = ImportManager(target_path=target_path)
    dependency_manager = DependencyManager(import_manager, target_path=target_path)
    # graph = dependency_manager.resolve_dependency_graph(target_path, entry_point, args.verbose)
    # print(import_manager.import_object)