# NIST SP 800-88 Rev. 2 Crosswalk

## Scope of this document

SDIDA can produce evidence about selective logical removal from explicitly scoped interfaces. It does not, by itself, establish physical-media sanitization.

This document records that boundary so a passing SDIDA workflow is not accidentally overstated as a Clear, Purge, or Destroy claim.

## SDIDA evidence model

SDIDA's local filesystem workflow can establish a chain such as:

1. known source artifacts were fingerprinted;
2. exact materializations were observed on recorded storage paths;
3. a frozen pre-remediation inventory was created;
4. a subset of inventoried descendants was explicitly approved;
5. approved files were rehashed immediately before logical removal;
6. discovery was rerun after remediation;
7. expected-absent instances were not observed through the same scoped interface;
8. expected-preserved instances remained observable;
9. the evidence files were bound into an assurance record.

That is useful provenance and verification evidence. It is deliberately narrower than a media-sanitization claim.

## Boundary against media sanitization terminology

SDIDA v0.1 reports its filesystem-removal technique as:

```text
SELECTIVE_LOGICAL_FILE_REMOVAL
```

The assurance record explicitly sets:

```text
nist_clear_claimed: false
nist_purge_claimed: false
nist_destroy_claimed: false
```

Ordinary file deletion can remove a file from the filesystem namespace without demonstrating that the underlying storage locations are resistant to recovery. SDIDA therefore does not promote a successful logical-removal audit into a physical-media sanitization assertion.

## What a passing audit means

A passing audit means that, through the recorded discovery method and within the recorded scan scope:

- instances expected to be absent were not rediscovered;
- instances expected to remain were rediscovered;
- no inventoried expected-present instances unexpectedly disappeared; and
- no new exact seed matches appeared.

It does **not** establish that:

- deleted sectors cannot be recovered;
- remapped or overprovisioned blocks were sanitized;
- snapshots or backups outside the scan scope were destroyed;
- a cloud provider eliminated all retained copies;
- an underlying device satisfied a Clear, Purge, or Destroy procedure.

## Operational use

SDIDA evidence may be one component of a broader sanitization process. A media-level sanitization claim requires controls and evidence appropriate to the storage technology and sanitization method in use.

The SDIDA assurance record therefore uses the framing `NIST_INFORMED` with `compliance_claim: false` unless a separate process establishes a stronger claim outside SDIDA's selective logical-removal workflow.

## Public validation fixture

The repository's automated synthetic test validates the SDIDA evidence mechanics rather than any particular real-world corpus. See [`validation.md`](validation.md).
