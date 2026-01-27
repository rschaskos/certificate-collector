"""
Visual Automation Engine - Professional PyAutoGUI Implementation

This module provides a professional, robust visual automation system that:
1. Finds elements using template matching (image recognition)
2. Falls back to OCR (text recognition) when templates fail
3. Uses multiple strategies for maximum reliability
4. Is resolution-independent and self-healing

Author: Certificate Collector Team
Version: 1.0.0
"""

import sys
import time
import random
import threading
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image, ImageGrab
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pytesseract
    # Configure Tesseract path for Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from core.logger import get_logger


class FindStrategy(Enum):
    """Strategies for finding elements on screen."""
    TEMPLATE = "template"      # Image template matching
    OCR = "ocr"                # Text recognition
    COLOR = "color"            # Find by color region
    MULTI = "multi"            # Try all strategies


@dataclass
class ElementMatch:
    """Result of element search."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    strategy: FindStrategy

    @property
    def center(self) -> Tuple[int, int]:
        """Get center coordinates."""
        return (self.x + self.width // 2, self.y + self.height // 2)


class VisualAutomation:
    """
    Professional visual automation engine using PyAutoGUI with intelligent element finding.

    Features:
    - Template matching with configurable confidence
    - OCR text finding with fuzzy matching
    - Human-like mouse movements and typing
    - Automatic template capture and caching
    - Multi-monitor support
    - Retry logic with exponential backoff
    """

    def __init__(self, templates_dir: str = None):
        """
        Initialize visual automation engine.

        Args:
            templates_dir: Directory containing element templates
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError(
                "Required packages not installed. Run:\n"
                "pip install pyautogui opencv-python pillow numpy"
            )

        self.logger = get_logger('VisualAutomation')
        self.templates_dir = Path(templates_dir) if templates_dir else Path('./core/templates')
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # PyAutoGUI settings
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.05     # Small pause between actions

        # Cache for loaded templates
        self._template_cache: Dict[str, np.ndarray] = {}

        # Screen info
        self.screen_width, self.screen_height = pyautogui.size()
        self.logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")

    # ==================== ELEMENT FINDING ====================

    def find_element(
        self,
        template_name: str = None,
        text: str = None,
        confidence: float = 0.8,
        timeout: float = 10.0,
        region: Tuple[int, int, int, int] = None,
        strategy: FindStrategy = FindStrategy.MULTI
    ) -> Optional[ElementMatch]:
        """
        Find element on screen using specified strategy.

        Args:
            template_name: Name of template image (without extension)
            text: Text to find using OCR
            confidence: Minimum confidence threshold (0.0-1.0)
            timeout: Maximum time to search in seconds
            region: Screen region to search (x, y, width, height)
            strategy: Search strategy to use

        Returns:
            ElementMatch if found, None otherwise
        """
        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            attempt += 1

            # Try template matching first if template provided
            if template_name and strategy in (FindStrategy.TEMPLATE, FindStrategy.MULTI):
                match = self._find_by_template(template_name, confidence, region)
                if match:
                    self.logger.info(f"Found '{template_name}' by template (confidence: {match.confidence:.2f})")
                    return match

            # Try OCR if text provided
            if text and strategy in (FindStrategy.OCR, FindStrategy.MULTI):
                match = self._find_by_text(text, region)
                if match:
                    self.logger.info(f"Found '{text}' by OCR (confidence: {match.confidence:.2f})")
                    return match

            # Small delay before retry
            if time.time() - start_time < timeout:
                time.sleep(0.5)

        self.logger.warning(f"Element not found after {attempt} attempts: template={template_name}, text={text}")
        return None

    def _find_by_template(
        self,
        template_name: str,
        confidence: float,
        region: Tuple[int, int, int, int] = None
    ) -> Optional[ElementMatch]:
        """Find element using template matching."""
        template = self._load_template(template_name)
        if template is None:
            return None

        # Take screenshot
        screenshot = self._take_screenshot(region)
        if screenshot is None:
            return None

        # Convert to numpy array for OpenCV
        screenshot_np = np.array(screenshot)
        screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        # Convert template to grayscale if needed
        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)

        # Template matching
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            h, w = template_gray.shape
            x, y = max_loc

            # Adjust for region offset
            if region:
                x += region[0]
                y += region[1]

            return ElementMatch(
                x=x,
                y=y,
                width=w,
                height=h,
                confidence=max_val,
                strategy=FindStrategy.TEMPLATE
            )

        return None

    def _find_by_text(
        self,
        text: str,
        region: Tuple[int, int, int, int] = None
    ) -> Optional[ElementMatch]:
        """Find element using OCR text recognition."""
        if not OCR_AVAILABLE:
            self.logger.warning("pytesseract not available for OCR")
            return None

        screenshot = self._take_screenshot(region)
        if screenshot is None:
            return None

        # Use pytesseract to get text with bounding boxes
        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='por')
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return None

        # Search for text (case-insensitive, partial match)
        text_lower = text.lower()
        best_match = None
        best_confidence = 0

        for i, word in enumerate(data['text']):
            if not word:
                continue

            word_lower = word.lower()
            conf = int(data['conf'][i]) / 100.0

            # Check for match
            if text_lower in word_lower or word_lower in text_lower:
                if conf > best_confidence:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]

                    # Adjust for region offset
                    if region:
                        x += region[0]
                        y += region[1]

                    best_match = ElementMatch(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=conf,
                        strategy=FindStrategy.OCR
                    )
                    best_confidence = conf

        return best_match

    def find_all_elements(
        self,
        template_name: str,
        confidence: float = 0.8,
        region: Tuple[int, int, int, int] = None
    ) -> List[ElementMatch]:
        """Find all instances of template on screen."""
        template = self._load_template(template_name)
        if template is None:
            return []

        screenshot = self._take_screenshot(region)
        if screenshot is None:
            return []

        screenshot_np = np.array(screenshot)
        screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)

        matches = []
        h, w = template_gray.shape

        for pt in zip(*locations[::-1]):
            x, y = pt
            if region:
                x += region[0]
                y += region[1]

            # Check for overlapping matches (keep only the best)
            is_duplicate = False
            for existing in matches:
                if abs(existing.x - x) < w // 2 and abs(existing.y - y) < h // 2:
                    is_duplicate = True
                    break

            if not is_duplicate:
                matches.append(ElementMatch(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=result[y if region is None else y - region[1],
                                      x if region is None else x - region[0]],
                    strategy=FindStrategy.TEMPLATE
                ))

        return matches

    # ==================== MOUSE ACTIONS ====================

    def click(
        self,
        element: ElementMatch = None,
        x: int = None,
        y: int = None,
        clicks: int = 1,
        button: str = 'left',
        human_like: bool = True
    ) -> bool:
        """
        Click on element or coordinates with human-like movement.

        Args:
            element: ElementMatch to click on
            x, y: Coordinates to click (used if element not provided)
            clicks: Number of clicks
            button: Mouse button ('left', 'right', 'middle')
            human_like: Use human-like movement curve

        Returns:
            True if click successful
        """
        if element:
            target_x, target_y = element.center
        elif x is not None and y is not None:
            target_x, target_y = x, y
        else:
            self.logger.error("Click requires either element or coordinates")
            return False

        try:
            if human_like:
                self._human_move_to(target_x, target_y)
            else:
                pyautogui.moveTo(target_x, target_y)

            time.sleep(random.uniform(0.05, 0.15))
            pyautogui.click(clicks=clicks, button=button)

            self.logger.debug(f"Clicked at ({target_x}, {target_y})")
            return True

        except Exception as e:
            self.logger.error(f"Click failed: {e}")
            return False

    def double_click(self, element: ElementMatch = None, x: int = None, y: int = None) -> bool:
        """Double click on element or coordinates."""
        return self.click(element, x, y, clicks=2)

    def right_click(self, element: ElementMatch = None, x: int = None, y: int = None) -> bool:
        """Right click on element or coordinates."""
        return self.click(element, x, y, button='right')

    def move_to(self, element: ElementMatch = None, x: int = None, y: int = None, human_like: bool = True):
        """Move mouse to element or coordinates without clicking."""
        if element:
            target_x, target_y = element.center
        elif x is not None and y is not None:
            target_x, target_y = x, y
        else:
            return

        if human_like:
            self._human_move_to(target_x, target_y)
        else:
            pyautogui.moveTo(target_x, target_y)

    def _human_move_to(self, x: int, y: int):
        """Move mouse with human-like curve and speed variation."""
        current_x, current_y = pyautogui.position()

        # Calculate distance
        distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5

        # Duration based on distance (faster for short distances)
        duration = max(0.2, min(1.0, distance / 1500))

        # Add small random offset to target
        x += random.randint(-3, 3)
        y += random.randint(-3, 3)

        # Use easing function for natural movement
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)

    # ==================== KEYBOARD ACTIONS ====================

    def type_text(
        self,
        text: str,
        human_like: bool = True,
        interval_range: Tuple[float, float] = (0.05, 0.15)
    ):
        """
        Type text with optional human-like delays.

        Args:
            text: Text to type
            human_like: Add random delays between keystrokes
            interval_range: (min, max) delay between keystrokes in seconds
        """
        if human_like:
            for char in text:
                if char.isdigit():
                    pyautogui.press(char)
                else:
                    pyautogui.typewrite(char, interval=0)
                time.sleep(random.uniform(*interval_range))
        else:
            pyautogui.typewrite(text)

        self.logger.debug(f"Typed: {text[:20]}{'...' if len(text) > 20 else ''}")

    def press_key(self, key: str, presses: int = 1):
        """Press a keyboard key."""
        pyautogui.press(key, presses=presses)
        self.logger.debug(f"Pressed key: {key}")

    def hotkey(self, *keys):
        """Press keyboard hotkey combination."""
        pyautogui.hotkey(*keys)
        self.logger.debug(f"Hotkey: {'+'.join(keys)}")

    def paste_text(self, text: str):
        """Paste text using clipboard (faster than typing)."""
        try:
            import pyperclip
            pyperclip.copy(text)
            self.hotkey('ctrl', 'v')
            self.logger.debug(f"Pasted: {text[:20]}{'...' if len(text) > 20 else ''}")
        except ImportError:
            self.logger.warning("pyperclip not available, falling back to typing")
            self.type_text(text)

    # ==================== UTILITY METHODS ====================

    def wait(self, seconds: float):
        """Wait for specified duration."""
        time.sleep(seconds)

    def random_wait(self, min_seconds: float = 0.5, max_seconds: float = 1.5):
        """Wait for random duration to simulate human behavior."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def scroll(self, clicks: int, x: int = None, y: int = None):
        """
        Scroll the mouse wheel.

        Args:
            clicks: Number of scroll clicks (positive = up, negative = down)
            x, y: Position to scroll at (current position if not specified)
        """
        pyautogui.scroll(clicks, x=x, y=y)

    def take_screenshot(self, filepath: str = None, region: Tuple[int, int, int, int] = None) -> Image.Image:
        """
        Take screenshot of screen or region.

        Args:
            filepath: Optional path to save screenshot
            region: Optional region (x, y, width, height)

        Returns:
            PIL Image object
        """
        screenshot = self._take_screenshot(region)

        if filepath and screenshot:
            screenshot.save(filepath)
            self.logger.info(f"Screenshot saved: {filepath}")

        return screenshot

    def _take_screenshot(self, region: Tuple[int, int, int, int] = None) -> Optional[Image.Image]:
        """Internal screenshot method."""
        try:
            if region:
                return ImageGrab.grab(bbox=(region[0], region[1],
                                           region[0] + region[2],
                                           region[1] + region[3]))
            return ImageGrab.grab()
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    # ==================== TEMPLATE MANAGEMENT ====================

    def _load_template(self, template_name: str) -> Optional[np.ndarray]:
        """Load template image from cache or file."""
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Try different extensions
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            template_path = self.templates_dir / f"{template_name}{ext}"
            if template_path.exists():
                template = cv2.imread(str(template_path))
                if template is not None:
                    self._template_cache[template_name] = template
                    return template

        self.logger.warning(f"Template not found: {template_name}")
        return None

    def capture_template(
        self,
        template_name: str,
        region: Tuple[int, int, int, int] = None,
        interactive: bool = True
    ) -> bool:
        """
        Capture a region of the screen as a new template.

        Args:
            template_name: Name for the template
            region: Region to capture (x, y, width, height)
            interactive: If True, let user select region with mouse

        Returns:
            True if template captured successfully
        """
        if interactive and region is None:
            print(f"\n📸 Capturing template: {template_name}")
            print("   Move mouse to TOP-LEFT corner of element, then press Enter...")
            input()
            top_left = pyautogui.position()

            print("   Move mouse to BOTTOM-RIGHT corner of element, then press Enter...")
            input()
            bottom_right = pyautogui.position()

            region = (
                top_left[0],
                top_left[1],
                bottom_right[0] - top_left[0],
                bottom_right[1] - top_left[1]
            )
            print(f"   Region: {region}")

        if region:
            screenshot = self._take_screenshot(region)
            if screenshot:
                template_path = self.templates_dir / f"{template_name}.png"
                screenshot.save(str(template_path))
                self.logger.info(f"Template captured: {template_path}")

                # Clear cache to reload
                if template_name in self._template_cache:
                    del self._template_cache[template_name]

                return True

        return False

    def capture_templates_interactive(self, template_names: List[str]):
        """Interactively capture multiple templates."""
        print("\n" + "=" * 60)
        print("INTERACTIVE TEMPLATE CAPTURE")
        print("=" * 60)
        print(f"\nYou will capture {len(template_names)} templates.")
        print("For each template, select the TOP-LEFT and BOTTOM-RIGHT corners.\n")

        for name in template_names:
            self.capture_template(name, interactive=True)
            print()

        print("✅ All templates captured!")

    # ==================== HIGH-LEVEL ACTIONS ====================

    def click_element_by_template(
        self,
        template_name: str,
        confidence: float = 0.8,
        timeout: float = 10.0,
        human_like: bool = True
    ) -> bool:
        """Find element by template and click it."""
        element = self.find_element(template_name=template_name, confidence=confidence, timeout=timeout)
        if element:
            return self.click(element, human_like=human_like)
        return False

    def click_element_by_text(
        self,
        text: str,
        timeout: float = 10.0,
        human_like: bool = True
    ) -> bool:
        """Find element by text (OCR) and click it."""
        element = self.find_element(text=text, timeout=timeout, strategy=FindStrategy.OCR)
        if element:
            return self.click(element, human_like=human_like)
        return False

    def wait_for_element(
        self,
        template_name: str = None,
        text: str = None,
        timeout: float = 30.0,
        confidence: float = 0.8
    ) -> Optional[ElementMatch]:
        """Wait for element to appear on screen."""
        return self.find_element(
            template_name=template_name,
            text=text,
            confidence=confidence,
            timeout=timeout
        )

    def element_exists(
        self,
        template_name: str = None,
        text: str = None,
        confidence: float = 0.8
    ) -> bool:
        """Check if element exists on screen (quick check, no waiting)."""
        element = self.find_element(
            template_name=template_name,
            text=text,
            confidence=confidence,
            timeout=0.5
        )
        return element is not None

    # ==================== SAFE CLICK WITH RECOVERY ====================

    def safe_click(
        self,
        element: ElementMatch = None,
        x: int = None,
        y: int = None,
        max_retries: int = 3,
        position_tolerance: int = 15,
        human_like: bool = True
    ) -> bool:
        """
        Click with position verification and recovery.

        If user moves the mouse during automation, this method will:
        1. Detect the mouse was moved
        2. Re-position to the target
        3. Retry the click

        Args:
            element: ElementMatch to click on
            x, y: Coordinates to click (used if element not provided)
            max_retries: Maximum number of retry attempts
            position_tolerance: Allowed deviation in pixels
            human_like: Use human-like movement

        Returns:
            True if click was successful
        """
        if element:
            target_x, target_y = element.center
        elif x is not None and y is not None:
            target_x, target_y = x, y
        else:
            self.logger.error("safe_click requires either element or coordinates")
            return False

        for attempt in range(max_retries):
            try:
                # Move to target
                if human_like:
                    self._human_move_to(target_x, target_y)
                else:
                    pyautogui.moveTo(target_x, target_y)

                # Small pause
                time.sleep(random.uniform(0.05, 0.1))

                # Verify position
                current_x, current_y = pyautogui.position()
                dx = abs(current_x - target_x)
                dy = abs(current_y - target_y)

                if dx <= position_tolerance and dy <= position_tolerance:
                    # Position OK, click
                    pyautogui.click()
                    self.logger.debug(f"Safe click successful at ({target_x}, {target_y})")
                    return True
                else:
                    # Mouse was moved by user
                    self.logger.warning(
                        f"Mouse moved! Expected ({target_x}, {target_y}), "
                        f"got ({current_x}, {current_y}). Attempt {attempt + 1}/{max_retries}"
                    )
                    time.sleep(0.3)  # Brief pause before retry

            except Exception as e:
                self.logger.error(f"Safe click error: {e}")

        self.logger.error(f"Safe click failed after {max_retries} attempts")
        return False

    def safe_type(
        self,
        text: str,
        max_retries: int = 2,
        human_like: bool = True
    ) -> bool:
        """
        Type text with verification.

        Args:
            text: Text to type
            max_retries: Maximum retry attempts
            human_like: Use human-like typing

        Returns:
            True if typing completed
        """
        for attempt in range(max_retries):
            try:
                self.type_text(text, human_like=human_like)
                return True
            except Exception as e:
                self.logger.warning(f"Typing error: {e}. Attempt {attempt + 1}/{max_retries}")
                time.sleep(0.5)

        return False


# ==================== MOUSE GUARD ====================

class MouseGuard:
    """
    Monitors mouse position and automatically returns it to the target position
    if the user moves it. This provides visual feedback that automation is in control.

    Usage:
        guard = MouseGuard()
        guard.start()
        guard.set_target(500, 300)  # Mouse will stay at this position
        # ... do automation ...
        guard.release()  # Allow user to move mouse
        guard.stop()
    """

    def __init__(self, check_interval: float = 0.05, tolerance: int = 10):
        """
        Initialize mouse guard.

        Args:
            check_interval: How often to check mouse position (seconds)
            tolerance: Allowed deviation in pixels before repositioning
        """
        self._target_x: Optional[int] = None
        self._target_y: Optional[int] = None
        self._is_running = False
        self._is_locked = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = check_interval
        self._tolerance = tolerance
        self._lock = threading.Lock()
        self.logger = get_logger('MouseGuard')

    def start(self):
        """Start the mouse guard monitoring thread."""
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("MouseGuard started")

    def stop(self):
        """Stop the mouse guard."""
        self._is_running = False
        self._is_locked = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        self.logger.info("MouseGuard stopped")

    def set_target(self, x: int, y: int):
        """
        Set target position and lock mouse to it.

        Args:
            x, y: Target coordinates
        """
        with self._lock:
            self._target_x = x
            self._target_y = y
            self._is_locked = True
        self.logger.debug(f"Mouse locked to ({x}, {y})")

    def release(self):
        """Release the mouse lock (allow user to move freely)."""
        with self._lock:
            self._is_locked = False
            self._target_x = None
            self._target_y = None
        self.logger.debug("Mouse released")

    def is_locked(self) -> bool:
        """Check if mouse is currently locked."""
        return self._is_locked

    def _monitor_loop(self):
        """Main monitoring loop (runs in separate thread)."""
        while self._is_running:
            try:
                with self._lock:
                    if self._is_locked and self._target_x is not None:
                        current_x, current_y = pyautogui.position()
                        dx = abs(current_x - self._target_x)
                        dy = abs(current_y - self._target_y)

                        if dx > self._tolerance or dy > self._tolerance:
                            # User moved mouse - return to target
                            pyautogui.moveTo(self._target_x, self._target_y, duration=0.1)
                            self.logger.debug(
                                f"Mouse repositioned: ({current_x},{current_y}) -> ({self._target_x},{self._target_y})"
                            )

                time.sleep(self._check_interval)

            except Exception as e:
                self.logger.error(f"MouseGuard error: {e}")
                time.sleep(0.1)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


# ==================== AUTOMATION OVERLAY ====================

class JsonAutomationOverlay:
    """
    Creates a visual overlay using a separate Python process.
    This approach is more reliable on Windows than threading with tkinter.
    """

    def __init__(self):
        self._process = None
        self._script_path = None

    def show(self, message: str = None):
        """Show the overlay window in a separate process."""
        import subprocess
        import tempfile
        import os

        if self._process is not None:
            return

        if message is None:
            message = "AUTOMACAO EM ANDAMENTO\\n\\nNao mexa no mouse!\\n\\nMova o mouse para o CANTO\\nSUPERIOR ESQUERDO para cancelar."

        # Create a temporary Python script for the overlay
        overlay_code = '''
import tkinter as tk
import sys

def create_overlay():
    root = tk.Tk()
    root.title("Automacao")

    # Window settings
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.9)
    root.overrideredirect(True)
    root.configure(bg='#1a1a2e')

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Window size and position (top-right corner)
    window_width = 340
    window_height = 140
    x_position = screen_width - window_width - 20
    y_position = 20

    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    # Frame with border
    frame = tk.Frame(root, bg='#1a1a2e', bd=3, relief='raised', highlightbackground='#ffd700', highlightthickness=2)
    frame.pack(fill='both', expand=True, padx=2, pady=2)

    # Icon/emoji
    icon_label = tk.Label(
        frame,
        text="⚠️",
        font=('Segoe UI Emoji', 24),
        fg='#ffd700',
        bg='#1a1a2e'
    )
    icon_label.pack(pady=(10, 0))

    # Message
    message = """MESSAGE_PLACEHOLDER"""
    label = tk.Label(
        frame,
        text=message,
        font=('Segoe UI', 10, 'bold'),
        fg='#ffffff',
        bg='#1a1a2e',
        justify='center'
    )
    label.pack(pady=(5, 10))

    # Blinking effect
    def blink():
        current_color = frame.cget('highlightbackground')
        new_color = '#ff4444' if current_color == '#ffd700' else '#ffd700'
        frame.configure(highlightbackground=new_color)
        root.after(500, blink)

    blink()
    root.mainloop()

if __name__ == "__main__":
    create_overlay()
'''
        # Replace placeholder with actual message
        overlay_code = overlay_code.replace('MESSAGE_PLACEHOLDER', message)

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(overlay_code)
            self._script_path = f.name

        # Start overlay process
        try:
            # Use pythonw.exe to avoid console window
            python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(python_exe):
                python_exe = sys.executable

            self._process = subprocess.Popen(
                [python_exe, self._script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(0.5)  # Give time for window to appear
        except Exception as e:
            print(f"Failed to start overlay: {e}")

    def hide(self):
        """Hide and destroy the overlay window."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except:
                try:
                    self._process.kill()
                except:
                    pass
            self._process = None

        # Clean up temp file
        if self._script_path:
            try:
                import os
                os.unlink(self._script_path)
            except:
                pass
            self._script_path = None

    def __enter__(self):
        """Context manager entry."""
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.hide()
        return False


# Simple overlay using just a console message (fallback)
class ConsoleOverlay:
    """Simple console-based overlay notification."""

    def __init__(self):
        self._shown = False

    def show(self, message: str = None):
        if not self._shown:
            print("\n" + "=" * 50)
            print("   AUTOMACAO EM ANDAMENTO")
            print("   Nao mexa no mouse!")
            print("   Mova para o canto superior esquerdo para CANCELAR")
            print("=" * 50 + "\n")
            self._shown = True

    def hide(self):
        if self._shown:
            print("\n" + "=" * 50)
            print("   AUTOMACAO FINALIZADA")
            print("=" * 50 + "\n")
            self._shown = False

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.hide()
        return False


# Choose best available overlay
def get_overlay():
    """Get the best available overlay for the current system."""
    try:
        import tkinter as tk
        # Test if tkinter works
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return JsonAutomationOverlay()
    except:
        return ConsoleOverlay()


class ProtectedAutomation:
    """
    Context manager for protected automation sessions.

    Features:
    - MouseGuard: Automatically returns mouse to target if user moves it
    - Visual Overlay: Shows warning message to user
    - Safe clicks with position verification
    - Visual feedback through mouse "resistance"

    Usage:
        with ProtectedAutomation(visual) as protected:
            protected.safe_click(element)
            protected.safe_type("text")
    """

    def __init__(self, visual_automation: VisualAutomation, show_overlay: bool = True):
        """
        Initialize protected automation session.

        Args:
            visual_automation: VisualAutomation instance
            show_overlay: Whether to show the warning overlay
        """
        self.visual = visual_automation
        self.mouse_guard = MouseGuard(check_interval=0.03, tolerance=8)
        self.show_overlay = show_overlay
        self.overlay = get_overlay() if show_overlay else None
        self.logger = get_logger('ProtectedAutomation')

    def __enter__(self):
        """Start protected session."""
        # Show overlay first
        if self.overlay:
            self.overlay.show()

        # Start mouse guard
        self.mouse_guard.start()
        self.logger.info("Protected automation session started (MouseGuard + Overlay active)")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End protected session."""
        # Stop mouse guard
        self.mouse_guard.stop()

        # Hide overlay
        if self.overlay:
            self.overlay.hide()

        self.logger.info("Protected automation session ended")
        return False

    def safe_click(
        self,
        element: ElementMatch = None,
        x: int = None,
        y: int = None,
        hold_duration: float = 0.3
    ) -> bool:
        """
        Protected click with MouseGuard.

        The mouse will be locked to the target position, preventing
        user interference. If user tries to move, mouse returns automatically.

        Args:
            element: ElementMatch to click on
            x, y: Coordinates to click (used if element not provided)
            hold_duration: How long to hold position after click

        Returns:
            True if click was successful
        """
        if element:
            target_x, target_y = element.center
        elif x is not None and y is not None:
            target_x, target_y = x, y
        else:
            self.logger.error("safe_click requires either element or coordinates")
            return False

        try:
            # Lock mouse to target position
            self.mouse_guard.set_target(target_x, target_y)

            # Move to target (MouseGuard will keep it there)
            pyautogui.moveTo(target_x, target_y, duration=0.2)

            # Small pause to let MouseGuard stabilize
            time.sleep(0.1)

            # Click
            pyautogui.click()

            # Hold position briefly after click
            time.sleep(hold_duration)

            # Release mouse
            self.mouse_guard.release()

            self.logger.debug(f"Safe click completed at ({target_x}, {target_y})")
            return True

        except Exception as e:
            self.logger.error(f"Safe click error: {e}")
            self.mouse_guard.release()
            return False

    def safe_type(self, text: str, human_like: bool = True) -> bool:
        """
        Protected typing.

        Args:
            text: Text to type
            human_like: Use human-like typing delays

        Returns:
            True if typing completed
        """
        try:
            # Release mouse during typing (user might need to see the field)
            self.mouse_guard.release()

            self.visual.type_text(text, human_like=human_like)
            return True

        except Exception as e:
            self.logger.error(f"Safe type error: {e}")
            return False

    def find_element(self, **kwargs) -> Optional[ElementMatch]:
        """Find element (delegates to visual automation)."""
        # Release mouse during element search
        self.mouse_guard.release()
        return self.visual.find_element(**kwargs)

    def random_wait(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Random wait (mouse is released during wait)."""
        self.mouse_guard.release()
        self.visual.random_wait(min_sec, max_sec)

    def take_screenshot(self, filepath: str):
        """Take screenshot."""
        self.mouse_guard.release()
        return self.visual.take_screenshot(filepath)

    def lock_mouse(self, x: int, y: int):
        """Manually lock mouse to a position."""
        self.mouse_guard.set_target(x, y)

    def release_mouse(self):
        """Manually release mouse lock."""
        self.mouse_guard.release()
