@echo off
REM AI Interview System - PostgreSQL Database Stop Script (Windows)

echo ========================================
echo   Stopping PostgreSQL Database
echo ========================================
echo.

REM Stop and remove container
docker-compose down

echo.
echo [SUCCESS] Database stopped
echo.
echo To restart, run: scripts\start-db.bat
echo.
