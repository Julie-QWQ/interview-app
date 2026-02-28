"""
创建 prompt_configs 表的迁移脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_cursor

print("[INFO] 开始迁移：创建 prompt_configs 表")

try:
    with get_db_cursor() as cur:
        # 创建表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prompt_configs (
                id SERIAL PRIMARY KEY,
                config_type VARCHAR(50) UNIQUE NOT NULL,
                config_data JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("[SUCCESS] prompt_configs 表创建成功")

except Exception as e:
    print(f"[ERROR] 迁移失败: {e}")
    sys.exit(1)
