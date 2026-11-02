# V15-01 — Local acceptance evidence

Initial source: `c5ada13871043ed52cd43557bc7b222399f7b7eb`, clean `main` tracking
`origin/main`. Branch: `codex/v15-01-product-consolidation-foundation`.
Source was verified with `python -m tools.verify_source_checkout --output
output/v15-01/baseline-source.json`; installed 1.4.0/engine 1.3.0 matched all
runtime source modules with `tools/verify_environment.py` under Python 3.12.14.

## Requirement-to-evidence map

| Requirement | Evidence / command |
|---|---|
| Demonstrated UX failures before correction | Agent B six CLI reproductions under `output/v15-01/ux/` |
| Diagnostic recovery and output preservation | `python -m pytest tests/test_v15_foundation.py` |
| Real successful/deterministic history workflows | Existing history/drift/Explorer walkthrough tests and CLI receipts |
| First-run package imports and examples | Agent D isolated wheel/sdist imports, `--version`, `validate`, `explore` outside checkout |
| Full product assurance | Full pytest with Python network guard; exact counts recorded below after execution |
| Static quality | `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy`, `python -m pip check` |
| Native/presentation integrity | `python -m tools.verify_legacy_candidate --output output/v15-01/native-compatibility` |
| Frozen evidence | `python -m tools.read_capture_evidence tests/fixtures/capture-contract-v2/{supported,limited}` and frozen tests |
| Package inventory/licenses/metadata | `tools/audit_release.py WHEEL SDIST --source-root SOURCE --output RECEIPT` |
| Performance | Agent C warmup + five runs, fixture/source/output identities; no optimization claim |
| Independent challenge | Agent E final review, disposition recorded below |

## Executed results

**READY_FOR_OWNER_REVIEW** for this local gate, subject to the owner gates below.
Tested implementation: clean `b3bc51271c94a67d01aa8328aa215d4dbea45673`;
public-source SHA-256
`84475e753c15cab9a653c3e202ad3d0ebdf914a7e56380b8882e58703f36fc9a`.
The final commit adds documentation/evidence and inventory entries only; its
exact HEAD and final archive audit are recorded in the delivered local
`output/v15-01/final-packages/` receipts and owner-facing delivery message.
No full-suite result is attributed to an unexecuted final-head rerun.

| Check | Actual result |
|---|---|
| Full suite, regular fresh wheel, Windows / CPython 3.12.14 | **4,387 PASS / 0 FAIL / 0 ERROR / 1 SKIP**, 4,388 unique collected cases; 824.39 s reported by pytest |
| Skipped case | Actual Windows junction creation unavailable in sandbox. Inspected and rerun alone outside sandbox with both temporary paths under fresh task output: **1 PASS / 0 FAIL / 0 ERROR / 0 SKIP**. Same case, not another unique test. |
| New focused regressions, fresh wheel | **16 PASS / 0 FAIL / 0 ERROR / 0 SKIP** |
| Same regressions, actual extracted sdist + sdist-installed runtime | **16 PASS / 0 FAIL / 0 ERROR / 0 SKIP**; counts overlap |
| Ruff / formatting / strict mypy / pip check | PASS; 409 Python files checked for formatting, 266 files checked by mypy |
| Exact installed package verification | PASS, regular site-packages imports and all 97 source-module hashes |
| Immutable native/presentation verifier | PASS: 124 artifact comparisons, 110 analytical artifacts, 13 HTML JSON appendices, 54 historical test files checked; 12 internal commands exit 0 |
| Frozen supported + limited evidence consumers | Both exit 0 |
| Wheel / isolated sdist / prepared-backend sdist | Three fresh installs, metadata/license/inventory audit and 97-module equivalence PASS; all three first reports generated outside checkout |
| Real packaged historical tutorials | Lifecycle, drift and Historical Explorer all PASS from extracted sdist |
| Performance | 24 workloads / 120 untraced samples / 22 separate allocation trials; no workload failures; child memory unmeasured |
| Independent Agent E review | NO_BLOCKING_FINDINGS; raw audit `output/v15-01/audit/final.json` |

The [concise receipt](v15-01-evidence.json) contains commands, source identities
and counts. Raw `verification.json`, JUnit, stdout/stderr, package receipts,
benchmark driver and environments remain ignored under `output/v15-01/`.
The full sdist suite was **not** rerun: this tooling-only gate uses one full
regular-wheel suite plus independent installed-sdist identity, focused tests and
all three affected packaged tools. Agent E reviewed that coverage decision.
The complete typed benchmark matrix was not rerun; measured receipts identify
the original preserved driver by hash. Static/smoke checks and independent
operation correspondence cover the typed reproduction driver.

Native-v1.2 HTML is not byte-identical to the already approved v1.4 semantic
presentation (`historical_html_bytes_identical: false` is expected). The existing
approved-presentation comparison passes. No baseline, pin, historical test,
allowlist, report renderer or analytical expectation was weakened.

Packaging receipts retain **40 successful commands and 1 recovered environment
bootstrap error**, rather than pretending all attempts succeeded. Writable
TEMP/TMP and new fresh environments resolved ensurepip's sandbox-temp failure;
a brief ignored recovery-driver initialization error is also disclosed. Neither
changed source or expected tests. Pip resolution used only local wheelhouse
artifacts with indexes disabled; isolated backend children are not claimed to
have a universally enforced Python network hook or a physical air gap.

Agent E independently recalculated benchmark medians/MAD/hashes, read package
and JUnit receipts, verified protected bytes and challenged the harness's command
and pending/error bookkeeping. Those findings were corrected before freeze.
Its Git-checkout prerequisite and browser/hosted limits are explicit. F06 remains
a nonblocking deferred P2 fault-injection finding, not concealed as repaired.

## Final reconciliation

The final documentation/evidence/inventory change requires its own exact-source
and wheel/sdist audit. Final receipts under `output/v15-01/final-packages/`
bind the final HEAD, archive hashes and equality of all 97 runtime modules to the
tested installation. These final archives are local candidates, not published
v1.4.0 assets. No repeat of unchanged analytical tests is inferred from this audit.

## Owner gates

No push, PR, merge, tag or publication is authorized. All six hosted jobs must
run on the eventual submitted head. Local Windows verification cannot establish
Ubuntu/macOS or Python 3.14 results. Human acceptance and assistive-technology
behavior remain distinct from automated structural checks. The browser tool
rejected `file:` navigation; no alternate browser surface/server workaround was
attempted. Keyboard/focus, 200% zoom, narrow viewport, long identifiers/IPv6,
print and assistive-technology checks remain owner acceptance. Gate completion does
not establish v1.5 release readiness.
