# Gate V12-03 — secure graphical topology evidence

This report describes the implemented subset and closure procedure. The final
source-bound verdict, exact source/artifact identities and executed results are
recorded in ignored `output/v1.2-development/v12-03/final-01/acceptance.json`
and `acceptance-report.md`. A report alone does not confer acceptance. Only a
fresh successful closure on the same public-source snapshot permits local PASS.
No hosted platform or release acceptance is implied.

## A. Baseline and Git integrity

Started on `codex/v12-ingestion-foundation` at
`d95d52ddea1d9789a7b57374673902ed45e700d6`. Recomputed public-source identity
`e1cff1e407ab62f3fa34808fc3ccbb40fdbd049757d9ac448354de090b77443b` exactly
matched the accepted V12-02R manifest and all 40 prospective changed/untracked
project files. There were no intervening source changes. Existing acceptance
records identified the same source and successful prior tests; those results
were baseline evidence, not tests of this gate.

After checking ignored evidence/environments, exact staged bytes and the proposed
file list, created local consolidation commit `cc7850b`. Every committed public
file reproduced the accepted digest without modifying source bytes. Created
`codex/v12-03-graph-evidence` from that clean baseline. Historical main, independent
root, stable tree and both annotated tag objects matched the supplied identities.
The closing record verifies them again and records final branch/HEAD/status.

## B. Actual implementation

New production modules: `graphical.py` (shared evidence, limits and mapping),
`graphml.py`, `drawio.py`, `xml_safe.py` (extracted existing XLSX XML parser).
Changed records, structured mapping, shared workflow and CLI integrate the five
existing import commands. The XLSX wrapper preserves its existing budgets/codes.
No analytical module or dependency changed. Development remains `1.2.0.dev0`.

GraphML supports its correct namespace, named top-level graphs, explicit node IDs,
optional edge IDs, directed/undirected defaults and per-edge direction overrides,
scalar typed keys/data/defaults and precise graph/element/key locations.
Anonymous edges have deterministic structural IDs, preserving parallel occurrences.
Attributes are selected by key ID; numeric values preserve V12-02R exact tokens.
No schema reference is fetched. Nested graphs, ports, hyperedges, locators and
extension elements fail closed; unsupported attributes have bounded diagnostics.

draw.io supports namespace-free mxfile pages with explicit IDs, uncompressed
mxGraphModel, canonical compressed diagrams.net pages, and explicitly selected
standalone mxGraphModel. It handles mxCell vertices/edges, object/UserObject
wrappers with scalar attributes, layers, text, groups/swimlanes, parent relationships,
bounded geometry and selected inert style metadata. Missing/cyclic parents and
duplicate IDs fail. Dangling connector endpoints remain unresolved evidence.

Version-3 graph profiles reuse TableMapping/FieldMapping, selecting exact scopes
and nodes/assets, groups/zones, or edges/evidence-only connections. A graph draft
and sidecar use version 4; previous versions keep their representation and workflow.
Decisions remain version 1. Templates stay unresolved, with literal corrections,
reasoned decisions and complete model confirmation required. Emit rereads and
reproduces the original source, verifies review binding, validates schema 1 twice,
and publishes the complete model/sidecar atomically with no overwrite.

Commands and the complete profile/review walkthrough are in
[Import Studio](../import-studio.md). For example:

```text
otarchguard import inspect industrial.drawio
otarchguard import inspect directed.graphml
otarchguard import map industrial.drawio --profile drawio-profile.json --output draft.json
otarchguard import review draft.json --context model-context.yaml --decisions decisions.json
otarchguard import emit draft.json --source industrial.drawio --decisions decisions.json --output accepted
otarchguard validate accepted/architecture.yaml
```

Emission requires completing the generated owner decisions between review and
emit. The shipped synthetic examples contain six industrial devices, two draw.io
containers, five connectors, compressed repeated-ID pages and GraphML direction
variants. They contain no customer material.

## C. Security and resource accounting

See [ADRs A–D and exact boundaries](v12-03-graphical-formats.md). Expat callbacks
reject DTD/entities/PIs and non-UTF-8 input, charging depth, elements, text,
attributes, expanded names and namespace declarations before tree construction.
All pages, including unselected pages, are validated. No external entity, schema,
link, image, attachment or plugin is fetched/executed/rendered.

Compressed pages require canonical bounded Base64, raw-DEFLATE with incremental
maximum-length output, complete EOF and no trailing/concatenated stream, strict
percent escapes and UTF-8, then the same XML checks. No unrestricted decompression
or recursive decode exists. Source is at most 1 MiB; each inflated page at most
2 MiB and aggregate expansion at most 8 MiB. Charged expansion includes percent
text, conservatively larger than decoded XML. At most 16 pages, 1,000 nodes
(including layers/groups), 1,000 edges, 64 keys, 128-character IDs,
4,096-character values, depth 24, 150,000 XML elements and 200 diagnostics.
Drafts/sidecars retain 5 MiB/depth-32/200,000-event limits and 1,000 candidates.
These are rejection ceilings, not capacity promises.

Adversarial tests cover actual default source/page/aggregate/name/depth/element/
attribute/node/page limits and reduced edge/text/diagnostic boundaries, malformed
Base64/DEFLATE/percent/UTF-8, truncation/concatenation, DTD/entity/PI attempts,
namespaces, duplicate IDs/keys, cycles/dangling references, invalid directions,
unsupported nesting/ports/hyperedges/extensions/plugins/stencils/attachments,
HTML/links as inert evidence, and sensitive attribute-name aliases. No material
unresolved defect was found in the implemented subset. Preparation corrected a
synthetic helper keyword collision and a proposed ID exceeding schema's 64-character
limit; explicit scoped IDs now fit that unchanged contract. Initial failed attempts
are not counted as acceptance.

## D. Semantic integrity

Every graph edge has `relationship: diagram_evidence_only`. Direction records
whether it came from a graph default, edge override or graphical arrowheads.
Nothing converts these records to native transport, forwarding, service or rules.
Groups never automatically establish zones or asset zone membership. Profile
constants are proposals requiring owner confirmation.

Profiles explicitly request `connections: evidence_only`; omitting an edges table
retains connectors in the reviewed sidecar without generating declaration
candidates. Selecting edges creates individually reviewed connection candidates
that must be rejected. Confirming one returns `IMPORT_RELATIONSHIP`. No new review
state or bulk declaration acceptance was added.

Independent tests inspect emitted native fields and build the actual state graph.
With separately owner-declared interfaces and a TCP/502 service, native tracing
still finds no authorized interval/path from diagram connectors. Schema 1,
normalization/model hashes, deny/default-deny, ports, transport/forwarding and
report/trace version 1 remain byte-preserved outside ingestion.

## E. Verification closure

Preparation passed all 109 new graphical cases, plus the exercised structured,
numeric and XLSX security regression cases. Ruff lint/format and strict mypy
(92 files) are required again after the final documentation/manifests freeze.
Fresh acceptance requires full installed-wheel suites on Windows Python 3.12.14
and 3.14.5 (1,843 cases each) and installed-sdist ingestion/review suites on each
(494 cases each), with zero failures/errors/skips. Exact executed JUnit totals,
return codes, stdout/stderr hashes and timings belong to the final evidence.

Four fresh environments reuse already approved local dependencies without downloads.
Fresh wheel/sdist archive audits enforce the complete public allowlist and exact
source bytes. All installed production modules, distribution/console version,
direct artifact hash and noneditable identity are checked. Installed workflows run
outside the checkout and include inspection, preview, mapping, unresolved review
rejection, reviewed emission, validation/check, stale-source and no-overwrite errors.
An inherited socket/DNS/HTTP guard is actively probed; no source-tree fallback is
accepted. Existing complete regression suites cover CSV/TSV/JSON/XLSX/NetBox and
analytical semantics. Deterministic repeated drafts/emissions and serialization,
page/node ordering, geometry, repeated labels/IDs and compression equivalence
have independent assertions.

## F. Performance observations

Preparation observations on this Windows host (single samples, not guarantees):

| 400 assets / 399 edges | Source bytes | Charged expansion | Parse s | Map incl. parse s | Load s | Emit incl. validation s | Draft / sidecar bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GraphML | 54,539 | 54,539 | 0.034 | 0.181 | 0.291 | 1.347 | 1,854,686 / 2,111,740 |
| draw.io raw | 116,377 | 116,304 | 0.050 | 0.189 | 0.332 | 1.324 | 1,905,725 / 2,161,179 |
| draw.io compressed | 10,653 | 188,406 | 0.061 | 0.188 | 0.316 | 1.355 | 1,905,731 / 2,161,185 |

At 50 assets, mapping Python allocation peaks were about 2.42–2.50 MB using
tracemalloc (not RSS/native allocations). Dense 1,000-node GraphML parsed but its
mapped evidence exceeded the existing event budget. The 1,000-device draw.io
fixture exceeded the node budget because its four layer/group cells also count.
Per-field provenance and control events remain the main capacity bottleneck.
The final frozen run repeats measurements with installed code and retains raw
samples; its actual timings can differ under concurrent host load.

## G–H. Artifacts and limitations

Public manifests include the new modules, two graphical test modules, synthetic
generator/examples and this report/reference; selected review ZIP membership is
extended explicitly. The final frozen source manifest avoids circular hashing
by living in ignored evidence, alongside changed-file inventory, package/ZIP
digests, installed identities, JUnit, performance and history checks.

Only documented structural subsets are supported. No vendor rendering, arbitrary
SVG/HTML, custom stencil/plugin, attachment, hierarchy/port/hyperedge GraphML,
network discovery, policy inference or multi-source reconciliation. Root/graph/
page/element identities must be explicit (ordinary GraphML edge IDs may be absent).
GraphML labels require explicit key selection; there is no vendor label discovery.
Unselected custom fields and external targets are excluded; core draw.io labels
remain local evidence and can contain sensitive data. This is not universal secret
detection. Manual JSON owner review and finite diagnostic/candidate budgets limit
large-diagram ergonomics. No public graphical HTML preview is introduced.
Only Windows is locally verified; hosted Ubuntu/macOS remain required before
cross-platform release. Local single-writer/crash-durability limitations persist.

## I–K. Verdict, next gate and publication boundary

The final acceptance record selects exactly one of PASS/PARTIAL/BLOCKED/FAIL based
on this gate's newly executed evidence. Old receipts never accept new parsers.
V12-04 readiness requires distinct source identities/provenance, order-independent
explicit matching, cross-source conflicts and owner-reviewed reconciliation;
connector evidence must remain separate from authorized native declarations.
V12-04 is not implemented here.

No remote push/PR, main rewrite, historical tag mutation, release/PyPI publication,
v1.2 tag, dependency acquisition, live IT/OT access, cloud document processing or
customer-document access is part of this local task.
