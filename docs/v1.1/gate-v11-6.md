# Gate V11-6 — 1.1.0 release-candidate finalization

## 1. Executive summary

**GATE V11-6 — LOCALLY COMPLETE; RELEASE-CANDIDATE OWNER REVIEW REQUIRED**

Local verification on 2026-10-23 prepares a genuine unpublished 1.1.0 candidate.
All locally executable authorized criteria pass; no unresolved local Critical or
High blocker was found in the exercised scope. Owner review, current hosted CI,
merge, tag and publication remain separate pending decisions. Finite evidence
does not establish absolute correctness, deployed-network safety or certification.

## 2. Objective and recommendation

Represent the accepted V11-5 implementation as 1.1.0 without changing analytical
meaning. FE-18 protects version/contract invariants; FE-19 audits distributions;
FE-20 verifies compatibility/installations; FE-21 prepares public documentation;
FE-22 defines owner publication/recovery; FE-23 binds evidence for review.
Recommendation: **accept the local candidate for independent owner review; do not
publish until the owner approves and current six-way CI/post-merge checks pass**.

## 3. Authorization boundary

The authoritative OT-ArchGuard-CLEAN checkout alone was used. No private backup,
original historical implementation or proprietary reference material was used.
The only production edit is the central runtime version literal. No feature,
signature, schema, resource limit, dependency bound or analytical refactor changed.
No v1.2 implementation began.

## 4. Local-only Git compliance

Git operations were local inspection and the explicitly authorized branch switch.
The normal branch switch hit the read-only .git sandbox; the approved escalation
created the requested local branch. No fetch/pull/push/clone, GitHub connector,
API/browser query, remote inspection, commit, staging, merge, rebase, reset, tag
creation, upload or publication occurred. Historical dossier remote commands
were read as history and never executed. No owner work was overwritten.

## 5. Starting checkout and development branch

Starting branch: clean `main`. Accepted main and current development HEAD:
`bfa94942c185ad8ba677ea0ca567dc1672c836dd`. Branch created from that verified main:
`codex/gate-v11-6`. All 20 public changes remain uncommitted/unstaged. HEAD alone
does not identify candidate bytes: ignored manifests hash every public file and
runtime module. Evidence: `output/gate-v11-6/baseline.json`, `final-integrity.json`.

## 6. V11-5 integration

Local main is PR #5's merge. Both development/hardening commit
`ea375fedef031cb1d7e019dfa8b61d71e38dc550` and Unix help correction
`f026743363c1ad73d5473e4c25d7bcb342490556` are ancestors of main; the latter is a
merge parent. Existing V11-5 tests, inventory, capture tool and dossier are present.
`tests/test_release_hardening.py` remains byte-identical, including the copied
child environment `NO_COLOR=1`, `TERM=dumb`. Earlier dossiers V11-1 through V11-5
were reviewed and preserved byte for byte.

## 7. Prior hosted evidence classification

V11-5's dossier and ignored unix-help-fix results record owner-supplied historical
Ubuntu/macOS 3.12 help failures and locally successful correction, with hosted
reruns pending. No locally supplied successful rerun receipt for accepted main
was found. Current V11-5 hosted acceptance: **NOT_VERIFIED**. A local merge proves
ancestry, not hosted job success. No stale failure is asserted to remain active.

## 8. Independent root

Sole root: `8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`, unchanged. Local fsck
exits 0 with existing dangling-tree notices and no corruption. Workflow
EXPECTED_ROOT_SHA references and the entire root-check step are unchanged; the
remote variable was neither inspected nor altered.

## 9. Historical stable identity

Annotated v1.0.1 tag object: `39c855ad6204953495fdca4a7058fd53a3ba8f8c`, peeling
to the independent root. It remains the only local tag. Original local stable
wheel/sdist/checksum file hashes match the V11-1 recorded values; no historical
asset was rebuilt, moved or replaced. This is local evidence, not a new remote
asset verification.

## 10. Versioning decision

Use the explicitly authorized final identity **1.1.0** for the unpublished
development-branch candidate. No approved versioning convention conflicts with
it. No rc/dev suffix was invented. Published stable remains v1.0.1; version
metadata in a local archive does not create a release or owner approval.

## 11. Authoritative and derived version references

`pyproject.toml` distribution version and `src/otarchguard/__init__.py` runtime
literal change exactly 1.0.1 → 1.1.0. CLI/report/trace import that same runtime
constant; no new version constant is added. Installed metadata, METADATA,
PKG-INFO, console output and filenames are checked independently.

## 12. Complete executable/configuration diff

| File | Exact purpose |
| --- | --- |
| src/otarchguard/__init__.py | one runtime version literal |
| pyproject.toml | one distribution version literal; all bounds unchanged |
| .github/workflows/ci.yml | exactly two candidate archive filename versions |
| tests/test_release_audit.py | exact current dist-info license path |
| tests/test_release_candidate.py | 13 additional identity/allowlist/exit regressions |
| tools/compare_versioned_contract.py | bounded offline version-aware comparison |
| MANIFEST.in, tools/public-files.txt | five deliberately added public files |

All 24 other production modules have identical accepted-main SHA-256 values.
All existing tests are unchanged except the one exact package-path assertion.
The new tool does not alter application output or baseline evidence.

## 13. Frozen contract identities and version-occurrence classification

Schema = 1; legacy report_version = 1; trace_version = 1. New exact assertions
check runtime, installed metadata, native version, all five stdout/report engine
versions and the separate contract versions. The existing 1.0.1 dist-info test
was a current candidate-package assertion and now exactly names 1.1.0. Historical
dossiers/release notes, stable changelog, image captions and captured fixtures
remain historical. The new comparator tests intentionally use old-version
fixtures. No permissive substring, arbitrary archive pattern or skip was added.

## 14. Preserved historical baseline

Before changing authoritative versions, regular installed V11-5 code on both
interpreters matched accepted source. Those prior installations had historical
staging distribution metadata 1.0.1.dev5+gate.v11.5 and runtime 1.0.1, recorded
explicitly in baseline-installed.json. One fresh authoritative 3.12 pre-version
capture reproduced **197/197** historical files, and a separate native capture
reproduced **123/123 artifacts plus its manifest** exactly against V11-5 evidence.
These directories remain immutable under `baseline197/` and `baseline123/`.
`preserved-baseline-hashes.json` binds their raw bytes.

## 15. Precise compatibility allowlist

JSON: only the complete envelope's root `/engine_version` may change exactly
1.0.1 → 1.1.0. Compare complete parsed structures and require all serialization
bytes to equal the single exact token replacement. Never drop nested version
fields, schema/report/trace versions, keys, whitespace or arbitrary strings.
HTML: only that root field inside the uniquely delimited complete JSON appendix,
plus the exact trace header engine text. All other HTML bytes must match.
SVG/canonical JSON and other artifacts require exact bytes. Capture manifests
verify artifact hashes, all input/model hashes and exits; interpreter/platform
and the central version-module hash are provenance checked separately. Mutation
tests reject changed truth/schema/types/nested versions/formatting, SVG/text and
non-appendix HTML substitutions.

## 16. Canonical model identity results

Both candidate interpreters pass all 197 historical artifacts and 123 expanded
artifacts, allowing only section 15's version metadata changes. Every canonical
file and SVG is unchanged; model hashes are identical. The minimal fixture keeps
`66f0739f9cea30a3c2a90f226eea5360596027c6a0c9c6c777ca170ac5799be8`.
Full per-artifact classifications and canonical SHA-256 maps are in
`compatibility197-312.json`, `compatibility197-314.json`,
`compatibility123-312.json`, `compatibility123-314.json` and
`compatibility-summary.json`. The expanded comparison also checks its provenance
manifest, so its tool count is 124 files = 123 artifacts + 1 manifest.

## 17. Exact queries, witnesses and diagnostics

Complete captures preserve intervals, deterministic selected witnesses, replay
data, structural absence versus policy failure, missing permits versus explicit
deny, intent/exposure/comparison outcomes, baseline/proposal identities and
diagnostics. Independent graph/policy/per-port and witness oracles remain in the
full suite, including mixed truth and extreme TCP/UDP ports. Finite evidence is
not a proof for all possible declarations.

## 18. Policy and resources

Unordered default deny/deny precedence, original endpoint selectors, edge-rule
associations, exact destination ports, finite overlap/scoped duplicate evidence,
actual counters, ceilings and prospective reservations are unchanged. All
non-version production bytes and complete resource/analytical artifacts agree.
Existing boundary/oracle tests pass; resource rejection never becomes unreachable
success or partial successful evidence. No new ceiling or resource unit exists.

## 19. Installed native CLI

All five commands pass native console checks on each interpreter. Forty-five
expanded native cases cover help/parser errors, JSON/HTML output, reachable/mixed/
missing-permit/deny/structurally absent traces and failure sentinels. The 197-file
corpus and 27-command walkthroughs cover real baseline/proposal comparisons and
intent exits. New tests explicitly preserve exit 1 for a failed required intent;
full existing tests retain exit 2 failures and report preservation. Destination
assertions, policy evidence and exact TCP/UDP semantics remain exercised.

## 20. Python API compatibility

No analytical module/type/signature changes. Existing file/bytes/prevalidated
adapter-equivalence tests, independent oracles and complete programmatic report
captures pass. The sole runtime-root export change is __version__. The historical
public inventory remains a V11-5 snapshot with a V11-6 addendum link; it does not
claim newly importable helpers as supported APIs.

## 21. Offline HTML/SVG and determinism

All SVG bytes are identical; HTML differs only at the exact engine locations.
Escaping, inactive hostile labels, CSP, local fragments, complete evidence,
atomic writes and prior-report preservation remain tested. Both interpreters and
PYTHONHASHSEED 0/12345 produce identical mixed-policy trace JSON/HTML; receipts:
`determinism/evidence.json`. No runtime network, telemetry, script dependency,
timestamp or input-machine path was introduced. The Python network-denial hook
guards acceptance children; this is not an OS air-gap claim.

## 22. Adversarial regression and preparation reuse

The full suites retain malformed UTF-8/Unicode/YAML, scalar/reference checks,
bounded raw graph/metamorphic cases, prospective work limits, atomic partial-write/
replace faults and sanitized diagnostics. V11-4 call-count/input-change tests
still require one validation for check/exposure and two for compare reports.
No new persistent cache or duplicate validation was introduced; failure policy
is unchanged.

## 23. Cross-platform scope

Direct local execution is Windows AMD64 only, on CPython 3.12.14 and 3.14.5.
Unicode/spaces paths, native launchers, UTF-8 subprocesses, deterministic LF
reports and close-before-replace behavior pass. Fonts/ACLs/path limits, fresh OS,
Python 3.13, and broader browser/print/accessibility behavior remain unverified.
Plain help uses the accepted child environment; no ANSI-styled cross-OS byte
equivalence is claimed. Linux/macOS require owner-hosted execution.

## 24–25. Actual installed regression outcomes

| Interpreter | Passed/collected | Failed | Errors | Skipped | Xfailed | Time | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CPython 3.12.14 | 1349 | 0 | 0 | 0 | 0 | 310.98 s driver wall | PASS |
| CPython 3.14.5 | 1349 | 0 | 0 | 0 | 0 | 329.79 s driver wall | PASS |

No xpassed or new conditional skips. Final pytest-final stdout, stderr, JUnit XML and
command/exit/timing JSON are under `output/gate-v11-6/312/` and `314/`.
Final pytest summaries: 1349 passed in 310.26s (0:05:10);
1349 passed in 328.94s (0:05:28).
The first complete suites passed 1,347 tests in 314.19/333.87 s. A second-pass
review tightened capture input/exit comparison to distinguish integer, Boolean
and floating-point values; two corruption regressions were added and the final
complete suites were rerun on the stabilized executable tooling. Both sets of
receipts remain preserved. Unchanged examples/benchmarks/captures were not repeated
for that tooling-only correction; the tightened comparator was rerun against
the retained actual artifacts. No documentation-only edit triggered a full suite.
Suites ran concurrently; these are local observations, not performance comparisons.

## 26. Static checks and dependencies

Both interpreters pass Ruff lint, format (100 Python/example files), strict mypy
(67 configured source files), pip check and installed environment provenance.
Verification dependencies are unchanged: setuptools 84.2.1, pytest 9.1.1,
Ruff 0.17.1, mypy 1.20.2, types-PyYAML 6.0.12.20260906; runtime closure is
recorded separately. Pip versions are 25.0.1 / 26.1.1. No registry, online version
or vulnerability query, dependency download or replacement occurred.

## 27–28. Sdist and wheel integrity

Genuine backend-generated names:
`otarchguard-1.1.0-py3-none-any.whl` and `otarchguard-1.1.0.tar.gz`.
Build backend: setuptools.build_meta, Python 3.12.14, setuptools 84.2.1.
Every explicit public file is copied byte-for-byte into ignored staging; no
staged version substitution or archive renaming occurs. The existing audit checks
every member, source bytes, METADATA/PKG-INFO, Requires-Python, runtime/dev
requirements, entry point, licenses, generated source inventory and wheel RECORD.
Wheel contains exactly 25 production modules plus seven approved metadata/license
members. Sdist contains exactly 122 reviewed files plus eight generated records.

## 29. Source-to-installed equivalence

Both interpreters freshly installed the genuine sdist offline with the existing
approved backend, then installed the regular wheel. Imports resolve to each
environment's site-packages, never checkout src; direct_url is non-editable.
Every installed production module hash equals reviewed source. Console paths
come from sysconfig, not PATH. Final package rebuilds preserve the already tested
executable bytes; final wheel/sdist installation/provenance and focused version
checks are repeated after documentation finalization.

## 30. Extracted-sdist rebuild

The audited sdist is extracted in independent ignored staging with data-filtered
tar extraction. A wheel is built there without network/build isolation and all
32 member contents/hashes, including metadata/RECORD, are compared with the
direct wheel. All agree. SOURCE_DATE_EPOCH uses the accepted HEAD commit time for
the controlled builds. Archive-level equality, if observed, is recorded in
`build-final.json`; only demonstrated member equivalence is an acceptance claim.
No universal archive SHA reproducibility is asserted.

## 31. Archive checksum inventory

Final local archives are under `output/gate-v11-6/candidate/`. Their exact sizes,
SHA-256 values, member inventories and source hashes are in
`archive-audit-final.json`, `release-candidate-manifest.json` and
`candidate/SHA256SUMS.txt`. These ignored records are the authoritative checksum
inventory. Embedding an sdist's own final hash inside its packaged dossier would
create a circular identity, so this public dossier deliberately references the
separate record. Initial build receipts/archives are retained independently.
New owner post-merge builds require new checksums tied to their exact bytes.

## 32. Explicit manifest and exclusions

Public count: **122**, deliberately increased from historical 117 by release notes,
publication runbook, this dossier, the version-sensitive tests and comparator.
MANIFEST.in and tools/public-files.txt match all tracked/new public files exactly.
Every sdist public byte matches reviewed source. Excluded: output/evidence,
archives, environments, build/cache/egg-info directories, credentials, debug/logs,
private/backup material and machine records. No runtime data file or unexpected
module appears. New verification tooling/tests/docs are deliberately public.

## 33. Security, privacy and licenses

Apache-2.0 LICENSE and THIRD_PARTY_NOTICES.md are byte-preserved in source and
packages. Both installed runtime closures have 14 expected distributions at the
documented versions with upstream license/notice files, including Typer's bundled
Click notice. `licenses-312.json` / `licenses-314.json` retain metadata/file hashes.
No dependency is vendored in the application wheel. This is a local metadata/
notice audit, not legal sign-off or an online vulnerability assessment. No private
file, credential, new network behavior or unsupported conformity claim is added.

## 34–38. Public documentation and upgrade review

README separates candidate 1.1.0 from published stable v1.0.1; historical preview
captions remain historical. CHANGELOG adds an unpublished 1.1.0 entry while
preserving the stable entry exactly. Release notes describe actual V11-1–V11-6
changes without inventing a date, URL, signature or prior trace support.
Installation uses parallel environments, explicit native consoles, reviewed
wheel/sdist, no-index options, schema-1 validation/examples/offline reports and
stable-environment rollback. Tested install/native commands are captured; the
fresh empty environment is created with local TEMP/TMP, but the conditional
fresh-wheelhouse install needs owner-provided dependency wheels and is explicitly
not claimed executed. Current dedicated environments reuse approved dependencies.
Historical verification remains labeled; limitations clarify the fixed candidate
Unicode issue. Public Markdown file targets resolve. No v1.2 feature is present;
easier guided/template/spreadsheet/YAML/visual authoring is a future requirement.

## 39. Fixed benchmark and unchanged thresholds

| Python | Routine exposure maximum seconds | Peak traced Python bytes | Result |
| --- | ---: | ---: | --- |
| 312 | 1.176155 | 7,392,801 | PASS |
| 314 | 1.413623 | 7,599,713 | PASS |

Existing five timings, warm-up, separate traced allocation, routine 30-second /
512-MiB target, work units and controlled pathological rejections remain intact.
Fresh records: `312/benchmark-results.json`, `314/benchmark-results.json`.
This is a local fixed-target check, not RSS, universal capacity or a new speedup
study. Verification drivers may overlap; no before/after timing comparison is
claimed. Historical V11-4 profiling was not repeated or substituted as new data.

## 40. Hosted six-way acceptance

CI retains Windows/Ubuntu/macOS × Python 3.12/3.14, fail-fast false, read-only
permissions, all triggers, independent root check, regular installed verification,
Ruff/format/mypy/pip check, offline full suite/examples, package audit, fixed
benchmark and distinct per-matrix evidence. Only the two explicit archive
filenames change. Every new hosted result is **PENDING_OWNER_PUSH_AND_PR**.
No local test or earlier owner report is represented as six-way candidate PASS.

## 41–44. Owner PR, merge, tagging, publication and recovery

The [owner-only runbook](../release-publication-1.1.0.md) specifies local review,
explicit staging/commit/push/PR, current six-way CI, owner merge/synchronization,
clean exact accepted-commit rebuild/audit, separate annotated-tag approval,
separate destination/asset publication approval and downloaded-asset verification.
GitHub Release and package-index publication remain distinct decisions. Recovery
separates pre-publication abort, post-merge/pre-tag correction, created-but-unshared
tag, shared tag, already published asset and stable-user parallel rollback.
Do not silently move public tags or replace published bytes; prefer a documented
advisory/corrective version. These are planned owner operations, never executed
by this gate. Original stable assets remain available locally and unchanged.

## 45. Findings, failed attempts and limitations

No confirmed analytical defect or unresolved local Critical/High blocker was
found. One copied historical capture script was decoded with Windows' default
encoding, corrupting a generated Unicode input; the mismatch was rejected before
version promotion. The failed capture remains in attempt197-encoding-error; the
authoritative capture uses the original verified UTF-8 input and exactly matches
history. Python 3.14's initial sdist install hit a sandbox-denied external pip
cache; workspace-local PIP_CACHE_DIR resolved it offline. Empty-venv ensurepip
likewise passed with workspace TEMP/TMP. A license-probe spelling mismatch
(typing_extensions versus normalized typing-extensions) was corrected. Initial
Ruff line-length findings were fixed before full verification. The new comparison
tool's original Python equality could accept a corrupted Boolean/float exit equal
to integer zero; typed JSON equality and two mutation tests now reject both.
This verification-tool correction changed no product byte or captured analytical
result; it received fresh focused, static and complete regression checks. None required a
production workaround or weakened assertion. Previous hosted status, fresh OS,
complete offline wheelhouse, broader browser/print and OS behavior are explicit
unverified boundaries, not hidden passed Booleans.

## 46. Remaining blockers and owner approvals

Unresolved **local** Critical/High blockers: zero. No blocker is downgraded to
force acceptance. New hosted CI is an outstanding publication requirement, not a
confirmed current failure. If it fails, record identifier/severity/reproduction/
impact/contract/remedy/disposition/authorization and stop release advancement.
Owner review/commit/push/PR, hosted results, merge, final source/package audit,
tagging, publication and post-publication acceptance all remain pending.

## 47. Reproduction and retained evidence

Use the corresponding 314 executable for the second interpreter. Baselines must
be captured from the preserved accepted 1.0.1 source **before** version promotion;
do not regenerate/overwrite them from 1.1.0 or interpret a later source checkout
as historical evidence. Ignored gate-local drivers and raw artifacts must be
retained for reproducing this particular local audit. A fresh source package
includes public tests/comparator, not ignored historical evidence.

```powershell
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
$env:NO_COLOR = '1'
$env:TERM = 'dumb'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PIP_NO_INDEX = '1'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:PIP_CACHE_DIR = (Join-Path (Get-Location) 'output/gate-v11-6/pip-cache')
$env:TEMP = (Join-Path (Get-Location) 'output/gate-v11-6/tmp')
$env:TMP = $env:TEMP
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/gate-v11-6/312/review-installed.json
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
.venv-verify312/Scripts/python.exe -m pytest -q --tb=short --basetemp=.pytest_tmp/gate6-owner312
.venv-verify312/Scripts/python.exe examples/run_examples.py
.venv-verify312/Scripts/python.exe -m benchmarks.run --output output/gate-v11-6/312/review-benchmark.json
.venv-verify312/Scripts/python.exe tools/compare_versioned_contract.py output/gate-v11-6/baseline197 output/gate-v11-6/candidate197-312 --output output/gate-v11-6/review197.json
.venv-verify312/Scripts/python.exe tools/compare_versioned_contract.py output/gate-v11-6/baseline123 output/gate-v11-6/candidate123-312 --output output/gate-v11-6/review123.json
.venv-verify312/Scripts/python.exe tools/audit_release.py output/gate-v11-6/candidate/otarchguard-1.1.0-py3-none-any.whl output/gate-v11-6/candidate/otarchguard-1.1.0.tar.gz --source-root . --output output/gate-v11-6/review-archives.json
git diff --check
git fsck --full
git rev-list --max-parents=0 HEAD
git rev-parse v1.0.1 'v1.0.1^{}'
```

Exact executed subprocess arguments, exits, timing and stdout/stderr are retained
under each interpreter. Build driver copies only manifest files, runs the approved
backend, audits, extracts/rebuilds and compares; its final source/module hashes
are retained in build-final.json and the ignored candidate manifest.

## 48. Changed public files recommended for review

Source/configuration: src/otarchguard/__init__.py, pyproject.toml,
.github/workflows/ci.yml. Tests: tests/test_release_audit.py,
tests/test_release_candidate.py. Verification/manifests: MANIFEST.in,
tools/public-files.txt, tools/compare_versioned_contract.py.
Documentation: README.md, CHANGELOG.md, docs/installation.md, docs/limitations.md,
docs/release-checklist.md, docs/release-notes-1.1.0.md,
docs/release-publication-1.1.0.md, docs/testing-strategy.md, docs/trace.md,
docs/v1.1/public-contract-inventory.md, docs/verification.md and this dossier.
The independent second pass directly checks accepted Git bytes, exact manifests,
historical immutability, version-only module diff and artifacts; it does not
merely copy the test summary. See final-integrity.json and archive-audit-final.json.

## 49. Machine-readable handoff and evidence labels

Ignored `handoff.json` and `release-candidate-manifest.json` bind candidate/source/
archive hashes, dirty-tree state, baseline/root/tag, dependencies, installed
provenance, per-interpreter tests, exact public inventory, local audit results,
hosted pending status and required owner actions. Unknowns use explicit statuses,
never passed Booleans. Historical evidence remains distinct from direct local
measurements, owner-reported failures, planned operations and unverified claims.

## 50. Final candidate readiness matrix

All evidence paths below are relative to output/gate-v11-6 unless a public path
is given. PASS is limited to the directly exercised local scope.

| Area / required condition | Status | Evidence | Limitation | Remaining action |
| --- | --- | --- | --- | --- |
| Accepted V11-5 source/integration/help fix | PASS | baseline.json; final-integrity.json | local ancestry | owner review |
| Historical Git root unchanged | PASS | final-integrity.json | local Git | preserve |
| Published v1.0.1 tag unchanged | PASS | final-integrity.json | local tag/assets | preserve |
| Application version 1.1.0 candidate | PASS | */installed.json; exact-version tests | unpublished | owner approve |
| Distribution version 1.1.0 candidate | PASS | archive-audit-final.json | local archives | post-merge rebuild |
| Schema 1 | PASS | exact-version tests; canonical evidence | finite scope | preserve |
| Legacy report contract 1 | PASS | exact-version tests | finite scope | preserve |
| Trace contract 1 | PASS | exact-version tests | finite scope | preserve |
| Analytical semantics unchanged | PASS | source hashes; compatibility-summary.json; oracles | finite evidence | owner inspect |
| Canonical model hashes unchanged | PASS | compatibility-summary.json | exercised models | preserve |
| Policy semantics unchanged | PASS | unchanged policy modules; oracles | declared model | preserve |
| Resource limits/work unchanged | PASS | unchanged contract/modules; exact corpus | not capacity promise | preserve |
| CLI preserved except engine metadata | PASS | 197/123 captures; native tests | controlled terminal | hosted CI |
| Python API no unauthorized break | PASS | module bytes; adapter/oracle tests | established API scope | review |
| Windows/Python 3.12 | PASS | 312/pytest-final.xml and receipts | this environment | hosted Windows too |
| Windows/Python 3.14 | PASS | 314/pytest-final.xml and receipts | this environment | hosted Windows too |
| Ubuntu/macOS after owner PR | PENDING_OWNER_PUSH_AND_PR | retained CI matrix | no hosted query | owner execute |
| Offline reports safe/deterministic | PASS | report tests/captures; determinism/evidence.json | browser/print unverified | optional manual review |
| Source distribution audited | PASS | archive-audit-final.json | local candidate | audit final release source |
| Wheel audited | PASS | archive-audit-final.json | local candidate | audit final release wheel |
| Installed modules source-equivalent | PASS | final installed receipts | existing approved deps | post-publication verify |
| Public manifest exact | PASS | final-integrity.json; archive audit | 122 files | approve inventory |
| License/notices preserved | PASS | archive audit; licenses-*.json | no legal sign-off | retain upstream notices |
| Release notes prepared | PASS | docs/release-notes-1.1.0.md | unpublished | owner review |
| Upgrade instructions prepared/tested | PASS | installation guide; install/smoke receipts | wheelhouse prerequisite disclosed | owner supply if fresh offline install |
| Rollback/publication procedure | PASS | docs/release-publication-1.1.0.md | procedure only | owner decisions |
| Local Critical blockers zero | PASS | findings; direct audits | finite assessment | review |
| Local High blockers zero | PASS | findings; direct audits | hosted CI still required | review |
| Owner approval | PENDING | handoff.json | no approval inferred | owner review |
| Commit | NOT_PERFORMED | unchanged HEAD/index | explicitly prohibited | owner decide |
| Remote push | NOT_PERFORMED | local-only operation record | explicitly prohibited | owner decide |
| Merge | NOT_PERFORMED | unchanged main/HEAD | explicitly prohibited | owner decide |
| v1.1.0 tag | NOT_CREATED | local tag inventory | explicitly prohibited | separate approval |
| Publication/deployment | NOT_PERFORMED | handoff.json | unpublished candidate | separate approval |

**GATE V11-6 — LOCALLY COMPLETE; RELEASE-CANDIDATE OWNER REVIEW REQUIRED**
