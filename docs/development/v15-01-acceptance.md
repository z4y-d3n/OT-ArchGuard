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

Execution is in progress. No pending check in this draft is a PASS claim.
Final results, exact candidate source identity and final audit will replace this
paragraph before delivery. Raw logs/environments/reports remain ignored under
`output/v15-01/`; concise portable receipts are suitable for source control.

## Owner gates

No push, PR, merge, tag or publication is authorized. All six hosted jobs must
run on the eventual submitted head. Local Windows verification cannot establish
Ubuntu/macOS or Python 3.14 results. Human acceptance and assistive-technology
behavior remain distinct from automated structural checks. Gate completion does
not establish v1.5 release readiness.
