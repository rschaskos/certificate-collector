"""
Base certificate class for Certificate Collector v4.0
Abstract base class that all certificate implementations inherit from.
"""

import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from core.logger import get_logger
from core.config import get_config


class BaseCertificate(ABC):
    """Abstract base class for all certificate generators."""

    def __init__(self, cnpj: str, page: Page, extra_data: dict = None):
        """
        Initialize certificate generator.

        Args:
            cnpj: Company CNPJ number
            page: Playwright Page instance
            extra_data: Additional data (e.g., start_date for federal certificate)
        """
        self.cnpj = cnpj
        self.page = page
        self.extra_data = extra_data or {}
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)

        # Get certificate-specific config
        self.cert_type = self._get_cert_type()
        self.url = self.config.get_url(self.cert_type)
        self.selectors = self.config.get_selectors(self.cert_type)
        self.timeout = self.config.get_timeout('default_wait')

    def human_delay(self, min_ms: int = 500, max_ms: int = 1500):
        """
        Add random delay to simulate human behavior.

        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        delay = random.randint(min_ms, max_ms)
        self.page.wait_for_timeout(delay)

    def slow_type(self, selector: str, text: str, delay_min: int = 50, delay_max: int = 150):
        """
        Type text slowly like a human.

        Args:
            selector: CSS selector or XPath
            text: Text to type
            delay_min: Minimum delay between keystrokes in ms
            delay_max: Maximum delay between keystrokes in ms
        """
        element = self.page.locator(selector)
        element.click()
        self.human_delay(300, 600)
        # Type with random delay between keystrokes
        element.type(text, delay=random.randint(delay_min, delay_max))

    @abstractmethod
    def _get_cert_type(self) -> str:
        """Return the certificate type identifier (e.g., 'fgts', 'estadual')."""
        pass

    @abstractmethod
    def generate(self) -> bool:
        """
        Generate the certificate.

        Returns:
            True if successful, False otherwise
        """
        pass

    def wait_for_selector(self, selector: str, timeout: int = None, state: str = 'visible') -> bool:
        """
        Wait for element with logging.

        Args:
            selector: CSS selector or XPath
            timeout: Custom timeout in milliseconds
            state: Element state to wait for ('visible', 'attached', 'hidden')

        Returns:
            True if element found, False on timeout
        """
        timeout = timeout or self.timeout
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state=state)
            self.logger.debug(f'Element found: {selector}')
            return True
        except PlaywrightTimeoutError:
            self.logger.warning(f'Timeout waiting for element: {selector}')
            return False
        except Exception as e:
            self.logger.error(f'Error waiting for element {selector}: {e}')
            return False

    def click_element(self, selector: str, timeout: int = None) -> bool:
        """
        Click element with error handling.

        Args:
            selector: CSS selector or XPath
            timeout: Custom timeout in milliseconds

        Returns:
            True if clicked successfully, False otherwise
        """
        try:
            if not self.wait_for_selector(selector, timeout):
                return False

            self.page.click(selector)
            self.logger.debug(f'Clicked element: {selector}')
            return True
        except Exception as e:
            self.logger.error(f'Failed to click element {selector}: {e}')
            return False

    def fill_input(self, selector: str, value: str, timeout: int = None) -> bool:
        """
        Fill input field with error handling.

        Args:
            selector: CSS selector or XPath
            value: Value to fill
            timeout: Custom timeout in milliseconds

        Returns:
            True if filled successfully, False otherwise
        """
        try:
            if not self.wait_for_selector(selector, timeout):
                return False

            self.page.fill(selector, value)
            self.logger.debug(f'Filled input {selector} with: {value}')
            return True
        except Exception as e:
            self.logger.error(f'Failed to fill input {selector}: {e}')
            return False

    def get_text(self, selector: str, timeout: int = None) -> Optional[str]:
        """
        Get text content from element.

        Args:
            selector: CSS selector or XPath
            timeout: Custom timeout in milliseconds

        Returns:
            Text content or None if not found
        """
        try:
            if not self.wait_for_selector(selector, timeout):
                return None

            text = self.page.text_content(selector)
            self.logger.debug(f'Got text from {selector}: {text}')
            return text
        except Exception as e:
            self.logger.error(f'Failed to get text from {selector}: {e}')
            return None

    def download_pdf(self, filename: str = None) -> Optional[Path]:
        """
        Handle PDF download.

        Args:
            filename: Custom filename (without extension)

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Wait for download
            with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                # Trigger is handled by caller
                pass

            download = download_info.value
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

            if filename:
                filepath = self.config.get_path('downloads') / f'{filename}_{timestamp}.pdf'
            else:
                filepath = self.config.get_path('downloads') / f'{self.cert_type}_{self.cnpj}_{timestamp}.pdf'

            download.save_as(str(filepath))
            self.logger.info(f'PDF downloaded: {filepath.name}')
            return filepath

        except Exception as e:
            self.logger.error(f'Failed to download PDF: {e}')
            return None

    def navigate(self) -> bool:
        """
        Navigate to certificate URL.

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            self.logger.info(f'Navigating to {self.url}')
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
            # Wait a bit more for dynamic content
            self.page.wait_for_timeout(1000)
            self.logger.debug('Page loaded successfully')
            return True
        except Exception as e:
            self.logger.error(f'Failed to navigate to {self.url}: {e}')
            return False

    def check_error_message(self, error_selector: str) -> Optional[str]:
        """
        Check if error message is present.

        Args:
            error_selector: Selector for error message element

        Returns:
            Error message text if present, None otherwise
        """
        try:
            if self.page.is_visible(error_selector):
                error_text = self.page.text_content(error_selector)
                self.logger.warning(f'Error message found: {error_text}')
                return error_text
        except Exception:
            pass
        return None

    def take_screenshot(self, name: str = None):
        """Take screenshot for debugging."""
        try:
            screenshots_dir = Path('./screenshots')
            screenshots_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = name or f'{self.cert_type}_{timestamp}'
            filepath = screenshots_dir / f'{filename}.png'

            self.page.screenshot(path=str(filepath))
            self.logger.info(f'Screenshot saved: {filepath.name}')
        except Exception as e:
            self.logger.error(f'Failed to take screenshot: {e}')
