from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sdida.fingerprint import sha256_file
from sdida.models import ArtifactRecord


def scan_paths(paths: list[Path], seed_hashes: set[str]) -> list[ArtifactRecord]:
    """Scan files under paths for exact SHA-256 matches.

    This function is read-only. It does not move, quarantine, or delete files.
    """
    results: list[ArtifactRecord] = []

    for root in paths:
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file():
                continue
            try:
                digest = sha256_file(path)
            except OSError:
                continue
            if digest not in seed_hashes:
                continue

            results.append(
                ArtifactRecord.from_path(
                    artifact_id=f"A-{uuid4().hex[:12]}",
                    path=path,
                    sha256=digest,
                    match_method="sha256_exact",
                )
            )

    return results
