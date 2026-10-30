# Historical Evidence & Drift Explorer

The historical Explorer presents an **existing** drift-v1 comparison, after exact
source-dependent reproduction against an existing workspace-v2. It creates no
baseline, approval or analytical comparison. Native engine `1.3.0` and drift
engine `1.4.0-drift.1` retain their accepted semantics.

The v1.4 candidate includes the owner-accepted V14-04 semantic presentation.
Previous browser acceptance applies to the reviewed presentation, while candidate
source/package checks and eventual integrated-source acceptance remain separate.

```console
otarchguard evidence drift explore WORKSPACE REPORT.json NEW_DIRECTORY
otarchguard evidence drift explore-verify NEW_DIRECTORY
otarchguard evidence drift explore-verify NEW_DIRECTORY --workspace WORKSPACE
```

Open `NEW_DIRECTORY/index.html` directly in a local browser. Copy the entire
directory to preserve navigation. HTML, one local stylesheet and bounded static
SVG need no JavaScript, server, font download or network access. `--page-size`
accepts 5..200 records; the default is 50. Counts describe canonical findings,
not severity, incidents or an overall risk score.

Follow Overview → domain → finding → retained evidence → source context. Domain,
category, result status, unchanged support and abstention indexes are static links;
previous/next and first/last links navigate complete paginated records. Full
identities remain available in native disclosures. Diagrams are bounded aids;
tables and record details retain complete access.

## Authority and verification

Generation performs one complete lifecycle acquisition and canonical drift
replay. Exact source/report bytes are checked again before the completion
manifest is published. A historical report remains reproducible after its
reference approval is revoked or superseded; the site separates recorded
approval from the status checked at generation. That status may subsequently
change. Reviews remain unauthenticated local human assertions.

`explore-verify DIRECTORY` checks portable bundle integrity: strict inventory,
file hashes, controlled local links/fragments, HTML/CSS/SVG restrictions and
the versioned presentation identity. It **does not reproduce analytical
meaning or authenticate original evidence**. Hashes provide no signature.
An attacker able to replace the whole bundle can also recompute its hashes.

Adding `--workspace` reproduces the exact retained report from fresh source
dependencies, checks deterministic rendering and returns current approval
separately. It does not rewrite the bundle or authenticate its claimed generation
time/status. Another renderer implementation requires regeneration with the
supported version; it must not silently reinterpret an old presentation.

Exact producer-source binding also applies to stored analytical revisions.
Preserve a compatible development environment for `1.4.0.dev1` workspace replay;
the `1.4.0` distribution transition does not migrate prior analyses or approvals.
Portable integrity checks alone do not remove that
[upgrade boundary](installation.md#historical-workspaces-and-upgrade).

`explorer-manifest.json` independently versions the publication as
`historical_explorer_version: 1`. It binds exact drift bytes/ID, baseline and
approval IDs, source workspace inventory digest, generation verification,
renderer source digest and page-size option. Paths and local clocks are excluded
from deterministic identity. The manifest inventories every emitted member.

The bundle includes exact drift metadata as `report.json` and a lightweight
`verification.json` receipt. No raw capture, process payload or arbitrary source
attachment is copied. Imported report text may itself be sensitive, including
reviewer rationale and internal labels; inspect the whole bundle before sharing.
HTML masks path-like text. Original input paths are never injected by generation.
Do not publish this evidence publicly by default.

## Publication and finite resources

The destination must be fresh, local, outside the immutable workspace and under
an existing directory. Links, junctions and reparse ancestors are rejected.
Exclusive directory/file creation prevents replacement. The manifest is the last
completion marker. A failed/interrupted publication may leave an incomplete
directory for inspection; it cannot pass verification and must not be treated as
a successful site. Choose another fresh destination after resolving the cause.
This is a local single-writer publication protocol, not a filesystem sandbox
against a malicious concurrent administrator.

Presentation and bundle ceilings bound findings, scalar text, nesting, traversal,
pages, local links, diagrams, per-file and total bytes. Excessive input fails with
structured diagnostics; retained findings are never silently dropped. Dense
communication diagrams give way to complete paginated records. Changing page
size changes presentation identity but never analytical counts.

## Interpretation

- Candidate-only/reference-only records describe finite selected observations.
  They do not establish unauthorized traffic, absence, blocking or outages.
- Protocol header recognition, hints and unsupported/malformed/truncated records
  retain their canonical meaning. Write-type metadata does not prove execution.
- Architecture changes describe declarations. Native reachability applies to the
  selected model/query/port interval; it does not prove deployed enforcement.
- Decoder reinterpretation remains separate from physical collection differences.
- Unchanged support and abstentions remain visible. Neither means proven safety.

## Fictional walkthrough and owner review

```console
python -m tools.historical_explorer_walkthrough --output output/my-historical-explorer
python -m benchmarks.historical_explorer --output output/my-explorer-benchmark
```

The walkthrough reuses the V14-03 fictional packet producer. It covers normal
architecture/native changes, incomplete coverage, same-capture decoder changes,
unchanged support, revoked approval and dense pagination. No external captures
or real industrial process are involved.

Review the six criteria and recorded execution evidence in
[the V14-04 handoff](development/v14-04-handoff-es.md). Automated structural and
visual checks do not grant owner acceptance or accessibility certification.
