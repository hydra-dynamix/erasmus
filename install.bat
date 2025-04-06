@echo off
setlocal enabledelayedexpansion

:: Universal Installer for Watcher Project
:: Supports Windows environments

:: Color codes for output
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set NC=[0m

:: Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED%Error: Python is not installed!%NC%
    echo Please install Python 3.8+ before proceeding.
    exit /b 1
)

:: Verify Python version
for /f "tokens=*" %%a in ('python -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")"') do set PYTHON_VERSION=%%a
for /f "tokens=1 delims=." %%a in ("%PYTHON_VERSION%") do set MAJOR=%%a
for /f "tokens=2 delims=." %%a in ("%PYTHON_VERSION%") do set MINOR=%%a

if %MAJOR% lss 3 (
    echo %RED%Error: Python 3.8+ is required. Current version: %PYTHON_VERSION%%NC%
    exit /b 1
)
if %MAJOR% equ 3 if %MINOR% lss 8 (
    echo %RED%Error: Python 3.8+ is required. Current version: %PYTHON_VERSION%%NC%
    exit /b 1
)

:: Install uv package manager
echo %YELLOW%Installing uv package manager...%NC%
python -m pip install uv

:: Verify uv installation
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED%Failed to install uv package manager!%NC%
    exit /b 1
)

:: Completion message
echo %GREEN%Installation complete!%NC%
echo You can now run the watcher script directly using:
echo uv run watcher.py

exit /b 0
