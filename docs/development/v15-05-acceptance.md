# V15-05 — Installation and distribution acceptance

**READY_FOR_OWNER_REVIEW**. Required local documentation, installed-source and
package checks pass; owner acceptance and the candidate's six hosted jobs remain
pending. This is installation/distribution assurance, not stable-release readiness.
No push, PR, merge, tag or Release is authorized or performed in this gate.

## Source boundary

| Identity | Value |
|---|---|
| Starting clean main / integrated V15-04 | `b62f816a88d8cf61e2798c368e8b277621b5d5bc` |
| Starting tree | `e2c4d35f57c4a2e8c0b6cf09f3aa93301ae9b8e4` |
| Branch | `codex/v15-05-installation-distribution-docs` |
| Functional campaign source | `f9d5c15dd287643f67dc3c292e2eb74b75fbfa15` |
| Functional campaign tree | `5728a964643a05df160ecb29020bcfe01d45625c` |
| Final HEAD/tree, public-source digest, archive hashes | External `output/v15-05/final/freeze.json` |
| Distribution / native engine / YAML schema | `1.5.0.dev3` / `1.3.0` / `1` |
| Production scope | All 97 Python modules preserved byte-for-byte |
| Historical renderer | `1.5.0.dev1-historical-explorer.1` |
| Renderer digest | `442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b` |

Fetch confirmed `origin/main` equals the starting SHA, with no local changes.
Baseline [CI run 41918807010](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41918807010)
completed all six supported jobs successfully. Candidate CI remains pending.

Only Markdown and the two explicit inventories change: `README.md`,
`CHANGELOG.md`, `docs/installation.md`, `docs/dependencies.md`,
`docs/testing-strategy.md`, `docs/release-checklist.md`, these three V15-05
documents, `MANIFEST.in` and `tools/public-files.txt`. No production, metadata,
test, CI, prior verifier or historical fixture changes. Stable assets remain fixed.

## Findings and corrections

| Finding | Severity | Correction |
|---|---|---|
| Installation's current development section still said dev1 and referred to stable instructions "below" although they were above | P2 | Identify dev3 and separate exact-source build/audit/regular install/first report from stable assets |
| Testing strategy labelled V15-02 as current | P2 | Add current V15-05 tiered verification and preserve the old checkpoint explicitly |
| V15-01 changelog wording could read as current distribution 1.4.0 | P2 | Label its original checkpoint; add concise V15-05 unreleased entry |
| No concrete dev3 first-install/recovery sequence or final stable assembly boundary | P2 | Add platform paths, interpreter/source checks, extracted-sdist example, recovery table, target-specific offline prerequisites and V15-06 duties |

No demonstrated P0/P1 runtime or packaging defect was found. Stable Quick Start,
owner screenshot/provenance and published release links are preserved. Historical
V15-04 optimization proposals remain historical; this gate's installation scope
supersedes them without editing their evidence.

## Verification and receipts

The [matrix](v15-05-installation-matrix.md) distinguishes executed installation
paths from historical/static review. Commands/exits, source policy, dependency
closure, package inventory and module hashes belong under `output/v15-05/`.
Initial candidate packages and later documentation-closure packages must each be
audited against their own committed public bytes; never reuse an old sdist hash.
Final archive hashes and Git identities are external to this self-packaged record.

| Check actually executed | Result / receipt under `output/v15-05/` |
|---|---|
| Nine changed Markdown documents: local links and relevant fragments | PASS, 167 targets; `docs-check.json` |
| Command syntax and manual command/path review | PASS, 16 PowerShell blocks and three bash blocks (`bash -n` only); `powershell-syntax.json`, `posix-syntax.json` |
| Explicit inventory / duplicate/case check / whitespace | PASS, 554 public files, exact MANIFEST lines, no duplicates/collisions; `docs-check.json` and final receipt |
| Starting-source preservation | PASS, 304 protected source/test/tool/CI/metadata files, including all 97 production modules, byte-identical to merged V15-04; `docs-check.json` |
| Exact committed public bytes / archive audits | PASS; candidate and final `source.json`, `audit.json`; 104 wheel members / 562 sdist members |
| Fresh wheel and sdist regular installation | PASS, Windows x64 / Python 3.14.5, local wheelhouse, pip 26.2.2 and setuptools 84.2.1; `candidate/commands.json` |
| Pre-import approved V15-04 policy | PASS, all 97 installed physical modules in both environments; `{candidate,final}/{wheel,sdist}-authorized.json` |
| Interpreter, site-packages, metadata, CLI/native version and dependency consistency | PASS in both; `{candidate,final}/{wheel,sdist}-environment.json`, pip-check/version logs |
| CLI help, fictional native validation and Explorer | PASS in both; `candidate/{wheel,sdist}-{help,validate,explore}.stdout` |
| First-report local file/link/fragment audit | PASS, each 54 files / 52 HTML / 132 anchors / 781 links / zero broken links; Explorer receipts and `report-links.json` |
| Existing focused archive/source regression tests | 42 PASS, zero failures/errors/skips; `candidate/focused-tests.xml` |

The focused tests are `tests/test_release_integrity.py`,
`tests/test_release_audit.py` and `tests/test_final_release.py`. All successful
acceptance commands exit 0. Runtime analysis carries the existing Python offline
hook; installs resolve only local wheels with `--no-index --find-links` and the
sdist uses its preinstalled backend with `--no-build-isolation`. The wheelhouse
inventory and actual installed closure are recorded, not asserted universal.
Package audits check metadata/dependencies, entry point, Python requirement,
licenses/notices, RECORD and every public source/runtime byte.

Operational attempts are retained: `candidate-build-attempt/` records a local
runner error (setuptools mutates `sys.argv`; saving the destination first fixed
the misplaced sdist). The first sdist install in `candidate/commands.json` failed
because the sandbox denied pip's default cache. Moving `PIP_CACHE_DIR` under
`output/v15-05/` allowed the same audited archive to install successfully; only
the affected steps were retried. Neither issue required package/runtime changes.

Documentation closure changes only these acceptance records. Final archives are
rebuilt/audited against that final commit and regularly reinstalled in the same
two previously fresh environments. Repeated authorization, metadata/console and
dependency checks bind the closure archives to the already-smoked runtime; no
second functional or full-suite campaign is implied. Final hashes are in
`output/v15-05/final/freeze.json` and `final/receipt.json`, not the earlier package
hashes. The final receipt also records the clean Git status and HEAD/tree.

The unchanged CI retains full wheel/sdist suites and historical/capture
walkthroughs. They are not repeated locally for Markdown/inventory-only changes.
Historical recovery is covered by the retained prior-gate source boundary, not
claimed as freshly executed here. No stable download reinstallation, physical
air-gap, POSIX runtime or new human browser review is inferred.

Read-only GitHub release metadata revalidation confirms latest stable v1.4.0 and
the four documented asset digests (`stable-assets.json`); no assets were changed
or freshly reinstalled. No local full capture/historical walkthrough, isolated
sdist build, online-index install or new Python 3.12 installation is claimed.

## Owner gates and open items

Review final diff and receipts, confirm zero runtime/policy drift, inspect the
first report and accept documentation. Publish the branch only after review;
all six hosted jobs must pass for the exact submitted SHA before merge.
V15-06 remains responsible for stable-version authorization, integrated-source
release acceptance, final assembly and publication preparation. See the
[Spanish handoff](v15-05-handoff-es.md). Archive hashes provide integrity, not
authenticated authorship or release authorization.
