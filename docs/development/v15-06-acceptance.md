# V15-06 — local acceptance and source freeze

**READY_FOR_OWNER_REVIEW**. Required local safety, compatibility and package
checks pass; candidate hosted CI, integration and publication remain pending.
This dossier distinguishes local gate acceptance, exact integrated-source
acceptance and explicit owner publication authorization.

| Identity | Value |
|---|---|
| Starting clean main / merged V15-05 | `7c5d6cb5c0efd6ee5946943bf8b83e12e98a9057` |
| Starting tree | `e2c40a52a3f5d9370d2053474d9f2aab1d1463b4` |
| Branch | `codex/v15-06-final-release-readiness` |
| Distribution transition | `1.5.0.dev3` → unpublished stable candidate `1.5.0` |
| Native engine / schema | `1.3.0` / `1` unchanged |
| Runtime change | `__init__.py` distribution literal only; 96 modules byte-identical |
| Final committed SHA/tree, public inventory digest, four hashes | `output/v15-06/final/freeze.json` |

The final identity and final asset hashes are external receipts to avoid placing
a commit/archive's own hash inside its source. The source-bound manifest records
the exact commit/tree and all public bytes. No archive byte reproducibility claim
is made. Source/payload equivalence is checked independently.

## Executed checks and receipts

| Check | Outcome / receipt |
|---|---|
| PR #30 merged and final candidate six jobs | PASS; `preflight/github.json`, run 42138952966 |
| Initial focused safety/current dev3 | 925 passed; `safety/baseline.xml` |
| New stable policy, propagation and manifest regressions | 49 passed initial campaign; `safety/stable.xml`; superseded by expanded P1/full runs |
| Expanded protocols/imports/validation/Explorer and stable regressions | 734 passed; `safety/p1.xml` |
| Final source/assembly/safety supplement | 56 passed; `safety/final-frozen.xml`; includes five new unique source/cache/entry controls |
| Ruff lint/format, strict mypy, dependencies | PASS; strict mypy 283 source files; final logs and `final/checks.json` |
| Complete applicable regularly installed wheel suite | 4515 passed, 1 skipped; `final/full-suite.xml`; historical exact-version exclusions only |
| Archived dev3 / dev2 / dev1 policy tests | 34 / 24 / 30 passed in matching runtimes, plus unchanged recursive native-v1.4/v1.2 chain; `compatibility/verified/` |
| Independent native byte comparison and producer isolation/recovery | PASS: 123 analytical artifacts EXACT_BYTES plus verified manifest; dev3 recovery, stable EVIDENCE_REVISION, unchanged historical files and no approval transfer |
| Four-asset assembly, reopen audit, source/inventory, wheel/sdist installs | `final/checks.json`, `final/freeze.json`, `packages/` |
| Installed fictional native/Architecture/Capture/Historical/Drift walkthroughs | `final/checks.json` and `packages/walkthroughs/` |
| Documentation links, inventories and final source policy | `final/checks.json` |

All paths in the table are beneath ignored `output/v15-06/`. The final freeze
records unique collected node IDs and counts; focused/repeated runs overlap and
are not added to the complete-suite total. Final unique collection is 4521
identities: 4520 passed and one skipped across the complete suite and final
supplement. Five new controls are absent from the earlier 4516-node collection;
the other supplement cases overlap it. The full campaign ran from functional
commit `1f23f36c12e97a228f225477c2c5000abe8f7db8`, tree
`441398ca802497e1fe1a7db3803d49633bba230a`. Subsequent changes refine new
three-zone/propagation tests and harden only the new assembler; all affected
V15-06 suites run again on the final frozen Python bytes. Their hash inventory
is `safety/final-supplement-source.json`. The full suite is not falsely reported
as a second execution on the final documentation commit.

The sole skip is `test_historical_explorer_bundle.py:560`: this Windows account
cannot create junctions. Junction traversal behavior is not locally certified;
normal bundle/path rejection and other source negative checks still run. This
skip remains explicit for owner/hosted review. Failed setup/exploratory attempts
are retained separately and are not acceptance evidence.

The safety matrix documents actual assertions and the two added high-value
relations. No unresolved production P0/P1 defect was demonstrated. Declared
negative reachability remains qualified by model scope, unverified completeness
and explicit limitations. Unsupported/invalid/resource-rejected evidence never
becomes a complete successful analysis. See [safety](v15-06-safety-assurance.md)
and [compatibility](v15-06-compatibility.md).

## Packaging boundary

Rehearsal folder `output/v15-06/rehearsal/assets/` contains exactly:

1. `otarchguard-1.5.0-py3-none-any.whl`
2. `otarchguard-1.5.0.tar.gz`
3. `release-manifest.json`
4. `SHA256SUMS.txt`

The checksum file covers exactly the other three files. Independent
`final/freeze.json` records SHA-256 of all four. Audits compare every wheel/sdist
member with the committed public inventory, metadata, entry point, notices,
runtime modules, RECORD and generated source inventory. Extra assets, unsafe/
duplicate members, changed data, forged manifest acceptance claims, dirty source
and reused output are rejected. The original v1.4 assembler is unchanged.

Both regular installations passed source authorization, environment/CLI/help
and dependency checks. Audits cover 104 wheel members, 572 sdist members and
564 public source files. The independent sdist focused suite passed 33 cases;
the full sdist suite is left to hosted CI. All project, document, quality,
capture, evidence, history, drift and Historical Explorer walkthroughs passed,
including extracted-sdist native/Architecture Explorer, fictional examples,
supported/limited capture consumers and original/v1.4 protocol corpora.
The final committed assembly is rebuilt/reopened and reinstalled after dossier
freeze; its four final hashes live in `final/freeze.json`. Earlier
`rehearsal/functional-assets/` and `functional-hashes.json` describe their own
functional commit, not final documentation source or eventual integration.

Two assembly issues were resolved: the backend's argv mutation redirected the
first sdist (audit refused publication), and mutable helper caches could execute
before authorization. The stable assembler captures its destination, requires
isolated source execution, loads its reviewed policy from source and compiles
reused primitives from authenticated Git bytes. Independent negative controls
verify both corrections. No production semantics changed.

## Pending or unexecuted

Candidate hosted CI is pending publication of this branch; earlier successful
jobs do not validate it. Post-merge integrated source and its six successful jobs,
fresh final release assembly, owner authorization, annotated tag, GitHub Release,
upload and downloaded-asset verification remain pending. No remote write occurs.

Local platform is Windows / Python 3.14.5. Local Ubuntu/macOS and Python 3.12
execution are not claimed; the hosted matrix must establish them. No live OT,
physical isolation/enforcement, full protocol reconstruction, external decoder
expansion, browser/accessibility certification or universal correctness is
claimed. Existing owner screenshot provenance and published v1.4 assets remain
unchanged. The [Spanish handoff](v15-06-handoff-es.md) gives conditional owner steps.
