# V15-06 — local acceptance and source freeze

Status is finalized from the receipts below; publication remains pending.
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
| Ruff lint/format, strict mypy, dependencies | Final logs in `final/checks.json` and command logs |
| Complete applicable regularly installed wheel suite | `final/full-suite.xml`; historical exact-version exclusions only |
| Archived dev3 and recursive dev2/dev1/v1.4 policies/tests | `compatibility/verified/transition.json` and recursive XML/command receipts |
| Independent native byte comparison and producer isolation/recovery | Same transition receipt; frozen capture/protocol tests and installed walkthroughs |
| Four-asset assembly, reopen audit, source/inventory, wheel/sdist installs | `final/checks.json`, `final/freeze.json`, `packages/` |
| Installed fictional native/Architecture/Capture/Historical/Drift walkthroughs | `final/checks.json` and `packages/walkthroughs/` |
| Documentation links, inventories and final source policy | `final/checks.json` |

All paths in the table are beneath ignored `output/v15-06/`. The final freeze
records unique collected node IDs and counts; focused/repeated runs overlap and
are not added to the complete-suite total. Failed setup/exploratory attempts are
retained separately and are not acceptance evidence.

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
