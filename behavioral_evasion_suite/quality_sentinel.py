"""
Patch 10: Pydantic Data Integrity & Honeypot Sentinel
Monitors schema drift, detects empty pages, and screens element bounding boxes
to discard layout-hidden Honeypot traps.
"""
import logging
from typing import Dict, Any, List, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("BehavioralEvasion.QualitySentinel")


class QualitySentinel:
    """
    Monitors schema drift, detects empty pages, and screens element bounding boxes
    to discard layout-hidden Honeypot traps.
    """
    def __init__(self, max_allowed_failure_ratio: float = 0.5, window_size: int = 5) -> None:
        self.max_allowed_failure_ratio = max_allowed_failure_ratio
        self.window_size = window_size
        self.extraction_history: List[bool] = []

    def check_honeypots(self, element_metadata: Dict[str, Any]) -> bool:
        """Screens elements to identify display:none or zero-height honeypots."""
        style = element_metadata.get("style", {}).get("display", "").lower()
        opacity = float(element_metadata.get("style", {}).get("opacity", "1.0"))
        height = float(element_metadata.get("boundingBox", {}).get("height", "10"))
        width = float(element_metadata.get("boundingBox", {}).get("width", "10"))

        if "none" in style or opacity == 0.0 or height <= 0 or width <= 0:
            logger.warning("QualitySentinel: Detected visually hidden Honeypot element!")
            return True
        return False

    def monitor_data_quality(self, url: str, raw_payload: Dict[str, Any], schema_class: Type[BaseModel]) -> bool:
        is_blank = not raw_payload or all(val is None or val == "" for val in raw_payload.values())

        try:
            if is_blank:
                raise ValueError("Blank payload detected (100% data loss)")

            schema_class(**raw_payload)
            self.extraction_history.append(True)
            logger.info(f"QualitySentinel: Validation succeeded for {url}")
            return True

        except (ValidationError, ValueError) as e:
            self.extraction_history.append(False)
            logger.error(f"QualitySentinel: Schema drift validation error for {url}: {e}")

            recent_fails = self.extraction_history[-self.window_size:]
            fail_ratio = recent_fails.count(False) / len(recent_fails)

            if len(self.extraction_history) >= self.window_size and fail_ratio >= self.max_allowed_failure_ratio:
                logger.critical("QualitySentinel: CRITICAL SCHEMA DRIFT THRESHOLD EXCEEDED! Halting pipeline.")
                raise RuntimeError("Pipeline halted by QualitySentinel due to excessive validation errors.")
            return False
