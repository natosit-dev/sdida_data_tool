from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from .models import ArtifactRecord


def _record_dict(record: ArtifactRecord | dict[str, Any]) -> dict[str, Any]:
    return record.to_dict() if isinstance(record, ArtifactRecord) else record


def append_jsonl(path: Path, records: Iterable[ArtifactRecord | dict[str, Any]]) -> None:
    """Append records to a JSONL audit stream."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_record_dict(record), sort_keys=True) + "\n")


def write_jsonl(
    path: Path,
    records: Iterable[ArtifactRecord | dict[str, Any]],
    *,
    force: bool = False,
) -> None:
    """Write a frozen JSONL snapshot.

    Refuses to overwrite an existing manifest unless force=True.
    """
    if path.exists() and not force:
        raise FileExistsError(f"Manifest already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_record_dict(record), sort_keys=True) + "\n")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Read a JSONL manifest as dictionaries."""
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path} at line {line_number}: {exc}"
                ) from exc
