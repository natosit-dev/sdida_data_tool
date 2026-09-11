from __future__ import annotations

from collections import Counter
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .fingerprint import sha256_file
from .manifest import read_jsonl


EXECUTION_FAILURE_RESULTS = {
    "REFUSED_NOT_APPROVED",
    "REFUSED_UNSUPPORTED_SOURCE",
    "REFUSED_INCOMPLETE_APPROVAL",
    "REFUSED_NOT_FILE",
    "REFUSED_HASH_MISMATCH",
    "ERROR_HASHING",
    "ERROR_DELETING",
    "ERROR_STILL_PRESENT",
}


def _path_identity(value: str) -> str:
    return os.path.normcase(os.path.normpath(value))


def _resolved_identity(path: Path) -> str:
    return _path_identity(str(path.resolve()))


def _recorded_path_identity(value: Any) -> str | None:
    if not value:
        return None
    return _path_identity(str(Path(str(value)).resolve()))


def _package_version() -> str | None:
    try:
        return version("sdida")
    except PackageNotFoundError:
        return None


def _git_commit() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _evidence_entry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Evidence file does not exist: {path}")
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def _derived_discovery_paths(inventory: list[dict[str, Any]]) -> list[Path]:
    values: set[str] = set()
    for root in inventory:
        for instance in root.get("instances", []):
            for observed_in in instance.get("observed_in", []):
                if observed_in:
                    values.add(str(observed_in))
    return [Path(value) for value in sorted(values)]


def _approval_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        _path_identity(str(record.get("location") or "")),
        str(record.get("sha256") or ""),
    )


def _deletion_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        _path_identity(str(record.get("location") or "")),
        str(record.get("approved_sha256") or ""),
    )


def _validate_chain(
    seed_manifest: Path,
    inventory_manifest: Path,
    approval_manifest: Path,
    seed: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    deletions: list[dict[str, Any]],
    audit: list[dict[str, Any]],
) -> dict[str, bool]:
    seed_id = _resolved_identity(seed_manifest)
    inventory_id = _resolved_identity(inventory_manifest)
    approval_id = _resolved_identity(approval_manifest)

    seed_hashes = {
        str(record.get("artifact_id") or ""): str(record.get("sha256") or "")
        for record in seed
    }
    inventory_hashes = {
        str(record.get("root_id") or ""): str(record.get("seed_sha256") or "")
        for record in inventory
    }

    approval_inventory_links = {
        _recorded_path_identity(record.get("approved_from_inventory"))
        for record in approvals
        if record.get("approved_from_inventory")
    }
    deletion_approval_links = {
        _recorded_path_identity(record.get("approval_manifest"))
        for record in deletions
        if record.get("approval_manifest")
    }
    audit_seed_links = {
        _recorded_path_identity(record.get("seed_manifest"))
        for record in audit
        if record.get("seed_manifest")
    }
    audit_inventory_links = {
        _recorded_path_identity(record.get("inventory_manifest"))
        for record in audit
        if record.get("inventory_manifest")
    }

    approval_keys = {_approval_key(record) for record in approvals}
    deletion_keys = {_deletion_key(record) for record in deletions}
    audit_root_ids = {str(record.get("root_id") or "") for record in audit}
    inventory_root_ids = set(inventory_hashes)

    checks = {
        "inventory_root_set_matches_seed": set(seed_hashes) == inventory_root_ids,
        "inventory_seed_hashes_match_seed": seed_hashes == inventory_hashes,
        "approval_references_inventory": approval_inventory_links == {inventory_id},
        "deletion_references_approval": deletion_approval_links == {approval_id},
        "deletion_target_set_matches_approval": approval_keys == deletion_keys,
        "deletion_record_count_matches_approval": len(deletions) == len(approvals),
        "audit_references_seed": audit_seed_links == {seed_id},
        "audit_references_inventory": audit_inventory_links == {inventory_id},
        "audit_root_set_matches_inventory": audit_root_ids == inventory_root_ids,
    }

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(
            "Evidence chain validation failed: " + ", ".join(sorted(failed))
        )

    return checks


def build_assurance_record(
    seed_manifest: Path,
    inventory_manifest: Path,
    approval_manifest: Path,
    deletion_manifest: Path,
    audit_manifest: Path,
) -> dict[str, Any]:
    seed = list(read_jsonl(seed_manifest))
    inventory = list(read_jsonl(inventory_manifest))
    approvals = list(read_jsonl(approval_manifest))
    deletions = list(read_jsonl(deletion_manifest))
    audit = list(read_jsonl(audit_manifest))

    if not seed:
        raise ValueError(f"No seed records found in {seed_manifest}")
    if not inventory:
        raise ValueError(f"No inventory records found in {inventory_manifest}")
    if not approvals:
        raise ValueError(f"No approval records found in {approval_manifest}")
    if not deletions:
        raise ValueError(f"No deletion records found in {deletion_manifest}")
    if not audit:
        raise ValueError(f"No audit records found in {audit_manifest}")

    chain_checks = _validate_chain(
        seed_manifest,
        inventory_manifest,
        approval_manifest,
        seed,
        inventory,
        approvals,
        deletions,
        audit,
    )

    deletion_counts = Counter(str(record.get("result") or "UNKNOWN") for record in deletions)
    deletion_modes = {str(record.get("mode") or "") for record in deletions}
    refused_or_errors = sum(deletion_counts[result] for result in EXECUTION_FAILURE_RESULTS)
    destroyed = deletion_counts["DESTROYED"]
    already_absent = deletion_counts["ALREADY_ABSENT"]

    verification_pass = (
        deletion_modes == {"EXECUTE"}
        and refused_or_errors == 0
        and destroyed + already_absent == len(approvals)
    )

    audit_status_counts: Counter[str] = Counter()
    unexpected_new = 0
    for root in audit:
        for instance in root.get("instances", []):
            audit_status_counts[str(instance.get("status") or "UNKNOWN")] += 1
        unexpected_new += len(root.get("unexpected_new_instances", []))

    expected_absent = (
        audit_status_counts["VERIFIED_ABSENT"]
        + audit_status_counts["EXPECTED_ABSENT_BUT_PRESENT"]
    )
    verified_absent = audit_status_counts["VERIFIED_ABSENT"]
    expected_present = (
        audit_status_counts["VERIFIED_PRESENT"]
        + audit_status_counts["UNEXPECTED_MISSING"]
    )
    verified_present = audit_status_counts["VERIFIED_PRESENT"]
    unexpected_missing = audit_status_counts["UNEXPECTED_MISSING"]
    expected_absent_but_present = audit_status_counts["EXPECTED_ABSENT_BUT_PRESENT"]

    validation_pass = (
        all(str(root.get("result") or "") == "PASS" for root in audit)
        and verified_absent == expected_absent
        and verified_present == expected_present
        and unexpected_missing == 0
        and expected_absent_but_present == 0
        and unexpected_new == 0
    )

    discovery_entries = [
        _evidence_entry(path) for path in _derived_discovery_paths(inventory)
    ]

    scan_paths = sorted(
        {
            str(value)
            for record in audit
            for value in record.get("scan_paths", [])
        }
    )
    expect_absent_prefixes = sorted(
        {
            str(value)
            for record in audit
            for value in record.get("expect_absent_prefixes", [])
        }
    )

    pre_remediation_instances = sum(int(root.get("instance_count") or 0) for root in inventory)
    overall = "ACCEPTED" if verification_pass and validation_pass else "REJECTED"

    return {
        "schema_version": "0.1",
        "record_type": "SDIDA_SANITIZATION_ASSURANCE_RECORD",
        "created_at": datetime.now().astimezone().isoformat(),
        "framework": {
            "reference": "NIST SP 800-88 Rev. 2",
            "alignment": "NIST_INFORMED",
            "compliance_claim": False,
        },
        "tool": {
            "name": "SDIDA",
            "version": _package_version(),
            "git_commit": _git_commit(),
        },
        "remediation": {
            "method_claim": None,
            "technique": "SELECTIVE_LOGICAL_FILE_REMOVAL",
            "nist_clear_claimed": False,
            "nist_purge_claimed": False,
            "nist_destroy_claimed": False,
        },
        "scope": {
            "roots": len(inventory),
            "pre_remediation_instances": pre_remediation_instances,
            "approved_for_destruction": len(approvals),
            "expected_preserved": expected_present,
            "scan_paths": scan_paths,
            "expect_absent_prefixes": expect_absent_prefixes,
        },
        "evidence_chain": {
            "seed_manifest": _evidence_entry(seed_manifest),
            "discovery_manifests": discovery_entries,
            "inventory_manifest": _evidence_entry(inventory_manifest),
            "deletion_approval_manifest": _evidence_entry(approval_manifest),
            "deletion_manifest": _evidence_entry(deletion_manifest),
            "audit_manifest": _evidence_entry(audit_manifest),
            "chain_checks": chain_checks,
        },
        "execution": {
            "approved": len(approvals),
            "destroyed": destroyed,
            "already_absent": already_absent,
            "refused_or_errors": refused_or_errors,
            "result_counts": dict(sorted(deletion_counts.items())),
        },
        "verification": {
            "status": "PASS" if verification_pass else "FAIL",
            "basis": (
                "Execution manifest records an EXECUTE operation for every approved target, "
                "with each target either destroyed or already absent and no refusal/error results."
            ),
        },
        "validation": {
            "status": "PASS" if validation_pass else "FAIL",
            "verified_absent": verified_absent,
            "expected_absent": expected_absent,
            "verified_present": verified_present,
            "expected_present": expected_present,
            "unexpected_missing": unexpected_missing,
            "expected_absent_but_present": expected_absent_but_present,
            "unexpected_new": unexpected_new,
        },
        "residual_risk": {
            "physical_sector_recovery_tested": False,
            "provider_backup_destruction_tested": False,
            "unscoped_storage_tested": False,
            "statement": (
                "Validation establishes absence through the recorded scoped discovery interfaces. "
                "It does not assert physical-media Clear, Purge, or Destroy."
            ),
        },
        "result": overall,
    }


def write_assurance_record(
    path: Path,
    record: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Assurance record already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_assurance_record(
    seed_manifest: Path,
    inventory_manifest: Path,
    approval_manifest: Path,
    deletion_manifest: Path,
    audit_manifest: Path,
    output: Path,
    *,
    force: bool = False,
) -> int:
    record = build_assurance_record(
        seed_manifest,
        inventory_manifest,
        approval_manifest,
        deletion_manifest,
        audit_manifest,
    )
    write_assurance_record(output, record, force=force)
    digest = sha256_file(output)

    print(f"Assurance record {record['result']} -> {output}")
    print(f"Record SHA-256: {digest}")
    print(
        "Verification: "
        f"{record['verification']['status']}; "
        "validation: "
        f"{record['validation']['status']}"
    )
    return 0 if record["result"] == "ACCEPTED" else 2
