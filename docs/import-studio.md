# Import Studio

Import Studio is included in [stable v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0).
It supports reviewed CSV/TSV, restricted XLSX, explicit JSON inventories, a
versioned offline NetBox export subset, bounded GraphML and diagrams.net evidence.
Single-source drafts take
one source file; structured profiles can select several collections or sheets.
A separate project workflow combines multiple documents without
merging their authoritative YAML by hand. Start with the
[complete project walkthrough](../examples/import-studio/projects/README.md).
The [project reference](development/v12-04-projects-and-reconciliation.md) documents
manifest/draft/decision contracts, exact CLI commands, explicit owner partitions,
field conflicts and safe hash-bound connector acknowledgment. Existing commands
below keep their single-source behavior.
Restricted UTF-8 TXT/Markdown and transitional DOCX/PPTX text evidence are also supported.
Use profile version 4, explicit `select` collections and optional exact-header
table mappings; drafts use version 5. Project controls retain version 1. Every
nonempty document observation set requires evidence-only owner acknowledgment;
mapped candidates require separate partition/field review and model confirmation.
See the [document tutorial](../examples/import-studio/documents/README.md) and
[format/security/review reference](development/v12-06-document-evidence-and-explorer.md).
Imports remain evidence until the owner confirms declarations. No connectivity or
permission is inferred. Install the published `1.3.0` distribution using the
[installation guide](installation.md). Historical V12 records describe when the
adapters were introduced; they do not make the current implementation unreleased.

## First architecture from a synthetic inventory

Use a regular installed v1.3.0 wheel or sdist and the synthetic files in
[`examples/import-studio`](../examples/import-studio). They are shipped in the
published source distribution, so these commands work outside a Git checkout.
Create an empty working directory, copy the three example files into it, and
ensure its `output` directory exists. The installed `otarchguard` console supplies
the implementation; the source files are only inputs.

```text
otarchguard import inspect assets.csv
otarchguard import preview assets.csv --profile assets-profile.yaml
otarchguard import map assets.csv --profile assets-profile.yaml --output output/draft.json
otarchguard import review output/draft.json --context model-context.yaml --decisions output/decisions.json
```

Inspection lists the table, exact headers, data row count, parser capabilities
and limits. It performs the same bounded parse as mapping but creates no model.
Preview lists every candidate, field evidence, missing/invalid fields, unmapped
values and duplicate-ID conflicts. It never modifies a source. JSON output uses
escaped Unicode and retains original text without executing it.

Open `output/decisions.json` in a text editor. The generated template is always
unresolved. After reviewing the two synthetic rows, explicitly provide:

- `reviewer`: your review identifier.
- `model_confirmed`: `true` only after checking the complete `model` context.
- `model_rationale`: why these declarations and their omissions are acceptable.
- Each resolution: `decision` = `OWNER_CONFIRMED` or `OWNER_REJECTED`, with an
  individual `rationale`. Leave `corrections` empty unless a correction is needed.

Keep the generated `draft_sha256` and candidate IDs unchanged. Do not bulk-accept
unreviewed real inventory. The example context explicitly declares that this is
an inventory-only exercise: no interfaces, communication, listeners or policies.
Its zone and classifications are synthetic owner choices, not parser discoveries.

```text
otarchguard import emit output/draft.json --source assets.csv --decisions output/decisions.json --output output/accepted
otarchguard validate output/accepted/architecture.yaml
otarchguard check output/accepted/architecture.yaml --report output/inventory.html
```

`emit` rereads the original file and reproduces all evidence before accepting
decisions. It then validates the complete model using the original validator.
Success publishes a new directory containing the normalized `architecture.yaml`
and `architecture.provenance.json`. The sidecar binds the native model hash to
the source digest, exact profile, raw fields, transformations, original conflicts,
each owner's decision/correction and final collection/object IDs. Conflicts in
the sidecar remain the original evidence; decisions explain their resolution.
The owner-declared remaining model fields are recorded separately.

`check` on this example succeeds over an empty intent set. That is **not evidence
of any permitted communication**. Add only explicitly reviewed native declarations
before using existing trace/exposure workflows. Current HTML is the existing report;
Single-source provenance remains inspectable as JSON. The V12-05
[Explorer walkthrough](../examples/explorer/README.md) navigates project-version-1
provenance; other sidecars require model-only output without `--provenance`.

## Mapping contract

CSV/TSV profiles are strict version-1 YAML or JSON documents. Headers match exactly;
there is no automatic stripping, fuzzy matching, case conversion or type coercion.

```yaml
profile_version: 1
entity: asset
fields:
  id: Asset ID
  name: Display Name
  role: Role
  zone_id: Zone
constants:
  kind: endpoint
  scope: internal
  domain_classification: iacs
  safety_classification: unassessed
  criticality: unspecified
```

`fields` maps native field name → exact source header. A source ID column is
mandatory; it is never replaced with a slug derived from a display name. One
column maps to one field. `constants` are explicit profile proposals, labeled
`CANDIDATE_INFERENCE` until the owner confirms each whole candidate. A field cannot
have both a column and a constant. Unmapped columns remain evidence, including
addresses or connection notes; they cannot grant permission.

Supported `entity` values:

| Entity | Fields | Emission |
| --- | --- | --- |
| `asset` | Native asset fields | Confirmed rows populate `assets` |
| `zone` | Native zone fields | Confirmed rows populate `zones` |
| `interface` | Native interface fields | Confirmed rows populate `interfaces` |
| `connection` | `id`, `source`, `destination`, `direction`, `label`, `protocol` | Evidence only; explicit rejection required before emitting other owner declarations |

See [schema 1](yaml-schema-v1.md) for required fields and valid enums. Missing or
invalid fields produce review diagnostics. A profile need not fill every field
initially: owners can supply explicit per-row string `corrections`, for example
`{"zone_id": "control"}` or `{"id": "plc_second"}`. Accepted corrections must
satisfy the native entity contract. Rejected rows cannot contain corrections.

The remaining model context must omit every imported collection entirely. All other
native fields are supplied explicitly, including empty sequences where appropriate.
No hidden defaults fill analytical gaps. The original validator decides whether
the resulting model is valid, including references, safety/zone consistency and
resource ceilings. The context can contain explicitly owner-confirmed directional
transport and rules; these are separate from extracted inventory claims.

## Conflicts, identity and review changes

Every row must receive exactly one decision. Unknown/duplicate decisions,
unresolved candidates, blank rationales and repeated accepted IDs block emission.
Reject duplicate rows or correct their IDs explicitly. Identical repeated rows
remain separate evidence. Sharing a name/IP never triggers an automatic merge.

Row and candidate IDs remain stable under row/property ordering and moving the
source to a different directory with the same basename. Physical row/cell
locations and the exact file digest remain in the draft. Reordering rows or
changing line endings changes the draft hash and requires a new review even
when the native accepted model is equivalent. Changing source bytes, mappings,
draft evidence or a stale decision hash blocks emission. Hashes provide change
detection, not signatures or proof of the human reviewer's identity.

## Safety and failure behavior

UTF-8/BOM is the default. A profile may explicitly select `encoding: cp1252` and
`delimiter: ";"`; inspection accepts matching `--encoding` and `--delimiter`.
TSV defaults to a tab. Encoding and delimiters are never guessed. Quoted fields,
commas, Unicode and multiline cells are supported with physical line provenance.
Unknown columns are preserved; duplicate/equivalent headers and ragged rows fail.
Formula-like values receive diagnostics and remain inert strings. This feature
does not export CSV or execute spreadsheet formulas, external links or scripts.

See the [format/limit matrix](development/v1.2-import-formats.md). Data and control
files must be local regular files; leaf symlinks and special files are refused.
All operations are bounded; excessive diagnostics reject the draft. Generated
drafts must also fit the control loader's byte/depth/event budgets. A densely
mapped table can reach its event ceiling before the nominal 1,000-row limit.
Sensitive unmapped values remain in local drafts/sidecars: review before sharing.

Commands return 0 on completed inspection/review or validated emission; invalid
input, unresolved decisions and I/O failures return 2. Import errors are bounded
JSON diagnostics on stderr. No partial valid model is returned. Argument syntax
errors use the CLI's existing usage-error behavior.

Draft/template publication uses atomic no-clobber Windows rename or POSIX hard
links; unsupported filesystems fail safely. Emission stages both artifacts in a
sibling directory and renames once. The destination's parent must exist. Existing
paths are refused; choose a new destination rather than replacing old evidence.
Use a destination dedicated to one writer. Directory publication does not promise
crash durability, distributed-filesystem atomicity or adversarial concurrent-writer
isolation on every platform. A process failure before publication can leave a
hidden staging directory; its contents are not a published validated bundle.

## Related workflows and references

- Excel/JSON-to-first-architecture: the structured workflow below is implemented
  in V12-02, with explicit sheet/collection selection and literal formula corrections.
- draw.io-to-draft: V12-03 extracts shapes/groups/connectors as evidence, without
  translating diagram arrows into forwarding or permissions.
- Several documentation sources: V12-04 project reconciliation retains explicit
  owner partitions, contradictory observations and field selections.
- Architecture Explorer: V12-05 adds static source/asset/interface navigation,
  bounded diagrams, owner-decision links and explicit exact-query regeneration.
- Before/after: existing `compare` evaluates two native declared models. A source
  document change does not itself establish a physical or analytical change.

PDF/VSDX remain unsupported. Explicit declaration/documentary coverage and
before/after review are implemented by `quality` and `compare-architecture`; see
the [quality/comparison tutorial](../examples/quality-comparison/README.md).
The following records preserve the earlier design context:

[architecture](development/v1.2-architecture.md),
[decision record](development/v1.2-design-decisions.md) and
[roadmap](development/v1.2-roadmap.md).

## Structured inventories (V12-02)

The shipped synthetic examples cover all three new adapters. Copy the relevant
source, profile and context from `examples/import-studio` into a writable folder.
Use a regular `1.3.0` installation, with no additional runtime dependencies.
For an approved local wheel and existing runtime wheels, offline installation is:

```text
python -m pip install --no-index --find-links /approved/wheelhouse otarchguard-1.3.0-py3-none-any.whl
```

The wheelhouse must contain the existing Typer, PyYAML, Pydantic dependencies and
their dependencies. No openpyxl/Excel installation or optional extra is needed.

```text
otarchguard import inspect structured-inventory.xlsx
otarchguard import preview structured-inventory.xlsx --profile workbook-profile.json
otarchguard import map structured-inventory.xlsx --profile workbook-profile.json --output excel-draft.json
otarchguard import review excel-draft.json --context structured-context.yaml --decisions excel-owner.json
```

The workbook profile explicitly selects `assets`, `zones`, `interfaces` sheets.
The JSON equivalent selects `/assets`, `/zones`, `/interfaces` arrays:

```text
otarchguard import inspect structured-inventory.json
otarchguard import map structured-inventory.json --profile structured-profile.json --output json-draft.json
otarchguard import review json-draft.json --context structured-context.yaml --decisions json-owner.json
```

Only after editing each unresolved decision, supplying reviewer/rationales and
confirming the model, emit to a new destination:

```text
otarchguard import emit excel-draft.json --source structured-inventory.xlsx --decisions excel-owner.json --output excel-accepted
otarchguard validate excel-accepted/architecture.yaml
otarchguard import emit json-draft.json --source structured-inventory.json --decisions json-owner.json --output json-accepted
otarchguard validate json-accepted/architecture.yaml
```

The explicit NetBox offline contract is selected by its profile, never guessed:

```text
otarchguard import inspect netbox-inventory.json --adapter netbox-offline-v1
otarchguard import preview netbox-inventory.json --profile netbox-profile.json
otarchguard import map netbox-inventory.json --profile netbox-profile.json --output netbox-draft.json
otarchguard import review netbox-draft.json --context netbox-context.yaml --decisions netbox-owner.json
otarchguard import emit netbox-draft.json --source netbox-inventory.json --decisions netbox-owner.json --output netbox-accepted
otarchguard validate netbox-accepted/architecture.yaml
```

The sample demonstrates integer export IDs with explicit `dev_`/`if_` prefixes,
an explicit owner-proposed `control` zone, interface ownership references and
`/@assigned_ipv4` projection. The IP field retains `/ip_addresses/0/address`,
its raw host/prefix and the unique-assignment transformation rule. Sites do not
become zones, roles do not imply filtering, and cable terminations are diagnosed
and excluded. Nothing is fetched or authenticated. Only this versioned combined
export shape is supported, not all NetBox API/export versions.

Version-2 field mapping examples (excerpts; use the complete shipped profiles):

```yaml
profile_version: 2
adapter: json
tables:
  - name: interfaces
    collection: /interfaces
    entity: interface
    fields:
      id: {path: /id, value_type: string}
      asset_id: {path: /asset, reference: {table: assets}}
      placement_zone_id: {path: /zone, reference: {table: zones}}
      ipv4: {path: /ip, normalize: ipv4_interface}
```

`assets` and `zones` must also be selected for those reference targets. XLSX
uses literal sheet names and header strings instead of pointers, and accepts an
explicit `header_row` (default 1). No wildcard or expression language exists.
Unknown profile keys are errors. Every field has an explicit expected type
(`string` by default), optional `normalize`, `prefix`, `missing` and `reference`.
Constants are proposals requiring the same owner confirmation as source values.
Normalization is limited to exact/trim/lower/upper/IPv4 host-with-prefix; no
addresses, prefixes, leading zeros, dates or locale semantics are guessed.

Each new-format field records source value type (including missing/null/empty
containers), allowed raw scalar, proposed value, transformation and pointer/cell.
Mapped nonempty structures are unsupported and their values are excluded. Unknown
fields retain counts, not contents. Sensitive paths such as tokens, notes/comments
and URLs are rejected; mapped authenticated URLs also fail. CSV/TSV retains its
older unmapped-text behavior. Review local evidence before sharing it.

Formula cells report cache presence but exclude both expression and cached value.
Mapped formulas require literal corrections, even if the owner confirms the row.
Styled numeric values, merges, missing fields and type mismatches require the
same correction/rejection. Hidden sheets and external relationships are diagnosed;
external targets are excluded and never followed. Unsupported package parts,
macros, objects, dates/styles needing interpretation and other formats fail closed.

Examples of controlled errors: `IMPORT_JSON_DUPLICATE`, `IMPORT_XLSX_PART`,
`IMPORT_XLSX_RELATIONSHIP`, `IMPORT_NETBOX_REFERENCE`, `IMPORT_PRIVATE_FIELD`,
`IMPORT_MAPPING`, `LIMIT_EXCEEDED`. Unresolved formula/type/reference values block
emission with `IMPORT_CORRECTION`. Renamed/rejected targets require explicit
dependent corrections (`IMPORT_REFERENCE`). Duplicate accepted IDs fail with
`IMPORT_CONFLICT`. Changed source/draft or decision hashes fail with
`IMPORT_SOURCE_CHANGED`/`IMPORT_STALE_REVIEW`, before output publication.

Duplicate IDs, duplicate names and reused IPs are reported; there is no automatic
merge. Native validation remains authoritative, including correction references
and IPv4 host/prefix semantics. JSON key order and excluded metadata do not affect
semantic candidate identity; array position remains relevant. XLSX sheet order
does not affect candidate identity when selected names/content are unchanged.
Every source-byte change still requires a new draft and review. These single-source
commands do not reconcile separate files; use the
[project workflow](../examples/import-studio/projects/README.md) for explicit
cross-file identity/field decisions. See the
[subset and resource budgets](development/v1.2-import-formats.md).

## Exact numeric evidence (V12-02R)

Structured drafts and provenance now use `import_version: 3`. Existing profile
version 2 and decision version 1 remain supported. A version-2 structured draft
returns `IMPORT_LEGACY_DRAFT`: map the original source to a new draft, generate
new decisions and review again. Old rounded evidence cannot be promoted by editing
the version or copying its review hash. CSV/TSV version-1 drafts remain supported.

JSON decimals/exponents retain their exact source lexeme and numeric category in
a tagged raw record. `0.10000000000000001`, `1.00`, `1e-400` and `-0` retain that
spelling as proposed text when explicitly mapped as numbers. Numeric fields do
not accept numeric strings or booleans. Decimal/exponent tokens do not satisfy an
integer-only mapping. Exponents are bounded to ±9999, tokens to 64 characters.
No automatic rounding, truncation or permissions result from these values.

XLSX preserves the number stored in OOXML, which may already differ from what a
person entered in Excel. Styled, precision-sensitive, out-of-range, merged and
formula values still require literal correction/rejection. Underflow `1e-400`
is retained as evidence and requires correction; it never silently becomes zero.
Quoted native YAML text preserves exponent-shaped declarations through validation.
See the [complete numeric policy](development/v12-02r-numeric-policy.md).

For a selected source-review archive from the repository, use a regular installed
interpreter with the regular installed package and new destinations:

```text
python -m tools.review_bundle --output ingestion-v12-02r-review.zip --inventory ingestion-v12-02r-inventory.json
```

The tool reopens the ZIP and verifies selected source bytes and its hash manifest.
It excludes bytecode, environments and development evidence. It retains deliberate
synthetic hostile-input strings in tests; this is a reviewed source selection, not
a sanitizer for arbitrary owner documents or an independently installable project.
The complete source distribution has its separate public-file audit. Review mapped
values before sharing drafts/provenance: path-name filtering cannot identify every
secret concealed in an otherwise allowed scalar.

## GraphML and diagrams.net (V12-03)

The shipped `industrial.drawio`, compressed two-page `multipage.drawio`,
`directed.graphml` and `undirected.graphml` are synthetic industrial topologies.
Copy the source, matching profile and `model-context.yaml` into a working folder
outside the checkout. With a regular installed v1.3.0 distribution:

```text
otarchguard import inspect industrial.drawio
otarchguard import inspect directed.graphml
otarchguard import preview industrial.drawio --profile drawio-profile.json
otarchguard import map industrial.drawio --profile drawio-profile.json --output draft.json
otarchguard import review draft.json --context model-context.yaml --decisions decisions.json
```

Review each proposed asset, its exact source fields, classifications and zone
proposal, plus the graph evidence and complete context. Supply reviewer, model
confirmation/rationale and an explicit decision/rationale for every candidate as
above. The profile constants are owner proposals, not parser discoveries.

```text
otarchguard import emit draft.json --source industrial.drawio --decisions decisions.json --output accepted
otarchguard validate accepted/architecture.yaml
```

For GraphML, use `directed.graphml` with `graphml-profile.json` in the same commands.
For multipage draw.io, copy the profile and explicitly set `scopes` to
`["page1", "page2"]`. For compatible XML inspection, use
`otarchguard import inspect topology.xml --adapter drawio` (or `graphml`).
Standalone mxGraphModel uses explicit scope `standalone`.

Graph profiles use `profile_version: 3`, exact `scopes`, `connections: evidence_only`,
`unknown_policy: diagnose` and the existing named tables/typed fields/constants.
Example node fields are `/scoped_id`, `/label` (draw.io), `/attributes/label`
(GraphML key ID), `/attributes/role`. Only these explicit selections propose
native fields. Use `/id` only when source IDs are suitable native IDs and unique
across selected pages. No expressions, XPath, role guessing or fuzzy matching.

Connectors remain in `graph.edges` even if the profile has no edges table, as in
the shipped profiles. This explicit evidence-retention policy avoids generating
hundreds of rejection-only candidates. The model review covers retained evidence;
no edge becomes a native declaration. An optional `edges` table with entity
`connection` adds individually reviewed candidates that must be explicitly
rejected before emission. Trying to confirm one returns `IMPORT_RELATIONSHIP`:
"Evidence-only connections cannot be promoted."

Groups/layers and parent IDs remain evidence; only an explicit `groups` mapping
can propose zones, with missing native fields corrected and owner confirmed.
GraphML directed/undirected/override values and draw.io arrowheads retain their
own meaning. Neither supplies communication direction or effective reachability.
The synthetic context declares no interfaces, services, rules or transport.
Every emitted model still passes the original schema-1 validator.

Version-4 graph drafts/sidecars retain source bytes/digest, scope, element IDs,
locations, selected attributes, exact numeric tokens, transformation records,
candidates/conflicts and owner resolutions. Serialization reorder/geometry changes
can retain candidate IDs, but every source-byte change invalidates old review.
Limits, unsupported formats and diagnostics are in the
[graphical reference](development/v12-03-graphical-formats.md).
