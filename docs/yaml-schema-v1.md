# YAML schema v1

This is the implemented serialization contract. These are project software
contracts. See the [domain model](domain-model.md).

## Document and strict primitives

Use UTF-8, exactly one YAML document, with a mapping at its root. Only mappings
with string keys, sequences and the scalar types below are accepted. Reject
duplicate mapping keys, unknown fields at every level, YAML directives, explicit
tags, anchors, aliases, merge keys, extra documents and non-string mapping keys.
No external resolution, includes, plugins or object construction is permitted.
An optional `---` document-start and `...` end marker are allowed. Comments have
no semantic effect. Strings resembling numbers/booleans must be quoted.

Scalar resolution is fixed rather than inherited from a library default:
plain `true`/`false` are booleans; plain `null`/`~` or an empty scalar are null;
plain `-?(0|[1-9][0-9]*)` are integers; plain `true`, `false`, and `null` are
case-sensitive. Other plain scalars are strings except numeric float forms,
which are rejected. Float recognition uses a full match of
`[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|[-+]?[0-9]+[eE][-+]?[0-9]+`
or `[-+]?\.(?:inf|nan)` (case-insensitive for inf/nan only).
Legacy YAML 1.1 `yes`, `no`, `on`, `off` and dates remain strings; no octal,
hexadecimal, underscore-digit or sexagesimal numeric conversion is performed.
Use quoted strings for these forms when intended as text. Null is never a valid
field value. No type coercion or stripping of supplied text is permitted.

| Notation | Exact type / constraint |
| --- | --- |
| `id` | String matching the entire ASCII pattern `[a-z][a-z0-9_-]{0,63}`. Case-sensitive. |
| `text` | String containing at least one non-whitespace character. Preserved verbatim. |
| `int` | Integer scalar, excluding booleans, strings and floats. |
| `enum(...)` | String equal to exactly one listed lowercase value. |
| `list<T>` | YAML sequence of the stated type, including `[]` unless stated nonempty. No implicit scalar-to-list conversion. |
| `idset<T>` | Nonempty sequence of distinct IDs referencing entity kind T; order has no meaning. |
| `ports` | Nonempty sequence of mappings `{start: int, end: int}`. Both keys required; `1 <= start <= end <= 65535`. Singleton port uses equal bounds. |
| `selector` | Exactly one mapping form: `{asset_ids: idset<asset>}`, `{zone_ids: idset<zone>}`, or `{all_assets: true}`. Literal boolean true only. No other keys. |

Entity IDs are unique within each collection/kind. Transport and forwarding share
one **edge ID namespace** so rule/access-point edge references are unambiguous.
Access-point IDs and dependency IDs each have their own namespace within the
single SUC. Cross-kind reuse is permitted; all references are typed. Repeated
items in set-like lists are invalid, including identical repeated raw port
intervals. Distinct overlapping port intervals are accepted and their union is
normalized to disjoint intervals, merging adjacent intervals. The evaluator uses exact interval atoms, without individual-port expansion.

All fields listed below are required unless marked optional. Optional fields
are omitted, never null. No implicit defaults, omitted wildcard or additional
metadata keys exist. Record lists may be empty; the top-level zones/assets lists
must be nonempty. An inventory asset can have no interface, but any selected
origin asset must have at least one. No reachability is inferred from inventory.

## Root record

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | int, exactly `1` | Other integer versions are unsupported, wrong primitive types invalid. |
| `architecture_id` | id | Stable snapshot-family identity. |
| `revision` | text | Human metadata; not a content hash. |
| `suc` | SUC mapping below | Exactly one declared system under consideration. |
| `zones` | nonempty list<Zone> | Administrative groups. |
| `assets` | nonempty list<Asset> | Internal inventory and external context. |
| `interfaces` | list<Interface> | Explicit owned interfaces and placements. |
| `conduits` | list<Conduit> | Pairwise conceptual channel groups. |
| `transport_edges` | list<TransportEdge> | Directed inter-asset transfers. |
| `forwarding_edges` | list<ForwardingEdge> | Directed internal boundary-device transfers. |
| `services` | list<Service> | Explicit listener catalog. |
| `rules` | list<EnforcementRule> | Explicit per-edge permissions. |
| `intents` | list<CommunicationIntent> | Independent required/prohibited declarations. |
| `scenarios` | list<ExposureScenario> | Explicit finite query scopes. |

There are no result, comparison, security-level, approval-evidence, remote-file
or arbitrary extension fields. Separate comparison scope is a CLI/API concern,
not an architecture document field.

## SUC, access points and dependencies

| SUC field | Type |
| --- | --- |
| `id` | id |
| `name` | text |
| `purpose` | text; intended use |
| `controlled_process` | text |
| `boundary_description` | text |
| `completeness_assertion` | text; owner statement including known omissions |
| `access_points` | list<AccessPoint> |
| `external_dependencies` | list<ExternalDependency> |

AccessPoint is a discriminated mapping:

| Field | `kind: modeled_network` | `kind: unmodeled` |
| --- | --- | --- |
| `id` | id, required | id, required |
| `kind` | enum(modeled_network), required | enum(unmodeled), required |
| `description` | text, required | text, required |
| `external_interface_id` | id → Interface, required | forbidden |
| `internal_interface_id` | id → Interface, required | forbidden |
| `edge_ids` | idset<edge>, required | forbidden |

The external interface is placed in an external zone and the internal interface
in an internal zone. At least one of their owning assets is internal. Each edge
must connect that exact interface pair in either declared direction, respecting
its edge kind; reverse edges are never inferred. Every internal/external
placement crossing belongs to exactly one modeled access point. Same-scope
edges cannot be access-point members. An access point does not create an edge.
An internal firewall may own both interfaces; placement, not inventory scope,
defines the crossing. Unmodeled records have no path effect and remain unassessed.
Analysis depending on unsupported network semantics must stop, rather than
silently treating an unmodeled record as a supported transfer.

ExternalDependency has exactly:

| Field | Type |
| --- | --- |
| `id` | id |
| `description` | text |
| `external_asset_ids` | list<id → Asset>; distinct, possibly empty; every referenced asset external |
| `required_intent_ids` | list<id → Intent>; distinct, possibly empty; each referenced intent required |

An empty dependency list is an explicit declaration. A dependency can be
nonnetwork and have empty reference lists. It grants neither intent nor permission.
Completeness is a human assertion; consistency cannot prove real-world coverage.

## Zones, assets and interfaces

| Zone field | Type |
| --- | --- |
| `id`, `name` | id, text respectively |
| `purpose`, `grouping_rationale` | text each |
| `scope` | enum(internal, external) |
| `safety_designation` | enum(non_safety, safety, mixed_safety, unassessed) |
| `mixed_safety_rationale` | optional text; required when designation is mixed_safety; forbidden otherwise |

Safety checks use owned assets, never attached interfaces: known safety-related
and non-safety members require mixed_safety plus rationale. A non_safety zone
cannot own known safety-related assets; a safety zone cannot own known non-safety
assets. Any unknown safety member requires unassessed unless known mixed
membership already requires mixed_safety. Mixed_safety always requires rationale,
including when uncertainty remains, and documents the whole zone as safety-related.
For empty or otherwise homogeneous membership, the stated designation is retained
subject to these prohibitions; no automatic designation is inferred.
Business/IACS mixing is owner-review context, not a normative violation.

| Asset field | Type |
| --- | --- |
| `id`, `name`, `role` | id, text, text respectively; role is descriptive |
| `zone_id` | id → Zone; exactly one administrative owner |
| `kind` | enum(endpoint, boundary_device) |
| `scope` | enum(internal, external); equals owner-zone scope |
| `domain_classification` | enum(business, iacs, unassessed) |
| `safety_classification` | enum(safety_related, non_safety, unassessed) |
| `criticality` | enum(unspecified, low, medium, high, critical) |

| Interface field | Type |
| --- | --- |
| `id` | id |
| `asset_id` | id → Asset |
| `placement_zone_id` | id → Zone |
| `ipv4` | String: dotted-decimal IPv4 host address followed by `/` and decimal prefix length 0–32; no bare address, DNS name, integer mask or netmask notation |

IPv4 syntax follows Python's `ipaddress.IPv4Interface` with the additional
slash/decimal-prefix restriction above. Host bits are preserved, not masked into
a network address. Host addresses must be globally unique regardless of prefixes;
overlapping prefixes are allowed and grant no paths. Only IPv4 unicast is in
scope: multicast, unspecified, limited broadcast, loopback and subnet-directed
broadcast addresses are outside this model. A /31 permits both addresses and /32
permits its host. Documentation ranges are valid synthetic addresses. An endpoint's
interfaces must be placed in its owner zone. Boundary devices may attach to other
zones; placement does not change owner or classification.

## Pairwise conduits and explicit edges

| Conduit field | Type |
| --- | --- |
| `id`, `name`, `purpose`, `common_security_needs` | id, text, text, text respectively |
| `zone_ids` | Exactly two distinct id → Zone values, unordered |

Conduit membership is derived solely from edge references; there is no member
asset list, device ownership, transit-zone list or conduit permission.

| TransportEdge field | Type |
| --- | --- |
| `id` | id in shared edge namespace |
| `source_interface_id` | id → Interface; source egress |
| `destination_interface_id` | id → Interface; destination ingress on another asset |
| `conduit_id` | optional id → Conduit, conditional below |

| ForwardingEdge field | Type |
| --- | --- |
| `id` | id in shared edge namespace |
| `ingress_interface_id` | id → Interface |
| `egress_interface_id` | id → Interface; distinct interface of the same boundary_device |
| `conduit_id` | optional id → Conduit, conditional below |

For both edge kinds: different placement zones require conduit_id whose unordered
zone pair matches exactly; same placement prohibits conduit_id. Compare placements,
not asset owner zones. A mismatched pair, forwarding between assets, or forwarding
on an endpoint is invalid supported input. Same-interface hairpin forwarding is
unsupported. Parallel edges with different IDs are permitted. No edge is implied
by an address, role, membership, access-point or conduit. Summarized transport
is the explicit logical abstraction described in domain-model.md; authors must
disclose hidden infrastructure in SUC boundary/completeness prose. This schema
adds no physical-topology or vendor-configuration capability.

## Services, rules, intents and scenarios

| Service field | Type |
| --- | --- |
| `id` | id |
| `asset_id` | id → Asset |
| `interface_id` | id → Interface owned by that asset |
| `protocol` | enum(tcp, udp) |
| `destination_ports` | ports |

One service binds exactly one interface. Distinct service IDs may overlap ports.
Every port in a range is an asserted listener of interest. No listener is inferred.

| EnforcementRule field | Type |
| --- | --- |
| `id` | id |
| `edge_ids` | idset<edge> |
| `source` | selector |
| `destination` | selector |
| `protocol` | enum(tcp, udp) |
| `destination_ports` | ports |
| `effect` | enum(allow, deny) |

Selectors expand by administrative ownership, never interface placement. Expansion
must be nonempty. Rules always match unchanged original source and final destination
assets and the same protocol/destination port. Each traversed edge needs at least
one matching allow and no matching deny; deny overrides irrespective of file order.
Allow/deny overlap is valid. Wildcard protocols, source ports, interface selectors,
local-origin interface restrictions and ordered policies are unsupported.

| CommunicationIntent field | Type |
| --- | --- |
| `id` | id |
| `kind` | enum(required, prohibited) |
| `source` | selector |
| `destination_service_ids` | idset<Service> |

| ExposureScenario field | Type |
| --- | --- |
| `id` | id |
| `origin_asset_ids` | idset<Asset> |
| `destination_service_ids` | idset<Service> |
| `description` | optional text describing assumed origin |

Self asset/service pairs are removed in every mode, including explicit sets;
an intent/scenario with no remaining inter-asset pair is invalid. Selected
origins require interfaces. Required intent quantifies over every remaining
source/service/port; prohibited intent requires none reachable. Contradictory
required/prohibited scopes are invalid even when different overlapping service
IDs express the same endpoint/interface/protocol/ports. Intents grant no permits.
Scenario origins are explicit assumptions, not compromised-host conclusions.

Transport transfers egress→ingress; forwarding transfers ingress→egress. Paths
start at any source-owned egress and finish at the service-bound ingress, alternating
transport and forwarding with transport at both ends. Neither two transport
edges meeting at an interface nor two forwarding edges in succession create
transit. No reverse initiation, application relay or pivot is implied. These
are the evaluation semantics; they do not assert
real session success, deployed enforcement or exploitability.

## Diagnostics and stopping behavior

Diagnostics have `category` (one of the strings below), `code` (stable
uppercase string below), `location` (rooted field path such as
`$.interfaces[0].placement_zone_id`, or `$` for document/execution errors), and
`message` (actionable prose). Parser errors may additionally carry 1-based `line`
and `column`. Do not echo full inputs, unrelated contents or tracebacks by default.
No diagnostics are serialized to files. `validate` prints JSON diagnostics to
stderr and exits 2 on errors; on success it prints a structural summary and hash
and exits 0. `check` emits a complete intent result (0 for all pass, 1 for failed
intents) or controlled errors (2). `exposure` evaluates one declared scenario and
all intents; `compare` evaluates both snapshots with one common scope. They emit
complete JSON (0 with no failed intents, 1 with failed intents, 2 on errors).
There are no remaining command placeholders. The historical not_implemented
diagnostic category remains reserved; no current command emits it.

| Category | Code(s) and trigger |
| --- | --- |
| `invalid_input` | `YAML_SYNTAX`, `YAML_FEATURE` (tags, directives, aliases, anchors, merge), `MULTIPLE_DOCUMENTS`, `DUPLICATE_KEY`, `UNKNOWN_FIELD`, `MISSING_FIELD`, `TYPE_MISMATCH`, `INVALID_VALUE`, `INVALID_ID`, `DUPLICATE_ID`, `DUPLICATE_ITEM`, `MISSING_REFERENCE`, `INVALID_ADDRESS`, `DUPLICATE_ADDRESS`, `INVALID_PORT`, `INVALID_PLACEMENT`, `SCOPE_MISMATCH`, `SAFETY_INCONSISTENCY`, `INVALID_CONDUIT_PAIR`, `INVALID_EDGE`, `INVALID_SERVICE_BINDING`, `INVALID_ACCESS_POINT`, `INVALID_DEPENDENCY`, `INVALID_SELECTOR`, `EMPTY_QUERY_SCOPE`, `CONTRADICTORY_INTENTS` |
| `unsupported_model` | `UNSUPPORTED_VERSION`, `UNSUPPORTED_PROTOCOL`, `UNSUPPORTED_ADDRESS_FAMILY`, `UNSUPPORTED_ADDRESS_KIND`, `UNSUPPORTED_OWNERSHIP`, `UNSUPPORTED_CONDUIT`, `UNSUPPORTED_FORWARDING`, `UNSUPPORTED_POLICY`, `UNSUPPORTED_FEATURE`, `UNSUPPORTED_QUERY` |
| `resource_limit` | `LIMIT_EXCEEDED`; identify limit name, allowed maximum and observed/planned count |
| `io_error` | `READ_ERROR`, `REPORT_IO_ERROR` |
| `execution_error` | `INTERNAL_ERROR`; no partial successful result |
| `not_implemented` | `NOT_IMPLEMENTED`; reserved; not emitted by current commands |

Unsupported semantics must be identified before ordinary shape rejection when
explicitly recognizable: a conduit with more than two distinct zone IDs is
UNSUPPORTED_CONDUIT; fewer than two or repeated IDs are invalid. A zone_id list,
`owner_zone_ids` or `owner_conduit_id` asset field indicates unsupported ownership;
`transit_zone_ids`/`protected_transit` on a conduit indicates unsupported transit.
These are **rejected diagnostic spellings, not schema extensions**. Recognize
`source_ports`, `source_interface_ids`, `stateful`, `rule_order` as unsupported
policy requests and `sl_t`, `sl_c`, `sl_a`, `nat`, `vrf`, `vlan`, `proxy` as
unsupported features wherever supplied. Other unknown fields remain invalid.
Non-tcp/udp protocol strings and IPv6 literals are unsupported; primitive type
errors remain invalid. NAT, VRFs, VLAN/L2, dynamic routing and vendor parsers are
outside scope, with no automatic flattening or substitution. A standalone
self-only query is unsupported (distinct from an invalid self-only embedded scope).

Parsing/budget checks precede schema/reference checks; supported-model consistency
and selector/intent validation precede analysis. If errors are collected,
sort by location then code; any fatal category stops analysis. No invalid,
unsupported or resource-limited run yields unreachable, compliant or successful
partial results. CLI exit 0 is reserved for successful work, exit 1 for completed
analysis with failed intents, exit 2 for errors including unsupported models and
reserved future commands. Exposure deltas alone do not imply failure. These codes
are not standards violations or certification judgments.

## Initial resource ceilings (provisional)

These are enforced rejection ceilings, not measured capacity. Entity, parser,
association, atom and planned/actual evaluation budgets are independent.
See [algorithms](algorithms.md) for work formulas.
The event ceiling counts the logical document event stream during the preflight;
the bounded stream is replayed for construction, without retaining all events.
No truncation or automatic limit increase is allowed.

| Name in `contract.ResourceLimits` | Ceiling | Counting rule |
| --- | --- | --- |
| `input_bytes` | 5,242,880 (5 MiB) | Raw file bytes before decoding/parsing |
| `nesting_depth` | 32 | Root container depth 1; each nested container adds 1 |
| `parser_events` | 200,000 | Every YAML parser event, including stream/document events, before object construction |
| `assets` | 1,000 | Raw asset records |
| `interfaces` | 2,000 | Raw interface records |
| `edges` | 5,000 | Transport + forwarding records combined |
| `rules` | 5,000 | Raw rule records |
| `services` | 1,000 | Raw service records |
| `zones` | 1,000 | Raw zone records |
| `conduits` | 5,000 | Raw conduit records |
| `access_points` | 5,000 | All modeled and unmodeled records |
| `dependencies` | 1,000 | External dependency records |
| `protocol_port_atoms` | 2,048 | Distinct requested protocol/port atoms, combined across protocols |
| `state_edge_visits` | 50,000,000 | Prospective traversal bound across queries, before allocation/traversal |
| `edge_rule_associations` | 500,000 | Sum of referenced edges over rules |
| `edge_rule_atom_checks` | 50,000,000 | Prospective predicate-check product before allocation |
| `diagnostic_edges_per_query` | 20 | Display sample only; preserve total failures and mark truncation |

Other collections/text remain bounded by byte/event/depth budgets; reference lists
are distinct and bounded by their target catalogs. Access-point edge references
are additionally bounded by combined edge ceiling and unique crossing coverage.
Work products are checked before oversized expansion. Routine performance
targets are separate from conservative maximum-input rejection limits.

## Fixtures and evidence boundary

See the [fixture guide](../tests/fixtures/README.md) and [testing strategy](testing-strategy.md).
Normalized hashing, initiation checks, finite scenarios, comparisons and offline
reports are implemented. Completeness, deployed enforcement, exploitability,
session completion and physical safety remain outside the verified model.
