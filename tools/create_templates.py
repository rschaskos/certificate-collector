"""
Create Templates from Screenshots

Extracts element templates from the existing screenshots for visual automation.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image
except ImportError:
    print("Install pillow: pip install pillow")
    sys.exit(1)


def extract_and_save(image_path: Path, region: tuple, output_path: Path):
    """Extract region from image and save."""
    img = Image.open(image_path)
    x, y, w, h = region
    cropped = img.crop((x, y, x + w, y + h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output_path)
    print(f"  [OK] {output_path.name} ({w}x{h})")


def main():
    screenshots_dir = project_root / 'screenshots'
    templates_dir = project_root / 'core' / 'templates' / 'federal'

    print("=" * 60)
    print("CREATING TEMPLATES FROM SCREENSHOTS")
    print("=" * 60)

    # Source screenshot (use the one with all elements visible)
    source = screenshots_dir / 'federal_pyautogui_result.png'

    if not source.exists():
        print(f"[ERROR] Source screenshot not found: {source}")
        return False

    print(f"\nSource: {source.name}")
    print(f"Output: {templates_dir}\n")

    # Element coordinates (x, y, width, height)
    # Analyzed from the screenshot federal_pyautogui_result.png (1904x985)
    # Coordinates obtained via automatic color detection
    templates = {
        'campo_cnpj.png': (295, 520, 250, 50),                # CNPJ input field with value
        'btn_consultar_certidao.png': (1097, 705, 227, 40),   # Consultar button
        'btn_emitir_certidao.png': (1343, 705, 194, 40),      # Emitir button (blue)
        'btn_aceitar_cookies.png': (1745, 913, 104, 32),      # Aceitar button (blue in footer)
        'label_cnpj.png': (290, 490, 55, 25),                 # CNPJ label
    }

    print("Extracting templates:")
    for template_name, region in templates.items():
        output_path = templates_dir / template_name
        try:
            extract_and_save(source, region, output_path)
        except Exception as e:
            print(f"  [ERROR] {template_name}: {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Templates created successfully!")
    print("=" * 60)

    # List created files
    print("\nCreated templates:")
    for f in templates_dir.glob('*.png'):
        img = Image.open(f)
        print(f"  - {f.name} ({img.width}x{img.height})")

    return True


if __name__ == "__main__":
    main()
