import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict

from aiologger import Logger  # type: ignore
from aiologger.formatters.base import Formatter  # type: ignore
from aiologger.handlers.streams import AsyncStreamHandler  # type: ignore
from aiologger.levels import LogLevel  # type: ignore
from aiologger.records import LogRecord  # type: ignore

from app.core.config.settings import settings


class AsyncJSONFormatter(Formatter):
    """Custom JSON formatter for structured logging."""

    def format_exception(
        self,
        exc_info: tuple,
    ) -> str:
        """Format exception info as a string."""
        return "".join(traceback.format_exception(*exc_info))

    def format(
        self,
        record: LogRecord,
    ) -> str:
        """Format log record as JSON string."""
        record.message = record.msg % record.args if record.args else record.msg

        # Base log record attributes
        log_object: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.message,
            "module": record.module,
            "function": getattr(record, "funcName", None),
            "line": record.lineno,
        }

        # Add request_id if available
        if hasattr(record, "request_id"):
            log_object["request_id"] = record.request_id

        # Add extra fields if available
        if hasattr(record, "extra"):
            log_object.update(record.extra)

        # Add exception info if available
        if record.exc_info:
            log_object["exception"] = self.format_exception(record.exc_info)

        return json.dumps(log_object)


def setup_async_logging() -> Logger:
    """Configure async application logging."""
    # Create async logger
    logger = Logger(
        name="app_logger",
        level=LogLevel.DEBUG if settings.app.debug else LogLevel.INFO,
    )

    # Create async console handler
    console_handler = AsyncStreamHandler(
        stream=sys.stdout,
    )
    console_handler.formatter = AsyncJSONFormatter()
    logger.add_handler(console_handler)

    return logger


class AioHandler(logging.Handler):
    def __init__(
        self,
        aio_logger: Logger,
    ):
        super().__init__()
        self.aio_logger = aio_logger

    async def emit_async(
        self,
        logger: Logger,
        record: LogRecord,
    ) -> None:
        await logger.handle(record)

    def emit(
        self,
        record: LogRecord,
    ) -> None:
        if record.name == self.aio_logger.name:
            return

        try:
            asyncio.get_running_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(self.emit_async(self.aio_logger, record))
            )
        except Exception:
            self.handleError(record)


def patch_uvicorn_loggers(
    aio_logger: Logger,
) -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []  # очищаем стандартные хендлеры
        logger.propagate = False  # важно
        logger.addHandler(AioHandler(aio_logger))
        logger.setLevel(logging.INFO)
