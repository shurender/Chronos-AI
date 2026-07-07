"""
Gap detection: bucket chunks by (project, month) and flag buckets with too few
source chunks as sparse-coverage periods. Runs over the raw chunk list, separate
from per-chunk extraction, since it's a corpus-level view.
"""

import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv

from backend.schema import GapRecord

load_dotenv()

GAP_MIN_CHUNKS = int(os.getenv("GAP_MIN_CHUNKS", "2"))


def _month_bucket(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return f"{dt.year:04d}-{dt.month:02d}"
    except ValueError:
        return None


def detect_gaps(chunks: list[dict], min_chunks: int = GAP_MIN_CHUNKS) -> list[GapRecord]:
    buckets: dict[tuple[str | None, str], int] = defaultdict(int)

    for chunk in chunks:
        project = chunk.get("project")
        period = _month_bucket(chunk.get("timestamp"))
        if period is None:
            continue  # missing timestamps are their own kind of gap; log separately if needed
        buckets[(project, period)] += 1

    gaps = [
        GapRecord(project=project, period=period, chunk_count=count)
        for (project, period), count in buckets.items()
        if count < min_chunks
    ]
    return sorted(gaps, key=lambda g: (g.project or "", g.period))


def detect_missing_timestamps(chunks: list[dict]) -> list[dict]:
    """Chunks with no timestamp at all are gaps we can't even bucket — surface them separately."""
    return [c for c in chunks if not c.get("timestamp")]