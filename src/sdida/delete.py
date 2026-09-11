from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from .fingerprint import sha256_file
from .manifest import read_jsonl, write_jsonl


def _path_identity(value: str) -> str:
    return os.path.normcase(os.path.normpath(value))


def _is_under(location: str, prefix: Path) -> bool:
    """Return True when location is the prefix itself or is below it."""
    location_id = _path_identity(location)
    prefix_id = _path_identity(str(prefix.resolve()))
    try:
        return os.path.commonpath([location_id, prefix_id]) == prefix_id
    except ValueError:
        return False


def build_delete_approval(
    inventory_manifest: Path,
    prefixes: list[Path],
) -> list[dict[str, Any]]:
    """Select already-inventoried filesystem descendants for deletion.

    This function does not scan the filesystem and does not delete anything.
    It only turns a frozen inventory plus explicit path prefixes into an
    approval manifest.
    """
    if not prefixes:
        raise ValueError("At least one --under path prefix is required")

    inventory = list(read_jsonl(inventory_manifest))
    if not inventory:
        raise ValueError(f"No inventory records found in {inventory_manifest}")

    approved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for root in inventory:
        root_id = str(root.get("root_id") or "")
        for instance in root.get("instances", []):
            location = str(instance.get("location") or "")
            source_type = str(instance.get("source_type") or "")
            relation = str(instance.get("relation") or "")
            sha256 = str(instance.get("sha256") or "")

            if source_type != "filesystem":
                continue
            if relation == "SEED_LOCATION":
                continue
            if not location or not sha256:
                continue
            if not any(_is_under(location, prefix) for prefix in prefixes):
                continue

            key = (_path_identity(location), sha256)
            if key in seen:
                continue
            seen.add(key)

            approved.append(
                {
                    "artifact_id": instance.get("artifact_id"),
                    "root_id": root_id,
                    "source_type": source_type,
                    "location": location,
                    "filename": instance.get("filename"),
                    "sha256": sha256,
                    "relation": relation,
                    "classification": instance.get("classification"),
                    "state": "APPROVED_FOR_DESTRUCTION",
                    "approved_from_inventory": str(inventory_manifest),
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    approved.sort(key=lambda record: _path_identity(str(record["location"])))
    return approved


def run_approve_delete(
    inventory_manifest: Path,
    prefixes: list[Path],
    output: Path,
    *,
    force: bool = False,
) -> int:
    records = build_delete_approval(inventory_manifest, prefixes)
    write_jsonl(output, records, force=force)
    print(f"Approved {len(records)} inventoried descendants for deletion -> {output}")
    return 0


def execute_delete(
    approval_manifest: Path,
    *,
    execute: bool,
) -> list[dict[str, Any]]:
    """Validate and optionally delete only artifacts named in an approval manifest.

    The current file hash must still equal the approved SHA-256 immediately
    before deletion. A changed path is never deleted on the strength of stale
    inventory data.
    """
    approvals = list(read_jsonl(approval_manifest))
    if not approvals:
        raise ValueError(f"No approved deletion records found in {approval_manifest}")

    results: list[dict[str, Any]] = []

    for approval in approvals:
        location = str(approval.get("location") or "")
        approved_sha256 = str(approval.get("sha256") or "")
        state = str(approval.get("state") or "")
        source_type = str(approval.get("source_type") or "")

        base = {
            "artifact_id": approval.get("artifact_id"),
            "root_id": approval.get("root_id"),
            "source_type": source_type,
            "location": location,
            "approved_sha256": approved_sha256,
            "approval_manifest": str(approval_manifest),
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "mode": "EXECUTE" if execute else "DRY_RUN",
        }

        if state != "APPROVED_FOR_DESTRUCTION":
            results.append({**base, "result": "REFUSED_NOT_APPROVED"})
            continue
        if source_type != "filesystem":
            results.append({**base, "result": "REFUSED_UNSUPPORTED_SOURCE"})
            continue
        if not location or not approved_sha256:
            results.append({**base, "result": "REFUSED_INCOMPLETE_APPROVAL"})
            continue

        path = Path(location)
        if not path.exists():
            results.append({**base, "result": "ALREADY_ABSENT"})
            continue
        if not path.is_file():
            results.append({**base, "result": "REFUSED_NOT_FILE"})
            continue

        try:
            current_sha256 = sha256_file(path)
        except OSError as exc:
            results.append({**base, "result": "ERROR_HASHING", "error": str(exc)})
            continue

        if current_sha256 != approved_sha256:
            results.append(
                {
                    **base,
                    "current_sha256": current_sha256,
                    "result": "REFUSED_HASH_MISMATCH",
                }
            )
            continue

        if not execute:
            results.append(
                {
                    **base,
                    "current_sha256": current_sha256,
                    "result": "WOULD_DELETE",
                }
            )
            continue

        try:
            path.unlink()
            result = "DESTROYED" if not path.exists() else "ERROR_STILL_PRESENT"
            results.append(
                {
                    **base,
                    "current_sha256": current_sha256,
                    "result": result,
                }
            )
        except OSError as exc:
            results.append(
                {
                    **base,
                    "current_sha256": current_sha256,
                    "result": "ERROR_DELETING",
                    "error": str(exc),
                }
            )

    return results


def run_delete(
    approval_manifest: Path,
    output: Path,
    *,
    execute: bool = False,
    force: bool = False,
) -> int:
    records = execute_delete(approval_manifest, execute=execute)
    write_jsonl(output, records, force=force)

    counts: dict[str, int] = {}
    for record in records:
        result = str(record.get("result") or "UNKNOWN")
        counts[result] = counts.get(result, 0) + 1

    summary = "; ".join(f"{key}: {counts[key]}" for key in sorted(counts))
    mode = "EXECUTE" if execute else "DRY RUN"
    print(f"Delete {mode} -> {output}")
    print(summary)

    failure_results = {
        "REFUSED_NOT_APPROVED",
        "REFUSED_UNSUPPORTED_SOURCE",
        "REFUSED_INCOMPLETE_APPROVAL",
        "REFUSED_NOT_FILE",
        "REFUSED_HASH_MISMATCH",
        "ERROR_HASHING",
        "ERROR_DELETING",
        "ERROR_STILL_PRESENT",
    }
    failed = any(str(record.get("result")) in failure_results for record in records)
    return 2 if failed else 0
