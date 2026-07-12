"""
API-driven ingestion service.

Parses sources (demo mock files / a public GitHub repo / uploaded files) into
Chunk-shaped dicts, then runs the SAME extraction pipeline + storage used by
`backend/main.py` (Decision_Graph.extraction_pipeline + backend.storage) so
the resulting graph/vector-store state is exactly what /graph, /query/similar,
and /simulate already read from. Synchronous by design — reliability over
concurrency for now.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import UploadFile

from backend import config
from backend.Decision_Graph.extraction_pipeline import build_pipeline, run_pipeline_on_chunk
from backend.ingestion_pipeline.parsers.github_parser import parse_github_commits, parse_github_issues
from backend.ingestion_pipeline.parsers.notion_parser import parse_notion_markdown
from backend.ingestion_pipeline.parsers.pdf_parser import PdfParserError, parse_pdf_resume
from backend.ingestion_pipeline.parsers.slack_parser import parse_slack_export
from backend.llm import embed_text
from backend.logging_config import get_logger
from backend.storage import (
    G,
    add_chunk_to_chroma,
    get_chunk_metadata,
    remove_graph_records_for_chunk,
    reset_all as _storage_reset_all,
    save_graph,
)

from .ingestion_schema import IngestGithubRequest, IngestionRun

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
RAW_SOURCES_DIR = BASE_DIR.parent / "ingestion_pipeline" / "raw_sources"
UPLOAD_DIR = BASE_DIR / "uploads"

RUNS_STORE_PATH = os.getenv("INGESTION_RUNS_STORE_PATH", str(BASE_DIR / "runs.json"))

_lock = threading.Lock()
_runs: dict[str, dict] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    if os.path.exists(RUNS_STORE_PATH):
        with open(RUNS_STORE_PATH, "r", encoding="utf-8") as f:
            try:
                _runs.update(json.load(f))
            except json.JSONDecodeError:
                pass
    _loaded = True


def _persist(run: IngestionRun) -> None:
    _ensure_loaded()
    with _lock:
        _runs[run.run_id] = json.loads(run.model_dump_json())
        os.makedirs(os.path.dirname(RUNS_STORE_PATH) or ".", exist_ok=True)
        with open(RUNS_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(_runs, f, indent=2, default=str)


def list_runs(limit: int = 50, offset: int = 0) -> list[dict]:
    _ensure_loaded()
    items = sorted(_runs.values(), key=lambda r: r.get("started_at", ""), reverse=True)
    return items[offset : offset + limit]


def get_run(run_id: str) -> dict | None:
    _ensure_loaded()
    return _runs.get(run_id)


# ---------------------------------------------------------------------------
# Shared: run chunks through extraction + storage
# ---------------------------------------------------------------------------


def _run_extraction(run: IngestionRun, chunks: list[dict]) -> None:
    """Feeds chunks through the extraction pipeline, mutating `run` in place with
    counts/warnings/errors. Never raises — a bad chunk is recorded, not fatal."""
    deduped_chunks: list[dict] = []
    dedupe_counts = {"fetched": len(chunks), "new": 0, "updated": 0, "skipped_duplicate": 0, "failed": 0}
    for chunk in chunks:
        text = chunk.get("raw_text", "")
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        meta = chunk.setdefault("metadata", {})
        meta["content_hash"] = content_hash
        meta.setdefault("connector_provider", meta.get("connector_provider") or chunk.get("source_type"))
        meta.setdefault("connector_source_id", meta.get("connector_source_id") or chunk.get("project") or chunk.get("source_id"))
        meta.setdefault("external_id", meta.get("external_id") or chunk.get("source_id"))
        meta.setdefault("source_name", meta.get("source_name") or chunk.get("project") or chunk.get("source_id") or chunk["chunk_id"])
        meta.setdefault("source_url", meta.get("source_url") or meta.get("url") or chunk.get("source_url"))
        existing = get_chunk_metadata(chunk["chunk_id"])
        if existing and existing.get("content_hash") == content_hash:
            dedupe_counts["skipped_duplicate"] += 1
            continue
        if existing:
            remove_graph_records_for_chunk(chunk["chunk_id"])
            dedupe_counts["updated"] += 1
        else:
            dedupe_counts["new"] += 1
        deduped_chunks.append(chunk)

    run.source_summary = {**run.source_summary, **dedupe_counts}
    chunks = deduped_chunks
    run.chunks_created = len(chunks)
    if not chunks:
        run.warnings.append("No chunks were produced from the given source(s).")
        return

    pipeline = build_pipeline()
    nodes_before, edges_before = G.number_of_nodes(), G.number_of_edges()

    from backend import config
    from backend.Safety.redaction import redact

    contradiction_count = 0
    contradiction_chunk_count = 0

    for chunk in chunks:
        # Privacy: redact PII/secrets from raw_text BEFORE it is embedded, stored,
        # or extracted — unless explicitly configured to store raw. Never logs the
        # matched values.
        if not config.STORE_RAW_UNREDACTED:
            redacted_text, categories, n = redact(chunk.get("raw_text", ""))
            if n:
                chunk["raw_text"] = redacted_text
                meta = chunk.setdefault("metadata", {})
                meta["pii_redacted"] = True
                meta["redaction_categories"] = ",".join(categories)

        # Provenance: every chunk becomes a retrievable SourceRecord (source_id
        # shares the chunk_id namespace). Best-effort — never blocks ingestion.
        try:
            from backend.Provenance.provenance_schema import SourceRecord
            from backend.Provenance.provenance_service import create_source

            create_source(
                SourceRecord(
                    source_id=chunk["chunk_id"],
                    source_type=chunk.get("source_type", "unknown"),
                    source_name=chunk.get("metadata", {}).get("source_name")
                    or chunk.get("source_id")
                    or chunk.get("project")
                    or chunk["chunk_id"],
                    uri=chunk.get("metadata", {}).get("source_url"),
                    source_url=chunk.get("metadata", {}).get("source_url"),
                    connector_provider=chunk.get("metadata", {}).get("connector_provider"),
                    external_id=chunk.get("metadata", {}).get("external_id"),
                    content_hash=chunk.get("metadata", {}).get("content_hash"),
                    author=chunk.get("author"),
                    timestamp=chunk.get("timestamp"),
                    project=chunk.get("project"),
                    raw_excerpt=(chunk.get("raw_text") or "")[:1000],
                    metadata=chunk.get("metadata", {}),
                )
            )
        except Exception as exc:  # noqa: BLE001 — provenance is best-effort
            logger.warning("Provenance source record failed for %s: %s", chunk.get("chunk_id"), exc)

        try:
            add_chunk_to_chroma(
                chunk_id=chunk["chunk_id"],
                text=chunk["raw_text"],
                metadata={
                    "source_type": chunk.get("metadata", {}).get("connector_provider") or chunk.get("source_type"),
                    "author": chunk.get("author"),
                    "timestamp": chunk.get("timestamp"),
                    "project": chunk.get("project"),
                    "source_id": chunk.get("source_id"),
                    "source_name": chunk.get("metadata", {}).get("source_name"),
                    "source_url": chunk.get("metadata", {}).get("source_url"),
                    "external_id": chunk.get("metadata", {}).get("external_id"),
                    "connector_provider": chunk.get("metadata", {}).get("connector_provider"),
                    "connector_source_id": chunk.get("metadata", {}).get("connector_source_id"),
                    "source_auth": chunk.get("metadata", {}).get("source_auth"),
                    "source_live": bool(chunk.get("metadata", {}).get("source_live", False)),
                    "content_hash": chunk.get("metadata", {}).get("content_hash"),
                    "pii_redacted": bool(chunk.get("metadata", {}).get("pii_redacted", False)),
                },
                embedding=embed_text(chunk["raw_text"]),
            )
            result = run_pipeline_on_chunk(pipeline, chunk)
            contradictions = result.get("contradictions", [])
            if contradictions:
                contradiction_count += len(contradictions)
                contradiction_chunk_count += 1
        except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
            logger.warning("Chunk %s failed extraction: %s", chunk.get("chunk_id"), exc)
            run.errors.append(f"chunk {chunk.get('chunk_id', '?')}: {exc}")

    if contradiction_count:
        run.warnings.append(
            f"{contradiction_count} possible contradiction(s) flagged across {contradiction_chunk_count} chunk(s). Review graph evidence before relying on these extracted claims."
        )

    save_graph()
    run.nodes_created = G.number_of_nodes() - nodes_before
    run.edges_created = G.number_of_edges() - edges_before


def _finalize(run: IngestionRun) -> IngestionRun:
    # Only a total wipeout (every chunk errored, nothing written) counts as
    # "failed" — partial success still surfaces its errors/warnings but the run
    # as a whole succeeded, matching "reliability > complexity".
    if run.source_type == "upload" and run.chunks_created == 0 and run.nodes_created == 0 and run.edges_created == 0:
        run.status = "failed"
    elif run.errors and run.nodes_created == 0 and run.edges_created == 0 and run.chunks_created > 0:
        run.status = "failed"
    else:
        run.status = "succeeded"
    run.completed_at = datetime.utcnow()
    _persist(run)
    return run


def _fail(run: IngestionRun, message: str) -> IngestionRun:
    run.status = "failed"
    run.errors.append(message)
    run.completed_at = datetime.utcnow()
    _persist(run)
    return run


# ---------------------------------------------------------------------------
# POST /ingest/demo
# ---------------------------------------------------------------------------


def ingest_demo() -> IngestionRun:
    run = IngestionRun(source_type="demo", status="running")
    _persist(run)

    chunks: list[dict] = []
    summary: dict[str, int] = {}

    try:
        github_file = RAW_SOURCES_DIR / "sample_github.json"
        if github_file.exists():
            data = json.loads(github_file.read_text(encoding="utf-8"))
            commit_chunks = parse_github_commits(data.get("commits", []), "Chronos-AI")
            issue_chunks = parse_github_issues(data.get("issues", []), "Chronos-AI")
            chunks.extend(commit_chunks)
            chunks.extend(issue_chunks)
            summary["github_commits"] = len(commit_chunks)
            summary["github_issues"] = len(issue_chunks)

        slack_file = RAW_SOURCES_DIR / "sample_slack.json"
        if slack_file.exists():
            data = json.loads(slack_file.read_text(encoding="utf-8"))
            slack_chunks = parse_slack_export(data, "dev-team")
            chunks.extend(slack_chunks)
            summary["slack_messages"] = len(slack_chunks)

        notion_file = RAW_SOURCES_DIR / "sample_notion.json"
        if notion_file.exists():
            content = notion_file.read_text(encoding="utf-8")
            notion_chunks = parse_notion_markdown(content, str(notion_file), "Project Specs")
            chunks.extend(notion_chunks)
            summary["notion_pages"] = len(notion_chunks)

        pdf_file = RAW_SOURCES_DIR / "sample_resume.pdf"
        if pdf_file.exists():
            pdf_chunks = parse_pdf_resume(str(pdf_file), author="Jane Doe")
            chunks.extend(pdf_chunks)
            summary["pdf_resumes"] = len(pdf_chunks)
    except Exception as exc:
        return _fail(run, f"Failed to parse demo sources: {exc}")

    run.source_summary = summary
    for chunk in chunks:
        meta = chunk.setdefault("metadata", {})
        meta["source_auth"] = "demo"
        meta["source_live"] = False
    _run_extraction(run, chunks)
    return _finalize(run)


# ---------------------------------------------------------------------------
# POST /ingest/github
# ---------------------------------------------------------------------------


def _parse_repo_ref(repo: str) -> tuple[str, str]:
    repo = repo.strip()
    if repo.startswith("http://") or repo.startswith("https://"):
        parts = [p for p in repo.rstrip("/").split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Could not parse owner/repo from URL: {repo!r}")
        owner, name = parts[-2], parts[-1]
        if name.endswith(".git"):
            name = name[: -len(".git")]
        return owner, name
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return owner, name
    raise ValueError(f"Invalid repo reference {repo!r}. Use 'owner/repo' or a GitHub URL.")


def _fetch_github(owner: str, name: str, include_issues: bool, max_items: int) -> tuple[list[dict], list[dict]]:
    """Public GitHub REST API — no OAuth required for public repos. Uses GITHUB_TOKEN
    as a Bearer token if set (raises the unauthenticated 60 req/hr rate limit),
    but works without one for public repos."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") if config.GITHUB_PUBLIC_INGEST_USE_TOKEN else None
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base = f"https://api.github.com/repos/{owner}/{name}"
    try:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            commits_res = client.get(f"{base}/commits", params={"per_page": max_items})
    except httpx.RequestError as exc:
        raise RuntimeError(f"No network access to GitHub API: {exc}") from exc

    if commits_res.status_code == 404:
        raise RuntimeError(f"Repository '{owner}/{name}' not found (or private — OAuth is not implemented yet).")
    if commits_res.status_code == 403:
        raise RuntimeError(
            "GitHub API rate limit exceeded or access forbidden. "
            "Set a GITHUB_TOKEN env var to raise the unauthenticated rate limit."
        )
    commits_res.raise_for_status()
    raw_commits = commits_res.json()

    raw_issues: list[dict] = []
    if include_issues:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            issues_res = client.get(f"{base}/issues", params={"per_page": max_items, "state": "all"})
        issues_res.raise_for_status()
        raw_issues = issues_res.json()

    return raw_commits, raw_issues


def _map_real_commits(raw_commits: list[dict]) -> list[dict]:
    mapped = []
    for c in raw_commits:
        commit = c.get("commit") or {}
        author_info = commit.get("author") or {}
        mapped.append(
            {
                "sha": c.get("sha"),
                "author": author_info.get("name") or "unknown",
                "timestamp": author_info.get("date"),
                "message": commit.get("message", ""),
                # The commits-list endpoint doesn't include full diffs (an extra
                # per-commit request would burn the unauthenticated rate limit).
                "diff": "",
            }
        )
    return mapped


def _map_real_issues(raw_issues: list[dict]) -> list[dict]:
    mapped = []
    for i in raw_issues:
        mapped.append(
            {
                "id": i.get("id"),
                "number": i.get("number"),
                "title": i.get("title", ""),
                "body": i.get("body") or "",
                "author": (i.get("user") or {}).get("login", "unknown"),
                "timestamp": i.get("created_at"),
            }
        )
    return mapped


def ingest_github(request: IngestGithubRequest, *, authenticated: bool = False) -> IngestionRun:
    run = IngestionRun(source_type="github", status="running")
    _persist(run)

    try:
        owner, name = _parse_repo_ref(request.repo)
        raw_commits, raw_issues = _fetch_github(owner, name, request.include_issues, request.max_items)
    except Exception as exc:
        return _fail(run, str(exc))

    repo_label = f"{owner}/{name}"
    commit_chunks = parse_github_commits(_map_real_commits(raw_commits), repo_label)
    issue_chunks = parse_github_issues(_map_real_issues(raw_issues), repo_label) if raw_issues else []
    for chunk in commit_chunks + issue_chunks:
        meta = chunk.setdefault("metadata", {})
        meta["connector_provider"] = "github"
        meta["source_auth"] = "authenticated" if authenticated or os.getenv("GITHUB_TOKEN") else "public"
        meta["source_live"] = True

    run.source_summary = {
        "repo": repo_label,
        "commits_fetched": len(raw_commits),
        "issues_fetched": len(raw_issues),
    }
    _run_extraction(run, commit_chunks + issue_chunks)
    return _finalize(run)


def ingest_connector_chunks(
    source_type: str,
    chunks: list[dict],
    source_summary: dict | None = None,
) -> IngestionRun:
    """Ingest already-fetched live connector chunks through the shared pipeline."""
    run = IngestionRun(source_type=source_type, status="running")
    _persist(run)
    run.source_summary = source_summary or {}
    for chunk in chunks:
        meta = chunk.setdefault("metadata", {})
        meta.setdefault("connector_provider", source_type)
        meta.setdefault("source_auth", "authenticated")
        meta.setdefault("source_live", True)
    _run_extraction(run, chunks)
    return _finalize(run)


# ---------------------------------------------------------------------------
# POST /ingest/upload
# ---------------------------------------------------------------------------


def ingest_upload(files: list[UploadFile]) -> IngestionRun:
    run = IngestionRun(source_type="upload", status="running")
    _persist(run)

    chunks: list[dict] = []
    filenames: list[str] = []
    parsed_files: list[str] = []
    failed_files: list[str] = []

    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        for f in files:
            original_name = Path(f.filename or "upload").name  # strip any path components
            run.files_received += 1
            safe_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
            dest = UPLOAD_DIR / safe_name
            dest.write_bytes(f.file.read())
            filenames.append(original_name)

            suffix = dest.suffix.lower()
            before = len(chunks)
            if suffix == ".pdf":
                try:
                    chunks.extend(parse_pdf_resume(str(dest), author="Uploaded User", warnings=run.warnings))
                except PdfParserError as exc:
                    failed_files.append(original_name)
                    run.files_failed += 1
                    run.errors.append(f"{original_name}: {exc}")
                    continue
            elif suffix in (".md", ".markdown"):
                chunks.extend(
                    parse_notion_markdown(dest.read_text(encoding="utf-8"), str(dest), dest.stem)
                )
            elif suffix == ".txt":
                text = dest.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    chunks.append(
                        {
                            "chunk_id": str(uuid.uuid4()),
                            "source_type": "uploaded_file",
                            "source_id": original_name,
                            "raw_text": text[:5000],
                            "author": None,
                            "timestamp": None,
                            "project": "uploaded",
                            "metadata": {"original_filename": original_name},
                        }
                    )
                else:
                    run.warnings.append(f"{original_name}: uploaded text file is empty.")
            elif suffix == ".json":
                data = json.loads(dest.read_text(encoding="utf-8"))
                if isinstance(data, dict) and ("commits" in data or "issues" in data):
                    chunks.extend(parse_github_commits(data.get("commits", []), dest.stem))
                    chunks.extend(parse_github_issues(data.get("issues", []), dest.stem))
                else:
                    chunks.append(
                        {
                            "chunk_id": str(uuid.uuid4()),
                            "source_type": "uploaded_file",
                            "source_id": original_name,
                            "raw_text": json.dumps(data, indent=2)[:5000],
                            "author": None,
                            "timestamp": None,
                            "project": "uploaded",
                            "metadata": {"original_filename": original_name},
                        }
                    )
            else:
                failed_files.append(original_name)
                run.files_failed += 1
                run.errors.append(
                    f"Unsupported file type skipped: {original_name}. Supported upload types: .pdf, .txt, .md, .markdown, .json."
                )
                continue

            if len(chunks) > before:
                parsed_files.append(original_name)
                run.files_parsed += 1
            else:
                failed_files.append(original_name)
                run.files_failed += 1
    except Exception as exc:
        return _fail(run, f"Failed to process uploaded file(s): {exc}")

    run.source_summary = {
        "files": filenames,
        "files_received": run.files_received,
        "files_parsed": parsed_files,
        "files_failed": failed_files,
    }
    if not chunks:
        if not run.errors and not run.warnings:
            run.errors.append("Uploaded file(s) produced no readable text chunks.")
        return _finalize(run)

    for chunk in chunks:
        meta = chunk.setdefault("metadata", {})
        meta["connector_provider"] = "upload"
        meta["source_auth"] = "uploaded"
        meta["source_live"] = False
    _run_extraction(run, chunks)
    return _finalize(run)


# ---------------------------------------------------------------------------
# POST /ingest/reset
# ---------------------------------------------------------------------------


def reset_all() -> tuple[int, int]:
    nodes_before, edges_before = G.number_of_nodes(), G.number_of_edges()
    _storage_reset_all()
    return nodes_before, edges_before
