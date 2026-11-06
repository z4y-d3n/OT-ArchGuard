# V15-05 — Installation and distribution acceptance

Local candidate preparation; package campaign results will close this record.
No push, PR, merge, tag or Release is authorized or performed in this gate.

## Source boundary

| Identity | Value |
|---|---|
| Starting clean main / integrated V15-04 | `b62f816a88d8cf61e2798c368e8b277621b5d5bc` |
| Starting tree | `e2c4d35f57c4a2e8c0b6cf09f3aa93301ae9b8e4` |
| Branch | `codex/v15-05-installation-distribution-docs` |
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

Required local campaign: links/anchors, command syntax/review, inventory equality,
case/duplicate checks, whitespace, committed source, unchanged production/policies,
archive audit, two fresh regular installs, pre-import V15-04 authorization,
environment verification, dependency consistency, CLI help/version, fictional
validation and first Explorer. Results pending the candidate campaign.

The unchanged CI retains full wheel/sdist suites and historical/capture
walkthroughs. They are not repeated locally for Markdown/inventory-only changes.
Historical recovery is covered by the retained prior-gate source boundary, not
claimed as freshly executed here. No stable download reinstallation, physical
air-gap, POSIX runtime or new human browser review is inferred.

## Owner gates and open items

Review final diff and receipts, confirm zero runtime/policy drift, inspect the
first report and accept documentation. Publish the branch only after review;
all six hosted jobs must pass for the exact submitted SHA before merge.
V15-06 remains responsible for stable-version authorization, integrated-source
release acceptance, final assembly and publication preparation. See the
[Spanish handoff](v15-05-handoff-es.md). Archive hashes provide integrity, not
authenticated authorship or release authorization.
