"""Convert shell scripts to Windows batch scripts using direct pattern matching."""
print("Script converter module loaded!")
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ScriptConverter:
    def __init__(self):
        # Mapping of shell commands to batch equivalents
        self.command_map = {
            'command -v': 'where',
            'echo -e': 'echo',
            '>/dev/null 2>&1': '>nul 2>&1',
            '||': '|| (',
            '&&': '&& (',
            'fi': ')',
            'then': '(',
            'else': ') else (',
            'case': 'if',
            'esac': ')',
            'uname -s': 'ver',
        }

        # Special patterns that need custom handling
        self.patterns = {
            r'#!/usr/bin/env bash': '@echo off\nsetlocal enabledelayedexpansion',
            r'\$\{(\w+)\}': r'%\1%',  # ${VAR} -> %VAR%
            r'\$(\w+)': r'%\1%',      # $VAR -> %VAR%
            r'\[\[(.+?)\]\]': r'"\1"', # [[condition]] -> "condition"
        }

        # Function conversion templates
        self.function_templates = {
            'detect_os': '''
:detect_os
set "OS=Unknown"
for /f "tokens=* usebackq" %%i in (`ver`) do set "VER_OUT=%%i"
echo !VER_OUT! | findstr /i "Windows" >nul 2>&1 && (
    set "OS=Windows"
    goto :eof
)
echo !VER_OUT! | findstr /i "Darwin" >nul 2>&1 && (
    set "OS=macOS"
    goto :eof
)
echo !VER_OUT! | findstr /i "Linux" >nul 2>&1 && (
    set "OS=Linux"
    goto :eof
)
goto :eof
''',
            'check_python': '''
:check_python
set "PYTHON_CMD="
where python.exe >nul 2>&1 && set "PYTHON_CMD=python.exe"
if "!PYTHON_CMD!"=="" (
    where python3.exe >nul 2>&1 && set "PYTHON_CMD=python3.exe"
)
if "!PYTHON_CMD!"=="" (
    echo Error: Python is not installed!
    echo Please install Python 3.8+ before proceeding.
    exit /b 1
)

for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.major)"`) do set "MAJOR=%%i"
for /f "tokens=* usebackq" %%i in (`!PYTHON_CMD! -c "import sys; print(sys.version_info.minor)"`) do set "MINOR=%%i"

if "!MAJOR!" lss "3" (
    echo Error: Python 3.8+ is required.
    exit /b 1
) else if "!MAJOR!" equ "3" (
    if "!MINOR!" lss "8" (
        echo Error: Python 3.8+ is required.
        exit /b 1
    )
)
goto :eof
''',
            'check_prerequisites': '''
:check_prerequisites
call :detect_os
if "!OS!"=="Windows" (
    echo Checking Windows prerequisites...
    where winget.exe >nul 2>&1 || (
        echo Installing winget...
        powershell -Command "Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
        where winget.exe >nul 2>&1 || (
            echo Failed to install winget. Please install it manually from the Microsoft Store.
            exit /b 1
        )
    )
) else if "!OS!"=="macOS" (
    echo Checking macOS prerequisites...
    where brew.exe >nul 2>&1 || (
        echo Homebrew is required but not installed.
        echo Please install Homebrew first: https://brew.sh
        exit /b 1
    )
) else if "!OS!"=="Linux" (
    echo Checking Linux prerequisites...
    where curl.exe >nul 2>&1 || (
        echo Installing curl...
        where apt-get.exe >nul 2>&1 && (
            apt-get update && apt-get install -y curl
        ) || (
            where yum.exe >nul 2>&1 && (
                yum install -y curl
            ) || (
                echo Could not install curl. Please install it manually.
                exit /b 1
            )
        )
    )
)
goto :eof
''',
            'install_uv': '''
:install_uv
echo Installing uv package manager...
if "!OS!"=="Windows" (
    winget install --id=astral-sh.uv -e
) else if "!OS!"=="macOS" (
    brew install uv
) else if "!OS!"=="Linux" (
    curl -LsSf https://astral.sh/uv/install.sh | sh
) else (
    echo Unsupported operating system: !OS!
    exit /b 1
)

where uv.exe >nul 2>&1 || (
    echo Failed to install uv package manager!
    exit /b 1
)

echo Installation complete!
echo You can now run: uv run watcher.py
goto :eof
'''
        }

    def convert_function(self, func_name: str, content: str) -> str:
        """Convert a shell function to a batch label."""
        if func_name in self.function_templates:
            return self.function_templates[func_name]
        
        # Convert the function content
        converted = self._convert_lines(content.split('\n'))
        return f":{func_name}\n{converted}\ngoto :eof\n"

    def _convert_lines(self, lines: List[str]) -> str:
        """Convert shell script lines to batch script lines."""
        converted_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Replace known commands
            for shell_cmd, batch_cmd in self.command_map.items():
                line = line.replace(shell_cmd, batch_cmd)

            # Apply patterns
            for pattern, replacement in self.patterns.items():
                line = re.sub(pattern, replacement, line)

            converted_lines.append(line)

        return '\n'.join(converted_lines)

    def convert_script(self, shell_script: str) -> str:
        """Convert a shell script to a batch script."""
        # Start with initialization
        batch_lines = ['@echo off', 'setlocal enabledelayedexpansion', '']

        # Add function templates
        for func_name, template in self.function_templates.items():
            batch_lines.append(template)

        # Add main section
        batch_lines.append('\n:main')
        batch_lines.append('call :detect_os')
        batch_lines.append('call :check_prerequisites')
        batch_lines.append('call :check_python')
        batch_lines.append('call :install_uv')
        batch_lines.append('exit /b %ERRORLEVEL%')

        # Run main
        batch_lines.append('\n:start')
        batch_lines.append('call :main')
        batch_lines.append('exit /b %ERRORLEVEL%')

        return '\n'.join(batch_lines)

    def convert_file(self, shell_path: Path, batch_path: Optional[Path] = None) -> Path:
        """Convert a shell script file to a batch script file."""
        if not shell_path.exists():
            raise FileNotFoundError(f"Shell script not found: {shell_path}")

        if batch_path is None:
            batch_path = shell_path.parent / f"{shell_path.stem}.bat"

        shell_content = shell_path.read_text(encoding='utf-8')
        batch_content = self.convert_script(shell_content)
        batch_path.write_text(batch_content, encoding='utf-8')

        return batch_path

def main():
    """Test the converter."""
    print("Starting script converter...")
    converter = ScriptConverter()
    script_dir = Path(__file__).parent.parent
    shell_path = script_dir / 'install.sh'
    batch_path = script_dir / 'release' / 'erasmus_v0.0.1.bat'

    print(f"Script dir: {script_dir}")
    print(f"Shell path: {shell_path}")
    print(f"Batch path: {batch_path}")

    try:
        if not shell_path.exists():
            print(f"Shell script not found at: {shell_path}")
            return 1

        print("Converting shell script...")
        output_path = converter.convert_file(shell_path, batch_path)
        print(f"Successfully converted script to: {output_path}")
        return 0
    except Exception as e:
        print(f"Error converting script: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    main()
