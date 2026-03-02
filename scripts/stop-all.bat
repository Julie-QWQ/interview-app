@echo off
REM 停止所有服务

echo ========================================
echo   停止所有服务
echo ========================================
echo.

echo [1/2] 停止后端服务...
taskkill /FI "WINDOWTITLE eq AI Interview System - Backend*" /F 2>nul
if errorlevel 1 (
    echo [INFO] 后端服务未运行或已停止
) else (
    echo [SUCCESS] 后端服务已停止
)

echo.
echo [2/2] 停止前端服务...
taskkill /FI "WINDOWTITLE eq AI Interview System - Frontend*" /F 2>nul
if errorlevel 1 (
    echo [INFO] 前端服务未运行或已停止
) else (
    echo [SUCCESS] 前端服务已停止
)

echo.
echo [INFO] 清理可能残留的 Python 进程...
taskkill /F /IM python.exe /FI "USERNAME eq %USERNAME%" 2>nul
if errorlevel 1 (
    echo [INFO] 没有残留的 Python 进程
) else (
    echo [SUCCESS] 已清理残留的 Python 进程
)

echo.
echo ========================================
echo   所有服务已停止
echo ========================================
echo.
timeout /t 2 /nobreak >nul
