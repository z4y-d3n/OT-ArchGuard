# Offline evidence reports, version 1

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
are added. Evidence hashes must match the supplied validated models. The CLI
revalidates report metadata and checks those hashes before writing, rejecting
evidence if the input changed between analysis and reporting.

HTML presents failed requirements as readable findings first, then expanded SVG
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

All criticality, safety/business/IACS classifications, scope and completeness are
owner assertions. SL-T, SL-C and SL-A remain **unassessed, not zero**. Assessment
and approval evidence stays external. A report is neither a full cybersecurity
requirements specification nor verified deployed inventory. It makes no external standards conformity/certification, exploitability, compromise-probability or
physical-risk-reduction claim. See [the synthetic walkthroughs](../examples/README.md).
