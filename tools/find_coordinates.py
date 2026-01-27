"""
Find Coordinates Tool

This script helps identify the correct coordinates of elements in screenshots.
Run this and click on the image to get coordinates.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image
    import cv2
    import numpy as np
except ImportError:
    print("Install packages: pip install pillow opencv-python numpy")
    sys.exit(1)


def show_image_with_grid(image_path):
    """Display image with coordinate grid overlay."""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Could not load: {image_path}")
        return

    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")

    # Add grid lines every 100 pixels
    for x in range(0, w, 100):
        cv2.line(img, (x, 0), (x, h), (200, 200, 200), 1)
        cv2.putText(img, str(x), (x + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    for y in range(0, h, 100):
        cv2.line(img, (0, y), (w, y), (200, 200, 200), 1)
        cv2.putText(img, str(y), (2, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    # Resize for display if too large
    scale = 1.0
    if w > 1600 or h > 900:
        scale = min(1600 / w, 900 / h)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    clicks = []

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Convert back to original coordinates
            orig_x = int(x / scale)
            orig_y = int(y / scale)
            clicks.append((orig_x, orig_y))
            print(f"Click {len(clicks)}: ({orig_x}, {orig_y})")

            if len(clicks) == 2:
                x1, y1 = clicks[0]
                x2, y2 = clicks[1]
                w = x2 - x1
                h = y2 - y1
                print(f"\nRegion: ({x1}, {y1}, {w}, {h})")
                print(f"Copy: '{x1}, {y1}, {w}, {h}'")
                clicks.clear()

    cv2.namedWindow('Image - Click to get coordinates')
    cv2.setMouseCallback('Image - Click to get coordinates', mouse_callback)

    print("\nInstructions:")
    print("- Click on TOP-LEFT corner of element")
    print("- Click on BOTTOM-RIGHT corner of element")
    print("- Region coordinates will be printed")
    print("- Press 'q' to quit\n")

    while True:
        cv2.imshow('Image - Click to get coordinates', img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()


def analyze_screenshot(image_path):
    """Analyze screenshot and suggest element locations."""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Could not load: {image_path}")
        return

    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")
    print("\nAnalyzing elements...\n")

    # Convert to HSV for color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Find blue buttons (Emitir, Aceitar)
    # Blue in HSV: H=100-130, S=100-255, V=100-255
    lower_blue = np.array([100, 100, 100])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Find contours of blue regions
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    print("Blue elements found (buttons):")
    for i, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area > 1000:  # Filter small noise
            print(f"  [{i}] Position: ({x}, {y}, {w}, {h}), Area: {area}")

    # Find white buttons with borders
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    print("\nEdge analysis complete.")
    print("\nTo get precise coordinates, use the interactive mode:")
    print("  python tools/find_coordinates.py --interactive")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Find element coordinates in screenshots")
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode with GUI')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analyze screenshot automatically')
    parser.add_argument('--file', '-f', type=str, help='Screenshot file to analyze')

    args = parser.parse_args()

    screenshots_dir = project_root / 'screenshots'
    default_file = screenshots_dir / 'federal_pyautogui_result.png'

    if args.file:
        image_path = Path(args.file)
    else:
        image_path = default_file

    if not image_path.exists():
        print(f"File not found: {image_path}")
        return

    if args.interactive:
        show_image_with_grid(image_path)
    elif args.analyze:
        analyze_screenshot(image_path)
    else:
        print("Federal Screenshot Analysis")
        print("=" * 50)
        analyze_screenshot(image_path)
        print("\nFor interactive coordinate selection, run:")
        print("  python tools/find_coordinates.py --interactive")


if __name__ == "__main__":
    main()
