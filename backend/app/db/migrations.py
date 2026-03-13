"""Database bootstrap and migration helpers."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import re
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import connection, cursor
from psycopg2 import sql

logger = logging.getLogger(__name__)

DEFAULT_MAINTENANCE_DB = "postgres"
MIGRATION_FILENAME_RE = re.compile(r"^\d+.*\.(sql|py)$")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _migrations_dir() -> Path:
    return _project_root() / "migrations"


def _maintenance_database_url(database_url: str) -> tuple[str, str]:
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise ValueError("Database URL must include a database name.")

    maintenance_path = f"/{DEFAULT_MAINTENANCE_DB}"
    maintenance_url = parsed._replace(path=maintenance_path).geturl()
    return maintenance_url, database_name


def _connect(database_url: str, *, autocommit: bool = False) -> connection:
    conn = psycopg2.connect(database_url)
    conn.autocommit = autocommit
    return conn


def ensure_database_exists(database_url: str) -> None:
    """Create the target database when it does not exist yet."""
    maintenance_url, database_name = _maintenance_database_url(database_url)

    with _connect(maintenance_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            if cur.fetchone():
                logger.info("Database %s already exists", database_name)
                return

            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            logger.info("Created database %s", database_name)


def ensure_schema_migrations_table(conn: connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            ALTER TABLE schema_migrations
            ALTER COLUMN version TYPE VARCHAR(255)
            """
        )
    conn.commit()


def get_applied_migrations(conn: connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def _iter_migration_files() -> Iterator[Path]:
    migrations_dir = _migrations_dir()
    if not migrations_dir.exists():
        return iter(())

    files = sorted(
        path
        for path in migrations_dir.iterdir()
        if path.is_file() and MIGRATION_FILENAME_RE.match(path.name)
    )
    return iter(files)


def _apply_sql_migration(cur: cursor, migration_file: Path) -> None:
    sql = migration_file.read_text(encoding="utf-8")
    cur.execute(sql)


def _apply_python_migration(cur: cursor, migration_file: Path) -> None:
    spec = importlib.util.spec_from_file_location(migration_file.stem, migration_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module: {migration_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    upgrade = getattr(module, "upgrade", None)
    if upgrade is None:
        raise RuntimeError(f"Python migration missing upgrade(): {migration_file}")
    upgrade(cur)


def apply_migration(conn: connection, migration_file: Path) -> None:
    description = migration_file.stem.replace("_", " ")
    logger.info("Applying migration %s", migration_file.name)

    with conn.cursor() as cur:
        if migration_file.suffix == ".sql":
            _apply_sql_migration(cur, migration_file)
        elif migration_file.suffix == ".py":
            _apply_python_migration(cur, migration_file)
        else:
            raise ValueError(f"Unsupported migration type: {migration_file}")

        cur.execute(
            """
            INSERT INTO schema_migrations (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING
            """,
            (migration_file.name, description),
        )

    conn.commit()
    logger.info("Applied migration %s", migration_file.name)


def run_startup_migrations(database_url: str) -> None:
    """Ensure database exists and all known migrations are applied."""
    ensure_database_exists(database_url)

    with _connect(database_url) as conn:
        ensure_schema_migrations_table(conn)
        applied = get_applied_migrations(conn)

        for migration_file in _iter_migration_files():
            if migration_file.name in applied:
                continue
            apply_migration(conn, migration_file)
            applied.add(migration_file.name)


def get_migration_status(database_url: str) -> tuple[list[str], list[str]]:
    ensure_database_exists(database_url)

    with _connect(database_url) as conn:
        ensure_schema_migrations_table(conn)
        applied = get_applied_migrations(conn)
        all_files = [path.name for path in _iter_migration_files()]
        pending = [name for name in all_files if name not in applied]
        return sorted(applied), pending


def main() -> None:
    parser = argparse.ArgumentParser(description="Database migration manager")
    parser.add_argument("command", choices=["migrate", "status"])
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.command == "migrate":
        run_startup_migrations(args.database_url)
        print("Database migrations are up to date.")
        return

    applied, pending = get_migration_status(args.database_url)
    print(f"Applied migrations: {len(applied)}")
    for version in applied:
        print(f"  - {version}")
    print(f"Pending migrations: {len(pending)}")
    for version in pending:
        print(f"  - {version}")


if __name__ == "__main__":
    main()
