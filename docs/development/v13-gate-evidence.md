# V13 development gate evidence

Recorded 2026-10-25. These are provisional engineering results, not owner acceptance,
an assertion of product security, or authorization to publish a stable release.
The implementation is on `codex/v13-01-capture-foundation`.

The tested implementation commit is
`3d3bbd5fda3c90690478df06085432fb6371abf8`; subsequent evidence-only commits
do not change production or test bytes. The immutable baseline commit is
`f52c792b683cb499dc7de765b65b5cc897a96854`; its v1.2.0 source tree is
`2229b0657128cdb56eb978eb4fb0a5e74fd275f4`.
See [the baseline inventory](v13-00-baseline-and-decisions.md) for remote reference
verification, compatibility decisions, source inspection and technical references.

## Evidence ledger

The following executions have been reported by the implementing agents. Counts
from overlapping suites are not additive evidence of independent coverage. The
four current capture suites contain 211 tests (91 + 43 + 64 + 13).
PASS below identifies provisional component verification, not human approval or
completion of the separate candidate-wide hardening and release gates.

| Execution | Observed result | Scope and qualification |
| --- | --- | --- |
| Historical v1.2 baseline suite | PASS: 2,322 tests, 579.94 s | Before the candidate changes; establishes baseline health, not candidate regression success |
| `tests/test_capture_parser.py` | PASS: 91 tests, 2.60 s | Local Windows Python 3.14, development source; final parser functionality |
| `tests/test_capture_observations.py` | PASS: 43 tests | Local decoder, aggregation, damaged packet, TCP options and EPB flags checks |
| `tests/test_capture_reconciliation.py` | PASS: 64 tests | Shared mapping/comparison tests, including strict controls, native engine oracles and result amplification budgets |
| `tests/test_capture_cli.py` | PASS: 13 tests | CLI, output preservation, HTML, denied sockets/DNS and deterministic site bytes |
| Ruff and strict mypy | PASS repository-wide | Ruff check and formatting; strict mypy: 141 source files; pip check: no broken requirements |
| Entire candidate regression suite | PASS: 2,533 tests, 486.51 s | Regular installed final candidate wheel, Windows/Python3.14.5, network denied; 0 failures/errors/skips. `output/v1.3-candidate/full-suite.xml` and source-identity receipts bind the tested code. Superseded runs are not acceptance evidence |
| Wheel and sdist archive audit | PASS | `output/v1.3-review/archive-audit.json` and final `output/v1.3-final/archive-audit.json` record archive/source bytes, metadata, licenses and public manifests |
| Clean wheel and sdist environment installations | PASS, offline | Separate fresh environments, no-index/no-deps/no-build-isolation product installs; `clean-wheel.json` and `clean-sdist.json` verify installed module hashes and native consoles |
| Clean installed-sdist capture suite | PASS: 211 tests, 6.35 s | Network denied; `output/v1.3-review/sdist-capture.xml` |
| Legacy command/report comparison | PASS: 45 cases, 123 artifacts | Exact JSON/HTML/SVG/stdout/stderr bytes and exit codes versus immutable v1.2; `output/v1.3-candidate/legacy-contract-comparison.json` |
| Committed public source identity | PASS: 269 files | `verify_source_checkout.py` verifies exact Git blob bytes; final receipt at `output/v1.3-final/source-checkout.json` |
| Installed-console fictional walkthrough | PASS | `output/capture-tutorial/walkthrough.json`; all six expected finding classes were verified |
| Clean wheel/sdist walkthroughs outside checkout | PASS, both | Copied standalone driver, no development source imports; `output/v1.3-review/clean-wheel-tutorial/walkthrough.json` and corresponding `clean-sdist-tutorial/` |
| Representative benchmark executions | PASS: seven final-source workers | Six complete reports, one expected resource rejection; [measured conditions and hashes](v13-benchmark-results.md) |
| Candidate Windows/Ubuntu/macOS × Python 3.12/3.14 hosted CI | NOT RUN | No remote candidate branch/PR write has been authorized |

The parser command was run with `PYTHONPATH=src` and a workspace-contained pytest
base directory because the managed environment's default temporary directory did
not permit pytest directory creation. This is not installed-distribution evidence.
The initial baseline environment had no new capture modules. Setup/collection
failures from that environment were corrected before the successful runs above.

## V13-00 — Baseline and architecture decisions

**A. Executive result — PASS, provisional engineering baseline.** The local and
remote main/tag relationship, historical release and workflow evidence, native
contracts and parser alternatives were inspected before substantive implementation.
The historical local test suite passed. The additive capture boundary is documented.

**B. Technical evidence.** Branch and baseline commit/tree are recorded above.
The initial inventory is `docs/development/v13-00-baseline-and-decisions.md`.
No historical acceptance record, release, tag or protected branch was modified.
Baseline hosted CI success concerns the baseline alone. The initial document records
the independently verified baseline Actions run and published release identity.

**C. Quality.** Native schema 1, initiation semantics, deterministic contracts,
Import Studio and Architecture Explorer remain the compatibility boundaries.
No runtime dependency is added. The limited standard-library parser was selected
after evaluating dpkt against required provenance, section/interface and limit needs.

**D. Risks.** A parser subset requires its own adversarial validation. Source and
candidate release manifests must remain synchronized. No human acceptance is
asserted, and baseline success does not validate new code.

**E. Continuation.** Implement the documented container subset and verify both its
independent binary fixtures and the affected product contracts.

## V13-01 — Secure capture foundation

**A. Executive result — PASS, provisional component verification.** The contracted
container parser, independent capture limits and `capture inspect` are implemented.
Targeted parser checks, additive CLI integration and initial archive integrity pass;
candidate-wide regression and final distribution checks remain assigned to V13-06.

**B. Technical evidence.** New files are `capture/__init__.py`, `capture/contract.py`
and `capture/parser.py` under `src/otarchguard/`, plus `tests/test_capture_parser.py`.
Capture contract 1 records exact file hash/size, supported record counts, interface
provenance and limitations. The 91 tests include four PCAP magic variants, endian
changes, exact timestamps, SPB, options, section boundaries and resource edges.
Fixed mutations are bounded to 192 tiny inputs. A real-descriptor read oracle scans
2,000 records using 4,003 reads, each at most 60 bytes.

**C. Quality.** Hashing and parsing share one regular opened stream. File identity
is checked before/after; container corruption is fatal. Captured size, packets,
blocks, block size, metadata and interfaces are independently bounded. Input links,
junctions and UNC paths are refused. No packet payload or metadata string is exported.
Ruff and strict mypy pass. See the appendix for timestamp, padding and capture flags.

**D. Risks.** Unknown blocks receive generic framing validation only; obsolete packet
blocks are omitted with an explicit limitation. Supported packet counts exclude
those blocks. Concurrent hostile filesystem replacement is not sandboxed. Windows
Python 3.14 exposes different ctime meanings through lstat/fstat; cross-API identity
uses device/inode/size/mtime, retaining ctime checks between the two fstat calls.

**E. Continuation.** Complete candidate-wide verification and preserve the parser's
failure-before-publication behavior through decoding and report integration.

## V13-02 — Observations and conversations

**A. Executive result — PASS, provisional component verification.** Header metadata,
deterministic directed aggregates, bidirectional groups, coverage and catalog-1
industrial port hints are implemented. Targeted checks and all seven final-source
representative workload executions passed their stated expected outcomes.

**B. Technical evidence.** `capture/observations.py` and
`tests/test_capture_observations.py` implement observation contract 1. The 43-test
execution covers Ethernet/raw IP, VLAN, IPv4/IPv6, TCP/UDP, ICMP/ARP, short packets,
fragments, extension bounds, metadata cardinality, sample omissions, TCP options
and EPB flags. `benchmarks/capture.py` executed fixed synthetic 1k/10k/100k/250k,
skewed and high cardinality scenarios. The final-source table and exact fixture
hashes are in [the benchmark report](v13-benchmark-results.md).
Repeated 1k/10k/100k/250k workloads measured 0.312/1.786/17.094/44.636 seconds,
respectively; their traced peak Python allocations stayed below 488,000 bytes.
The 1k high-cardinality case completed with 11,231,180 traced peak bytes and
6,855,711 report bytes. The adversarial 10k high-cardinality input was rejected
at the 64 MiB allocation-accounting ceiling without publishing a partial report.
These are single Windows Python 3.14.5 measurements under concurrent test load,
with tracing enabled; process RSS and other platforms were NOT MEASURED.

**C. Quality.** Ports are cleared for damaged/fragmented/unsupported metadata.
Only qualifying SYN headers contribute possible-initiation evidence. Exact rational
first/last times preserve missing values. Captured copies remain record counts;
neither independent sessions nor successful application exchanges are inferred.
Conservative allocation accounting and cardinality limits bound aggregation.
The final review corrected TCP option TLV/known-length/padding and reserved-bit
validation before the installed candidate was frozen. Malformed options cannot
contribute ports or SYN initiation evidence.

**D. Risks.** There is no deduplication, reassembly, application decoder or checksum
validation. Port hints are not protocol recognition. Allocation accounting is not
a measured RSS limit. Synthetic traffic does not demonstrate real-plant coverage.

**E. Continuation.** Preserve the measured workload conditions and verify that every
association and comparison remains bound to canonical observations and uncertainty.

## V13-03 — Evidence mapping and owner review

**A. Executive result — PASS, provisional component verification.** Exact IPv4
interface proposals and evidence-bound owner decisions are implemented. No identity
is accepted automatically. Targeted controls and installed-console tutorial pass;
the candidate-wide regression result remains pending in V13-06.

**B. Technical evidence.** `capture/reconciliation.py` introduces association
contract 1; CLI `capture map` emits pending JSON. Binding includes capture, canonical
model, observation and candidate hashes. The shared 64-test reconciliation suite
covers stale bindings, duplicate/orphan proposals, contradictory selections, strict
JSON, explicit rejection, pending decisions and exact candidate selection.

**C. Quality.** Accepted/rejected decisions require reviewer and rationale. Proposed
facts cannot be edited. MACs, names, roles, prefixes and vendors do not establish
identity. Valid native models already reject duplicate declared IPv4 addresses.
No capture workflow emits or edits native YAML.

**D. Risks.** Hashes do not authenticate reviewer identity. Owner review must account
for DHCP, reused addresses, NAT and sensor visibility; exact matching alone cannot
resolve those uncertainties. Real operational decisions require the actual owner.

**E. Continuation.** Verify bound mapping consumption in the installed CLI and retain
the precise owner decisions in every resulting comparison.

## V13-04 — Declared versus observed reconciliation

**A. Executive result — PASS, provisional component verification.** Conservative
adapters use the original evaluator;
stable classifications, native query results and selected-port witnesses/diagnostics
are implemented. Targeted independent oracles pass; final regression remains pending.

**B. Technical evidence.** `capture/reconciliation.py` introduces comparison contract
1. The shared 64-test suite covers reachable/unreachable native models, undeclared
services, unmapped endpoints, ambiguous services, uncertain direction, midstream
TCP, UDP, IPv6, ARP, fragments and incomplete interpretation. This is the same test
execution reported for V13-03, not another independent 64 tests.

**C. Quality.** Native queries require decoded IPv4 TCP SYN evidence, reviewed exact
endpoints, one supported direction and one declared matching destination service.
Multihomed source and self-asset observations are unevaluated. Native work is shared
across queries and resource failures abort the complete operation. Unknown blocks,
damaged packets and snapshot truncation suppress service-absence findings.
The final review corrected repeated native-result amplification: repeated findings
share cached query data, allocation is preflighted before dataclass expansion, and
cumulative pretty-JSON output is bounded. Three independent resource tests verify
shared identity, pre-allocation rejection and repeated-output rejection.

**D. Risks.** Reachability concerns declared initiation, not the captured packet's
physical route, return path, authorization or application success. No discrepancy
establishes intrusion or deployed firewall violation. Incomplete-evaluation code
is reserved; current budget failures are exit 2 with no partial result.

**E. Continuation.** Complete installed walkthrough and regression verification;
retain direct traceability from every conclusion to original native evidence.

## V13-05 — PCAP Evidence Explorer

**A. Executive result — PARTIAL.** Offline overview, host, flow, protocol, finding,
association, evidence and coverage pages are implemented. Automated report checks
pass. Manual browser review is NOT RUN: the available browser's security policy
explicitly rejected the local `file:` protocol and permits only HTTP/HTTPS. That
policy prohibits using an alternate surface to bypass the rejection; no server
workaround was introduced into this offline product.

**B. Technical evidence.** `capture/explorer.py`, `capture/cli.py` and additive CLI
registration provide site contract 1 and four commands. The 13 CLI tests include
canonical output, paths with spaces, preserved inputs/outputs, corrupt input,
pagination, denied sockets/DNS, hostile reviewer text and site-byte determinism.
The existing independent HTML parser audits emitted links and local fragments.

**C. Quality.** Fresh destinations are staged before publication. Fixed local
filenames, escaping, CSP, semantic tables and no active resources preserve offline
operation. Payloads and original captures are omitted. Sensitive metadata notices
remain visible. Large diagrams are explicitly omitted while full tables remain.

**D. Risks.** Automated structural HTML checks do not establish usability or formal
accessibility. There is no anonymization guarantee. Local reports retain necessary
network metadata and must be reviewed before sharing. Publication assumes a local
single writer, as documented for the historical output model.

**E. Continuation.** Review actual rendered pages and execute packaged tutorials;
correct material rendering defects before recommending release candidacy. The
installed-console fictional walkthrough passed all six expected finding classes;
its result is `output/capture-tutorial/walkthrough.json`.

## V13-06 — Hardening and representative validation

**A. Executive result — PARTIAL.** Bounded mutation, uncertainty, determinism,
output-preservation and offline-denial checks execute successfully in targeted
suites. Seven representative synthetic workers completed their expected outcomes.
The final complete installed regression and clean wheel/sdist verification passed.
The gate remains PARTIAL because browser visual review is unavailable and native
evaluation has the bounded-work, non-RSS resource limitation described below.

**B. Technical evidence.** Targeted evidence appears in the ledger. The parser has
192 deterministic mutations; decoder tests add 500 bounded packet mutations.
`tools/capture_workloads.py`, `tools/capture_walkthrough.py` and
`examples/capture-studio/` provide reproducible fictional fixtures and expected codes.
No real capture or benchmark data is used. The installed tutorial passed six
expected classifications. [Benchmark evidence](v13-benchmark-results.md) records
actual times, traced allocations, output sizes and input/source hashes. Both clean
installations verified exact production module hashes and native console origins.
The complete final wheel suite passed 2,533 tests; clean installed-sdist capture
tests passed 211. Historical test files remain byte-identical to the baseline;
the original CLI's additive registration is the only changed historical production
module. Native command/report compatibility preserved 123 exact artifacts.

**C. Quality.** No new runtime dependency, native tool, privilege or network service
is required. v1.2 tests and expectations were preserved. Wheel/sdist, source audits,
full regression and runtime environment checks must agree on candidate bytes.

**D. Risks.** Baseline results are not candidate regression results. Fixed mutations
are not exhaustive fuzzing or a security audit. Local Windows evidence cannot prove
all supported OS/Python combinations. The browser rejected local `file:` navigation,
so visual review remains NOT RUN despite successful structural HTML/link audits.
Pending checks are NOT RUN, not PASS.
Branch/line coverage percentages were NOT MEASURED. Native QueryResult construction
occurs inside the preserved evaluator under cumulative native work ceilings;
capture allocation accounting bounds retained evidence and its conversion, not
every transient engine allocation or whole-process RSS. No OS memory sandbox is
claimed. This residual limitation requires review for unusually large native models.

**E. Continuation.** Complete visual review and review residual native-model resource
assumptions. Repeat affected verification when production/test bytes change. Preserve
the executed suite, walkthrough and workload evidence with their stated scope.

## V13-07 — Release candidate preparation

**A. Executive result — PARTIAL.** Local review preparation is complete. This work
is not recommended as a stable v1.3 release candidate while required evidence is
missing. Human acceptance and stable version transition remain outstanding.

**B. Technical evidence.** Documentation includes overview/contracts, supported
matrix, privacy/threat model, CLI, interpretation, limits and fictional tutorial.
Candidate source/test manifests, audited wheel/sdist, installed module identities,
complete local regression and draft release notes are available for review.
Final artifact/source hashes are in `output/v1.3-final/`; the implementation and
all historical refs remain distinct. Candidate six-cell hosted CI
is NOT RUN. Baseline six-cell CI is historical reference evidence only.

**C. Quality.** Native schema, engine contracts and existing reports remain at their
historical versions. The package/engine version intentionally remains 1.2.0 during
additive development. Capture contracts are independently versioned at 1. No stable
tag, release, package publication, merge, auto-merge or history rewrite occurred.

**D. Risks.** Remote candidate CI requires an authorized remote write. Stable
version changes, final acceptance and publication require explicit owner action.
Claims about all six candidate environments must wait for actual successful runs.
Visual browser review also remains NOT RUN because local `file:` navigation was
denied by the available browser's security policy.

**E. Continuation.** Present the concrete local diff and evidence for review, obtain
remote write authorization only when needed, execute six hosted combinations and
obtain formal human acceptance before any stable publication.

## Parser contract appendix

- Classic PCAP 2.4 supports both byte orders and micro/nanoseconds. Reserved fields
  and extended LINKTYPE/FCS flags are rejected as outside the accepted subset.
- PCAPNG supports version 1.0; compatible minor 2 is explicitly treated as 0 under
  draft-ietf-opsawg-pcapng-06. Other section versions are fatal incompatibilities.
- Timestamp resolution is exact: decimal and binary exponents 0 through 127,
  unsigned original ticks and signed 64-bit whole-second interface offset.
- Option, EPB and SPB alignment padding is required to be zero. A missing option-end
  marker is accepted only when the list ends exactly at its block boundary.
- Unknown/custom data is never decoded or exported. Custom options and recognized
  custom block types require their structural four-byte enterprise-number field.
- EPB error flags become explicit damaged-packet observations. Segmentation-offload
  flags prevent native initiation evaluation. Neither flag is interpreted as an
  application verdict or deployed policy decision.
- `packet_bytes` bounds captured bytes; original wire length remains an unsigned
  reported counter and never controls allocation. Metadata, records and block
  storage have independent ceilings. Defaults are rejection budgets, not capacity
  guarantees.
