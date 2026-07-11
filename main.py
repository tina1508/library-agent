"""
Library AI Agent — Application Entry Point
Also exposes create_app() at module level for gunicorn / wsgi.
"""

import sys
import os
import logging

# Ensure the project root is on sys.path regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("library-agent")

# Re-export create_app for gunicorn ("main:create_app()")
from api.app import create_app  # noqa: E402


def main():
    from config import app_config

    app = create_app()

    logger.info("=" * 55)
    logger.info("  Library AI Agent — IBM watsonx.ai Studio")
    logger.info("=" * 55)
    logger.info("  Demo mode : %s", app_config.use_demo_mode)
    logger.info("  watsonx.ai: %s", app_config.use_watsonx)
    logger.info("  Host      : http://%s:%d", app_config.host, app_config.port)
    logger.info("=" * 55)

    app.run(
        host=app_config.host,
        port=app_config.port,
        debug=app_config.debug,
    )


if __name__ == "__main__":
    main()
