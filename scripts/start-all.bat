@echo off
REM AI Interview System - One-Click Startup Script (Windows)

echo ========================================
echo   AI Interview System - Startup
echo ========================================
echo.

REM 1. Start database
echo [1/3] Starting database...
call scripts\start-db.bat
if errorlevel 1 (
    echo [ERROR] Database startup failed
    goto :error
)

echo.
echo [INFO] Waiting for database to be fully ready...
timeout /t 5 /nobreak >nul

REM 2. Start backend
echo.
echo [2/3] Starting backend service...
cd backend

REM Check if .venv exists, if not create it
if not exist ".venv" (
    echo [INFO] Creating virtual environment with uv...
    uv venv
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

if not exist ".env" (
    echo [WARNING] .env file not found
    echo   Copy .env.example to .env and configure it
    echo   Command: copy .env.example .env
    echo.
)

echo [INFO] Installing dependencies with uv...
uv pip install -r requirements.txt

echo [INFO] Starting backend service (port 8000)...
start "AI Interview System - Backend" cmd /k "cd /d %CD% && .venv\Scripts\python.exe main.py"
cd ..

echo [SUCCESS] Backend service started

REM 3. Start frontend
echo.
echo [3/3] Starting frontend service...
cd frontend

if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    call npm install
)

echo [INFO] Starting frontend dev server (port 5173)...
start "AI Interview System - Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo   All Services Started Successfully!
echo ========================================
echo.
echo Access URLs:
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo Tips: Close windows to stop corresponding services
echo ========================================
echo.
goto :end

:error
    exit /b 1

:end
