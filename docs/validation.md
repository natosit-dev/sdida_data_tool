# Validation

SDIDA's public validation fixture is synthetic and generated at test time. It contains no user, customer, employer, project, or production data.

## Known-answer topology

The test creates three seed artifacts:

```text
source/
  alpha.txt
  beta.json
  gamma.bin
```

It then materializes exact copies on two additional surfaces:

```text
surface_a/
  alpha.txt
  alpha-copy.txt
  beta.json
  gamma.bin

surface_b/
  alpha.txt
  beta.json
  gamma.bin
```

Expected pre-remediation topology:

- 3 seed roots
- 10 exact materializations total
- one root with 4 instances
- two roots with 3 instances each

## End-to-end assertions

The automated test performs the complete local-filesystem workflow:

```text
Seed
→ Discover = 10 exact matches
→ Inventory = 3 roots / 10 instances
→ Approve surface_a = 4 targets
→ Dry run = 4 WOULD_DELETE
→ Execute = 4 DESTROYED
→ Audit
   4/4 expected-absent instances verified absent
   6/6 expected-present instances verified present
   0 unexpected missing
   0 unexpected new
→ Assurance Record = ACCEPTED
```

The destructive phase is confined to pytest's temporary directory. No test path is accepted from the host environment.

## Run

```bash
pip install -e ".[test]"
pytest
```

The test is intentionally small enough to inspect manually while still exercising the evidence chain, approval boundary, dry-run behavior, execution-time rehashing path, post-remediation audit, and final assurance record.
