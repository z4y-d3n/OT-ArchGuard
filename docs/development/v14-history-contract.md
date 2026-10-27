# V14-02 historical evidence contracts and migration decision

Status: implemented development contracts, independently versioned from frozen
native and packet-evidence contracts. This is a local single-writer foundation
for future V14-03 comparison, not a drift engine or historical Explorer.

## Identities and storage

Physical collection identity remains SHA-256 of original capture bytes, imported
from validated frozen observation-v2/capture-v1 metadata. Metadata validation
does not reopen those bytes or establish authenticity. Each collection has one
original snapshot; repeated ingestion preserves it and reports duplicate capture.
Analytical revisions and local human assertions have distinct identities.

Workspace-v2 has `workspace.json` and five directories: `snapshots/`,
`attachments/`, `analyses/`, `baselines/` and `reviews/`. Each directory contains
only regular files named `<singular>-<64 lowercase hex>.json`. The manifest
declares workspace 2 and snapshot/attachment/analysis/baseline/review 1. There is
no mutable selection pointer or database. Inventory is derived from files; the
migration provenance records authoritative membership of the original imported
snapshots, including their exact byte hashes. Additional collections are allowed.

Snapshot-v1 IDs and bytes remain unchanged. For each new object remove only its
`<singular>_id` field and hash compact sorted-key ASCII-escaped JSON containing
`{"domain":"otarchguard.<singular>","value":<remaining object>}`. Prefix the
SHA-256 with `<singular>-`. The manifest digest uses the separately named
`otarchguard.producer-semantics.v1` domain and the same envelope. Objects include
their own exact integer contract versions. Booleans are not version integers.
Serialized files use sorted keys, ASCII escaping, two-space indentation and a
final LF. Floats, duplicate JSON keys, NaN/Infinity and unsupported fields are
rejected. Lists have contract-specific canonical order. Capture times remain
exact rational values; no floating-point conversion determines identity.

## Explicit migration and publication

`evidence init` retains its v1 default. `evidence init PATH --version 2` creates a
fresh v2 workspace. `evidence migrate SOURCE DESTINATION` accepts only a complete
supported v1 workspace and a fresh, separate destination. Unknown versions never
trigger automatic migration. Existing v1 readers continue rejecting v2.

Migration validates the strict source inventory, every snapshot, physical
uniqueness and resource limits before reserving the new directory with exclusive
creation. It records the raw source manifest SHA and sorted original snapshot
IDs, raw byte SHAs, capture SHAs and observation SHAs. Original files are copied
byte-for-byte using atomic no-replace publication. All source files are reopened
and compared again, destination bytes are checked, and `workspace.json` is
published last. No snapshot is reserialized or relabeled. Baselines, attachments,
analyses and reviews start empty. A label never becomes an approval.

The v1 manifest contains no historical membership index. A snapshot deleted
before migration validation cannot be distinguished from an originally smaller
valid workspace. Missing or changed files during migration are detected; after
migration, the recorded original membership and byte hashes must remain intact.

Failed creation retains its reserved destination and any pending marker or
copied objects. A destination without its committed manifest is not valid.
Inspect or quarantine the abandoned directory manually, preserve any needed
bytes, and retry into a different fresh destination. The application never
recursively deletes evidence or repairs a source automatically. Pending files
inside a committed workspace require inspection and cause verification failure.

Subsequent lifecycle writes append one complete object after validating the
entire prospective state. Existing IDs are idempotent only for identical
canonical content; a collision or overwrite fails closed. POSIX uses no-replace
hard links and Windows uses no-replace rename. Unsupported filesystem behavior
fails closed. Local single-writer use is required: this is not an OS sandbox,
authenticated custody system or defense against a privileged concurrent writer.

## Attachment-v1

Each attachment binds kind, capture SHA, observation SHA, native component SHA,
exact model/mapping attachment dependencies, retained payload and limitations.
Only four kinds are accepted; arbitrary JSON attachments have no supported path.

| Kind | Validation and dependency policy |
|---|---|
| `enrichment` | Enrichment schema 1, exact supported decoder revision 1/2, canonical producer hash, exact preserved capture metadata, packet/interface/endpoint/transport/protocol-selection joins and privacy field allowlists. |
| `model` | Actual native schema-1 YAML/JSON is parsed and validated through the native API. The canonical native model and its native identity are retained; the input file is never rewritten. |
| `mapping` | Requires an exact validated model attachment; the existing reviewed-association consumer verifies capture/observation/model, candidates, decisions, reviewer assertions and mapping hash. |
| `comparison` | Requires exact model and mapping attachments. Replays the native comparison with those validated inputs and requires exact canonical equality with the imported result; no self-reported digest substitutes for replay. |

V14-01 enrichment legitimately has `observations_sha256: null`; this is accepted
and retained as no producer observation binding. Attachment-v1 also accepts a
nonnull field only when it equals the exact preserved observation SHA and the
original producer digest verifies. Its frozen producer structure is checked
through a separate equivalent null-bound validation copy; retained input and
digest are never changed. This is an explicit attachment-consumer extension,
not a change to the frozen V14-01 producer or standalone reader.

Sampled packet references are checked exactly. For unsampled packets only the
available aggregate, interface and timestamp relationships can be validated;
reopening the original capture would be necessary to establish every packet
claim. Structural recognition, port hints, malformed/truncated/unsupported
records and mappings retain their original meanings and never imply approval,
device ownership, command execution or comprehensive visibility.

## Analytical revision-v1 and producer semantics

An analysis binds exact physical capture SHA and observation SHA, enrichment,
model, mapping and comparison attachment IDs/native SHAs, explicit absent
components, explicit absent policy, and a versioned producer-semantics manifest
and digest. One physical collection may have many analyses. Paths, labels,
snapshot IDs, local filenames, import times, OS and Python version do not define
an analysis. Repeated identical validated interpretations are idempotent.

The manifest binds native engine identity 1.3.0, frozen component versions,
decoder revision, a fixed inventory of exact parser/evaluator/consumer source
SHAs, capture/native/enrichment consumer limits, retained enrichment producer
limits, metadata-only parser mode and enforced boolean analysis options
`require_complete_scan` and `require_reviewed_mapping`. Unsupported manifests
and unknown source implementations fail closed. The current runtime supports
its exact implementation inventory; supporting historical manifests from a
future changed implementation requires an explicit compatible reader.

Frozen observations do not attest original producer source code or parser
configuration. Therefore `original_capture_parameters` is explicitly null and
original producer provenance is explicitly unattested. The manifest identifies
selected local validation and native replay semantics; it does not fabricate
knowledge of how the original PCAP was processed. Distribution identity remains
1.4.0.dev1, independently of native engine semantics 1.3.0.

## Baseline-v1 and review-v1

Evidence baseline proposals select nonempty exact analyses, at most one per
physical collection. Architecture baseline proposals require an exact validated
model attachment. Either may explicitly link that model and selected analyses;
the proposal binds every identity and has no human authority on creation.

Scope has exactly `environment`, `purpose` and `coverage` printable strings, plus
sorted unique printable-string lists `uncertainties`, `vantage_points` and
`protocols`. Unknown visibility or packet loss should be stated as unknown.
The original snapshots retain available rational collection windows; scope
does not invent sensor completeness, period uniformity or missing measurements.
Changing scope, membership, analysis or model creates a different proposal ID.

Reviews bind exact subject baseline ID, subject type `baseline`, scope SHA,
decision, human-supplied reviewer and rationale, exact evidence references,
optional predecessor, nullable asserted UTC contextual time and limitations.
Contextual time is identity-bound assertion metadata and is never ordering or
authentication evidence. The CLI's distinct `approve`, `reject`, `revoke` and
`supersede` commands are explicit intent; no parser, label, import or mapping can
invoke these decisions automatically. Only fictional reviewer labels are used
by automated tests and walkthroughs.

State is derived iteratively from immutable records:

- No decision means `PROPOSED`.
- `approve` introduces `APPROVED`; `reject` introduces terminal `REJECTED`.
- `revoke` references an exact active approval and the same exact baseline,
  making it `REVOKED` while retaining the old record.
- `supersede` references an exact active approval and a different proposal of
  the same baseline kind and exact scope, approving the new baseline and marking
  the predecessor subject `SUPERSEDED`.
- Each baseline has at most one introducing decision; each approval has at most
  one successor. Conflicting successors, cycles, missing dependencies and two
  active approvals for the same exact kind/scope fail closed. Terminal decisions
  cannot be revived. Identical decisions are idempotent. Different scopes may
  have independent active approvals; there is no global implicit current pointer.

An old approval continues to describe its exact old interpretation when a new
analysis exists. That new interpretation remains unapproved until explicitly
selected and reviewed. Existing decisions are never rewritten or deleted.
`baseline show/review --text` presents bounded membership, declared scope,
uncertainties, exact review IDs and pending action without packet arrays.

Reviewer identity, organizational authority, capture authenticity, deployment,
operational safety and comprehensive visibility remain unverified local claims.
SHA-256 provides integrity and content identity, not authority or truth.

## Limits, diagnostics and future consumers

Defaults: 256 collections/snapshots, 1,024 attachments, 1,024 analyses, 1,024
reviews, 256 baselines, 256 baseline members, 64 MiB per JSON object, 256 MiB
total committed workspace bytes, JSON depth 64 and 2,000,000 nodes. There are
four attachment slots per analysis, fixed acyclic component dependencies and
at most 1,024 review-chain traversal steps globally. Individual JSON text is
limited to 4,096 characters; scope strings 1,024, scope list entries/reviewer
256, rationale 2,048 and scope lists 32 entries. These are work ceilings, not
performance guarantees.

Local portable paths only: traversal, UNC/device/alternate-stream names,
symlinks, junctions/reparse points, nonregular entries and unexpected inventories
fail closed. Bounded strict reads detect file replacement/modification. User
text is printable and never executable HTML. No raw packet payloads, captures,
credentials or external corpus downloads are introduced by this subsystem.

CLI failures exit 2 with structured diagnostics. `LIMIT_EXCEEDED` identifies a
resource rejection; `EVIDENCE_PATH/FILE/READ/WRITE/EXISTS/CHANGED/INTERRUPTED`
describe local I/O failures; `EVIDENCE_WORKSPACE/OBJECT/ID/NOT_FOUND` describe
storage contracts; `EVIDENCE_ATTACHMENT/REVISION/SEMANTICS/BASELINE/REVIEW/GRAPH`
describe semantic and dependency failures. Existing v1 behavior and error codes
remain authoritative for its commands.

The public `lifecycle.load_state`, `show_object`, `list_revisions` and
`verify_lifecycle` validate all stored object semantics and relationships before
returning analytical data. Low-level history storage validates content identity
and inventory; it requires the lifecycle callback before analytical use. A
metadata verification result explicitly separates structural/cross-artifact
consistency, original-capture availability, authenticity and local review
assertions. Future V14-03 must use exact validated references and independently
define coverage comparability and drift meanings. V14-02 implements none of
those future findings or severity classifications.
