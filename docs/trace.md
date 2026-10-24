# Exact communication trace

Development Explorer integration uses `otarchguard explore MODEL --output NEW
--trace SOURCE:SERVICE` (repeatable). It regenerates the same exact engine result,
retains model binding and port/transport/direction/negative-result qualifications,
and links the involved native entities. No query runs by default. See the
[offline tutorial](../examples/explorer/README.md). The trace API and standalone
report contracts below remain unchanged.

`otarchguard trace MODEL --source ASSET --service SERVICE` evaluates the complete
declared TCP/UDP destination-port union through the existing exact evaluator.
`--destination ASSET` asserts the service's binding; it cannot retarget it.
`--policy-evidence` requests finite policy diagnostics. `--report PATH` writes
offline HTML by default; `--report-format json` writes the same trace envelope as
stdout. An explicit report format requires a report path.

Exit 0 means a supported query completed, including unreachable or mixed results.
Exit 2 means invalid input, unsupported scope, resource exhaustion or execution/I/O
failure. Exit 1 is reserved for the existing independent intent commands.

## Version 1 contract

The independently versioned envelope has these required fields. There are no
optional top-level fields, timestamps, source paths or overall `passed` flag.

| Field | Type / meaning |
| --- | --- |
| trace_version | integer 1 |
| engine_version | application version string (1.1.0) |
| schema_version | integer 1 |
| status | literal `complete`; does not assert reachability |
| model_sha256 | canonical validated snapshot SHA-256 string |
| intents_assessed | literal false |
| scope | source_asset_id, destination_asset_id, destination_interface_id, service_id (strings), protocol (`tcp` or `udp`), destination_ports (ordered inclusive integer start/end records) |
| intervals | ordered exact evaluator atoms; start/end integers, protocol, reachable boolean, witness and diagnostics |
| policy_evidence | discriminated status: `not_requested` or `complete` |
| work | integer query_atoms, state_edge_visits, edge_rule_atom_checks for the trace evaluator alone |
| resource_ceilings | complete ResourceLimits record used for this run |
| interpretation | fixed scope/limitations text |

Each interval has `witness: null` if unreachable and `diagnostics: null` if
reachable. A witness retains the established Witness dataclass fields: snapshot
hash, original source/final destination/service IDs, protocol, start/end, ordered
steps. Each step retains edge ID, transport/forwarding kind, source/target
endpoints (state interface_id/phase, asset_id, placement_zone_id, IPv4), nullable
conduit_id, and ordered allow_rule_ids.

Unreachable diagnostics retain reason (`no_structural_path` or
`no_permitted_path`), structural_path_exists, blocked_edges (edge_id, reason
`explicit_deny`/`missing_permit`, allow_rule_ids, deny_rule_ids), actual
blocked_edge_count, truncated boolean, and limitation text. Frontier evidence is
bounded by diagnostic_edges_per_query; it establishes no unique root cause,
minimal cut or guaranteed fix. Even a structurally absent route can have observed
policy frontier entries; those entries do not change its structural classification.

The interval list exactly covers the declared service union without extra ports,
overlap or coalescing of evaluator atoms. A witness is one deterministic supported
initiation route. It proves neither uniqueness nor return traffic, authentication,
availability, deployed connectivity, application success, risk or conformity.
Invalid and unsupported queries produce ModelError, never an unreachable result.
Other source/service pairs and intents are unassessed by a trace.

JSON uses sorted keys, ASCII escaping, two-space indentation and LF termination.
HTML is static, escaped, deterministic, and has a complete JSON appendix. Reports
are atomically replaced only after successful evaluation and serialization.
No additional runtime dependency, protocol, schema field or resource ceiling is
introduced.

## Typed Python API

```python
from pathlib import Path
from otarchguard.trace import trace_architecture, trace_bytes, trace_file
from otarchguard.trace_reporting import trace_html, trace_json

result = trace_file(
    Path("model.yaml"), "eng", "svc_plc", destination_asset_id="plc", policy_evidence=True
)
json_bytes = trace_json(result)
html_bytes = trace_html(result)
```

All three functions take source_asset_id, service_id, optional positional
ResourceLimits, and keyword destination_asset_id (nullable) / policy_evidence
(boolean, default false). `trace_architecture` takes a completed
`api.ValidatedArchitecture` from the shared validation boundary. Bytes and file
entry points validate with the supplied limits. Expected errors are ModelError.
No presentation reread, cross-run cache or HTML rendering is needed for analysis.
The frozen typed TraceResult/TraceScope/TraceInterval/TraceWork records are defined
in `otarchguard.trace`; existing Witness and UnreachableDiagnostics are reused.

## Optional finite policy evidence

`not_requested` contains only status. A `complete` policy_evidence record has all
these required non-null fields:

- scope: original source_asset_id, destination_asset_id, service_id, protocol,
  destination_ports (inclusive integer pairs), examined_edge_ids,
  examined_rule_ids, rule_edge_associations, resource_ceilings.
- scoped_duplicate_effects: effect, ordered rule_ids, matching_domain (edge_ids
  and destination_ports inclusive pairs, representing their exact Cartesian
  product), kind=`scoped_duplicate_effect`. Only identical **nonempty** finite
  domains of the same effect are grouped. Matching spans may merge adjacent atoms
  within an edge because every exposed match field is identical.
- allow_deny_overlaps: edge_id, original source_asset_id, destination_asset_id,
  protocol, start, end, allow_rule_ids, deny_rule_ids, and effective_decision
  `explicit_deny`. These retain exact evaluator atoms.
- no_match_in_scope_rule_ids: ordered rule IDs with no predicate match anywhere
  in this diagnostic scope.
- work: actual and planned edge_atom_evaluations / edge_rule_atom_checks.
- status=`complete` and limitation text. Every finding inherits this exact scope.

The typed `policy_evidence_for_query(engine, query)` helper reuses compiled
predicates, atoms and associations on a run-local ReachabilityEngine. Supply a
completed result from that engine. All declared edges are examined, including
edges outside the selected witness; this is not alternate-path enumeration.
The helper debits the engine's shared counters and returns additional work
separately. Before expansion, combined conservative reserved query work (or
actual work, if larger) plus diagnostic work must fit unchanged visit/predicate
limits. No quadratic rule-pair or source/destination enumeration is performed.
Resource rejection is a fatal error, never a complete partial diagnosis.

Scoped duplicates and no-match findings establish no global redundancy, safe rule
removal, unchanged end-to-end reachability after removal or ordered shadowing.

## Completed-result summaries and comparison interpretation

`summaries.summarize_exposure(validated, result, *, noncomparable_service_ids=())`
returns frozen FiniteScopeSummary data, without further reachability evaluation.
It records snapshot identity, present query_scope, evaluated pair/interval/port
counts, distinct reachable destination IDs, PairCoverage and reachable
CommunicationTuple records (including administrative owning zones and inclusive
port pairs), cross_owner_zone_tuples, unavailable identities, noncomparable
services, excluded self pairs, and unevaluated_present_query_pairs.
`outside_scope_pair_count` is always null; no all-model evaluation is implied.
Counts explicitly state units. Concrete port counts sum across source/service
pairs; they are not counts of distinct assets or exact partition records.
Unavailable identities supplement the present scope; unassessed entities are not
assigned unreachable status. Criticality remains an owner annotation in the
existing exposure evidence.

`summaries.explain_comparison(result)` returns ObservedChangeExplanation:
declaration_changes references (entity_kind, entity_id, change, fields), exact
delta interval counts, source/service tuples gaining/losing ports, newly/no-longer
reachable source/service pair counts, newly/no-longer reachable destination asset
counts, noncomparable_service_ids, and conservative interpretation text.
Partial port changes can affect an already reachable pair; new pair access can
affect an already reachable asset. References describe co-occurring declaration
changes without attributing a unique cause or proposing remediation.

Native exposure/comparison HTML reports include these additive sections. Python
callers can supply `html_report(envelope, snapshots, analysis=completed_result)`
to include them; the typed result must match the envelope. Existing JSON
report-version-1 envelopes and analytical classifications are unchanged.

## V12-07 quality and architecture comparison

The additive `quality` and `compare-architecture` commands assess explicit
model-bound requirements and native/documentary/owner changes. Exact comparative
reachability comes only from explicit before/after native trace evaluation.
Missing evidence is not a vulnerability; changed scope never resolves a finding.
Selected evidence, external owner information and native declarations remain
separate. Split/merge and fuzzy identity inference are unsupported.
See the [seven ADRs](development/v12-07-quality-and-comparison.md) for versioned schemas,
coverage denominators, query comparability, resource ceilings, compact offline
views, installed-console tests, reproducible benchmarks and independent local,
PR, hosted-CI and owner-review acceptance. Actual file-URL browser interaction
was policy-blocked; static checks do not establish WCAG certification.
