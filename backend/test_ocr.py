"""Test script for verifying WSL Tesseract OCR functionality."""
import os
from pathlib import Path
from PIL import Image
import pytesseract

# Configure pytesseract to use WSL Tesseract with full path
pytesseract.tesseract_cmd = 'wsl /usr/bin/tesseract'
print(f"Tesseract configured at: {pytesseract.tesseract_cmd}")
def test_ocr(image_path: str):
    """Test OCR extraction from an image."""
    try:
        print(f"Testing OCR on: {image_path}")
        
        # Verify file exists and is accessible
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        print(f"Opening image file: {image_path}")
        img = Image.open(image_path)
        print("Image opened successfully, performing OCR...")
        text = pytesseract.image_to_string(img)
        print("OCR Result:")
        print(text.strip())
        
        return True
    except Exception as e:
        print(f"OCR test failed: {e}")
        return False

if __name__ == "__main__":
    # Test with a sample image (update path as needed)
    test_image = os.path.join(Path(__file__).parent, "test_data", "sample.png")
    if not os.path.exists(test_image):
        print(f"Test image not found at: {test_image}")
        print("Please create a test image at that location")
    else:
        test_ocr(test_image)