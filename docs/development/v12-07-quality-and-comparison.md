# V12-07 quality and architecture comparison contracts

Development version remains `1.2.0.dev0`; native schema 1 and existing trace,
intent, exposure and `compare` semantics remain unchanged. The additive commands
are `quality` and `compare-architecture`. Both are read-only and offline.

## ADR V12-07A — Assessment semantics

Quality contract 1 assesses declarations, retained documentary evidence and
explicit requirements. It makes no deployed-network, vulnerability, physical
completeness, global segmentation or conformity claim. There is no security score.
Missing documentary support is not evidence that a device is absent or insecure.

Each finding has a stable semantic ID, rule/version, domain, entity/scope,
model/provenance binding, expected and observed conditions, explanation, owner
action, review priority, limitations and exact selected source references.
Domains are STRUCTURAL, DOCUMENTARY, RECONCILIATION, REQUIREMENT_BACKED and
ANALYTICAL. States include SATISFIED, MISSING_REQUIRED_INFORMATION,
REVIEW_REQUIRED, NOT_ASSESSED and NOT_APPLICABLE. The contract reserves
CONTRADICTORY_EVIDENCE, NOT_DOCUMENTED and UNSUPPORTED for future objective rules;
it does not manufacture findings merely to exercise every taxonomy value.

Built-ins report native validation, provenance availability, absent requirement
scope, retained parser diagnostics, resolved conflicts, rejected/evidence-only
alternatives and availability of actual requested exact queries. Diagnostics are
review context, not a blanket security failure. A retained contradictory source
group whose valid final owner resolution is verified is SATISFIED for the
resolution check; its observations and rationale remain visible. Final rejected
alternatives are not unresolved errors.

Only accepted project provenance is supported. Unresolved or stale review fails
the shared retained-review verifier instead of producing a normal partial report.
Unreviewed Import Project drafts remain in Import Studio's existing workflow.
Invalid native input, malformed controls and incompatible sidecars are execution
errors (CLI exit 2), never normal negative analytical findings.

## ADR V12-07B — Explicit requirements and coverage

Quality profile 1 is strict JSON with exactly `profile_version: 1`,
`model_sha256`, nonempty `context`, optional `requirements`, external
`information` and explicit `queries`. It is bound to the validated normalized
model identity, not raw YAML formatting. Unknown fields, duplicate keys, boolean
versions and noncanonical hashes fail closed.

A requirement has a distinct `id`, `expectation`, native `entity_kind`, exact
`entity_ids` or the sole wildcard `["*"]`, optional `field`/`expected_value`, and
a nonblank `rationale`. Supported expectations:

| Expectation | Evidence needed to satisfy it |
| --- | --- |
| DECLARED_VALUE | Existing native field is present and not empty, unassessed or unspecified; an explicit string expected value instead requires exact equality |
| FIELD_PROVENANCE | Located documentary field selected by the confirmed partition; literal corrections, reference corrections and profile constants do not supply documentary support |
| ENTITY_PROVENANCE | At least one such selected documentary field supports the entity |
| SOURCE_AVAILABLE | Explicit registered source ID is present in matching verified provenance; wildcard is forbidden |
| OWNER_INFORMATION | External model-bound note for exact entity/field with value, reviewer and rationale; optional exact string value |

Only existing native fields may be required by DECLARED_VALUE/FIELD_PROVENANCE.
Description/ownership metadata absent from native schema belongs in external
OWNER_INFORMATION, never an invented native field. Profiles do not authorize
traffic or mutate models. Native IDs and labels are not fuzzy selectors.

Coverage records retain the complete requirement scope, satisfied numerator,
required denominator and exclusions (currently empty). Required but unavailable
evidence remains in the denominator. An empty selected native collection has
NOT_APPLICABLE coverage and denominator zero. Without a profile, completeness is
NOT_ASSESSED and no percentage is invented. Different profile contexts,
requirements, external notes or requested analyses invalidate cross-version
quality comparability. Stopping a rule never resolves a finding.

## ADR V12-07C — Exact native and documentary changes

Comparison contract 1 binds both ordered model hashes, optional independently
verified provenance hashes, mapping and analysis options, rule version, stable
change IDs and complete canonical before/after values. Native collection indexes
and field classifications reuse `comparison.declaration_catalogs` and
`comparison.declaration_fields`, the same canonical helpers as existing analysis.
No second validator or reachability engine exists.

All supported native collections are compared: assets, zones, interfaces,
conduits, transport/forwarding edges, rules, services, intents, scenarios, access
points, dependencies, SUC and snapshot metadata. Exact zone membership changes
are represented by asset `zone_id` changes, interface reassignment by `asset_id`,
and placement by `placement_zone_id`. Raw references remain unchanged by mapping;
their before/after differences are visible. Renames have explicit correspondence
and changed ID fields, not a guessed physical identity.

Equal canonical IDs mean declared continuity by default. This is a documented
owner assumption, not identity proof. Labels, IPs and similar attributes never
merge entities. Mapping version 1 binds both ordered models and permits reasoned
one-to-one `correspondences` (`entity_kind`, `baseline_id`, `proposed_id`,
`rationale`). Unknown IDs, duplicate sources/targets, ambiguous displaced stable
IDs, stale bindings and conflicting mappings fail. A complete explicit swap can
establish correspondence. Splits/merges remain unmatched add/remove records.
`reused_identifiers` explicitly breaks same-ID continuity and produces separate
removed/added records. Mappings never rewrite either model or query.

Documentary changes are assessed only when both sidecars are supplied and verified.
Source registration IDs qualify all locations. Source bytes/metadata, retained
candidate identities, document structural locations, graph scope/element IDs,
connectors, conflicts, owner partitions, field selections/corrections and
acknowledgments have separate change records. Content-dependent candidate IDs can
produce remove/add records after a changed observation; no undocumented relocation
or equivalence is inferred. Document observations use exact retained structural
locations, not text similarity. Reusing a source registration means that declared
document slot is being revised; hashes still do not authenticate authorship.

A changed source digest is not a changed native declaration. A new drawn connector
is DOCUMENTARY, never native transport or analytical permission. A different owner
selection can leave the native value unchanged. Missing provenance on either side
is NOT_ASSESSED, not an invented source-addition/removal history.

## ADR V12-07D — Exact analytical precision

Repeatable `--trace SOURCE_ASSET:SERVICE` explicitly selects at most 16 queries.
Quality profiles may also explicitly request trace queries. The unchanged
`trace_architecture` adapter invokes the existing ReachabilityEngine for each
model; arbitrary saved analytical artifacts are never accepted as proof.

Each side retains its exact query scope, model hash, TCP/UDP port intervals,
witnesses, negative frontier diagnostics and resource ceilings. Comparable trace
scopes must match source, destination, bound interface, service, protocol and
normalized requested port union. Port intervals are overlaid by their exact
boundaries; ports are not enumerated and queries are not extrapolated.

Interval states are UNCHANGED_EVALUATED_RESULT,
NEWLY_ALLOWED_FOR_EVALUATED_QUERY, NO_LONGER_ALLOWED_FOR_EVALUATED_QUERY or
CHANGED_EXPLANATION. Changed binding, missing endpoint, declared identifier reuse,
changed correspondence or different SUC identity prevents comparative connectivity
claims. Native unsupported self-only queries are retained as unavailable with
NOT_COMPARABLE reasons. Other native errors stop the report. No explicit queries
means NOT_EVALUATED, never DENIED. Two actual negative results are not physical
network isolation proof. Separate TCP and UDP oracles verify both transports.

## ADR V12-07E — Compact offline presentation

The existing SiteWriter, semantic page identities, hash-bucket compaction,
escaping, CSP, stylesheet, SVG renderer and independent link/resource audit are
reused. There is no frontend framework, JavaScript, server or external resource.
Baseline/proposed declaration indexes share grouped record pages. Changes, findings
and exact analyses retain full semantic anchors. Indexes contain 60 rows per page;
details are bounded per entity. Both native diagrams have captions and complete
textual alternatives. Larger models use the existing summary diagram mode.

The overview separates native, documentary, owner-decision, quality and analytical
views. Before/after field tables, descriptive navigation, state text, +/−/Δ and
letter labels provide non-color meanings. Existing focus styling, skip links,
semantic tables, scroll-region focusability and responsive layout remain.
Removed means removed from the proposed model, not from the plant.

`quality MODEL` prints canonical machine JSON without generating a site.
`--output NEW` additionally publishes human HTML, `review.json`, local CSS and
manifest as one fresh directory. `compare-architecture` requires `--output NEW`.
Publication stages next to the destination, audits every link/fragment and then
renames once. Existing destinations, linked paths and partial publication fail.
There is no unconditional filesystem retry or concurrent-writer guarantee.

These are sensitive full-detail local engineering reports. Paths entered as source
text are withheld in HTML by the established display filter; canonical machine
records preserve selected supplied content and may contain sensitive declarations.
No environment paths or generation timestamps are inserted into canonical reports.
This is not a public-safe export or universal secret scanner.

The actual `file://` browser attempt was rejected by the browser URL policy.
No loopback or alternate surface was used. Keyboard, zoom, visual CSS/CSP behavior,
console/network panels and assistive technology remain unverified. Static checks
are not WCAG certification. Manual acceptance: open original `index.html`, verify
local CSS; follow before/after, changed-field, source-reference and query links;
Tab through skip/navigation/scroll regions; verify visible focus at 200% zoom and
narrow width; inspect console/network and review with assistive technology.

## ADR V12-07F — Integration and real hosted evidence

Initial branch/HEAD and public-source identity exactly matched accepted V12-06.
Read-only `git ls-remote --heads origin` found no `v1.2`; all remote heads matched
cached refs. Local `v1.2` is rooted at accepted V12-06, and the feature branch is
`codex/v12-07-quality-comparison`. This is an integration proposal, not publication
authorization. The GitHub connector requires reauthentication. Before any first
push, disclose every newly reachable commit and changed historical path, audit
their contents, obtain explicit operational authorization and recheck remote heads.
Do not overwrite divergent owner work. One PR targets `v1.2`; no retrospective PRs.

CI preserves Windows/Ubuntu/macOS × Python 3.12/3.14, full installed-wheel tests,
focused installed-sdist tests, actual module hashes, native console, offline runtime
guard, dependency consistency, lint/type checks and archive audits. It adds the
quality/comparison walkthrough, benchmark, tests, exact tested Git revision,
PR head, run ID/attempt and canonical public-source identity. On pull_request,
tested_commit may be GitHub's merge commit; pr_head is recorded separately.

Permissions are contents:read, checkout credentials are not persisted, no
pull_request_target exists, dependencies retain the approved pinned provisioning
list and actions retain the repository's exact-version policy. Artifacts contain
only synthetic walkthrough/integrity evidence. PR code receives no owner secrets
from these workflows. Dependency provisioning may use the network; runtime model,
document and analytical tests run under the existing active socket/DNS/HTTP guard.
EXPECTED_ROOT_SHA remains an owner-configured governance prerequisite. No branch
protection settings are changed.

YAML does not prove execution. PR, six hosted cells, owner review and merge remain
pending until supported by real run/review references. No auto-merge, main merge,
release tag, GitHub release, PyPI upload or live industrial testing is authorized.
The final v1.2 release candidate must rerun the whole matrix independently.

## ADR V12-07G — Bounds, determinism and measurement

Controls: 2 MiB UTF-8 JSON, depth 16, 10,000 array records, 100,000 scalars,
4,096-character text, 1,000 requirements, 2,000 external notes, 2,000 mapping pairs
and reused-ID entries each, and 16 exact queries. Existing native and project
sidecar bounds apply before assessment. Findings/changes: at most 24,000 each,
24 MiB accumulated record bytes, 32 MiB final machine report. Visual JSON gets
that same 32 MiB ceiling; HTML remains 1 MiB/page and all output 256 MiB/24,000
files. A single oversized record fails; there is no silent truncation.

Model/source indexes and selected-field support indexes avoid pairwise matching
and repeated full provenance hashing. No automatic all-pairs reachability is run.
Canonical JSON uses sorted keys and ASCII escapes, without timestamps or absolute
generation paths. IDs use full SHA-256 semantic payloads. Comparison identity binds
both input identities, options and resulting exact records. Changing profile scope
invalidates comparability; reversed comparisons reverse the exact structural values.

`python -m benchmarks.quality_comparison --output NEW.json` uses the accepted
20/150/500-asset complexity (30/200/600 interfaces, 40/250/750 documentary connectors,
3/5/6 sources). One interface revision exercises native, source, candidate and
decision differences without invented communication. Three real timed comparison
samples, independent traced-allocation samples, generation/validation/render/audit
timings, rule/finding/change/query counts, file/byte/link inventories and repeated
byte checks are recorded. The existing single-model Explorer is measured on the
same baseline to detect regression. Timing is observational, not a linearity claim.
The benchmark intentionally evaluates zero traffic queries; the separate tutorial
and oracle tests evaluate exact traffic. Frozen acceptance contains actual results.
