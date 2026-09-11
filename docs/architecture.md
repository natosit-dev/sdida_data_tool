# Architecture

## Purpose

SDIDA separates discovery, decision, remediation, and verification into distinct evidence-producing phases. The design is intentionally conservative: a destructive phase may act only on artifacts already identified and explicitly approved by earlier non-destructive phases.

The pipeline is:

```text
Seed → Discovery → Inventory → Approval → Delete → Audit → Assurance Record
```

## Governing invariants

### Discovery and deletion are separate responsibilities

**Delete never discovers. Discovery never deletes.**

Discovery is read-only and produces observations. Delete consumes an explicit approval manifest derived from a frozen inventory. The deletion phase does not broaden scope, search for additional files, or infer new targets.

### Approval is frozen before execution

Deletion approval contains the exact location and SHA-256 observed before remediation. Immediately before deleting a filesystem target, SDIDA hashes the current bytes again. If the current digest differs from the approved digest, deletion is refused.

### Canonical seed locations are preserved

In v0.1, approval generation excludes inventory instances classified as `SEED_LOCATION`. This prevents the known source corpus from being selected as a descendant-remediation target through the standard approval workflow.

### Verification uses the same matching method

Audit reruns exact SHA-256 discovery across explicitly supplied surfaces and compares current observations with the frozen pre-remediation inventory. Expected-absent and expected-present instances are evaluated independently, and new exact matches are reported as unexpected.

## Artifact model

The core `ArtifactRecord` is content-neutral. It records identifiers and provenance such as:

- artifact and root identifiers
- source type
- location and filename
- SHA-256 and optional text fingerprint
- parent/root relationship
- match method and score
- classification and lifecycle state
- timestamp and notes

The exact-discovery pipeline treats file content as opaque bytes. Domain semantics are not required for matching.

## Phase responsibilities

### Seed

Seed expands explicitly supplied files/directories into a stable list and fingerprints each file with SHA-256. Each seed artifact receives a stable root identifier within the generated manifest.

### Discovery

Discovery searches only the surfaces supplied to it. Local filesystem discovery hashes candidate files and emits records only for exact seed matches. Provider adapters may implement equivalent read-only discovery against other storage systems.

### Inventory

Inventory joins one or more discovery manifests back to the seed corpus. Repeated observations of the same materialized instance are deduplicated while retaining the manifests in which the instance was observed.

### Approval

Approval selects only already-inventoried filesystem descendants beneath explicit path prefixes. It cannot discover new targets and does not mutate storage.

### Delete

Delete validates each approval independently. Unsupported source types, incomplete approvals, stale hashes, non-files, and other unsafe conditions are refused. Dry-run is the default behavior.

### Audit

Audit reruns exact discovery and compares observed reality with the frozen inventory. It distinguishes:

- verified absent
- expected absent but present
- verified present
- unexpected missing
- unexpected new exact matches

### Assurance record

The assurance record binds the seed, discovery, inventory, approval, execution, and audit evidence through file hashes and path references. It reports whether the recorded execution and validation chain is internally consistent.

## Storage adapters

Storage specificity and content specificity are separate concerns. SDIDA can remain content-agnostic while supporting provider-specific discovery adapters.

Current optional Google support:

- Gmail attachments
- non-Google-native Google Drive files

Both adapters use read-only API scopes and hash bytes in memory rather than materializing discovered content into the repository.

## Trust boundaries

SDIDA verifies what can be established through the interfaces and scopes it is given. It does not imply visibility into unscoped storage, provider backups, deleted-block recovery, physical media sectors, or other systems outside the recorded discovery surfaces.

Accordingly, selective filesystem removal plus a passing SDIDA audit is evidence of absence from the recorded scoped interfaces. It is not evidence of physical-media sanitization.
