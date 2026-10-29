# V14-00 evidence workspace development contract

V14-01 preserves this exact workspace/snapshot-v1 contract, including duplicate
capture rejection. [The analytical revision ADR](v14-analysis-revisions-adr.md)
defines the explicit additive transition required for V14-02; it is not a silent
extension of these stored objects.

Status: implemented development contract for local review, not the final v1.4
contract freeze. The [v1.3 evidence freeze](v13-18-evidence-contract-freeze.md)
remains authoritative for capture and observation meanings. This document describes
the narrower lifecycle consumer and the independently versioned artifacts it writes.

## Responsibilities and boundaries

The observation producer remains responsible for scanning the original local capture
and producing frozen observation version 2 / capture version 1 / catalog version 1.
The lifecycle consumer validates imported metadata structure, canonical observation
hashes, aggregate identities, packet/interface joins, coverage denominators and the
timestamp summaries it consumes. It does not reopen, copy or authenticate capture
bytes. The imported capture SHA-256 remains an assertion about the original source
until those exact bytes are independently checked.

The source JSON is never rewritten. The consumer retains the complete accepted
observation object in the snapshot without changing its values, identities, array
ordering or hash. JSON whitespace and object-key order are presentation rather than
source-byte identities. No mapping, baseline approval, native comparison, enrichment
meaning or address-ownership claim is introduced by importing an observation.

The product supports `evidence init`, `add`, `list`, `show` and `verify`. A successful
`verify` reports `VERIFIED_METADATA`; it establishes local metadata integrity within
the implemented contract, not authenticity, collection authority or chain of custody.

## Artifact fields and identities

`workspace.json` has exactly two integer root fields:

```json
{"snapshot_version": 1, "workspace_version": 1}
```

The workspace contains a `snapshots/` directory. Every committed member is a regular
file named `snapshot-<64 lowercase hexadecimal SHA-256 characters>.json`. There is no
mutable snapshot index: list operations derive the inventory from validated files.
The filename stem must equal the object's `snapshot_id`.

Snapshot version 1 has exactly these root fields:

| Field | Type and meaning |
|---|---|
| `snapshot_version` | Integer `1`; booleans are rejected. |
| `snapshot_id` | `snapshot-` plus the canonical snapshot digest described below. |
| `generator` | Exactly `{"name": "otarchguard", "snapshot_implementation": 1}`. |
| `capture_sha256` | Exact imported `observations.capture.sha256`; also bound to `capture_id`. |
| `observations_sha256` | Exact validated frozen observation digest. |
| `label` | Owner-supplied printable Unicode text, including the empty string. |
| `collection` | Exactly `first_timestamp`, `last_timestamp`, `missing_timestamps`. |
| `observations` | Complete accepted frozen version-2 metadata object. |
| `limitations` | Deterministic producer limitations describing integrity, source verification, collection coverage, owner review and sensitivity. |

Collection bounds are the minimum first and maximum last flow timestamps. Each is
reduced rational UTC-second text (`numerator/denominator`) or null when no timestamp
exists. Missing timestamps sum the flow counters. Import time, file creation time,
execution order, paths and filenames do not enter the snapshot. Collection bounds
describe available packets and do not assert continuous monitoring, equal vantage
points, complete visibility or activity between observations.

The snapshot digest is SHA-256 over the whole snapshot object **except** `snapshot_id`,
using compact sorted-key ASCII-escaped JSON with separators `,` and `:` and no final
newline. The retained observation digest excludes only `observations_sha256` inside
the original observation. The snapshot digest therefore binds the original
observation, its original digest, derived collection summary, label, generator and
limitations. Capture identity remains the original capture SHA; it is never derived
from a path or label.

The label is descriptive text rather than an identity lookup key or approval.
Because it is integrity-bound metadata, changing it would change a newly built
snapshot's digest. Importing the same capture SHA again never creates that second
object in the same workspace: `DUPLICATE_CAPTURE` reports the existing summary,
`observations_match` and `label_match`, preserves the first object's bytes and label,
and performs no merge. This also applies when an observation is regenerated or
renamed. It prevents duplicate evidence from inflating apparent coverage.

## Serialization, ordering and supported inputs

Files and CLI results use UTF-8 JSON, ASCII escaping, sorted object keys, two-space
indentation and one final LF. Duplicate keys, NaN, Infinity, floating-point values,
nonobject roots and unsupported version values are rejected. Integers and booleans
remain distinct in validation and canonical-byte comparisons.

Snapshot list order is ascending snapshot filename/identity, not assumed chronology.
Accepted host arrays retain IP-text ordering and flow arrays retain ID ordering.
Other frozen observation arrays retain their original supported order. The lifecycle
does not reorder evidence to invent a temporal sequence or silently repair inputs.

The lifecycle-v1 storage allowlist requires the exact documented frozen field names
at the observation root and in capture, interface, host, flow, ARP, packet sample,
timestamp, protocol hint, conversation and coverage records. **Unknown optional
fields are rejected**, so arbitrary extension payloads are not silently archived.
This deliberately narrower persistent-storage policy differs from the independent
development probe `tools/read_capture_evidence.py`, which preserves unknown optional
fields for read-only examination. The probe and the source observation are unchanged.
Supporting a future extension requires explicit lifecycle review, tests and a contract
decision; consumers must not remove unknown fields and then reuse the old digest.

Unknown codes in supported fields are never interpreted as positive evidence. Some
frozen structural enum fields, including flow status and transport, reject unknown
values. Other uninterpreted text fields, for example a future `transport_evidence`
code, are retained as unassessed metadata. This slice produces no drift, reachability,
approval, vulnerability or absence verdict from those values. Unknown workspace,
snapshot, observation, capture and catalog versions are rejected; no automatic
migration occurs.

## Bounds and persistence safety

| Default bound | Limit |
|---|---:|
| Input JSON or serialized snapshot | 64 MiB each |
| Total snapshot-directory file bytes | 256 MiB |
| Snapshots per workspace | 256 |
| JSON nesting | 64 |
| JSON value/container nodes | 2,000,000 |
| Individual text values | 4,096 characters |
| Snapshot label | 256 characters |
| Rational timestamp text | 512 characters before fraction parsing |

Frozen inventories retain their own finite limits, including 256 capture interfaces,
20,000 hosts, 50,000 flows/conversations and eight samples per flow/sample kind.
Resource rejection publishes no new snapshot. Verification processes snapshots one
at a time; the listing retains bounded summaries rather than all observation objects.
These are rejection ceilings, not measured throughput or RSS guarantees.

Only portable local paths are supported. UNC paths, reserved device names, alternate
data streams, trailing spaces/dots, control characters, path traversal components,
symlinks and junction traversal are rejected. Snapshot identifiers cannot serve as
paths. Nonregular, unexpectedly named or corrupt snapshot entries fail the operation
rather than disappearing from the inventory.

Publication writes and flushes a temporary regular file in the destination directory,
then atomically publishes it without replacing an existing name: Windows uses
no-replace rename; POSIX uses no-replace hardlink publication followed by temporary
unlink. Unsupported filesystems fail closed. Existing workspaces and snapshot files
are never overwritten. Interrupted `.pending-*.tmp` members fail verification with
`EVIDENCE_INTERRUPTED`; inspect and remove only the uncommitted temporary file after
checking that the committed snapshot inventory remains intact, then verify again.
There is no automatic cleanup that might erase reviewed evidence.

The supported model is a **local single writer**. There is no concurrent-writer lock,
malicious-filesystem sandbox or power-loss durability claim. Read identity checks
detect ordinary file replacement or mutation; filesystem races and hostile privileged
writers remain outside this guarantee. Atomic publication prevents ordinary partial
JSON files from acquiring committed snapshot names.

## Controlled failures

CLI failures use structured JSON diagnostics on stderr and exit code 2. Expected
codes include:

| Code | Meaning |
|---|---|
| `EVIDENCE_PATH`, `EVIDENCE_ID` | Unsupported local path or snapshot identifier. |
| `EVIDENCE_FILE`, `EVIDENCE_READ`, `EVIDENCE_CHANGED` | Nonregular, unreadable or changed input. |
| `EVIDENCE_JSON`, `EVIDENCE_OBSERVATIONS` | Invalid JSON or unsupported/tampered source metadata. |
| `EVIDENCE_LABEL` | Unsupported descriptive text. |
| `EVIDENCE_SNAPSHOT`, `EVIDENCE_WORKSPACE` | Invalid immutable object, manifest or inventory. |
| `EVIDENCE_EXISTS`, `EVIDENCE_WRITE` | Existing destination or unsuccessful atomic publication. |
| `EVIDENCE_INTERRUPTED` | Uncommitted temporary evidence requires local review. |
| `EVIDENCE_NOT_FOUND` | Exact snapshot identity absent from the workspace. |
| `LIMIT_EXCEEDED` | A finite parser, storage or output budget was exceeded. |
| `INVALID_VALUE` | Command usage failure at `$.evidence_options`. |
| `EVIDENCE_INTERNAL` | Unexpected processing failure; no analytical result available. |

The independently specified frozen fixtures and adversarial tests in
`tests/test_evidence_workspace.py` exercise canonical identities, duplicate handling,
typed-version rejection, tampering, publication failures, portable paths, bounded
inputs and CLI behavior. Final acceptance and any later contract transition remain
tracked in [v14-progress.md](v14-progress.md).
