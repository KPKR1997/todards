"""
Todards Pipeline — Structured Logging

Configures unified logging for all pipeline components.
Outputs formatted logs to stdout and optionally to a daily log file.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "todards",
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Logger name (hierarchy dot-separated).
        log_dir: Directory where log files are stored. Defaults to data/logs.
        level: Logging level (default: logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Console Handler with clear formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File Handler
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_path = log_dir / f"todards_{date_str}.log"

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger
