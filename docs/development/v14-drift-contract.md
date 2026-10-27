# V14-03 historical comparison contract and decisions

Distribution `1.4.0.dev1`; native engine `1.3.0`; drift engine `1.4.0-drift.1`;
`drift_version: 1`, comparability policy 1, explicit context version 1.
This is an additive offline consumer of the V14-02P lifecycle. Existing source
artifacts, approvals, canonical identities and workspace formats are preserved.

## Authority and acquisition

Every public comparison acquires the entire workspace through the trusted
`lifecycle._operation` boundary, including semantic validation of unselected
objects, native replay, exact attachment joins and review graph resolution.
The private operation context owns its validated data and native model cache.
No caller flag, raw historical storage read, or digest alone grants authority.
No authority survives into a later operation. Native models are reused within
the operation; there is no model validation inside communication-finding loops.

The caller selects an exact baseline ID, candidate IDs, optional subset of exact
baseline members and explicit collection alignment. An evidence baseline must
have an effective `APPROVED` state and an exact active introducing review record.
Proposed, rejected, revoked and superseded references fail normal comparison.
An architecture baseline requires both its model attachment and an explicitly
selected candidate model attachment. Candidate revisions never inherit approval;
independent approved memberships and their scopes/review IDs are recorded.
Review labels remain unauthenticated local assertions.

At most one interpretation of a capture may be selected per side. The same
capture on both sides is one physical collection, even with different decoders.
Pairs are explicit, one-to-one and deterministically sorted. Filenames, labels,
import order and timestamps never choose a correspondence. Selected collections
without a pair produce `UNALIGNED_COLLECTION` abstentions. An `unresolved` pair
permits dataset descriptions with indeterminate alignment, never asserted
operational continuity. No cross-capture ownership is inferred.

## Comparability before interpretation

Each pair records `COMPARABLE`, `PARTIALLY_COMPARABLE`, `INDETERMINATE` or
`INCOMPARABLE` for every dimension, with source evidence, reason and consequence:

| Dimension | Evidence and interpretation |
|---|---|
| Physical collection / revision | Capture SHA versus independent analytical ID |
| Producer semantics | Exact supported observation versions, parser mode, limits and source identities |
| Container completeness | `complete_file_scan` and unknown block count |
| Packet interpretation | Raw total, interpreted and uninterpreted denominators |
| Fragmentation / truncation | Fragmented, truncated, malformed and truncated-record counts |
| Linktypes | Supported Ethernet 1 / raw IP 101 versus uninterpreted types |
| Timestamps | Exact rational bounds and missing timestamps; clocks/order remain unattested |
| Observation scope | Exact environment, purpose, coverage assertions and uncertainties |
| Vantage points | Explicit equal, different or missing declared sensor labels |
| Protocol visibility | Explicit declared protocol coverage |
| Alignment | User assertion or unresolved correspondence |
| Architecture | Exact native canonical model identity |
| Reviewed associations | Independently accepted mappings and common model requirement |
| Provenance | Validated structural joins; source authenticity remains unknown |
| Baseline scope | Exact approved membership and scope |
| Decoder | Exact enrichment schema/revision/inventory/limits/consumer semantics |

Overall status includes provenance uncertainty and can remain indeterminate even
when communication metadata is comparable. Domain statuses are authoritative
for their limited meanings; there is no single security verdict.

`strict` rejects nonequivalent communication scope/coverage or unaligned selected
collections. Missing models or protocol equivalence still yield explicit domain
abstentions; strict never turns unknown evidence into proof. `qualified` retains
supported partial metadata differences and limitations. `descriptive` explicitly
labels finite dataset differences. No mode bypasses source or approval validation.
No `force-comparable` option exists.

Observed timestamp bounds use `Fraction`, never floats. Ordering is same
collection, candidate-window-after, candidate-window-before, overlapping, or
indeterminate. Bounds do not attest continuous exposure, synchronized clocks or
activity in gaps. Counts remain raw counts; no rates, percentages or trends are
computed.

## Independent result domains

Communication keys preserve packet-header direction, IP family, source/destination
IP, transport, source/destination port and VLANs. ARP opcode/operation remain
distinct; opaque null-endpoint linktypes cannot fabricate an endpoint identity.
Status and linktype differences are metadata, not arbitrary new TCP sessions.
Equivalent flows aggregate raw counts, framing statuses, initiation evidence,
flags, hints and supported ARP metadata. Timestamps support provenance without
making every different capture an apparent metadata change. Representative
references are bounded to eight flows, packets and initiation records per key;
omitted counters retain denominators. Exact source snapshots retain all evidence.

Communication records distinguish `OBSERVED_IN_BOTH`, candidate-only,
reference-only, changed metadata and unassessed opaque observations. Only finite
capture presence is asserted. Reference-only never means blocked, offline,
removed, interrupted or malicious. Same addresses never establish stable devices.
Asset annotations require independently `ACCEPT`ed equivalent asset/interface
relationships in the exact same model on both sides. Pending, ambiguous, changed
or missing relationships abstain. Even accepted annotations describe reviewed
model-relative assertions, not authenticated physical continuity.

All seven bounded protocol families participate: Modbus TCP, PROFINET DCP,
EtherNet/IP/limited CIP, classic S7comm, IEC-104, OPC UA Binary and DNP3/TCP.
Only validated categorical header fields are indexed. Transaction/sequence IDs
and arbitrary payloads are excluded. Positive recognition, hints, malformed,
truncated and unsupported records retain their status distinctions. Exact decoder,
schema, inventory, configured limits and supported consumer semantics are required
for protocol differences. Decoder 1 versus 2 is analytical interpretation,
including for one physical capture; old enrichment is never reinterpreted.
Write-type recognition never proves command execution or process manipulation.

Architecture uses canonical native record catalogs and validated fields, covering
assets, zones, interfaces, conduits, transport/forwarding edges, services, rules,
intents, scenarios, access points and external dependencies, plus SUC/root metadata.
Common IDs align declarations only; renamed IDs are added/removed, without fuzzy
matching. Native classifications distinguish metadata, structural, definition,
enforcement and scope changes. YAML comments, spacing and harmless order changes
do not produce deltas. There is no invented subnet or deployed firewall model.

Explicit native queries contain exactly `source_asset_id` and `service_id`.
Paired evaluation requires equivalent SUC, source/destination asset and interface
semantics and destination service definition. Changed policies/edges may then
yield model-relative reachability differences. The unchanged native engine uses
peer model port partitions and retains exact query, intervals and witnesses.
Missing/non-equivalent/self-origin/unsupported queries abstain, never deny.
Native results do not establish real packet enforcement or application success.

Top-level finding families are declared architecture, observed communication,
protocol metadata, native assessment, analytical interpretation, coverage and
indeterminate comparison. Each binds its exact key, sources, comparability,
explanation, limitations and unsupported interpretations. Unchanged support rows
remain inspectable and must not be counted as operational changes. There are no
CVSS scores, incident severities, attribution or safety conclusions.

## Standalone immutable artifact

Workspace-v2 retains exactly its existing five object directories. Reports live
outside that tree. Root fields are `drift_version`, `engine_version`,
`comparability_policy_version`, `implementation_sha256`, `inputs`, `options`,
`comparisons`, `unaligned_findings`, `architecture_findings`, `summary`, `limits`,
`resource_usage`, `limitations`, `reproduction` and `drift_id`.

Inputs bind the original workspace-manifest byte SHA, complete exact baseline,
effective review decision, recorded review frontier, selected source identities,
candidate review status and optional exact model pair. Sources bind snapshot,
capture, observations, analytical revision, producer semantics and attachment IDs.
Options bind explicit selections, context, scopes, alignment rationale and queries.
Paths, local output names and generation times do not enter identity.

Remove only `drift_id`, then hash compact sorted-key ASCII JSON of
`{"domain":"otarchguard.drift.v1","value":<remaining report>}` using SHA-256.
Prefix the lowercase digest with `drift-`. Published JSON uses sorted keys,
two-space indentation and final LF. Lists have deterministic contract order.
Only exact JSON primitives are supported; floats, duplicate keys, invalid Unicode,
unsupported fields/versions and excessive nesting are rejected.

`read_report` verifies bounded structure and identity only. It grants no analytical
authority. `verify_report` validates the whole source lifecycle, replays the
recorded predecessor-closed review graph, rebuilds every result and requires exact
canonical equality. A self-consistent recomputed report digest is insufficient.
The consumer reports structure validity, source availability, exact reproduction
and current baseline approval separately. A later revocation/supersession does
not alter historical report bytes or the recorded graph; current authority is
explicitly false. There is no authenticated creation timestamp, signature or
proof that a local review assertion was truthful when originally recorded.

Exact comparison implementation source identities are bound. This consumer
supports its current implementation only. A future incompatible engine must
provide an explicit compatible historical reader; a new parser cannot silently
grant old artifacts new meanings. Dependency loss or unsupported source semantics
fails closed rather than displaying unverified findings as authoritative.

Publication owns a defensive copy of caller data, replays before publishing, checks
the complete acquired workspace bytes again and uses atomic no-replace publication.
`generate_report` combines acquisition/comparison/publication within one operation.
Portable local path checks reject traversal, UNC/device/ADS names, reserved names,
links/junctions/reparse points, in-workspace outputs and existing destinations.
This remains a local single-writer contract, not a sandbox against a privileged
writer racing arbitrary directory ancestors. No original PCAP/payload is retained.

## Finite budgets and downstream interface

Defaults: 64 selected revisions total, 64 distinct collections, 50,000 accounted
normalization keys, 20,000 finding records, 50,000 protocol records, 200,000 source
references, 32 MiB published report, 128 native evaluations and 2,000,000 comparison
work units. Configurable API limits may narrow these ceilings only. Native graph
work is additionally bounded by the existing native resource contract and the
remaining comparison budget. Existing 256 MiB workspace / 64 MiB object / JSON
depth 64 / 2,000,000-node lifecycle bounds remain unchanged. Finite canonical and
intermediate structures are accounted; budgets are not guaranteed resident-memory
or latency promises. Failures publish no successful report.

V14-04 can consume `inspect_report` / `verify_report` and the exact domain records,
comparability matrix, identities, bounded source references, counts and abstentions.
It must preserve current-versus-recorded approval and unchanged-versus-difference
distinctions. No historical HTML Explorer, live monitoring, automatic trend/incident
detection, active OT traffic, new decoder or external service is implemented here.
