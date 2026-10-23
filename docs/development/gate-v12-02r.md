# V12-02R — remediation and pre-graphical-import hardening

Local development decision: **V12-02R — PASS; READY FOR V12-03 DEVELOPMENT**.
The decision is valid only with the fresh `final-01/acceptance.json` described
below, whose verifier executes every required command against this final source.
Earlier receipts alone cannot establish acceptance. V12-03 was not implemented.

## Baseline and preserved history

Initial branch: `codex/v12-ingestion-foundation`; HEAD
`d95d52ddea1d9789a7b57374673902ed45e700d6`; HEAD tree
`9d27f12ce805c8027ab22fe68998d0c344487c2e`.
The working slice contained 17 modified tracked and 17 untracked public files.
Its canonical public-file manifest exactly matched accepted V12-02 identity
`c0bd5b71eb8e009775021acb932dc1867a3123b8ad20fc223e38485c55e5b925`.
No subsequent owner changes were detected; nothing was restored blindly.
`initial-baseline.json` is read-only and records full status, file hashes and refs.

Preserved main/v1.1.0 commit: `0ffc7c6ce9a1963b3018c695a6c5748f25a7307e`;
stable tree: `18c17133fe03a3b55c57978b454b85fd2d18fcfc`.
Annotated tags remain `39c855ad6204953495fdca4a7058fd53a3ba8f8c` (v1.0.1)
and `8b3bfe05909eb0f11711e69b466a4fa6b566f8e8` (v1.1.0).
The independent root remains `8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.
The closing verifier rehashes all 770 initial V12-01/V12-02 evidence files,
20,786 preserved release files, both earlier gate reports and the copied accepted
public source. No commit, push, remote PR, tag or release operation was performed.

## Findings and corrections

| Risk | Reproduced finding or resolved assessment | Disposition |
| --- | --- | --- |
| R-001 | JSON binary64 conversion rounded evidence before identity/review and could emit changed values | Exact token/category representation; no float in evidence |
| R-002 | XLSX underflow could emit zero; existing precision guards retained already-rounded raw evidence | Preserve OOXML token; keep ambiguity guards and require correction outside Excel normal range |
| R-003 | Reported manual ZIP contained bytecode; original was unavailable locally | New allowlisted ZIP builder and actual-output audit; previous actual wheel/sdist separately passed |
| R-004 | Old version-2 structured drafts cannot establish original numeric spelling | Explicit rejection/remap/renewed review; no hash migration |
| R-005 | Numeric category/coercion boundary required explicit adaptation | Strict tagged validation; float/Decimal/nonfinite and control coercion tests; native types unchanged |
| R-006 | Existing structured privacy controls worked in reviewed cases | Preserved, with explicit sharing limitations |
| R-007 | Existing ZIP/XML and workflow controls reassessed | Budgets and fail-closed restrictions retained; R-010/R-011 corrected |
| R-008 | Changed source required new installed-distribution acceptance | Fresh builds, noneditable installs, source hashes and executed tests |
| R-009 | Hosted Ubuntu/macOS not executed | Outstanding release/platform requirement; local development acceptance only |
| R-010 | 19,046 XML bytes generated 3,093,001 expanded-name characters while charging zero against the 2 MiB text ceiling | Charge expanded names/namespaces before tree allocation, with bounded name lengths |
| R-011 | Sheet IDs `1` and `01` evaded duplicate detection | Compare bounded ASCII uint32 identities; reject aliases and invalid IDs |
| R-012 | Exact exponent-shaped text emitted plain by PyYAML was rejected by native loader | Importer-local safe dumper quotes text in both validation passes |

The machine-readable risk register includes evidence, root cause, impact,
remediation/limitation, regression test and final-run binding for every entry.
No additional defect was asserted merely because a conversion or parser existed.
R-012 failed closed; the eight initial failing tests and the benchmark harness's
diagnostic-serialization failure are retained. Corrections were rerun successfully.

Production changes are limited to ingestion: new `numbers.py`; number callbacks in
`json_inventory.py`/`xlsx.py`; raw-value/category validation in `records.py`;
exact mapping/reference text and draft version in `structured.py`; legacy guards
and quoted YAML emission in `workflow.py`. `tools/review_bundle.py`, two new test
modules, the structured numeric assertions, public manifests and current development
docs complete the change. There are 19 changed/added public files relative to the
accepted V12-02 snapshot. The 25 non-ingestion modules, including version metadata,
are unchanged. Native schema 1, model identity, deny precedence/default deny,
transport/forwarding/ports and trace/report contract 1 are unchanged.

## Numeric fidelity and migration

See [exact numeric policy](v12-02r-numeric-policy.md). Canonical integer tokens stay
exact integers. `-0` and decimal/exponent tokens retain a bounded immutable tag:
`{"numeric_token":"1.00","numeric_category":"number"}`. Source category is
never relabelled string. Proposed native text follows only explicit profile
transforms; quoted YAML preserves that text through the unchanged native validator.
No unsupported Decimal instance enters Pydantic/JSON/native contracts.

| Source token | Previous observed behavior | Corrected JSON | Corrected XLSX |
| --- | --- | --- | --- |
| `0`, `-0` | Negative zero lost its sign | Preserve distinct lexemes/categories | Preserve stored token |
| `0.1` | Binary64 representation | Exact token; ordinary decimals supported | Exact stored token |
| `0.10000000000000001` | JSON normalized/emitted `0.1`; XLSX raw rounded | Exact raw/proposed/reviewed text | Exact raw; precision correction required |
| `1.0`, `1.00`, `1e3` | Scale/exponent spelling could change | Retain each original token | Retain each stored token |
| `1e-400` | JSON and XLSX emitted `0.0` | Exact nonzero token | Exact raw; magnitude correction required |
| `1e309`, `1e-9999` | Rejected or underflowed due binary64 range | Compact finite exact tokens | Exact raw; magnitude correction required |
| `9007199254740993.0` | Rounded to `9007199254740992.0` before review | Exact token | Exact raw; precision correction required |
| Long integers/decimals | Integer JSON was already exact; decimal conversion could round | Exact within 64 characters | Exact raw; existing >15-digit guard remains |

Tokens use strict JSON numeric grammar, at most 64 characters, with explicit
exponents ±9999. They never expand to fixed-decimal form. `NaN`, infinities,
malformed numbers and larger tokens/exponents fail. Decimal/exponent tokens do not
satisfy integer-only mappings; bool/null/number/string remain distinct. Pydantic
rejects floats/Decimal instances and invalid numeric tags. Numeric controls cannot
coerce versions, model confirmation, owner corrections or native integer ports.
Lexical differences bind candidates/drafts and stale review is rejected. Source
dictionaries imitating the tag remain unsupported objects.

Structured drafts and sidecars use version **3**; profiles stay version 2,
decisions version 1, CSV/TSV drafts version 1 and package `1.2.0.dev0`.
Version-2 structured drafts return `IMPORT_LEGACY_DRAFT` on load/review/emit.
Remap the original source and renew review; rounded evidence is not upgraded.
Source reproduction and decision digest checks are unchanged.

XLSX tokens establish only what OOXML stores. No recovery of original Excel user
entry/display precision is promised. Styles, dates/errors, merges, >15-digit
ambiguity, unsupported magnitude and formulas require correction/rejection.
Expressions/caches remain excluded even when a formula cache exists.

## Security and privacy review

JSON duplicate keys, strict UTF-8/Unicode, numeric grammar and byte/depth/string/
record/field/scalar/container limits are exercised. Explicit RFC 6901 pointers have
no include/evaluation semantics. No number is an expression or a source filename.

XLSX checks central-directory names, duplicates/case conflicts, member types,
compression methods/ratio, cumulative decompression, package parts/relationships,
XML encoding/depth/elements/text/names, shared strings, cells and unselected parts.
DTD/entities/processing instructions, external workbook parts and unsupported
constructs fail closed. External relationship targets are excluded and never
followed. No extraction, formula execution, style interpretation or Office service
occurs. Namespace expansion and sheet identity reproducers now reject under the
actual default limits. Dense evidence still reaches original control ceilings.

NetBox requires the explicit offline format/version. Integer/string IDs, duplicate
identities, typed references, VLAN bounds, IPv4 prefix/assignment uniqueness,
missing/reused/unsupported addresses and evidence-only cables are tested. Sites,
roles and cables never imply zones, forwarding or ACLs. No live NetBox access.

Shared workflow tests cover rereading the source, full draft reproduction, source/
decision hashes, missing/duplicate/unresolved decisions, invalid corrections,
identity conflicts, renamed/rejected reference targets, no automatic confirmation,
native validation, provenance/model hashes and no-overwrite/complete publication.
No analytical engine refactor or policy inference was introduced.

Unknown structured values retain counts only. Sensitive mapped paths and
authenticated URLs are rejected; formulas/caches/external targets are omitted.
This is not universal secret detection: an allowed mapped scalar may contain
sensitive text, and CSV retains its historical unmapped-text contract. Owners must
review drafts/provenance before sharing. Local acceptance records contain actual
environment paths intentionally and are excluded from the shareable review ZIP.

The replacement ZIP contains exactly 20 selected public source/test/license files
and one generated relative-path hash manifest. It excludes bytecode, environments,
staging, private docs and development evidence. Tests compile real marshal bytecode
with local `co_filename` and verify exclusion; actual ZIP reopening checks CRC,
regular member modes, approved names, source bytes, manifest and private home/root
paths including escaped spelling. Deliberate synthetic hostile paths remain in
tests; this is not a sanitizer for arbitrary documents. Earlier wheel/sdist were
independently audited without inferring that stable v1.1.0 was unsafe.

## Fresh verification and package identity

The final run uses Python **3.12.14** and **3.14.5**, Windows AMD64. Existing approved
dependencies were copied into four fresh isolated environments without fetching
anything; otarchguard itself was installed from fresh wheel/sdist artifacts.
No editable installation or source-path test fallback is accepted.

The final procedure requires:

- 1,734 full-suite cases per installed wheel interpreter, with zero failures,
  errors or skips; 136 more cases than V12-02.
- 385 focused cases per installed sdist interpreter across all six ingestion/review
  modules; narrower sdist coverage is explicit. These include actual numeric CLI
  mapping/review/correction/emission/native-validation workflows.
- Ruff lint/format check, strict mypy (85 source files), `git diff --check`, exact
  wheel/sdist public manifest audit and dependency checks in all four environments.
- Matching installed bytes for all 35 production modules, application/distribution/
  console version, interpreter and direct installation artifact SHA-256.
- 27 documented structured CLI commands and 31 existing example commands on each
  wheel interpreter, including rejection before review and stale-source failure.
- Fresh numeric matrix, before/after benchmark, actual review ZIP audit and closing
  source/history/evidence preservation assertions.

`accept_final.py` refuses existing run directories and executes all these stages;
it cannot manufacture acceptance by rereading earlier PASS receipts. Every command
records argv, actual exit code, elapsed time, stdout/stderr hashes and identical
public-source identities before/after execution. JUnit case totals and failures
are inspected, and all final source/test/build/install manifests must agree.
Build/install/test/CLI subprocesses inherit an opt-in socket/DNS/HTTP audit guard;
negative probes verify it. No dependency download, network interaction, remote Git
mutation or external service was used.

The final public-source digest includes this report, so it is stored outside the
hashed source to avoid a self-reference: `final-01/frozen-source.json` and
`final-01/acceptance.json` contain the exact canonical digest and per-file hashes.
Artifact digests are in `final-01/sanitized-artifact-manifest.json`. The changed-file
inventory distinguishes this remediation from the cumulative uncommitted V12-02
slice; no local commit is created. The acceptance record, not a Git commit, binds
the final working source.

## Performance

The reproducible harness uses the preserved accepted source and corrected installed
modules in separate guarded subprocesses, identical synthetic input hashes, the
same Python 3.12 host and three samples per case. Parse and serialization are
separate; mapping includes a fresh parse, load includes the draft file write, and
emission includes reread/remap/review/two native validations/serialization but no
publication. Separate tracemalloc samples measure Python allocations, not process
RSS or native allocations. Final raw samples are retained, without a universal
speed/capacity claim.

Preparation medians before → after (seconds) were:

| Fixture | Parse | Map including parse | Serialize | Load | Emit |
| --- | --- | --- | --- | --- | --- |
| CSV, 1,000 rows | 0.0235 → 0.0206 | 0.2949 → 0.3078 | 0.1063 → 0.1106 | 0.5719 → 0.6200 | 3.1159 → 3.1206 |
| Numeric JSON, 100 rows | 0.0014 → 0.0018 | 0.0320 → 0.0428 | 0.0107 → 0.0110 | 0.0748 → 0.0771 | 0.3143 → 0.3055 |
| Numeric XLSX, 100 rows | 0.0096 → 0.0107 | 0.0393 → 0.0426 | 0.0104 → 0.0109 | 0.0711 → 0.0758 | 0.3294 → 0.3222 |
| Numeric JSON, 400 rows | 0.0029 → 0.0050 | 0.1258 → 0.1363 | 0.0423 → 0.0466 | 0.2564 → 0.2657 | 1.2747 → 1.2463 |
| Numeric XLSX, 400 rows | 0.0391 → 0.0368 | 0.1884 → 0.1740 | 0.0458 → 0.0470 | 0.2783 → 0.2702 | 1.3969 → 1.2984 |

The original 3,190,254-byte CSV draft remains byte-identical; corrected load samples
were 0.591–0.625 seconds, comparable to the earlier gate's 0.563–0.638 seconds.
The 100-row JSON draft grew 381,619 → 390,959 bytes; XLSX 389,028 → 398,048 bytes.
Mapping peaks grew 3,932,795 → 4,046,119 bytes (JSON) and 4,098,726 → 4,207,602 bytes
(XLSX); emission peaks grew 4,117,149 → 4,247,772 and 4,292,667 → 4,419,637 bytes.
The added exact tags cost about 2–3% evidence/allocation size in these fixtures.
Both before and after reject dense 1,000-row structured drafts at the unchanged
200,000-event ceiling. Short extreme exponent tokens remain compact; no exponent
expansion or budget relaxation was introduced. Final-run benchmarks repeat the
same measurements after source freeze; their raw values are authoritative for
that run, while this table identifies its preparation measurement explicitly.

## Evidence and next gate

All new local evidence is under `output/v1.2-development/v12-02r/`:
initial baseline, accepted source copy, before numeric/security reproducers,
separate earlier-distribution audit, environment inventory, retained failed
attempts, performance preparation and the final verification scripts. The
`final-01/` directory contains command receipts/JUnit, frozen source manifest,
fresh artifacts/audits, installed identities, numeric results, security-test
summary, risk register, performance samples, review ZIP/inventory, changed-file
and preservation records, sanitized artifact manifest and acceptance JSON.

Reproduce using the available isolated development Python and a **new** run name:

```text
python output/v1.2-development/v12-02r/accept_final.py final-new-run
```

It requires the prepared offline environments and preserved fixtures; it does not
download or create a new execution host. Do not rerun historical gate drivers into
old evidence directories. Failed runs remain evidence and require a new run name.

Local remediation is ready for V12-03 development once the source-bound final
acceptance record passes. Hosted Ubuntu/macOS checks remain outstanding before
cross-platform release. The restricted OOXML subset, finite budgets, legacy remap,
sharing limits and local publication concurrency/crash-durability limits remain
explicit. No live source, universal parser-security or deployed-completeness claim
is made. This task stops at V12-02R; graphical import remains unimplemented.
