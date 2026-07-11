from __future__ import annotations

from io import BytesIO
from pathlib import Path
import shutil
from types import SimpleNamespace
import uuid


def _upload(name: str, content: bytes):
    return SimpleNamespace(filename=name, file=BytesIO(content))


def _local_tmp_dir() -> Path:
    path = Path("backend/tests/.tmp_uploads") / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_upload_txt_file_creates_chunks(monkeypatch):
    from backend.Ingestion import ingestion_service as service

    upload_dir = _local_tmp_dir()
    monkeypatch.setattr(service, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(service, "_persist", lambda run: None)

    def fake_run_extraction(run, chunks):
        run.chunks_created = len(chunks)
        run.nodes_created = 1

    monkeypatch.setattr(service, "_run_extraction", fake_run_extraction)

    try:
        run = service.ingest_upload([_upload("resume.txt", b"Built Chronos graph ingestion.")])

        assert run.status == "succeeded"
        assert run.files_received == 1
        assert run.files_parsed == 1
        assert run.files_failed == 0
        assert run.chunks_created == 1
    finally:
        shutil.rmtree(upload_dir.parent, ignore_errors=True)


def test_upload_unsupported_file_fails_clearly(monkeypatch):
    from backend.Ingestion import ingestion_service as service

    upload_dir = _local_tmp_dir()
    monkeypatch.setattr(service, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(service, "_persist", lambda run: None)

    try:
        run = service.ingest_upload([_upload("resume.docx", b"not supported")])

        assert run.status == "failed"
        assert run.files_received == 1
        assert run.files_failed == 1
        assert "Supported upload types" in run.errors[0]
    finally:
        shutil.rmtree(upload_dir.parent, ignore_errors=True)


def test_pdf_parser_missing_dependency_is_clear(monkeypatch):
    from backend.ingestion_pipeline.parsers import pdf_parser

    monkeypatch.setattr(pdf_parser, "pypdf", None)

    try:
        pdf_parser.parse_pdf_resume("resume.pdf")
    except pdf_parser.PdfParserError as exc:
        assert "pypdf is not installed" in str(exc)
        assert "requirements-cpu.txt" in str(exc)
    else:
        raise AssertionError("Expected PdfParserError")


def test_pdf_parser_no_selectable_text_warns(monkeypatch):
    from backend.ingestion_pipeline.parsers import pdf_parser

    class EmptyPage:
        def extract_text(self):
            return ""

    class Reader:
        pages = [EmptyPage()]

    monkeypatch.setattr(pdf_parser, "pypdf", SimpleNamespace(PdfReader=lambda _path: Reader()))
    warnings: list[str] = []

    chunks = pdf_parser.parse_pdf_resume("scanned.pdf", warnings=warnings)

    assert chunks == []
    assert warnings == [pdf_parser.NO_TEXT_PDF_MESSAGE]
