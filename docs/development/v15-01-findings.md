# V15-01 — Consolidated findings

Baseline source and scope are recorded in the [plan](v15-01-plan.md). No
demonstrated P0 was found in this bounded review. Absence of a finding is not
proof of exhaustive defect absence. Severity describes impact in the documented
workflow, not industrial operational risk.

| ID / origin | Area / severity | Reproduction and evidence | Root cause / disposition | Coverage or deferral |
|---|---|---|---|---|
| F01 / B | Tutorial UX / P1 | Three `python -m tools.{evidence_history,drift,historical_explorer}_walkthrough --output ABSENT/new` calls exit 1 with `FileNotFoundError`; existing destinations produce `FileExistsError` traceback. Six baseline cases retained under `output/v15-01/ux/`. | CLI invokes exclusive scenario directory creation without explaining prerequisites. Add shared `tools/walkthrough_cli.py` preflight to three mains: actionable exit 2, no creation or overwrite. Scenario APIs/publication checks unchanged. | `tests/test_v15_foundation.py`: missing parent, file parent, existing file/directory, unchanged sentinel/inventory, relative fresh destination dispatch. Existing end-to-end scenarios cover real success and deterministic identities. |
| F02 / A+B | CI / P1 | `.github/workflows/ci.yml` push patterns match v13/v14 but not requested v15 branch; PR to main remains covered. | Add `codex/v15-*` only. Existing jobs, permissions, dependencies and six-platform/interpreter combinations retained. | Parse actual YAML; match requested branch; assert PR targets and exact matrix. Hosted execution still pending. |
| F03 / B | Onboarding / P1 | Three historical guides show `output/...` without parent-creation instruction; Historical Explorer also omits tool/source prerequisites. | Document PowerShell/POSIX parent creation, source or extracted sdist root, regular installed interpreter, wheel/tool distinction and fresh destinations. | Destination regressions plus actual extracted-sdist first run and historical walkthrough verification; manual command readability remains owner review. |
| F04 / B | Installation docs / P2 | Current structured-inventory section in `docs/import-studio.md` recommends 1.3.0 wheel. | Link current regular installation guidance; use 1.4.0 in that current command only. Historical records retained. | Documentation/link review and package identity checks. |
| F05 / A | Compatibility / constraint | `tools/verify_legacy_candidate.py::_candidate_module_hashes`, `_check_candidate_source` pin all 97 modules; `tests/test_v146_version_gate.py` rejects other changes. | Preserve pin policy and version. This is an engineering dependency, not an analytical defect. | Existing adversarial version/identity tests and exact verifier; explicit transition proposed for V15-02. |
| F06 / A | Report diagnostics / P2 | Fault injection into both `reporting.write_report` replacement and temporary-file unlink makes cleanup `PermissionError` mask controlled `REPORT_IO_ERROR`; old output preserved. Receipt `output/v15-01/architecture/reliability-receipt.json`. | Unguarded cleanup in `src/otarchguard/reporting.py` finally block. Deferred because F05 prevents runtime changes; no ordinary-use loss or critical failure established. | Future double-fault regression should preserve original diagnostic and old bytes. No contract weakened to implement it here. |
| F07 / A | Maintainability / P2 | Private imports cross `evidence/validation.py`, `drift/engine.py`, `drift/explorer.py`; similar option parsing wrappers in capture/evidence CLI. | Verified coupling; no demonstrated behavioral defect justifies refactoring now. | Retain existing integration/adversarial coverage; defer ownership/abstraction review. |

All reproduced F01–F06 observations have high confidence; F07's maintenance
impact has medium confidence. F01–F04 have low implementation risk and bounded
verification cost; F06 has a small possible fix but an unauthorized source-policy
surface. No protocol expansion, cache, concurrency, dependency or renderer change
was selected. Agent C's bottleneck candidates remain measurement hypotheses in
the [performance report](v15-01-performance.md).

## Dependency and risk map

- Native: loading → parsing/domain → validation/normalization → immutable
  `api.ValidatedArchitecture` → graph/policy/reachability → intents/exposure/trace/
  comparison → reports/Explorer. `api.py` rejects fatal input before snapshots;
  `diagnostics.check_limit` owns resource rejection.
- Imports: bounded adapters → explicit profile → draft/review/reconciliation →
  native validation before emission (`ingestion/workflow.py`). Documentary arrows
  do not automatically become network permissions.
- Capture: bounded parser → observations + separate protocol enrichment → reviewed
  associations → native comparison → static Explorer. Metadata is not permission.
- History: immutable collections → validated attachments → exact-source revisions
  → explicit reviews → coverage-aware drift → Historical Explorer.
  `evidence/revisions.py::implementation_identities` uses installed resources;
  replay is source-bound, not checkout-path-bound.
- Publication intentionally differs: report replacement is atomic; capture/import
  bundles stage; immutable historical objects publish exclusively.
  `evidence/history.py` reacquires source bytes at publication. Unifying these
  writers mechanically would risk different output-preservation contracts.

Existing integration evidence includes reporting, independent capture publication,
history validation context, history performance audit, resource envelope, security
and version-gate tests. Static review cannot establish browser accessibility.
