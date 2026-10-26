# V13-09 — Independent semantic verification

Review date: 2026-10-25. Reviewer B inspected production code before using prior
gate reports. Review baseline: `4fb9b4863ee59684211e7a3315221ff89102bebb` on
`codex/v13-01-capture-foundation`. This record adds evidence; it does not revise
historical gate outcomes or grant release acceptance.

## Result and independence

**Local semantic corpus verified: 43 passed, 0 failed, 0 skipped.** No confirmed
analytical defect was found in this review scope. Final frozen-source installed
regression and six-platform CI remain separate requirements in V13-12/V13-13.

`tests/test_capture_independent_semantics.py` constructs classic PCAP and a
two-interface PCAPNG directly with `struct`; it imports neither the production
capture writer nor existing reconciliation-test helpers. Its independent oracle
is the Boolean result for one directed edge and an explicit permitted-port set.
Twelve combinations vary edge presence, permit presence and observed ports
501/502/503. The production native engine is additionally called to compare full
witness/diagnostic preservation, but is not used to compute oracle expectations.
The model is the established schema-v1 minimal fixture, modified before normal
validation. This is a finite reference corpus, not an independent implementation
of the entire native reachability engine.

## Finding and hypothesis register

| ID | Severity/status | Location | Challenge, evidence and resolution |
|---|---|---|---|
| SEM-01 | No defect reproduced | `capture/reconciliation.py:407-459` | Suspected result reuse across observed destination ports. A single cached native query produced unreachable/reachable/unreachable for 501/502/503; exact intervals and port values were preserved. Run-local `(source_asset, service)` cache is adequate because a service fixes destination/interface/protocol and retains all native intervals. |
| SEM-02 | No defect reproduced | `capture/reconciliation.py:228-283` | Suspected transferable owner approval. Changed capture, model revision, candidate facts, host identity and forbidden reviewer controls all failed closed. Existing strict-owner suite also covers missing, duplicated, orphaned and contradictory proposals. |
| SEM-03 | No defect reproduced | `capture/reconciliation.py:331-399` | Suspected implicit identity or wrong-interface listener matching. Pending/rejected identities made zero native queries; an accepted destination address on a different interface from the declared listener remained undeclared. Multihomed source queries remained unsupported. |
| SEM-04 | Retained scope limitation | `capture/observations.py:482-492`, `capture/reconciliation.py:36-48` | Observed IP reuse and different frame-source MACs aggregate under one IP record. This does not resolve DHCP, NAT, spoofing or transit ownership. Proposals remain pending; any acceptance is an explicit owner assertion for this capture. No automatic causal or identity conclusion is made. |
| SEM-05 | Retained scope limitation | `capture/reconciliation.py:463-506` | Fully parsed finite capture absence is scoped even when physical sensor coverage is unknown. Empty capture produces only `DECLARED_SERVICE_NOT_OBSERVED`, expressly stating that this does not establish blocking or complete visibility. |
| SEM-06 | Unsupported premise resolved | `validation.py:197-215` | Multiple declared interfaces with the same exact IPv4 host cannot occur in a legitimate validated schema-v1 model: duplicate addresses are rejected. Manufacturing an invalid `ValidatedArchitecture` would bypass the product validation contract and is not valid evidence of an accepted ambiguity case. |

No production edits were necessary for the findings above. No critical/high
semantic issue remains identified by this reviewer. This statement is limited to
the reviewed paths and executed corpus, not a comprehensive security guarantee.

## Claim-to-evidence matrix

All test names below refer to `tests/test_capture_independent_semantics.py` unless
another file is specified. Parameterized cases are included in the total 43.

| Claim/condition | Exact evidence | Expected and observed outcome |
|---|---|---|
| Reachable and unreachable native queries; retained witnesses/diagnostics; source/model preservation | `test_independent_port_sensitive_reference_corpus` (12 cases) | One-edge oracle agrees; capture digest, packet offsets, association IDs and complete native result agree; input bytes/canonical model unchanged. |
| Cached queries do not exchange port conclusions | `test_cache_selects_each_observed_port_from_shared_query` | One native query; distinct correct selected intervals for three ports. |
| Initial SYN; SYN-ACK without SYN; midstream; RST; SYN+RST; UDP | `test_independent_raw_classification_and_evidence` | Only valid initial SYN receives a native result. Remaining cases retain uncertain initiation. |
| Undeclared port, unknown source/destination, NAT not represented in model | `test_independent_raw_classification_and_evidence` | Undeclared or unmapped, zero native result. Familiar port is only `PORT_HINT`. |
| IPv6, ARP, fragments, truncated headers, unknown encapsulation | `test_independent_raw_classification_and_evidence` | Unsupported native scope; fragment/truncation/unknown linktype expose no authoritative ports or initiation and suppress absence. |
| Destination interface differs from listener interface | `test_declared_destination_interface_must_match_observed_address` | Undeclared; zero query; listener remains absent within stated scope. |
| Repeated packets, multiple sensor interfaces, partial visibility | `test_duplicate_sensor_copies_are_counted_without_strengthening_conclusions` | Two records retained, one aggregated flow, both interface references, one native query; sensor visibility remains unknown. |
| Missing traffic in a completely parsed capture | `test_no_traffic_is_only_finite_capture_absence` | Empty observation list, scoped absence only, no blocking claim. |
| Pending and owner-rejected identities | `test_unaccepted_owner_identity_never_runs_evaluator` (2 cases) | Unmapped; zero native queries. |
| Owner-accepted identities and exact IPv4 correspondence | All raw initial-SYN oracle cases through `_accept` | Acceptance selects only an original exact interface candidate and binds reviewer/rationale. |
| Capture/model/host/candidate/reviewer tampering | `test_review_cannot_transfer_to_changed_evidence_or_review_controls` (5 cases) | `ModelError`, no result. |
| Native evaluator resource exhaustion | `test_native_resource_failure_aborts_whole_comparison` | Mapping work fits budget 4; native preflight fails specifically on `state_edge_visits`; no partial result. |
| Duplicate declared IPv4 addresses | `test_duplicate_declared_addresses_are_rejected_before_mapping` | Validation rejects `DUPLICATE_ADDRESS`. |
| Multihomed source | `test_multihomed_source_is_not_evaluated_from_unobserved_interface` | Unsupported; zero native query. |
| Source/destination port confusion | `test_familiar_source_port_is_not_an_observed_destination_service` | Source port 502 is only a hint; undeclared destination 41000 is not evaluated as listener 502. |
| Conflicting SYN directions | `test_two_syn_directions_in_one_tuple_never_assert_a_single_initiator` | Both directions uncertain, zero native queries. |
| DHCP/address reuse and differing frame MACs | `test_address_reuse_and_transit_macs_remain_owner_uncertainties` | MAC multiplicity retained; default mappings pending; owner assertion and external uncertainty remain explicit after acceptance. |
| Stale observation digest, conflicting decisions, extra review fields, strict decision JSON, incomplete-interpretation absence suppression | `tests/test_capture_reconciliation.py::{test_changed_observation_contents_invalidate_review,test_invalid_owner_decisions_fail_closed,test_strict_bounded_decision_json,test_incomplete_interpretation_suppresses_absence_findings}` | Existing coverage inspected; final execution is recorded by V13-12, not counted as additional independent cases here. |

## Reproduction and raw result

PowerShell in repository root, Windows, Python 3.14.5; pytest 9.1.1,
Ruff 0.17.1, mypy 1.20.2:

```powershell
$env:PYTHONPATH = 'src'
$env:MYPYPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests/test_capture_independent_semantics.py -q --basetemp .pytest_tmp/independent-semantics-03 --tb=short
.\.venv\Scripts\python.exe -m mypy --strict tests/test_capture_independent_semantics.py
.\.venv\Scripts\python.exe -m ruff check tests/test_capture_independent_semantics.py
.\.venv\Scripts\python.exe -m ruff format --check tests/test_capture_independent_semantics.py
```

Observed outputs, all commands exit 0:

```text
...........................................                              [100%]
43 passed in 1.51s
Success: no issues found in 1 source file
All checks passed!
1 file already formatted
```

An initial run without `--basetemp` reported one pass and 38 setup errors because
the managed environment could not create numbered directories in its default
pytest temporary directory. No affected test body ran. Using a fresh workspace
temporary root resolved the environmental failure. Standalone mypy also needs
`MYPYPATH=src`; otherwise it resolves the installed untyped distribution instead
of source. Neither failure is evidence of a product defect. The final corpus
contains four additional cases beyond that initial 39-case draft.

The reviewed `capture/reconciliation.py` SHA-256 was
`dd8cdd35dfaae3eb1cf7958ab24988fa43c29f7ff08fe13476fa198f4b4de29a`;
`reachability.py` was
`79642298a099e852b99757c3b033d574f4678a944284b4db5d4ba925ab71e788`.
The final candidate manifest in V13-12/V13-13 identifies all later integrated
changes and tests against their exact final source.

## Residual assumptions and exclusions

- Owner decisions are integrity-bound to capture/model/observations/candidates,
  not digitally authenticated identities or proof of address ownership.
- The in-process dictionary APIs consume product-generated observation records;
  the CLI reanalyzes the original capture. A self-computed SHA-256 is not an
  authenticity guarantee for arbitrary caller-created dictionaries.
- DHCP epochs, NAT translations, VLAN address spaces and physical sensor
  coverage are not independently established. No missing traffic proves blocking.
- SYN evidence describes observed headers, not an established session,
  application identity, successful command, deployed policy or authorization.
- IPv6 analytical evaluation, reassembly, UDP initiation, source multihoming and
  self-asset native queries remain intentionally unevaluated.
- No remote writes, model mutation, policy changes or transport-edge creation
  were performed by this review. Hosted cross-platform acceptance is not inferred
  from this local run.
