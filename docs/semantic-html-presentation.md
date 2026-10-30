# Semantic offline HTML presentation

The accepted F1 exposure layout is the production Architecture Explorer view.
Its schema-aware tables and exact appendix are retained. The former
`compact_prototype` Python arguments remain accepted for compatibility but no
longer select a separate layout. There is no new CLI mode or JavaScript.

## Active renderer map

| Renderer/helper | Active callers | Output families | Shape and implementation |
|---|---|---|---|
| `explorer_exposure.exposure_tables` | `Explorer.render_analysis` | Exposure scenarios | Accepted overview, assets, modeled observations, prohibited diagnostics, required ordered witnesses; unchanged schema-aware implementation |
| `explorer_html.structured_value`, `properties`, `table` | `Explorer.value`, `evidence`, `render_native`, `query_page`, documentary renderers | Overview, zones/assets/interfaces/services, declarations, intents, traces, scenarios, source records, candidates/connectors/decisions | Inline associated scalar fields; comparable record tables; independent complex sections; source links retained |
| Same shared helpers | `review_explorer._value`, quality and comparison renderers | Import Studio/project quality, findings, source locations, baseline/proposed declarations, exact evaluated queries and analytical comparisons | Preserves separate sides and result qualifiers; structured records replace recursive properties |
| Same shared helpers | `capture.display.render_value`, `property_list`, `capture.views` | PCAP overview, metadata, coverage, protocol hints, limitations and comparison context | Ordinary identity lists remain lists; nested records use shared semantic layout; exact rational timestamp adapter unchanged |
| `capture.explorer._record_table` | Paginated address/communication/association/finding listings | PCAP Evidence Studio indexes and detail evidence | Original anchored summary rows retained; complex review/binding fields follow at full width; no nested tables in cells |
| `reporting._table`, `_field_values`, `_query_evidence` | `html_report`, `trace_html` | Native validation/check/exposure/comparison, policy evidence, witness/diagnostic trace reports, inventories and omissions | Structured tables and numbered witness rows; global diagnostic and individual edges remain distinct; complete canonical JSON stays in technical disclosure |
| `drift.explorer_render._value`, `pair_value`, `properties`, `table` | Overview/scope, pairs, domain/source pages, findings, native and coverage evidence, verification | Historical Explorer, including dense/incomplete/decoder/revoked cases | Shared semantic fallback retains timestamps, source links, descriptive communication and Modbus labels, exact finding anchors and recorded/current review authority |
| `diagrams.serialize_svg`, `spatial_svg`, Explorer diagram adapters | Native reports, architecture and historical diagrams | Static SVG and legends | Existing satisfactory presentation retained; no engine/layout geometry changes |
| `ingestion.project_review.review_markdown` | Project review/emit workflow | Project Markdown | Previously corrected structured locations/diagnostics and escaping retained; revalidated with existing fictional project |

Repository search found no other active HTML document producer. Console JSON,
canonical JSON serialization and archival fixtures are not HTML renderers.

## Shared layout rules

Simple objects use compact `Label: Value` definition pairs. Uniform collections
use actual tables, with captions, column headers and numbered row headers. Wide
arbitrary schemas are grouped into at most six source columns plus a record
number, without changing record order. Different schemas keep separate record
sections. Structured child values appear outside competing table cells.

Flattened sections retain explicit parent/group/record references. These local
display numbers are not canonical finding or evidence identities. Witness step
numbers always follow input order; source and target endpoint details retain
their exact parent step. Diagnostic reasons are not treated as unique causes.
Empty collections, absent fields, false and zero remain distinguishable.

Primitive identity lists retain list semantics. Recursion into structured values
does not create recursive decorative lists, nested definition lists or tables
inside narrow table cells. Each caller retains its original escaping, source
link, timestamp and resource-limit boundary. Responsive scroll regions are
keyboard focusable and labeled; print tables repeat headers and release screen
minimum widths. The original production safety and output ceilings still apply.

## Historical identity and compatibility

The semantic renderer identifies itself as `1.4.0-historical-explorer.2`.
Its source digest now also binds `explorer_html.py` and `capture/display.py`,
which participate in the emitted presentation. Portable integrity still accepts
the preceding `.1` renderer version; the bundle format remains version 1.
Canonical drift reports, analytical implementation identities, evidence and
review decisions do not change. Regeneration changes presentation/bundle hashes.

## Acceptance evidence

The fresh corpus and detailed Spanish owner checklist are generated under
`output/v144-semantic-html-acceptance/`. Previous outputs are preserved.
Automated structure/link checks are not human visual acceptance. The owner
retains the final decision, including narrow viewports, 200%/300% zoom and print.
