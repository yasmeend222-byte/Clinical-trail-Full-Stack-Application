@echo off
setlocal
set "ROOT=%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3 and add it to PATH.
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js was not found. Install Node.js and add it to PATH.
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found. Install Node.js with npm and add it to PATH.
    exit /b 1
)

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
    echo Creating the backend Python environment...
    python -m venv "%ROOT%backend\.venv"
    if errorlevel 1 exit /b 1

    echo Installing backend packages...
    "%ROOT%backend\.venv\Scripts\python.exe" -m pip install -r "%ROOT%backend\requirements.txt"
    if errorlevel 1 exit /b 1
)

if not exist "%ROOT%frontend\node_modules" (
    echo Installing frontend packages...
    pushd "%ROOT%frontend"
    call npm ci
    if errorlevel 1 (
        popd
        exit /b 1
    )
    popd
)

start "ContextSync Backend" /D "%ROOT%backend" cmd /k ""%ROOT%backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000"
start "ContextSync Frontend" /D "%ROOT%frontend" cmd /k "npm.cmd run dev"

echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:5173
echo Login:    admin@contextsync.dev / admin123
