"""
Logging system for Certificate Collector v4.0
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class CertificateLogger:
    """Centralized logging system with file and console output."""

    _instance = None
    _logger = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Configure logger with file and console handlers."""
        self._logger = logging.getLogger('CertificateCollector')
        self._logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid duplicates
        self._logger.handlers = []

        # Create logs directory if it doesn't exist
        logs_dir = Path('./logs')
        logs_dir.mkdir(exist_ok=True)

        # File handler with daily rotation naming
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'certidoes_{today}.log'

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)-8s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def get_logger(self, name: str = None):
        """Get a logger instance with optional name prefix."""
        if name:
            return logging.getLogger(f'CertificateCollector.{name}')
        return self._logger

    def cleanup_old_logs(self, days: int = 30):
        """Remove log files older than specified days."""
        logs_dir = Path('./logs')
        if not logs_dir.exists():
            return

        now = datetime.now()
        for log_file in logs_dir.glob('certidoes_*.log'):
            try:
                file_date_str = log_file.stem.replace('certidoes_', '')
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                age_days = (now - file_date).days

                if age_days > days:
                    log_file.unlink()
                    self._logger.info(f'Removed old log file: {log_file.name}')
            except Exception as e:
                self._logger.warning(f'Failed to process log file {log_file.name}: {e}')


# Global instance
_certificate_logger = None


def setup_logger(log_level: str = 'INFO'):
    """Initialize the global logger instance."""
    global _certificate_logger
    _certificate_logger = CertificateLogger()

    # Set log level from config
    level = getattr(logging, log_level.upper(), logging.INFO)
    _certificate_logger.get_logger().setLevel(level)

    # Cleanup old logs
    _certificate_logger.cleanup_old_logs()

    return _certificate_logger


def get_logger(name: str = None):
    """Get logger instance. Initializes if not already set up."""
    global _certificate_logger
    if _certificate_logger is None:
        _certificate_logger = CertificateLogger()
    return _certificate_logger.get_logger(name)
