# Declared architecture domain model

The analyzer evaluates a finite logical forwarding abstraction.
The complete typed serialization contract is [schema 1](yaml-schema-v1.md).

## Entities and ownership

A snapshot contains one system under consideration (SUC), zones, assets, interfaces,
pairwise conduits, explicit transport/forwarding edges, destination services,
enforcement rules, independent intents and finite scenarios. IDs are typed stable
identities; names and roles are descriptive.

Each asset has one administrative owner zone; scope agrees with that zone.
Interface placement is explicit and distinct from ownership. Endpoints place
interfaces in their owner zone; boundary devices may attach to multiple zones
while retaining one identity. Safety checks use owned assets, not attachments.
Unknown classification and criticality are not inferred from roles or addresses.

A conduit groups channels between exactly two zones; it is not a device or permit.
Cross-placement edges reference the exact conduit pair; same-placement edges have none.
Transport connects different assets' egress to ingress. Forwarding connects distinct
interfaces of one boundary device, ingress to egress. Reverse transitions must be
separately declared. No role, zone, subnet, conduit or listener supplies an edge.

## SUC and assertions

Purpose, controlled process, boundary and completeness are owner declarations.
Every internal/external placement crossing has exactly one modeled access-point
record for its actual interface pair/edges. Unmodeled access points and external
dependencies retain descriptions/references but create no paths. Declaration
consistency cannot prove actual inventory completeness, deployed control or safety.

## Queries and policy

A query names an original source asset and a declared destination service.
The service binds an asset, interface, TCP/UDP and closed destination-port union.
All source-owned egress states are possible starts; listener ingress is the goal.
Standalone self queries are unsupported; embedded scopes exclude self pairs and
must retain at least one inter-asset pair.

Every traversed edge requires a matching allow and no matching deny for unchanged
original endpoints/protocol/port. Rules are unordered and selectors use administrative
ownership, not interface placement. Paths alternate transport and explicit
forwarding. Ordinary hosts never relay implicitly. Reaching a broker/jump service
does not authorize another application leg.

Required intents quantify every selected port; prohibited intents permit none.
Contradictory required/prohibited endpoint traffic is invalid before analysis.
Intents never grant permissions.

## Comparison and evidence

Comparisons use one common finite scope and matching SUC identity. Stable IDs link
snapshots; renames are removal/addition. Inventory, service and intent definition
changes remain separate from connectivity differences. Failure on either side
remains visible; reduced exposure cannot cancel required/prohibited findings.

Permitted exact intervals retain deterministic shortest witnesses bound to hashes,
states, edges, conduits and matching rule IDs. Unreachable diagnostics distinguish
structural absence from policy blockage, using a bounded frontier rather than a
unique cause/minimum-cut claim. Unsupported/resource-limited analysis is an error.

See [algorithms](algorithms.md), [worked example](boundary-device-example.md)
and [limitations](limitations.md).
