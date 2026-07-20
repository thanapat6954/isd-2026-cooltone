import easyocr
import os

# 1. Initialize the reader with Thai ('th') and English ('en')
print("Loading EasyOCR models (this may take a moment on the first run)...")
reader = easyocr.Reader(['th', 'en'], gpu=False)  # Set gpu=True if you have an Nvidia GPU setup

# 2. Path to your test image
image_path = "data/input/sample.jpg"  # Change this to your actual image file name

if not os.path.exists(image_path):
    print(f"Error: Could not find the image at {image_path}. Please check the file name.")
else:
    print(f"Processing OCR on {image_path}...")
    
    # 3. Perform OCR
    # detail=0 returns just a list of extracted text strings
    results = reader.readtext(image_path, detail=0)
    
    print("\n--- OCR Results ---")
    for line in results:
        print(line)