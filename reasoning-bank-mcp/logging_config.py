"""
Structured logging configuration for ReasoningBank MCP server

Configures structlog to wrap the standard logging library, providing
JSON-formatted structured logs while maintaining backward compatibility
with existing logging.info() calls throughout the codebase.
"""
import logging
import sys
import structlog


def configure_logging():
    """
    Configures structured logging for the entire application.
    Existing loggers will be processed by structlog.
    
    All logs will be rendered as JSON to stdout with the following fields:
    - event: The log message
    - level: Log level (info, warning, error, etc.)
    - timestamp: ISO 8601 formatted timestamp
    - logger: Name of the logger
    - Additional context fields as provided
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    print("✓ Structured logging configured successfully")