# Gate V11-5 public contract inventory

Review snapshot of accepted main `8c6d46dd0dea127044232d2b44e6bd11d2af3f53`.
Derived from source, native commands and existing documentation. This inventory
does not supersede [schema 1](../yaml-schema-v1.md), [report version 1](../reporting.md)
or [trace version 1](../trace.md). Application/engine version remains 1.0.1.
Private helpers and importable implementation classes acquire no support promise
merely by appearing in source. Changes require the compatibility classification
in [the gate dossier](gate-v11-5.md).

## Native interface

All commands accept `--help`. Root accepts `--version` (prints `1.0.1` plus newline).
Paths are local filesystem paths; no stdin, URL or discovery input is supported.

| Command | Positionals | Scope options | Completion |
| --- | --- | --- | --- |
| validate | architecture | none | 0 for structural validity |
| check | architecture | none; all declared intents | 0 all pass, 1 failed intents |
| exposure | architecture | required `--scenario ID` | 0/1 according to independent intents |
| compare | baseline, proposed | `--scenario ID` OR both repeatable `--origin ID` and `--service ID` | 0/1 according to comparison intent outcomes |
| trace | architecture | required `--source ID`, `--service ID`; optional `--destination ID` equality assertion; `--policy-evidence` default false | 0 for completed reachable, mixed or unreachable |

Every command supports optional `--report PATH` and `--report-format html|json`
(default html, independent of extension). The first four accept repeatable
`--zone-order ID` only with an HTML report; trace does not accept zone order.
Trace rejects explicit report format without a report; legacy commands accept
and ignore it when no report is requested. Compare rejects missing/ambiguous
scope combinations. Scalar options retain Typer's last-occurrence behavior;
list options append and domain scope validation rejects duplicate identities.
Empty IDs are invalid domain values. Unknown options, absent required options,
missing values and invalid report enums exit 2. Trace parser errors emit one
structured INVALID_VALUE diagnostic; legacy parser errors use native Typer usage
stderr, which is not a JSON diagnostic. This distinction is accepted behavior.

Successful stdout is sorted-key ASCII-escaped JSON plus newline; trace uses
two-space indentation. Validation emits status, schema_version, engine_version,
model_sha256 and scope. Check/exposure/compare add versions to their dataclass
payloads below. Optional reports leave stdout unchanged. Fatal failures emit no
successful stdout and exit 2, preserving an existing report.

| Failure | Category | Code / structure |
| --- | --- | --- |
| Invalid shape/reference/text | invalid_input | precise codes from source list below |
| Unsupported declaration/query | unsupported_model | UNSUPPORTED_* |
| Prospective/actual ceiling | resource_limit | LIMIT_EXCEEDED |
| Input read | io_error | READ_ERROR |
| Report collision/write/replace | io_error | REPORT_IO_ERROR |
| Unexpected execution/renderer/serializer exception | execution_error | INTERNAL_ERROR; fixed sanitized message |
| Native parser misuse | trace: invalid_input; legacy: native usage | trace INVALID_VALUE; legacy Typer text |

ModelError diagnostics are ordered by (location, code); each stderr line has
category, code, location, message, nullable line and column. API expected errors
raise ModelError with a sorted diagnostics tuple; unexpected programming/I/O
exceptions outside translated boundaries may propagate. APIs do not promise
the CLI's catch-all execution translation.

## Python entry points

Trace, summaries and policy-evidence signatures are explicitly documented in
trace.md. The validation and analytical adapters are established typed module
interfaces exercised by the public suite; report helpers are the existing module
interface described by reporting.md. `normalization` serialization and raw flow
observations are supporting interfaces used by existing verification/performance
documentation. None is re-exported from package root, which exposes __version__.
The signatures below are transcribed from accepted source, including positional
limits and keyword-only parameters; they create no new API.

File adapters accept Path, bytes adapters accept bytes, architecture adapters
accept completed ValidatedArchitecture. Prevalidated calls trust that boundary;
they do not revalidate arbitrary forged dataclasses. Limits apply to each new
validation/evaluation; snapshots retain their original immutable bytes/hash.

### otarchguard.api

```text
def validate_bytes(data: bytes, limits: ResourceLimits=RESOURCE_LIMITS) -> ValidatedArchitecture
def validate_file(path: Path, limits: ResourceLimits=RESOURCE_LIMITS) -> ValidatedArchitecture
```

### otarchguard.intents

```text
def check_architecture(validated: ValidatedArchitecture, limits: ResourceLimits=RESOURCE_LIMITS) -> CheckResult
def check_file(path: Path, limits: ResourceLimits=RESOURCE_LIMITS) -> CheckResult
def check_bytes(data: bytes, limits: ResourceLimits=RESOURCE_LIMITS) -> CheckResult
```

### otarchguard.exposure

```text
def exposure_architecture(validated: ValidatedArchitecture, scenario_id: str, limits: ResourceLimits=RESOURCE_LIMITS) -> ExposureResult
def exposure_file(path: Path, scenario_id: str, limits: ResourceLimits=RESOURCE_LIMITS) -> ExposureResult
def exposure_bytes(data: bytes, scenario_id: str, limits: ResourceLimits=RESOURCE_LIMITS) -> ExposureResult
```

### otarchguard.comparison

```text
def compare_architectures(baseline: ValidatedArchitecture, proposed: ValidatedArchitecture, scenario_id: str | None=None, *, scope: QueryScope | None=None, limits: ResourceLimits=RESOURCE_LIMITS) -> ComparisonResult
def compare_files(baseline: Path, proposed: Path, scenario_id: str | None=None, *, scope: QueryScope | None=None, limits: ResourceLimits=RESOURCE_LIMITS) -> ComparisonResult
def compare_bytes(baseline: bytes, proposed: bytes, scenario_id: str | None=None, *, scope: QueryScope | None=None, limits: ResourceLimits=RESOURCE_LIMITS) -> ComparisonResult
```

### otarchguard.trace

```text
def trace_architecture(validated: ValidatedArchitecture, source_asset_id: str, service_id: str, limits: ResourceLimits=RESOURCE_LIMITS, *, destination_asset_id: str | None=None, policy_evidence: bool=False) -> TraceResult
def trace_bytes(data: bytes, source_asset_id: str, service_id: str, limits: ResourceLimits=RESOURCE_LIMITS, *, destination_asset_id: str | None=None, policy_evidence: bool=False) -> TraceResult
def trace_file(path: Path, source_asset_id: str, service_id: str, limits: ResourceLimits=RESOURCE_LIMITS, *, destination_asset_id: str | None=None, policy_evidence: bool=False) -> TraceResult
```

### otarchguard.reporting

```text
def json_report(report: dict[str, Any]) -> bytes
def build_report(kind: ReportKind, snapshots: tuple[ValidatedArchitecture, ...], result: Analysis=None, *, limits: ResourceLimits=RESOURCE_LIMITS) -> dict[str, Any]
def architecture_svg(snapshot: ValidatedArchitecture, *, zone_order: tuple[str, ...]=()) -> str
def html_report(report: dict[str, Any], snapshots: tuple[ValidatedArchitecture, ...], *, zone_order: tuple[str, ...]=(), analysis: Analysis=None) -> bytes
def write_report(path: Path, data: bytes, inputs: tuple[Path, ...]) -> None
```

### otarchguard.trace_reporting

```text
def trace_json(result: TraceResult) -> bytes
def trace_html(result: TraceResult) -> bytes
```

### otarchguard.normalization

```text
def canonical_bytes(snapshot: ArchitectureSnapshot) -> bytes
def model_hash(snapshot: ArchitectureSnapshot) -> str
```

### otarchguard.policy_evidence

```text
def policy_evidence_for_query(engine: ReachabilityEngine, query: QueryResult) -> PolicyEvidence
```

The documented policy-evidence helper requires the existing run-local engine.
Its constructor and query/replay methods are supporting typed interfaces:

```text
ReachabilityEngine(validated: ValidatedArchitecture, service_ids: frozenset[str] | None = None, limits: ResourceLimits = RESOURCE_LIMITS, *, partition_peers: tuple[ArchitectureSnapshot, ...] = ())
ReachabilityEngine.evaluate(source_asset_id: str, service_id: str) -> QueryResult
ReachabilityEngine.replay(witness: Witness) -> bool
evaluate_query(validated: ValidatedArchitecture, source_asset_id: str, service_id: str, limits: ResourceLimits = RESOURCE_LIMITS) -> QueryResult
```

The engine's mutable reservation/counter state belongs to one run. Its internal
search/cache attributes and `ensure_capacity` implementation method are not new
extension APIs. Loading returns YAML primitives; parsing, graph construction,
partitioning and compiler helpers are lower-level implementation boundaries,
not substitutes for the documented completed-validation entry points.

### otarchguard.summaries

```text
def summarize_exposure(validated: ValidatedArchitecture, result: ExposureResult, *, noncomparable_service_ids: tuple[str, ...]=()) -> FiniteScopeSummary
def explain_comparison(result: ComparisonResult) -> ObservedChangeExplanation
```

### otarchguard.flows

```text
def observations(queries: tuple[QueryResult, ...], reachable: bool=True) -> tuple[FlowInterval, ...]
```

## Typed result and work inventory

The following are existing returned records and supporting work/resource types.
Field order is recorded for review; JSON keys are sorted by serializers. Tuple
order remains meaningful: canonical entity IDs, exact port intervals, deterministic
BFS witness steps, bounded diagnostic frontier and sorted matching rule identities.
Work counts actual operations; prospective reservations are separate admission
bounds. Query atoms are interval records, not concrete port counts. Evidence work
is additional and never changes trace query work. Mutable Work is run-local,
not an immutable analysis result or a general public extension mechanism.

| Module.type | Fields in declaration order |
| --- | --- |
| api.ValidatedArchitecture | `model: ArchitectureSnapshot, canonical_json: bytes, sha256: str` |
| intents.IntentResult | `id: str, kind: str, passed: bool, queries: tuple[QueryResult, ...]` |
| intents.CheckResult | `snapshot_sha256: str, passed: bool, intents: tuple[IntentResult, ...], failed_intent_count: int, failed_interval_count: int, atom_queries: int, state_edge_visits: int, edge_rule_atom_checks: int, scope: str` |
| exposure.QueryScope | `origin_asset_ids: tuple[str, ...], destination_service_ids: tuple[str, ...]` |
| exposure.AssetExposure | `asset_id: str, criticality: str` |
| exposure.ExposureResult | `snapshot_sha256: str, suc_id: str, scenario_id: str | None, query_scope: QueryScope, unavailable_origin_asset_ids: tuple[str, ...], unavailable_destination_service_ids: tuple[str, ...], observations: tuple[FlowInterval, ...], destination_assets: tuple[AssetExposure, ...], queries: tuple[QueryResult, ...], intent_checks: CheckResult, passed: bool, atom_queries: int, state_edge_visits: int, edge_rule_atom_checks: int, completeness_assertion: str, interpretation: str` |
| comparison.InventoryChange | `entity_kind: str, added_ids: tuple[str, ...], removed_ids: tuple[str, ...]` |
| comparison.FieldChange | `field: str, classification: str, baseline: YamlValue, proposed: YamlValue` |
| comparison.EntityChange | `entity_kind: str, id: str, fields: tuple[FieldChange, ...]` |
| comparison.ComparedAsset | `asset_id: str, baseline_criticality: str, proposed_criticality: str` |
| comparison.IntentComparison | `id: str, classification: str, baseline_passed: bool | None, proposed_passed: bool | None, introduced_failures: tuple[FlowInterval, ...], resolved_failures: tuple[FlowInterval, ...], persisting_failures: tuple[FlowInterval, ...]` |
| comparison.IntentFlowChange | `intent_id: str, flow: FlowInterval` |
| comparison.ComparisonResult | `suc_id: str, scenario_id: str | None, query_scope: QueryScope, baseline: ExposureResult, proposed: ExposureResult, comparable_service_ids: tuple[str, ...], noncomparable_service_ids: tuple[str, ...], newly_reachable: tuple[FlowInterval, ...], no_longer_reachable: tuple[FlowInterval, ...], newly_reachable_assets: tuple[ComparedAsset, ...], no_longer_reachable_assets: tuple[ComparedAsset, ...], inventory_changes: tuple[InventoryChange, ...], entity_changes: tuple[EntityChange, ...], suc_definition_changes: tuple[FieldChange, ...], intent_changes: tuple[IntentComparison, ...], broken_required_communications: tuple[IntentFlowChange, ...], introduced_prohibited_violations: tuple[IntentFlowChange, ...], resolved_prohibited_violations: tuple[IntentFlowChange, ...], passed: bool, interpretation: str` |
| graph.State | `interface_id: str, phase: Literal['egress', 'ingress']` |
| reachability.Endpoint | `state: State, asset_id: str, placement_zone_id: str, ipv4: str` |
| reachability.WitnessStep | `edge_id: str, kind: str, source: Endpoint, target: Endpoint, conduit_id: str | None, allow_rule_ids: tuple[str, ...]` |
| reachability.Witness | `snapshot_sha256: str, source_asset_id: str, destination_asset_id: str, service_id: str, protocol: ProtocolValue, start: int, end: int, steps: tuple[WitnessStep, ...]` |
| reachability.BlockedEdge | `edge_id: str, reason: str, allow_rule_ids: tuple[str, ...], deny_rule_ids: tuple[str, ...]` |
| reachability.UnreachableDiagnostics | `reason: str, structural_path_exists: bool, blocked_edges: tuple[BlockedEdge, ...], blocked_edge_count: int, truncated: bool, limitation: str` |
| reachability.IntervalResult | `start: int, end: int, reachable: bool, witness: Witness | None, diagnostics: UnreachableDiagnostics | None` |
| reachability.QueryResult | `source_asset_id: str, destination_asset_id: str, service_id: str, protocol: ProtocolValue, intervals: tuple[IntervalResult, ...]` |
| flows.FlowInterval | `source_asset_id: str, destination_asset_id: str, service_id: str, protocol: ProtocolValue, start: int, end: int` |
| policy.Work | `limits: ResourceLimits, state_edge_visits: int, edge_rule_atom_checks: int` |
| policy_evidence.PolicyScope | `source_asset_id: str, destination_asset_id: str, service_id: str, protocol: ProtocolValue, destination_ports: tuple[tuple[int, int], ...], examined_edge_ids: tuple[str, ...], examined_rule_ids: tuple[str, ...], rule_edge_associations: int, resource_ceilings: ResourceLimits` |
| policy_evidence.MatchingDomain | `edge_ids: tuple[str, ...], destination_ports: tuple[tuple[int, int], ...]` |
| policy_evidence.ScopedDuplicateEffect | `effect: str, rule_ids: tuple[str, ...], matching_domain: MatchingDomain, kind: Literal['scoped_duplicate_effect']` |
| policy_evidence.AllowDenyOverlap | `edge_id: str, source_asset_id: str, destination_asset_id: str, protocol: ProtocolValue, start: int, end: int, allow_rule_ids: tuple[str, ...], deny_rule_ids: tuple[str, ...], effective_decision: Literal['explicit_deny']` |
| policy_evidence.PolicyEvidenceWork | `edge_atom_evaluations: int, edge_rule_atom_checks: int, planned_edge_atom_evaluations: int, planned_edge_rule_atom_checks: int` |
| policy_evidence.PolicyEvidence | `scope: PolicyScope, scoped_duplicate_effects: tuple[ScopedDuplicateEffect, ...], allow_deny_overlaps: tuple[AllowDenyOverlap, ...], no_match_in_scope_rule_ids: tuple[str, ...], work: PolicyEvidenceWork, status: Literal['complete'], limitation: str` |
| trace.TracePortInterval | `start: int, end: int` |
| trace.TraceScope | `source_asset_id: str, destination_asset_id: str, destination_interface_id: str, service_id: str, protocol: ProtocolValue, destination_ports: tuple[TracePortInterval, ...]` |
| trace.TraceInterval | `start: int, end: int, protocol: ProtocolValue, reachable: bool, witness: Witness | None, diagnostics: UnreachableDiagnostics | None` |
| trace.TraceWork | `query_atoms: int, state_edge_visits: int, edge_rule_atom_checks: int` |
| trace.PolicyNotRequested | `status: Literal['not_requested']` |
| trace.TraceResult | `scope: TraceScope, intervals: tuple[TraceInterval, ...], model_sha256: str, work: TraceWork, resource_ceilings: ResourceLimits, policy_evidence: PolicyNotRequested | PolicyEvidence, trace_version: Literal[1], engine_version: str, schema_version: Literal[1], status: Literal['complete'], intents_assessed: Literal[False], interpretation: str` |
| summaries.PairCoverage | `source_asset_id: str, service_id: str, destination_asset_id: str, protocol: ProtocolValue, evaluated_ports: tuple[tuple[int, int], ...], exact_interval_records: int, reachable_interval_records: int, unreachable_interval_records: int` |
| summaries.CommunicationTuple | `source_asset_id: str, destination_asset_id: str, service_id: str, protocol: ProtocolValue, source_owner_zone_id: str, destination_owner_zone_id: str, reachable_ports: tuple[tuple[int, int], ...]` |
| summaries.FiniteScopeSummary | `snapshot_sha256: str, query_scope: QueryScope, evaluated_query_pairs: int, evaluated_exact_interval_records: int, reachable_exact_interval_records: int, unreachable_exact_interval_records: int, evaluated_destination_ports_across_pairs: int, reachable_destination_ports_across_pairs: int, distinct_reachable_destination_asset_ids: tuple[str, ...], pair_coverage: tuple[PairCoverage, ...], reachable_communication_tuples: tuple[CommunicationTuple, ...], cross_owner_zone_tuples: tuple[CommunicationTuple, ...], unavailable_origin_asset_ids: tuple[str, ...], unavailable_service_ids: tuple[str, ...], noncomparable_service_ids: tuple[str, ...], excluded_self_asset_pairs: tuple[tuple[str, str], ...], unevaluated_present_query_pairs: int, outside_scope_pair_count: None, limitation: str` |
| summaries.DeclarationChangeReference | `entity_kind: str, entity_id: str, change: str, fields: tuple[str, ...]` |
| summaries.ObservedChangeExplanation | `declaration_changes: tuple[DeclarationChangeReference, ...], newly_reachable_interval_records: int, no_longer_reachable_interval_records: int, source_service_tuples_gaining_ports: int, source_service_tuples_losing_ports: int, newly_reachable_source_service_pairs: int, no_longer_reachable_source_service_pairs: int, newly_reachable_destination_assets: int, no_longer_reachable_destination_assets: int, noncomparable_service_ids: tuple[str, ...], interpretation: str` |
| diagnostics.Diagnostic | `category: DiagnosticCategory, code: str, location: str, message: str, line: int | None, column: int | None` |
| contract.ResourceLimits | `input_bytes: int, nesting_depth: int, parser_events: int, assets: int, interfaces: int, edges: int, rules: int, services: int, zones: int, conduits: int, access_points: int, dependencies: int, protocol_port_atoms: int, state_edge_visits: int, edge_rule_associations: int, edge_rule_atom_checks: int, diagnostic_edges_per_query: int` |

## Structured outputs and ordering

Legacy envelopes contain exactly report_version, engine_version, schema_version,
kind, status, scope, limitations, security_level_evidence, resource_ceilings,
snapshots, result. Snapshot roles are architecture or ordered baseline/proposed;
each includes model_sha256, full canonical model and diagram summary. Result is
null for validation, otherwise the typed analysis above. Trace has its separately
documented exact version-1 envelope and discriminated policy_evidence status.
Never substitute Boolean equivalence for byte compatibility.

Normalization sorts ID-bearing declarations and selector collections, coalesces
port unions and preserves free text. Canonical model JSON is sorted, literal UTF-8,
compact and hashed by SHA-256; reports use ASCII escaping, sorted keys, indentation and LF.
Reports contain no timestamps or source paths. Witnesses select deterministic BFS
routes through declared interface states. Collection semantics and normative
schema defaults remain in yaml-schema-v1.md; frozen ceilings are defined once in
contract.ResourceLimits and reproduced in report resource_ceilings.

Diagnostic code vocabulary found in constant fail/Diagnostic arguments (not a
promise that every code is possible on every entry point):

`CONTRADICTORY_INTENTS`, `DUPLICATE_ADDRESS`, `DUPLICATE_ID`, `DUPLICATE_ITEM`, `DUPLICATE_KEY`, `EMPTY_QUERY_SCOPE`, `INTERNAL_ERROR`, `INVALID_ACCESS_POINT`, `INVALID_ADDRESS`, `INVALID_CONDUIT_PAIR`, `INVALID_DEPENDENCY`, `INVALID_EDGE`, `INVALID_ID`, `INVALID_PLACEMENT`, `INVALID_PORT`, `INVALID_REFERENCE`, `INVALID_SELECTOR`, `INVALID_SERVICE_BINDING`, `INVALID_TEXT`, `INVALID_VALUE`, `LIMIT_EXCEEDED`, `MISSING_FIELD`, `MISSING_REFERENCE`, `MULTIPLE_DOCUMENTS`, `READ_ERROR`, `REPORT_IO_ERROR`, `SAFETY_INCONSISTENCY`, `SCOPE_MISMATCH`, `TYPE_MISMATCH`, `UNKNOWN_FIELD`, `UNSUPPORTED_ADDRESS_FAMILY`, `UNSUPPORTED_ADDRESS_KIND`, `UNSUPPORTED_CONDUIT`, `UNSUPPORTED_FEATURE`, `UNSUPPORTED_FORWARDING`, `UNSUPPORTED_OWNERSHIP`, `UNSUPPORTED_POLICY`, `UNSUPPORTED_PROTOCOL`, `UNSUPPORTED_QUERY`, `UNSUPPORTED_VERSION`, `YAML_FEATURE`, `YAML_SYNTAX`

## Distribution interface

| Item | Accepted definition |
| --- | --- |
| Distribution | otarchguard; authoritative metadata 1.0.1 |
| Console | otarchguard = otarchguard.cli:app |
| Python | requires-python >=3.12; native CI 3.12 and 3.14 |
| Build | setuptools>=77; setuptools.build_meta |
| Runtime | typer>=0.16,<1; PyYAML>=6,<7; pydantic>=2.12,<3 |
| Dev extra | pytest>=8,<10; types-PyYAML>=6,<7; ruff>=0.11,<1; mypy>=1.15,<2 |
| License | Apache-2.0; LICENSE and THIRD_PARTY_NOTICES.md |
| Wheel | otarchguard Python modules, dist-info metadata/entry point/licenses/RECORD; no runtime data files |
| Sdist | exact tools/public-files.txt allowlist plus accepted generated metadata; enforced by tools/audit_release.py |
| Public examples | segmented-plant, flat-plant, remote-support, trace and test fixtures |
| Public verification | tests, benchmarks, tools/verify_environment.py, tools/audit_release.py, offline audit hook, pinned verification requirements |

MANIFEST.in and tools/public-files.txt are the packaging authority, not this
snapshot's historical count of 112 files. Gate additions must be added to both.
No environments, private material, output, profiling logs or built archives belong
in the public payload. Development staging may use 1.0.1.dev5+gate.v11.5;
installed application/engine stays 1.0.1. Hosted six-way execution and any actual
release transition require subsequent owner authorization.
