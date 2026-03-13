"""ASGI entrypoint for the interview service."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from config.settings import settings


def setup_logging() -> None:
    """Configure application logging."""
    log_level = settings.get("logging.level", "INFO")
    log_format = settings.get(
        "logging.format",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/app.log", encoding="utf-8"),
        ],
    )


setup_logging()
app = create_app()


def main() -> None:
    """Run the development ASGI server."""
    logger = logging.getLogger(__name__)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Listening on %s:%s", settings.host, settings.port)
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
