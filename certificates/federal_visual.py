"""
Federal Certificate (Receita Federal) - Visual Automation Implementation

This module uses professional visual automation (PyAutoGUI + OpenCV + OCR) to:
1. Find elements by image templates (template matching)
2. Find elements by text (OCR)
3. Execute human-like interactions

This approach is undetectable because it:
- Uses real OS-level mouse/keyboard events
- Opens the browser normally (no WebDriver)
- Has no JavaScript injection

Author: Certificate Collector Team
Version: 1.0.0
"""

import os
import sys
import time
import random
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.visual_automation import VisualAutomation, FindStrategy, ElementMatch, ProtectedAutomation
from core.logger import get_logger
from core.config import get_config


class FederalCertificateVisual:
    """
    Federal Certificate generator using Visual Automation.

    This implementation is completely undetectable because it:
    1. Opens Chrome normally (not via WebDriver)
    2. Uses PyAutoGUI for native OS input events
    3. Finds elements visually (template matching + OCR)
    """

    # Template names for elements
    TEMPLATES = {
        'campo_cnpj': 'federal/campo_cnpj',
        'btn_consultar': 'federal/btn_consultar_certidao',
        'btn_emitir': 'federal/btn_emitir_certidao',
        'btn_aceitar_cookies': 'federal/btn_aceitar_cookies',
        'btn_consultar_submit': 'federal/btn_consultar_certidao_submit',  # Blue button on date selection page
        'icon_download': 'federal/icon_download',  # Download icon in results table
        'campo_data': 'federal/campo_data',
        'msg_erro': 'federal/msg_erro',
        'certidao_pdf': 'federal/certidao_pdf',
    }

    # Text patterns for OCR fallback
    TEXT_PATTERNS = {
        'cnpj_label': 'CNPJ',
        'consultar': 'Consultar',
        'emitir': 'Emitir',
        'aceitar': 'Aceitar',
        'certidao': 'Certidão',
    }

    def __init__(self, cnpj: str, start_date: str = None):
        """
        Initialize the visual automation certificate generator.

        Args:
            cnpj: Company CNPJ number
            start_date: Optional start date for certificate (DD/MM/YYYY)
        """
        self.cnpj = self._format_cnpj(cnpj)
        self.cnpj_raw = cnpj.replace('.', '').replace('/', '').replace('-', '')
        self.start_date = start_date
        self.config = get_config()
        self.logger = get_logger('FederalVisual')

        # Initialize visual automation engine
        templates_dir = project_root / 'core' / 'templates'
        self.visual = VisualAutomation(templates_dir=str(templates_dir))

        self.url = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"
        self.chrome_process = None

    def _format_cnpj(self, cnpj: str) -> str:
        """Format CNPJ with punctuation."""
        cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj

    def _find_chrome(self) -> Optional[str]:
        """Find Chrome executable on the system."""
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                return path

        # Try to find via which/where
        try:
            if sys.platform == 'win32':
                result = subprocess.run(['where', 'chrome'], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass

        return None

    def _open_browser(self) -> bool:
        """Open Chrome browser with the target URL."""
        chrome_exe = self._find_chrome()
        if not chrome_exe:
            self.logger.error("Chrome not found! Please install Google Chrome.")
            return False

        self.logger.info(f"Opening Chrome: {chrome_exe}")

        try:
            # Open Chrome with user profile (normal mode, not WebDriver)
            self.chrome_process = subprocess.Popen([
                chrome_exe,
                "--start-maximized",
                self.url
            ])
            self.logger.info("Chrome opened successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to open Chrome: {e}")
            return False

    def _wait_for_page_load(self, timeout: float = 15.0) -> bool:
        """Wait for the page to fully load by looking for key elements."""
        self.logger.info("Waiting for page to load...")

        # First, wait a base time for initial load
        time.sleep(5)

        # Then look for the CNPJ field or related text
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('campo_cnpj'),
            text='CNPJ',
            timeout=timeout,
            strategy=FindStrategy.MULTI
        )

        if element:
            self.logger.info("Page loaded - CNPJ field found")
            return True

        self.logger.warning("Page load timeout - CNPJ field not found")
        return False

    def _handle_cookies_dialog(self) -> bool:
        """Accept cookies dialog if present."""
        self.logger.debug("Checking for cookies dialog...")

        # Try to find and click "Aceitar" button
        aceitar_element = self.visual.find_element(
            template_name=self.TEMPLATES.get('btn_aceitar_cookies'),
            text='Aceitar',
            timeout=3.0,
            strategy=FindStrategy.MULTI
        )

        if aceitar_element:
            self.logger.info("Cookies dialog found, clicking Accept...")
            self.visual.click(aceitar_element)
            self.visual.random_wait(0.5, 1.0)
            return True

        self.logger.debug("No cookies dialog found")
        return False

    def _find_cnpj_input(self) -> Optional[ElementMatch]:
        """Find the CNPJ input field."""
        self.logger.info("Looking for CNPJ input field...")

        # Strategy 1: Template matching
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('campo_cnpj'),
            confidence=0.7,
            timeout=5.0,
            strategy=FindStrategy.TEMPLATE
        )

        if element:
            return element

        # Strategy 2: OCR - find "CNPJ" label and click below it
        element = self.visual.find_element(
            text='CNPJ',
            timeout=5.0,
            strategy=FindStrategy.OCR
        )

        if element:
            # The input is typically below the label
            return ElementMatch(
                x=element.x,
                y=element.y + element.height + 10,
                width=200,
                height=40,
                confidence=element.confidence,
                strategy=FindStrategy.OCR
            )

        return None

    def _find_consultar_button(self) -> Optional[ElementMatch]:
        """Find the 'Consultar Certidão' button."""
        self.logger.info("Looking for Consultar button...")

        # Strategy 1: Template matching
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('btn_consultar'),
            confidence=0.7,
            timeout=5.0,
            strategy=FindStrategy.TEMPLATE
        )

        if element:
            return element

        # Strategy 2: OCR - find button by text
        element = self.visual.find_element(
            text='Consultar',
            timeout=5.0,
            strategy=FindStrategy.OCR
        )

        return element

    def _find_emitir_button(self) -> Optional[ElementMatch]:
        """Find the 'Emitir Certidão' button."""
        self.logger.info("Looking for Emitir button...")

        # Strategy 1: Template matching
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('btn_emitir'),
            confidence=0.7,
            timeout=5.0,
            strategy=FindStrategy.TEMPLATE
        )

        if element:
            return element

        # Strategy 2: OCR - find button by text
        element = self.visual.find_element(
            text='Emitir',
            timeout=5.0,
            strategy=FindStrategy.OCR
        )

        return element

    def _find_consultar_submit_button(self) -> Optional[ElementMatch]:
        """Find the blue 'Consultar Certidão' submit button on date selection page."""
        self.logger.info("Looking for Consultar submit button (blue)...")

        # Strategy 1: Template matching (specific blue button)
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('btn_consultar_submit'),
            confidence=0.7,
            timeout=5.0,
            strategy=FindStrategy.TEMPLATE
        )

        if element:
            return element

        # Strategy 2: OCR fallback
        element = self.visual.find_element(
            text='Consultar Certidao',
            timeout=5.0,
            strategy=FindStrategy.OCR
        )

        return element

    def _find_download_icon(self) -> Optional[ElementMatch]:
        """Find the download icon in the results table."""
        self.logger.info("Looking for download icon...")

        # Strategy 1: Template matching
        element = self.visual.find_element(
            template_name=self.TEMPLATES.get('icon_download'),
            confidence=0.7,
            timeout=5.0,
            strategy=FindStrategy.TEMPLATE
        )

        if element:
            return element

        # Strategy 2: Find all download icons and return the first one
        icons = self.visual.find_all_elements(
            template_name=self.TEMPLATES.get('icon_download'),
            confidence=0.6
        )

        if icons:
            # Return the first (topmost) icon
            icons.sort(key=lambda e: e.y)
            return icons[0]

        return None

    def _check_for_error(self) -> Optional[str]:
        """Check if an error message is displayed."""
        # Only use template matching for error detection (OCR gives false positives)
        # Skip if no error template exists
        error_template = self.TEMPLATES.get('msg_erro')
        if not error_template:
            return None

        error_element = self.visual.find_element(
            template_name=error_template,
            confidence=0.8,
            timeout=1.0,
            strategy=FindStrategy.TEMPLATE
        )

        if error_element:
            # Take screenshot of error
            self.visual.take_screenshot(
                str(project_root / 'screenshots' / f'federal_visual_error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            )
            return "Error detected on page"

        return None

    def generate(self, use_protection: bool = True) -> bool:
        """
        Generate Federal certificate using visual automation.

        Flow:
        1. Open Chrome normally
        2. Wait for page to load
        3. Handle cookies dialog
        4. Find and fill CNPJ field (visual)
        5. Click Consultar/Emitir button (visual)
        6. Wait for date page
        7. Click Consultar submit button
        8. Wait for results table
        9. Click download icon
        10. Wait for download

        Args:
            use_protection: If True, shows overlay and uses safe clicks with recovery

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Starting Federal certificate generation for CNPJ: {self.cnpj}")
        self.logger.info("Using Visual Automation (PyAutoGUI + OpenCV)")
        self.logger.info(f"Protection mode: {'ENABLED' if use_protection else 'DISABLED'}")

        try:
            # Step 1: Open browser (before protection starts)
            self.logger.info("[1/10] Opening browser...")
            if not self._open_browser():
                return False

            # Step 2: Wait for page to load
            self.logger.info("[2/10] Waiting for page to load...")
            if not self._wait_for_page_load():
                self.logger.error("Page failed to load")
                self.visual.take_screenshot(str(project_root / 'screenshots' / 'federal_visual_load_failed.png'))
                return False

            # Start protected automation session
            with ProtectedAutomation(self.visual, show_overlay=use_protection) as protected:

                # Step 3: Handle cookies dialog
                self.logger.info("[3/10] Handling cookies dialog...")
                aceitar_element = self.visual.find_element(
                    template_name=self.TEMPLATES.get('btn_aceitar_cookies'),
                    text='Aceitar',
                    timeout=3.0,
                    strategy=FindStrategy.MULTI
                )
                if aceitar_element:
                    protected.safe_click(aceitar_element)
                    protected.random_wait(0.5, 1.0)

                # Step 4: Find and fill CNPJ
                self.logger.info("[4/10] Filling CNPJ...")
                cnpj_input = self._find_cnpj_input()

                if not cnpj_input:
                    self.logger.error("CNPJ input field not found!")
                    self.visual.take_screenshot(str(project_root / 'screenshots' / 'federal_visual_no_cnpj.png'))
                    return False

                # Click on input and type CNPJ (with protection)
                if not protected.safe_click(cnpj_input):
                    self.logger.error("Failed to click CNPJ input")
                    return False

                protected.random_wait(0.3, 0.6)

                if not protected.safe_type(self.cnpj_raw, human_like=True):
                    self.logger.error("Failed to type CNPJ")
                    return False

                self.logger.info(f"CNPJ typed: {self.cnpj}")
                protected.random_wait(1.0, 2.0)

                # Step 5: Click Consultar/Emitir button (first page)
                self.logger.info("[5/10] Clicking first submit button...")

                submit_btn = self._find_consultar_button()
                if not submit_btn:
                    submit_btn = self._find_emitir_button()

                if not submit_btn:
                    self.logger.error("Submit button not found!")
                    self.visual.take_screenshot(str(project_root / 'screenshots' / 'federal_visual_no_button.png'))
                    return False

                if not protected.safe_click(submit_btn):
                    self.logger.error("Failed to click submit button")
                    return False

                self.logger.info("First submit button clicked")

                # Step 6: Wait for date selection page
                self.logger.info("[6/10] Waiting for date selection page...")
                protected.random_wait(3.0, 5.0)

                # Check for error
                error = self._check_for_error()
                if error:
                    self.logger.error(f"Error from site: {error}")
                    return False

                # Step 7: Click the blue "Consultar Certidão" button on date page
                self.logger.info("[7/10] Looking for Consultar submit button on date page...")
                consultar_submit = self._find_consultar_submit_button()

                if consultar_submit:
                    self.logger.info("Found Consultar submit button, clicking...")
                    if not protected.safe_click(consultar_submit):
                        self.logger.warning("Failed to click Consultar submit button")
                    protected.random_wait(3.0, 5.0)
                else:
                    self.logger.warning("Consultar submit button not found - may already be on result page")

                # Step 8: Wait for results table
                self.logger.info("[8/10] Waiting for results table...")
                protected.random_wait(3.0, 5.0)

                # Check for error
                error = self._check_for_error()
                if error:
                    self.logger.error(f"Error from site: {error}")
                    return False

                # Take screenshot of results
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.visual.take_screenshot(
                    str(project_root / 'screenshots' / f'federal_visual_result_{timestamp}.png')
                )

                # Step 9: Find and click download icon
                self.logger.info("[9/10] Looking for download icon...")
                download_icon = self._find_download_icon()

                if download_icon:
                    self.logger.info("Found download icon, clicking...")
                    if not protected.safe_click(download_icon):
                        self.logger.warning("Failed to click download icon")
                        return False
                    protected.random_wait(2.0, 4.0)
                else:
                    self.logger.warning("Download icon not found - certificate may need manual download")
                    return False

                # Step 10: Wait for download to complete
                self.logger.info("[10/10] Waiting for download...")
            self.visual.random_wait(3.0, 5.0)

            # Take final screenshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.visual.take_screenshot(
                str(project_root / 'screenshots' / f'federal_visual_download_{timestamp}.png')
            )

            self.logger.info("Process completed - PDF should be downloaded")
            return True

        except Exception as e:
            self.logger.error(f"Error during generation: {e}", exc_info=True)
            self.visual.take_screenshot(str(project_root / 'screenshots' / 'federal_visual_exception.png'))
            return False

    def capture_templates(self):
        """Interactive mode to capture element templates."""
        print("\n" + "=" * 60)
        print("FEDERAL CERTIFICATE - TEMPLATE CAPTURE MODE")
        print("=" * 60)
        print("""
This will help you capture templates for visual element recognition.
You need to have the Receita Federal page open in Chrome.

For each element, you'll select the region on screen.
        """)

        input("Press Enter when the page is open and ready...")

        templates_to_capture = [
            ('federal/campo_cnpj', 'CNPJ input field'),
            ('federal/btn_consultar_certidao', 'Consultar Certidão button'),
            ('federal/btn_emitir_certidao', 'Emitir Certidão button'),
            ('federal/btn_aceitar_cookies', 'Aceitar (cookies) button'),
        ]

        for template_name, description in templates_to_capture:
            print(f"\n📸 Capturing: {description}")
            print(f"   Template name: {template_name}")

            proceed = input("   Capture this template? (y/n/skip): ").strip().lower()
            if proceed == 'skip':
                continue
            elif proceed != 'y':
                break

            self.visual.capture_template(template_name, interactive=True)

        print("\n✅ Template capture completed!")
        print(f"   Templates saved in: {self.visual.templates_dir}")


def run_interactive():
    """Interactive mode for testing and template capture."""
    print("\n" + "=" * 60)
    print("FEDERAL CERTIFICATE - VISUAL AUTOMATION")
    print("=" * 60)
    print("""
Options:
1. Generate certificate (WITH protection - recommended)
2. Generate certificate (WITHOUT protection)
3. Capture templates interactively
4. Test element finding
5. Take screenshot
    """)

    choice = input("Enter choice (1-5): ").strip()

    if choice == "1":
        cnpj = input("Enter CNPJ (numbers only): ").strip() or "75658377000131"
        print("\n[PROTECTION ENABLED]")
        print("- Overlay will be shown")
        print("- Safe clicks with recovery")
        print("- Move mouse to TOP-LEFT corner to cancel\n")
        cert = FederalCertificateVisual(cnpj=cnpj)
        result = cert.generate(use_protection=True)
        print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")

    elif choice == "2":
        cnpj = input("Enter CNPJ (numbers only): ").strip() or "75658377000131"
        print("\n[PROTECTION DISABLED]")
        print("- No overlay")
        print("- Standard clicks (no recovery)\n")
        cert = FederalCertificateVisual(cnpj=cnpj)
        result = cert.generate(use_protection=False)
        print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")

    elif choice == "3":
        cert = FederalCertificateVisual(cnpj="00000000000000")
        cert.capture_templates()

    elif choice == "4":
        templates_dir = project_root / 'core' / 'templates'
        visual = VisualAutomation(templates_dir=str(templates_dir))

        print("\nTesting element finding...")
        print("Looking for 'CNPJ' text on screen...")

        element = visual.find_element(text='CNPJ', timeout=5.0, strategy=FindStrategy.OCR)
        if element:
            print(f"[OK] Found at: ({element.x}, {element.y}), confidence: {element.confidence:.2f}")
            print(f"   Click to highlight? (y/n): ", end="")
            if input().strip().lower() == 'y':
                visual.move_to(element)
        else:
            print("[NOT FOUND]")

    elif choice == "5":
        templates_dir = project_root / 'core' / 'templates'
        visual = VisualAutomation(templates_dir=str(templates_dir))

        filepath = project_root / 'screenshots' / f'manual_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        visual.take_screenshot(str(filepath))
        print(f"Screenshot saved: {filepath}")

    else:
        print("Invalid choice")


if __name__ == "__main__":
    run_interactive()
