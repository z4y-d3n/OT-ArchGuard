# Gate V12-02 — local development verification

Decision: **V12-02 — PASS; LOCAL DEVELOPMENT ACCEPTED**.
This accepts the documented subsets locally for owner review, not a release.

## Baseline and preservation

Initial/final branch: `codex/v12-ingestion-foundation`. Starting commit
`d95d52ddea1d9789a7b57374673902ed45e700d6`, tree
`9d27f12ce805c8027ab22fe68998d0c344487c2e`, already committed V12-01 with a clean
working tree and no intervening owner changes. V12-01 acceptance remains in its
original report and ignored evidence. The V12-02 changes are a local working slice.

Preserved main/v1.1.0 commit `0ffc7c6ce9a1963b3018c695a6c5748f25a7307e`, tree
`18c17133fe03a3b55c57978b454b85fd2d18fcfc`; annotated v1.0.1 object
`39c855ad6204953495fdca4a7058fd53a3ba8f8c`, v1.1.0 object
`8b3bfe05909eb0f11711e69b466a4fa6b566f8e8`; independent root
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.

## Delivered scope

Strict bounded JSON, explicit multi-sheet XLSX, and selected offline NetBox
envelopes use the existing inspect/preview/map/review/emit workflow. Named tables
map assets, zones and interfaces; connection candidates remain evidence-only.
Profiles explicitly declare types, paths/headers, constants, allowed transforms
and typed within-source references. Every candidate requires owner confirmation
or rejection. Formula caches never become declarations. Missing/type/formula/
reference ambiguity requires literal correction/rejection. Renamed/rejected
targets require explicit dependent correction. Native validation remains final.

Modules: `json_inventory.py`, `netbox.py`, `structured.py`, `xlsx.py`, shared
records/workflow/CLI extensions. The CSV/TSV adapter is unchanged. All 24 prior
non-ingestion modules other than the separate package version declaration retain
their bytes. Native model/trace/report semantics are unchanged.

See [supported subsets and ceilings](v1.2-import-formats.md),
[architecture](v1.2-architecture.md), [ADR](v1.2-design-decisions.md),
[parser decision](v12-02-parser-decision.md), and the real commands and profiles in
[Import Studio](../import-studio.md). Public examples are entirely synthetic.

## Dependencies and development identity

Both approved Windows environments lack openpyxl/defusedxml. Restricted
standard-library ZIP/Expat/ElementTree parsing adds no runtime/optional dependency
or wheelhouse requirement. Python's PSF and Expat's MIT runtime licenses apply; no third-party parser is
bundled. This is intentionally a finite transitional OOXML inventory subset,
with package allowlists, no extraction/fetching, bounded XML and fail-closed
unsupported constructs. It is not full Office compatibility.

Package metadata, console, current-version tests, CI filenames and distributions
use exactly **1.2.0.dev0**. Historical stable comparison fixtures retain their exact
1.0.1/1.1.0 expectations. Published version 1.1.0 remains unchanged.

## Verification

| Check | Actual result |
| --- | --- |
| Full installed-wheel suite, Windows Python 3.12.14 | **1,598 passed**, 0 failures/errors/skips; 377.914 s |
| Full installed-wheel suite, Windows Python 3.14.5 | **1,598 passed**, 0 failures/errors/skips; 395.252 s |
| New coverage over accepted V12-01 | **160 cases**, included in both full runs |
| Installed-sdist focused suite, Python 3.12 / 3.14 | **249 passed each**, 0 failures/errors/skips |
| Ruff lint / format / strict mypy | PASS; mypy checked 81 source files |
| Wheel/sdist archive and dependency audit | PASS; explicit public-file allowlist, source bytes, metadata, licenses and RECORD |
| Regular installed distribution identity | PASS; 34 production modules match source, no editable install, native console 1.2.0.dev0 |
| Offline operation | Full/focused tests inherit socket denial; walkthrough actively verifies that denial |
| Installed structured walkthrough | 27 commands per run: inspect/preview/map/review/emit/validate/check, unresolved review and source mutation |
| Existing documented examples | All 31 commands pass with expected exits in a copied fixture workspace |
| Source/release preservation | 24 native engine modules and all 20,786 retained release files unchanged; V12-01 report preserved |

Full test commands:

```text
.venv-v12-312/Scripts/python.exe -m pytest --basetemp=.pytest_tmp/v12-02-312 --tb=short -q
.venv-v12-314/Scripts/python.exe -m pytest --basetemp=.pytest_tmp/v12-02-314 --tb=short -q
```

Both commands inherited `OTARCHGUARD_OFFLINE_CHECK=1` and `PYTHONPATH=tools/offline`.
Receipt JSON, stdout/stderr and JUnit XML are retained. Installed wheel and source
archive checks use matching production-source hashes; final documentation updates
are followed by a fresh build/archive audit and regular installed CLI checks.
No hosted Ubuntu/macOS result is claimed.

Security coverage includes corrupt/hostile ZIP/XML, unsupported parts, macros,
external links, DTD/entities/processing instructions, depth/element/string/cell/
dimension limits, formula caches, merged/hidden sheets, ambiguous numeric IDs,
strict JSON syntax/types/numbers/Unicode, duplicate keys/IDs, reference cycles,
renamed targets, credential metadata exclusion, stale decisions, source mutation,
no-overwrite/no-partial output and default-deny analytical checks. Offline socket
denial is inherited by test child processes. Existing analytical tests are retained.

Development failures were corrected: IPv4 normalization initially dropped the
native required prefix; tests initially inspected ModelError's generic string
instead of structured diagnostic codes; duplicate IDs also correctly produced
ambiguous reference correction requirements. These preliminary failures are not
accepted results. Critical review also added exact sheet/cell/range locations to otherwise unmapped
formula/merge/hidden-sheet diagnostics. Both full suites were repeated after that
change. Final receipts identify the verified state.

## Performance and limits

Three repeatable V12-01/current runs on the same 1,000-row, 63,828-byte CSV produced
identical 3,190,254-byte drafts. Baseline control loading took 9.877–10.059 s;
the strict JSON control path took 0.563–0.638 s. Mapping medians were approximately
0.285 s baseline and 0.323 s current. This demonstrates faster control loading
for this fixture, not a universal throughput or mapping improvement. JSON uses
the original 5 MiB/depth-32/200,000-event budgets; no provenance was removed.

At 400 assets, JSON source/draft sizes were 36,992/1,664,702 bytes; map/serialize/
control-load times approximately 0.194/0.056/0.292 s. XLSX sizes were
142,387/1,630,843 bytes; times 0.242/0.054/0.334 s. At 100 rows, Python allocation
peaks during mapping were approximately 4.31 MB JSON / 4.56 MB XLSX using
tracemalloc (not total process memory). Dense 1,000-row structured evidence was
rejected at 238,136 events against the preserved 200,000-event ceiling. Repeated
bytes were deterministic. Per-field evidence remains a size/capacity bottleneck.

## Limitations and next gate

Only documented subsets are accepted. XLSX excludes drawings, comments, charts,
macros, embedded objects, defined names, strict OOXML, rendering, date/format
interpretation and formula evaluation. JSON requires explicit arrays/pointers;
arbitrary nested discovery and non-scalar declarations are unsupported. NetBox
support is a combined versioned offline envelope, with one IPv4 per interface;
no API, IPv6, VRF/routing/ACL inference or cable authorization. Unknown values are
excluded in new adapters; mapped sensitive paths fail. CSV's older unmapped-text
contract remains. Hashes are not signatures; publication assumes a local single
writer. Cross-file reconciliation is deferred to V12-04. Windows is the only
locally verified platform; hosted Ubuntu/macOS remain outstanding.

V12-03 prerequisites: a separate bounded diagrams.net/GraphML XML/container
contract, group/shape identity and provenance design, explicit evidence-only
connector mapping, adversarial compressed/XML fixtures, and owner-reviewed native
validation using the same workflow. No V12-03 code was implemented.

All audit evidence lives under ignored `output/v1.2-development/v12-02/`.
No main/tag/release-asset mutation, push, PR, release/PyPI operation, dependency
download, cloud document processing, live NetBox or production-network operation
occurred. No v1.2 tag/release/publication was created.
