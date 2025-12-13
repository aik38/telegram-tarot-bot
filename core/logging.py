import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Configure console and rotating file logging for the bot."""
    log_level = logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [logging.StreamHandler()]

    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    file_path = os.path.join(logs_dir, "bot.log")

    file_handler = RotatingFileHandler(
        file_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handlers.append(file_handler)

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


__all__ = ["setup_logging"]
