import logging
import sys
from logging.handlers import RotatingFileHandler

APP_LOGGER_NAME = 'main'
FILE_NAME = "main.log"
LOGGING_LEVEL = logging.DEBUG


def setup_applevel_logger(logger_name=APP_LOGGER_NAME, file_name=FILE_NAME):
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOGGING_LEVEL)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(sh)
    if file_name:
        fh = RotatingFileHandler(file_name, maxBytes=16777216, backupCount=2)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


def get_logger(module_name):
    return logging.getLogger(APP_LOGGER_NAME).getChild(module_name)
