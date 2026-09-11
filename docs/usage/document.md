# Document Ingestion Usage Guide (PDF / DOCX)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Spatial PDF & DOCX Parsing

Extract text with 2-column layout reconstruction and table structures from local documents:

```python
import asyncio
from bp_facade12 import BP

async def process_documents():
    async with BP() as bp:
        # Parse PDF with spatial reading order
        pdf_res = await bp.document.parse_pdf("sample.pdf")
        print(f"PDF Pages: {pdf_res['pages_count']}")
        print("Text Snippet:", pdf_res["text"][:200])

        # Parse Word (.docx) Document
        docx_res = await bp.document.parse_docx("report.docx")
        print(f"DOCX Paragraphs: {len(docx_res.get('paragraphs', []))}")

if __name__ == "__main__":
    asyncio.run(process_documents())
```
