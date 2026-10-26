@echo off
title Cheer Sagar - Dhruvika Store
cd /d "%~dp0backend"

echo ====================================================
echo           CHEER SAGAR - DHRUVIKA STORE
echo ====================================================
echo.

rem Check for Python executable (prefer python, then py)
set "PY_CMD="
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python not found on your system!
    echo Please install Python 3.10+ from https://python.org and make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

rem Create virtual environment if missing
if not exist .venv\Scripts\activate.bat (
    echo [INFO] Setting up virtual environment...
    %PY_CMD% -m venv --system-site-packages .venv
)

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

rem Check/Install requirements
echo [INFO] Verifying packages...
python -m pip install -r requirements.txt --quiet --no-warn-script-location 2>nul

echo.
echo ====================================================
echo   Cheer Sagar Store is running!
echo   Open in browser: http://127.0.0.1:8000
echo ====================================================
echo.

rem Launch browser automatically
start "" http://127.0.0.1:8000

rem Start FastAPI Uvicorn Server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped.
pause

