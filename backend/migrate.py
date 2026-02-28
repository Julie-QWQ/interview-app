"""
数据库迁移脚本 - 添加 current_stage 字段
使用 Flask app 上下文执行
"""
import sys
import os

# 设置环境变量
os.environ.setdefault('FLASK_ENV', 'development')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db_cursor
import logging

logger = logging.getLogger(__name__)


def migrate_add_current_stage():
    """添加 current_stage 字段"""
    print("[INFO] 开始迁移：添加 current_stage 字段到 interviews 表")

    try:
        with get_db_cursor() as cur:
            # 检查字段是否已存在
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='interviews' AND column_name='current_stage'
            """)

            if cur.fetchone():
                print("[INFO] current_stage 字段已存在，跳过迁移")
                return True

            # 添加字段
            cur.execute("""
                ALTER TABLE interviews
                ADD COLUMN current_stage VARCHAR(50) DEFAULT 'welcome'
            """)
            print("[SUCCESS] current_stage 字段添加成功")

            # 为现有记录设置默认值
            cur.execute("""
                UPDATE interviews
                SET current_stage = 'welcome'
                WHERE current_stage IS NULL
            """)
            print("[SUCCESS] 现有记录已更新")

            # 创建索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_interviews_current_stage
                ON interviews(current_stage)
            """)
            print("[SUCCESS] 索引创建成功")

        print("\n[SUCCESS] 迁移完成！")
        return True

    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("数据库迁移工具")
    print("=" * 50)
    print()

    success = migrate_add_current_stage()

    print()
    print("=" * 50)
    if success:
        print("[SUCCESS] 所有迁移执行成功！")
        return 0
    else:
        print("[ERROR] 迁移执行失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
