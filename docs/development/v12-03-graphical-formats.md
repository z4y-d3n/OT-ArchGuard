# V12-03 graphical adapter decisions

## ADR V12-03A — shared evidence, existing workflow

Use typed graph pages, nodes, edges and containment records alongside the existing
structured candidates. Graph profile version 3 reuses `TableMapping` and
`FieldMapping`; exact scope IDs and `nodes`, `groups`, `edges` select records.
Only nodes may propose assets and groups may propose zones. Edges may only propose
connection evidence. All selected relationships also remain in a version-4 draft
and provenance sidecar. Mapping delegates to `map_extracted`; review, source
reproduction, corrections, native validation and atomic emission remain shared.
Decisions version 1 is preserved: connection candidates require explicit rejection.
No bulk acknowledgment state is introduced. Missing declarations require correction.

## ADR V12-03B — bounded XML and raw DEFLATE

Extract the existing Expat callback budget into a reusable utility, retaining XLSX
diagnostic names and accounting. Reject DTD/entities/processing instructions and
non-UTF-8 XML. Count expanded names, namespace declarations, attributes and text
before building trees. No schema fetches, rendering, extraction or new dependency.
Use strict canonical Base64, raw-DEFLATE incremental inflation with `max_length`,
EOF/trailing-data checks, strict percent escapes and UTF-8 decoding. Decode once;
the inner root must be `mxGraphModel`, so nested compression is rejected.

Ceilings: source 1 MiB, inflated page 2 MiB, total inner XML/percent text 8 MiB,
16 pages/graphs, 1,000 nodes including groups, 1,000 edges, 4,096 characters per
label/attribute, 128 per identity, XML depth 24, 150,000 elements, 8 MiB charged XML
characters, 64 attributes per element, 200 diagnostics. All pages are validated
even when unselected. Drafts/candidates/sidecars retain existing 5 MiB, depth 32,
200,000 events and 1,000 candidate ceilings. These are rejection limits, not
capacity promises. Explicitly unsupported structures fail closed.

## ADR V12-03C — graph structure has no network authority

GraphML direction and draw.io arrowheads are descriptive evidence. Parent cells
and groups are graphical containment. No connector, icon, label or attribute grants
transport, forwarding, listening, routing, zone membership or policy. Profiles
explicitly select descriptive attributes and native proposals; every declaration
requires owner confirmation. Unknown styles have diagnostics, no role inference.
Text/HTML labels are inert JSON text. External link/image payloads are omitted and
diagnosed without retaining targets. Native schema and analytical code stay intact.

## ADR V12-03D — scope and provenance

Require explicit unique page/graph and node/cell IDs. IDs are scoped by page/graph;
duplicate IDs within a scope fail. GraphML edges without IDs use a deterministic
hash of their supported structure plus duplicate occurrence (indistinguishable
parallel edges remain separate). Candidate records use stable scope/element IDs,
mapped values and explicit profile semantics; serialization order and geometry
do not determine identity. `/scoped_id` offers a safe, collision-resistant proposed
native ID. Exact source bytes and basename bind the draft and stale-review check.
Every changed byte requires renewed review, including omitted metadata. No paths
or timestamps enter evidence. Hashes detect change; they are not signatures.

## Supported boundaries

GraphML requires `http://graphml.graphdrawing.org/xmlns`, top-level named graphs,
explicit `edgedefault`, nodes, ordinary edges, per-edge boolean direction, scalar
keys (`string`, `boolean`, `int`, `long`, `float`, `double`) and defaults. Numeric
values use the V12-02R exact token grammar, with integer category enforced for
int/long. Keys are selected by key ID, never guessed from `attr.name`. Nested
graphs, ports, hyperedges, locators and vendor extension elements are rejected.
Schema-location attributes are inert and never fetched. Missing edge endpoints
are diagnosed and retained; unknown referenced IDs never become guessed targets.

draw.io accepts namespace-free `mxfile` with named/identified `diagram` pages,
uncompressed `mxGraphModel/root/mxCell`, compressed pages and explicit standalone
`mxGraphModel` via the drawio adapter (scope `standalone`). Supports object/UserObject
wrappers with scalar custom attributes, standard root/layer cells, vertices, edges,
groups/swimlanes, and inert geometry. Unknown XML elements, recursive/missing
parents, custom stencil payloads, plugins and attachments are rejected. Links,
images, HTML labels, locked/hidden cells, extra layers and unrecognized styles
receive bounded diagnostics. No style-based role or zone inference is performed.
Custom attribute values are retained only when explicitly selected in a mapping.

Profile paths: `/id`, `/scoped_id`, `/label`, `/parent`, `/source`, `/destination`,
`/direction`, `/attributes/KEY` (RFC 6901 escaping). No XPath or expressions.
An explicit `unknown_policy: diagnose` and `connections: evidence_only` are required.
Geometry is retained as bounded lexical text; no binary float conversion occurs.
