"""
Logging configuration for BlendX Core.

Configures application-wide logging using settings from the environment. Provides a setup_logging function to initialize logging handlers and formatters for both console and file output.
"""

import logging
import logging.config

from app.config.settings import get_settings


def setup_logging():
    """Set up logging configuration for the application using environment settings."""
    settings = get_settings()
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": settings.log_level,
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "standard",
                "level": settings.log_level,
                "filename": "app.log",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": settings.log_level,
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file"],
                "level": settings.log_level,
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(logging_config)


setup_logging()

logger = logging.getLogger("app")
