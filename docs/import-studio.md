# Import Studio — unreleased v1.2 foundation

Gate V12-01 imports **one CSV/TSV inventory** into a reviewed schema-1 model.
It records source evidence separately from declarations. It does not discover a
network or infer permissions. The published v1.1.0 wheel does not contain these
commands. This development branch retains baseline version metadata; do not
distribute its builds under the published release identity.

## First architecture from a synthetic inventory

Use an installed development wheel and the synthetic files in
[`examples/import-studio`](../examples/import-studio). They are shipped in the
development source archive, so these commands work outside a Git checkout.
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
the new provenance is inspected as JSON. Explorer crosslinks are planned V12-05.

## Mapping contract

Profiles are strict version-1 YAML or JSON documents. Headers match exactly;
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

The remaining model context must omit the imported collection entirely. All other
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

## Following gates and scenarios

- Excel-to-first-architecture: V12-02 will add explicit sheet selection and cached
  formula handling to this same review pipeline. XLSX is currently rejected.
- draw.io-to-draft: V12-03 will extract shapes/groups/connectors as evidence, without
  translating diagram arrows into forwarding or permissions.
- Several documentation sources: V12-04 will reconcile source identities and
  contradictions using owner decisions; current mapping takes one file.
- Architecture Explorer: V12-05 will add stable source/asset/trace links and explicit
  legends for source, declaration and analytical evidence.
- Before/after: existing `compare` evaluates two native declared models. A source
  document change does not itself establish a physical or analytical change.

These are planned scenarios, not claims of current format support. See the
[architecture](development/v1.2-architecture.md),
[decision record](development/v1.2-design-decisions.md) and
[roadmap](development/v1.2-roadmap.md).
