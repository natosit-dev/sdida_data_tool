from __future__ import annotations

from collections import Counter
from pathlib import Path

from sdida.assurance import build_assurance_record, write_assurance_record
from sdida.audit import run_audit
from sdida.delete import run_approve_delete, run_delete
from sdida.discover import run_discover
from sdida.inventory import run_inventory
from sdida.manifest import read_jsonl
from sdida.seed import run_seed


def _write_fixture(root: Path) -> tuple[Path, Path, Path]:
    source = root / "source"
    surface_a = root / "surface_a"
    surface_b = root / "surface_b"
    for path in (source, surface_a, surface_b):
        path.mkdir()

    payloads = {
        "alpha.txt": b"alpha\n",
        "beta.json": b'{"beta": 2}\n',
        "gamma.bin": bytes(range(32)),
    }

    for name, payload in payloads.items():
        (source / name).write_bytes(payload)
        (surface_a / name).write_bytes(payload)
        (surface_b / name).write_bytes(payload)

    (surface_a / "alpha-copy.txt").write_bytes(payloads["alpha.txt"])
    return source, surface_a, surface_b


def test_synthetic_end_to_end(tmp_path: Path) -> None:
    source, surface_a, surface_b = _write_fixture(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    seed = evidence / "seed.jsonl"
    discovery = evidence / "discovery.jsonl"
    inventory = evidence / "inventory.jsonl"
    approval = evidence / "approval.jsonl"
    dry_run = evidence / "deletion_dry_run.jsonl"
    deletion = evidence / "deletion.jsonl"
    audit = evidence / "audit.jsonl"
    assurance = evidence / "assurance.json"

    assert run_seed([source], seed) == 0
    assert run_discover(seed, [source, surface_a, surface_b], discovery) == 0

    discovered = list(read_jsonl(discovery))
    assert len(discovered) == 10

    assert run_inventory(seed, [discovery], inventory) == 0
    inventory_records = list(read_jsonl(inventory))
    assert len(inventory_records) == 3
    assert sum(record["instance_count"] for record in inventory_records) == 10
    assert sorted(record["instance_count"] for record in inventory_records) == [3, 3, 4]

    assert run_approve_delete(inventory, [surface_a], approval) == 0
    approvals = list(read_jsonl(approval))
    assert len(approvals) == 4
    assert all(Path(record["location"]).is_relative_to(surface_a) for record in approvals)

    assert run_delete(approval, dry_run, execute=False) == 0
    dry_run_records = list(read_jsonl(dry_run))
    assert Counter(record["result"] for record in dry_run_records) == {"WOULD_DELETE": 4}
    assert len(list(surface_a.iterdir())) == 4

    assert run_delete(approval, deletion, execute=True) == 0
    deletion_records = list(read_jsonl(deletion))
    assert Counter(record["result"] for record in deletion_records) == {"DESTROYED": 4}
    assert list(surface_a.iterdir()) == []

    assert run_audit(
        seed,
        inventory,
        [source, surface_a, surface_b],
        audit,
        expect_absent_prefixes=[surface_a],
    ) == 0

    audit_records = list(read_jsonl(audit))
    statuses = Counter(
        instance["status"]
        for root in audit_records
        for instance in root["instances"]
    )
    assert statuses == {"VERIFIED_ABSENT": 4, "VERIFIED_PRESENT": 6}
    assert all(root["result"] == "PASS" for root in audit_records)
    assert all(not root["unexpected_new_instances"] for root in audit_records)

    record = build_assurance_record(seed, inventory, approval, deletion, audit)
    assert record["result"] == "ACCEPTED"
    assert record["execution"]["destroyed"] == 4
    assert record["validation"]["verified_absent"] == 4
    assert record["validation"]["verified_present"] == 6
    assert record["validation"]["unexpected_missing"] == 0
    assert record["validation"]["unexpected_new"] == 0

    write_assurance_record(assurance, record)
    assert assurance.exists()

    # Canonical seed corpus and the unapproved surface remain intact.
    assert len(list(source.iterdir())) == 3
    assert len(list(surface_b.iterdir())) == 3
