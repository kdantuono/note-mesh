"""
Comprehensive logging configuration for NoteMesh backend.
"""
import logging
import logging.config
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from ..config import get_settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage'):
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{self.BOLD}{record.levelname}{self.RESET}"

        # Color the logger name
        record.name = f"\033[90m{record.name}{self.RESET}"

        return super().format(record)


def get_log_level(level_str: Optional[str] = None) -> int:
    """Get log level from string or environment."""
    settings = get_settings()
    level_str = level_str or settings.log_level

    levels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
    }

    return levels.get(level_str.upper(), logging.INFO)


def setup_logging() -> None:
    """Setup comprehensive logging configuration."""
    settings = get_settings()

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter,
            },
            'colored': {
                '()': ColoredFormatter,
                'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'file': {
                'format': '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-20s:%(lineno)-4d | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored' if settings.debug else 'json',
                'stream': sys.stdout,
                'level': get_log_level(),
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_dir / 'notemesh.log',
                'maxBytes': 10_000_000,  # 10MB
                'backupCount': 5,
                'formatter': 'file',
                'level': 'DEBUG',
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_dir / 'error.log',
                'maxBytes': 10_000_000,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
                'level': 'ERROR',
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'notemesh': {
                'handlers': ['console', 'file', 'error_file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'uvicorn': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'uvicorn.access': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'sqlalchemy': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'alembic': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
        }
    }

    logging.config.dictConfig(config)

    # Log startup info
    logger = logging.getLogger('notemesh.logging')
    logger.info("Logging system initialized", extra={
        'log_level': settings.log_level,
        'debug': settings.debug,
        'environment': getattr(settings, 'environment', 'unknown')
    })


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"notemesh.{name}")


class LoggingMiddleware:
    """FastAPI middleware for request logging."""

    def __init__(self, app, logger_name: str = "http"):
        self.app = app
        self.logger = get_logger(logger_name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = datetime.utcnow()
        request_id = id(scope)  # Simple request ID

        # Log request
        self.logger.info("HTTP Request", extra={
            'request_id': request_id,
            'method': scope['method'],
            'path': scope['path'],
            'query_string': scope.get('query_string', b'').decode(),
            'client_ip': scope.get('client', ['unknown'])[0] if scope.get('client') else 'unknown',
            'user_agent': next((h[1].decode() for h in scope.get('headers', []) if h[0] == b'user-agent'), 'unknown')
        })

        # Process request
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Log response
                self.logger.info("HTTP Response", extra={
                    'request_id': request_id,
                    'status_code': message.get('status', 0),
                    'duration_ms': round(duration, 2),
                    'method': scope['method'],
                    'path': scope['path']
                })

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000

            self.logger.error("HTTP Request Failed", extra={
                'request_id': request_id,
                'method': scope['method'],
                'path': scope['path'],
                'duration_ms': round(duration, 2),
                'exception_type': type(exc).__name__,
                'exception_message': str(exc)
            })
            raise