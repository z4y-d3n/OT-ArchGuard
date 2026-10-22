# Gate V11-1 — Correctness, reliability and regression hardening

Local engineering verification performed on 2026-10-22. This report concerns a
development candidate only; application version 1.0.1 and YAML schema 1 remain
unchanged. No release publication is authorized by this gate.
This revision incorporates the owner's requested correction of V11-1-F01 before
gate acceptance; the prior AUD-01-only evidence remains separately retained.

## 1. Initial Git and environment state

The authoritative checkout was `OT-ArchGuard-CLEAN`, initially clean on `main`
tracking `origin/main`. HEAD, the sole ancestry root and the `v1.0.1` tag all
resolved to `8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`. The configured fetch/push
remote was `https://github.com/z4y-d3n/OT-ArchGuard.git`. Work continued on the
local branch `codex/gate-v11-1`, without committing, pushing or changing tags.

The observed platform was Windows 11, build 10.0.26100. Explicit interpreters
under the checkout were used throughout:

| Environment | Executable relative to checkout | Observed Python |
| --- | --- | --- |
| 3.12 | `.venv-verify312/Scripts/python.exe` | 3.12.14, AMD64 |
| 3.14 | `.venv-verify314/Scripts/python.exe` | 3.14.5, AMD64 |

Both initially imported `otarchguard` from their own `Lib/site-packages`, with
distribution version 1.0.1 and a `direct_url.json` identifying the original local
wheel. Neither was editable. All 21 installed production Python modules matched
the initial source byte for byte. The Windows `py -0p` launcher found no registered
interpreters, so it was not used for verification. The historical 608-test result
is a supplied release baseline; the new full-suite results below are separate
observations.

The F01 follow-up began on the same `codex/gate-v11-1` branch with the earlier
gate edits still uncommitted. Both environments then had the regular local
`1.0.1.dev2+gate.v11.1` candidate installed. HEAD, root, tag and original archive
checksums were rechecked before changing the scanner boundary.

## 2. Confirmed reproduction

Before production edits, replace `revision: initial` in the synthetic
`tests/fixtures/minimal-valid.yaml` with the ASCII YAML text
`revision: "\uD800"`. Its bytes are valid UTF-8; the YAML escape becomes an
isolated surrogate in the parser's scalar value.

On **both installed baseline environments**, `validate_bytes` raised
`UnicodeEncodeError` (`surrogates not allowed`). The native installed launcher
returned exit 2 and `execution_error` / `INTERNAL_ERROR`. Fifteen native scenarios
per interpreter covered `validate`, `check`, `exposure`, each comparison input,
and no report / JSON / HTML. Stdout was empty, there was no traceback, and existing
binary report sentinels remained unchanged. This independently reproduces AUD-01;
it does not indicate a graph-reachability defect.

For F01, both installed `dev2` environments were independently exercised with
`revision: "\U00110000"` and `revision: "\UFFFFFFFF"`. The former raised
`ValueError` on both interpreters. The latter raised `OverflowError` on Python
3.12.14 and `ValueError` on Python 3.14.5. All 30 native scenarios per interpreter
returned exit 2 with `INTERNAL_ERROR`, empty stdout and unchanged report sentinels.
This new installed reproduction supplements the earlier archive-import finding.

## 3. Root cause and shared API routes

`load_bytes` strictly decodes UTF-8, checks bounded YAML events, then constructs
primitive keys and values through `_build` and `_scalar`. PyYAML 6.0.3 accepts
surrogates produced by `\u` and `\U` escapes. Text fields preserve these Python
characters through schema parsing, structural validation and normalization.
`canonical_bytes` serializes with `ensure_ascii=False`, then UTF-8 encoding fails.

`validate_file` uses `load_file` -> `load_bytes`; `check_bytes` / `check_file` and
`exposure_bytes` / `exposure_file` call the validation APIs. `compare_bytes` and
`compare_files` validate both snapshots through the same APIs. CLI report paths
also use these validated entry points. A single scalar-boundary correction covers
all these routes before canonicalization or analysis.

F01 occurs earlier: PyYAML 6.0.3's pure-Python
`Scanner.scan_flow_scalar_non_spaces` verifies eight hex digits, computes the
integer, then calls `chr(code)` before advancing past the digits. Out-of-range
values therefore raise at a known reader position before any scalar event exists.
The same `chr(code)` call produces different exception types on the tested
interpreter versions. The directive-recognition rescan uses the same scanner and
also needs the correction.

## 4. Implementation decisions

`loading._scalar` now rejects any character in the inclusive range U+D800–U+DFFF
before scalar resolution. It raises the existing `ModelError` through `fail`:

```json
{"category":"invalid_input","code":"INVALID_TEXT","column":11,"line":3,"location":"$.revision","message":"Text must contain only Unicode scalar values; surrogate code points are forbidden."}
```

The check runs for keys **before** constructing a path containing that key, and
for scalar values at their existing model path. Invalid keys therefore identify
their containing mapping. One-based line/column coordinates identify the start
of the YAML scalar. The fixed ASCII message never includes malformed text.
Existing CLI diagnostic serializers already use ASCII-safe JSON, including for
valid non-ASCII ancestor keys, so they required no change.

There is no repair, Unicode normalization, broad encoding-exception catch,
serializer change, new dependency or new limit. The parser still classifies raw
invalid UTF-8 and independently rejected YAML characters as `YAML_SYNTAX`.
Existing unsupported-model, declaration, resource, I/O and execution categories
are preserved. Direct construction of internal domain objects is not an
untrusted-input API; those objects retain their existing caller obligations.

For F01, a private `_StrictLoader` subclass adds one scanner-method adapter.
Only `ValueError` and `OverflowError` from the superclass's quoted-scalar scanner
are inspected. Conversion to `ScannerError` requires **all** of the following:

- The scanner is processing a double-quoted scalar.
- Its current mark has a source buffer and two preceding characters available.
- Those preceding characters are exactly `\U`, followed at the current pointer
  by exactly eight hexadecimal digits representing a value above U+10FFFF.

Every other exception or scanner state is re-raised unchanged. The adapter does
not search raw input for escape-looking substrings, alter text, monkeypatch
PyYAML globally, or duplicate the scanner. Both event passes and the directive
scan explicitly select this loader. The existing `MarkedYAMLError` handler then
provides the existing safe message, root location `$`, and the first hex digit's
one-based line/column. For the revision fixture the diagnostic is:

```json
{"category":"invalid_input","code":"YAML_SYNTAX","column":14,"line":3,"location":"$","message":"Malformed YAML; check syntax at the reported location."}
```

Surrogate escapes that reach scalar construction still produce `INVALID_TEXT`.
Ordinary malformed escapes keep `YAML_SYNTAX`; valid U+10FFFF and literal
backslash text retain their existing interpretation. Event/depth/byte checks,
schema parsing, canonicalization and analysis remain unchanged.

## 5. Modified and added files

| File | Purpose |
| --- | --- |
| `src/otarchguard/loading.py` | Scalar surrogate guard plus the narrowly guarded scanner adapter used by all parsing/scanning passes. |
| `tests/test_unicode.py` | New loader, public API and independent canonical-byte regressions. |
| `tests/test_unicode_cli.py` | Installed native CLI/report matrix for surrogates and out-of-range escapes. |
| `docs/yaml-schema-v1.md` | Clarify Unicode scalar requirements and diagnostics; schema remains 1. |
| `docs/v1.1/gate-v11-1.md` | Public engineering completion report. |
| `MANIFEST.in`, `tools/public-files.txt` | Explicitly include the new public report and test files. |

Local scripts, candidate packages, captured baseline bytes and verification logs
remain under ignored `output/gate-v11-1/`. They are not public distribution
payloads. Existing release documents retain their historical meaning.

## 6. New regression coverage

The original AUD-01 stage added 262 cases. The F01 follow-up adds 113 further
cases: 83 loader/API tests and 30 additional native CLI matrix cases. The combined
gate coverage is 375 cases: 285 loader/API/canonical tests and 90 native CLI cases.
One case additionally enumerates **all 2,048 surrogate points**.
All 375 focused cases passed against each final regular installed candidate.

Coverage includes high/low exact boundaries and interior points, both YAML escape
widths, lowercase escapes, root scalars, mapping keys, nested lists, names,
descriptions, revision and ID fields, both file/byte APIs, both comparison inputs,
and deterministic source locations. Escaped surrogate pairs are rejected without
being combined. U+D7FF, U+E000, U+FFFF, U+10000, U+1F600 and U+10FFFF remain valid
where accepted by YAML. Spanish, multilingual and combining text are retained,
including currently accepted XML-incompatible scalar values.

Canonical expectations are computed from an already ordered synthetic declaration
using the standard JSON encoder and SHA-256, without production normalization or
hash helpers. Composed and decomposed text keep different bytes and hashes.
Raw malformed UTF-8 retains its parser diagnostic. Existing tests continue to
exercise valid native exit codes 0 and 1, unsupported models, resource limits,
graph and policy semantics, escaped reports and deterministic witnesses.

F01 tests independently assert exact diagnostics for U+110000, U+110001,
0x7FFFFFFF, 0x80000000 and 0xFFFFFFFF, including lowercase hex, mapping keys,
nested values and root scalars. Every byte/file entry point and each comparison
side is covered for both required escapes. Valid U+10FFFE/U+10FFFF, extra literal
characters after a valid escape, `\u`/`\x` widths, escaped backslashes, comments,
plain/single-quoted/block scalars, truncated/nonhex escapes, directive precedence,
byte-limit precedence and parser-error preservation through the rescan are tested.
Injected unrelated `ValueError`, `OverflowError` and `RuntimeError` instances must
escape unchanged, even when the source contains an invalid escape later in the
scanner's processing. These test expectations do not call the adapter to compute
expected values.

## 7. Before/after behavior

| Observation | Original installed 1.0.1 | Installed development candidate |
| --- | --- | --- |
| Surrogate byte API | Raw `UnicodeEncodeError` | Structured `ModelError` |
| Native category/code | `execution_error` / `INTERNAL_ERROR` | `invalid_input` / `INVALID_TEXT` |
| Native exit | 2 | 2 |
| Stdout / traceback | Empty / absent | Empty / absent |
| Existing JSON/HTML report | Preserved | Preserved |
| Valid-model canonical and analytical outputs | Captured baseline | Exact match |

For F01 the installed `dev2` before-state was raw `ValueError`/`OverflowError` at
the API and `execution_error` / `INTERNAL_ERROR` at the CLI. The correction yields
structured `ModelError` with `invalid_input` / `YAML_SYNTAX`, root location `$`,
line 3 / column 14 for the minimal revision fixture, and native exit 2. The native
regressions require empty stdout, no traceback/internal fallback, deterministic
stderr and unchanged absent/existing reports and directory snapshots.

## 8. Valid-input preservation evidence

Before the fix, both baseline installations produced identical fingerprints for
16 inputs: the minimal fixture, all seven documented example YAML files, and
eight text variants. For every input, observations retained canonical bytes,
model SHA-256, SVG, and JSON/HTML for validation, check, exposure and self-comparison.
All **176 fingerprints** matched the original 3.12 baseline in the original 3.14
installation and both changed installations. Comparisons include report analysis
payloads; they are not limited to hashes of input text. The full suite and example
walkthroughs also verify comparisons between different snapshots.
The F01 follow-up repeated the same complete 176-entry comparison on both
installed `dev3` candidates; both matched the original baseline exactly. F01's
30 installed native observations per interpreter separately confirmed the new
scanner diagnostic while the 15 AUD-01 observations retained `INVALID_TEXT`.

Representative unchanged model SHA-256 values:

| Input | SHA-256 |
| --- | --- |
| Minimal fixture | `66f0739f9cea30a3c2a90f226eea5360596027c6a0c9c6c777ca170ac5799be8` |
| Spanish revision and first asset name | `78167586cb748a31b4a782a7ae9ab9ed4c190e674c3010120fcf00f3e75eacf5` |
| Supplementary U+1F600, U+10000, U+10FFFF | `334ad2897db1ae9adf79610ccfc0585818d4449e84ce021f69459bd9c22806b6` |
| Combining `e` + U+0301 | `d21b3c125fe5b0e5b893de895f28426ed3c769481c1ac8062e5223cbd3b0214a` |
| U+0000, U+0001, U+FFFE, U+FFFF inside prose | `c7b7dcfba1126a02759330ef4b38e935fafd0ac836e9d8e3368995d150c13baf` |

## 9. Installed-package integrity (FE-02)

A wheel was built in an ignored staging directory with distribution version
`1.0.1.dev3+gate.v11.1`, then installed using `--no-index --no-deps` in each
verification environment. Only the staged `pyproject.toml` version changed for
packaging. Reviewed production module bytes, including `__version__ = "1.0.1"`,
were copied unchanged. The development metadata intentionally distinguishes this
local wheel from the published release; it is not a release-version claim.

Candidate wheel:

```text
otarchguard-1.0.1.dev3+gate.v11.1-py3-none-any.whl
SHA256 8a106d465758b6bd3f20346e4cb690ee353886c13c950cc142f0a24ed6da5048
```

On each interpreter, verification recorded `sys.executable`, `sys.prefix`,
distribution metadata, the complete installed package inventory, `direct_url.json`
and the actual imported module directory. Imports resolved to that interpreter's
`Lib/site-packages/otarchguard`, never `src/otarchguard`; editable metadata was
absent. Independently calculated SHA-256 maps for **all 21 production modules**
matched the reviewed source exactly, including the corrected loader. Native
commands used the same environment's `Scripts/otarchguard.exe`, resolved through
`sysconfig`, from separate working directories with spaces.

An independent ZIP-level comparison also matched all 21 wheel modules to source,
and verified license bytes and the unchanged runtime requirements. The public
allow-list and `MANIFEST.in` matched all 93 tracked or newly introduced public
files exactly; ignored local candidates and evidence were excluded.

Baseline and candidate environment records are separate. The initial source-only
202-test run and F01's 285-test source-only run are explicitly development
evidence, not installed-package acceptance. Original `candidate312/` and
`candidate314/` records describe `dev2`; F01 final evidence uses `f01-312/` and
`f01-314/` for the distinct `dev3` installation.

## 10. Python 3.12 verification

The prior AUD-01-only `dev2` candidate passed 262 focused tests and 870 full tests.
The final `dev3` candidate, including F01, passed on Python 3.12.14:

| Check | Observed result | Native exit |
| --- | --- | --- |
| Focused new regression suite | 375 passed in 93.77 s | 0 |
| Full regression suite | 983 passed in 213.88 s | 0 |
| Ruff lint | `All checks passed!` | 0 |
| Ruff format | `72 files already formatted` | 0 |
| Strict mypy | `Success: no issues found in 49 source files` | 0 |
| Pip dependency check | `No broken requirements found.` | 0 |
| Installed integrity / baseline observation | 21 matching modules; 176 matching fingerprints; 15 controlled native failures | 0 |
| F01 installed observations | Both API failures are `ModelError`; all 30 native failures have exact `YAML_SYNTAX` diagnostics and preserve reports | 0 |
| Offline example walkthroughs | All 27 installed native commands returned their expected 0/1 exits | 0 |

## 11. Python 3.14 verification

The prior AUD-01-only `dev2` candidate passed 262 focused tests and 870 full tests.
The final `dev3` candidate, including F01, passed on Python 3.14.5:

| Check | Observed result | Native exit |
| --- | --- | --- |
| Focused new regression suite | 375 passed in 100.43 s | 0 |
| Full regression suite | 983 passed in 223.15 s | 0 |
| Ruff lint | `All checks passed!` | 0 |
| Ruff format | `72 files already formatted` | 0 |
| Strict mypy | `Success: no issues found in 49 source files` | 0 |
| Pip dependency check | `No broken requirements found.` | 0 |
| Installed integrity / baseline observation | 21 matching modules; 176 matching fingerprints; 15 controlled native failures | 0 |
| F01 installed observations | Both API failures are `ModelError`; all 30 native failures have exact `YAML_SYNTAX` diagnostics and preserve reports | 0 |
| Offline example walkthroughs | All 27 installed native commands returned their expected 0/1 exits | 0 |

## 12. Static analysis and dependency consistency

The environments retained the approved verification versions: pytest 9.1.1,
Ruff 0.17.1, mypy 1.20.2, types-PyYAML 6.0.12.20260906, setuptools 84.2.1,
PyYAML 6.0.3, Pydantic 2.14.1 and Typer 0.27.3. Pip was 25.0.1 on Python 3.12
and 26.1.1 on Python 3.14. Runtime dependency declarations are unchanged.

Ruff checks the complete repository; strict mypy uses the existing configuration
covering `src`, `tests`, `benchmarks` and `tools`. No runtime or mandatory
development dependency was added. Candidate installation was offline and reused
the already installed dependency set. Final per-interpreter outcomes appear above.

## 13. Native CLI, report failure and offline verification

The 90 native matrix cases per interpreter cover four surrogate boundaries and
the two F01 escapes, five input positions (including each comparison side), and
three output modes.
Each runs twice: with an absent output and then an existing binary sentinel.
The assertions require exit 2, empty stdout, exactly the expected diagnostic,
identical stderr across runs, no traceback or `INTERNAL_ERROR`, and an unchanged
directory-content snapshot. This proves no successful partial report, overwrite
or unintended temporary-file residue. Strict `PYTHONIOENCODING=ascii:strict`
exercises Windows-safe diagnostic output.

All native tests and walkthroughs run with the existing opt-in Python network
audit guard inherited by child processes. The complete suite also verifies that
the guard rejects socket construction and name resolution. This is evidence of
offline behavior within the tested Python operations, not an OS network-isolation
or operational-security certification.

## 14. Security and compatibility implications

Invalid surrogate text is rejected before schema interpretation, canonical UTF-8,
model hashing, analysis and report creation. It cannot be echoed into an unsafe
diagnostic key path. Existing report writing and exception classification remain
unchanged. All accepted scalar values retain their original characters.

Application version, schema 1, ownership/placement, explicit forwarding,
default-deny/deny-overrides, port intervals, deterministic BFS, intent evaluation,
exposure/comparison, report interpretation and resource ceilings remain unchanged.
No network feature, SVG layout change, policy-hygiene feature or new CLI command
was implemented. Apache-2.0 and third-party notices are preserved. This work makes
no standards-certification, deployment-security or operational-safety claim.

## 15. F01 resolution, limitations and failed attempts

**V11-1-F01, now corrected within the owner's expanded gate authorization:**
Before the scanner adapter, PyYAML raised before emitting
a scalar for numeric escapes above U+10FFFF. `"\U00110000"` raises `ValueError`
on both interpreters; `"\UFFFFFFFF"` raises `OverflowError` on 3.12 and
`ValueError` on 3.14. This was independently reproduced through the original
wheel imported directly as an archive, and the installed changed candidate.
The archive-import experiment is explicitly not installed-release evidence.
Invalid hexadecimal `"\uZZZZ"` remains a controlled `YAML_SYNTAX` error.
These out-of-range escapes never reach `_scalar`. The guarded scanner adapter
now routes them through `YAML_SYNTAX` without classifying unrelated failures as
input errors. Verification uses the actual installed PyYAML 6.0.3 implementation
on both interpreters; it is not a claim about every future scanner implementation.
If that dependency changes its conversion state, these regressions must be rerun.
No output-cleanup or path-race defect was observed in the affected tests.

The earlier remote published-release verification remains **not verified**: the GitHub connector
required reauthentication; the web lookup could not access the endpoint; the
sandboxed HTTP attempt failed DNS resolution; an unsandboxed read-only REST GET
returned HTTP 404. This does not establish remote asset absence or identity.
Local archive checksums and the local release tag were verified independently.
No GitHub settings, tags, Releases or files were written.

Relevant failed attempts and resolution:

- The normal PowerShell startup profile emitted unrelated access errors; further
  commands used `login=false`.
- Creating a local branch required sandbox escalation for `.git`; the approved
  retry succeeded without changing history.
- The local observation script initially imported `architecture_svg` from the
  wrong module; correcting the import allowed both baseline captures to complete.
- Two long test lines failed the first Ruff check; Ruff formatting corrected them
  before installed verification.
- The first installed candidate (`1.0.1.dev1+gate.v11.1`) passed 870 tests on each
  interpreter but failed strict mypy because YAML source marks are typed as
  optional. Explicit optional-mark handling resolved both errors without changing
  normal parser locations. Evidence from that attempt remains in
  `attempt1-312/` and `attempt1-314/`; the subsequent `dev2` candidate passed the
  earlier gate stage. The F01 follow-up uses `dev3` and fresh installed verification.
- Pip initially failed moving the launcher into the sandbox's external temporary
  directory. Retrying with `TEMP`/`TMP` under ignored workspace output installed
  the candidates successfully. The failed uninstall's `~tarchguard` rollback
  directories were removed after verifying their exact paths were inside the two
  local verification environments. Dependency verification follows this cleanup.
- F01's two new `validate_bytes` regressions were deliberately run against the
  pre-fix installed `dev2` candidate: both failed with the original Python 3.12
  `ValueError`/`OverflowError`, proving they detect the defect. They passed in the
  subsequent 285-test source run. The captured red run remains in
  `f01-red-tests.log`. Ruff corrected import ordering and test formatting before
  installed F01 verification.

No private reference or historical research material was accessed or introduced.
The gate does not publish, tag or approve a release.

## 16. Commands and retained evidence

Commands ran from the authoritative checkout using PowerShell without its startup
profile. Initial inspection included:

```powershell
git status --porcelain=v1
git branch --show-current
git rev-parse HEAD
git rev-list --max-parents=0 HEAD
git remote -v
git tag --list
git rev-list -n 1 v1.0.1
git switch -c codex/gate-v11-1
py -0p
Get-FileHash dist/* -Algorithm SHA256
```

Local baseline observation commands (executed before the fix and replacement
installs) were:

```powershell
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
.venv-verify312/Scripts/python.exe output/gate-v11-1/observe.py baseline312
.venv-verify314/Scripts/python.exe output/gate-v11-1/observe.py baseline314
```

The source-only check used `PYTHONPATH` set to the resolved `src` directory and
ran the following; that override was not used for installed acceptance:

```powershell
.venv-verify312/Scripts/python.exe -m pytest tests/test_unicode.py -q --basetemp=output/gate-v11-1/source-tests --tb=short
.venv-verify312/Scripts/python.exe -m ruff format tests/test_unicode.py
```

F01 reproduction and source-only checks additionally ran:

```powershell
.venv-verify312/Scripts/python.exe output/gate-v11-1/f01_observe.py before-f01-312
.venv-verify314/Scripts/python.exe output/gate-v11-1/f01_observe.py before-f01-314
.venv-verify312/Scripts/python.exe -m pytest tests/test_unicode.py -k 'out_of_range_escape_public_apis and validate_bytes' -q --basetemp=output/gate-v11-1/f01-red-tests --tb=short
.venv-verify312/Scripts/python.exe -m pytest tests/test_unicode.py -q --basetemp=output/gate-v11-1/f01-source-tests --tb=short
```

The first two commands recorded their stdout in corresponding `.log` files.
The red regression run intentionally exited 1 with two failures. The source-only
run used the resolved `src` directory as `PYTHONPATH` and exited 0 with 285 passes.

After staging the runtime sources and uniquely versioned packaging metadata,
the final F01 wheel build and installation commands were:

```powershell
.venv-verify312/Scripts/python.exe -c "import os; from setuptools import build_meta; os.chdir('output/gate-v11-1/package'); build_meta.build_wheel('../artifacts')"
New-Item -ItemType Directory -Force output/gate-v11-1/temp312 | Out-Null
$env:TEMP = (Resolve-Path output/gate-v11-1/temp312).Path
$env:TMP = $env:TEMP
.venv-verify312/Scripts/python.exe -m pip install --no-index --no-deps --force-reinstall 'output/gate-v11-1/artifacts/otarchguard-1.0.1.dev3+gate.v11.1-py3-none-any.whl'
.venv-verify312/Scripts/python.exe output/gate-v11-1/verify.py f01-312
```

The 3.14 installation used the identical commands with `312` changed to `314`.
The local verification driver saved the exact executable/argument arrays and
native exit codes in each `f01-*/checks.json`, with separate stdout/stderr
logs. Its expanded 3.12 checks were:

```powershell
.venv-verify312/Scripts/python.exe -m pytest tests/test_unicode.py tests/test_unicode_cli.py -q --basetemp=output/gate-v11-1/f01-312-focused --tb=short
.venv-verify312/Scripts/python.exe output/gate-v11-1/observe.py f01-312
.venv-verify312/Scripts/python.exe output/gate-v11-1/f01_observe.py f01-312
.venv-verify312/Scripts/python.exe -m pytest -q --basetemp=output/gate-v11-1/f01-312-pytest --tb=short
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
.venv-verify312/Scripts/python.exe examples/run_examples.py
```

The 3.14 checks used the identical commands with `312` changed to `314`.
The driver set `PYTHONPATH` to `tools/offline`, `OTARCHGUARD_OFFLINE_CHECK=1`,
`NO_COLOR=1` and `TERM=dumb`. The earlier archive-import boundary observations
and the current independent release/source boundary check ran:

```powershell
.venv-verify312/Scripts/python.exe output/gate-v11-1/related.py
.venv-verify314/Scripts/python.exe output/gate-v11-1/related.py
.venv-verify312/Scripts/python.exe output/gate-v11-1/boundary.py
git diff --check
```

Each baseline/candidate evidence directory contains environment metadata, module
hash maps, observed API/native diagnostics, full captured outputs and the 176-entry
fingerprint map. These ignored files are retained for local owner review; they
are not needed to run the new regression tests. A fresh checkout cannot
reconstruct the historical captures from the changed source alone.

## 17. Acceptance checklist and release boundary

All nine verification stages passed on each final `dev3` candidate. AUD-01 and
V11-1-F01 are corrected and locally verified. Owner acceptance remains pending;
no commit or release action is performed by verification.

- [x] AUD-01 reproduced against both original regular installations.
- [x] Shared input boundary rejects every surrogate code point with `INVALID_TEXT`.
- [x] Relevant byte/file APIs raise structured `ModelError`.
- [x] All native commands, including each comparison input, return exit 2.
- [x] Absent and existing JSON/HTML reports and directory contents are preserved.
- [x] Safe deterministic diagnostics; no traceback, partial success or internal fallback.
- [x] Independent canonical-byte/hash tests and 176 before/after fingerprints match.
- [x] Final full 983-test suites pass on both supported Python versions.
- [x] Ruff lint/format, strict mypy and `pip check` pass on both versions.
- [x] Native installed walkthroughs and guarded offline execution pass.
- [x] Regular installation, unique development metadata and all module bytes verified.
- [x] Application/schema versions, dependencies, resource limits and notices unchanged.
- [x] Public source manifest matches all 93 intended files; no private material added.
- [x] Original local archives, approved history root, release tag and ancestry unchanged.
- [x] V11-1-F01 reproduced on both interpreters and corrected under explicit authorization.
- [x] Out-of-range escapes produce deterministic `YAML_SYNTAX`; unrelated scanner failures retain their original exception identity.
- [ ] Remote published asset identity independently reverified: unavailable, see section 15.
- [ ] Owner acceptance, commit or any subsequent release action: pending authorization.

The original local release artifacts have the following unchanged SHA-256 values:

```text
211d7bea564792bb215f5448572d4db54a1442e8b8b8083186c90debff159f78  otarchguard-1.0.1-py3-none-any.whl
05511291a4fec1ac14459a6736d84e32eb65359df63dff8fa5af186789eb08a9  otarchguard-1.0.1.tar.gz
53d767e9c8f794aeed0bd11650a7e4f1ccd5a913eca1bd9c1745ee39a982ce18  SHA256SUMS.txt
```

## 18. Recommended next gate and owner summary

After owner acceptance, the planned next increment remains Gate V11-2:
deterministic SVG layout and offline report improvements. It has not started.
V11-1-F01 is included in this gate following the owner's explicit request.

The local candidate rejects surrogate text deterministically at the shared input
boundary, preserves valid bytes and analysis outputs, and protects previous
reports on failure. Out-of-range escapes now use the existing scanner diagnostic
contract. Both regular installed candidates passed all 983 tests and all required
local static, dependency and offline checks; all 176 baseline fingerprints match.
Review the final verification tables and unavailable remote release
check alongside the completed local verification before accepting the
gate. No commit, push, release publication or history rewrite was performed.
