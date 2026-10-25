# V13-00 — baseline, compatibility inventory and initial decisions

Date: 2026-10-25. Development branch: `codex/v13-01-capture-foundation`.
This is engineering evidence, not owner acceptance or a stable-release claim.

## Immutable reference

The initially clean checkout has HEAD = main = origin/main = peeled v1.2.0:
`f52c792b683cb499dc7de765b65b5cc897a96854`.
Tree: `2229b0657128cdb56eb978eb4fb0a5e74fd275f4`.
The GitHub read connector independently confirmed remote main and the published
v1.2.0 release (2026-10-25T20:42:24Z). Baseline Actions run `40229517515`
completed successfully, including Windows/Ubuntu/macOS × Python 3.12/3.14.
Local baseline execution is recorded separately; remote baseline CI is not CI
evidence for the changes developed here. No remote modifications are authorized.

## Inspected contracts and compatibility risks

| Component inspected with associated tests | Reuse / adapter / risk |
| --- | --- |
| pyproject, manifests, release audits, workflows | Python >=3.12; Typer, PyYAML, Pydantic only. Explicit public-file and sdist allowlists must grow together. Historical release tests require package version 1.2.0; keep it during development, version capture contracts independently. Stable version transition is deferred to release preparation. |
| cli, diagnostics, contract | Add a separate capture command group. JSON stdout, structured stderr, 0 completed result (including discrepancies), 2 invalid/resource/operational failure; 1 remains failed declared intents. |
| domain, validation, normalization, api | Reuse validated immutable schema-1 model and canonical model hash. No traffic in native YAML. Model-formatting changes do not change canonical identity. Valid native models reject duplicate IPv4 addresses. |
| trace, reachability, graph, policy, policy_evidence | Reuse original initiation evaluator, witnesses and frontier diagnostics. Exact service interface, transport and port required. Source queries start at all interfaces of an asset; multihomed sources require conservative handling. No return/session/IPv6/ARP/NAT inference. Bound total capture comparison work as well as query count. |
| ingestion records/reconciliation/project review | Reuse immutable-record, digest, strict-control and explicit-review patterns, not inventory schemas or YAML emission. Decisions bind capture, observations, candidates and model; nothing auto-accepted. |
| explorer/data/html, reporting | Independent capture site; preserve existing Explorer contracts. Reuse escaping and link auditing. Fixed local paths, staged publication, no-clobber output and ancestor-link checks. Existing document shell contains declaration-specific claims and must not be reused unchanged. |
| quality, architecture comparison | Preserve declared-vs-declared semantics. Adapt only bounded control validation patterns. Missing observed traffic never proves blocked traffic. |

## Parser decision and references

Choose a deliberately limited standard-library streaming parser. No new runtime
dependencies or native software. The alternative evaluated was dpkt's maintained
pure-Python capture reader. Its general decoding surface is unnecessary here;
its current PCAPNG Reader centers one IDB and does not supply this project's
section/interface provenance, resource and exact-rational timestamp contract.
A wrapper would still need independent block validation and limits. This is an
implementation-risk decision, not a claim that a custom parser is inherently safer
or that the library has a security defect. Bounded adversarial validation is required.

Technical references inspected:

- [PCAP draft-ietf-opsawg-pcap-09](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcap-09.html)
- [PCAPNG draft-ietf-opsawg-pcapng-06](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcapng-06.html)
- [IANA PCAP LINKTYPE registry](https://www.iana.org/assignments/pcap)
- [dpkt PCAPNG implementation](https://github.com/kbandla/dpkt/blob/master/dpkt/pcapng.py)

PCAP 2.4: both byte orders, micro/nanoseconds. PCAPNG 1.0: SHB, IDB,
EPB, SPB, multiple sections/interfaces, changing byte order, decimal/binary
timestamp resolution and signed timestamp offset. SPB has no timestamp.
Unknown block framing is validated and counted; contents are not interpreted.
Obsolete packet blocks and secrets/name-resolution/custom metadata are not decoded.

## Threat model and boundaries

Attacker controls all capture bytes, sizes, metadata, packet headers and review
files. Reject invalid container framing, inconsistent lengths, invalid interface
references and resource exhaustion before publication. Malformed packet contents
remain explicit damaged observations, never native queries. No payload export,
reassembly, DNS, active capture, remote resources, code execution or model writes.
Input and output paths reject links/junctions and nonregular inputs. Publication
is staged and no-clobber. Concurrent malicious filesystem replacement remains a
platform-dependent risk; do not claim a filesystem sandbox.

## Initial versioned design and acceptance corpus

Capture contract 1 records SHA-256, byte size, format, section/interface metadata,
exact timestamps, counters and coverage. Transient packet bytes are discarded.
Observation contract 1 stores bounded hosts, directed aggregates, bidirectional
conversation identities, explicit TCP SYN evidence and packet index/offset references.
Port catalog 1 labels associations PORT_HINT; header facts TRANSPORT_OBSERVED.
No signature-supported application recognition is planned in this subset.
Mapping contract 1 binds canonical observation/candidate/model and capture hashes;
every accepted/rejected association needs reviewer rationale. Comparison contract 1
retains native query and exact selected interval, original result and limitations.

Independent hand-built binary fixtures will cover four PCAP magic values,
PCAPNG byte-order changes, timestamps, SPB, invalid sizes/options/references,
limits, unknown encapsulation, fragmentation, direction ambiguity, stale decisions,
and output preservation. Full historical tests and installed-distribution checks
remain required. Default ceilings are conservative rejection budgets, not measured
capacity claims; benchmark evidence must identify actual hardware/runtime/workloads.

## Gate result before implementation

A. Executive result: PARTIAL. Reconnaissance and decisions complete; local baseline
execution and candidate evidence are pending. Architecture is additive.

B. Technical evidence: reference commit/tree above; no product code modified before
this inventory. Three independent read-only inspections covered native analytical,
ingestion/review/reporting, and release/baseline contracts. Baseline remote CI PASS;
local regression baseline NOT RUN at the time of this initial report.

C. Quality: no dependency additions; historical contracts preserved by design.
Determinism, parser safety, output safety and runtime performance require execution.

D. Risks: local Python initially lacked verification dependencies; six-platform
candidate CI requires an authorized remote branch/PR operation. Owner review is
indispensable before accepting real identity associations or any stable release.

E. Continuation: implement V13-01 on the new local development branch, execute
adversarial/parser and historical tests, then proceed through later gates where
evidence permits. No gate is formally approved by these engineering reports.
