@echo off

:: Color codes for output
setlocal enabledelayedexpansion

:RED
echo.%%RED%%Error: %%NC%%
goto :error

:GREEN
echo.%%GREEN%%Installation complete!%%NC%%
goto :end

:YELLOW
echo.%%YELLOW%%Installing uv package manager...%%NC%%

:error
echo.
echo.
echo.
echo.
exit /b 1

:end
echo.
echo You can now run the watcher script directly using:
echo uv run watcher.py