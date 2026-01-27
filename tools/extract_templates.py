"""
Template Extraction Tool

This script extracts element templates from existing screenshots.
Templates are used by the visual automation engine for element recognition.

Usage:
    python tools/extract_templates.py

Author: Certificate Collector Team
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image
    import cv2
    import numpy as np
except ImportError:
    print("Required packages not installed. Run:")
    print("pip install pillow opencv-python numpy")
    sys.exit(1)


def extract_region(image_path: str, region: tuple, output_path: str):
    """
    Extract a region from an image and save it.

    Args:
        image_path: Path to source image
        region: (x, y, width, height) region to extract
        output_path: Path to save extracted region
    """
    img = Image.open(image_path)
    x, y, w, h = region

    # Crop the region
    cropped = img.crop((x, y, x + w, y + h))

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save
    cropped.save(output_path)
    print(f"✓ Saved: {output_path}")


def main():
    """Extract templates from existing screenshots."""

    screenshots_dir = project_root / 'screenshots'
    templates_dir = project_root / 'core' / 'templates' / 'federal'
    templates_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("TEMPLATE EXTRACTION TOOL")
    print("=" * 60)
    print(f"\nSource: {screenshots_dir}")
    print(f"Output: {templates_dir}")
    print()

    # Check for source screenshots
    screenshot_files = list(screenshots_dir.glob('federal*.png'))
    if not screenshot_files:
        print("No federal screenshots found!")
        print("Run the certificate generator first to capture screenshots.")
        return

    print(f"Found {len(screenshot_files)} federal screenshots:")
    for i, f in enumerate(screenshot_files):
        print(f"  {i + 1}. {f.name}")

    print("\n" + "-" * 60)
    print("MANUAL EXTRACTION MODE")
    print("-" * 60)
    print("""
I'll guide you through extracting templates from the screenshots.
You'll need to look at the screenshots and provide coordinates.

Coordinates format: x,y,width,height
Example: 57,360,314,50

You can open the screenshots in an image viewer to find coordinates.
Most image viewers show pixel coordinates when you hover.
    """)

    # Define templates to extract
    templates = [
        ('campo_cnpj.png', 'CNPJ input field (the text box where you type CNPJ)'),
        ('btn_consultar_certidao.png', 'Consultar Certidão button (white button with search icon)'),
        ('btn_emitir_certidao.png', 'Emitir Certidão button (blue button)'),
        ('btn_aceitar_cookies.png', 'Aceitar button (blue button in cookies dialog)'),
    ]

    # Try to open the most recent screenshot
    screenshot_file = max(screenshot_files, key=lambda f: f.stat().st_mtime)
    print(f"\nUsing screenshot: {screenshot_file.name}")

    # Show the screenshot
    try:
        img = Image.open(screenshot_file)
        print(f"Image size: {img.width}x{img.height}")
    except Exception as e:
        print(f"Could not open screenshot: {e}")
        return

    for template_name, description in templates:
        print(f"\n📸 Template: {template_name}")
        print(f"   Description: {description}")

        coords = input("   Enter coordinates (x,y,w,h) or 'skip': ").strip()

        if coords.lower() == 'skip':
            continue

        try:
            x, y, w, h = map(int, coords.split(','))
            output_path = templates_dir / template_name

            extract_region(str(screenshot_file), (x, y, w, h), str(output_path))

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Template extraction completed!")
    print(f"   Templates saved in: {templates_dir}")
    print("=" * 60)


def auto_extract_from_known_coordinates():
    """
    Auto-extract templates using pre-defined coordinates.
    Based on analysis of the existing screenshots.
    """

    screenshots_dir = project_root / 'screenshots'
    templates_dir = project_root / 'core' / 'templates' / 'federal'
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Coordinates extracted from analyzing the screenshots
    # Format: (screenshot_name, template_name, (x, y, w, h))
    extractions = [
        # From federal_error.png (shows the full page with buttons visible)
        ('federal_error.png', 'btn_consultar_certidao.png', (790, 342, 190, 45)),
        ('federal_error.png', 'btn_emitir_certidao.png', (1042, 342, 170, 45)),
        ('federal_error.png', 'campo_cnpj.png', (56, 147, 320, 50)),

        # From federal_pyautogui_result.png (shows cookies banner)
        ('federal_pyautogui_result.png', 'btn_aceitar_cookies.png', (1389, 730, 85, 35)),
    ]

    print("=" * 60)
    print("AUTO-EXTRACTING TEMPLATES")
    print("=" * 60)

    for screenshot_name, template_name, region in extractions:
        screenshot_path = screenshots_dir / screenshot_name
        template_path = templates_dir / template_name

        if not screenshot_path.exists():
            print(f"⚠️  Screenshot not found: {screenshot_name}")
            continue

        try:
            extract_region(str(screenshot_path), region, str(template_path))
        except Exception as e:
            print(f"❌ Failed to extract {template_name}: {e}")

    print("\nDone!")


def interactive_extraction():
    """Interactive mode to select regions from screenshots."""

    try:
        import tkinter as tk
        from tkinter import filedialog
        from PIL import ImageTk
    except ImportError:
        print("Tkinter not available for interactive mode")
        return

    print("Starting interactive extraction...")
    print("(This requires a display)")

    # Simple tkinter window for region selection
    root = tk.Tk()
    root.title("Template Extraction")

    screenshots_dir = project_root / 'screenshots'
    screenshot_files = list(screenshots_dir.glob('federal*.png'))

    if not screenshot_files:
        print("No screenshots found!")
        return

    # Use most recent
    screenshot_file = max(screenshot_files, key=lambda f: f.stat().st_mtime)

    img = Image.open(screenshot_file)
    # Resize if too large
    max_size = (1200, 800)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    photo = ImageTk.PhotoImage(img)

    canvas = tk.Canvas(root, width=img.width, height=img.height)
    canvas.pack()
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)

    # Selection rectangle
    rect = None
    start_x = start_y = 0

    def on_press(event):
        nonlocal start_x, start_y, rect
        start_x, start_y = event.x, event.y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_drag(event):
        canvas.coords(rect, start_x, start_y, event.x, event.y)

    def on_release(event):
        end_x, end_y = event.x, event.y
        print(f"Selected region: {start_x},{start_y},{end_x - start_x},{end_y - start_y}")

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    root.mainloop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract templates from screenshots")
    parser.add_argument('--auto', action='store_true', help='Use auto-extraction with predefined coordinates')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode with GUI')

    args = parser.parse_args()

    if args.auto:
        auto_extract_from_known_coordinates()
    elif args.interactive:
        interactive_extraction()
    else:
        main()
