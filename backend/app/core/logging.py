import logging
from typing import Any

logger = logging.getLogger(__name__)


class Logger:
    """Wrapper for structured logging."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str, **kwargs):
        """Log info message with optional context."""
        self.logger.info(f"{message} {kwargs}" if kwargs else message)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context."""
        self.logger.warning(f"{message} {kwargs}" if kwargs else message)

    def error(self, message: str, **kwargs):
        """Log error message with optional context."""
        self.logger.error(f"{message} {kwargs}" if kwargs else message)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context."""
        self.logger.debug(f"{message} {kwargs}" if kwargs else message)


def get_logger(name: str) -> Logger:
    """Get a logger instance."""
    return Logger(name)
