import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class SafeLogFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self.secrets = [value for value in secrets if value]

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "***")
        record.msg = message
        record.args = ()
        return True


def setup_logging() -> None:
    """Configure console and rotating file logging for the bot."""
    log_level = logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(name)s [rid=%(request_id)s]: %(message)s"

    handlers = [logging.StreamHandler()]

    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    file_path = os.path.join(logs_dir, "bot.log")

    file_handler = RotatingFileHandler(
        file_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handlers.append(file_handler)

    filter_instance = SafeLogFilter(
        [os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("OPENAI_API_KEY", "")]
    )
    for handler in handlers:
        handler.addFilter(filter_instance)

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


__all__ = ["setup_logging", "request_id_var"]
