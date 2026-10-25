# V13-21 — Hosted candidate acceptance and authorization boundary

Date: 2026-10-25. Status: **FAIL for the published candidate; local correction
prepared, remaining jobs in progress.** The owner specifically authorized the
normal push of `38c1ec96d95e274e3b9ebdd30ad42a3e8cb84a9e` to
`refs/heads/codex/v13-01-capture-foundation`. That exact push succeeded and created
the remote branch. The owner authorization covers that commit only. PR, merge,
tags, releases, uploads, settings and any subsequent push remain unauthorized.

## Actual hosted results

| Platform | Python | Final 1.3.0 result | Tested commit / run |
| --- | --- | --- | --- |
| Windows | 3.12 | IN PROGRESS | job121324170857 |
| Windows | 3.14 | IN PROGRESS | job121324170817 |
| Ubuntu | 3.12 | FAIL: strict mypy | job121324170800 |
| Ubuntu | 3.14 | FAIL: strict mypy | job121324170894 |
| macOS | 3.12 | FAIL: strict mypy | job121324170818 |
| macOS | 3.14 | FAIL: strict mypy | job121324170716 |

All cells belong to [Python verification run40244859860](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40244859860),
attempt1, event push, started2026-10-25T23:27:38Z, exact head38c1ec96d95e274e3b9ebdd30ad42a3e8cb84a9e.
No historical v1.2 or earlier candidate run is substituted. Local Windows results
establish no hosted multiplatform PASS. Raw authorization/push/branch/run/job/log
and downloaded-artifact receipts are retained under `output/v13-hosted/`.

## Confirmed hosted defect and local correction

Four POSIX cells completed source verification, 1.3.0 wheel/sdist builds, archive
audits, installed module/console verification, Ruff lint and formatting. Strict
mypy then reported four undefined Windows ctypes attributes in
`benchmarks/capture.py`: WinDLL (twice), WinError and get_last_error. Its runtime
`os.name == "nt"` condition excluded those calls on POSIX, but mypy did not use
that condition to exclude the Windows-only API declarations. Product analyzer
modules were not implicated. Later tests/walkthroughs/benchmarks in these cells
were skipped, not PASS.

The local correction uses `sys.platform == "win32"`, recognized by mypy and
equivalent for the supported native platforms. No ignores, weakened checks,
forced Windows typing in hosted POSIX jobs, runtime dependency or production
module change is introduced. Full strict mypy passes separately with win32,
linux and darwin targets (155 files each); Ruff/format pass and the real local
Windows RSS helper returns a positive integer. Receipts:
`output/v13-platform-typing-fix/receipt.json` and mypy target logs. These static
cross-target checks do not claim POSIX runtime success. The fixed commit still
requires owner authorization and a new six-cell run.

Four failed-cell integrity ZIPs were retained and their API SHA-256 digests
matched downloaded bytes. They contain source-checkout, environment, archive
audit, actual packages and golden/interoperability manifests. Full-suite XML,
sdist installation, compatibility/consumer/walkthrough/benchmark results are
absent because mypy stopped execution. Their absence is explicitly recorded.

## Prepared workflow

`.github/workflows/ci.yml` defines all six cells, read-only contents permission,
exact-source verification before building, backend-derived wheel/sdist filenames,
archive/member/source/RECORD/metadata audit, regular wheel installation, complete
network-denied suite, Ruff/format/strict mypy/dependency checks and native console
and module hashing. It independently reinstalls the sdist and runs the complete
suite again, followed by fictional installed-console walkthroughs and fixed
resource workloads. New capture interoperability, ARP and evidence-consumer tests
are collected by both complete suites; they must remain in the public manifest.

The prepared historical compatibility step uses the pinned local Git baseline
`f52c792b683cb499dc7de765b65b5cc897a96854`, a fresh regular baseline environment
sharing only approved installed dependencies, no-index installation, exact
installed-baseline hashes, and strict version-aware artifact comparison.
Historical fixtures, native schema/contract bytes and the narrowly permitted
current-release assertion are checked before execution. The existing comparison
tool is reused; arbitrary version-string substitution is forbidden.

Retained candidate evidence includes source-checkout, environment/module hashes,
actual archives, archive audit, both suite XML receipts, native compatibility
captures/comparison, walkthroughs and exact tested-commit/run identifiers. The
named frozen-consumer step reads the supported and limited golden bundles without
capture bytes; both JSON receipts, the golden manifest, interoperability corpus
manifest and independent decoder receipt are retained explicitly. The
retention step runs even on failure, preserving available diagnostics. Benchmark
evidence is retained separately. Setup may access approved dependencies; product
execution and the baseline comparison are network denied. The required repository
variable `EXPECTED_ROOT_SHA` must already match the independently verified history
root; this task does not change repository settings.

## Required owner decision

Before requesting authorization, the integration owner must report the exact
final branch, HEAD, parent commit(s), clean/dirty status, complete changed-file
list and diff summary, final local receipts, proposed remote destination and
literal non-forced Git command. Inspect remote destination refs read-only and
reconcile any existing candidate branch without force-pushing. The final exact
source identity is in V13-20 and the release manifest, not the starting revision
of this review.

The proposed destination is the existing repository
`https://github.com/z4y-d3n/OT-ArchGuard.git`, candidate branch
`codex/v13-01-capture-foundation`, subject to the read-only remote-ref check.
Expected workflow: **Python verification**, six matrix cells. Authorization may
publish only the exact reviewed candidate branch commit. Protected/historical
refs, `main`, stable tags and published packages must remain immutable.

After authorization and the normal push, inspect every job against the exact
tested commit and download/verify the retained source, package, suite,
walkthrough, compatibility and resource evidence. Missing checks stay NOT RUN or
BLOCKED. Fix actual failures locally and repeat affected validation. A PR requires
separate specific authorization. Any eventual merge commit requires its own
source-identity and required-CI verification before publication consideration.
