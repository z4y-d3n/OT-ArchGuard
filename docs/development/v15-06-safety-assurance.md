# V15-06 — safety assurance

Scope: finite fictional declarations and existing bounded independent corpora.
No production safety correction was necessary in the investigated supported
contracts. Runtime change is the distribution literal only. This is evidence
for owner review, not universal correctness or OT certification.

## Risk and assertion map

`EXISTING_VERIFIED` means the actual assertions were reviewed and executed;
`COVERAGE_GAP` identifies the two relations closed by this gate.
`CONTRACT_DEPENDENT` means the qualification follows the existing public boundary.
Exact node IDs/counts/outcomes are in the JUnit receipts cited below.

| Case / priority | Classification / input and mutation | Contract / independent oracle | Result / evidence |
|---|---|---|---|
| P0-A | COVERAGE_GAP closed: boundary-device IT→gateway→DMZ→second gateway→OT, denied direct crossing and explicit access records | Existing raw `oracle` per port and `replay_raw` witness; direct deny cannot erase the other permitted route | PASS: `test_v15_06_safety.py::test_alternate_multihop_route_and_critical_forwarding` |
| P0-B | EXISTING_VERIFIED: boundary-device interfaces, absent/reverse forwarding, protocol and selector changes | Every directed transport/forwarding edge needs allow; applicable deny wins regardless of specificity/order; interfaces never imply forwarding | PASS: reachability T04/T05/T06/B02–B08/T09, oracle and policy suites |
| P0-C | COVERAGE_GAP closed: deny critical `f_it_dmz`, restore it, allow direct alternative, remove original declaration | True→false→true and surviving independent witness; general allow cannot defeat specific deny | PASS: same new relation; minimal witness replay independently reads original edge/rule declarations |
| P0-D | EXISTING_VERIFIED / CONTRACT_DEPENDENT: unknown reference, interface placement, unsupported policy, document conflicts, stale review | Validation rejects invalid supported declarations; review never implicitly approves candidates; finite validated subsets retain owner completeness qualification | PASS: validation, ingestion projects/documents, reporting and new propagation tests |
| P0-E | COVERAGE_GAP closed: valid minimal model with no permits and prohibited intent versus missing destination interface | CLI JSON/HTML retain model scope, all limitations and completeness declaration; genuine negative has diagnostics; rejected input exits 2, writes no report/Explorer | PASS: two parameterized public-output relations in `test_v15_06_safety.py` |
| P1-CAP | EXISTING_VERIFIED: empty/truncated PCAP/PCAPNG, length conflicts, unknown link type, multiple interfaces/times, duplicates, IPv6 subset, exact ceilings | Container metadata and reference packets; controlled diagnostics, deterministic identity and no partial publication | PASS: parser, independent semantics/resources, reconciliation, ARP and frozen evidence suites |
| P1-OBS | EXISTING_VERIFIED: observed model-unreachable, declared unobserved, pending/rejected mappings, reused addresses | Preserve evidence/discrepancy; absence is finite and coverage-scoped; unaccepted mapping performs zero native queries | PASS: `test_capture_independent_semantics.py` explicit classification/absence/review assertions |
| P1-PROT | EXISTING_VERIFIED: seven bounded header subsets, every split prefix, inconsistent/unsupported framing | Hand-authored cases, fixed CRC vector/reference corpus; absent fields on abstention; header recognition does not assert execution | PASS: protocol enrichment, ENIP/S7, IEC/OPC/DNP suites and existing corpus walkthrough |
| P1-IMP | EXISTING_VERIFIED: complete/partial/conflicting/malformed documents, duplicate identities, stale source and owner controls | Retain documentary observations, unresolved candidates, explicit review; reviewed round trip does not infer links/rules | PASS: documents, projects, graphical/XLSX security; malformed source prevents publication |
| P1-HTML | EXISTING_VERIFIED: HTML labels, Unicode/bidi, controls, long IDs, unsafe paths, broken anchors, JSON/HTML | Escaping, CSP, path masking, bounded output, link audit, atomic publication | PASS: reporting/Explorer, hostile documents, drift adversarial suites |
| P1-HIST | EXISTING_VERIFIED: rehashed malicious reports, cross-producer replay, revocation/supersession | Recorded approval differs from current authority; no approval transfer; unchanged evidence after old-source recovery | PASS subject to exact transition receipt: see compatibility record |
| P1-PKG | EXISTING_VERIFIED plus new stable authorization: forged metadata/source/inventory, checksum/manifest claims | Exact immutable Git bytes, pre-import physical hashes, independent archive reopen; never trust candidate-generated expected hashes | See compatibility and acceptance receipts |
| CSV formula export | NOT_APPLICABLE | No CSV/spreadsheet report export surface; hostile XLSX **input** formulas are separately tested | No export-security claim |
| Live devices / physical isolation / TCP reassembly | NOT_APPLICABLE | Outside supported offline/passive contract | Not tested or implemented |

## Independence and bounded work

`test_reachability_oracle.oracle` builds transitions directly from dictionaries,
selects raw rules and recursively enumerates simple state paths for concrete
ports. It calls no production reachability or policy helper. `replay_raw` checks
every witness endpoint, phase, original edge, selector, port and deny/allow
evidence independently. The fixed 36-seed comparison and 12-seed ordering/
permission properties are reused. Existing metamorphic coverage also checks
trace coverage corruption, isolated assets, display/order changes and equivalent
rule splitting. Monotonicity is applied only under actual deny precedence.
No duplicate solver or open-ended fuzz campaign was introduced.

Parser fuzz reuse is exactly 192 tiny mutations, seed 1301, two finite valid
container seeds. It accepts controlled `ModelError` or verifies input size/hash
and bounded packet count. Existing protocol mutations/split-prefix tests and
import hostile-container ceilings add independent finite cases. No resource
limit was increased and no transaction/parser capability was added.

## Findings and limitations

No unexplained oracle disagreement or unqualified false-isolation result was
demonstrated. A structurally valid model with missing real-world connections can
yield a negative **within that declared model**. JSON/HTML preserve the explicit
completeness declaration, scope and limitations; Explorer preserves the owner
scope and unassessed classifications. This remains a human completeness boundary,
not evidence of deployed isolation. Invalid input never reaches native evaluation
or a complete success report. Resource rejection is explicitly an error.

The new topology initially lacked the mandatory external-crossing access record;
validation correctly rejected the test fixture. Correcting the fictional fixture
was a test-contract correction, not a product fix or weakened assertion.
The first batch also encountered a missing pytest temporary parent; its interrupted
log is retained and excluded from passing counts. Both issues were corrected.

The first assembler rehearsal exposed a packaging-tool defect: using `sys.argv[1]`
again after `setuptools.build_meta.build_wheel` used its rewritten argv as the
sdist destination. The audit rejected the missing expected archive and published
no four-asset set. The tool now captures the destination before either build;
an independent tiny backend that mutates argv reproduces the defect and verifies
the correction. The complete suite was interrupted for this correction and
restarted after stabilization; interrupted counts are not reported as acceptance.

Assembly review also identified an avoidable trust gap in importing protected
predecessor helpers before checking them: an unchecked helper `.pyc` could execute
before source authorization. The new assembler compiles authenticated Git bytes
for reused checkout/audit/assembly primitives directly. A benign marker payload
in an unchecked helper cache never executes; an unsafe-import mutation does
execute it, demonstrating regression sensitivity. No predecessor tool or policy
was changed. Final assembly and safety refinements receive a focused supplement;
the complete runtime suite is not counted twice.

Receipts: `output/v15-06/safety/baseline.xml` (925 passed), `p1.xml`,
`stable.xml`, and final complete-suite XML under `output/v15-06/final/`.
Overlapping executions are not summed. See [acceptance](v15-06-acceptance.md)
for final outcomes and explicitly unexecuted validations.
