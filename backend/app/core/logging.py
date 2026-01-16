"""
Structured logging configuration
JSON format for log aggregation (ELK, CloudWatch, etc.)
"""

import logging
import sys
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logging():
    """Configure structured logging"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatter for production
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "levelname": "level",
                "asctime": "timestamp",
                "name": "logger",
            }
        )
    else:
        # Standard formatter for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logger
