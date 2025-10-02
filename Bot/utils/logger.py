import logging
import sys
import json
from pathlib import Path

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[90m",   # ƒOƒŒ[
        logging.INFO: "\033[92m",    # —Î
        logging.WARNING: "\033[93m", # ‰©F
        logging.ERROR: "\033[91m",   # Ô
        logging.CRITICAL: "\033[95m" # Ž‡
    }
    RESET = "\033[0m"

    def format(self, record):
        formatted = super().format(record)
        color = self.COLORS.get(record.levelno, self.RESET)
        return f"{color}{formatted}{self.RESET}"

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

def Logger(name: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name or __name__)
    level_name = "DEBUG"

    if logger.handlers:
        logger.setLevel(LEVEL_MAP.get(level_name, logging.INFO))
        return logger

    logger.setLevel(LEVEL_MAP.get(level_name, logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter("[%(asctime)s] [%(levelname)s | %(name)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger