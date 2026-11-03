# V15-02 — Local acceptance record

**READY_FOR_OWNER_REVIEW** for this local development gate. Hosted execution and
human visual acceptance remain separate owner gates; this is not a stable release.

Baseline is merged `b3adcc9de21dfff6ad58946028a241844ff88294`; see
[plan](v15-02-plan.md) and [compatibility contract](v15-02-compatibility-contract.md).
Raw receipts remain local and ignored under `output/v15-02/`; they are not
included in public distributions.

| Requirement | Evidence |
|---|---|
| Exact 97-module transition, protected historical inputs | `tools.verify_v15_transition`, `test_v15_transition.py` |
| Original V14 contract | Unchanged verifier on isolated predecessor |
| Independent exact native outputs | Predecessor/candidate capture comparison |
| Producer boundaries and recovery | Real old installed workspace, new rejection, old replay |
| Seven-statement UX and renderer identity | `test_v15_renderer_ux.py`, fresh walkthrough |
| F06 primary/secondary diagnostics | Pre-fix receipts, `test_v15_report_reliability.py` |
| Regular packages and source identity | Archive audit and environment receipts |
| Regression/static quality | Full JUnit, Ruff, formatting, strict mypy, pip check |
| Performance | Paired `benchmarks.v15_transition`, same driver/input scales |
| Independent skeptical review | Agent E audit and dispositions |

## Exact source and executed checks

Full-suite source: `762a9db78c01d3259617a6cfb040d45120f2bd41`, public source
SHA-256 `795032d56f39f2c8cdcf91b66a9e526df77001dec27313aa18519dbd13dd80c9`.
Subsequent verification hardening: `b007eb1841a12d92eecef1813a05ec8c3c7cdc3d`.
All 97 runtime module bytes are identical between these sources and final closure.
The later checker/test/CI changes received focused tests, the complete isolated
transition campaign and independent adversarial review. No full-suite rerun is
attributed to that later tooling or the final documentation-only commit.
`final-source.json` records the exact delivered HEAD/tree/public hashes; final
archive and installed receipts reside under `output/v15-02/final-packages/`.

Windows 11 / AMD64, CPython 3.12.14, regular fresh wheel installation:

| Campaign | PASS | FAIL | ERROR | SKIP | Receipt |
|---|---:|---:|---:|---:|---|
| Complete suite, 980.25 s | 4439 | 0 | 0 | 1 | `verified-full-suite.xml` |
| Same Windows junction case, bounded external rerun | 1 | 0 | 0 | 0 | `junction-final.xml` |
| Final new regressions, regular wheel | 55 | 0 | 0 | 0 | `final-focused.xml` |
| Regular sdist, affected regressions plus V15 foundation | 71 | 0 | 0 | 0 | `sdist-focused.xml` |
| Actual extracted sdist, report/foundation checks | 26 | 0 | 0 | 0 | `extracted-focused.xml` |
| Frozen identity fixture and transition correction | 75 | 0 | 0 | 0 | `audit-fix.xml` |

Counts overlap. The full run collected 4,440 cases. Three bootstrap regressions
were added later and passed in focused/sdist runs. Including the same junction
case's successful rerun, all 4,443 current unique cases have successful execution
evidence across these campaigns; there was no single 4,443-case full run.
The junction was skipped because sandbox policy denied creation; the rerun used
two paths under a fresh, checked workspace directory. No new unique case is counted.

Ruff, 421-file formatting, strict mypy (271 source files) and dependency consistency
pass. The sdist full suite was not repeated locally: exact equality of all 97
installed modules, affected regressions, extracted-source checks and real workflows
complement the full wheel run. Hosted CI retains both full installed suites.

## Independent compatibility and package evidence

The authoritative command is `python -I tools/verify_v15_transition.py --output
output/NEW`. `transition-final/transition.json` reports PASS with seven outer
commands exiting 0. The unchanged V14 verifier independently checks 124 artifacts,
110 analytical artifacts, 13 HTML appendices and 54 historical test files. The
candidate comparison checks 124 artifacts: every non-manifest artifact retains
exact predecessor bytes; the manifest is independently source-bound provenance.

An actual old installed producer creates a workspace/bundle. New source rejects
analytical loading with `EVIDENCE_REVISION`; portable verification remains separate;
the original installation successfully replays it. The entire historical file
inventory remains unchanged. New own-source walkthroughs pass exact replay,
deterministic repetition and recorded/current approval separation.

Wheel/sdist inventory, metadata, RECORD, licenses, entry points and dependency
audits pass; regular imported source matches all 97 reviewed modules. Real extracted
sdist examples, project, Architecture Explorer, capture and Historical Explorer
walkthroughs pass, as do both frozen evidence consumers. Final archives are local
development artifacts, never replacements for published v1.4.0 assets.

Full pytest used the configured Python network audit hook. Isolated verifier and
capture parents ignore `PYTHONPATH`; approved code is offline and pip uses no
index, but universal hook coverage or a physical air gap is not claimed.

## Adversarial review and preserved negative results

Agent E demonstrated and resolved four findings: mutable reference parser trust,
historical fixture copying current development identity, checkout standard-library
shadowing, and runtime import preceding installed-byte validation. It independently
confirmed rejection after correction. A real poisoned `.pyc` control also executed
under ordinary import and did not execute under the hardened verifier. Immutable
Git parsing, isolated entry, trusted external Git, immutable-byte comparator compile,
pre-import module checks and fresh cache prefixes close these demonstrated paths.
No unresolved blocking independent finding remains; raw proofs/dispositions are
under `audit/`, including `review.json`.

Initial focused run: 40 PASS / 3 FAIL, corrected test harness/oracle setup; audit
fixture reproduction: 3 PASS / 2 FAIL, resolved without weakening assertions.
An early full run was interrupted at 17% after discovering that fixture dependency;
it is not a successful full run. The first integrated legacy campaign failed on
nested dependency visibility and was corrected with local approved dependency
copies. Sandbox TEMP/uninstall/cache failures and an invalid preliminary paired
benchmark remain recorded. The clean final environments, no-cache installation
and final sequential timing campaign supersede them; none is hidden as PASS.

## Targeted performance

One warmup and three untraced trials per operation, fictional scale 512, same
driver/capture hashes and all resolved dependency versions except distribution:

| Median | Predecessor | Candidate | Change |
|---|---:|---:|---:|
| Explorer generation | 18.2093 s | 18.2000 s | -0.05% |
| Source replay | 5.0574 s | 5.0196 s | -0.75% |
| Atomic 1 MiB report | 3.098 ms | 2.338 ms | -0.759 ms |
| CLI startup | 0.7308 s | 0.7209 s | -1.35% |

No material regression shown. Scheduler/cache noise prevents an optimization
claim, especially for sub-millisecond report differences. Memory was not compared.
Physical snapshot and capture identities match; producer/analysis/review identities
differ and report summaries match. Raw data: `performance-comparison.json`, paired
`performance-*-final/`, and `performance-dependencies.json`.

## Owner gates

Hosted Windows/Ubuntu/macOS × Python 3.12/3.14 remains pending for the submitted
head. Open `output/v15-02/owner-review/revoked/index.html` and perform the complete
browser checklist in the [Spanish handoff](v15-02-handoff-es.md). No browser,
keyboard, assistive-technology or print acceptance is fabricated. No push, remote
PR, new merge, tag or release was performed.
