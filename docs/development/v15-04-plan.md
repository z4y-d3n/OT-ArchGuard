# V15-04 — Profile-guided performance consolidation

Mission: measure, profile, prove a bottleneck, select at most two bounded changes,
compare independent immutable references, measure again, and audit. This is a
development milestone, never a stable release or industrial capacity certificate.

## Baseline and authorization

- Merged V15-03: `18cb7e84ef16871daf857af48e3cd003ec8200ba`.
- Tree: `0b512bce31da2b0d9b10160b1a8cdc13ec23fab4`.
- Clean `main` matched freshly fetched `origin/main`; local branch:
  `codex/v15-04-performance-scalability`.
- V15-03 post-merge [run 41841310683](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41841310683):
  all six Windows/Ubuntu/macOS × Python 3.12/3.14 jobs succeeded.
- Regular `.venv-v153-final` installation passed the unchanged V15-03 source-only
  verifier before investigation (97 modules, distribution `1.5.0.dev2`, native
  `1.3.0`, YAML schema `1`). Receipts: `output/v15-04/baseline/`.
- No remote writes, PR, merge, tag, release, destructive reset, or historical
  reference changes are authorized. Only ordinary local candidate commits.

## Scope and sequence

Primary: Architecture Explorer generation using existing small/medium/larger
fictional workloads. Secondary: historical validation/replay/rendering attribution.
Controls: supported/limited/dense capture presentation and bounded resource cases.
No new parser, network functionality, persistent cache, resource ceiling increase,
evidence omission, approval transfer, or skipped validation.

Initial read-only specialists A (architecture), B (history), C (capture), D
(measurement integrity), E (compatibility/package/CI); final independent skeptical
auditor F after the candidate stabilizes. Four active slots require sequential
dispatch of some specialists. Main integrator owns every tracked source change.
CPU/allocation/latency campaigns and full suites run separately, without duplicate
expensive campaigns. Agent raw work is isolated under ignored `output/v15-04/`.

Phases: baseline → read-only discovery/profiles → ranked opportunities → recorded
quantitative policy → explicit source transition → smallest proven optimization →
paired installed-runtime comparison → integrated checks → independent adversarial
audit → exact candidate freeze and Spanish handoff.

## Acceptance policy recorded before implementation

Target at least 15% median uninstrumented generation improvement on the selected
representative bottleneck, with one excluded warmup and at least five trials per
runtime, balanced ordering, identical inputs/interpreter/dependencies, raw timings,
median/MAD/range. Investigate reproducible control slowdowns around 10%, memory
growth, changed inventories, bytes, or incomplete/error behavior. Smaller benefits
require specific justification. cProfile times never substitute for wall latency;
tracemalloc and process high-water RSS are separate observations.

Demand exact architecture output bytes, independent native output references,
intact historical approvals/producer identities, current candidate authorization,
negative source/inventory/installed-byte checks, full applicable pytest plus
separate historical policy suites, Ruff, strict mypy, dependency consistency,
audited wheel/sdist and regular installation. Any shared identity-bound renderer
change requires an explicit renderer transition. Preserve previous gate policies.
Hosted candidate six-job CI remains pending owner publication.

If a stop condition in the execution prompt is demonstrated, stop the affected
implementation, continue safe independent work, preserve failures, and report the
actual incomplete or blocked state. Never manufacture an optimization or a PASS.
