"""Shared helpers for data download scripts.

Every script writes:
    raw/<dataset>_<YYYYMMDD>.<ext>
and appends a manifest row to data/download_log.md with sha256, source URL,
script path and timestamp (UTC). This keeps the AFA provenance trail clean.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sys
from pathlib import Path
from typing import Iterable

DATA_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = DATA_DIR / "raw"
LOG_PATH = DATA_DIR / "download_log.md"
PROJECT_TZ = "UTC"


def utc_stamp() -> str:
    """Return a UTC timestamp suitable for filenames."""
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def utc_date() -> str:
    """Return a UTC date suitable for filenames."""
    return dt.datetime.utcnow().strftime("%Y%m%d")


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def append_manifest(
    dataset: str,
    source: str,
    script: str,
    output: Path,
    note: str = "",
) -> None:
    """Append a row to data/download_log.md."""
    sha = sha256_of(output)
    row = (
        f"| {utc_stamp()} | {dataset} | {source} | `{script}` | "
        f"`{output.relative_to(DATA_DIR).as_posix()}` | {sha} | {note} |"
    )
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write("\n" + row)


def ensure_raw_dir() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_DIR
