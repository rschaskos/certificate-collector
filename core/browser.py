"""
Browser manager for Certificate Collector v4.0
Handles Playwright browser lifecycle and context management.
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from core.config import get_config


class BrowserManager:
    """Manages Playwright browser instances with proper lifecycle management."""

    def __init__(self):
        self.logger = get_logger('BrowserManager')
        self.config = get_config()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright_context = None

    def start(self, headless: bool = None) -> Page:
        """
        Start browser and return a page instance.

        Args:
            headless: Override config headless setting if provided

        Returns:
            Page instance ready for automation
        """
        try:
            # Determine headless mode
            if headless is None:
                headless = not self.config.get_setting('browser_headless', False)

            self.logger.info(f'Starting browser (headless={headless})')

            # Start Playwright
            self._playwright_context = sync_playwright().start()
            self.playwright = self._playwright_context

            # Launch browser (Chromium)
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--start-maximized']
            )

            # Create context with download settings
            self.context = self.browser.new_context(
                viewport=None,  # Use full screen
                accept_downloads=True
            )

            # Set default timeout
            timeout = self.config.get_timeout('browser_timeout')
            self.context.set_default_timeout(timeout)

            # Create page
            self.page = self.context.new_page()

            self.logger.info('Browser started successfully')
            return self.page

        except Exception as e:
            self.logger.error(f'Failed to start browser: {e}')
            self.close()
            raise

    def close(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
                self.page = None

            if self.context:
                self.context.close()
                self.context = None

            if self.browser:
                self.browser.close()
                self.browser = None

            if self._playwright_context:
                self._playwright_context.stop()
                self._playwright_context = None
                self.playwright = None

            self.logger.info('Browser closed successfully')

        except Exception as e:
            self.logger.warning(f'Error during browser cleanup: {e}')

    def new_page(self) -> Page:
        """Create a new page in the current context."""
        if not self.context:
            raise RuntimeError('Browser not started. Call start() first.')

        page = self.context.new_page()
        self.logger.debug('New page created')
        return page

    def screenshot(self, name: str):
        """Take a screenshot of the current page."""
        if not self.page:
            self.logger.warning('Cannot take screenshot: no active page')
            return

        try:
            screenshots_dir = Path('./screenshots')
            screenshots_dir.mkdir(exist_ok=True)

            filepath = screenshots_dir / f'{name}.png'
            self.page.screenshot(path=str(filepath))
            self.logger.info(f'Screenshot saved: {filepath}')

        except Exception as e:
            self.logger.error(f'Failed to take screenshot: {e}')

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def create_browser_manager() -> BrowserManager:
    """Factory function to create a new BrowserManager instance."""
    return BrowserManager()
