def __init__(self, languages: str = "tha+eng", psm: int = 6):
    import pytesseract

    self.pytesseract = pytesseract
    self.pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    self.languages = languages
    self.config = f"--oem 3 --psm {psm}"