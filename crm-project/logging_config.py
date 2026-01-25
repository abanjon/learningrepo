# logging_config.py
import logging
import config
import os


def setup_logging():
    """Configure logging for entire application"""

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Clear any existing handlers
    logging.getLogger().handlers.clear()

    # Create formatter
    formatter = logging.Formatter(config.LOG_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_handler.setFormatter(formatter)

    # Main file handler
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    file_handler.setFormatter(formatter)

    # Error file handler (errors only)
    error_handler = logging.FileHandler(config.ERROR_LOG_FILE)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)
