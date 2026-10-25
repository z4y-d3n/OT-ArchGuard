# Gate V12-01 — development acceptance

Status: **PASS — local Gate V12-01 acceptance; ready for owner review**.
This accepts the implemented CSV/TSV foundation, not a v1.2 release or the later
format/Explorer gates. No publication is authorized or performed.

Baseline commit `0ffc7c6ce9a1963b3018c695a6c5748f25a7307e`, tree
`18c17133fe03a3b55c57978b454b85fd2d18fcfc`. Annotated v1.0.1 object
`39c855ad6204953495fdca4a7058fd53a3ba8f8c`, annotated v1.1.0 object
`8b3bfe05909eb0f11711e69b466a4fa6b566f8e8`, independent root
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.

Clean local main matched all identities before branch creation. Development is
isolated on `codex/v12-ingestion-foundation`. The retained post-publication verdict
records published v1.1.0 and four actual downloaded-archive installations.
The baseline installed Windows Python 3.12.14 suite passed 1,349 tests in 311.37 s.

Implementation: additive `import inspect/preview/map/review/emit`, bounded CSV/TSV
adapter, versioned typed evidence, exact profiles, stable row/candidate IDs,
conflicts, decisions templates, source/draft hash checks, correction/rejection,
native model validation and atomic new artifact bundles. No analytical module
changes or new dependency. Synthetic fixtures and installed-CLI tests are included.
The package allowlist and source manifest include the new public files, and
installed-module verification now recursively checks the new subpackage.

See [architecture](v1.2-architecture.md), [ADR](v1.2-design-decisions.md),
[supported formats and budgets](v1.2-import-formats.md),
[usage](../import-studio.md), and [roadmap](v1.2-roadmap.md).

Ignored evidence is in `output/v1.2-development/v12-01/`. It records baseline,
preserved-release hashes, dependency reuse, tests, distributions and final diff.
Hosted platform CI, additional source formats and multi-source reconciliation
remain future gates. No result from the old release accepts this new source.

## Delivered behavior and changed files

The shared typed pipeline and record boundaries are documented in the ADR. Actual
supported sources are `.csv` and `.tsv`, UTF-8/BOM or explicit CP1252, one table,
explicit delimiter/header mapping. Asset, zone and interface inventories can be
confirmed; connection rows remain evidence-only. Required native fields may be
corrected explicitly in the decision file. Every row requires a reasoned decision;
missing decisions, duplicate identities, invalid corrections and stale evidence
block emission. Confirmed remaining SUC/zone/policy context is supplied explicitly.

New files: five modules under `src/otarchguard/ingestion/`, two ingestion test
modules, three synthetic inputs under `examples/import-studio/`, this report,
four v1.2 development documents and `docs/import-studio.md` (16 files).
Modified baseline files: `src/otarchguard/cli.py` (additive group only), README,
the two explicit package manifests, and recursive installed-module verification
(five files). Existing tests and fixtures were not edited. All 24 existing
production modules other than the CLI remain byte-identical to v1.1.0.

The walkthrough documents actual installed-console commands:

```text
otarchguard import inspect assets.csv
otarchguard import preview assets.csv --profile assets-profile.yaml
otarchguard import map assets.csv --profile assets-profile.yaml --output draft.json
otarchguard import review draft.json --context model-context.yaml --decisions decisions.json
```

After the owner edits and confirms the generated decisions:

```text
otarchguard import emit draft.json --source assets.csv --decisions decisions.json --output accepted
otarchguard validate accepted/architecture.yaml
```

## Verification results

| Check | Actual result |
| --- | --- |
| Baseline installed suite, Windows Python 3.12.14 | 1,349 passed |
| Final development wheel suite, Windows Python 3.12.14 | **1,438 passed**, 0 failures/errors/skips; 347.10 s |
| Final development wheel suite, Windows Python 3.14.5 | **1,438 passed**, 0 failures/errors/skips; 363.34 s |
| Added tests | 89, included in both final full runs |
| Ruff, format check, strict mypy | PASS; mypy checked 74 files |
| Installed provenance | PASS; 30 production modules matched source in each of two new regular wheel installations |
| Dependency consistency | `pip check` passed in both isolated development environments |
| Offline operation | Both full suites inherited the existing socket-denial guard; walkthrough also actively verified the guard |
| Installed import walkthrough | Seven commands passed; emitted native model validated with matching sidecar hash |
| Existing documented examples | All 31 commands completed with their expected exits in a copied fixture workspace |
| Distribution contents | Wheel and sdist passed the explicit public-source/archive audit |
| Determinism | Repeated drafts/emissions identical; row/header/profile ordering retained candidate identities; source changes required fresh review |

Main final test commands (with the existing offline guard inherited):

```text
.venv-v12-312/Scripts/python.exe -m pytest --basetemp=.pytest_tmp/v12-full-312 --tb=short -q
.venv-v12-314/Scripts/python.exe -m pytest --basetemp=.pytest_tmp/v12-full-314 --tb=short -q
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
```

Exact commands, environments, exits, elapsed times, stdout/stderr and JUnit XML
are retained in ignored receipts. Old v1.1.0 verification environments and release
assets were not reused as development installs. No dependency download occurred.

## Adversarial review and corrected failures

Coverage includes duplicate/equivalent headers, ragged/empty rows, malformed
quotes/encodings, Unicode and multiline provenance, binary/control text, field/
row/column/cell/byte ceilings, diagnostic overflow, generated draft event budgets,
hostile YAML tags/aliases/duplicate keys/depth, formula-like and markup text,
special-file/leaf-symlink guards, stale or edited drafts, invalid/duplicate/missing
decisions, unsupported relationships, native reference/safety validation,
no-overwrite publication, staging cleanup and forbidden bundle member names.
A default-deny trace test proves accepting inventory does not grant a permission.

Preliminary failures are retained and resolved: Windows hard links were denied,
so Windows now uses no-overwrite rename; a test safety context was corrected to
satisfy the unchanged validator; oversized pytest parameter IDs exceeded Windows'
32,767-character environment limit and were given short IDs. Initial copied-tool
and sandbox Temp installation probes were corrected by reusing approved static
tools and forcing no-index installation with workspace-local Temp. Installed
source hashes caught an initially retained old same-version package. No failing
attempt was classified as a passing gate; the two final full runs passed.

## Resource observations and limitations

A synthetic 1,000-row inventory (63,828 source bytes) generated a 3,190,254-byte
draft in 0.298 s, with identical repeated bytes. Parsing that draft through the
bounded control loader took 10.812 s under concurrent test load. These are local
observations, not throughput or peak-memory guarantees. Dense per-cell provenance
can hit the control event ceiling below 1,000 rows and is rejected before writing.

Current limitations: one source/table per draft; no source merging, JSON inventory,
XLSX, diagrams, document or vendor configuration import; no automatic connectivity,
rule or service generation; no new Explorer/provenance HTML view. Owner metadata
and remaining model collections are explicit. Full native validity does not imply
documentary or deployed completeness. Review hashes detect changes but are not
signatures. Output assumes a local single writer; no crash-durability or hostile
concurrent-writer guarantees are made. POSIX hard-link behavior and hosted
Ubuntu/macOS runs have not been executed in this session. The existing six-way
Windows/Ubuntu/macOS × 3.12/3.14 CI matrix remains intact for later hosted review.
Only wheel installations were exercised here; sdist installation belongs to the
later package acceptance gate.

Schema 1, trace/report version 1, default deny, directed transport/forwarding,
deny overrides, interval semantics and model identity hashing remain unchanged.
No migration is required for native models. Import controls have their own
version 1. Runtime/core dependencies and Python compatibility are unchanged.
Development metadata remains 1.1.0 temporarily, with explicit documentation that
these private builds must not replace or be published as the stable distribution.

## Acceptance and next gate

All first-gate acceptance criteria are satisfied locally. The retained baseline
evidence includes the published annotated tag and actual downloaded-archive
verification. All **20,786** retained release files matched their recorded hashes;
all 38 previous test/fixture files and 24 non-CLI production modules are unchanged.
Both historical annotated tags, main and the independent root are preserved. This slice is
ready for owner review as a coherent local development commit.

Next: **V12-02 — XLSX and JSON integration**, beginning with a documented JSON
inventory/export subset and safe explicit sheet/table selection. Acceptance must
cover multi-sheet cell provenance, hidden/merged/formula/external-link diagnostics,
bounded containers and cells, a versioned offline NetBox-like subset, deterministic
identity/conflicts, unchanged review/validator boundaries, and adversarial tests.
Select an optional workbook parser only after its license, Python versions,
security and offline-installation implications are reviewed. New dependency/tool
downloads need separate owner approval; none is needed to review this gate.
Version governance should also explicitly establish a development identity and
coordinate its exact-version tests before distributing any future candidate.

No main rewrite, tag movement, remote Git mutation, release/PyPI publication,
dependency acquisition, private-data upload or production-network interaction
occurred. v1.2.0 was not tagged.
