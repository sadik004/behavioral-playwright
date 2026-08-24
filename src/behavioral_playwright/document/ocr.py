"""Document processing namespace: OCR with contrast-boost preprocessing.

Real implementation using optional dependencies:
  - Pillow (PIL) for grayscale + contrast enhancement
  - pytesseract for the OCR engine (lazy-imported so the package remains
    usable without it; a clear ProviderUnavailableError is raised instead)
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from typing import Any, Dict

from behavioral_playwright.exceptions import ProviderError, ProviderUnavailableError

_CONTRAST_SCALE = 1.5


class DocumentNamespace:
    """Offline document/OCR utilities exposed as ``bp.document``."""

    @staticmethod
    def _get_sha256(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def clean_parsed_text(text: str) -> str:
        """Removes watermark markers and normalizes whitespace."""
        cleaned = text.replace("CONFIDENTIAL", "").replace("DRAFT", "")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r" *\n *", "\n", cleaned)
        cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)
        return cleaned.strip()

    async def ocr_image_with_autocorrect(self, file_path: str) -> Dict[str, Any]:
        """Runs contrast-boosted OCR on an image file.

        Raises:
            FileNotFoundError: if the image does not exist.
            ProviderUnavailableError: if pytesseract is not installed.
            ProviderError: if the OCR engine fails at runtime.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found: {file_path}")

        def _run_ocr_pipeline() -> str:
            try:
                from PIL import Image, ImageEnhance, ImageOps
                with Image.open(file_path) as img:
                    gray_img = ImageOps.grayscale(img)
                    preprocessed = ImageEnhance.Contrast(gray_img).enhance(
                        _CONTRAST_SCALE)
                import pytesseract  # lazy: tests patch sys.modules['pytesseract']
                return pytesseract.image_to_string(preprocessed)
            except ImportError as exc:
                raise ProviderUnavailableError(
                    "OCR engine 'pytesseract' is not installed. "
                    "Install pytesseract to enable image OCR.") from exc
            except (ProviderError, ProviderUnavailableError):
                raise
            except Exception as exc:
                raise ProviderError(f"OCR execution failed: {exc}") from exc

        try:
            raw_text = await asyncio.to_thread(_run_ocr_pipeline)
        except (FileNotFoundError, ProviderUnavailableError, ProviderError):
            raise
        except Exception as exc:
            raise ProviderError(f"Failed to process image for OCR: {exc}") from exc

        return {
            "success": True,
            "file_path": file_path,
            "contrast_scale": _CONTRAST_SCALE,
            "raw_text": raw_text,
            "text": self.clean_parsed_text(raw_text),
            "checksum": self._get_sha256(file_path),
            "format": "ocr_image_autocorrect",
        }

    async def ocr_image(self, file_path: str) -> Dict[str, Any]:
        """Alias for :meth:`ocr_image_with_autocorrect`."""
        return await self.ocr_image_with_autocorrect(file_path)
