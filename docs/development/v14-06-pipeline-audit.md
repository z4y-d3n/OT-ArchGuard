# V14-06 capture, protocol and historical pipeline assurance

This is specialist B's bounded internal review, performed against the exact
V14-05 production bytes installed in `.venv` (distribution `1.4.0.dev1`, native
engine `1.3.0`, Python 3.14.5 on Windows). Parent commit:
`ac893bc3174f0a7ace67454d19ad6e61116425af`. The integrator must rerun the new
checks against the frozen `1.4.0` installation; these results alone do not
validate a later installation or hosted matrix.

## Result and changes

No demonstrated parser, protocol-decoder, historical authority or source-replay
P0/P1 implementation defect was found in this investigation. Four composed
regressions were added in `tests/test_v146_pipeline_audit.py`; production code,
schemas, frozen fixtures and existing assertions were not changed.

One significant upgrade-documentation boundary requires explicit disclosure:
the distribution-only change in `__init__.py` changes selected implementation
identity, so old analytical revisions are deliberately unsupported by the
current exact-source consumer. It is not valid to claim in-place continuity of
development workspaces merely because native analytical semantics are unchanged.

## Finding V146-B01: exact-source workspace upgrade boundary

| Field | Evidence |
|---|---|
| Capability / severity | Development workspace-v2 upgrade / P1 documentation and onboarding risk; no data-corruption finding |
| Expected contract | `revisions.build_revision` requires exact selected implementation semantics; unknown source implementations fail closed. Existing `docs/v14-history.md` explicitly rejects altered implementation hashes. |
| Reproduction | Create a parent revision, baseline, approval and source-reproducible drift report. Replace only the selected `__init__.py` hash with the SHA of the exact `DISTRIBUTION_VERSION = "1.4.0.dev1"` to `"1.4.0"` byte substitution. Call `lifecycle.load_state` and `reports.verify_report`. |
| Actual | Both reject `EVIDENCE_REVISION`: unsupported/inconsistent producer semantics. Generic storage integrity still verifies. Every workspace byte remains unchanged. Restoring the parent selected identity restores canonical source replay. |
| Source | `evidence/revisions.py`: `_SOURCES`, `implementation_identities`, `build_semantics`, exact equality in `build_revision`; `lifecycle._operation` validates the complete dependency graph. |
| Original / stable-token init SHA-256 | `970f736133968e77bee8b8675d01c70465c8fe441c368e6750d0cdf76e311525` / `dfea43564e1416d2996e5007a29da17f2d97603f5883c48c9c3aec9f70a8289c` |
| Local receipt | `output/v146/pipeline-version-boundary.json`; exact token replacement simulated through the selected-source identity function, without modifying installed files. |
| Recommended disposition | Preserve exact development environment and original workspace for prior replay. For stable work, initialize a fresh workspace, import preserved validated observations and attachments, create new revisions, and explicitly propose/review a new baseline. Do not rehash old analyses or transfer approval. Integrator owns public documentation disposition. |
| Verification / residual limit | New unknown-init-identity regression checks rejection, separate storage integrity, no rewrite and restored original interpretation. No automatic migration or arbitrary source-hash normalization is implemented or justified. |

The exact-source boundary is intentional conservative behavior. Changing the
distribution identity does not change frozen native results, but it does change
the recorded implementation bytes. A future compatible consumer or migration
would require an independently reviewed contract; this review does not invent it.

## Cross-component consistency and contract inventory

| Transition / identity | Independently checked behavior | Evidence and interpretation boundary |
|---|---|---|
| PCAP/PCAPNG container v1 → observation v2 | Bounded packet/header metadata; unsupported linktypes do not expose inner industrial bytes | V14-05 interoperability and historical-integrity cases retain NULL/SLL/unknown framing as unassessed through HTML. Complete file scan is not complete sensor visibility. |
| Packet adapter → enrichment v1, decoder 2 | Complete supported outer frame required; standard ports alone remain hints | New seven-family workflow retains six empty TCP SYNs as `PORT_HINT` and incomplete DCP as `TRUNCATED`, with no positive header fields or message category, after attachments, revisions and drift. |
| Packet sequence → protocol metadata | Consecutive TCP sequence numbers and packet ordering do not implement reassembly | New split-Modbus workflow uses a complete literal FC6 ADU split across two independently framed TCP packets. Both capture orders remain two truncated records through replayed historical comparison; private register/value bytes are absent from the report. |
| Enrichment → attachment v1 | Capture metadata, exact sampled packet references, endpoints, transport, protocol selection and allowed header fields are checked | Cross-capture imports publish no attachment/revision. Unsampled aggregate joins remain explicitly weaker than exact original-packet reproduction. Metadata hashes do not authenticate capture origin. |
| Snapshot v1 / workspace v2 → analysis v1 | Physical capture and analytical identities are separate; exact source semantics and selected limits are recorded | Narrower limits for the same capture produce a different analysis. Decoder/limit mismatch withholds operational protocol comparison and remains analytical reinterpretation. |
| Analysis → baseline/review v1 | Approval binds exact membership and scope; modified interpretations do not inherit approval | Supersession/revocation are freshly evaluated. Old reports preserve recorded historical facts; current approval is a separate answer. Reviewer text remains unauthenticated. |
| Baseline → drift v1 | Finite observed metadata differences retain coverage, comparability, unknown and unsupported states | Missing records do not prove absence, outage, blocking or process change. SYNs do not prove an established application session. Source/port labels are not deployed firewall authority. |
| Drift → historical Explorer v1 | Exact source reproduction precedes publication; bundle identity and portable integrity differ from source authority | Missing unselected dependencies reject fresh source validation. Render-time source changes publish no successful manifest. Rehashed generation assertions cannot authenticate current approval. |

Resource ceilings remain the actual configured capture, enrichment, workspace,
drift and publication ceilings. Reviewed tests exercise exact bundle-byte limits,
record iteration, packet framing and publication failures. New tests introduce
no limit increases, ignored errors, application session inference or network use.

## Seven bounded protocol families

| Family | Supported metadata boundary | Independent evidence reviewed | Remaining limit |
|---|---|---|---|
| Modbus TCP | MBAP and selected PDU shapes; no values/transaction correlation | Literal positive, exception, truncation, unsupported shapes; split-packet historical workflow | No external positive reference capture accepted; no TCP reassembly |
| PROFINET DCP | Selected Ethernet FrameID/service/selector/TLV forms | Literal VLAN Get/response and negative framing; incomplete header through history | No accepted external positive reference; no identity/configuration-success inference |
| EtherNet/IP / limited CIP | Selected TCP encapsulation/CPF/CIP envelopes | Independent literal cases and retained external field-comparison receipts | UDP implicit I/O/deep services/session success outside scope |
| Classic S7comm | Selected TPKT/COTP/S7 header forms | Literal job/error cases and retained external Snap7 receipts | S7 Plus, unsupported functions/userdata and segmented forms abstain |
| IEC-104 | Selected APCI/ASDU structure | Literal I/S and adversarial length/layout cases | No accepted external positive reference; process values and success outside scope |
| OPC UA Binary | Selected transport/message/chunk metadata | Literal HEL/ERR private-body cases; retained external gap/handshake receipts | Opaque secure bodies, segmented/incomplete and unsupported framing remain distinct |
| DNP3/TCP | Selected link/transport/application header subset with CRC checks | Literal read/response cases and retained external receipts | Unsupported application functions and transport fragmentation abstain |

The original V14-05 fixture has 28 finite packets, independently authored literal
expectations and retained TShark field joins. Its existing tests validate fixture
bytes, reference-receipt identity and protocol/status denominators. This review
did not reacquire external traces or rerun TShark; retained external receipts are
historical observations, not new external execution evidence.

## Corpus provenance and distribution rights

The reviewed manifest contains 14 entries: two original fictional synthetic
entries, eight `approved_external` local-analysis entries and four candidates.
All eight approved external entries retain `redistribution: unknown`; that
status authorizes neither redistribution nor an operational provenance claim.
Their documented collector/context uncertainties remain material. Existing
external receipts report both positive selected-field matches and actual
unsupported outer-linktype outcomes; zero-positive NULL/SLL cases are not
positive protocol validation.

`git ls-files '*.pcap' '*.pcapng'` lists only the two fictional capture-studio
examples and the two original synthetic protocol fixtures. No external capture
bytes were added or redistributed by this review. Modbus/DCP/IEC104 external
positive gaps remain disclosed. No plant validation, authenticated custody,
professional pentest or industrial certification is claimed.

## Executed verification

All commands used `.venv/Scripts/python.exe`. Runtime imported the regular
installed package under `.venv/Lib/site-packages`, with parent init hash above.
For test commands, `OTARCHGUARD_OFFLINE_CHECK=1` and `PYTHONPATH=tools/offline`
denied Python network operations, including child processes covered by that hook.
This is tested offline behavior, not evidence of a physical air gap.

| Campaign | Result | Receipt |
|---|---|---|
| New pipeline tests before final type-only edit | 4 PASS, 3.90 s | Focused terminal result |
| 14-file pipeline/security/authority campaign | 612 PASS, 1 SKIP, 101.55 s | `output/v146/pipeline-focused.xml` |
| New tests plus protocol corpus and external-receipt/provenance tests after formatting/type correction | 59 PASS, 8.02 s | `output/v146/pipeline-provenance.xml` |
| Ruff lint and format on new test file | PASS | Focused terminal result |
| Strict mypy with source modules and isolated cache | PASS, 98 source files | `python -m mypy --cache-dir .mypy_cache/v146-pipeline src tests/test_v146_pipeline_audit.py` |

The 14-file campaign comprised the new file, V14-05 corpus/interoperability/
historical integrity, V14-01 protocol integration, the three protocol-decoder
suites, drift observations/adversarial, evidence revisions/reviews, and historical
Explorer/bundle suites. The SKIP is the existing Windows junction test:
`tests/test_historical_explorer_bundle.py:560`, OS junction creation unavailable.
The campaigns overlap; their execution counts must not be summed as new unique
tests. The candidate-wide final campaign and hosted CI remain integrator/owner
gates.

## Residual scope

No TCP reassembly, DLT_NULL/Linux SLL support, application command-success
verification, automatic source-version migration, authenticated review, general
forensic authenticity or multi-writer safety was added. Metadata may contain
sensitive IP/MAC/protocol header identifiers; omission of private application
values is not anonymization. Portable bundle integrity is distinct from
source-dependent analytical reproduction and current authority.
