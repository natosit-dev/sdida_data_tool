from __future__ import annotations

import argparse
from pathlib import Path

from .fingerprint import normalize_filename, sha256_file
from .manifest import write_jsonl
from .models import ArtifactRecord, ArtifactState
from .naming import timestamped_manifest_path


def iter_seed_files(paths: list[Path]) -> list[Path]:
    """Expand files/directories into a stable, deduplicated file list."""
    resolved: dict[str, Path] = {}

    for root in paths:
        if not root.exists():
            raise FileNotFoundError(f"Seed path does not exist: {root}")

        candidates = [root] if root.is_file() else root.rglob("*")
        for candidate in candidates:
            if not candidate.is_file():
                continue
            absolute = candidate.resolve()
            resolved[str(absolute)] = absolute

    return [resolved[key] for key in sorted(resolved)]


def build_seed_records(paths: list[Path]) -> list[ArtifactRecord]:
    """Create the canonical seed corpus from known source files."""
    records: list[ArtifactRecord] = []

    for index, path in enumerate(iter_seed_files(paths), start=1):
        artifact_id = f"S-{index:06d}"
        try:
            digest = sha256_file(path)
        except OSError as exc:
            records.append(
                ArtifactRecord(
                    artifact_id=artifact_id,
                    root_id=artifact_id,
                    source_type="seed_filesystem",
                    location=str(path),
                    filename=path.name,
                    classification="SEED_ERROR",
                    state=ArtifactState.ERROR,
                    notes=f"Could not fingerprint seed: {exc}",
                )
            )
            continue

        records.append(
            ArtifactRecord(
                artifact_id=artifact_id,
                root_id=artifact_id,
                source_type="seed_filesystem",
                location=str(path),
                filename=path.name,
                sha256=digest,
                text_fingerprint=None,
                match_method="seed_sha256",
                match_score=1.0,
                classification="SEED",
                state=ArtifactState.PRESERVED,
                notes=f"normalized_filename={normalize_filename(path.name)}",
            )
        )

    return records


def run_seed(paths: list[Path], output: Path, *, force: bool = False) -> int:
    records = build_seed_records(paths)
    write_jsonl(output, records, force=force)

    ok = sum(record.state != ArtifactState.ERROR for record in records)
    errors = len(records) - ok
    print(f"Seeded {ok} files -> {output}")
    if errors:
        print(f"WARNING: {errors} seed files could not be fingerprinted; see manifest")
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdida-seed",
        description="Create a canonical SDIDA seed manifest from known source files.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Seed file(s) or directorie(s)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an explicitly named existing seed manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or timestamped_manifest_path("seed")
    return run_seed(args.paths, output, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
