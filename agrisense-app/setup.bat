@echo off
title SaltWatch — First-Time Setup
color 0B

echo.
echo  ============================================
echo   SaltWatch First-Time Setup
echo  ============================================
echo.

REM ── Locate the project root ────────────────────────────────────────────────
cd /d "%~dp0"
set PROJECT_ROOT=%cd%

REM ═══════════════════════════════════════════════════════════════════════════
REM  1. CHECK PREREQUISITES
REM ═══════════════════════════════════════════════════════════════════════════

echo  [1/5] Checking prerequisites...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Download Python 3.11 or newer from:
    echo      https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During install, tick "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [OK] %PY_VER%

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Node.js is not installed or not in PATH.
    echo.
    echo  Download Node.js 20 LTS from:
    echo      https://nodejs.org/en/download
    echo.
    echo  After installing, close and reopen this window, then run setup.bat again.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VER=%%i
echo  [OK] Node.js %NODE_VER%

echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM  2. CREATE PYTHON VIRTUAL ENVIRONMENT
REM ═══════════════════════════════════════════════════════════════════════════

echo  [2/5] Setting up Python virtual environment...
echo.

cd backend

if exist ".venv\Scripts\activate.bat" (
    echo  [SKIP] Virtual environment already exists.
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created at backend\.venv
)

call .venv\Scripts\activate.bat
echo  [OK] Environment activated.
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM  3. INSTALL PYTHON PACKAGES
REM ═══════════════════════════════════════════════════════════════════════════

echo  [3/5] Installing Python packages (may take 2-4 minutes)...
echo.

pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  [ERROR] pip install failed. Check your internet connection and try again.
    pause
    exit /b 1
)
echo.
echo  [OK] Python packages installed.
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM  4. DATABASE — SEED IF MISSING
REM ═══════════════════════════════════════════════════════════════════════════

echo  [4/5] Checking database...
echo.

if exist "salinity.db" (
    echo  [OK] Database found — pre-seeded data will be used.
    echo       (3 farms, 9 fields, 150 days of sensor history ready)
) else (
    echo  [INFO] Database not found. Running seed script to generate demo data...
    echo         This takes about 30 seconds...
    echo.
    python -m app.seed.seed
    if %errorlevel% neq 0 (
        echo  [ERROR] Seed script failed.
        pause
        exit /b 1
    )
    echo  [OK] Database seeded with demo data.
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM  5. BUILD FRONTEND
REM ═══════════════════════════════════════════════════════════════════════════

echo  [5/5] Checking frontend build...
echo.

cd "%PROJECT_ROOT%\frontend"

if exist "dist\index.html" (
    echo  [OK] Pre-built frontend found — no build step needed.
    echo       (The built UI is bundled with the project)
) else (
    echo  [INFO] Building frontend (requires internet for package install)...
    echo         This takes about 1-2 minutes...
    echo.
    npm ci
    if %errorlevel% neq 0 (
        echo  [ERROR] npm ci failed. Check your internet connection.
        pause
        exit /b 1
    )
    npm run build
    if %errorlevel% neq 0 (
        echo  [ERROR] Frontend build failed. See errors above.
        pause
        exit /b 1
    )
    echo  [OK] Frontend built successfully.
)

echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM  DONE
REM ═══════════════════════════════════════════════════════════════════════════

echo  ============================================
echo   Setup complete!
echo  ============================================
echo.
echo  To start the demo:
echo.
echo      Double-click  start_demo.bat
echo.
echo  Or from this terminal:
echo.
echo      cd backend
echo      .venv\Scripts\activate
echo      python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo  Then open: http://localhost:8000
echo.
pause
