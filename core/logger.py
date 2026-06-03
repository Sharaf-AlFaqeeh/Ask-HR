import logging
import json
import os
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, cast

# Context variable to hold request correlation ID for tracing
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="system")

class EnterpriseLogger(logging.Logger):
    """
    Custom Logger subclass to dynamically intercept and handle 'extra_fields'
    passed to log statements, making it transparent for Python standard logging library.
    """
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        extra_fields = kwargs.pop("extra_fields", None)
        if extra_fields is not None:
            if extra is None:
                extra = {}
            extra["extra_fields"] = extra_fields
        super()._log(
            level, msg, args, 
            exc_info=exc_info, 
            extra=extra, 
            stack_info=stack_info, 
            stacklevel=stacklevel,
            **kwargs
        )

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().debug(msg, *args, **kwargs)

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().info(msg, *args, **kwargs)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().critical(msg, *args, **kwargs)

    def exception(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        super().exception(msg, *args, **kwargs)

# Register custom EnterpriseLogger class
logging.setLoggerClass(EnterpriseLogger)

class StructuredJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in structured JSON format.
    Ideal for enterprise environments and log aggregators.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get("system"),
            "file": f"{record.pathname}:{record.lineno}",
            "function": record.funcName
        }
        
        # Merge extra fields if present
        if record.__dict__.get("extra_fields"):
            log_data.update(record.__dict__["extra_fields"])
            
        # Include exception info if logging an error
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)

def get_logger(name: str) -> EnterpriseLogger:
    """
    Configures and returns a logger with structured JSON format for console.
    """
    logger = cast(EnterpriseLogger, logging.getLogger(name))
    
    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger to avoid duplicate default logs
    logger.propagate = False
    
    return logger

# Middleware utility to set trace ID
def set_correlation_id(trace_id: str) -> None:
    correlation_id.set(trace_id)

def clear_correlation_id() -> None:
    correlation_id.set("system")
