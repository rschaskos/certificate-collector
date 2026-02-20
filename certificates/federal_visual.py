"""
Federal Certificate (Receita Federal) - Playwright + OCR Implementation

This module uses a hybrid approach to avoid WebDriver detection:
1. Opens Chrome via subprocess (no WebDriver flags)
2. Connects Playwright via CDP for control
3. Humanized delays and mouse movements
4. OCR as fallback when selectors fail

Flow:
- Tela 1: Preencher CNPJ -> Clicar "Emitir Certidao" (azul)
- Tela 2: Modal -> Clicar "Consultar Certidao" (branco, esquerda)
- Tela 3: Datas -> Clicar "Cons1ultar Certidao" (azul)
- Tela 4: Tabela -> Verificar "Valida" -> Clicar download

Author: Certificate Collector Team
Version: 4.0.0 (Chrome subprocess + CDP)
"""

import os
import sys
import time
import random
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

from playwright.sync_api import (
    sync_playwright,
    Page,
    BrowserContext,
    Browser,
    Playwright,
    TimeoutError as PlaywrightTimeoutError
)
import pytesseract
from PIL import Image

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger
from core.config import get_config


# Known selectors for the Federal certificate site
SELECTORS = {
    'cnpj_input': 'input[placeholder="Informe o CNPJ"]',
    'cnpj_input_alt': 'br-input input',
    'cnpj_input_xpath': '//input[@placeholder="Informe o CNPJ"]',
    'emitir_btn': 'button:has-text("Emitir Certidao")',
    'emitir_btn_alt': 'button.primary:has-text("Emitir")',
    'consultar_secondary': 'button.secondary:has-text("Consultar")',
    'consultar_primary': 'button.primary:has-text("Consultar")',
    'consultar_btn': 'button:has-text("Consultar Certidao")',
    'download_icon': 'td button, td a[download], table button, table a',
    'modal_container': '.br-modal, [class*="modal"]',
    'table_situacao': 'table td:has-text("Valida"), table td:has-text("Vencida")',
}


class FederalVisualCertificate:
    """
    Federal Certificate generator using Playwright + OCR.

    Combines the reliability of Playwright selectors with OCR fallback
    for difficult-to-select elements.
    """

    URL = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"

    def __init__(self, cnpj: str, download_dir: str = None):
        """
        Initialize the certificate generator.

        Args:
            cnpj: Company CNPJ number (with or without formatting)
            download_dir: Directory to save downloaded PDFs
        """
        self.cnpj = self._format_cnpj(cnpj)
        self.cnpj_raw = cnpj.replace('.', '').replace('/', '').replace('-', '')
        self.download_dir = download_dir or str(project_root / 'downloads')
        self.logger = get_logger('FederalVisual')
        self.config = get_config()

        # Playwright objects
        self._playwright_context: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.chrome_process: Optional[subprocess.Popen] = None

        # Browser profile directory (persistent context)
        self.user_data_dir = project_root / 'browser_profile'
        self.user_data_dir.mkdir(exist_ok=True)

        # Screenshots directory
        self.screenshots_dir = project_root / 'screenshots'
        self.screenshots_dir.mkdir(exist_ok=True)

        # Downloads directory
        Path(self.download_dir).mkdir(exist_ok=True)

    def _format_cnpj(self, cnpj: str) -> str:
        """Format CNPJ with punctuation (XX.XXX.XXX/XXXX-XX)."""
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj

    def setup_browser(self) -> bool:
        """
        Opens Chrome via subprocess and connects Playwright via CDP.

        This approach avoids WebDriver detection because Chrome is started
        as a normal process (not by Playwright), and Playwright only connects
        to control it via Chrome DevTools Protocol.

        IMPORTANT: Chrome is opened with the target URL directly to ensure
        the visible window is the one being controlled by Playwright.

        Returns:
            True if browser started successfully
        """
        try:
            self.logger.info("Starting Chrome via subprocess (no WebDriver)...")

            # Find Chrome executable on Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]

            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    self.logger.info(f"Found Chrome at: {path}")
                    break

            if not chrome_path:
                self.logger.error("Google Chrome not found! Please install Chrome.")
                raise Exception("Google Chrome nao encontrado!")

            # Profile directory for persistent session
            profile_dir = str(self.user_data_dir)

            # Chrome command with remote debugging enabled
            # IMPORTANT: Open with URL directly so the visible window is the controlled one
            cmd = [
                chrome_path,
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
                self.URL,  # Open target URL directly in the visible window
            ]

            self.logger.info(f"Launching Chrome with URL: {self.URL}")
            self.logger.debug(f"Full command: {' '.join(cmd)}")

            # Start Chrome as a subprocess (NOT using WebDriver!)
            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for Chrome to start and page to load
            self.logger.info("Waiting for Chrome to start and load page...")
            time.sleep(5)  # Increased wait time for page to load

            # Connect Playwright via CDP (Chrome DevTools Protocol)
            self.logger.info("Connecting Playwright via CDP...")
            self._playwright_context = sync_playwright().start()
            self.browser = self._playwright_context.chromium.connect_over_cdp("http://localhost:9222")

            # Get the existing context
            self.context = self.browser.contexts[0]

            # Set default timeout
            self.context.set_default_timeout(30000)

            # Log all available pages for debugging
            self.logger.info(f"Found {len(self.context.pages)} page(s) in context")
            for i, p in enumerate(self.context.pages):
                self.logger.info(f"  Page {i}: {p.url}")

            # Find the page with our target URL (the visible one)
            self.page = None
            for p in self.context.pages:
                if "servicos.receitafederal.gov.br" in p.url or "certidoes" in p.url:
                    self.page = p
                    self.logger.info(f"Using page with URL: {p.url}")
                    break

            # Fallback: use first page if target URL not found
            if not self.page and self.context.pages:
                self.page = self.context.pages[0]
                self.logger.info(f"Using first available page: {self.page.url}")

            # Last resort: create new page (should rarely happen)
            if not self.page:
                self.logger.warning("No existing pages found, creating new one...")
                self.page = self.context.new_page()
                self.page.goto(self.URL, wait_until='domcontentloaded')

            # Bring page to front and focus
            self.page.bring_to_front()
            self.page.evaluate("window.focus()")

            # Small delay to ensure focus is set
            time.sleep(0.5)

            self.logger.info("Browser connected successfully via CDP (no WebDriver detection!)")
            self.logger.info(f"Active page URL: {self.page.url}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            # Cleanup if failed
            if self.chrome_process:
                try:
                    self.chrome_process.terminate()
                except:
                    pass
            return False

    def human_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Add humanized random delay between actions."""
        delay_ms = int(random.uniform(min_sec, max_sec) * 1000)
        self.page.wait_for_timeout(delay_ms)

    def slow_type(self, selector: str, text: str, delay_min: int = 50, delay_max: int = 150):
        """
        Type text character by character with humanized delays.

        Args:
            selector: CSS selector for the input element
            text: Text to type
            delay_min: Minimum delay between keystrokes in ms
            delay_max: Maximum delay between keystrokes in ms
        """
        try:
            element = self.page.locator(selector)
            element.click()
            self.human_delay(0.3, 0.6)

            # Clear existing text
            element.fill('')
            self.human_delay(0.1, 0.2)

            # Type character by character with random delays
            for char in text:
                element.type(char, delay=random.randint(delay_min, delay_max))

            self.logger.debug(f"Typed '{text}' into {selector}")

        except Exception as e:
            self.logger.warning(f"slow_type failed for {selector}: {e}")
            raise

    def safe_click(self, selector: str, timeout: int = 10000) -> bool:
        """
        Click element with error handling and humanized behavior.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds

        Returns:
            True if clicked successfully
        """
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state='visible', timeout=timeout)
            self.human_delay(0.2, 0.5)

            # Get element position and add small random offset
            box = locator.bounding_box()
            if box:
                offset_x = random.randint(-3, 3)
                offset_y = random.randint(-3, 3)
                locator.click(position={
                    'x': box['width'] / 2 + offset_x,
                    'y': box['height'] / 2 + offset_y
                })
            else:
                locator.click()

            self.logger.debug(f"Clicked element: {selector}")
            return True

        except PlaywrightTimeoutError:
            self.logger.warning(f"Timeout waiting for element: {selector}")
            return False
        except Exception as e:
            self.logger.warning(f"Failed to click {selector}: {e}")
            return False

    def take_screenshot(self, name: str) -> Optional[Path]:
        """
        Save screenshot for debugging.

        Args:
            name: Base name for the screenshot file

        Returns:
            Path to saved screenshot
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.screenshots_dir / f'{name}_{timestamp}.png'
            self.page.screenshot(path=str(filepath))
            self.logger.debug(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {e}")
            return None

    def find_text_with_ocr(
        self,
        text: str,
        avoid_right_side: bool = True,
        confidence_threshold: float = 60.0
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Use OCR to find text on page (fallback method).

        Args:
            text: Text to find (case-insensitive partial match)
            avoid_right_side: If True, ignore elements on right 15% of screen
            confidence_threshold: Minimum OCR confidence (0-100)

        Returns:
            Tuple (x, y, width, height) of found text, or None
        """
        try:
            # Take screenshot
            screenshot_path = self.screenshots_dir / 'ocr_temp.png'
            self.page.screenshot(path=str(screenshot_path))

            # Load image and run OCR
            image = Image.open(screenshot_path)
            viewport_size = self.page.viewport_size
            screen_width = viewport_size['width'] if viewport_size else 1920

            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                lang='por'
            )

            text_lower = text.lower()
            matches = []

            for i, word in enumerate(data['text']):
                if not word:
                    continue

                word_lower = word.lower()
                conf = float(data['conf'][i])

                # Check if text matches (partial match)
                if text_lower in word_lower or word_lower in text_lower:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]

                    # Filter out VLibras area (right side of screen)
                    if avoid_right_side and x > (screen_width * 0.85):
                        self.logger.debug(f"Ignoring '{word}' at x={x} (VLibras area)")
                        continue

                    # Check confidence
                    if conf >= confidence_threshold:
                        matches.append((x, y, w, h, conf))
                        self.logger.debug(f"OCR found '{word}' at ({x}, {y}), conf={conf:.1f}")

            if matches:
                # Return the match with highest confidence
                matches.sort(key=lambda m: m[4], reverse=True)
                best = matches[0]
                return (best[0], best[1], best[2], best[3])

        except Exception as e:
            self.logger.warning(f"OCR error: {e}")

        return None

    def click_with_ocr_fallback(
        self,
        selector: str,
        ocr_text: str,
        timeout: int = 10000
    ) -> bool:
        """
        Try to click using selector, fallback to OCR if it fails.

        Args:
            selector: CSS selector to try first
            ocr_text: Text to search for with OCR as fallback
            timeout: Timeout for selector in milliseconds

        Returns:
            True if clicked successfully
        """
        # First try with selector
        if self.safe_click(selector, timeout):
            return True

        self.logger.info(f"Selector '{selector}' failed, trying OCR for '{ocr_text}'...")

        # Fallback to OCR
        result = self.find_text_with_ocr(ocr_text)
        if result:
            x, y, w, h = result
            center_x = x + w // 2
            center_y = y + h // 2

            # Click using Playwright's mouse
            self.page.mouse.move(center_x, center_y)
            self.human_delay(0.1, 0.3)
            self.page.mouse.click(center_x, center_y)
            self.logger.info(f"OCR click on '{ocr_text}' at ({center_x}, {center_y})")
            return True

        self.logger.error(f"Failed to click: selector '{selector}' and OCR '{ocr_text}' both failed")
        return False

    def wait_for_navigation_or_modal(self, timeout: int = 5000) -> str:
        """
        Wait and detect what happened after an action.

        Returns:
            'modal' if modal appeared, 'navigation' if page changed, 'timeout' if nothing
        """
        try:
            # Wait a bit for things to settle
            self.page.wait_for_timeout(1000)

            # Check for modal
            modal_selectors = [
                '.br-modal',
                '[class*="modal"]',
                'div[role="dialog"]',
                '.modal-content',
            ]

            for modal_sel in modal_selectors:
                try:
                    if self.page.locator(modal_sel).first.is_visible(timeout=2000):
                        self.logger.info("Modal detected")
                        return 'modal'
                except:
                    pass

            # Check for specific text indicating modal
            if self.page.locator('text="Certidao Valida Encontrada"').first.is_visible(timeout=1000):
                return 'modal'
            if self.page.locator('text="Certidao valida encontrada"').first.is_visible(timeout=1000):
                return 'modal'

            return 'navigation'

        except Exception as e:
            self.logger.debug(f"wait_for_navigation_or_modal: {e}")
            return 'timeout'

    def check_for_error(self) -> bool:
        """
        Check if an error message is displayed.

        Returns:
            True if error found
        """
        error_patterns = [
            'Nao foi possivel',
            'nao foi possivel',
            'Erro',
            'erro ao',
            'falha',
            'CNPJ invalido',
        ]

        try:
            for pattern in error_patterns:
                if self.page.locator(f'text="{pattern}"').first.is_visible(timeout=1000):
                    self.logger.warning(f"Error detected: '{pattern}'")
                    self.take_screenshot('error_detected')
                    return True
        except:
            pass

        return False

    def step1_fill_cnpj_and_emit(self) -> bool:
        """
        Step 1: Fill CNPJ and click "Emitir Certidao" button.

        Returns:
            True if successful
        """
        self.logger.info("[1/4] Navigating and filling CNPJ...")

        try:
            # Check if we're already on the target page (opened by setup_browser)
            current_url = self.page.url
            if "servicos.receitafederal.gov.br" in current_url and "certidoes" in current_url:
                self.logger.info(f"Already on target page: {current_url}")
                # Wait for page to fully load
                self.page.wait_for_load_state('domcontentloaded')
            else:
                # Navigate to the page if not already there
                self.logger.info(f"Navigating to {self.URL}...")
                self.page.goto(self.URL, wait_until='domcontentloaded', timeout=30000)

            self.human_delay(2.0, 3.0)
            self.take_screenshot('step1_page_loaded')

            # Try multiple selectors for CNPJ input
            cnpj_selectors = [
                SELECTORS['cnpj_input'],
                SELECTORS['cnpj_input_alt'],
                'input[type="text"]',
                'br-input input',
            ]

            input_filled = False
            for selector in cnpj_selectors:
                try:
                    self.logger.debug(f"Trying CNPJ selector: {selector}")
                    locator = self.page.locator(selector).first
                    if locator.is_visible(timeout=3000):
                        locator.click()
                        self.human_delay(0.3, 0.5)
                        locator.fill('')  # Clear first
                        self.human_delay(0.1, 0.2)

                        # Type CNPJ with humanized delays
                        for char in self.cnpj_raw:
                            locator.type(char, delay=random.randint(50, 100))

                        self.logger.info(f"CNPJ filled using selector: {selector}")
                        input_filled = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not input_filled:
                self.logger.error("Could not find CNPJ input field!")
                return False

            self.human_delay(0.5, 1.0)
            self.take_screenshot('step1_cnpj_filled')

            # Click "Emitir Certidao" button
            emitir_selectors = [
                SELECTORS['emitir_btn'],
                SELECTORS['emitir_btn_alt'],
                'button:has-text("Emitir")',
                'button.primary',
            ]

            emitir_clicked = False
            for selector in emitir_selectors:
                if self.safe_click(selector, timeout=5000):
                    self.logger.info(f"Clicked 'Emitir' using selector: {selector}")
                    emitir_clicked = True
                    break

            # Fallback to OCR
            if not emitir_clicked:
                self.logger.info("Trying OCR fallback for 'Emitir'...")
                emitir_clicked = self.click_with_ocr_fallback(
                    'button:has-text("Emitir")',
                    'Emitir'
                )

            if not emitir_clicked:
                self.logger.error("Could not click 'Emitir Certidao' button!")
                return False

            self.human_delay(2.0, 3.0)
            self.take_screenshot('step1_after_emitir')

            # Check for errors
            if self.check_for_error():
                return False

            return True

        except Exception as e:
            self.logger.error(f"Step 1 failed: {e}")
            self.take_screenshot('step1_error')
            return False

    def step2_handle_modal(self) -> bool:
        """
        Step 2: Handle the "Certidao Valida Encontrada" modal.
        Click "Consultar Certidao" (white/secondary button on the LEFT).

        Returns:
            True if successful (or if no modal appeared)
        """
        self.logger.info("[2/4] Checking for modal...")
        self.human_delay(1.0, 2.0)

        try:
            # Check if modal appeared
            modal_text_visible = False
            try:
                # Look for modal text
                modal_texts = [
                    'Certidao Valida Encontrada',
                    'Certidao valida encontrada',
                    'CERTIDAO VALIDA ENCONTRADA',
                    'Valida Encontrada',
                ]
                for text in modal_texts:
                    if self.page.locator(f'text="{text}"').first.is_visible(timeout=3000):
                        modal_text_visible = True
                        self.logger.info(f"Modal detected with text: '{text}'")
                        break
            except:
                pass

            if not modal_text_visible:
                self.logger.info("No modal detected, proceeding to next step...")
                return True

            self.take_screenshot('step2_modal_detected')
            self.human_delay(0.5, 1.0)

            # Click "Consultar Certidao" - the SECONDARY (white) button on the LEFT
            # The modal has 2 buttons:
            # - LEFT: "Consultar Certidao" (secondary/white) - WE WANT THIS
            # - RIGHT: "Emitir Nova Certidao" (primary/blue) - AVOID

            consultar_selectors = [
                SELECTORS['consultar_secondary'],
                'button.secondary:has-text("Consultar")',
                '.br-modal button.secondary',
                'button.secondary',
            ]

            clicked = False
            for selector in consultar_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if locator.is_visible(timeout=3000):
                        self.logger.info(f"Clicking modal 'Consultar' with: {selector}")
                        locator.click()
                        clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")

            # Fallback: try to find button by text and position
            if not clicked:
                try:
                    # Find all buttons with "Consultar" text
                    buttons = self.page.locator('button:has-text("Consultar")').all()
                    if buttons:
                        # Get the leftmost one (secondary button is usually on left)
                        leftmost_btn = None
                        min_x = float('inf')

                        for btn in buttons:
                            try:
                                box = btn.bounding_box()
                                if box and box['x'] < min_x:
                                    min_x = box['x']
                                    leftmost_btn = btn
                            except:
                                pass

                        if leftmost_btn:
                            self.logger.info("Clicking leftmost 'Consultar' button")
                            leftmost_btn.click()
                            clicked = True

                except Exception as e:
                    self.logger.debug(f"Fallback button search failed: {e}")

            # OCR fallback
            if not clicked:
                self.logger.info("Trying OCR for modal 'Consultar'...")
                result = self.find_text_with_ocr('Consultar', avoid_right_side=False)
                if result:
                    x, y, w, h = result
                    center_x = x + w // 2
                    center_y = y + h // 2
                    self.page.mouse.click(center_x, center_y)
                    self.logger.info(f"OCR clicked 'Consultar' at ({center_x}, {center_y})")
                    clicked = True

            if not clicked:
                self.logger.warning("Could not click modal 'Consultar' button")
                # Try pressing Escape to close modal and continue
                self.page.keyboard.press('Escape')
                self.human_delay(0.5, 1.0)

            self.human_delay(2.0, 3.0)
            self.take_screenshot('step2_after_modal')
            return True

        except Exception as e:
            self.logger.error(f"Step 2 failed: {e}")
            self.take_screenshot('step2_error')
            return True  # Continue anyway

    def step3_date_selection(self) -> bool:
        """
        Step 3: Date selection page - click "Consultar Certidao" (blue/primary button).

        Returns:
            True if successful
        """
        self.logger.info("[3/4] Date selection page...")
        self.human_delay(1.0, 2.0)

        try:
            self.take_screenshot('step3_date_page')

            # Verify we're on date page (optional check)
            try:
                date_page = self.page.locator('text="Data Inicial"').first.is_visible(timeout=3000)
                if date_page:
                    self.logger.info("Date selection page confirmed")
            except:
                self.logger.debug("Date page markers not found, continuing anyway...")

            # Click "Consultar Certidao" - the PRIMARY (blue) button
            consultar_selectors = [
                SELECTORS['consultar_primary'],
                SELECTORS['consultar_btn'],
                'button.primary:has-text("Consultar")',
                'button[type="submit"]:has-text("Consultar")',
                'button:has-text("Consultar Certidao")',
            ]

            clicked = False
            for selector in consultar_selectors:
                if self.safe_click(selector, timeout=5000):
                    self.logger.info(f"Clicked 'Consultar' with: {selector}")
                    clicked = True
                    break

            # Fallback: find primary/blue button
            if not clicked:
                try:
                    primary_btns = self.page.locator('button.primary, button[type="submit"]').all()
                    for btn in primary_btns:
                        try:
                            text = btn.text_content() or ''
                            if 'Consultar' in text:
                                btn.click()
                                self.logger.info("Clicked primary 'Consultar' button")
                                clicked = True
                                break
                        except:
                            pass
                except:
                    pass

            # OCR fallback
            if not clicked:
                self.logger.info("Trying OCR for 'Consultar Certidao'...")
                clicked = self.click_with_ocr_fallback(
                    'button:has-text("Consultar")',
                    'Consultar'
                )

            if not clicked:
                self.logger.error("Could not click 'Consultar Certidao' on date page!")
                return False

            self.human_delay(3.0, 5.0)
            self.take_screenshot('step3_after_consultar')

            # Check for errors
            if self.check_for_error():
                return False

            return True

        except Exception as e:
            self.logger.error(f"Step 3 failed: {e}")
            self.take_screenshot('step3_error')
            return False

    def step4_download_certificate(self) -> bool:
        """
        Step 4: Results table - check status and download certificate.

        Returns:
            True if successful
        """
        self.logger.info("[4/4] Checking results and downloading...")
        self.human_delay(2.0, 3.0)

        try:
            self.take_screenshot('step4_results_table')

            # Check certificate status
            try:
                # Look for "Valida" in the table
                valida_visible = self.page.locator('text="Valida"').first.is_visible(timeout=5000)
                if valida_visible:
                    self.logger.info("Certificate status: VALIDA")
            except:
                self.logger.debug("Could not find 'Valida' text")

            # Check for "Vencida" (expired)
            try:
                vencida_visible = self.page.locator('text="Vencida"').first.is_visible(timeout=2000)
                if vencida_visible:
                    self.logger.warning("Certificate status: VENCIDA (expired)")
                    print("\n" + "=" * 60)
                    print("  CERTIDAO VENCIDA!")
                    print("  Consulte o contador da instituicao.")
                    print("=" * 60 + "\n")
                    return False
            except:
                pass

            # Find and click download icon in "2a Via" column
            download_selectors = [
                'table button',
                'table a[download]',
                'table td button',
                'td:last-child button',
                'td:last-child a',
                'button:has(svg)',
                'a:has(svg)',
                'i.fa-download',
                '[class*="download"]',
            ]

            clicked = False
            for selector in download_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if locator.is_visible(timeout=3000):
                        self.logger.info(f"Clicking download with: {selector}")

                        # Set up download handler
                        with self.page.expect_download(timeout=30000) as download_info:
                            locator.click()

                        download = download_info.value
                        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                        filename = f'federal_{self.cnpj_raw}_{timestamp}.pdf'
                        filepath = Path(self.download_dir) / filename

                        download.save_as(str(filepath))
                        self.logger.info(f"Certificate downloaded: {filepath}")
                        clicked = True
                        break

                except PlaywrightTimeoutError:
                    self.logger.debug(f"Download timeout with selector: {selector}")
                except Exception as e:
                    self.logger.debug(f"Download selector {selector} failed: {e}")

            # Fallback: look for "2a Via" text and click nearby
            if not clicked:
                self.logger.info("Trying to find download by '2a Via' column...")
                try:
                    via_cell = self.page.locator('text="2a Via"').first
                    if via_cell.is_visible(timeout=3000):
                        # Get position and click in the row
                        box = via_cell.bounding_box()
                        if box:
                            # Click to the right of the header (in the data cell)
                            click_x = box['x'] + box['width'] // 2
                            click_y = box['y'] + box['height'] + 30  # Below header

                            with self.page.expect_download(timeout=30000) as download_info:
                                self.page.mouse.click(click_x, click_y)

                            download = download_info.value
                            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                            filename = f'federal_{self.cnpj_raw}_{timestamp}.pdf'
                            filepath = Path(self.download_dir) / filename

                            download.save_as(str(filepath))
                            self.logger.info(f"Certificate downloaded: {filepath}")
                            clicked = True

                except Exception as e:
                    self.logger.debug(f"2a Via fallback failed: {e}")

            # OCR fallback for download
            if not clicked:
                self.logger.info("Trying OCR to find download icon...")
                result = self.find_text_with_ocr('Via', avoid_right_side=False)
                if result:
                    x, y, w, h = result
                    # Click to the right of "Via" text where icon should be
                    click_x = x + w + 30
                    click_y = y + h // 2

                    try:
                        with self.page.expect_download(timeout=30000) as download_info:
                            self.page.mouse.click(click_x, click_y)

                        download = download_info.value
                        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                        filename = f'federal_{self.cnpj_raw}_{timestamp}.pdf'
                        filepath = Path(self.download_dir) / filename

                        download.save_as(str(filepath))
                        self.logger.info(f"Certificate downloaded: {filepath}")
                        clicked = True

                    except Exception as e:
                        self.logger.warning(f"OCR download click failed: {e}")

            if not clicked:
                self.logger.error("Could not download certificate!")
                return False

            self.human_delay(1.0, 2.0)
            self.take_screenshot('step4_download_complete')
            return True

        except Exception as e:
            self.logger.error(f"Step 4 failed: {e}")
            self.take_screenshot('step4_error')
            return False

    def run(self) -> bool:
        """
        Execute the complete certificate generation flow.

        Returns:
            True if successful
        """
        self.logger.info("=" * 60)
        self.logger.info(f"CERTIDAO FEDERAL - CNPJ: {self.cnpj}")
        self.logger.info("Playwright + OCR automation")
        self.logger.info("=" * 60)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Setup browser
                if not self.page:
                    if not self.setup_browser():
                        return False

                # Garante que a página está em foco antes de começar
                self.page.bring_to_front()

                # Execute flow
                if not self.step1_fill_cnpj_and_emit():
                    retry_count += 1
                    self.logger.warning(f"Step 1 failed, retrying ({retry_count}/{max_retries})...")
                    self.human_delay(2.0, 3.0)
                    continue

                if not self.step2_handle_modal():
                    retry_count += 1
                    self.logger.warning(f"Step 2 failed, retrying ({retry_count}/{max_retries})...")
                    self.human_delay(2.0, 3.0)
                    continue

                if not self.step3_date_selection():
                    retry_count += 1
                    self.logger.warning(f"Step 3 failed, retrying ({retry_count}/{max_retries})...")
                    self.human_delay(2.0, 3.0)
                    continue

                if not self.step4_download_certificate():
                    retry_count += 1
                    self.logger.warning(f"Step 4 failed, retrying ({retry_count}/{max_retries})...")
                    self.human_delay(2.0, 3.0)
                    continue

                # Success!
                self.logger.info("=" * 60)
                self.logger.info("SUCCESS! Certificate downloaded.")
                self.logger.info("=" * 60)
                return True

            except Exception as e:
                self.logger.error(f"Error during automation: {e}", exc_info=True)
                self.take_screenshot('error_exception')
                retry_count += 1

                if retry_count < max_retries:
                    self.logger.info(f"Retrying ({retry_count}/{max_retries})...")
                    self.human_delay(2.0, 3.0)

        self.logger.error(f"Failed after {max_retries} retries")
        return False

    def close(self):
        """Close browser, Playwright, and Chrome process."""
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception as e:
                    self.logger.debug(f"Error closing page: {e}")
                self.page = None

            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    self.logger.debug(f"Error closing browser: {e}")
                self.browser = None

            if self.context:
                self.context = None

            if self._playwright_context:
                try:
                    self._playwright_context.stop()
                except Exception as e:
                    self.logger.debug(f"Error stopping playwright: {e}")
                self._playwright_context = None

            # Terminate the Chrome subprocess
            if self.chrome_process:
                try:
                    self.chrome_process.terminate()
                    self.chrome_process.wait(timeout=5)
                    self.logger.info("Chrome process terminated")
                except Exception as e:
                    self.logger.debug(f"Error terminating Chrome process: {e}")
                    # Force kill if terminate didn't work
                    try:
                        self.chrome_process.kill()
                    except:
                        pass
                self.chrome_process = None

            self.logger.info("Browser and Chrome process closed successfully")

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def run_interactive():
    """Interactive mode for testing."""
    print("\n" + "=" * 60)
    print("CERTIDAO FEDERAL - Playwright + OCR")
    print("=" * 60)
    print("""
Opcoes:
1. Gerar certidao (fluxo completo)
2. Testar OCR (encontrar texto na tela)
3. Tirar screenshot
4. Testar navegacao basica

    """)

    choice = input("Escolha (1-4): ").strip()

    if choice == "1":
        cnpj = input("Digite o CNPJ (somente numeros): ").strip()
        if not cnpj:
            cnpj = "75658377000131"  # Default for testing
            print(f"Usando CNPJ padrao: {cnpj}")

        print("\nIniciando automacao...")

        with FederalVisualCertificate(cnpj=cnpj) as cert:
            result = cert.run()
            print(f"\nResultado: {'SUCESSO' if result else 'FALHOU'}")

    elif choice == "2":
        text = input("Texto para buscar na tela: ").strip()
        if not text:
            text = "CNPJ"

        print(f"\nBuscando '{text}' na tela...")

        with FederalVisualCertificate(cnpj="00000000000000") as cert:
            cert.setup_browser()  # Already loads the URL
            cert.human_delay(3.0, 5.0)

            result = cert.find_text_with_ocr(text)

            if result:
                x, y, w, h = result
                print(f"ENCONTRADO em ({x}, {y}), tamanho {w}x{h}")
            else:
                print("NAO ENCONTRADO")

    elif choice == "3":
        print("\nTirando screenshot...")

        with FederalVisualCertificate(cnpj="00000000000000") as cert:
            cert.setup_browser()  # Already loads the URL
            cert.human_delay(3.0, 5.0)
            filepath = cert.take_screenshot('manual_test')
            print(f"Screenshot salvo em: {filepath}")

    elif choice == "4":
        print("\nTestando navegacao basica...")

        with FederalVisualCertificate(cnpj="00000000000000") as cert:
            cert.setup_browser()  # Already loads the URL
            print(f"Pagina carregada: {cert.page.url}")
            cert.human_delay(5.0, 10.0)
            print("Fechando...")

    else:
        print("Opcao invalida!")


if __name__ == "__main__":
    run_interactive()
