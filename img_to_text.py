from PIL import Image
import pytesseract
import os
import platform

# Dynamically set the path to the Tesseract executable
if platform.system() == "Windows":
    # Check common installation paths for Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Tesseract-OCR', 'tesseract.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Tesseract-OCR', 'tesseract.exe')
    ]
    
    # Use environment variable if set
    tesseract_env = os.getenv("TESSERACT_CMD")
    if tesseract_env and os.path.exists(tesseract_env):
        pytesseract.pytesseract.tesseract_cmd = tesseract_env
    else:
        # Try to find tesseract in common locations
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        else:
            # If not found in common locations, use default and hope it's in PATH
            pytesseract.pytesseract.tesseract_cmd = "tesseract"
else:
    # For Linux and macOS, assume tesseract is in the PATH
    pytesseract.pytesseract.tesseract_cmd = "tesseract"

def extract_text_from_image(image_path):
    try:
        # Open the image file
        img = Image.open(image_path)
        
        # Extract text from image
        extracted_text = pytesseract.image_to_string(img)
        
        return extracted_text.strip()
    except Exception as e:
        return f"Error: {e}" 