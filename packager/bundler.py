import os
import re
import subprocess
import functools
import importlib.util
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional

from import_manager import ImportManager, DependencyManager
from visualizer import visualize_graph
from utils.rich_console import get_console_logger
from embedder import add_embedded_files

console = get_console_logger()

class PythonBundler:
    IGNORE_PATHS = {
        'test', 'tests', '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
        'node_modules', 'target', 'dist', 'build', '.venv', 'venv', '__init__.py'
    }
    IF_NAME_MAIN = ["if __name__ == '__main__':", 'if __name__ == "__main__"']

    def __init__(self, target_path: Path | None = None, output_path: Path | None = None, files_to_bundle: List[str] | None = None, entry_point: Path | None = None):
        """Initialize the bundler.
        
        Args:
            target_path: Path to the target package to bundle
            output_path: Path to write the bundled output
            files_to_bundle: Optional list of specific files to bundle
            entry_point: Optional entry point file path (relative to target_path)
        """
        console.info("Initializing bundler...")
        self.target_path = target_path or Path.cwd() / "data" / "simple_project"
        self.output_path = output_path or Path.cwd() / "data" / "simple_project" / "simple_project_bundle.py"
        self.entry_point = self.target_path / entry_point if entry_point else None
        self.files_to_bundle = files_to_bundle
        
        self.has_visualize = False
        self.check_visualization()
        self.suffix = ".py"
        self.third_party_libs: Set[str] = set()
        self.import_manager = ImportManager(self.target_path)
        self.dependency_manager = DependencyManager(self.import_manager, self.target_path, self.entry_point)
        self.directory_tree = None
        self.files_code_map = None
        self.dependency_graph = None
        self.ordered_files = None
        self.original_bundle = ""
        self.code_blocks = {}
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def check_visualization(self) -> None:
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            self.has_visualize = True
        except ImportError:
            self.has_visualize = False

        if not self.has_visualize:
            console.print("[error]Cannot visualize graph: networkx and/or matplotlib not installed.")
            console.print("[info]Install with: uv pip install networkx matplotlib")

    def visualize_graph(self, output_path: Path | None = None):
        self.check_visualization()
        if not self.has_visualize:
            return
        visualize_graph(self.files_code_map, self.dependency_graph, output_path)

    def should_ignore(self, path: str | Path) -> bool:
        parts = str(path).split(os.sep)
        return any(part in self.IGNORE_PATHS for part in parts)

    def walk_directory_tree(self, input_path: Path) -> dict[str, dict | str] | str:
        console.info(f"Walking directory tree for {input_path}...")
        if input_path.is_file():
            return str(input_path)

        def walk(path: Path, acc: dict[str, dict | str]) -> None:
            for child in path.iterdir():
                if self.should_ignore(child):
                    continue
                if child.is_file():
                    acc[str(child.name)] = str(child)
                elif child.is_dir():
                    acc.setdefault(str(child.name), {})
                    walk(child, acc[str(child.name)])

        tree = {}
        walk(input_path, tree)
        return tree

    def read_all_files(self, directory_tree: dict | None = None) -> dict[str, str]:
        console.info("Reading all files...")
        directory_tree = directory_tree or self.directory_tree
        files_code = {}

        def walk(tree: dict[str, dict | str]):
            for key, value in tree.items():
                if self.should_ignore(key):
                    continue
                if isinstance(value, str) and key.endswith(self.suffix):
                    code = Path(value).read_text()
                    files_code[value] = code
                elif isinstance(value, dict):
                    walk(value)

        walk(directory_tree)
        return files_code

    def is_local_import(self, module_name: str) -> bool:
        """Check if a module import is a local import."""
        console.info(f"Checking if {module_name} is a local import...")
        return self.import_manager.is_local_import(module_name)

    @functools.lru_cache(maxsize=128)
    def is_third_party(self, module: str) -> bool:
        """Check if a module is a third-party library (not stdlib and not local)."""
        console.info(f"Checking if {module} is a third-party library...")
        return self.import_manager.is_third_party(module)
    
    def clean_code(self, code: str) -> str:
        """Clean up the code by removing local imports and __main__ blocks."""
        console.info("Cleaning code...")
        # Use ImportManager to filter local imports and extract third-party imports
        code = self.import_manager.filter_local_imports(code)
        # Remove __main__ blocks
        code = self.remove_if_name_main(code)
        return code

    def remove_if_name_main(self, code: str) -> str:
        """Remove the if __name__ == '__main__' block from the code."""
        lines = code.splitlines()
        result = []
        
        for line in lines:
            if any(line.startswith(if_name_main) for if_name_main in self.IF_NAME_MAIN):
                break
            result.append(line)
        
        return "\n".join(result)

    def add_third_party_with_uv(self):
        """Install third-party dependencies using uv."""
        console.info("Adding third-party dependencies using uv...")
        
        # Verify that the output file exists
        if not self.output_path.exists():
            console.print(f"[error]Output file {self.output_path} does not exist. Cannot add dependencies.")
            return
            
        # Get third-party packages from import manager
        packages = self.import_manager.get_third_party_packages()
        
        if not packages:
            console.print("[info]No third-party packages to add.")
            return
            
        console.print(f"[info]Adding {len(packages)} third-party packages with uv...")
        
        # Create a list to collect all packages for a single uv add command
        all_packages = []
        
        for package in packages:
            # Skip the target package itself (this check is now done in ImportManager.get_third_party_packages)
            package_name = ImportManager.PACKAGE_NAME_MAP.get(package, package)
            all_packages.append(package_name)
        
        # Run a single uv add command with all packages
        try:
            # Build the command: uv add --script path/to/script.py pkg1 pkg2 pkg3...
            cmd = ["uv", "add", "--script", str(self.output_path)] + all_packages
            console.print(f"[info]Running: {' '.join(cmd)}")
            
            # Run the command
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Check if the command was successful
            if result.returncode == 0:
                console.print(f"[success]Successfully added all dependencies")
                # Add a comment to show the command output for debugging
                if result.stdout.strip():
                    console.print(f"[debug]Command output: {result.stdout.strip()}")
            else:
                console.print(f"[error]Failed to add dependencies: {result.stderr}")
        except subprocess.CalledProcessError as e:
            console.print(f"[error]Failed to add dependencies using uv: {e}")
            if e.stderr:
                console.print(f"[error]Error details: {e.stderr}")
        except FileNotFoundError:
            console.print(f"[error]The 'uv' command was not found. Make sure uv is installed and in your PATH.")
            console.print(f"[info]You can install uv with: pip install uv")
        except Exception as e:
            console.print(f"[error]Unexpected error adding dependencies: {e}")
            
    def _clean_imports(self, all_imports: set[str]):
        all_imports = list(set(all_imports))
        imports_dict =  {}
        imports_dict["indirect_imports"] = {}
        final_imports = ""
        for import_ in all_imports:
            if import_.startswith(f'from {self.target_path.name}'):
                continue
            if import_.startswith ("from ."):
                continue
            if import_.startswith ("import ."):
                continue
            if import_.startswith (f"import {self.target_path.name}"):
                continue
            if import_.startswith("from "):
                module_name = import_.split("from ", 1)[1].split(" import ", 1)[0]
                module_imports = import_.split("import ", 1)[1].split(", ")
                if module_name not in imports_dict["indirect_imports"]:
                    imports_dict["indirect_imports"][module_name] = set()
                if isinstance(module_imports, list):
                    imports_dict["indirect_imports"][module_name].update(module_imports)  
                else:
                    imports_dict["indirect_imports"][module_name].add(module_imports)
            if import_.startswith("import "):
                final_imports += import_ + "\n"
        for key in imports_dict["indirect_imports"].keys():
            imports_dict["indirect_imports"][key] = list(imports_dict["indirect_imports"][key])
        # console.print_json(imports_dict)
        for key in imports_dict["indirect_imports"].keys():
            final_imports += f"from {key} import {', '.join(imports_dict["indirect_imports"][key])}\n"
        return final_imports

    def generate_code(self, target_path: Path | None = None, entry_point: Path | None = None) -> str:
        """Generate the bundled code."""
        self.target_path = target_path if target_path else self.target_path
        self.entry_point = self.target_path / entry_point if entry_point else self.entry_point
        if not self.entry_point or not self.target_path:
            console.print("[bold red]No entry point or target path provided.[/]")
            return
        self.directory_tree = self.walk_directory_tree(self.target_path)
        # console.print_json(self.directory_tree)
        self.files_code_map = self.read_all_files(self.directory_tree)

        all_imports = set()
        for file_path, code in self.files_code_map.items():
            filepath = Path(file_path)
            filename = filepath.stem
            self.original_bundle += f"# {filename}\n"
            self.original_bundle += code
            self.original_bundle += "\n\n"
            
            code, extracted_imports = self.import_manager.extract_imports_from_code(code)
            code = self.remove_if_name_main(code)
            self.code_blocks[filename] = code
            all_imports.update(extracted_imports)
        final_imports = self._clean_imports(all_imports)

        code_to_write = final_imports + "\n\n"
        code_to_write += add_embedded_files() + "\n\n"
        
        sorted_modules = self.dependency_manager.resolve_dependency_graph(target_path=self.target_path, entry_point=self.entry_point)
        for module in sorted_modules:
            code_to_write += f"# {module}\n"
            code_to_write += self.code_blocks[Path(module).stem]
            code_to_write += "\n\n"


        code_to_write += """
if __name__ == "__main__":
    from click import UsageError

    try:
        app(standalone_mode=False)
    except UsageError as error:
        typer.echo(str(error))
        print_main_help_and_exit()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)
    except SystemExit as error:
        if error.code != 2:
            raise
"""
        self.output_path.write_text(code_to_write)


        self.add_third_party_with_uv()
    



        
    
if __name__ == "__main__":
    input_path = Path.home() / "repos" / "erasmus" / "erasmus"
    output_path = Path.cwd() / "data" / "output" / "erasmus_bundle.py"
    entry_point = Path("cli/main.py")  # Specify the entry point relative to input_path
    bundler = PythonBundler(input_path, output_path, entry_point)
    bundler.generate_code(target_path=input_path, entry_point=entry_point)
