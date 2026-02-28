#!/bin/bash
# 数据库迁移脚本

echo "[INFO] 正在执行数据库迁移..."

python -m backend.migrations "$@"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] 迁移完成！"
else
    echo "[ERROR] 迁移失败，请查看错误信息"
    exit 1
fi
