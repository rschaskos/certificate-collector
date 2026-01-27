"""
Federal Certificate (Receita Federal) implementation using undetected-chromedriver

This implementation bypasses bot detection that blocks Playwright.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from core.browser_undetected import UndetectedBrowserManager
from core.logger import get_logger
from core.config import get_config


class FederalCertificateUndetected:
    """
    Generates Federal certificate using undetected-chromedriver.

    This bypasses the bot detection on servicos.receitafederal.gov.br
    """

    def __init__(self, cnpj: str, start_date: str = None):
        """
        Initialize certificate generator.

        Args:
            cnpj: Company CNPJ number
            start_date: Optional start date for certificate (DD/MM/YYYY)
        """
        self.cnpj = cnpj
        self.start_date = start_date
        self.config = get_config()
        self.logger = get_logger('FederalUndetected')
        self.browser = UndetectedBrowserManager()
        self.url = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"

    def generate(self) -> bool:
        """
        Generate Federal certificate.

        Flow:
        1. Start undetected browser
        2. Navigate to Receita Federal
        3. Fill CNPJ
        4. Click "Consultar Certidão"
        5. Fill start date if required
        6. Submit and download PDF

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Federal certificate generation for CNPJ: {self.cnpj}')

        try:
            # Start browser
            if not self.browser.start(headless=False):
                return False

            driver = self.browser.driver

            # Navigate to page
            if not self.browser.navigate(self.url):
                return False

            # Wait for page to fully load
            time.sleep(3)
            self.browser.human_delay(1000, 2000)

            # Find and fill CNPJ input
            # The input is inside a custom component: br-input
            self.logger.info('Looking for CNPJ input...')

            # Try to find the input field
            cnpj_input = None

            # Strategy 1: Direct CSS selector
            try:
                cnpj_input = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    "br-input[placeholder='Informe o CNPJ'] input",
                    timeout=15
                )
            except:
                pass

            # Strategy 2: XPath
            if not cnpj_input:
                try:
                    cnpj_input = self.browser.wait_for_element(
                        By.XPATH,
                        "//br-input[@placeholder='Informe o CNPJ']//input",
                        timeout=10
                    )
                except:
                    pass

            # Strategy 3: Generic input search
            if not cnpj_input:
                try:
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "CNPJ" in placeholder.upper():
                            cnpj_input = inp
                            break
                except:
                    pass

            if not cnpj_input:
                self.logger.error('CNPJ input not found')
                self.browser.take_screenshot('federal_no_cnpj_input')
                return False

            self.logger.info('CNPJ input found, filling...')
            self.browser.human_delay(500, 1000)

            # Click and type CNPJ slowly
            self.browser.human_click(cnpj_input)
            self.browser.human_delay(300, 600)
            self.browser.slow_type(cnpj_input, self.cnpj)
            self.logger.info('CNPJ filled')

            self.browser.human_delay(1000, 2000)

            # Find and click "Consultar Certidão" button (first one - secondary)
            self.logger.info('Looking for Consultar button...')

            consultar_btn = None
            try:
                consultar_btn = self.browser.wait_for_clickable(
                    By.XPATH,
                    "//button[contains(@class, 'secondary') and contains(text(), 'Consultar')]",
                    timeout=10
                )
            except:
                pass

            if not consultar_btn:
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        text = btn.text or ""
                        classes = btn.get_attribute("class") or ""
                        if "Consultar" in text and "secondary" in classes:
                            consultar_btn = btn
                            break
                except:
                    pass

            if not consultar_btn:
                self.logger.error('Consultar button not found')
                self.browser.take_screenshot('federal_no_consultar_btn')
                return False

            self.logger.info('Clicking Consultar button...')
            self.browser.human_click(consultar_btn)

            # Wait for date field to appear (if required)
            self.browser.human_delay(2000, 3000)

            # Check if date input appeared
            date_input = None
            try:
                date_input = self.browser.wait_for_element(
                    By.CSS_SELECTOR,
                    "input[placeholder='Selecione a data']",
                    timeout=10
                )
            except:
                pass

            if date_input and self.start_date:
                self.logger.info('Date input found, filling...')
                self.browser.human_click(date_input)
                self.browser.human_delay(300, 500)
                self.browser.slow_type(date_input, self.start_date)
                self.browser.human_delay(500, 1000)

            # Find and click submit button
            self.logger.info('Looking for submit button...')
            submit_btn = None
            try:
                submit_btn = self.browser.wait_for_clickable(
                    By.XPATH,
                    "//button[@type='submit' and contains(text(), 'Consultar')]",
                    timeout=10
                )
            except:
                pass

            if not submit_btn:
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        text = btn.text or ""
                        btn_type = btn.get_attribute("type") or ""
                        if "Consultar" in text and btn_type == "submit":
                            submit_btn = btn
                            break
                except:
                    pass

            if submit_btn:
                self.logger.info('Clicking submit button...')
                self.browser.human_click(submit_btn)
                self.browser.human_delay(3000, 5000)

            # Wait for result
            time.sleep(5)

            # Check for error message
            try:
                error_elements = driver.find_elements(By.CLASS_NAME, "alert-danger")
                for err in error_elements:
                    if err.is_displayed():
                        error_text = err.text
                        self.logger.error(f'Error from site: {error_text}')
                        self.browser.take_screenshot('federal_error_message')
                        # Don't return False yet - maybe we can still proceed
            except:
                pass

            # Try to find download link or save page as PDF
            self.logger.info('Looking for certificate/download...')

            # Strategy 1: Look for download link
            download_link = None
            try:
                download_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Download')]")
            except:
                pass

            if download_link:
                self.logger.info('Download link found, clicking...')
                self.browser.human_click(download_link)
                time.sleep(5)

                # Get downloaded file
                downloaded = self.browser.get_downloaded_file(timeout=30)
                if downloaded:
                    # Rename file
                    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    new_name = self.config.get_path('downloads') / f'FEDERAL_{self.cnpj}_{timestamp}.pdf'
                    downloaded.rename(new_name)
                    self.logger.info(f'Certificate downloaded: {new_name.name}')
                    return True

            # Strategy 2: Save page as PDF
            self.logger.info('Trying to save page as PDF...')
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filepath = self.config.get_path('downloads') / f'FEDERAL_{self.cnpj}_{timestamp}.pdf'

            if self.browser.save_page_as_pdf(str(filepath)):
                self.logger.info(f'Certificate saved as PDF: {filepath.name}')
                return True

            self.browser.take_screenshot('federal_final_state')
            return False

        except Exception as e:
            self.logger.error(f'Error generating Federal certificate: {e}', exc_info=True)
            self.browser.take_screenshot('federal_exception')
            return False

        finally:
            self.browser.stop()


def test_federal_undetected():
    """Test function for Federal certificate with undetected-chromedriver."""
    cert = FederalCertificateUndetected(
        cnpj="75658377000131",
        start_date="01/01/2024"
    )
    result = cert.generate()
    print(f"Result: {'Success' if result else 'Failed'}")


def test_federal_with_real_profile():
    """
    Test with real Chrome profile for maximum stealth.
    Uses your actual Chrome profile with history, cookies, etc.
    """
    import undetected_chromedriver as uc
    import time
    import os

    print("Starting Chrome with REAL user profile...")
    print("This will use your actual Chrome data (cookies, history, etc.)")

    # Path to your real Chrome profile
    # Windows default: C:\Users\USERNAME\AppData\Local\Google\Chrome\User Data
    user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

    # Check if Chrome profile exists
    if not os.path.exists(user_data_dir):
        print(f"Chrome profile not found at: {user_data_dir}")
        print("Trying Edge profile...")
        user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")

    if not os.path.exists(user_data_dir):
        print("No browser profile found. Running without profile.")
        user_data_dir = None

    options = uc.ChromeOptions()

    if user_data_dir:
        print(f"Using profile: {user_data_dir}")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--window-size=1920,1080")

    try:
        # IMPORTANT: Close Chrome completely before running this!
        print("\n⚠️  IMPORTANT: Close ALL Chrome windows before continuing!")
        input("Press Enter when Chrome is completely closed...")

        driver = uc.Chrome(options=options, use_subprocess=True)

        print("Navigating to Receita Federal...")
        driver.get("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")

        print("\n" + "="*60)
        print("Browser opened with your real profile!")
        print("="*60)
        print("\nNow YOU can:")
        print("1. Fill the CNPJ manually")
        print("2. Solve any CAPTCHA that appears")
        print("3. Click 'Consultar Certidão'")
        print("\nThis tests if the site accepts your real browser profile.")
        print("Press Enter when done to close the browser...")
        input()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass


def test_federal_semi_manual():
    """
    Semi-manual test: Automation fills CNPJ, user solves CAPTCHA if needed.
    """
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    import time
    import random

    print("Starting semi-manual test...")
    print("Automation will fill CNPJ, you handle CAPTCHA if it appears.\n")

    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--window-size=1366,768")

    # More human-like settings
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    driver = uc.Chrome(options=options, use_subprocess=True, version_main=None)

    try:
        print("Navigating to Receita Federal...")
        driver.get("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")

        # Wait longer for page to stabilize
        print("Waiting for page to load...")
        time.sleep(5)

        # Move mouse randomly to simulate human
        print("Simulating human behavior...")
        driver.execute_script("""
            // Simulate mouse movement
            document.dispatchEvent(new MouseEvent('mousemove', {
                bubbles: true,
                clientX: Math.random() * window.innerWidth,
                clientY: Math.random() * window.innerHeight
            }));
        """)
        time.sleep(2)

        # Find CNPJ input
        print("Looking for CNPJ input...")
        cnpj_input = None

        for _ in range(10):
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "CNPJ" in placeholder.upper():
                            cnpj_input = inp
                            break
                if cnpj_input:
                    break
            except:
                pass
            time.sleep(1)

        if not cnpj_input:
            print("CNPJ input not found!")
            input("Press Enter to close...")
            return

        print("Found CNPJ input, clicking...")

        # Scroll to element first
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", cnpj_input)
        time.sleep(1)

        # Click with JavaScript to avoid detection
        driver.execute_script("arguments[0].click();", cnpj_input)
        time.sleep(0.5)

        # Type CNPJ slowly with random delays
        cnpj = "75658377000131"
        print(f"Typing CNPJ: {cnpj}")

        for char in cnpj:
            cnpj_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))

        print("CNPJ filled!")
        time.sleep(2)

        # Find and click Consultar button
        print("Looking for Consultar button...")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        consultar_btn = None

        for btn in buttons:
            try:
                text = btn.text or ""
                classes = btn.get_attribute("class") or ""
                if "Consultar" in text and "secondary" in classes:
                    consultar_btn = btn
                    break
            except:
                continue

        if consultar_btn:
            print("Clicking Consultar button...")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", consultar_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", consultar_btn)
        else:
            print("Consultar button not found!")

        print("\n" + "="*60)
        print("Automation paused - check the browser!")
        print("="*60)
        print("\nIf there's a CAPTCHA, solve it manually.")
        print("If there's an error, take note of it.")
        print("\nPress Enter when done to close browser...")
        input()

    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")
    finally:
        driver.quit()


def test_federal_auto_with_real_profile():
    """
    Full automation using real Chrome profile.
    This combines the stealth of real profile with automation.
    """
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    import time
    import random
    import os

    print("="*60)
    print("FULL AUTOMATION WITH REAL CHROME PROFILE")
    print("="*60)
    print("\n⚠️  IMPORTANT: Close ALL Chrome windows before continuing!")
    input("Press Enter when Chrome is completely closed...")

    # Path to real Chrome profile
    user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

    if not os.path.exists(user_data_dir):
        print(f"Chrome profile not found, trying Edge...")
        user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")

    options = uc.ChromeOptions()

    if os.path.exists(user_data_dir):
        print(f"Using profile: {user_data_dir}")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

    # Stealth options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    # Download settings
    downloads_path = str(Path('./downloads').resolve())
    prefs = {
        "download.default_directory": downloads_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        print("\n[1/7] Navigating to Receita Federal...")
        driver.get("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")

        # Wait for page to fully load
        print("[2/7] Waiting for page to load...")
        time.sleep(5)

        # Simulate human mouse movement
        print("[3/7] Simulating human behavior...")
        for _ in range(3):
            driver.execute_script("""
                document.dispatchEvent(new MouseEvent('mousemove', {
                    bubbles: true,
                    clientX: Math.random() * window.innerWidth,
                    clientY: Math.random() * window.innerHeight
                }));
            """)
            time.sleep(random.uniform(0.5, 1.5))

        # Find CNPJ input
        print("[4/7] Looking for CNPJ input...")
        cnpj_input = None

        for attempt in range(15):
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "CNPJ" in placeholder.upper():
                            cnpj_input = inp
                            break
                if cnpj_input:
                    break
            except:
                pass
            time.sleep(1)

        if not cnpj_input:
            print("❌ CNPJ input not found!")
            driver.save_screenshot("screenshots/federal_auto_no_input.png")
            input("Press Enter to close...")
            return False

        print("    ✓ CNPJ input found!")

        # Scroll to element smoothly
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            cnpj_input
        )
        time.sleep(random.uniform(0.8, 1.5))

        # Click the input
        driver.execute_script("arguments[0].click();", cnpj_input)
        time.sleep(random.uniform(0.3, 0.7))

        # Type CNPJ with human-like delays
        cnpj = "75658377000131"
        print(f"[5/7] Typing CNPJ: {cnpj}")

        for char in cnpj:
            cnpj_input.send_keys(char)
            time.sleep(random.uniform(0.08, 0.25))

        print("    ✓ CNPJ filled!")
        time.sleep(random.uniform(1.5, 2.5))

        # Find Consultar button
        print("[6/7] Looking for Consultar button...")
        consultar_btn = None

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                text = btn.text or ""
                classes = btn.get_attribute("class") or ""
                if "Consultar" in text and "secondary" in classes and btn.is_displayed():
                    consultar_btn = btn
                    break
            except:
                continue

        if not consultar_btn:
            print("❌ Consultar button not found!")
            driver.save_screenshot("screenshots/federal_auto_no_button.png")
            input("Press Enter to close...")
            return False

        print("    ✓ Consultar button found!")

        # Scroll to button and click
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            consultar_btn
        )
        time.sleep(random.uniform(0.8, 1.2))

        # Click with JavaScript
        print("[7/7] Clicking Consultar button...")
        driver.execute_script("arguments[0].click();", consultar_btn)

        # Wait for response
        print("\nWaiting for response...")
        time.sleep(5)

        # Check for error
        try:
            error_elements = driver.find_elements(By.CLASS_NAME, "alert-danger")
            for err in error_elements:
                if err.is_displayed():
                    print(f"\n❌ ERROR FROM SITE: {err.text}")
                    driver.save_screenshot("screenshots/federal_auto_error.png")
                    input("\nPress Enter to close...")
                    return False
        except:
            pass

        # Check for success - look for date input or certificate
        print("\n✅ No error detected!")
        print("Checking for next step (date input or certificate)...")

        time.sleep(3)

        # Look for date input
        try:
            date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='data']")
            if date_inputs:
                print("✓ Date input found - proceeding...")
                # Could fill date here
        except:
            pass

        driver.save_screenshot("screenshots/federal_auto_success.png")
        print("\n" + "="*60)
        print("Screenshot saved! Check the browser window.")
        print("="*60)
        input("\nPress Enter to close browser...")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        driver.save_screenshot("screenshots/federal_auto_exception.png")
        input("Press Enter to close...")
        return False

    finally:
        driver.quit()


def test_federal_pyautogui():
    """
    Full automation using PyAutoGUI for NATIVE mouse/keyboard control.
    This is undetectable because it uses real OS-level input events.
    """
    try:
        import pyautogui
    except ImportError:
        print("PyAutoGUI not installed. Run: pip install pyautogui")
        return False

    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    import time
    import random
    import os
    import subprocess

    print("="*60)
    print("FULL AUTOMATION WITH PYAUTOGUI (NATIVE INPUT)")
    print("="*60)
    print("\nThis uses REAL mouse/keyboard control - undetectable!")
    print("\n⚠️  Closing any existing Chrome processes...")

    # Kill ALL Chrome-related processes forcefully
    chrome_processes = ['chrome.exe', 'chromedriver.exe', 'Google Chrome']
    for proc in chrome_processes:
        try:
            subprocess.run(['taskkill', '/f', '/im', proc],
                          capture_output=True, timeout=10)
        except:
            pass

    # Also try using wmic for stubborn processes
    try:
        subprocess.run(['wmic', 'process', 'where', "name='chrome.exe'", 'delete'],
                      capture_output=True, timeout=10)
    except:
        pass

    # Wait longer for profile to be released
    print("    Waiting for profile lock to be released...")
    time.sleep(5)

    print("✓ Chrome processes cleared")
    print("\n⚠️  IMPORTANT:")
    print("   1. Don't move the mouse during automation")
    print("   2. Keep the browser window visible")
    input("\nPress Enter when ready...")

    # PyAutoGUI settings
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1

    # Ask user which profile to use
    print("\nChoose profile:")
    print("1. Fresh profile (new, no history)")
    print("2. Real Chrome profile (may have lock issues)")
    print("3. Copy cookies from real profile ⭐ RECOMMENDED")

    profile_choice = input("\nEnter choice (1/2/3): ").strip()

    options = uc.ChromeOptions()

    # Automation profile path
    automation_profile = Path('./browser_profile_federal').resolve()
    automation_profile.mkdir(exist_ok=True)

    if profile_choice == "2":
        # Use REAL Chrome profile directly
        user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        if not os.path.exists(user_data_dir):
            user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")

        if os.path.exists(user_data_dir):
            print(f"\n✓ Using REAL profile: {user_data_dir}")
            print("⚠️  Make sure Chrome is completely closed!")
            input("Press Enter when Chrome is closed...")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument("--profile-directory=Default")
        else:
            print("Real profile not found, using fresh profile")
            options.add_argument(f"--user-data-dir={automation_profile}")

    elif profile_choice == "3":
        # Copy cookies from real profile to automation profile
        import shutil

        real_profile = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"))
        if not real_profile.exists():
            real_profile = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default"))

        auto_default = automation_profile / "Default"
        auto_default.mkdir(exist_ok=True)

        print(f"\nCopying cookies from: {real_profile}")
        print(f"To automation profile: {auto_default}")

        # Files to copy for session/cookies
        files_to_copy = ['Cookies', 'Cookies-journal', 'Login Data', 'Login Data-journal',
                        'Web Data', 'Web Data-journal', 'Preferences', 'Secure Preferences']

        copied = 0
        for filename in files_to_copy:
            src = real_profile / filename
            dst = auto_default / filename
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception as e:
                    print(f"    Could not copy {filename}: {e}")

        print(f"✓ Copied {copied} files with cookies/session data")
        options.add_argument(f"--user-data-dir={automation_profile}")

    else:
        # Use fresh profile
        print(f"\nUsing fresh profile: {automation_profile}")
        options.add_argument(f"--user-data-dir={automation_profile}")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options, use_subprocess=True)

    def human_move_to(x, y):
        """Move mouse to coordinates with human-like curve."""
        # Get current position
        current_x, current_y = pyautogui.position()

        # Calculate duration based on distance
        distance = ((x - current_x)**2 + (y - current_y)**2)**0.5
        duration = max(0.3, min(1.5, distance / 1000))

        # Move with random curve
        pyautogui.moveTo(
            x + random.randint(-3, 3),
            y + random.randint(-3, 3),
            duration=duration,
            tween=pyautogui.easeOutQuad
        )
        time.sleep(random.uniform(0.1, 0.3))

    def human_click(x, y):
        """Move to position and click like a human."""
        human_move_to(x, y)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.click()
        time.sleep(random.uniform(0.1, 0.3))

    def human_type(text):
        """Type text with human-like delays."""
        for char in text:
            pyautogui.press(char) if char.isdigit() else pyautogui.typewrite(char)
            time.sleep(random.uniform(0.05, 0.2))

    try:
        print("\n[1/6] Navigating to Receita Federal...")
        driver.get("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj")

        print("[2/6] Waiting for page to load...")
        time.sleep(5)

        # Random mouse movements to seem human
        print("[3/6] Simulating human presence...")
        for _ in range(3):
            x = random.randint(300, 800)
            y = random.randint(200, 500)
            human_move_to(x, y)
            time.sleep(random.uniform(0.5, 1.0))

        # Find CNPJ input element position
        print("[4/6] Looking for CNPJ input...")
        cnpj_input = None

        for attempt in range(15):
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if "CNPJ" in placeholder.upper():
                            cnpj_input = inp
                            break
                if cnpj_input:
                    break
            except:
                pass
            time.sleep(1)

        if not cnpj_input:
            print("❌ CNPJ input not found!")
            input("Press Enter to close...")
            return False

        # Get element position on screen
        location = cnpj_input.location
        size = cnpj_input.size

        # Get browser window position
        window_rect = driver.get_window_rect()
        browser_x = window_rect['x']
        browser_y = window_rect['y']

        # Calculate screen coordinates (accounting for browser chrome ~100px)
        element_x = browser_x + location['x'] + size['width'] // 2
        element_y = browser_y + location['y'] + size['height'] // 2 + 100  # +100 for toolbar

        print(f"    ✓ CNPJ input found at screen position ({element_x}, {element_y})")

        # Click on CNPJ input using PyAutoGUI (NATIVE click!)
        print("[5/6] Clicking and typing CNPJ with native input...")
        human_click(element_x, element_y)
        time.sleep(0.5)

        # Type CNPJ using PyAutoGUI (NATIVE keyboard!)
        cnpj = "75658377000131"
        print(f"    Typing: {cnpj}")
        human_type(cnpj)
        print("    ✓ CNPJ typed!")

        time.sleep(random.uniform(1.0, 2.0))

        # Find Consultar button
        print("[6/6] Looking for Consultar button...")
        consultar_btn = None

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                text = btn.text or ""
                classes = btn.get_attribute("class") or ""
                if "Consultar" in text and "secondary" in classes and btn.is_displayed():
                    consultar_btn = btn
                    break
            except:
                continue

        if not consultar_btn:
            print("❌ Consultar button not found!")
            input("Press Enter to close...")
            return False

        # Get button position
        location = consultar_btn.location
        size = consultar_btn.size
        btn_x = browser_x + location['x'] + size['width'] // 2
        btn_y = browser_y + location['y'] + size['height'] // 2 + 100

        print(f"    ✓ Consultar button found at ({btn_x}, {btn_y})")

        # Click button with native mouse
        print("    Clicking Consultar button...")
        human_click(btn_x, btn_y)

        # Wait for response
        print("\n⏳ Waiting for response...")
        time.sleep(5)

        # Check for error
        try:
            error_elements = driver.find_elements(By.CLASS_NAME, "alert-danger")
            for err in error_elements:
                if err.is_displayed():
                    print(f"\n❌ ERROR: {err.text}")
                    driver.save_screenshot("screenshots/federal_pyautogui_error.png")
                    input("\nPress Enter to close...")
                    return False
        except:
            pass

        driver.save_screenshot("screenshots/federal_pyautogui_result.png")
        print("\n" + "="*60)
        print("✅ Check the browser window for results!")
        print("   Screenshot saved to screenshots/federal_pyautogui_result.png")
        print("="*60)
        input("\nPress Enter to close browser...")
        return True

    except pyautogui.FailSafeException:
        print("\n⚠️ FAILSAFE triggered (mouse moved to corner)")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        input("Press Enter to close...")
        return False
    finally:
        driver.quit()


def test_federal_pyautogui_only():
    """
    Pure PyAutoGUI approach - no Selenium/Playwright connection needed.
    Opens Chrome normally and uses screen coordinates.
    """
    try:
        import pyautogui
        import pyperclip  # For clipboard
    except ImportError:
        print("Install required packages: pip install pyautogui pyperclip")
        return False

    import time
    import random
    import os
    import subprocess

    print("="*60)
    print("PURE PYAUTOGUI (NO SELENIUM/PLAYWRIGHT)")
    print("="*60)
    print("\nThis opens Chrome normally and uses native mouse/keyboard.")
    print("Works exactly like you doing it manually!")

    # Kill existing Chrome
    print("\n⚠️  Closing existing Chrome processes...")
    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], capture_output=True)
    time.sleep(2)

    # Find Chrome
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break

    if not chrome_exe:
        print("❌ Chrome not found!")
        return False

    print(f"✓ Found Chrome: {chrome_exe}")

    # Open Chrome normally (with user profile)
    url = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"
    print(f"\nOpening: {url}")

    subprocess.Popen([chrome_exe, "--start-maximized", url])
    print("✓ Chrome opened!")

    # Wait for page to load
    print("\nWaiting for page to fully load...")
    time.sleep(8)

    # PyAutoGUI settings
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    def human_move(x, y):
        current = pyautogui.position()
        dist = ((x-current[0])**2 + (y-current[1])**2)**0.5
        dur = max(0.2, min(0.8, dist/1500))
        pyautogui.moveTo(x + random.randint(-3,3), y + random.randint(-3,3),
                        duration=dur, tween=pyautogui.easeOutQuad)

    def human_click(x, y):
        human_move(x, y)
        time.sleep(random.uniform(0.05, 0.1))
        pyautogui.click()

    def human_type_text(text):
        """Type using clipboard (faster and more reliable)"""
        try:
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        except:
            # Fallback to typing
            for char in text:
                pyautogui.press(char)
                time.sleep(random.uniform(0.03, 0.08))

    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("="*60)
    print("""
The script will now:
1. Click on the CNPJ field (you need to tell me where it is)
2. Type the CNPJ
3. Click the Consultar button

First, I need to know where the CNPJ field is on your screen.
""")

    input("Press Enter when the page is fully loaded...")

    # Get screen size
    screen_w, screen_h = pyautogui.size()
    print(f"\nScreen size: {screen_w}x{screen_h}")

    # Ask user to position mouse on CNPJ field
    print("\n👉 Move your mouse over the CNPJ input field...")
    print("   Press Enter when mouse is positioned...")
    input()

    cnpj_pos = pyautogui.position()
    print(f"✓ CNPJ field position: {cnpj_pos}")

    # Ask for button position
    print("\n👉 Move your mouse over the 'Consultar Certidão' button...")
    print("   Press Enter when mouse is positioned...")
    input()

    btn_pos = pyautogui.position()
    print(f"✓ Button position: {btn_pos}")

    # Confirm
    print(f"\n📍 Positions saved:")
    print(f"   CNPJ field: {cnpj_pos}")
    print(f"   Button: {btn_pos}")

    proceed = input("\nProceed with automation? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Cancelled.")
        return False

    # Do the automation
    print("\n🚀 Starting automation...")
    print("   (Move mouse to screen corner to abort)")

    try:
        # Random mouse movement first
        print("\n[1/4] Moving mouse naturally...")
        for _ in range(2):
            x = random.randint(300, 800)
            y = random.randint(200, 400)
            human_move(x, y)
            time.sleep(random.uniform(0.3, 0.5))

        # Click CNPJ field
        print("[2/4] Clicking CNPJ field...")
        human_click(cnpj_pos[0], cnpj_pos[1])
        time.sleep(0.5)

        # Clear any existing text
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)

        # Type CNPJ
        cnpj = "75658377000131"
        print(f"[3/4] Typing CNPJ: {cnpj}")
        human_type_text(cnpj)
        time.sleep(random.uniform(0.8, 1.2))

        # Click button
        print("[4/4] Clicking Consultar button...")
        human_click(btn_pos[0], btn_pos[1])

        print("\n⏳ Waiting for response...")
        time.sleep(5)

        print("\n" + "="*60)
        print("✅ Automation complete!")
        print("   Check the browser window for results.")
        print("="*60)

        # Take screenshot using PyAutoGUI
        screenshot = pyautogui.screenshot()
        screenshot.save("screenshots/federal_pyautogui_pure.png")
        print("   Screenshot saved: screenshots/federal_pyautogui_pure.png")

        return True

    except pyautogui.FailSafeException:
        print("\n⚠️ Aborted (mouse moved to corner)")
        return False


def test_federal_remote_debug():
    """
    Opens Chrome with remote debugging, connects via Playwright CDP.
    """
    try:
        import pyautogui
    except ImportError:
        print("PyAutoGUI not installed. Run: pip install pyautogui")
        return False

    from playwright.sync_api import sync_playwright
    import time
    import random
    import os
    import subprocess

    print("="*60)
    print("CHROME REMOTE DEBUG + PLAYWRIGHT + PYAUTOGUI")
    print("="*60)

    # Kill existing Chrome
    print("\n⚠️  Closing existing Chrome processes...")
    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], capture_output=True)
    time.sleep(3)

    # Find Chrome executable
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break

    if not chrome_exe:
        print("❌ Chrome not found! Please install Google Chrome.")
        return False

    print(f"✓ Found Chrome: {chrome_exe}")

    # Start Chrome with remote debugging
    debug_port = 9222
    user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

    print(f"\nStarting Chrome with remote debugging on port {debug_port}...")

    chrome_cmd = [
        chrome_exe,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={user_data}",
        "--profile-directory=Default",
        "--start-maximized",
    ]

    # Start Chrome as separate process
    chrome_proc = subprocess.Popen(chrome_cmd)
    print("✓ Chrome started!")

    # Wait for Chrome to initialize
    print("Waiting for Chrome to initialize...")
    time.sleep(5)

    # PyAutoGUI settings
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    def human_move_to(x, y):
        current_x, current_y = pyautogui.position()
        distance = ((x - current_x)**2 + (y - current_y)**2)**0.5
        duration = max(0.3, min(1.2, distance / 1000))
        pyautogui.moveTo(x + random.randint(-2, 2), y + random.randint(-2, 2),
                        duration=duration, tween=pyautogui.easeOutQuad)
        time.sleep(random.uniform(0.05, 0.15))

    def human_click(x, y):
        human_move_to(x, y)
        time.sleep(random.uniform(0.03, 0.08))
        pyautogui.click()
        time.sleep(random.uniform(0.08, 0.15))

    def human_type(text):
        for char in text:
            pyautogui.press(char) if char.isdigit() else pyautogui.typewrite(char)
            time.sleep(random.uniform(0.04, 0.12))

    try:
        with sync_playwright() as p:
            print(f"Connecting to Chrome via CDP on port {debug_port}...")

            # Connect to existing Chrome via CDP
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
            print("✓ Connected to Chrome!")

            # Get existing context and page, or create new
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = context.new_page()
            else:
                context = browser.new_context()
                page = context.new_page()

            # Navigate to the URL
            print("\nNavigating to Receita Federal...")
            page.goto("https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj",
                     wait_until="domcontentloaded", timeout=30000)

            print("Waiting for page to load...")
            time.sleep(5)

            # Random mouse movements
            print("\n[1/5] Simulating human presence...")
            for _ in range(3):
                x = random.randint(400, 900)
                y = random.randint(250, 550)
                human_move_to(x, y)
                time.sleep(random.uniform(0.3, 0.6))

            # Find CNPJ input
            print("[2/5] Looking for CNPJ input...")
            cnpj_input = page.locator("input[placeholder*='CNPJ']").first

            try:
                cnpj_input.wait_for(state="visible", timeout=15000)
            except:
                print("❌ CNPJ input not found!")
                page.screenshot(path="screenshots/federal_cdp_no_input.png")
                input("Press Enter to close...")
                return False

            # Get bounding box
            box = cnpj_input.bounding_box()
            if not box:
                print("❌ Could not get element position!")
                return False

            # Calculate screen position (add window position offset)
            # For maximized window, usually starts at 0,0 but has title bar
            element_x = int(box['x'] + box['width'] / 2)
            element_y = int(box['y'] + box['height'] / 2 + 80)  # +80 for taskbar/title

            print(f"    ✓ Found CNPJ input at ({element_x}, {element_y})")

            # Click and type using PyAutoGUI (native input)
            print("[3/5] Clicking and typing CNPJ (native input)...")
            human_click(element_x, element_y)
            time.sleep(0.3)

            cnpj = "75658377000131"
            human_type(cnpj)
            print(f"    ✓ Typed: {cnpj}")

            time.sleep(random.uniform(1.0, 1.5))

            # Find Consultar button
            print("[4/5] Looking for Consultar button...")
            consultar_btn = page.locator("button.secondary:has-text('Consultar')").first

            try:
                consultar_btn.wait_for(state="visible", timeout=10000)
            except:
                # Try alternative selector
                consultar_btn = page.locator("button:has-text('Consultar Certidão')").first

            box = consultar_btn.bounding_box()
            if not box:
                print("❌ Button not found!")
                page.screenshot(path="screenshots/federal_cdp_no_button.png")
                input("Press Enter to close...")
                return False

            btn_x = int(box['x'] + box['width'] / 2)
            btn_y = int(box['y'] + box['height'] / 2 + 80)

            print(f"    ✓ Found button at ({btn_x}, {btn_y})")

            # Click using PyAutoGUI
            print("[5/5] Clicking Consultar (native click)...")
            human_click(btn_x, btn_y)

            print("\n⏳ Waiting for response...")
            time.sleep(5)

            # Check for error
            try:
                error = page.locator(".alert-danger").first
                if error.is_visible():
                    print(f"\n❌ ERROR: {error.text_content()}")
            except:
                pass

            page.screenshot(path="screenshots/federal_cdp_result.png")
            print("\n✓ Screenshot saved: screenshots/federal_cdp_result.png")

            print("\n" + "="*60)
            print("Check the browser window for results!")
            print("="*60)
            input("\nPress Enter to finish (Chrome will stay open)...")

            # Don't close browser - let user see result
            return True

    except pyautogui.FailSafeException:
        print("\n⚠️ Aborted (mouse moved to corner)")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FEDERAL CERTIFICATE - TEST MODES")
    print("="*60)
    print("\n1. Automatic (without profile)")
    print("2. Manual with real Chrome profile")
    print("3. Semi-manual (auto fill + manual CAPTCHA)")
    print("4. Full auto with real Chrome profile")
    print("5. PYAUTOGUI with undetected-chromedriver")
    print("6. Remote debug + Playwright")
    print("7. PURE PYAUTOGUI (simplest) ⭐ RECOMMENDED")

    choice = input("\nEnter choice (1-7): ").strip()

    if choice == "1":
        test_federal_undetected()
    elif choice == "2":
        test_federal_with_real_profile()
    elif choice == "3":
        test_federal_semi_manual()
    elif choice == "4":
        test_federal_auto_with_real_profile()
    elif choice == "5":
        test_federal_pyautogui()
    elif choice == "6":
        test_federal_remote_debug()
    elif choice == "7":
        test_federal_pyautogui_only()
    else:
        print("Invalid choice")
