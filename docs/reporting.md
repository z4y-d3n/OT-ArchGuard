# Offline evidence reports, version 1

The additive development [Architecture Explorer](../examples/explorer/README.md)
uses static multipage navigation for native models and project provenance. Run
`otarchguard explore MODEL --output NEW_DIRECTORY`, optionally with
`--provenance SIDECAR`, `--trace SOURCE:SERVICE`, `--check` or `--scenario ID`.
Explicit analyses use the existing engines on the same validated model. No
arbitrary old HTML/JSON report is imported as analytical authority. Existing
single-file reports and their version-1 bytes/contracts remain unchanged.
See [input, security and size contracts](development/v12-05-architecture-explorer.md).

For current presentation design and observed verification, see
[Gate V11-2](v1.1/gate-v11-2.md). Analytical report JSON remains version 1.

All four commands retain their existing deterministic JSON stdout and native exit
codes. Add `--report PATH` to write a fully offline HTML artifact, or add
`--report-format json` for the richer JSON report envelope. The filename extension
does not select the format. Existing parent directories are required. No browser,
Graphviz, Jinja2, JavaScript, web server or additional dependency is required.

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\otarchguard.exe validate examples/remote-support/baseline.yaml --report output/validation.html
.\.venv\Scripts\otarchguard.exe check examples/remote-support/baseline.yaml --report output/check.json --report-format json
.\.venv\Scripts\otarchguard.exe exposure examples/remote-support/baseline.yaml --scenario support_scope --report output/exposure.html
.\.venv\Scripts\otarchguard.exe compare examples/flat-plant/baseline.yaml examples/flat-plant/proposed.yaml --scenario plant_scope --report output/comparison.html
```

The last command intentionally exits **1**: the proposal breaks a required HMI
flow. A report is still produced for completed analysis with failed intents.
Exit **2** means invalid/unsupported input, exhausted evaluation budgets, execution
failure or report I/O failure; no new success report or stdout result is produced.
An existing output artifact remains untouched on failure. Always inspect the exit
status: an old artifact is not evidence of a successful new run. Do not use an
input path as the report output. Writes use a temporary sibling and atomic
replacement; there is one output artifact, with its SVGs embedded.

Report JSON has `report_version: 1`, `engine_version`, `schema_version`, `kind`
(`validation`, `check`, `exposure`, `comparison`), `status`, `scope`, `limitations`,
`security_level_evidence`, `resource_ceilings`, `snapshots` and `result`.
Each snapshot records its role, SHA-256 hash, full canonical declared model and
diagram mode/legend/omission manifest. `result` retains the original analysis
record, including finite query scope, exact intervals, independent intent results,
bounded unreachable diagnostics and replayable permitted witnesses. Validation
reports explicitly leave intents and reachability unassessed. JSON uses sorted
keys, ASCII escapes, UTF-8 and one terminal LF. No clock values or machine paths
are added. Evidence hashes must match the supplied validated models. The native
CLI retains the completed immutable snapshots used for evaluation and verifies
their result/hash bindings before writing. Report-enabled check, exposure and
comparison validate each input once; comparison retains its two independent
snapshots. A later file change cannot substitute a different model into the
report. Independent CLI invocations and public file/bytes APIs still validate
their inputs afresh. There is no filename cache or persistent analytical state.
See [performance methodology](benchmarks/performance.md).

HTML presents failed requirements and introduced prohibited violations first, then expanded SVG
diagrams before any detailed table. Interpretation, independent intent outcomes,
per-side observations/criticality and connectivity/inventory/definition changes
follow. Wide tables scroll horizontally with minimum readable column widths;
nested values use formatted text rather than squeezed single-letter columns.
Native expandable sections retain per-query witness steps/diagnostics and full
SUC/inventory tables, without JavaScript. The complete JSON evidence appears in
a labeled expandable machine-readable appendix, separate from the diagrams. Baseline
failures remain visible even if resolved in the proposal. Failed required
communications are never replaced by a favorable exposure count or score.

SVG diagrams are spatial schematics: labeled zone boundaries enclose asset cards
and interface ports **by placement**. Each card labels the administrative owner
zone explicitly. A boundary asset may appear as dashed shield cards in several
zones: these are attachments of the same stable asset ID, not additional devices
or a change of ownership. An ownership-only card with no placed interface has no
network ports. Generic endpoint symbols do not infer device roles or capabilities.
Ingress ports are on the left, egress on the right. Blue solid transport arrows
connect egress→ingress; purple dashed forwarding arrows connect ingress→egress
of the same declared boundary asset. Arrows route around asset cards, with edge
IDs and applicable conduit IDs. They represent explicit directed declarations,
**not assertions of permission**. Wire crossings/overlaps are not junctions.
No extra arrow joins attachment copies just because they share an asset ID.
Ownership, IP prefix, shared placement and
application listeners create no implicit connectivity. Unmodeled access points
and external dependencies are shown in SUC evidence and remain unevaluated.
These diagrams reproduce no standards publication or vendor drawing.

At more than 24 assets, 24 interfaces, 48 edges or 12 zones, SVG uses a clearly
labeled summary with no asset attachments, ports or connectivity arrows: at most
12 zone containers are shown. Otherwise every declared asset/interface/edge is
shown. Conduits annotate their declared edges; unused conduits and all conduits
in summary mode are explicitly listed as omitted from the diagram, with full
pairwise declarations in tables/JSON. Exact omitted IDs are in the manifest.
Full tables and JSON retain all topology. Visual labels are shortened to fit the
card/zone, with complete text in SVG titles and tables. Wide schematics scroll
horizontally at a minimum readable size instead of shrinking all labels.
XML-incompatible control characters display as U+FFFD; JSON retains originals.
Markup-sensitive characters are escaped in every HTML/SVG text context. All
structural attributes, CSS and SVG elements are generated locally; untrusted
labels cannot become markup, attributes, links or CSS. CSP blocks remote content,
scripts, forms and base URLs as defense in depth. There are no external resources.

For Python callers, `build_report(kind, snapshots, result, limits=...)` binds an
already computed result to its exact validated models. Supply the same limits
used for analysis (CLI uses defaults). `json_report` and `html_report` return
bytes; `architecture_svg(snapshot)` returns standalone SVG text. These helpers do
not run analyses or infer paths. The default rendering retains all detailed
evidence in memory, with no separate report-size budget or streaming renderer;
large reports can be lengthy. Resource ceilings remain provisional.

## Presentation ordering (v1.1 development)

All four commands accept repeatable `--zone-order ZONE_ID` with an HTML `--report`:

```powershell
.\.venv\Scripts\otarchguard.exe compare examples/remote-support/baseline.yaml examples/remote-support/proposed.yaml --scenario support_scope --report output/ordered.html --zone-order enterprise --zone-order dmz --zone-order control
```

Unknown or repeated IDs produce controlled invalid-input diagnostics and exit 2,
preserving prior output. An order without a report, or with a JSON report, is
rejected. Comparisons validate against both snapshots' union of zone IDs and apply
each ID only where it exists. Requested IDs come first; remaining IDs use the
default order. Preferences, effective orders and visible subsets appear in HTML.
No membership, model hash, JSON envelope, analysis stdout or outcome changes.

The default builds a presentation-only zone relation from explicit cross-placement
transport/forwarding declarations. Kahn ordering chooses the smallest ready ID;
when a cycle leaves none, the smallest remaining ID breaks the cycle for drawing.
Disconnected and isolated zones use the same ID tie break. Names, trust, security
levels and subnet proximity do not influence placement.

Immutable geometry records hold rectangles, interface rows, state anchors, labels,
attachments, omissions and polylines. Every transition has separate side tracks
and a numbered shelf below cards in the affected zone span; disjoint spans may
reuse a shelf. An edge key retains IDs and conduits. Parallel/reverse declarations
stay distinct. Crossings/shared endpoint strokes are not junctions. This bounded
router does not promise crossing-free drawings; dense layouts can be tall.

Summary thresholds remain **more than** 12 zones, 24 assets, 24 interfaces or 48
edges. Membership retains the first 12 canonical zone IDs, keeping the existing
JSON omission manifest exact; preferences reorder that subset. HTML/SVG disclose
omitted cards, assets, interfaces, transitions and zones. Full declarations and a
deterministic device-to-interface map remain in HTML. No simplified synthetic
edges are generated, and summary mode never reduces analytical scope.

Labels use conservative code-point budgets and finite SVG clipping regions,
not measured pixel widths. Full values remain in SVG titles, tables and JSON.
The budget avoids runtime Unicode classification tables that differ by Python
version. Combining sequences may be shortened visually; their original text stays
in the full evidence.
Local font rasterization can vary by OS without changing SVG bytes. Scroll regions
retain intrinsic SVG dimensions. Print styles preserve findings and inventory;
wide diagrams may shrink, so use inventory for exact printed identifiers.

HTML includes a local table of contents, skip link, snapshot references, visible
focus styles, captioned tables and keyboard-focusable scroll regions. Comparison
SVG IDs are separately namespaced. Generated links use local fragments without
JavaScript. The JSON appendix remains the unchanged version-1 report envelope.
For Python use keyword-only `architecture_svg(snapshot, zone_order=("control",))`
or `html_report(report, snapshots, zone_order=("control",))`.
Browser focus, responsive and print behavior require the manual review listed in
the gate report; static tests and raster images do not establish those properties.

All criticality, safety/business/IACS classifications, scope and completeness are
owner assertions. SL-T, SL-C and SL-A remain **unassessed, not zero**. Assessment
and approval evidence stays external. A report is neither a full cybersecurity
requirements specification nor verified deployed inventory. It makes no external standards conformity/certification, exploitability, compromise-probability or
physical-risk-reduction claim. See [the synthetic walkthroughs](../examples/README.md).
The v1.1 development trace uses a separate `trace_version: 1` envelope and static
HTML entry points. See [trace evidence and finite summaries](trace.md). Native
exposure/comparison HTML adds summaries of completed scenario queries and
conservative declaration-change references. Existing report-version-1 JSON is
unchanged. Python HTML callers opt in with `analysis=completed_result`.

## Compact Explorer presentation contract 2

V12-06 groups candidate, decision, reconciliation, graphical and document evidence
records in bounded hash buckets with individual stable digest anchors. Native and
analytical pages remain separate. The manifest `locations` index maps semantic
record digest filenames to current relative paths/fragments. Old regenerated-site
bookmarks are not guaranteed; prior standalone sites remain readable. All conflicts,
rejected alternatives, source locations and owner choices stay linked.

Document observations link to explicitly mapped candidates by exact field locations.
No sentence or presentation arrow establishes a native permission. Grouped pages
contain other local evidence and are not public-safe exports. Share the original
whole folder, including CSS and all relative paths; browser Save Page As copies
are not canonical. See the [V12-06 reference](development/v12-06-document-evidence-and-explorer.md).

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
