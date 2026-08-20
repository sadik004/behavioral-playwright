import asyncio
import io
import logging
from typing import Any, Dict, List

logger = logging.getLogger("BehavioralAutomation.AI.OCR")


class OCREngine:
    """Wrapper for pytesseract OCR coordinates extraction."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logger

    def extract_text_with_coordinates(self, screenshot_bytes: bytes) -> List[Dict[str, Any]]:
        self.logger.info("[OCR] Processing screen buffer using OCR engine...")
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(screenshot_bytes))
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            results = []
            for i in range(len(data["level"])):
                text = data["text"][i].strip()
                if text:
                    results.append(
                        {
                            "text": text,
                            "bounding_box": {
                                "x": float(data["left"][i]),
                                "y": float(data["top"][i]),
                                "width": float(data["width"][i]),
                                "height": float(data["height"][i]),
                            },
                            "confidence": float(data["conf"][i]) / 100.0,
                        }
                    )
            return results
        except ImportError:
            self.logger.debug("[OCR] Pytesseract/PIL not available. Returning empty.")
            return []

    async def extract_text_with_coordinates_async(self, screenshot_bytes: bytes) -> List[Dict[str, Any]]:
        """Asynchronously processes screen buffer using OCR engine via worker thread."""
        return await asyncio.to_thread(self.extract_text_with_coordinates, screenshot_bytes)
