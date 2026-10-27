# OT-ArchGuard v1.4 progress and acceptance record

## V14-02 current checkpoint

Local branch: `codex/v14-02-evidence-revisions-and-baselines`, starting from
`bdf51dc54f991ab9edc1a09176b5e55b2ad0df6e`. The starting tree was clean. Remote
fetch confirmed that exact V14-01 head. Draft PR #18 remains open and unmerged,
based on Draft PR #17 at `3201f5d39db4c9bb4fbd565dd62fcc28145800b4`; local ancestry
confirms that relationship. The stable annotated v1.3.0 tag peels to
`10d7de6c416ec6f0ee364c671ebe9292ee69e672`.

At V14-02 preflight, all six V14-01 checks passed on the exact starting head in
[run 40417348042](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40417348042).
This supersedes the then-pending CI state in the preserved historical V14-01
handoff. It does not establish hosted V14-02 acceptance. No remote write, push,
PR creation, merge, tag, workflow dispatch or release is authorized or performed.

Implemented: workspace-v2 and explicit byte-preserving v1 migration; four strict
attachment kinds (enrichment/model/reviewed mapping/native comparison); exact
analytical revisions and producer-semantics manifests; evidence/architecture
baseline proposals; immutable locally asserted approval/rejection/revocation/
supersession; deterministic conflict rejection; full CLI and bounded textual
review; adversarial tests and a repeated fictional acceptance walkthrough.

Contracts and limitations: [historical evidence contracts](v14-history-contract.md).
User workflow: [historical evidence guide](../v14-history.md). Baseline authority
is an unauthenticated human assertion, not authenticity, safety or complete
coverage. Original producer provenance remains unknown where frozen imported
metadata does not attest it. Drift and historical visualization remain future.

Final local acceptance on Windows 11 AMD64 / Python 3.14.5:

| Gate actually executed | Result | Local receipt under `output/` |
|---|---|---|
| Regular installed wheel full suite | 3,573 PASS; no failures/errors/skips; 727.32 s | `v142-wheel-suite.xml` |
| Separate regular installed sdist full suite | 3,573 PASS; no failures/errors/skips; 703.12 s | `v142-sdist-suite.xml` |
| Independent adversarial audit | 38 PASS | `v142-audit.xml` |
| Final new V14-02 tests on installed wheel | 193 PASS; 30.61 s | `v142-new-final.xml` |
| Initial focused migration/attachment/revision/review/CLI regression | 244 PASS | `v142-focused.xml` |
| Ruff lint / format | PASS; 316 Python files formatted | `v142-ruff-*.log` |
| Strict mypy | PASS; 207 files | `v142-mypy.log` |
| Dependencies and regular installed source identity | PASS in wheel, sdist and restored default environment | `v142-*-environment.json` |
| Immutable native compatibility | PASS; 124 captured files | `v142-native-compatibility/comparison.json` |
| Frozen supported/limited consumers | Both PASS | `v142-reader-*.json` |
| Installed fictional historical CLI walkthrough | PASS; two independent runs produce identical IDs | `v142-installed-history-walkthrough/walkthrough.json` |
| Existing evidence/project/Explorer/document/quality/capture walkthroughs and examples | PASS | `v142-*-walkthrough/walkthrough.json`, `v142-examples.log` |
| Exact committed source and wheel/sdist inventories | PASS; no external captures | `v142-source-checkout.json`, `v142-archive-audit.json`; delivery `v142-delivery-source-checkout.json`, `v142-delivery-archive-audit.json` |

The 3,573 unique cases include 193 new V14-02 cases above the 3,380-test V14-01
checkpoint. Repeated/overlapping runs are not added to that inventory. Full
acceptance uses regular installations, not editable installs or `PYTHONPATH=src`;
Python network operations are denied in child processes. Runtime/test/fixture
bytes are frozen at implementation commit `3724062`; subsequent delivery changes
only this record, Spanish handoff and explicit document inventories. Final
source/archive audits are repeated over the documentation-bearing commit.

Staged local commits: `e714771` (workspace/migration), `acb139f` (attachments and
analytical identity), `3724062` (human review, lifecycle CLI, independent fixtures,
walkthrough, benchmark and integration). The final public inventory has 412
files. No frozen native producer, snapshot-v1 implementation, old golden or
third-party packet bytes changed. Full [Spanish owner handoff](v14-02-handoff-es.md)
records architecture, trust limits, commands, Git state and V14-03 inputs.

Finite performance measurement: 16 collections, 32 analyses, 16 model attachments,
nine baselines and nine reviews occupy 83 files / 721,436 B; snapshots 390,952 B,
largest object 35,049 B. Avoiding observation copies in 16 revisions saves
486,560 B. With tracemalloc, migration took 2.982 s, 16 model/revision imports
167.087 s, completing baseline membership 262.707 s, eight-approval successor
chain plus revocation 421.685 s, listing 6.496/6.584 s, triple verification
41.511 s, invalid reference rejection 6.447 s and resource rejection 1.043 s.
Peak Python allocation was 72,110,561 B; process lifetime peak RSS 124,932,096 B.
Without tracing, full verification took 5.979 / 6.196 / 6.025 s (18.200 s total).
Receipts: `v142-history-benchmark-source/benchmark.json` and
`v142-history-benchmark-source/untraced-verification.json`.

These are small synthetic workloads on a shared local interpreter, not a
production-capacity guarantee. Reads reserve up to 64 MiB even for small files;
public operations repeat full inventory/native validation. Smaller bounded read
buffers and per-operation validated dependency reuse are measured optimization
follow-ups before increasing scale; no database/index framework was introduced.

Optional read-only lifecycle import of all eight previously acquired hash-pinned
external Tier-3 captures passed with zero baselines/reviews and unchanged source
bytes. An existing registry discrepancy remains explicit: `cisa-opcua-gap`
declares PCAP although its exact known bytes are PCAPNG. The native parser
detects PCAPNG; the development registry verifier rejects that descriptive
mismatch. Receipt: `v142-optional-external-lifecycle/receipt.json`. This is no new
interoperability/production claim and does not authorize redistribution. Existing
Modbus/DCP/IEC104 external coverage gaps and NULL/SLL support remain separate.

Mandatory local gates 1-10 passed within the documented metadata-only,
single-writer and unauthenticated-review trust model. Original frozen artifacts
do not attest original producer source/configuration; the semantics manifest
honestly binds selected local validation/replay and records that provenance as
unknown. V14-02 hosted six-platform CI is a separate owner-controlled publication
gate and remains unexecuted. Drift/coverage-comparability and historical
visualization remain V14-03/V14-04, respectively.

## V14-01 historical checkpoint

The five remaining bounded decoders are implemented, bringing the inventory to
seven. Enrichment schema 1 emits decoder revision 2 and strictly accepts legacy
revision 1. The package/CLI uses `1.4.0.dev1`; native evidence and the historical
Python version alias retain engine `1.3.0`, preserving frozen analytical sources.
Workspace/snapshot v1 and its duplicate-capture rule remain unchanged.

Local V14-01 acceptance: final installed wheel and separate installed sdist each
pass **3,380 unique tests**, zero failures/errors/skips (711.66 s / 728.38 s).
There are 388 additional cases over V14-00; repeated runs are not added to the
unique inventory. The 565-case focused V14 suite, Ruff lint/format, strict mypy,
dependency checks, frozen consumers, 124-file immutable native comparison and
all final offline walkthroughs pass. Source/archive manifests and installed
module-byte equality are verified; the final documentation-only commit repeats
the source/archive audit. No hosted V14-01 acceptance is claimed.

Eight external parser-reference captures were acquired locally, with actual
hashes, pinned source revisions, rights review and TShark 4.6.7 receipts. Five
supported captures yielded 615 positive records and 2,194 matching safe-field
comparisons across ENIP/S7/OPC UA/DNP3. Three unsupported NULL/SLL captures are
retained as unsupported outcomes. Raw external bytes are excluded from Git and
packages; per-capture redistribution remains unknown. Modbus/DCP/IEC104 external
coverage is still pending. No production-plant provenance is claimed.

The consolidated owner-facing record is [V14-01 handoff in Spanish](v14-01-handoff-es.md),
with exact local gate results, protocol matrix, provenance, architectural ADRs,
performance measurements and prioritized V14-02 acceptance requirements.
The V14-00 sections below preserve historical checkpoint evidence; their older
inventory, package-version and pending-corpus statements describe that checkpoint.

This is the single rolling implementation/acceptance record. Documentation and code
are in English; owner-facing delivery summaries use Spanish. No v1.4 release,
remote branch, pull request or tag is authorized by this local development work.

## Starting identities

- Stable v1.3.0: `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
- Reviewed development base: `1febf7a864c074d2a3d3ac78005ea1bf2853009a`.
- Local branch: `codex/v14-00-evidence-lifecycle-foundation`.
- Package identity remains `1.3.0`; this modified development branch is not publishable.
- Baseline CI: all six jobs passed in run `40323647595`; this is baseline evidence,
  not hosted validation of the new development commit.
- Starting test collection: 2,815 tests. The existing local environment contained
  an outdated installed 1.2.0 package; verification must install the audited current
  wheel before claiming installed-package results.

## V14-00 acceptance — verified local checkpoint

Implemented locally:

- Typed bounded protocol interface and separate Modbus TCP / PROFINET DCP decoders.
- Independent enrichment v1 artifact, strict validator and `capture enrich` command.
- Workspace v1 / snapshot v1 with `evidence init/add/list/show/verify`, exact source
  bindings, bounded local publication and explicit duplicate preservation.
- Original synthetic protocol corpus, TShark 4.6.7 receipt, three-tier provenance
  manifest and bounded offline development verifier. Four external candidates remain
  unapproved; no external packet bytes are redistributed.
- Installed-console fictional walkthrough with two independent snapshots and duplicate
  import. Existing v1.3 capture walkthrough also passes.
- Explicit packaging inventories and additive CI foundation step; existing six-job
  OS/Python matrix is unchanged. No hosted candidate run has been dispatched.

Focused verification: 177 new tests passed in 5.21 s, zero failures/errors/skips,
across protocol (56), lifecycle (55), corpus (38), independent audit (26) and
integration (2) tests. Ruff lint/format, strict mypy (177 Python files) and the two
frozen evidence consumers pass. Native v1.2 compatibility passes for 124 captured
files with the pre-existing exact version/module allowlist. Final installed
wheel/sdist suites and source/archive results are recorded below.

Independent review found and corrected DCP service IDs, unrelated-PROFINET labeling,
Modbus register-response framing, unknown payload fields, impossible packet bounds,
timestamp joins, self-reported budgets, lifecycle aggregate joins and filesystem
reparse/mutation checks. Fourteen frozen capture/reader/golden files have identical
SHA-256 bytes against both the reviewed main and immutable v1.3.0 commit.

No original capture is modified or copied into snapshots. No new dependency,
networking, approval assertion or native evaluator behavior is introduced. New v1
contracts are development interfaces, not a final immutable release freeze:
[enrichment](v14-enrichment-contract.md), [lifecycle](v14-evidence-contract.md).

See [architecture decisions](v14-architecture.md) and
[corpus provenance](v14-protocol-corpus.md). No third-party packet capture is
authorized for redistribution merely by appearing in the source-candidate manifest.

## Executed verification

Implementation commit: `dacda7cd3bf12ed95ad52b8e5cf66533b79c0311`.
The acceptance-record commit after it changes documentation only. Production and
test bytes are identical to the implementation commit exercised here.

Local platform: Windows 11 AMD64 / Python 3.14.5. Dependencies were installed from
the existing offline wheelhouse. No candidate hosted or other-platform execution
is claimed. Both installations are regular installed packages, not editable or
`PYTHONPATH=src` substitutes; installed module SHA-256 inventories match each other
and the committed production source.

| Check | Actual result | Local receipt under `output/` |
|---|---|---|
| Final wheel full pytest, child networking denied | 2,992 passed, 0 failures/errors/skips, 531.27 s | `v14-final-wheel-suite.xml` |
| Final sdist full pytest, separate environment, child networking denied | 2,992 passed, 0 failures/errors/skips, 554.07 s | `v14-sdist-suite.xml` |
| Final wheel focused new tests | 177 passed, 4.57 s | `v14-final-wheel-focused.xml` |
| Ruff lint / formatting | Passed; 277 Python files formatted | Executed `ruff check .` / `ruff format --check .` |
| Strict mypy | Passed, 177 Python source files | Executed `python -m mypy` |
| `pip check` | Passed in both environments | No broken requirements |
| Exact committed public source | Passed | `v14-source-checkout.json` |
| Wheel and sdist member/content audit | Passed | `v14-final-archive-audit.json` |
| Installed source/console identity | Passed in both environments | `v14-final-wheel-environment.json`, `v14-sdist-environment.json` |
| Immutable v1.2 native compatibility | PASS, 124 captured files; historical test/contract guards preserved | `v14-native-compatibility/comparison.json` |
| Fourteen frozen capture/reader/golden files vs main and v1.3.0 | Exact bytes / SHA-256 match | `v14-frozen-integrity.json` |
| Independent frozen evidence consumers | Both passed: supported 10 flows, limited 12 flows | Executed `tools.read_capture_evidence` on both frozen directories |
| Original corpus integrity | Passed; exact 339-byte fixture and pinned TShark receipt | `tools.protocol_corpus --verify synthetic-industrial` |
| Final installed evidence walkthrough | Passed; 2 snapshots, duplicate preserved, metadata verified | `v14-final-evidence-walkthrough/walkthrough.json` |
| Existing installed capture walkthrough | Passed, all six expected classifications present | `v14-capture-walkthrough/walkthrough.json` |

The two full-suite totals overlap; they are **not** 5,984 unique tests. The current
inventory is 2,992 tests: the unchanged 2,815-test baseline plus 177 new cases.
An earlier pre-final-DCP wheel run passed 2,984 cases; it is superseded by the final
2,992-case run and is not used as the current acceptance count.

Full suite commands, with `PYTHONPATH=tools/offline` and
`OTARCHGUARD_OFFLINE_CHECK=1` in the local environment:

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=output/v14-final-wheel-test-tmp --tb=short --junitxml=output/v14-final-wheel-suite.xml
.venv-v14-sdist/Scripts/python.exe -m pytest -q --basetemp=output/v14-sdist-test-tmp --tb=short --junitxml=output/v14-sdist-suite.xml
```

The installed wheels/sdist are local verification artifacts retaining version
`1.3.0`; they must not be published or represented as the immutable stable release.
The initial stale installed package and sandbox temp/cache path failures were
resolved by using workspace-local temporary directories and disabling pip's cache.
No application test failure was waived. Old uninstall backup directories were
preserved under `output/v14-environment-recovery`, not discarded.

Local execution receipts are ignored workspace files, not source-distribution
contents. A final documentation-only handoff rebuild/audit uses
`v14-handoff-source-checkout.json`, `v14-handoff-archive-audit.json` and
`v14-handoff-environment.json`; it does not change tested production or test bytes.

## Finite resource measurement

Receipt: `output/v14-final-performance/measurements.json`. The workload repeats
the original four-frame synthetic corpus 1,000 times after its 24-byte PCAP header:
4,000 records / 315,024 input bytes. Input SHA-256:
`2863b7cef1877e8ebac4b66b530b6665431977f0a5f302bf51139a8af6167902`.

| Operation | Elapsed | Python traced peak bytes | Pretty JSON bytes | Process lifetime peak RSS bytes |
|---|---:|---:|---:|---:|
| Existing observations | 0.6175 s | 162,813 | 15,796 | 42,610,688 |
| Independent enrichment | 1.0827 s | 11,424,124 | 3,429,015 | 60,895,232 |
| Snapshot build/validation | 0.00463 s | Not measured | 17,993 | Not measured |

Enrichment retains 3,000 supported records and explicitly skips 1,000 unrelated
PROFINET frames. The original four-frame fixture itself produces three records,
one `NON_DCP_PROFINET_FRAME_ID` skip and 5,293 pretty JSON bytes. The two original
Modbus headers and DCP Identify header match the independent TShark receipt.

These are single finite measurements, not capacity or throughput guarantees.
RSS includes interpreter startup, imports and earlier operations in the process;
it is not an isolated per-operation delta. Python traced allocations are not RSS.
There is no historical HTML implementation to benchmark yet, and no before/after
speed improvement is claimed for the unchanged v1.3 parser. The local reproducible
measurement script is `output/v14-performance-measure.py`; choose a fresh output
directory when rerunning it.

## Known limits and trust status

- Two of seven protocol decoders are implemented. No general TCP reassembly,
  session validation, command execution inference or application values are added.
- Workspace storage is metadata-only and single-writer. Hashes establish integrity,
  not authenticity; ingestion does not reopen the original capture. Concurrent
  hostile filesystem mutation and power-loss durability are not guaranteed.
- Lifecycle storage deliberately rejects unknown extension fields instead of
  stripping them or silently copying arbitrary payloads. The frozen v1.3 read-only
  consumer remains unchanged and has its original optional-field policy.
- Enrichment attachments, reviewed associations/native comparisons, approved
  baselines, drift, historical Explorer and portable bundle export are pending.
- Corpus Tier 1 has one original fixture; Tier 2 is empty. Four Tier 3 candidates
  remain unapproved with unknown actual capture hashes where bytes were not acquired.
  No actual external industrial capture was tested or redistributed. Acquisition
  tooling remains deferred until an entry can be approved with exact byte identity.
- The package/engine-version transition and final v1.4 contract freeze are pending.
  Existing native comparison goldens and all historical tests were left intact.
- Hosted six-configuration acceptance and owner release approval remain mandatory
  before presenting a release candidate as accepted.

## Changed files and Git handoff

There are 33 changed files relative to the reviewed main:

```text
.github/workflows/ci.yml
CHANGELOG.md
MANIFEST.in
README.md
docs/development/v14-architecture.md
docs/development/v14-enrichment-contract.md
docs/development/v14-evidence-contract.md
docs/development/v14-progress.md
docs/development/v14-protocol-corpus.md
docs/v14-foundation.md
src/otarchguard/capture/cli.py
src/otarchguard/capture/protocols/__init__.py
src/otarchguard/capture/protocols/contract.py
src/otarchguard/capture/protocols/dcp.py
src/otarchguard/capture/protocols/modbus.py
src/otarchguard/capture/protocols/packet.py
src/otarchguard/capture/protocols/validation.py
src/otarchguard/cli.py
src/otarchguard/evidence/__init__.py
src/otarchguard/evidence/cli.py
src/otarchguard/evidence/observations.py
src/otarchguard/evidence/workspace.py
tests/fixtures/protocol-corpus/manifest.json
tests/fixtures/protocol-corpus/synthetic-industrial.pcap
tests/fixtures/protocol-corpus/tshark-receipt.json
tests/test_evidence_workspace.py
tests/test_protocol_corpus.py
tests/test_protocol_enrichment.py
tests/test_v14_independent_audit.py
tests/test_v14_integration.py
tools/evidence_walkthrough.py
tools/protocol_corpus.py
tools/public-files.txt
```

Local review commands:

```console
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
git show --stat dacda7cd3bf12ed95ad52b8e5cf66533b79c0311
```

No push, pull request, merge, tag, release, repository-setting change or hosted
workflow dispatch was performed. Remote mutation still requires owner authorization.

## Remaining milestones

1. V14-01: EtherNet/IP/CIP, classic S7comm, IEC-104, OPC UA Binary and DNP3,
   each with bounded framing, independent positive/negative fixtures and tests.
2. V14-02: reviewed enrichment/native-evidence attachments, complete snapshot
   lifecycle and explicit evidence/architecture baseline approval contracts.
3. V14-03: deterministic historical comparisons, coverage compatibility, stable
   findings and exact source joins; never infer blocking from missing observations.
4. V14-04: usable offline historical Explorer, source navigation, accessibility,
   pagination and finite performance measurements; evaluate the known native
   forwarding legend mismatch with a regression.
5. V14-05: legally reviewed actual external captures, pinned payload hashes,
   reference-decoder receipts and documented unsupported real-world cases.
6. V14-06: explicit package/engine-version transition preserving historical native
   witness contracts, final contract freeze/independent consumer, security/resource audits,
   installed wheel/sdist and historical compatibility, full six-configuration
   hosted candidate CI and owner-controlled release decision.

The next local step after the verified foundation is protocol V14-01. Preserve this
checkpoint and require each decoder's focused acceptance before adding its public
supported inventory entry. Do not advertise the development build as a complete
seven-protocol release candidate.
