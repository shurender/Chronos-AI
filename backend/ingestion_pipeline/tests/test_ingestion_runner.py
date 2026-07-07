import os
import subprocess
import sys
from pathlib import Path


def test_ingestion_runner_creates_output(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    ingestion_dir = repo_root / "backend" / "ingestion_pipeline"

    proc = subprocess.run(
        [sys.executable, "ingestion_runner.py"],
        cwd=ingestion_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr or proc.stdout

    output_path = ingestion_dir / "ingestion_output.jsonl"
    assert output_path.exists(), proc.stdout
    lines = [line for line in output_path.read_text().splitlines() if line.strip()]
    assert len(lines) >= 3, proc.stdout
