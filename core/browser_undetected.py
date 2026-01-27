"""
Undetected Chrome Browser Manager for Certificate Collector

Uses undetected-chromedriver to bypass bot detection on sites like
Receita Federal that detect Playwright/standard Selenium.

Installation:
    pip install undetected-chromedriver selenium
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import time
import random
from core.logger import get_logger


class UndetectedBrowserManager:
    """Manages undetected Chrome browser for bot-detection bypass."""

    def __init__(self):
        self.logger = get_logger('UndetectedBrowser')
        self.driver = None
        self.downloads_path = Path('./downloads').resolve()
        self.downloads_path.mkdir(exist_ok=True)

    def start(self, headless: bool = False) -> bool:
        """
        Start undetected Chrome browser.

        Args:
            headless: Run in headless mode (not recommended for detection bypass)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f'Starting undetected Chrome (headless={headless})')

            options = uc.ChromeOptions()

            # Download preferences
            prefs = {
                "download.default_directory": str(self.downloads_path),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "plugins.always_open_pdf_externally": True
            }
            options.add_experimental_option("prefs", prefs)

            # Additional arguments for stealth
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--lang=pt-BR")

            # Window size
            options.add_argument("--window-size=1920,1080")

            # Start browser
            self.driver = uc.Chrome(
                options=options,
                headless=headless,
                use_subprocess=True
            )

            # Set timeouts
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)

            self.logger.info('Undetected Chrome started successfully')
            return True

        except Exception as e:
            self.logger.error(f'Failed to start browser: {e}', exc_info=True)
            return False

    def stop(self):
        """Stop the browser."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info('Browser closed successfully')
            except Exception as e:
                self.logger.error(f'Error closing browser: {e}')
            finally:
                self.driver = None

    def navigate(self, url: str) -> bool:
        """Navigate to URL."""
        try:
            self.logger.info(f'Navigating to {url}')
            self.driver.get(url)
            time.sleep(2)  # Wait for page to stabilize
            return True
        except Exception as e:
            self.logger.error(f'Navigation failed: {e}')
            return False

    def human_delay(self, min_ms: int = 500, max_ms: int = 1500):
        """Add random delay to simulate human behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        time.sleep(delay)

    def slow_type(self, element, text: str, delay_min: int = 50, delay_max: int = 150):
        """Type text slowly like a human."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.randint(delay_min, delay_max) / 1000)

    def human_click(self, element):
        """Click with human-like mouse movement."""
        actions = ActionChains(self.driver)
        actions.move_to_element(element)
        self.human_delay(100, 300)
        actions.click()
        actions.perform()

    def wait_for_element(self, by: By, selector: str, timeout: int = 30):
        """Wait for element to be visible."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
            return element
        except Exception as e:
            self.logger.warning(f'Element not found: {selector}')
            return None

    def wait_for_clickable(self, by: By, selector: str, timeout: int = 30):
        """Wait for element to be clickable."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except Exception as e:
            self.logger.warning(f'Element not clickable: {selector}')
            return None

    def take_screenshot(self, name: str):
        """Take screenshot for debugging."""
        try:
            screenshots_dir = Path('./screenshots')
            screenshots_dir.mkdir(exist_ok=True)
            filepath = screenshots_dir / f'{name}.png'
            self.driver.save_screenshot(str(filepath))
            self.logger.info(f'Screenshot saved: {filepath.name}')
        except Exception as e:
            self.logger.error(f'Screenshot failed: {e}')

    def save_page_as_pdf(self, filepath: str) -> bool:
        """
        Save current page as PDF using Chrome's print functionality.

        Note: This uses Chrome DevTools Protocol for PDF generation.
        """
        try:
            import base64

            # Use Chrome DevTools Protocol to print to PDF
            result = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "landscape": False,
                "paperWidth": 8.27,  # A4
                "paperHeight": 11.69,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
            })

            # Decode and save
            pdf_data = base64.b64decode(result['data'])
            with open(filepath, 'wb') as f:
                f.write(pdf_data)

            self.logger.info(f'PDF saved: {filepath}')
            return True

        except Exception as e:
            self.logger.error(f'Failed to save PDF: {e}')
            return False

    def get_downloaded_file(self, timeout: int = 30) -> Path:
        """Wait for and return the most recently downloaded file."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            files = list(self.downloads_path.glob('*'))
            # Filter out incomplete downloads
            files = [f for f in files if not f.suffix == '.crdownload']
            if files:
                # Return most recent
                return max(files, key=lambda f: f.stat().st_mtime)
            time.sleep(0.5)
        return None
