import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from .main_config import LOG_DIRECTORY , LOG_NAME
import os


LOG_PATH = os.path.join(LOG_DIRECTORY, LOG_NAME)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d - %(funcName)s] - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Size-based rotation
    size_handler = RotatingFileHandler(
        filename=LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    size_handler.setFormatter(formatter)
    logger.addHandler(size_handler)

    # Time-based rotation
    time_handler = TimedRotatingFileHandler(
        filename=LOG_PATH,
        when="midnight",
        interval=1,
        backupCount=7
    )
    time_handler.setFormatter(formatter)
    logger.addHandler(time_handler)

    return logger