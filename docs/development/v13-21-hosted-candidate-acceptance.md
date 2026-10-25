# V13-21 — Hosted candidate acceptance and authorization boundary

Date: 2026-10-25. Status: **BLOCKED — specific owner remote-write authorization
pending**. No remote push, workflow dispatch, PR, merge, tag, release, upload or
repository-setting modification is authorized by the master prompt. Local work
continues independently; this status does not negate completed local checks.

## Actual hosted results

| Platform | Python | Final 1.3.0 result | Tested commit / run |
| --- | --- | --- | --- |
| Windows | 3.12 | NOT RUN | None |
| Windows | 3.14 | NOT RUN | None |
| Ubuntu | 3.12 | NOT RUN | None |
| Ubuntu | 3.14 | NOT RUN | None |
| macOS | 3.12 | NOT RUN | None |
| macOS | 3.14 | NOT RUN | None |

No historical v1.2 or earlier candidate run is substituted for these results.
There are no completed-run URLs or retained hosted artifacts for this final
candidate. Local Windows results establish no hosted multiplatform PASS.

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
