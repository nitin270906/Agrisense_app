@echo off
title AGRISENSE — AI Salinity & Crop Stress Forecaster
color 0A

echo.
echo  ============================================
echo   AGRISENSE  ^|  AI Salinity Intelligence
echo   UNDP Climate Hackathon Demo
echo  ============================================
echo.

REM ── Locate the project root (same folder as this .bat) ─────────────────────
cd /d "%~dp0"

REM ── Verify virtual environment exists ──────────────────────────────────────
if not exist "backend\.venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo.
    echo  Run setup.bat first, then try again.
    echo.
    pause
    exit /b 1
)

REM ── Verify database exists ─────────────────────────────────────────────────
if not exist "backend\salinity.db" (
    echo  [ERROR] Database not found: backend\salinity.db
    echo.
    echo  The pre-seeded database was not copied with the project.
    echo  Run setup.bat to create a fresh database and seed demo data.
    echo.
    pause
    exit /b 1
)

REM ── Activate environment and start ─────────────────────────────────────────
echo  Activating Python environment...
call backend\.venv\Scripts\activate.bat

echo  Starting backend server...
echo.
echo  App will be available at:
echo.
echo      http://localhost:8000       ^<-- open this in Chrome
echo      http://localhost:8000/docs  ^<-- API explorer
echo.
echo  Press Ctrl+C to stop the server.
echo  ─────────────────────────────────────────────────────────────
echo.

REM Open browser asynchronously after 7 seconds when server is listening
start /b "" cmd /c "ping 127.0.0.1 -n 8 >nul & start http://127.0.0.1:8000"

REM Start the backend from the backend\ directory
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  Server stopped.
pause
