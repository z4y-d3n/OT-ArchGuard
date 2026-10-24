# Import projects and reconciliation: V12-04 reference and ADRs

Project support is development version 1.2.0.dev0. It operates entirely on local
files, reusing the accepted CSV/TSV, JSON, XLSX, offline NetBox, draw.io and GraphML
adapters. It supplies no discovery, policy inference, new adapter or visual editor.

## ADR V12-04A: versioned manifest and portable paths

Use a strict YAML or JSON manifest with integer `project_version: 1`, native-syntax
`project_id`, and 1–16 sources. Each source requires `id`, `path`, `adapter`,
`profile`. Optional fields are `model_context`, `aliases` and `preferred_sources`.
Unknown keys, duplicate IDs, recursive source manifests and unsupported versions
fail. Explicit adapters must agree with profile versions and source extensions
where the adapter requires them. Safe XML suffixes retain existing explicit adapter
behavior. Profiles remain their existing versions; a manifest is never a profile.

Paths use portable relative forward-slash spelling beneath the manifest directory.
Absolute/drive/UNC/URL paths, traversal, backslashes, globs, alternate streams,
reserved Windows names, controls, ambiguous dot/space endings, symlinks/junctions
including ancestors, special files, file-ID aliases and case/Unicode-colliding
registered paths fail. Sources cannot overlap profiles, context or the manifest.
One profile can be reused under its single declared path. No includes or discovery
exist. Outputs cannot replace or contain protected inputs. Existing outputs fail.
File handles are checked by the inherited regular-file reader. Concurrent hostile
writers are outside the local single-writer contract; input snapshots are checked
around adapter mapping and reproduced again before emission.

The canonical manifest sorts independent sources and alias member sets. Its SHA-256
is semantic: manifest formatting/key/source-list order can change without renewing
approval. Every source/profile/context binds exact bytes. Source-byte mutations,
including semantically equivalent JSON serialization changes, require renewed review.
Absolute host paths and temporary directories never enter project identities.
Relocation with the same relative paths preserves drafts. Renaming registered files
is a configuration change. Implicit source-list precedence was rejected.

## ADR V12-04B: shared evidence catalog

Project draft version 1 is independent of single-source draft versions 1–4. It
retains each source draft once, including adapter/profile, source SHA-256, exact
numeric tokens, raw/normalized selected fields, locations, transformations,
references, diagnostics, conflicts and graphical pages/nodes/edges. It adds the
source registration and profile-byte SHA-256, context hash, reconciliation groups
and aggregate accounting. It does not duplicate fields into a flattened catalog.
`catalog()` provides a deterministic index over retained observations.

Observation IDs are `source-id::row_id`; candidate IDs are
`source-id::candidate_id`. Proposed canonical IDs remain observed attributes.
Final native IDs exist only in confirmed owner partitions. Connector IDs use
`source-id::edge::SHA256(scope_id, element_id)`; their source graph retains the
original readable page/edge identifiers. No hostname-keyed mutable overwrite exists.
Sidecars retain contradictions and rejected observations, with a compact many-to-one
identity index and final declaration fields. Original source documents are not
embedded. Existing adapter privacy rules remain in force: structured/graphical
unselected metadata is excluded; legacy CSV unmapped cells keep their established
behavior. Labels and selected fields may be sensitive. No universal secret detector
is claimed. Local outputs need the same access control as their inputs.

## ADR V12-04C: exact indexed identity proposals

Indexes use entity family plus exact mapped ID, name or IPv4 host address. Explicit
profile normalization remains recorded; there is no fuzzy score or implicit
case-insensitive merge. A separate NFC/casefold index detects identifier collisions.
Alias sets must contain distinct existing qualified candidates of one family;
aliases are unordered equivalence proposals, not executable or recursive chains.
Overlapping proposals are permitted because they do not form automatic clusters.

Each duplicate key creates one bounded member set, never all-pairs comparisons.
Categorical explanations distinguish `EXPLICIT_ID_MATCH`, `OWNER_DECLARED_ALIAS`,
`EXACT_ATTRIBUTE_MATCH` and `CONFLICT`. Explicit-ID matches also remain proposals.
Disagreement fields are listed. Conflicts include contradictory same-ID fields
(zones, roles, classifications, interface owners/addresses), repeated source
records, ambiguous names with distinct IDs, reused addresses and normalization
collisions. Adapter diagnostics retain unresolved/dangling references and graphical
connectors. A source record ID is not physical identity; no automatic merge exists.

Owner decisions explicitly partition all non-connector candidates. A partition
confirms one entity, keeps observations as `EVIDENCE_ONLY`, or rejects them.
Separate partitions mean keep separate; their final IDs must differ within a family.
Combining members means same entity/accepted alias, with a reviewer and rationale.
`canonical_id` explicitly corrects the identifier. Equal compatible attributes can
complement one another only under that partition's owner confirmation. Different
attributes require `field_sources` (qualified member) or literal `corrections`.
`references` selects an accepted qualified target and uses its final canonical ID.
Rejected/renamed/dangling structured references cannot silently survive.

Missing, null and empty fields remain distinct in original evidence and do not
assert an alternative value. Unsupported/type/formula states require literal
correction or explicit selection of usable evidence. Literal unknown labels remain
literal observations, never arbitrary defaults; invalid native values fail validation.
Different raw values with approved equal normalization preserve both originals.
Owner corrections are retained separately. `preferred_sources` supports the exact
documented entity.field names in `project.py`; it supplies review suggestions only.
It never selects values automatically. Global rankings and freshness authority
were rejected. Serial-number/hostname-specific fuzzy matching is not implemented;
owners can use explicit aliases for additional documented identifiers.

## ADR V12-04D: guided review and exact decisions

`project review` creates unresolved project decision version 1 and a Markdown
report ordered by blocking conflicts, matching proposals, missing native fields,
source diagnostics and evidence-only sets. `--group ID` focuses one group. Reports
escape imported Markdown/HTML; no active imported HTML or spreadsheet export exists.
The summary measures documentation coverage and review state, never deployed
completeness. Generating a template confirms zero entities.

`project resolve` updates exactly repeated `--member` selections, optionally using
`--field-source field=qualified-id`, `--set field=value`, and
`--reference field=qualified-id`. It requires reviewer/rationale and a final ID.
It refuses implicit splitting of a prior partition and resets whole-model
confirmation. `--decision OWNER_REJECTED|EVIDENCE_ONLY` retains explicit alternatives.
No accept-all command exists. Final conflict rationales and whole-model confirmation
remain editable structured decisions; automatic engineering judgment was rejected.

`project acknowledge` explicitly selects one source's complete, bounded connector
set. The CLI discloses count and every selected ID. The output decision records the
exact sorted members, set digest, rationale and draft digest. It neither confirms
the model nor changes entity decisions. Emission requires exactly one valid
acknowledgment per nonempty connector source. Graph connection candidates are
covered by these retained graph sets; non-graph connection candidates form equivalent
source-qualified evidence sets. Neither can become native declarations.

Aliases/profiles are reusable configuration, never reusable approval. Existing
decisions are current only while their exact draft binding remains valid. Reordered
independent manifest entries do not invalidate this contract. Source changes do;
there is no automatic carry-forward or cross-version reinterpretation.

## ADR V12-04E: emission, integrity and budgets

`project emit DRAFT --project MANIFEST --decisions OWNER --output NEW_DIRECTORY`
reopens all original sources/profiles/context, remaps with accepted adapters,
reconciles again, compares the entire reproduced draft, and verifies decisions.
It requires complete disjoint partitions, reasoned conflict resolutions, exact
connector acknowledgments and explicit named whole-model confirmation. Two clusters
cannot claim one final ID. Selected references must have the correct accepted family.
Native context collections and accepted declarations are combined; duplicate IDs
and invalid remaining references are independently rejected by schema 1.

Only assets, zones and interfaces are produced from candidate evidence. Graphical
connectors, arrows, groups, interfaces and inventory cables supply no transport,
forwarding, rules, services or allow/deny policy. An owner may supply these explicitly
in hash-bound native context, governed by the unchanged engine. The native validator
checks both declaration YAML and the normalized published bytes/model identity.
The two-artifact bundle uses the existing staged atomic publication/no-overwrite
mechanism. Local filesystem single-writer/crash-durability limitations remain.

| Project rejection ceiling | Value |
| --- | ---: |
| Manifest bytes | 65,536 |
| Sources | 16 |
| Aggregate source bytes | 16 MiB |
| Evidence items (fields plus graph nodes/edges) | 100,000 |
| Candidates / entity decisions | 5,000 each |
| Proposal groups / conflict groups | 4,096 each |
| Graph connectors | 8,000 |
| Draft/decision JSON bytes | 32 MiB |
| Control events / nesting | 1,200,000 / 40 |
| Sidecar bytes | 40 MiB |

Individual adapter limits remain unchanged, including their 1 MiB source and
5 MiB draft envelopes, graph/XML/ZIP limits and diagnostic ceilings. Each project
source draft remains independently bounded. Project controls use bounded strict
JSON parsing with exact numbers; manifests retain strict bounded YAML. Byte/event
checks occur during parsing and before outputs. Sidecar repeats the source catalog
once plus compact decisions/indexes. Rich per-field evidence remains the principal
space cost. Segmented storage was rejected for this gate because it complicates
atomic review binding without measured need at the tested scale.

Run `python -m benchmarks.projects --output output/project-performance.json` for
small (3 sources, 20 assets, 30 interfaces, 40 connectors), medium (5/150/200/250)
and larger (6/500/600/750) fictional workloads. Candidate counts include repeated
documentary observations. Receipts record per-source/aggregate mapping, serialization,
draft validation, emission, evidence/template/sidecar sizes and deterministic outputs.
A separate small tracemalloc sample measures Python allocations, not process RSS.
Dense duplicate labels are measured as member groups. These are samples, not
capacity guarantees; any tighter inherited source limit can reject a project.

## ADR V12-04F: cross-platform CI and release boundary

The existing native GitHub Actions matrix retains Windows, Ubuntu and macOS with
Python 3.12/3.14, using PowerShell steps, setup-python and the approved dependency
inventory. The full suite includes every project/adversarial test; Ruff, formatting,
strict mypy, dependency consistency and exact wheel/sdist audits remain required.
The workflow additionally installs the built sdist noneditably, verifies all module
hashes and runs focused ingestion suites plus the installed-console project tutorial.
JUnit and installation/tutorial evidence are retained. No expensive second full
suite is duplicated per matrix cell.

Runtime document handling is offline. CI provisioning may acquire approved Python
and build/test dependencies. The inherited socket/DNS/HTTP audit guard remains
enabled for full/focused tests and tutorial subprocesses on every OS; it is not
disabled to accommodate platforms. Paths, Unicode, line endings, archive names,
hashes and no-overwrite output use platform-aware tests. Managed Windows may deny
creating hard links; that test then independently simulates file-ID alias evidence
without disabling the rejection, while unrestricted platforms exercise real links.

Only locally executed Windows results count here. WSL availability probing found
no installed subsystem; Docker/Podman were not available. Hosted Windows/Ubuntu/macOS
runs were NOT EXECUTED by this task. Config review proves readiness to run, not OS
compatibility. Stable v1.2.0 release readiness remains BLOCKED until the final release
candidate passes all six actual hosted combinations, with commit/run/OS/Python,
test counts, failures/skips, artifacts, installed identities and offline-guard
evidence recorded, followed by separate owner publication authorization.
