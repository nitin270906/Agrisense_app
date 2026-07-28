@echo off
title AGRISENSE — Starting...
color 0A
cd /d "%~dp0"

echo.
echo  ================================================
echo    AGRISENSE  ^|  AI Salinity Intelligence
echo    UNDP Climate Hackathon
echo  ================================================
echo.

REM ── 1. PYTHON ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERROR] Python not found.
    echo.
    echo  Install Python 3.11+ from:  https://www.python.org/downloads/
    echo  IMPORTANT: tick "Add Python to PATH" during install.
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [OK] %PY_VER%

REM ── 2. VIRTUAL ENVIRONMENT ─────────────────────────────────────────────────
if not exist "backend\.venv\Scripts\activate.bat" (
    echo  [..] Creating Python environment ^(one-time, ~30s^)...
    python -m venv backend\.venv
    if %errorlevel% neq 0 ( color 0C & echo  [ERROR] Could not create venv. & pause & exit /b 1 )
    echo  [OK] Environment created.
) else (
    echo  [OK] Python environment ready.
)

call backend\.venv\Scripts\activate.bat

REM ── 3. PYTHON PACKAGES ─────────────────────────────────────────────────────
REM  Check if FastAPI is installed as a proxy for "packages are present"
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [..] Installing Python packages ^(one-time, ~2-4 min^)...
    pip install --upgrade pip --quiet
    pip install -r backend\requirements.txt
    if %errorlevel% neq 0 ( color 0C & echo  [ERROR] pip install failed. Check internet. & pause & exit /b 1 )
    echo  [OK] Packages installed.
) else (
    echo  [OK] Python packages present.
)

REM ── 4. DATABASE ────────────────────────────────────────────────────────────
if not exist "backend\salinity.db" (
    echo  [..] Seeding demo database ^(one-time, ~30s^)...
    cd backend
    python -m app.seed.seed
    if %errorlevel% neq 0 ( color 0C & echo  [ERROR] Seed failed. & pause & exit /b 1 )
    cd ..
    echo  [OK] Database seeded.
) else (
    echo  [OK] Database found.
)

REM ── 5. FRONTEND BUILD ──────────────────────────────────────────────────────
if not exist "frontend\dist\index.html" (
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        color 0C
        echo  [ERROR] frontend\dist\ is missing and Node.js is not installed.
        echo.
        echo  Either:
        echo    A) Copy frontend\dist\ from the source machine  ^(no Node needed^)
        echo    B) Install Node.js 20 LTS from https://nodejs.org  then re-run go.bat
        echo.
        pause & exit /b 1
    )
    echo  [..] Building frontend ^(one-time, ~1-2 min^)...
    cd frontend
    npm ci --silent
    npm run build
    if %errorlevel% neq 0 ( color 0C & echo  [ERROR] Frontend build failed. & pause & exit /b 1 )
    cd ..
    echo  [OK] Frontend built.
) else (
    echo  [OK] Frontend build present.
)

REM ── 6. LAUNCH ──────────────────────────────────────────────────────────────
echo.
echo  ================================================
echo   All checks passed — launching servers...
echo  ================================================
echo.
echo   Frontend (UI):   http://localhost:5173
echo   Backend (API):  http://127.0.0.1:8000
echo   API Docs:      http://127.0.0.1:8000/docs
echo.
echo   Press Ctrl+C to stop.
echo  ------------------------------------------------
echo.

REM  Open the browser asynchronously after 7 seconds when servers are listening
start /b "" cmd /c "ping 127.0.0.1 -n 8 >nul & start http://localhost:5173"

REM  Start Vite dev server in background
start /b "" cmd /c "cd frontend && npm run dev"

cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  Server stopped.
pause