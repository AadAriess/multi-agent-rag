"""
Konfigurasi logging untuk aplikasi
"""
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: int = logging.INFO, log_file: str = "app.log"):
    """
    Mengatur konfigurasi logging untuk aplikasi
    """
    # Format log
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Logger utama
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Handler untuk konsol
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # Handler untuk file
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=5  # 10MB
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger