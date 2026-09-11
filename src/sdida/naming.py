from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%z")


def timestamped_manifest_path(kind: str) -> Path:
    """Return a local-time, timezone-stamped manifest path safe for Windows filenames."""
    return Path("manifests") / f"{kind}_manifest_{_stamp()}.jsonl"


def timestamped_record_path(kind: str) -> Path:
    """Return a local-time, timezone-stamped JSON record path safe for Windows filenames."""
    return Path("manifests") / f"{kind}_record_{_stamp()}.json"
