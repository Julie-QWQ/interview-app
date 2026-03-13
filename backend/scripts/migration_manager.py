#!/usr/bin/env python3
"""CLI wrapper for database bootstrap and migrations."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.db.migrations import get_migration_status, run_startup_migrations
from config.settings import settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    command = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    database_url = settings.database_url

    if command == "migrate":
        run_startup_migrations(database_url)
        print("Database migrations are up to date.")
        return

    if command == "status":
        applied, pending = get_migration_status(database_url)
        print(f"Applied migrations: {len(applied)}")
        for version in applied:
            print(f"  - {version}")
        print(f"Pending migrations: {len(pending)}")
        for version in pending:
            print(f"  - {version}")
        return

    raise SystemExit(f"Unsupported command: {command}. Use 'migrate' or 'status'.")


if __name__ == "__main__":
    main()
