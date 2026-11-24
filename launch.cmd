@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%~dp0launch.py" %*
    if %ERRORLEVEL%==0 exit /b 0
    pause
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0launch.py" %*
    if %ERRORLEVEL%==0 exit /b 0
    pause
    exit /b %ERRORLEVEL%
)

echo Python 3.11+ was not found.
echo Install it from https://www.python.org/downloads/
pause
exit /b 1
