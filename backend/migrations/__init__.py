"""
数据库迁移工具
"""
import psycopg2
from pathlib import Path
from typing import List


class MigrationRunner:
    """迁移执行器"""

    def __init__(self, db_url: str, migrations_dir: str = None):
        self.db_url = db_url
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent
        self.migrations_dir = Path(migrations_dir)

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)

    def get_applied_migrations(self, conn) -> set:
        """获取已应用的迁移"""
        cursor = conn.cursor()

        # 确保迁移记录表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("SELECT name FROM _migrations")
        return {row[0] for row in cursor.fetchall()}

    def get_pending_migrations(self) -> List[Path]:
        """获取待执行的迁移文件"""
        if not self.migrations_dir.exists():
            return []

        migrations = []
        for file in sorted(self.migrations_dir.glob("*.py")):
            if file.name.startswith("migrate_") and file.name != "__init__.py":
                migrations.append(file)

        return migrations

    def apply_migration(self, conn, migration_file: Path):
        """执行单个迁移"""
        module_name = migration_file.stem

        # 动态导入迁移模块
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 执行迁移
        if hasattr(module, 'run_migration'):
            module.run_migration()

        # 记录迁移
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO _migrations (name) VALUES (%s)",
            (module_name,)
        )
        conn.commit()

        print(f"[SUCCESS] ✓ {module_name}")

    def run(self):
        """执行所有待执行的迁移"""
        print("[INFO] 开始检查数据库迁移...")

        conn = self.get_connection()
        try:
            applied = self.get_applied_migrations(conn)
            pending = self.get_pending_migrations()

            if not pending:
                print("[INFO] 没有待执行的迁移")
                return True

            # 过滤已应用的迁移
            pending = [m for m in pending if m.stem not in applied]

            if not pending:
                print("[INFO] 所有迁移都已应用")
                return True

            print(f"[INFO] 发现 {len(pending)} 个待执行的迁移：")

            for migration_file in pending:
                print(f"  - {migration_file.stem}")

            print("\n[INFO] 开始执行迁移...")

            for migration_file in pending:
                self.apply_migration(conn, migration_file)

            print(f"\n[SUCCESS] 所有迁移执行完成！")
            return True

        except Exception as e:
            print(f"\n[ERROR] 迁移执行失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


def main():
    """主函数"""
    import sys

    # 默认数据库配置
    db_url = "postgresql://postgres:postgres@localhost:5432/interview_db"

    # 如果有命令行参数，使用第一个参数作为数据库 URL
    if len(sys.argv) > 1:
        db_url = sys.argv[1]

    runner = MigrationRunner(db_url)
    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
