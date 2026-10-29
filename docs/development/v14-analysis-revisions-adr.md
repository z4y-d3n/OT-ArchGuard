# ADR V14-01: physical evidence, analytical revisions and human review

Status: V14-02 design accepted for implementation planning; experimental identity
probe only. No snapshot-v1 migration or baseline approval feature is implemented.

## Three identities

1. **Physical collection** is SHA-256 over original capture bytes. Reopening or
   reprocessing those bytes never creates another independent collection. A
   capture hash establishes integrity, not collector authenticity or authority.
2. **Analytical revision** binds that capture to exact validated observation,
   enrichment, architecture model, mapping, comparison and policy digests, plus
   producer semantics. Absent attachments are explicit nulls. Different inputs,
   parser modes, limits or producer semantics create a new revision of the same
   collection. File paths, import time and local filenames do not create one.
3. **Review/baseline decision** is an independently versioned human assertion
   over exact analytical inputs and a declared scope. A label is not approval.
   Review identity must bind decision type, subject digests, scope, reviewer
   assertion and supersession relationship. Baseline selection additionally
   binds collection membership and coverage assumptions. No existing approval
   transfers to new decoded meanings, model, mapping, policy or revision.

## Additive transition, never a silent snapshot extension

Workspace/snapshot v1 continues to reject unknown fields and duplicate captures.
Repeated ingestion still reports `DUPLICATE_CAPTURE` and preserves first bytes.
V14-02 should add explicitly versioned analysis-attachment and review objects in
a new workspace contract. A v1 reader must reject that new workspace version.
Migration is explicit, writes a fresh destination, verifies all old objects and
keeps their exact bytes/IDs. It must record links to the original snapshot,
without editing the snapshot or turning labels into human approvals.

List/count operations must report physical collections and analytical revisions
separately. Two analyses of one capture count as one collection. Revisions can
be compared only after validating component contracts, exact source joins and
coverage compatibility. Missing observations are not proof of blocking.

The versioned producer-semantics manifest must bind observation/capture/catalog
versions, decoder revision, evaluator identity, relevant implementation digests,
all selected parser/analysis limits and modes. Its canonical hash is an input to
analysis identity. A package version by itself is insufficient. Full component
implementation identities belong in execution receipts even when semantics are
unchanged. Every attachment must be validated before its claimed digest is used.

## Executable design boundary

`tools/evidence_identity.py` is a development-only domain-separated identity
probe. It takes exact SHA-256 inputs and produces `analysis-proposal-...`; this
prefix explicitly avoids defining a runtime storage contract. Tests independently
specify the canonical bytes and show that changing each analytical input changes
the revision while preserving physical identity, except when capture bytes change.
The probe creates no objects, imports, approvals, baseline or persistence API.
Existing snapshot-v1 tests continue to exercise actual duplicate prevention.

## Required V14-02 acceptance sequence

1. Freeze attachment schemas, bounded validation, canonical semantics manifest
   and exact joins to preserved observations/capture/model/mapping inputs.
2. Specify explicit workspace migration and revision storage, atomic no-replace
   publication, interrupted-write recovery, bounded inventories and rejection of
   duplicate physical collection inflation. Preserve unknown-version rejection.
3. Implement reviewer-authored scoped decisions and owner-selected baselines,
   including revocation/supersession and invalidation on changed inputs. No
   automatic carry-forward or baseline approval from structural recognition.
4. Independently test malicious rehashing, stale joins, missing attachments,
   duplicated captures, reordered migration, unsupported component versions,
   changed producer semantics, resource rejection and interrupted writes.
5. Only then expose lifecycle commands. Historical comparisons, drift and the
   Explorer remain later milestones with their own compatibility requirements.
