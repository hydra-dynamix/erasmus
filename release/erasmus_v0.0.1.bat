@echo off

:: Color codes for output
setlocal enabledelayedexpansion

:RED= (echo) & set "color[0;31m"
:GREEN= (echo) & set "color[0;32m"
:YELLOW= (echo) & set "color[1;33m"
:NC= (echo) & set "color[0m"

:: Detect operating system
set OS=
for /f "delims=" %%a in ('wmic os get osversion ^| findstr /r /c:"^"') do (
    if "%%a" == "10.0" set OS=Windows
    else if "%%a" == "11.0" set OS=Windows 11
    else if "%%a" == "12.0" set OS=Windows 12
)

:: Check if Python is installed
set PYTHON_CMD=
for /f "delims=" %%a in ('where python3 ^| findstr /r /c:"^"') do (
    set PYTHON_CMD=python3
)
if not exist "%PYTHON_CMD%" (
    for /f "delims=" %%a in ('where python ^| findstr /r /c:"^"') do (
        set PYTHON_CMD=python
    )
)

:: Verify Python version
set PYTHON_VERSION=%PYTHON_CMD% -c 'import sys; echo %sys.version_info.major%.%sys.version_info.minor%'
set MAJOR=%PYTHON_VERSION:~0,1%
set MINOR=%PYTHON_VERSION:~3,1%

if "%MAJOR%" equ 2 (
    if "%MINOR%" leq 7 (
        echo Error: Python 3.8+ is required. Current version: %PYTHON_VERSION%
        exit /b 1
    )
)

:: Install uv package manager
echo Installing uv package manager...
if exist "pip" (
    pip install uv
) else if exist "pip3" (
    pip3 install uv
) else (
    "%PYTHON_CMD%" -m ensurepip --upgrade
    "%PYTHON_CMD%" -m pip install uv
)

:: Verify uv installation
if not exist "uv" (
    echo Failed to install uv package manager!
    exit /b 1
)

:: Main installation process
echo Detected OS: %OS%
echo Installation complete!
echo You can now run the watcher script directly using:
echo uv run watcher.py