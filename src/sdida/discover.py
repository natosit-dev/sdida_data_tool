from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .discovery.filesystem import scan_paths
from .manifest import read_jsonl, write_jsonl
from .models import ArtifactRecord
from .naming import timestamped_manifest_path


def load_seed_index(seed_manifest: Path) -> dict[str, list[str]]:
    """Map each seed SHA-256 to one or more seed artifact IDs."""
    index: dict[str, list[str]] = defaultdict(list)

    for record in read_jsonl(seed_manifest):
        digest = record.get("sha256")
        artifact_id = record.get("artifact_id")
        if not digest or not artifact_id:
            continue
        index[str(digest)].append(str(artifact_id))

    if not index:
        raise ValueError(f"No usable seed hashes found in {seed_manifest}")

    return dict(index)


def discover_exact(
    seed_manifest: Path,
    paths: list[Path],
) -> list[ArtifactRecord]:
    """Discover exact SHA-256 descendants on the local filesystem.

    Read-only: this function never moves, quarantines, modifies, or deletes files.
    """
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Discovery path does not exist: {path}")

    seed_index = load_seed_index(seed_manifest)
    matches = scan_paths(paths, set(seed_index))

    unique: dict[tuple[str, str | None], ArtifactRecord] = {}
    for record in matches:
        roots = seed_index.get(record.sha256 or "", [])
        record.root_id = roots[0] if roots else None
        record.classification = "EXACT_COPY"
        record.match_score = 1.0
        if len(roots) > 1:
            record.notes = "same content matches multiple seed roots: " + ",".join(roots)

        unique[(record.location, record.sha256)] = record

    return sorted(unique.values(), key=lambda record: record.location)


def run_discover(
    seed_manifest: Path,
    paths: list[Path],
    output: Path,
    *,
    force: bool = False,
) -> int:
    records = discover_exact(seed_manifest, paths)
    write_jsonl(output, records, force=force)
    print(f"Discovered {len(records)} exact matches -> {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdida-discover",
        description="Search local filesystem paths for exact descendants of a seed corpus.",
    )
    parser.add_argument(
        "seed_manifest",
        type=Path,
        help="Seed manifest produced by sdida seed",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="File(s) or directorie(s) to scan")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL discovery manifest. Defaults to a timestamped file in manifests/.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an explicitly named existing discovery manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or timestamped_manifest_path("discovery")
    return run_discover(
        args.seed_manifest,
        args.paths,
        output,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
