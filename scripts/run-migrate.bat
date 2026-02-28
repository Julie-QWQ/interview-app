@echo off
REM 数据库迁移脚本

echo [INFO] 正在执行数据库迁移...

cd /d "%~dp0.."
python scripts/migrate.py

if %errorlevel% equ 0 (
    echo [SUCCESS] 迁移完成！
) else (
    echo [ERROR] 迁移失败，请查看错误信息
)

pause
