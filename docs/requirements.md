# Functional and engineering requirements

These are software contracts, not claims about a deployed plant.

| ID | Requirement and acceptance |
| --- | --- |
| FR-01 | Offline validate/check/exposure/compare CLI/API with stable native exits |
| FR-02 | Strict typed inventory, zones, interfaces, pairwise conduits, edges, listeners, rules, intents and scenarios |
| FR-03 | Validate IDs, references, addressing, ownership/placement, SUC/access points/dependencies and safety declarations before analysis |
| FR-04 | Directed TCP/UDP initiation; original endpoints/ports and unordered deny precedence on every edge |
| FR-05 | Independent required/prohibited quantified intents, no vacuous or contradictory scopes |
| FR-06 | Explicit boundary forwarding and exact cross-placement conduit consistency |
| FR-07 | Deterministic shortest witnesses, replay and bounded structural/policy diagnostics |
| FR-08 | Finite exposure tuples and deduplicated assets with owner criticality |
| FR-09 | Stable-ID comparison separates inventory, definitions, intents and connectivity; reduced exposure cannot cancel failures |
| FR-10 | Deterministic JSON/offline HTML/SVG, hash provenance, escaping and explicit omissions |
| FR-11 | Controlled invalid/unsupported/resource/I/O errors, atomic output and no successful partial result |
| FR-12 | Synthetic examples, user/developer documentation and independently audited distributions |

| ID | Nonfunctional requirement |
| --- | --- |
| NFR-01 | No network, telemetry, cloud, scanning or deployment at runtime |
| NFR-02 | Python 3.12 minimum; verify actual Windows installations |
| NFR-03 | Same engine/input/options produce repeated byte-identical JSON/HTML/SVG |
| NFR-04 | Independent small-model/per-port and interval-set oracles; witness replay |
| NFR-05 | Routine: 200 assets, 400 interfaces, 1200 edges, 200 rules, 25 services, 10 origins; warm exposure target <=30 s and <=512 MiB traced Python allocations on recorded host |
| NFR-06 | Typed modular core, minimal dependencies, Ruff/mypy clean |
| NFR-07 | Bounded parsing, escaped output, controlled errors and old-report preservation |
| NFR-08 | Honest finite scope and unassessed evidence; no risk/safety/certification inference |
| NFR-09 | Exact checks, installed CLI, source/test/archive consistency and license review |
| NFR-10 | No required paid infrastructure, hardware or service |

See [schema](yaml-schema-v1.md), [algorithms](algorithms.md),
[testing](testing-strategy.md) and [limitations](limitations.md).
