# src/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

LOG_FILE = Path(__file__).parent.parent / "relay_api.log"

# Create logger
logger = logging.getLogger("relay_api")
logger.setLevel(logging.INFO)

# ----- File handler -----
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
file_handler.setFormatter(file_formatter)

# ----- Stream handler (stdout) -----
stream_handler = logging.StreamHandler(sys.stdout)
stream_formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
stream_handler.setFormatter(stream_formatter)

# Avoid adding multiple handlers if module is imported multiple times
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

