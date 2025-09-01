import logging
from pathlib import Path
from typing import Optional,Union
from time import time


class ColoredFormatter(logging.Formatter):
    """Sets the color of different log levels. Adapted from https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/56944256#56944256."""    

    def __init__(self, format):
        super().__init__()

        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        self.FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: grey + format + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(logger_name: str,
               log_file: Optional[Union[Path, str]] = None,
               console_log_level: int = logging.INFO,
               file_log_level: int = logging.INFO,
               console_format_str: str = '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
               file_format_str: str = '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
               silent: bool = False
               ) -> logging.Logger:
    """Gets a logger with the specified setting.

    Args:
        logger_name (str): Name of the logger.
        log_file (Path, optional): If not None, logs to this file. Defaults to None.
        console_log_level/file_log_level (int, optional): Logging level for console/file. One of logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL. Defaults to logging.INFO.
        console_format_str/file_format_str (str, optional): Format of the log message for console/file. Defaults to '%(asctime)s - %(levelname)s - %(name)s - %(message)s'.
        silent (bool, optional): If True, does not log to console. Defaults to False.

    Returns:
        logging.Logger: Logger object.
    """

    logger_id = f"{logger_name}@{time()}"
    logger = logging.getLogger(logger_id)
    logger.setLevel(min(console_log_level, file_log_level))
    
    if not silent:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_log_level)
        console_formatter = ColoredFormatter(console_format_str)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_log_level)
        file_formatter = logging.Formatter(file_format_str)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
