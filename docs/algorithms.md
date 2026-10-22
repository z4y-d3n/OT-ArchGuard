# Exact bounded analysis algorithms

These contracts concern declared initiation reachability, not device emulation,
sessions, host compromise or physical process behavior.

## Input and identity

Read at most input_bytes plus one byte. Reject oversize/invalid UTF-8.
Event preflight bounds depth/count and rejects aliases/anchors/tags/extra documents
before object construction. A directive scan and bounded replay construct primitives,
rejecting duplicate/non-string keys. Strict typed parsing and reference/placement/
SUC/selector/listener/safety/contradictory-intent checks precede analysis.

Normalize set-like IDs/records and closed port unions deterministically. Preserve
meaningful text and IPv4 host addresses. SHA-256 of sorted compact canonical UTF-8
JSON identifies a declaration independently of comparison partitions.

## Graph, permissions and exact intervals

Create ingress/egress states per interface. Transport is egress-to-ingress between
assets; forwarding is ingress-to-egress inside one explicit boundary device.
Retain parallel edge identities. Sort origins/adjacency by state and edge ID.
Membership, addressing and conduit metadata create no edges.

Compile explicit rule-edge associations, expanded original endpoint sets, protocol
and normalized destination-port unions. Owner-zone selectors never mean placement.
Every traversed edge needs at least one matching allow and no matching deny.

For TCP/UDP separately, collect starts/end+1 from services/rules plus 1 and 65536.
Comparison uses both snapshots' boundaries. Consecutive boundaries define disjoint
closed atoms; retain requested listeners. Predicates are constant inside an atom;
one representative is exact without enumerating all ports. Merge resulting interval
unions by source/destination/service/protocol, not atom index.

## Search and replay

BFS starts at all source-owned egress states and ends at bound listener ingress.
Identity/protocol/port remain fixed. Visited states terminate cycles. Sorted
traversal supplies one deterministic shortest edge-count witness. Replay checks
hash, service, atom, endpoints, states, edge continuity, conduit and allow evidence.

Failed permitted search is followed by structural search without policy. Distinguish
no structural path from no permitted path. Sample the sorted blocked frontier
with total count and truncation flag. This is not all paths, a unique cause,
a minimal cut or a guaranteed repair.

## Scope and comparison

Expand finite intents/scenarios, exclude self pairs and reject vacuous domains.
Required means all selected ports; prohibited means none reachable. Exposure
retains exact tuples and deduplicated destination assets plus independent intents.
Origins are assumptions, not conclusions of compromise.

Validate snapshots independently, use shared atom boundaries and compare exact
normalized sets only for comparable stable entities/services. Separate inventory
and definition changes. Evaluate both sides' intents independently of exposure totals.

## Resource and output contracts

For Q reserved atom queries, V states, E edges and A rule-edge associations,
current conservative bounds include 3*Q*(V+E) visits and Q*A predicate checks.
Actual work is counted too. A fixed-atom BFS costs O(V+E) plus evaluated predicates;
partition sorting and selector expansion add cost. These are work bounds, not
universal timing/RSS guarantees. No path/global cache replaces input validation.

Budget rejection precedes expansion and returns an error. Hash/kind checks bind
reports to validated snapshots. Escape labels, serialize deterministically and
write through same-directory temporary/atomic replacement. Preserve old reports
on failure. Full evidence accompanies explicit diagram omission manifests.
See [schema limits](yaml-schema-v1.md) and [benchmark method](benchmarks/README.md).
