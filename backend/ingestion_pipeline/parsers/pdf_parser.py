import uuid

try:
    import pypdf
except ImportError:  # pragma: no cover - optional dependency
    pypdf = None


def parse_pdf_resume(pdf_path, author=None):
    chunks = []
    if pypdf is None:
        print(f"PDF parsing skipped for {pdf_path}: pypdf is not installed")
        return chunks

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
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return chunks