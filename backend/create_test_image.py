"""Create a test image for OCR verification."""
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_test_image():
    """Create a simple test image with text."""
    # Create test_data directory if it doesn't exist
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    
    # Create a blank white image
    img = Image.new('RGB', (600, 200), color='white')
    d = ImageDraw.Draw(img)
    
    # Use default font (may vary by system)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # Draw text
    d.text((50, 80), "Test OCR Text", fill="black", font=font)
    
    # Save image
    img_path = test_dir / "sample.png"
    img.save(img_path)
    print(f"Test image created at: {img_path}")

if __name__ == "__main__":
    create_test_image()