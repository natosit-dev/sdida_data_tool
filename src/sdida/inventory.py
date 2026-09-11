from __future__ import annotations

from collections import Counter, defaultdict
import os
from pathlib import Path
from typing import Any

from .manifest import read_jsonl, write_jsonl


def _path_identity(value: str | None) -> str | None:
    if not value:
        return None
    return os.path.normcase(os.path.normpath(value))


def load_seed_records(seed_manifest: Path) -> dict[str, dict[str, Any]]:
    """Load seed records keyed by stable seed artifact ID."""
    seeds: dict[str, dict[str, Any]] = {}

    for record in read_jsonl(seed_manifest):
        artifact_id = record.get("artifact_id")
        if not artifact_id:
            raise ValueError(f"Seed record in {seed_manifest} is missing artifact_id")
        seeds[str(artifact_id)] = record

    if not seeds:
        raise ValueError(f"No seed records found in {seed_manifest}")

    return seeds


def build_inventory(
    seed_manifest: Path,
    discovery_manifests: list[Path],
) -> list[dict[str, Any]]:
    """Collapse discovery observations into one root-centered record per seed.

    Multiple discovery manifests may be supplied. The same physical/materialized
    instance observed in more than one run is deduplicated by source type,
    location, and SHA-256 while retaining the list of manifests that observed it.
    """
    if not discovery_manifests:
        raise ValueError("At least one discovery manifest is required")

    seeds = load_seed_records(seed_manifest)

    grouped: dict[
        str,
        dict[tuple[str, str, str], dict[str, Any]],
    ] = defaultdict(dict)

    for manifest in discovery_manifests:
        if not manifest.exists():
            raise FileNotFoundError(f"Discovery manifest does not exist: {manifest}")

        for record in read_jsonl(manifest):
            root_id = record.get("root_id")
            artifact_id = record.get("artifact_id")

            if not root_id:
                raise ValueError(
                    f"Discovery record {artifact_id!r} in {manifest} is missing root_id"
                )
            root_id = str(root_id)
            if root_id not in seeds:
                raise ValueError(
                    f"Discovery record {artifact_id!r} in {manifest} references "
                    f"unknown root_id {root_id!r}"
                )

            source_type = str(record.get("source_type") or "")
            location = str(record.get("location") or "")
            sha256 = str(record.get("sha256") or "")
            key = (source_type, location, sha256)

            existing = grouped[root_id].get(key)
            if existing is None:
                grouped[root_id][key] = {
                    "record": record,
                    "observed_in": {str(manifest)},
                }
            else:
                existing["observed_in"].add(str(manifest))

    inventory: list[dict[str, Any]] = []

    for root_id in sorted(seeds):
        seed = seeds[root_id]
        seed_location_identity = _path_identity(str(seed.get("location") or ""))

        instances: list[dict[str, Any]] = []
        for item in grouped.get(root_id, {}).values():
            record = item["record"]
            location = str(record.get("location") or "")
            relation = (
                "SEED_LOCATION"
                if seed_location_identity
                and _path_identity(location) == seed_location_identity
                else "DESCENDANT"
            )

            instances.append(
                {
                    "artifact_id": record.get("artifact_id"),
                    "source_type": record.get("source_type"),
                    "location": record.get("location"),
                    "filename": record.get("filename"),
                    "sha256": record.get("sha256"),
                    "match_method": record.get("match_method"),
                    "match_score": record.get("match_score"),
                    "classification": record.get("classification"),
                    "discovered_at": record.get("discovered_at"),
                    "relation": relation,
                    "observed_in": sorted(item["observed_in"]),
                }
            )

        instances.sort(key=lambda item: str(item.get("location") or ""))
        seed_location_present = any(
            item["relation"] == "SEED_LOCATION" for item in instances
        )

        inventory.append(
            {
                "root_id": root_id,
                "seed_filename": seed.get("filename"),
                "seed_location": seed.get("location"),
                "seed_sha256": seed.get("sha256"),
                "instance_count": len(instances),
                "descendant_count": sum(
                    item["relation"] == "DESCENDANT" for item in instances
                ),
                "seed_location_present": seed_location_present,
                "instances": instances,
            }
        )

    return inventory


def _format_distribution(records: list[dict[str, Any]]) -> str:
    counts = Counter(int(record["instance_count"]) for record in records)
    parts = []
    for instance_count in sorted(counts):
        root_count = counts[instance_count]
        root_word = "root" if root_count == 1 else "roots"
        instance_word = "instance" if instance_count == 1 else "instances"
        parts.append(
            f"{root_count} {root_word} x {instance_count} {instance_word}"
        )
    return "; ".join(parts)


def run_inventory(
    seed_manifest: Path,
    discovery_manifests: list[Path],
    output: Path,
    *,
    force: bool = False,
) -> int:
    records = build_inventory(seed_manifest, discovery_manifests)
    write_jsonl(output, records, force=force)

    total_instances = sum(int(record["instance_count"]) for record in records)
    print(
        f"Inventoried {total_instances} exact instances across "
        f"{len(records)} roots -> {output}"
    )
    print(f"Instance-count distribution: {_format_distribution(records)}")
    return 0
