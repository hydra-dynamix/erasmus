@echo off
setlocal enabledelayedexpansion


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


:setup_env
echo Creating environment files...

:: Create .env.example
(
echo IDE_ENV=
echo GIT_TOKEN=
echo OPENAI_API_KEY=
) > .env.example

:: Prompt for IDE environment
echo Please enter your IDE environment (cursor/windsurf):
set /p "IDE_ENV="

:: Create .env
(
echo IDE_ENV=!IDE_ENV!
echo GIT_TOKEN=
echo OPENAI_API_KEY=
) > .env

echo Environment files created successfully
goto :eof


:init_watcher
echo Initializing watcher...

:: Check for compressed watcher script
if exist watcher.py.gz (
    echo Extracting watcher script...
    powershell -Command "Expand-Archive -Path watcher.py.gz -DestinationPath ."
)

:: Run watcher setup
if exist watcher.py (
    uv run watcher.py
) else (
    echo Error: watcher.py not found
    exit /b 1
)
goto :eof


:main
call :detect_os
call :check_prerequisites
call :check_python
call :install_uv
call :setup_env
call :init_watcher
echo Installation complete!
echo Watcher has been initialized with your IDE environment: !IDE_ENV!
exit /b %ERRORLEVEL%

:start
call :main
exit /b %ERRORLEVEL%