from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
from typing import Any

from .discover import discover_exact
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


def load_inventory(inventory_manifest: Path) -> list[dict[str, Any]]:
    records = list(read_jsonl(inventory_manifest))
    if not records:
        raise ValueError(f"No inventory records found in {inventory_manifest}")
    return records


def run_audit(
    seed_manifest: Path,
    inventory_manifest: Path,
    paths: list[Path],
    output: Path,
    *,
    expect_absent_prefixes: list[Path] | None = None,
    force: bool = False,
) -> int:
    """Rerun exact discovery and compare current reality to a frozen inventory.

    When expect_absent_prefixes are supplied, inventory instances beneath those
    prefixes are expected to be absent; all other inventoried instances are
    expected to remain present. Any new exact match is unexpected.
    """
    expected_absent_prefixes = expect_absent_prefixes or []
    inventory = load_inventory(inventory_manifest)
    current = discover_exact(seed_manifest, paths)

    audit_context = {
        "seed_manifest": str(seed_manifest.resolve()),
        "inventory_manifest": str(inventory_manifest.resolve()),
        "scan_paths": [str(path.resolve()) for path in paths],
        "expect_absent_prefixes": [
            str(prefix.resolve()) for prefix in expected_absent_prefixes
        ],
    }

    current_by_root: dict[str, dict[tuple[str, str, str], dict[str, Any]]] = defaultdict(dict)
    for record in current:
        root_id = str(record.root_id or "")
        key = (
            str(record.source_type or ""),
            _path_identity(str(record.location or "")),
            str(record.sha256 or ""),
        )
        current_by_root[root_id][key] = record.to_dict()

    audit_records: list[dict[str, Any]] = []
    total_expected_absent = 0
    total_verified_absent = 0
    total_expected_present = 0
    total_verified_present = 0
    total_unexpected_missing = 0
    total_unexpected_new = 0

    for root in inventory:
        root_id = str(root.get("root_id") or "")
        current_for_root = current_by_root.get(root_id, {})
        instance_results: list[dict[str, Any]] = []
        inventoried_keys_for_root: set[tuple[str, str, str]] = set()

        for instance in root.get("instances", []):
            source_type = str(instance.get("source_type") or "")
            location = str(instance.get("location") or "")
            sha256 = str(instance.get("sha256") or "")
            key = (source_type, _path_identity(location), sha256)
            inventoried_keys_for_root.add(key)

            expected_absent = any(
                _is_under(location, prefix) for prefix in expected_absent_prefixes
            )
            present_now = key in current_for_root

            if expected_absent:
                total_expected_absent += 1
                if present_now:
                    status = "EXPECTED_ABSENT_BUT_PRESENT"
                else:
                    status = "VERIFIED_ABSENT"
                    total_verified_absent += 1
            else:
                total_expected_present += 1
                if present_now:
                    status = "VERIFIED_PRESENT"
                    total_verified_present += 1
                else:
                    status = "UNEXPECTED_MISSING"
                    total_unexpected_missing += 1

            instance_results.append(
                {
                    "artifact_id": instance.get("artifact_id"),
                    "location": location,
                    "sha256": sha256,
                    "relation": instance.get("relation"),
                    "expected": "ABSENT" if expected_absent else "PRESENT",
                    "observed": "PRESENT" if present_now else "ABSENT",
                    "status": status,
                }
            )

        new_instances: list[dict[str, Any]] = []
        for key, record in current_for_root.items():
            if key in inventoried_keys_for_root:
                continue
            total_unexpected_new += 1
            new_instances.append(
                {
                    "artifact_id": record.get("artifact_id"),
                    "location": record.get("location"),
                    "sha256": record.get("sha256"),
                    "status": "UNEXPECTED_NEW_EXACT_MATCH",
                }
            )

        root_failed = any(
            item["status"] in {"EXPECTED_ABSENT_BUT_PRESENT", "UNEXPECTED_MISSING"}
            for item in instance_results
        ) or bool(new_instances)

        audit_records.append(
            {
                **audit_context,
                "root_id": root_id,
                "seed_filename": root.get("seed_filename"),
                "inventory_instance_count": root.get("instance_count"),
                "current_instance_count": len(current_for_root),
                "result": "FAIL" if root_failed else "PASS",
                "instances": instance_results,
                "unexpected_new_instances": new_instances,
            }
        )

    inventory_root_ids = {str(record.get("root_id") or "") for record in inventory}
    for root_id, records in current_by_root.items():
        if root_id in inventory_root_ids:
            continue
        for record in records.values():
            total_unexpected_new += 1
            audit_records.append(
                {
                    **audit_context,
                    "root_id": root_id,
                    "seed_filename": None,
                    "inventory_instance_count": 0,
                    "current_instance_count": 1,
                    "result": "FAIL",
                    "instances": [],
                    "unexpected_new_instances": [
                        {
                            "artifact_id": record.get("artifact_id"),
                            "location": record.get("location"),
                            "sha256": record.get("sha256"),
                            "status": "UNEXPECTED_NEW_EXACT_MATCH",
                        }
                    ],
                }
            )

    write_jsonl(output, audit_records, force=force)

    failures = (
        (total_expected_absent - total_verified_absent)
        + total_unexpected_missing
        + total_unexpected_new
    )
    overall = "PASS" if failures == 0 else "FAIL"

    print(f"Audit {overall} -> {output}")
    print(
        "Expected absent: "
        f"{total_verified_absent}/{total_expected_absent} verified absent; "
        "expected present: "
        f"{total_verified_present}/{total_expected_present} verified present; "
        f"unexpected missing: {total_unexpected_missing}; "
        f"unexpected new: {total_unexpected_new}"
    )
    return 0 if overall == "PASS" else 2
