"""
Certificate Collector v4.0
Automated Brazilian Government Certificate Generator

Developed by RSCHASKOS
Refactored to PySide6 + Playwright in 2026
"""

import sys
from PySide6.QtWidgets import QApplication
from core.logger import setup_logger
from core.config import get_config
from gui.main_window import MainWindow

__version__ = '4.0'


def main():
    """Main entry point for the application."""
    # Setup logging system
    config = get_config()
    log_level = config.get_setting('log_level', 'INFO')
    setup_logger(log_level)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName('Certificate Collector')
    app.setApplicationVersion(__version__)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Execute application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
