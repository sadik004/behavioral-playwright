# Feature Specification: Document Namespace (`bp.document`)

> **Last Verified Against Commit**: `v10.0.2`
> **Status**: [VERIFIED]

---

## 1. Overview & Capabilities
The `DocumentNamespace` ([`veil/facade.py`](src/veil/facade.py)) provides spatial PDF/DOCX document parsing, table extraction, and image OCR with contrast enhancement.

---

## 2. API Method Reference

### `ocr_image_with_autocorrect(file_path)`
- **Signature**: `async def ocr_image_with_autocorrect(self, file_path: str) -> Dict[str, Any]`
- **Description**: Applies PIL grayscale, 1.5x contrast boost, offloads Tesseract OCR to a worker thread, computes SHA256 checksum, and cleans text.
- **Throws**: `FileNotFoundError` if image missing; `ProviderUnavailableError` if Tesseract is not installed; `ProviderError` on engine crash.

### `parse_pdf(file_path)`
- **Signature**: `async def parse_pdf(self, file_path: str) -> Dict[str, Any]`
- **Description**: Parses PDF text streams, reconstructs spatial 2-column reading order, and extracts metadata.

### `parse_docx(file_path)`
- **Signature**: `async def parse_docx(self, file_path: str) -> Dict[str, Any]`
- **Description**: Ingests Word (.docx) files, extracting paragraphs and structured tables.
