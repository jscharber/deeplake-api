"""Logging configuration for the application."""

import logging
import sys
from typing import Dict, Any, Callable
import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging for the application."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if log_format == "json"
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("grpcio").setLevel(logging.WARNING)
    logging.getLogger("deeplake").setLevel(logging.INFO)


def get_logger(name: str) -> Any:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


class LoggingMixin:
    """Mixin to add logging capabilities to classes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)

    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self.logger.info(message, **kwargs)

    def log_error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self.logger.error(message, **kwargs)

    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self.logger.warning(message, **kwargs)

    def log_debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self.logger.debug(message, **kwargs)


def log_function_call(func: Callable) -> Callable:
    """Decorator to log function calls."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        logger.debug(
            "Function called", function=func.__name__, args=args, kwargs=kwargs
        )
        try:
            result = func(*args, **kwargs)
            logger.debug(
                "Function completed",
                function=func.__name__,
                result=type(result).__name__,
            )
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return wrapper
