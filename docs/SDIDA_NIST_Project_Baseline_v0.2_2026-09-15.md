# SDIDA / NIST Project Baseline

**Existing functionality, components, and related NIST sections**

**Version:** 0.2  
**Date:** 2026-09-15  
**Status:** Working project baseline  
**Scope:** Current SDIDA implementation only  
**Primary implementation source:** `natosit-dev/sdida_data_tool` (`main`)  
**Primary NIST sources:** NIST SP 800-53 Rev. 5; NIST SP 800-88 Rev. 2; NIST SP 800-53A Rev. 5  
**Compliance posture:** Descriptive relationship mapping; no compliance assertion

> **Baseline question:** What does SDIDA already do, and where does NIST discuss the same or adjacent functions?

This document intentionally stops before HIPAA mapping, retention-policy design, legal-hold logic, records schedules, or any claim of NIST/HIPAA compliance.

## Prompt provenance

The baseline was narrowed through direct project prompts. These are preserved to keep the scope decision auditable.

> **P-001** — “What I'd like to do now is create a NIST crosswalk to SDIDA. This has evolved into a rough draft for HIPAA compliant data retention and destruction. Go look which 800 series are relevant”

> **P-002** — “Ok I feel like you got ahead of me. First we want the baseline- what functionality and components exist in SDIDA, and what NIST sections are related. Very high level but be thorough”

> **P-003** — “Let's put that in a project baseline doc and print it, full trim, prompts, and decision log”

## Document history

| Version | Date | Status | Change |
|---|---|---|---|
| 0.1 | 2026-09-15 | Baseline | Initial descriptive mapping of existing SDIDA functionality to related NIST controls and sections. |
| 0.2 | 2026-09-15 | Expanded baseline | Added recovered creation-prompt lineage and provenance; baseline NIST mapping unchanged. |

## 1. Purpose and scope

This baseline inventories the functionality and components that exist in SDIDA today and associates them with NIST controls or publication sections that address the same or adjacent concern. The mapping is intentionally descriptive. It does not state that SDIDA implements a NIST control in full, satisfies an organizational control objective, or establishes HIPAA compliance.

Relationship labels used in this document:

- **Direct** — the current SDIDA mechanism closely resembles the function NIST describes.
- **Related** — NIST addresses the same concern, but SDIDA implements only part of that concern or uses the mechanism for a narrower purpose.
- **Boundary** — NIST describes an outcome or scope that SDIDA explicitly does not claim to establish.

## 2. Current SDIDA architecture

```text
Seed → Discovery → Inventory → Approval → Delete → Audit → Assurance Record
```

The architecture separates observation, decision, destructive action, and verification.

> **Governing invariant:** Delete never discovers. Discovery never deletes.

## 3. Baseline function-to-NIST crosswalk

This matrix maps what exists now. It is not a future-state design and intentionally does not introduce retention schedules, HIPAA rule mappings, organizational roles, or new remediation methods.

| SDIDA component | What exists now | Related NIST material | Relationship | Baseline interpretation |
|---|---|---|---|---|
| **Seed corpus** | Expands explicitly supplied files/directories, assigns stable root identifiers, and fingerprints each file with SHA-256. | SP 800-53 CM-12; CM-12(1); SI-7 | Related | Provides the known reference corpus used to identify exact materializations and later verify integrity. |
| **Exact fingerprinting / matching** | Uses SHA-256 exact-byte comparison; content is treated as opaque bytes rather than interpreted semantically. | SP 800-53 SI-7; CM-12 | Related | Integrity mechanisms and information-location controls address adjacent concerns; SDIDA uses hashing primarily for identity and change detection. |
| **Scoped discovery** | Read-only search of explicitly supplied surfaces for exact seed matches. Current adapters include local filesystem, Gmail attachments, and non-Google-native Drive files. | SP 800-53 CM-12; CM-12(1) | Direct | CM-12 addresses identifying and documenting where defined information is processed/stored; CM-12(1) explicitly addresses automated location tools. |
| **Provider / storage adapters** | Separates storage-specific discovery from content-specific logic; Google adapters use read-only scopes and hash bytes in memory. | SP 800-53 CM-12; AC-6 | Related | Supports information location while constraining access. SDIDA is not an access-control system. |
| **Root-centered inventory** | Joins seed and discovery evidence, deduplicates repeated observations, and retains where each materialized instance was observed. | SP 800-53 CM-12; CM-13; SI-12 | Direct / Related | Strong fit to information location; related to lifecycle/data-action mapping without implementing a complete processing map. |
| **Artifact / provenance model** | Records artifact/root identifiers, source type, location, filename, hashes, relationships, classification/state, timestamps, and notes. | SP 800-53 CM-12; CM-13; AU-3; AU-8 | Related | Produces provenance and accountability evidence; not a complete organizational audit-log implementation. |
| **Frozen pre-remediation inventory** | Freezes observed state before destructive action. Delete does not search for additional targets. | SP 800-53 MP-6(1); SP 800-88r2 §4.3.6 | Direct | Mirrors the review/decision/document-before-action structure of sanitization and disposal processes. |
| **Approval manifest** | Selects only previously inventoried descendants beneath explicit prefixes; seed locations are excluded; approval itself is non-destructive. | SP 800-53 MP-6(1); SP 800-88r2 §4.3.6 | Direct | Closely matches NIST's review, approve, track, document, and verify framing. |
| **Discovery / deletion separation** | Read-only discovery and destructive execution are separate responsibilities. | SP 800-53 AC-5; AC-6; MP-6(1) | Related | Structural analogue to separation of duties and least privilege; SDIDA does not by itself establish organizational role separation. |
| **Dry-run execution** | Destructive execution is not the default; approved targets can first be evaluated without removal. | SP 800-53 MP-6(1); SP 800-88r2 §4.3–4.4 | Related | Supports controlled review before action. |
| **Pre-delete identity check** | Immediately rehashes the approved target; refuses deletion if current bytes no longer match the approved digest. | SP 800-53 SI-7; MP-6(1) | Related | Prevents stale authorization from applying to changed content and preserves decision-to-action integrity. |
| **Selective logical deletion** | Removes only approved filesystem objects; unsupported sources, stale hashes, non-files, and incomplete approvals are refused. | SP 800-53 SI-12(3); MP-6; SP 800-88r2 §4.4 | Related / Boundary | Information disposal is directly relevant; ordinary filesystem deletion must not be promoted into a media-sanitization claim. |
| **Post-remediation audit** | Reruns exact discovery and classifies verified absent, expected absent but present, verified present, unexpected missing, and unexpected new matches. | SP 800-53 MP-6(1); SP 800-88r2 §4.5, §4.5.1, §4.5.2; SP 800-53A Rev. 5 | Direct | Strong fit to the verification/validation structure while remaining narrower than media-level sanitization assurance. |
| **Assurance record** | Binds seed, discovery, inventory, approval, execution, and audit evidence using file hashes and path references and checks evidence-chain consistency. | SP 800-53 MP-6(1); SP 800-88r2 §4.6 and Appendix C; AU-3; AU-9; AU-10 | Related | Structurally similar to an electronic evidence/certificate record while explicitly avoiding Clear/Purge/Destroy claims. |
| **Evidence integrity** | Hashes evidence artifacts into the assurance record; frozen manifests resist accidental mutation or overwrite. | SP 800-53 AU-9; AU-10 | Related | Provides tamper-evidence and provenance but not a full protected audit repository or cryptographic signature system. |
| **Evidence retention** | Generates durable evidence files but does not currently decide how long those records must be retained. | SP 800-53 AU-11; SI-12 | Related / Gap | NIST addresses retention of audit/control evidence; SDIDA currently produces records without a retention-policy engine. |
| **Lifecycle states** | Represents states such as discovered, approved, destroyed, verified absent, preserved, unresolved, or error. | SP 800-53 SI-12; CM-12; CM-13; MP-6 | Related | State tracking models parts of the information/disposition lifecycle without claiming to implement the full lifecycle governance model. |
| **Scope / trust boundary** | Asserts only what can be established through supplied interfaces; no visibility claim over unscoped backups, provider internals, physical sectors, remapped blocks, or recoverable deleted blocks. | SP 800-88r2 §2–§4.5 | Boundary | Critical distinction between “not rediscovered through this interface” and media sanitization. |
| **Explicit non-claim of Clear / Purge / Destroy** | Filesystem removal is described as selective logical file removal and NIST Clear/Purge/Destroy claims remain false. | SP 800-88r2 §3–§4 | Boundary | Prevents successful logical-removal evidence from being overstated as physical/media sanitization. |
| **Synthetic end-to-end validation / CI** | Synthetic known-answer tests exercise the deterministic workflow and CI runs the test suite automatically. | SP 800-53A Rev. 5; CA-2 | Related | Product-level verification resembles the evidence-oriented assessment logic in 800-53A, but is not itself an organizational control assessment. |

## 4. Strongest current NIST relationships

The current center of gravity is intentionally small:

- **CM-12 / CM-12(1)** — SDIDA's discovery and information-location behavior.
- **SI-12 / SI-12(3)** — the broader information-management and disposal lifecycle to which SDIDA is adjacent.
- **MP-6 / MP-6(1)** — approval, tracking, documentation, sanitization/disposal process, and verification.
- **SP 800-88 Rev. 2 §§4.3–4.6** — decision, execution, assurance, and documentation around sanitization.
- **AU-9 / AU-11** — integrity and retention of evidence.
- **SP 800-53A Rev. 5** — assessment logic for determining whether intended control behavior actually occurred.

This baseline does **not** claim that these controls are fully implemented by SDIDA. It records functional overlap and boundaries.

## 5. Current boundaries and non-claims

A passing SDIDA workflow currently supports a bounded statement:

> Within the recorded discovery method and recorded scan scope, expected-absent exact instances were not rediscovered, expected-present instances remained observable, and the evidence chain is internally consistent.

It does **not** establish that:

- deleted sectors cannot be recovered;
- remapped or overprovisioned blocks were sanitized;
- provider-retained copies or backups were destroyed;
- all possible storage surfaces were searched;
- an underlying device satisfied NIST Clear, Purge, or Destroy;
- an organization satisfies a NIST control in full;
- an organization is HIPAA compliant.

The existing filesystem-removal technique remains:

```text
SELECTIVE_LOGICAL_FILE_REMOVAL
```

and the corresponding media-sanitization non-claims remain explicit.

## 6. Baseline decision log

| Decision | Rationale |
|---|---|
| Map **existing functionality first** | Avoid designing a future compliance system before documenting what SDIDA already does. |
| Use **Direct / Related / Boundary** labels | Prevent adjacent concepts from being misrepresented as full control implementation. |
| Keep HIPAA mapping out of v0.2 | The current task is a technical baseline; HIPAA mapping is a later layer. |
| Keep retention-period logic out of v0.2 | SDIDA produces evidence and performs bounded remediation but does not yet determine legal/organizational retention periods. |
| Preserve the Clear/Purge/Destroy boundary | Logical file absence is not equivalent to physical-media sanitization. |
| Preserve creation prompts | The development history shows that the safety architecture emerged before the NIST crosswalk rather than being retrofitted to appear standards-aligned. |
| Keep known-answer testing central | SDIDA should be judged against independently known reality, not against internally plausible output. |

## 7. Deferred questions

The following questions are deliberately deferred from this baseline:

- HIPAA Security Rule mapping through NIST SP 800-66 Rev. 2;
- retention schedules and retention-authority metadata;
- legal-hold logic;
- records schedules and disposition eligibility;
- PHI/PII classification policy;
- organizational roles and separation of duties;
- whole-medium Clear/Purge/Destroy integrations;
- cloud/provider retention and backup-destruction evidence;
- cryptographic erase/key-destruction workflows;
- policy for retaining SDIDA's own evidence artifacts.

These belong to future-state design rather than the present-state baseline.

## 8. Primary reference set

- **NIST SP 800-53 Rev. 5** — *Security and Privacy Controls for Information Systems and Organizations*.
- **NIST SP 800-53A Rev. 5** — *Assessing Security and Privacy Controls in Information Systems and Organizations*.
- **NIST SP 800-88 Rev. 2** — *Guidelines for Media Sanitization*.
- Existing SDIDA architecture, validation, and sanitization-boundary documentation in this repository.

## 9. Recovered SDIDA creation-prompt lineage

The following prompt history was recovered from the private build documentation created during development. Personal account details are generalized; technical wording and sequence are preserved as closely as possible.

### 9.1 Origin: abstract the process and make it reusable

> **User:** “K, you agree. Let's design the process. Put it in Nat terms”
>
> **User:** “Think we could manage to create a reusable script for this? 🙃”
>
> **User:** “Let's start a private GitHub repo to build the tool”
>
> **User:** “Seed Discovery Inventory Delete Audit”
>
> **User:** “Ok, repo is created”
>
> **User:** “Ok, I think I've got a good initial test plan. Pull a copy of PIQITT onto my new machine. From my [source email] address send the contents to a new dummy Gmail address. Add the attached files to the account's Google Drive. That's a good baseline messiness. The audit should run against that, I think?”
>
> **User:** “Print this along with the prompts that led up to it to MD and upload it to the repo as project planning. Keep it scoped to general purpose tooling”

These prompts establish that the reusable process abstraction and general-purpose scope preceded most implementation work.

### 9.2 Minimum viable build: Seed and Discovery first

> **User:** “Ok, so what's the minimum we need to run for this process? I don't need to know every detail we're going to capture, just the basics of each script and the order.”
>
> **User:** “Ok, put together the seed and discover scripts and add them to the repo”
>
> **User:** “Let's make it even simpler. Here's where I dropped the piqitt-main folder: `C:\sdidas\piqitt-main` — give me a step by step build to installing python, confirming git, pulling the sdidas from powershell, then running the script on the folder I provided”
>
> **User:** “Done. json files should have a datetime stamp. Here's the output: Python 3.10.11; git version 2.55.0.windows.3; Seeded 11 files; Discovered 11 exact matches; Seed count: 11; Discovery count: 11”
>
> **User:** “Looks good! Let's post the results so far in a separate MD in the repo. Include my prompt history at the top”

This phase established deterministic SHA-256 seeding/discovery and timestamped evidence artifacts before adding more complex behavior.

### 9.3 Controlled mess: prove discovery against known reality

> **User:** “K, let's get messy”
>
> **User:** “Here's the output”
>
> **User:** “The email I created was [dummy Gmail account]. Let's move on to the next steps”
>
> **User:** “What do you mean by Google Cloud? I have Google Drive.”
>
> **User:** “Yeah, I like the desktop version better. Easier to inspect. Successfully downloaded and synced in `G:\My Drive` for the new [dummy Gmail account]. Next steps?”
>
> **User:** “Looks good” — Drive-only discovery returned 11 exact matches; combined local + mounted Drive discovery returned 34 exact matches.

This phase produced the reuse-before-specialization decision: use the validated filesystem scanner when a storage provider can expose ordinary bytes through a mounted filesystem.

### 9.4 Inventory: change the unit of analysis

> **User:** “Ok, it's the next day. Let's keep going with the next steps”
>
> **User:** “Here's the output: Inventoried 34 exact instances across 11 roots; Instance-count distribution: 10 roots x 3 instances; 1 root x 4 instances”
>
> **User:** “Before we test deletes, add a new MD to the repo with these results.”

Inventory converted 34 observations into 11 root-centered materialization families, making provenance rather than filename/count the operative model.

### 9.5 Audit before automated Delete

> **User:** “Ok, walk me through the delete test next”
>
> **User:** “Looking good” — Audit FAIL: expected absent 0/12 verified absent; expected present 22/22 verified present; unexpected missing 0; unexpected new 0. After manual removal, the exact same audit returned PASS: expected absent 12/12 verified absent; expected present 22/22 verified present; unexpected missing 0; unexpected new 0.

Audit was intentionally proven using manual removal before SDIDA was given destructive authority. This is the operational origin of the invariant:

> **Delete never discovers. Discovery never deletes.**

### 9.6 End-to-end destructive loop

> **User:** “Let's do it to it!”
>
> **User:** “Ohhhh piqitt-main has 2 subdirectories, the copy needs to be recursive”
>
> **User:** “Yup, looks good I think” — recursive controlled-mess file count 11; after creating one deliberate duplicate, 12.
>
> **User:** “Lookin good” — Discovered 34 exact matches; Inventoried 34 exact instances across 11 roots; distribution 10 roots x 3 instances and 1 root x 4 instances.
>
> **User:** “Output” — Approved 12 inventoried descendants for deletion; Delete DRY RUN; WOULD_DELETE: 12; after the dry run all 12 files remained.
>
> **User:** “Eureka?” — Delete EXECUTE; DESTROYED: 12; target file count 0; Audit PASS; 12/12 verified absent; 22/22 expected survivors present; 0 unexpected missing; 0 unexpected new.

This completed the constrained pipeline:

```text
Discovery observes.
Inventory organizes.
Approval authorizes.
Delete executes.
Audit independently checks reality.
```

### 9.7 Public generalization

> **User:** “I just created a new repo, sdida_data. Let's look at SDIDA repo and see how to copy it over clean to the new repo, make it content agnostic, sanitize any reference to me”

This began the public-distribution phase: reuse the generic implementation while excluding private fixture history and personal case assumptions from the published tool content.

### 9.8 Current evolution: baseline before future compliance design

> **User:** “What I'd like to do now is create a NIST crosswalk to SDIDA. This has evolved into a rough draft for HIPAA compliant data retention and destruction. Go look which 800 series are relevant”
>
> **User:** “Ok I feel like you got ahead of me. First we want the baseline- what functionality and components exist in SDIDA, and what NIST sections are related. Very high level but be thorough”
>
> **User:** “Let's put that in a project baseline doc and print it, full trim, prompts, and decision log”
>
> **User:** “Go pull all the relevant SDIDA prompts to show how the tool was created. Show me here”
>
> **User:** “Add it to the bottom of the project baseline doc and increment the version. Print”

These prompts explicitly separate the descriptive baseline — what already exists — from later HIPAA/retention architecture — what should be added.

### 9.9 Prompt-to-architecture trace

| Prompt / inflection point | Architectural consequence |
|---|---|
| Design the process / reusable script | Treat the original problem as a reusable provenance-and-remediation pipeline rather than a one-off cleanup script. |
| Seed Discovery Inventory Delete Audit | Create explicit phase boundaries rather than one broad scanner/deleter operation. |
| Known controlled mess | Use known-answer fixtures so correctness is measured against independently established reality. |
| Minimum first build | Start with deterministic exact hashing and local files before fuzzy matching, AI, APIs, or destructive behavior. |
| Drive desktop is easier to inspect | Normalize storage into an already-proven scanner when possible; specialize only when the evidence cannot otherwise be observed. |
| Inventory result | Change the unit of analysis from loose file observations to root-centered materialization families. |
| Audit before Delete | Prove the verification mechanism independently before granting automated destructive authority. |
| Explicit approval + dry run | Destructive action consumes a frozen approved manifest; it does not discover or expand its own target set. |
| “Eureka?” end-to-end test | Separate execution evidence from independent post-action state verification. |
| Public generalization | Publish the instrument without carrying forward private fixture history or personal case assumptions. |
| NIST baseline correction | Describe current functionality and standards relationships first; defer future compliance architecture until the baseline is explicit. |

## Appendix: baseline statement

The SDIDA architecture was not specified all at once and then implemented. It emerged through a sequence of deliberately constrained tests: define known roots, create known proliferation, verify deterministic discovery, reorganize observations into provenance families, prove independent audit before automation, add explicit approval, then permit destructive execution and verify the resulting state independently.

The prompt record is therefore part of the technical provenance of the tool, not merely conversational history.
