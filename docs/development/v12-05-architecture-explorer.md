# Architecture Explorer contract and ADRs (V12-05)

Development version remains **1.2.0.dev0**. `otarchguard explore MODEL --output NEW`
creates a read-only offline site. Optional `--provenance SIDECAR` accepts **project
provenance version 1**, not legacy single-source sidecars. A single-source accepted
model can be explored without a sidecar; its provenance is explicitly unavailable.
Explicit incompatible sidecars fail, never silently downgrade. No raw source
documents are needed to view a previously emitted project.

## ADR V12-05A — Presentation architecture

Three production modules separate bounded inputs (`explorer_data.py`), the HTML/SVG
safety/publication audit (`explorer_html.py`), and indexes/views (`explorer.py`).
The additive console command uses the existing native validator and exact engines.
It creates flat, hash-named HTML detail pages, paginated indexes (60 rows/page),
one local `assets.css`, and `manifest.json`. Flat paths simplify file relocation
and avoid deep Windows paths. Pages are not a single embedded evidence archive.
There is no JavaScript, server, database, template engine, external resource or
new dependency. `index.html` is the entry point after generation; Python can stop.

## ADR V12-05B — Trust semantics

Documentary nodes, connectors, original selected field values, transformations,
locations, conflicting groups, partitions, literal corrections and owner rationales
retain their separate identities. A selected native zone appears only in the
native declaration. Rejected alternatives remain on linked evidence pages.
Graphical containment, graph direction and connector geometry grant no permission.
Native solid transitions declare direction and forwarding context, not automatic
permission. Heavy analytical witness rows refer only to actual evaluated atoms.
Every page has the three-layer text legend; colors never carry meaning alone.

There is no automatic analysis. Explicit repeatable `--trace SOURCE:SERVICE`,
`--check`, and repeatable `--scenario ID` regenerate results through the unchanged
trace, intent and exposure APIs on the same immutable validated snapshot. Exact
source, service binding, destination, TCP/UDP, inclusive ports, witnesses, frontier
qualifications and model hash appear in result detail pages. Existing native HTML
or arbitrary old JSON reports are not accepted as analytical input. Comparisons
remain available through the existing command, outside this Explorer contract.
No new evaluator or comparison/quality feature is introduced.

`Not evaluated` and the explicit missing-result sentence never mean denied.
`no_structural_path` and `no_permitted_path` remain exact negative query reasons.
Missing model paths are unassessed; unsupported inputs fail with exit 2. Empty
intent checks make no global security claim. Explorer completion exits 0 even if
an explicitly requested analysis contains failed intents; the outcomes are shown
on the analytical pages. Existing check/exposure command exit codes are unchanged.

## ADR V12-05C — Stable navigation

Full SHA-256 of compact ASCII JSON `[kind, identity]` produces filenames. Source
IDs, qualified candidates, original graph scope/element IDs, reconciliation group
IDs and sorted partition members remain distinct. No display label forms a path.
Case differences and Unicode NFC/NFD spellings stay distinct. Native keys include
entity collection, avoiding namespace collisions. File names are lowercase ASCII,
portable to Windows/POSIX, without reserved names or imported path components.

Source → observation (`#observation`) → candidate → group → decision → native
entity → analytical result is navigable where those links exist. Observation and
candidate share one bounded page. There is no invented entity for rejected evidence.
Asset/interface/zone reverse indexes point to supporting candidates and applicable
exact analyses. Drawn endpoints link to graph nodes and mapped candidates. Every
generated page is parsed and every relative destination/fragment checked before
publication. Reordering irrelevant JSON keys and output relocation preserve bytes.
Native collection ordering is normalized by the existing model validator. Source
array ordering can remain meaningful to ingestion; it is not reinterpreted here.

## ADR V12-05D — Security and privacy

One escaping function handles text and quoted attributes, rejects binary/control/
surrogate characters and bounds displayed text. Imported URLs stay inert text.
Bidi formatting controls display as explicit Unicode code-point markers. Local
drive/UNC, file URLs and common absolute host paths are withheld in display text.
This is a narrowly scoped disclosure filter, not universal secret detection.
Output remains a **local full-detail engineering report**, not public-safe output;
there is no automatic shareable/redacted mode. Original documents, registered paths,
raw unmapped metadata, graph geometry/styles, private receipts and complete control
files are excluded. Selected names, addresses and rationales remain sensitive.

Only renderer-controlled links, classes, SVG elements and attributes are emitted.
Original HTML/SVG is never inserted. No source CSS, script, formula or expression
executes. CSP permits only local CSS and prohibits scripts, connections, images,
objects, forms and base URLs. Escaping and parsed resource audits are independent
of CSP. Local-file CSP/CSS behavior still needs real-browser verification; no
browser guarantee follows from a Python socket-denial guard or markup parsing.

Inputs reject symlink/junction traversal and nonregular files, including ancestors;
reads are bounded. Sidecar parsing checks depth, scalar/array/text counts, duplicate
JSON keys and exact versions. Typed catalog/decision validation, draft/manifest
digests, source IDs/digests, recomputed reconciliation, exact identity/declaration
indexes and native model hash are checked. The shared retained-review validator
regenerates the sidecar and model from saved evidence/decisions without reimport.
Emission still reproduces all original source documents first. Hashes and internal
consistency do **not** authenticate a document or owner, or prove deployed truth.

The whole site is staged beside a fresh destination and parsed before rename.
An existing destination is refused. Any failure removes staging and publishes no
partial site. As with ingestion, publication assumes a local single writer;
hostile concurrent filesystem replacement and crash durability are not promised.

## ADR V12-05E — Scalability and deterministic budgets

Indexes connect native entities, candidates, groups, partitions, graph endpoints
and results once. Large reverse-link collections use dedicated paginated pages.
There is no pairwise similarity matrix or evidence duplication on every page.
Each selected field is rendered on its candidate page; other views use links.
The existing bounded deterministic spatial renderer supplies the native overview.
Its full view supports at most 12 zones, 24 assets, 24 interfaces and 48 edges;
larger inputs show the inherited explicit zone summary, with omission counts and
complete indexed declarations. Explorer reserves dashed relationship lines for
documentary evidence; native forwarding retains its direction and uses solid lines.
Per-zone asset cards show 20 assets and disclose omissions. Relationship diagrams
show at most 20 distinct endpoints and 32 rows; complete text retains all records.
No arrow is added to unknown documentary direction.

| Independent rejection ceiling | Value |
| --- | ---: |
| Native model | Existing schema-1 limits (5 MiB input) |
| Provenance | 40 MiB; depth 40; 1,200,000 scalar/container controls |
| Displayed scalar | 4,096 characters |
| Site files including indexes/assets/manifest | 24,000 |
| HTML or CSS file | 1 MiB |
| Manifest | 4 MiB |
| Complete output | 256 MiB |
| Explicit requested analysis operations | 16 |
| Index page | 60 rows |

Excessive analysis detail can exceed a page budget and fail cleanly. No conflicts
are silently truncated. Budgets are rejection limits, not guaranteed capacity.
Generation timings are stdout/evidence only; canonical site bytes contain no clock,
absolute output path, random IDs, machine-specific separator or locale formatting.
The manifest inventories all content except itself, avoiding circular hashing.
It also records rendered entity/relationship marks aggregated across views (marks
can repeat the same entity), distinct from logical inventory counts.
`python -m benchmarks.explorer --output output/explorer-performance.json` measures
20/30/40, 150/200/250 and 500/600/750 asset/interface/connector workloads, repeated
labels/long rationales, link counts, file/byte/page/SVG sizes, loading/index/render
timings, deterministic reruns and separate traced Python allocation peaks (not RSS).

## ADR V12-05F — Accessibility and verification boundaries

Each page has English language, descriptive title, one H1, main/navigation landmarks,
skip link, visible focus, semantic heading order, table captions/column headers,
focusable labeled overflow regions, SVG titles/descriptions and linked text records.
The system-font layout wraps identifiers and uses responsive cards, ordinary links
and no motion. Core content/navigation requires no JavaScript. Default text/link
palette contrast is checked against all used backgrounds at the 4.5:1 threshold.

HTML/SVG parser tests verify structure, link integrity, inactive hostile labels,
local resources and textual equivalents. These establish structural properties,
not WCAG certification. The available browser tool rejects `file://` navigation;
no policy bypass, local server or browser download is used. Browser keyboard focus,
200% zoom, small viewport rendering, file-origin CSP/CSS behavior, console/network
inspection and assistive-technology review remain explicitly unverified.

## Extension boundary

V12-06 can supply additional reviewed documentary observations through the existing
source-qualified catalog and selected field/location projection. New adapters or
sidecar versions require explicit contract support and validation. The Explorer
must never infer new transport/policy from another documentary format. Optional
document formats, completeness scoring, visual comparison and stable release
publication are outside V12-05.
