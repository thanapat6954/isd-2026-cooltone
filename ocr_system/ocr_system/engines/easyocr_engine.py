import easyocr
import numpy as np
from ocr_system.engines.base import BaseOCREngine
from ocr_system.schemas import OCRLine

class EasyOCREngine(BaseOCREngine):
    def __init__(self, languages=['th', 'en']):
        # Set gpu=True if you have an NVIDIA graphics card configured
        self.name = "easyocr"
        self.reader = easyocr.Reader(languages, gpu=False)

    def recognize(self, image, page=1):
        if not isinstance(image, np.ndarray):
            image = np.array(image)
        
        results = self.reader.readtext(image)
        ocr_lines = []
        for bbox, text, confidence in results:
            # Cleaned up the citation tag here
            cleaned_box = np.array(bbox).astype(int).tolist()
            
            ocr_lines.append(OCRLine(
                text=text,
                confidence=float(confidence),
                box=cleaned_box,
                engine=self.name,
                page=page
            ))
        return ocr_lines