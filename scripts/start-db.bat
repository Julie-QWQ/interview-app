@echo off
REM AI Interview System - PostgreSQL Database Startup Script (Windows)

echo ========================================
echo   Starting PostgreSQL Database
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    goto :error
)

REM Start database container
echo [INFO] Starting container...
docker-compose up -d

echo.
echo [INFO] Waiting for database to be ready...
timeout /t 3 /nobreak >nul

REM Check container status
docker ps | findstr "interview-postgres" >nul
if not errorlevel 1 (
    echo.
    echo ========================================
    echo   PostgreSQL Database Started Successfully!
    echo ========================================
    echo.
    echo Connection Info:
    echo   Host: localhost
    echo   Port: 5432
    echo   Database: interview_db
    echo   Username: postgres
    echo   Password: postgres
    echo.
    echo Common Commands:
    echo   View logs: docker-compose logs postgres
    echo   Stop database: docker-compose down
    echo   Restart: docker-compose restart
    echo.
    goto :end
) else (
    echo.
    echo [ERROR] Database failed to start
    echo Check logs: docker-compose logs postgres
    goto :error
)

:error
    exit /b 1

:end
