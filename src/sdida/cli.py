from __future__ import annotations

import argparse
from pathlib import Path

from .assurance import run_assurance_record
from .audit import run_audit
from .delete import run_approve_delete, run_delete
from .discover import run_discover
from .inventory import run_inventory
from .naming import timestamped_manifest_path, timestamped_record_path
from .seed import run_seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdida",
        description="Seed → Discovery → Inventory → Delete → Audit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed", help="Build a seed manifest from known source files")
    seed.add_argument("paths", nargs="+", type=Path)
    seed.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    seed.add_argument("--force", action="store_true")

    discover = subparsers.add_parser(
        "discover",
        help="Find exact SHA-256 matches for a seed corpus on local filesystem paths",
    )
    discover.add_argument("seed_manifest", type=Path)
    discover.add_argument("paths", nargs="+", type=Path)
    discover.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    discover.add_argument("--force", action="store_true")

    inventory = subparsers.add_parser(
        "inventory",
        help="Collapse discovery manifests into one root-centered inventory record per seed",
    )
    inventory.add_argument("seed_manifest", type=Path)
    inventory.add_argument(
        "discovery_manifests",
        nargs="+",
        type=Path,
        help="One or more discovery manifests to inventory",
    )
    inventory.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    inventory.add_argument("--force", action="store_true")

    approve_delete = subparsers.add_parser(
        "approve-delete",
        help="Create an explicit deletion approval manifest from a frozen inventory",
    )
    approve_delete.add_argument("inventory_manifest", type=Path)
    approve_delete.add_argument(
        "--under",
        action="append",
        required=True,
        type=Path,
        help=(
            "Approve inventoried filesystem descendants beneath this exact path prefix. "
            "May be repeated. Canonical seed locations are excluded."
        ),
    )
    approve_delete.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL approval manifest. Defaults to a timestamped file in manifests/.",
    )
    approve_delete.add_argument("--force", action="store_true")

    delete = subparsers.add_parser(
        "delete",
        help="Validate and delete only files named in an explicit approval manifest",
    )
    delete.add_argument("approval_manifest", type=Path)
    delete.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete approved files. Without this flag, Delete is a dry run.",
    )
    delete.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL deletion result manifest. Defaults to a timestamped file in manifests/.",
    )
    delete.add_argument("--force", action="store_true")

    audit = subparsers.add_parser(
        "audit",
        help="Rerun exact discovery and compare current reality to a frozen inventory",
    )
    audit.add_argument("seed_manifest", type=Path)
    audit.add_argument("inventory_manifest", type=Path)
    audit.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Filesystem paths to rescan using the same exact-discovery method",
    )
    audit.add_argument(
        "--expect-absent",
        action="append",
        default=[],
        type=Path,
        help=(
            "Path prefix expected to have been removed. May be repeated. "
            "Inventoried instances elsewhere are expected to remain present."
        ),
    )
    audit.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    audit.add_argument("--force", action="store_true")

    record = subparsers.add_parser(
        "record",
        help="Produce a final sanitization assurance record from a completed evidence chain",
    )
    record.add_argument("--seed", required=True, type=Path, help="Seed manifest")
    record.add_argument("--inventory", required=True, type=Path, help="Frozen pre-remediation inventory")
    record.add_argument("--approval", required=True, type=Path, help="Deletion approval manifest")
    record.add_argument("--deletion", required=True, type=Path, help="Executed deletion result manifest")
    record.add_argument("--audit", required=True, type=Path, help="Post-remediation audit manifest")
    record.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON assurance record. Defaults to a timestamped file in manifests/.",
    )
    record.add_argument("--force", action="store_true")

    google = subparsers.add_parser(
        "discover-google",
        help="Find exact seed matches in Gmail attachments and Google Drive",
    )
    google.add_argument("seed_manifest", type=Path)
    google.add_argument("--account", required=True, help="Google account to verify after OAuth")
    google.add_argument(
        "--credentials",
        required=True,
        type=Path,
        help="Google OAuth desktop client credentials JSON",
    )
    google.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSONL manifest. Defaults to a timestamped file in manifests/.",
    )
    google.add_argument("--force", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "seed":
        output = args.output or timestamped_manifest_path("seed")
        return run_seed(args.paths, output, force=args.force)

    if args.command == "discover":
        output = args.output or timestamped_manifest_path("discovery")
        return run_discover(args.seed_manifest, args.paths, output, force=args.force)

    if args.command == "inventory":
        output = args.output or timestamped_manifest_path("inventory")
        return run_inventory(
            args.seed_manifest,
            args.discovery_manifests,
            output,
            force=args.force,
        )

    if args.command == "approve-delete":
        output = args.output or timestamped_manifest_path("deletion_approval")
        return run_approve_delete(args.inventory_manifest, args.under, output, force=args.force)

    if args.command == "delete":
        output = args.output or timestamped_manifest_path("deletion")
        return run_delete(args.approval_manifest, output, execute=args.execute, force=args.force)

    if args.command == "audit":
        output = args.output or timestamped_manifest_path("audit")
        return run_audit(
            args.seed_manifest,
            args.inventory_manifest,
            args.paths,
            output,
            expect_absent_prefixes=args.expect_absent,
            force=args.force,
        )

    if args.command == "record":
        output = args.output or timestamped_record_path("assurance")
        return run_assurance_record(
            args.seed,
            args.inventory,
            args.approval,
            args.deletion,
            args.audit,
            output,
            force=args.force,
        )

    if args.command == "discover-google":
        try:
            from .google_discover import run_google_discover
        except ModuleNotFoundError as exc:
            if exc.name and (
                exc.name.startswith("google") or exc.name.startswith("googleapiclient")
            ):
                raise SystemExit(
                    'Google API support is optional. Install it with: pip install -e ".[google]"'
                ) from exc
            raise

        output = args.output or timestamped_manifest_path("google_discovery")
        return run_google_discover(
            args.seed_manifest,
            args.account,
            args.credentials,
            output,
            force=args.force,
        )

    raise RuntimeError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
