# V13-28 — Final UX regression and package verification

Date: 2026-10-26. Status at source freeze: **targeted local checks passed; exact
installed-candidate results are recorded in the authoritative receipts below**.
This source document deliberately does not embed its own future commit or sdist
hash. Missing, failing or mismatched receipts cannot be treated as PASS.

## Executed preliminary evidence

| Check | Actual preliminary result | Evidence |
| --- | --- | --- |
| Independent UX integrity suite | 24 passed | V13-26 and its retained targeted receipts |
| Exact display/timestamp cases | 36 passed | V13-25 and `tests/test_capture_display.py` |
| Overview/protocol/coverage views | 9 passed | Current focused view execution and `tests/test_capture_views.py` |
| New UX assertions against exact old renderer | 11 failed, 13 passed, as expected | `output/v13-ux/integrity-baseline/old-renderer-final-tests-pytest.txt` |
| Frozen and original analytical evidence preservation | Exact canonical JSON; no input mutation | V13-26, frozen consumer and original-report invariance checks |
| Preserved original report reproduction | All 14 files byte-identical using installed baseline renderer | V13-27 and `provenance/original-render-reproduction.json` |

These executions support the change and demonstrate that the UX tests expose
the earlier renderer's shortcomings. Intentional old-renderer failures are not
failures of historical analytical acceptance. Focused counts overlap subsequent
complete suites and must not be added to their totals. The two fresh regular
verification environments have been prepared; preparation is not installed-product
acceptance. The complete source preflight is a separate preliminary execution.

A same-driver preliminary comparison against the verified regular installed
`5c4c18d` renderer preserves all nine input hashes and outcomes and all eight
completed observation identities. The richer HTML costs more: cardinality-1k
output grew from 7.24 to 14.83 MB and traced elapsed time from 3.84 to 16.30 seconds;
traced peak allocations grew about 26%, while process peak RSS grew about 4%.
These are single executions with tracing and uncontrolled concurrent host load,
not capacity or throughput guarantees. `benchmark-comparison.json` and
`reference-benchmark-identity.json` retain the measurements and installed baseline
identity. The final installed benchmark remains required and supersedes the
source preflight. Resource ceilings are unchanged; richer output can reach them
sooner and is rejected rather than silently truncated.

The complete integration preflight exposed a page-namespace regression: new
`evidence-index-N.html` pages were counted as existing `evidence-N.html` detail
pages by the unchanged capture CLI regression. The renderer now uses
`evidenceindex-N.html` for subsequent index pages, preserving the original detail
namespace and its test. The provisional `5ec9edc` candidate is not selected for
acceptance; its receipts and packages are retained separately when replacing the
working acceptance outputs. Fresh exact-source packages and complete suites are
required after this correction.

The corrected source then passed all 37 combined capture CLI and UX-integrity
cases, with Ruff lint/format and strict mypy passing. This focused execution is
additional diagnostic evidence, not a substitute for the final complete suites.

## Exact-source acceptance receipts

All paths below are under `output/v13-ux/`. Final completion is conditional on
the actual contents and successful outcomes, not this list's presence in source.

| Receipt | Required interpretation |
| --- | --- |
| `source-checkout.json` | Exact final tested commit and public-source inventory/hashes; checkout bytes match its committed blobs |
| `package-identities.json` | Actual backend-produced wheel/sdist filenames, sizes and SHA-256 values, bound to the selected source |
| `quality-receipt.json` | Actual Ruff lint/format, strict mypy, dependency consistency and relevant archive/source audit commands and exits |
| `wheel-suite.xml` | Full suite against the freshly, regularly installed selected wheel; actual tests/failures/errors/skips |
| `sdist-suite.xml` | Separate full suite against the freshly, regularly installed selected sdist; actual tests/failures/errors/skips |
| `legacy/comparison.json` | Immutable native v1.2 comparison, actual baseline identity and narrowly permitted engine-version differences |
| `benchmarks/benchmark.json` | Actual synthetic rendering/resource measurements and expected rejection behavior; no inferred throughput or capacity claim |
| `release-manifest.json` | Final source, package, installed-module, tests, walkthrough and limitations reconciliation |
| `owner-review.md` | Exact reviewed candidate, selected packages, report location, pending acceptance and proposed owner-controlled next action |

The integration owner must inspect every required outcome and its binding to the
same source before declaring local completion. An earlier source preflight, old
environment or historical archive cannot fill a missing final check. Installed
module hashes must match the reviewed production bytes, console/runtime and
distribution metadata must report 1.3.0, and editable installs are excluded.
Archive audits retain the exact public inventory, source/wheel/sdist equality,
metadata, entry point, licenses and wheel RECORD checks.

## Preservation and verification scope

The complete installed suites include native v1.2 regressions, independent capture
interoperability, ARP semantics, reconciliation, frozen JSON/consumer checks,
new presentation/navigation/time assertions, hostile text, deterministic output,
resource rejection, no-clobber publication and network denial. The selected
source must keep parser/observation/reconciliation/evaluator semantics and
canonical artifacts unchanged for identical inputs and decisions. HTML/CSS
differences are expected; unexplained analytical differences are not accepted.

Walkthroughs must execute the selected installed console outside the checkout
and generate fresh output directories. The final fictional browser report is
`output/v13-ux/wheel-tutorial/comparison/index.html`; its actual package/source
identity and generated hashes belong in the final manifest and owner packet.
Original reports and prior package selections remain preserved.

Historical six-platform success for `5c4c18d` is not a new execution. New hosted
validation is NOT RUN pending separate authorization (V13-29). Second human
browser acceptance is PENDING (V13-30). Local receipt success cannot satisfy
either requirement or authorize publication.
