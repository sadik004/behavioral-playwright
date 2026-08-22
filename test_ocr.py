import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image, ImageDraw

# Stub behavioral_playwright packages if not installed in local environment
class MockProviderUnavailableError(Exception):
    pass

class MockProviderError(Exception):
    pass

class MockInvalidRequestError(Exception):
    pass

for mod in [
    'behavioral_playwright',
    'behavioral_playwright.core',
    'behavioral_playwright.core.config',
    'behavioral_playwright.core.exceptions',
    'behavioral_playwright.core.circuit_breaker',
    'behavioral_playwright.core.v10_core',
    'behavioral_playwright.acquisition',
    'behavioral_playwright.acquisition.exceptions',
    'behavioral_playwright.acquisition.models',
    'behavioral_playwright.acquisition.router',
    'behavioral_playwright.acquisition.handoff',
]:
    if mod not in sys.modules:
        m = MagicMock()
        if mod == 'behavioral_playwright.acquisition.exceptions':
            m.ProviderUnavailableError = MockProviderUnavailableError
            m.InvalidRequestError = MockInvalidRequestError
        elif mod == 'behavioral_playwright.core.exceptions':
            m.ProviderError = MockProviderError
        sys.modules[mod] = m

from bp_facade12 import BP, ProviderUnavailableError, ProviderError


@pytest.fixture
def sample_image_path(tmp_path):
    """Creates a minimal readable test image."""
    img_path = str(tmp_path / "test_invoice.png")
    img = Image.new("RGB", (200, 80), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "INVOICE #12345", fill=(0, 0, 0))
    img.save(img_path)
    return img_path


@pytest.mark.asyncio
async def test_ocr_missing_file_raises_filenotfound():
    """Verify that a non-existent image path raises FileNotFoundError."""
    bp = BP()
    with pytest.raises(FileNotFoundError):
        await bp.document.ocr_image_with_autocorrect("non_existent_image_12345.png")


@pytest.mark.asyncio
async def test_ocr_missing_engine_raises_provider_unavailable(sample_image_path):
    """Verify that when pytesseract is not installed, ProviderUnavailableError is raised instead of returning fake text."""
    bp = BP()
    with patch.dict(sys.modules, {'pytesseract': None}):
        with pytest.raises(ProviderUnavailableError, match="OCR engine 'pytesseract' is not installed"):
            await bp.document.ocr_image_with_autocorrect(sample_image_path)


@pytest.mark.asyncio
async def test_ocr_real_pipeline_success_with_engine(sample_image_path):
    """Verify that when pytesseract is available, real OCR extraction and cleaning occurs."""
    bp = BP()
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "INVOICE #12345 CONFIDENTIAL"

    with patch.dict(sys.modules, {'pytesseract': mock_pytesseract}):
        result = await bp.document.ocr_image_with_autocorrect(sample_image_path)

        assert result["success"] is True
        assert result["file_path"] == sample_image_path
        assert result["raw_text"] == "INVOICE #12345 CONFIDENTIAL"
        assert result["text"] == "INVOICE #12345"
        assert len(result["checksum"]) == 64
        assert result["format"] == "ocr_image_autocorrect"
        assert "Simulated High-Contrast OCR" not in result["text"]


@pytest.mark.asyncio
async def test_ocr_engine_execution_failure_raises_provider_error(sample_image_path):
    """Verify that an underlying engine execution crash raises ProviderError."""
    bp = BP()
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.side_effect = RuntimeError("Tesseract binary crashed")

    with patch.dict(sys.modules, {'pytesseract': mock_pytesseract}):
        with pytest.raises(ProviderError, match="OCR execution failed"):
            await bp.document.ocr_image_with_autocorrect(sample_image_path)


@pytest.mark.asyncio
async def test_ocr_top_level_bp_delegates(sample_image_path):
    """Verify top-level BP methods delegate to DocumentNamespace."""
    bp = BP()
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "TOTAL: $100.00"

    with patch.dict(sys.modules, {'pytesseract': mock_pytesseract}):
        res1 = await bp.ocr_image(sample_image_path)
        assert res1["text"] == "TOTAL: $100.00"

        res2 = await bp.ocr_image_with_autocorrect(sample_image_path)
        assert res2["text"] == "TOTAL: $100.00"
