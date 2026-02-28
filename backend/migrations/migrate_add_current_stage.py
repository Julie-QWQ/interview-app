"""
数据库迁移脚本：添加 current_stage 字段
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from pathlib import Path


def run_migration():
    """执行迁移"""
    # 数据库连接配置
    db_config = "postgresql://postgres:postgres@localhost:5432/interview_db"

    print("[INFO] 开始数据库迁移：添加 current_stage 字段")

    try:
        # 连接数据库
        conn = psycopg2.connect(db_config)
        cursor = conn.cursor()

        # 读取 SQL 文件
        sql_file = Path(__file__).parent / "add_current_stage.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        # 执行 SQL
        cursor.execute(sql)
        conn.commit()

        print("[SUCCESS] current_stage 字段添加成功！")

        # 验证
        cursor.execute("SELECT column_name FROM information_schema.columns "
                      "WHERE table_name='interviews' AND column_name='current_stage'")
        result = cursor.fetchone()

        if result:
            print("[SUCCESS] 验证通过：current_stage 字段已存在")
        else:
            print("[ERROR] 验证失败：current_stage 字段不存在")
            return False

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
