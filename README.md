# SDIDA

**Seed → Discovery → Inventory → Delete → Audit**

SDIDA is a deterministic data provenance, selective remediation, and verification toolkit. It starts from a known seed corpus, discovers exact materializations across explicitly scoped storage surfaces, freezes an inventory, requires explicit deletion approval, revalidates content immediately before removal, and reruns discovery to verify the expected result.

> **Governing invariant:** Delete never discovers. Discovery never deletes.

## What it does

1. **Seed** known source files and record SHA-256 fingerprints.
2. **Discover** exact byte-for-byte matches across scoped surfaces.
3. **Inventory** those observations into one root-centered lineage record per seed artifact.
4. **Approve** only already-inventoried descendants beneath explicitly selected path prefixes.
5. **Delete** approved filesystem targets. Dry-run is the default; execution requires `--execute` and rehashes every target immediately before deletion.
6. **Audit** by rerunning the same exact-discovery method against the frozen inventory.
7. **Record** a final assurance record binding the evidence chain and verification result.

The current implementation treats content as opaque bytes for exact matching. Storage adapters define where SDIDA looks; they do not encode domain-specific meaning.

## Safety model

- Seed, discovery, inventory, and audit are read-only operations.
- Approval is generated from a frozen inventory; the deletion phase does not perform discovery.
- Canonical seed locations are excluded from deletion approval in v0.1.
- Delete is a dry run unless `--execute` is explicitly supplied.
- A target whose current SHA-256 differs from the approved SHA-256 is refused rather than deleted.
- Google support uses read-only Gmail and Drive scopes and is optional.
- Runtime manifests may contain sensitive paths and evidence metadata. They are ignored by Git by default.

SDIDA performs selective logical file removal. It does **not** claim that ordinary filesystem deletion constitutes NIST Clear, Purge, or Destroy of the underlying physical media.

## Installation

```bash
python -m venv .venv
# Activate the environment for your shell, then:
pip install -e .
```

Optional Google discovery support:

```bash
pip install -e ".[google]"
```

Development/test dependencies:

```bash
pip install -e ".[test]"
pytest
```

## Local filesystem workflow

```bash
sdida seed ./known-source -o manifests/seed.jsonl

sdida discover manifests/seed.jsonl ./surface-a ./surface-b \
  -o manifests/discovery.jsonl

sdida inventory manifests/seed.jsonl manifests/discovery.jsonl \
  -o manifests/inventory.jsonl

sdida approve-delete manifests/inventory.jsonl \
  --under ./surface-a \
  -o manifests/deletion_approval.jsonl

# Dry run by default
sdida delete manifests/deletion_approval.jsonl \
  -o manifests/deletion_dry_run.jsonl

# Explicit execution
sdida delete manifests/deletion_approval.jsonl --execute \
  -o manifests/deletion.jsonl

sdida audit manifests/seed.jsonl manifests/inventory.jsonl \
  ./known-source ./surface-a ./surface-b \
  --expect-absent ./surface-a \
  -o manifests/audit.jsonl

sdida record \
  --seed manifests/seed.jsonl \
  --inventory manifests/inventory.jsonl \
  --approval manifests/deletion_approval.jsonl \
  --deletion manifests/deletion.jsonl \
  --audit manifests/audit.jsonl \
  -o manifests/assurance.json
```

## Google discovery

With the optional dependencies installed, SDIDA can hash Gmail attachments and non-Google-native Drive files in memory and compare them with the same seed index:

```bash
sdida discover-google manifests/seed.jsonl \
  --account account@example.com \
  --credentials ./client_secret.json \
  -o manifests/google_discovery.jsonl
```

OAuth tokens are stored outside the repository under `~/.sdida/google/` by default.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — pipeline, invariants, trust boundaries, and data model.
- [`docs/validation.md`](docs/validation.md) — reproducible synthetic known-answer test.
- [`docs/nist-sp-800-88r2-crosswalk.md`](docs/nist-sp-800-88r2-crosswalk.md) — boundary between SDIDA verification and media-sanitization claims.

## License

GNU General Public License v3.0. See [`LICENSE`](LICENSE).
