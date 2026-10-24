# V12-06 document evidence and compact Explorer

## ADR V12-06A — Documentary formats

Development version remains 1.2.0.dev0. TXT, Markdown, transitional DOCX and
transitional PPTX have restricted offline structural readers using the standard
library. Extension, package manifests, namespaces and selected collections must
agree. No Office application, renderer, OCR, converter or network is used.

| Adapter | Retained subset | Structural locations |
|---|---|---|
| txt | Strict UTF-8 with optional BOM; nonempty lines; explicitly requested `key=value` mapping | `text` / `line:N`; `key-values` with original line pointer |
| md | Line paragraphs, ATX headings, simple lists, inert fences; rectangular pipe tables | `text` / `line:N`; `table:N` / `line:N/cell:N` |
| docx | Direct body paragraphs, built-in `Heading1`–`Heading9` style IDs, rectangular tables | `word/document.xml` / `paragraph:N`; `word/document.xml/table:N` / `row:N/cell:N` |
| pptx | Explicit presentation slide order, direct text shapes and simple DrawingML tables | `slide:SLIDE_ID`; record retains part, order, shape ID, paragraph or row/cell |

Word run text joins without inserted spaces; tabs and explicit breaks become tabs
and newlines. Paragraphs within a table cell join with newlines. This is a
documented structural transform, not rendered layout. Markdown cells retain the
text between delimiters; whitespace normalization requires an explicit profile
transform. Fenced text, embedded HTML, links, images and YAML-looking text are
inert evidence. Escaped pipes/code spans in recognized Markdown tables and ragged
mapped tables fail closed. Other pipe-containing lines remain text with a
diagnostic. There is no Markdown HTML interpretation or link/image resolution.

Word drawings, images, symbols, embedded objects, content controls, dynamic fields,
tracked changes, nested tables and table merges are rejected.
Foreign inline XML/alternate content and positional tabs are also rejected;
footnote/endnote/comment reference markers are diagnosed as excluded.
Common styles, settings, numbering, font/theme, header/footer and footnote/endnote XML can be
validated but are excluded with part diagnostics. Layout metadata is excluded.
PPTX layout/master/theme XML is validated and diagnosed, without inherited text
extraction. Direct connectors, groups and other non-text shapes are excluded with
shape diagnostics. Charts/SmartArt graphic frames without a supported table are
excluded. Notes, media, embedded files and other unallowlisted package parts are
rejected. Text extraction is not OCR, visual connectivity or complete coverage.

PDF is deferred. No PDF parser is an approved project runtime dependency; adding
one would change the distribution and require dependency/security review, including
encrypted input and extraction resource isolation. Availability of a document
viewer elsewhere on the workstation does not supply a distributable parser.
VSDX is deferred: no independently validated Visio pages/shapes/connections adapter
or fixtures exist. ZIP/XML similarity to DOCX is insufficient. `import inspect`
returns `IMPORT_DOCUMENT_UNSUPPORTED` for these formats. Neither optional deferral
waives the four mandatory adapters.

## ADR V12-06B — Secure parsing

`ingestion.ooxml.read_parts` is extracted from the accepted XLSX archive boundary;
XLSX keeps its format-specific OPC validation and all previous tests. DOCX/PPTX
reuse that exact ZIP boundary and `XmlBudget`. No filesystem extraction occurs.
Before tree allocation the parser checks member count, accumulated declared
expanded size, ratio, encryption, compression method, unsafe names, duplicate or
case-colliding names, special files and allowlisted parts/directories. Reads are
bounded and actual member size/CRC is checked. All XML, including unselected parts,
consumes one cumulative depth/element/name/attribute/text budget per package.
UTF-8 is required; DTDs, entities and processing instructions are forbidden.

External document relationships fail closed. Internal targets are resolved only
against already validated package members; encoded/URL/special targets and missing
parts fail. Main and slide references have exact type/context checks. No recursive
relationship traversal occurs. References back to the interpreted main document,
slide-to-slide cycles and malformed slide ordering fail; ordinary layout/master
metadata links are not interpreted as content or recursively followed.

Default document ceilings: 1 MiB input, 8 MiB expanded ZIP, 256 members, ratio 100,
XML depth 32, 150,000 cumulative elements, 2 MiB cumulative XML character/name/
attribute budget, 4,096 characters per observation/line, 4,000 lines/observations/
cells, 2,000 paragraphs, 64 tables and 128 slides. Native mapping remains capped
at 1,000 candidates per source. Existing project ceilings add 16 sources, 16 MiB
aggregate source bytes, 100,000 evidence items, 5,000 candidates, 32 MiB draft and
40 MiB sidecar. These are bounded rejection ceilings, not capacity promises for
every combination. Binary/control/surrogate text is rejected; bidi formatting is
rendered visibly in Explorer. No general secret scanner is claimed.

## ADR V12-06C — Evidence, mapping and review

Single-source profile version 4 and draft version 5 are additive. Existing versions
retain their meaning; project manifest/draft/decisions/provenance remain version 1
and embed the versioned source drafts. `DocumentEvidence` contains exact selected
text, category, structural location and deterministic observation identity. Its
validator rejects duplicate or mismatched identities and inconsistent coverage.
Project source qualification distinguishes equal local locations in different
documents. SHA-256 covers the complete original source, including unselected text.

An explicit `select` chooses `*` or exact collection names. A version-4 profile can
have zero tables and retain evidence only. Optional `tables` reuse existing
`TableMapping` and `FieldMapping`: exact table/header row, RFC 6901 single-header
paths, explicit transforms/constants and existing within-source references. Only
asset, zone and interface candidates are allowed. There is no text-to-hostname,
IP, protocol, topology, forwarding or permission detector. Original observation
text, selected field values, normalized values and owner corrections stay separate.

Project inspection/preview includes per-document counts, selected locations,
candidate counts and unsupported diagnostics. Standalone inspection includes at
most ten observation previews and twenty locations. Mapped candidates participate
in existing explicit identity proposals and conflict resolution. Every nonempty
document observation set needs a named owner evidence acknowledgment, bound to
its exact qualified members. `import project acknowledge` handles documents and
existing connector sets; this never confirms the model or any candidate. Mapped
candidate partitions still require independent review, field selection and final
model confirmation. Project emission reopens and reproduces all sources/profiles/
context; old decisions fail after any source change. The existing validator is
the only route to a native model. Saved provenance is independently reproduced
before Explorer generation, without reopening the originals.

## ADR V12-06D — Compact representation

Explorer contract 2 keeps native details, analysis, source pages and paginated
indexes. Candidate, group, decision, node, connector and document observation
records share bounded pages. Each record keeps its full semantic digest anchor;
local nested anchors are namespaced by that digest. Buckets start at one digest
nibble, separated by record type, and split recursively at 24 records or 384 KiB
estimated body bytes. Minor insertions affect only their bucket; a split can move
that bucket's physical paths. There is no positional global renumbering.

The manifest's `locations` maps every renderer semantic digest filename to its
current relative page/fragment. Native IDs, qualified candidate IDs and observation
IDs retain their meaning. All generated links are rewritten from the same index,
then audited against actual files and unique fragments. Older sites stay readable
as their original standalone directories. Old detail bookmarks are not guaranteed
in a newly generated contract-2 site; no thousands of redirect files are emitted.
Consumers must check `explorer_version`; version-1 manifests are not reinterpreted.

The validated native model, analyses, rejected alternatives, conflict rationales,
owner decisions, provenance fields and documentary connectors remain available.
Document → observation → explicitly mapped candidate → decision → native links use
exact field locations, never fuzzy text matching. Reverse indexes avoid repeated
scanning. Model-only output explicitly discloses unavailable provenance.

Grouped pages have a privacy notice: sharing one page includes its other records.
The site remains sensitive local documentation and has no public-safe redaction
mode. Share the entire original folder with relative paths/CSS intact. Browser
“Save Page As” copies are not canonical. A separate portable ZIP helper is deferred;
ordinary archiving must retain the whole folder without rewriting links.

## ADR V12-06E — Browser and accessibility verification

The available browser tool was asked to open the original generated `index.html`
using `file://`. Its URL policy rejected the protocol, permits only HTTP(S), and
explicitly prohibits alternate surfaces/workarounds for that action. No loopback
server, alternate browser route, security change or dependency download was used.
Actual browser CSS/CSP rendering, keyboard focus, 200% zoom, narrow viewport,
table scrolling, console/network behavior and assistive technology are **NOT
EXECUTED**. Static parsing does not establish those behaviors or WCAG certification.

Executed tests cover semantic headings/main/navigation, skip links, focus CSS,
captioned tables, focusable scroll regions, SVG descriptions, palette contrast,
inert labels, no scripts/external resources, duplicate anchors, rewritten crosslinks
and deterministic output. Manual Windows checklist: open the original folder's
`index.html`; confirm CSS; follow source/candidate/decision/native and fragment
links; Tab through skip/navigation/overflow regions; verify visible focus, 200%
zoom and narrow-window wrapping; scroll wide tables; inspect developer console and
network panel for errors/requests; review with assistive technology separately.

## ADR V12-06F — Performance and disk footprint

The exact accepted workloads retain the same input/model/sidecar digests. The
500-asset baseline has 7,705 pages: 3,102 candidates, 1,102 decisions, 1,102 native
details, 1,000 groups, 750 connectors, 504 nodes, 115 reverse lists, 19 asset/
interface index pages, six source pages and five other pages. Full before/after
breakdowns and timings are in ignored acceptance evidence.

Measured preparation output: 20 assets 290 → 139 pages; 150 assets 2,264 → 805;
500 assets 7,705 → 2,446. Medium/larger reductions exceed 40%. Corresponding bytes
are 1,288,878 → 1,067,166; 10,975,616 → 8,590,313; 38,711,323 → 29,956,457.
Fresh final measurements, including all stage timings and allocations, bind the
acceptance verdict; preparation receipts alone cannot accept final code.

Link auditing inventories regular files once instead of statting each link. Site
bytes remain deterministic; timings stay outside site bytes. Existing output
ceilings remain 1 MiB HTML/CSS, 4 MiB manifest, 256 MiB total and 24,000 records/files.
Buffered bodies consume the original total-byte ceiling before compaction; a
single overbudget record fails rather than losing evidence. Grouping adds modest
buffering; peak allocations are measured independently with tracemalloc, not RSS.
The public document benchmark records three timing samples, profiled parsing/
mapping, evidence/draft sizes and separate allocation samples at 20/150/500 notes.

`python -m tools.development_disk --output NEW_JSON` is report-only and never
deletes. Caches/environments can be regenerated; current verification environments,
owner files, Git history, published release files and historical gate evidence
must be retained unless the owner separately approves exact cleanup paths.
No bulk cleanup is performed. Historical acceptance directories are preserved.
