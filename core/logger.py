import logging
import logging.handlers
import json
import os
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional, cast

# Context variable to hold request correlation ID for tracing
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="system")

# ──────────────────────────────────────────────────────────────
# ANSI Color Codes for Terminal Output
# ──────────────────────────────────────────────────────────────
class _Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    # Level colors
    DEBUG   = "\033[36m"      # Cyan
    INFO    = "\033[32m"      # Green
    WARNING = "\033[33m"      # Yellow
    ERROR   = "\033[31m"      # Red
    CRITICAL = "\033[41m\033[37m"  # White on Red BG
    # Semantic colors
    CYAN    = "\033[36m"
    MAGENTA = "\033[35m"
    BLUE    = "\033[34m"
    WHITE   = "\033[37m"
    GRAY    = "\033[90m"


_LEVEL_COLORS = {
    "DEBUG":    _Colors.DEBUG,
    "INFO":     _Colors.INFO,
    "WARNING":  _Colors.WARNING,
    "ERROR":    _Colors.ERROR,
    "CRITICAL": _Colors.CRITICAL,
}

_LEVEL_ICONS = {
    "DEBUG":    "🔍",
    "INFO":     "✅",
    "WARNING":  "⚠️",
    "ERROR":    "❌",
    "CRITICAL": "🔥",
}

# ──────────────────────────────────────────────────────────────
# Custom Logger Class
# ──────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────────────────────
class ColoredConsoleFormatter(logging.Formatter):
    """
    Human-readable, color-coded formatter for terminal output.
    Shows timestamp, level icon, logger name, message, and extra fields
    in a visually clear format that's easy to scan in real-time.
    """
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = _LEVEL_COLORS.get(level, _Colors.RESET)
        icon = _LEVEL_ICONS.get(level, "")
        
        # Timestamp — short format for terminal
        ts = self.formatTime(record, "%H:%M:%S")
        
        # Logger name — shortened
        logger_name = record.name
        if len(logger_name) > 25:
            logger_name = "..." + logger_name[-22:]
        
        # Build main line
        msg = record.getMessage()
        line = (
            f"{_Colors.GRAY}{ts}{_Colors.RESET} "
            f"{color}{icon} {level:<8}{_Colors.RESET} "
            f"{_Colors.CYAN}[{logger_name}]{_Colors.RESET} "
            f"{_Colors.BOLD}{msg}{_Colors.RESET}"
        )
        
        # Append extra fields on new indented lines
        extra_fields = record.__dict__.get("extra_fields")
        if extra_fields:
            for key, value in extra_fields.items():
                val_str = str(value)
                # Truncate very long values for terminal readability
                if len(val_str) > 300:
                    val_str = val_str[:300] + "..."
                line += f"\n    {_Colors.MAGENTA}├─ {key}: {_Colors.WHITE}{val_str}{_Colors.RESET}"
        
        # Append exception info
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            line += f"\n{_Colors.ERROR}{exc_text}{_Colors.RESET}"
        
        return line


class StructuredJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in structured JSON format.
    Ideal for enterprise environments, log aggregators, and programmatic analysis.
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


# ──────────────────────────────────────────────────────────────
# Logger Factory
# ──────────────────────────────────────────────────────────────
def _get_project_logs_dir() -> str:
    """Returns the project-level logs directory, creating it if needed."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_logger(name: str) -> EnterpriseLogger:
    """
    Configures and returns a logger with:
    - Colored human-readable output on the terminal (console)
    - Structured JSON output to logs/app.log (RotatingFileHandler, 10MB x 5)
    """
    logger = cast(EnterpriseLogger, logging.getLogger(name))
    
    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))
    
    # ── Console Handler — Colored & Human-Readable ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredConsoleFormatter())
    console_handler.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logger.addHandler(console_handler)
    
    # ── File Handler — JSON Structured (Rotating) ──
    try:
        logs_dir = _get_project_logs_dir()
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(StructuredJSONFormatter())
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to initialize file logging handler: {e}", file=sys.stderr)
    
    # Prevent propagation to root logger to avoid duplicate default logs
    logger.propagate = False
    
    return logger


def get_llm_logger() -> EnterpriseLogger:
    """
    Returns a specialized logger for the LLM Inference Service.
    In addition to the standard console + app.log handlers,
    this logger writes to a dedicated `logs/llm_inference.log` file
    for focused monitoring and analysis.
    """
    logger_name = "llm_inference_service"
    logger = cast(EnterpriseLogger, logging.getLogger(logger_name))
    
    # If already configured (has handlers), return as-is
    if logger.handlers:
        return logger
    
    logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))
    
    # ── Console Handler — Colored & Human-Readable ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredConsoleFormatter())
    console_handler.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logger.addHandler(console_handler)
    
    try:
        logs_dir = _get_project_logs_dir()
        
        # ── General app.log — JSON Structured (Rotating) ──
        app_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        app_file_handler.setFormatter(StructuredJSONFormatter())
        app_file_handler.setLevel(logging.DEBUG)
        logger.addHandler(app_file_handler)
        
        # ── Dedicated LLM log — JSON Structured (Rotating) ──
        llm_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "llm_inference.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        llm_file_handler.setFormatter(StructuredJSONFormatter())
        llm_file_handler.setLevel(logging.DEBUG)
        logger.addHandler(llm_file_handler)
        
    except Exception as e:
        print(f"Warning: Failed to initialize LLM file logging handlers: {e}", file=sys.stderr)
    
    logger.propagate = False
    return logger


# ──────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────
def set_correlation_id(trace_id: str) -> None:
    """Set the correlation/trace ID for the current async context."""
    correlation_id.set(trace_id)

def clear_correlation_id() -> None:
    """Clear the correlation ID back to default."""
    correlation_id.set("system")

def print_banner(service_name: str, version: str = "1.0.0", extras: Optional[Dict[str, Any]] = None):
    """
    Prints a visually striking ASCII startup banner to the console.
    Used at service boot to make it immediately obvious which service started.
    """
    border = "═" * 60
    lines = [
        f"",
        f"{_Colors.CYAN}╔{border}╗{_Colors.RESET}",
        f"{_Colors.CYAN}║{_Colors.RESET}  {_Colors.BOLD}🚀  {service_name}{_Colors.RESET}",
        f"{_Colors.CYAN}║{_Colors.RESET}  {_Colors.GRAY}Version: {version}{_Colors.RESET}",
    ]
    if extras:
        for key, value in extras.items():
            lines.append(f"{_Colors.CYAN}║{_Colors.RESET}  {_Colors.MAGENTA}{key}: {_Colors.WHITE}{value}{_Colors.RESET}")
    lines.append(f"{_Colors.CYAN}║{_Colors.RESET}  {_Colors.GRAY}Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}{_Colors.RESET}")
    lines.append(f"{_Colors.CYAN}╚{border}╝{_Colors.RESET}")
    lines.append("")
    
    print("\n".join(lines), flush=True)
