import uuid

try:
    import pypdf
except ImportError:  # pragma: no cover - optional dependency
    pypdf = None

MISSING_PYPDF_MESSAGE = (
    "PDF parsing dependency pypdf is not installed. Run pip install -r requirements-cpu.txt."
)
NO_TEXT_PDF_MESSAGE = (
    "No selectable text found in this PDF. It may be scanned/image-only. OCR is not enabled yet."
)


class PdfParserError(RuntimeError):
    pass


def parse_pdf_resume(pdf_path, author=None, warnings=None):
    chunks = []
    if pypdf is None:
        raise PdfParserError(MISSING_PYPDF_MESSAGE)

    try:
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text or not text.strip():
                continue

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_type": "pdf_resume",
                "source_id": f"{pdf_path}#page={i+1}",
                "raw_text": text.strip(),
                "author": author,
                "timestamp": None,  # Left null intentionally for gap detection accuracy
                "project": None,
                "metadata": {
                    "file_path": pdf_path,
                    "page_number": i + 1,
                    "total_pages": len(reader.pages)
                }
            })
    except PdfParserError:
        raise
    except Exception as e:
        raise PdfParserError(f"Error reading PDF {pdf_path}: {e}") from e
    if not chunks and warnings is not None:
        warnings.append(NO_TEXT_PDF_MESSAGE)
    return chunks
