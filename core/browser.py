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
                headless = self.config.get_setting('browser_headless', False)

            self.logger.info(f'Starting browser (headless={headless})')

            # Start Playwright
            self._playwright_context = sync_playwright().start()
            self.playwright = self._playwright_context

            # User data directory for persistent profile (like a real user)
            user_data_dir = Path('./browser_profile')
            user_data_dir.mkdir(exist_ok=True)

            # Use persistent context (keeps cookies, history, etc.)
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                channel='msedge',
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--disable-browser-side-navigation',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-popup-blocking'
                ],
                viewport=None,
                accept_downloads=True,
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
                ignore_https_errors=True
            )

            # Comprehensive anti-detection script
            self.context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Override plugins to look real
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'PDF Viewer', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
                        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' },
                        { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer' },
                        { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer' }
                    ]
                });

                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });

                // Override platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });

                // Override hardwareConcurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });

                // Override deviceMemory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });

                // Override connection
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        rtt: 50,
                        downlink: 10,
                        saveData: false
                    })
                });

                // Remove automation indicators from Chrome object
                if (window.chrome) {
                    window.chrome.runtime = {
                        PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' },
                        PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                        PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                        RequestUpdateCheckStatus: { THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available' },
                        OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update' },
                        OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' }
                    };
                }

                // Override permissions query
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Make toString() return native code for overridden functions
                const nativeToString = Function.prototype.toString;
                Function.prototype.toString = function() {
                    if (this === window.navigator.permissions.query) {
                        return 'function query() { [native code] }';
                    }
                    return nativeToString.call(this);
                };
            """)

            # Set default timeout
            timeout = self.config.get_timeout('browser_timeout')
            self.context.set_default_timeout(timeout)

            # Get or create page
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
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

            # No separate browser when using persistent context
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
