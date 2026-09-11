# Image OCR & Autocorrection Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Contrast-Enhanced Image OCR

Extract text from image scans, invoices, and screenshots with 1.5x contrast boost and background worker thread execution:

```python
import asyncio
from bp_facade12 import BP

async def scan_image():
    async with BP() as bp:
        ocr_result = await bp.document.ocr_image_with_autocorrect("invoice_scan.png")
        print("Recognized Text:\n", ocr_result["text"])
        print("Image SHA256 Checksum:", ocr_result["checksum"])
        print("Metadata:", ocr_result["metadata"])

if __name__ == "__main__":
    asyncio.run(scan_image())
```

---

## 2. Error Handling & Provider Detection
- If the image path does not exist, raises `FileNotFoundError`.
- If the system `tesseract` binary is missing from PATH, raises `ProviderUnavailableError`.
- If the OCR engine crashes during decoding, raises `ProviderError`.
