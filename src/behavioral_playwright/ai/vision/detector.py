import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger("BehavioralAutomation.AI.VisualDetector")


class VisualDetector:
    """Wrapper for OpenCV rectangular contour box detections."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logger

    def detect_visual_elements(self, screenshot_bytes: bytes) -> List[Dict[str, Any]]:
        self.logger.info("[DETECTOR] Running OpenCV visual contour analysis...")
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)[1]
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detected = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > 20 and h > 10:
                    detected.append(
                        {
                            "type": "contour_box",
                            "bounding_box": {"x": float(x), "y": float(y), "width": float(w), "height": float(h)},
                            "confidence": 0.80,
                        }
                    )
            return detected
        except ImportError:
            self.logger.debug("[DETECTOR] OpenCV/Numpy are not loaded.")
            return []

    async def detect_visual_elements_async(self, screenshot_bytes: bytes) -> List[Dict[str, Any]]:
        """Asynchronously runs OpenCV visual contour analysis via worker thread."""
        return await asyncio.to_thread(self.detect_visual_elements, screenshot_bytes)
