# V13-15 — ARP semantic acceptance

## A. Executive status

**PASS for analyzer, aggregation and association semantics; integrated visual
acceptance pending.** Explorer rendering must be assessed using the integrated
V13-16/V13-17 acceptance evidence. This gate corrects
a demonstrated defect rather than adding industrial protocol inspection.

The baseline was `dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98`. Integration commit
and exact final installed-source identities are recorded in V13-20. The local
source test receipt is `output/v13-15-arp/receipt.json` (ignored acceptance output).

## B. Changes and compatibility

Changed production files: `src/otarchguard/capture/observations.py` and
`src/otarchguard/capture/reconciliation.py`. Added
`tests/test_capture_arp_semantics.py`; adapted the hand-authored observation
version in `tests/test_capture_reconciliation.py`. Native YAML schema 1 is unchanged.

Previously the ARP SPA/TPA fields populated `source_ip`/`destination_ip`; ordinary
endpoint aggregation then added both addresses to `hosts`. For a broadcast
request this attached `ff:ff:ff:ff:ff:ff` to the target IP's destination MAC set,
and made a target-only address eligible for a model-association proposal. ARP
opcode and hardware claims were not retained, so distinct messages could merge.

Now `flow.arp` preserves versioned sender/target protocol and hardware fields,
opcode, operation, Ethernet source/destination, and delivery type independently.
`source_ip` and `destination_ip` retain their historical ARP SPA/TPA meanings for
traceability; consumers must read the explicit ARP object to interpret them.
Non-ARP flows carry `arp: null`. Full ARP metadata participates in flow and
conversation identity, preserving differing hardware claims and delivery.

ARP targets do not populate the host catalog. A supported request/reply sender
may populate an unresolved address observation with `arp_request_sender` or
`arp_reply_sender` provenance, excluding the unspecified `0.0.0.0` probe sender.
Other packet endpoints retain `packet_source` and `packet_destination` roles.
Host `source_macs`/`destination_macs` remain Ethernet frame observations, not
ownership assertions; claimed ARP hardware addresses live in the ARP object.
An address later seen transmitting is cataloged from that separate evidence.

The host semantics and ARP identities changed, so `observation_version` is **2**.
The protocol hint `catalog_version` remains **1**. The association document shape
remains version **1**: its existing capture, model, observation and candidate
digests bind every review. Version-1 observations are explicitly rejected for new
association/comparison with a regenerate diagnostic. Regenerate observations and
owner review from the original capture; an old target-only host cannot safely be
migrated using only its old aggregate. Existing evidence may be retained read-only.
This is an explicit development-contract revision before the v1.3 freeze, not a
silent reinterpretation. Full freeze policy is documented in V13-18.

## C. Independent evidence

Fixtures are hand-authored directly from the field positions in
[RFC 826](https://www.rfc-editor.org/rfc/rfc826) and the unspecified-sender probe
definition in [RFC 5227](https://www.rfc-editor.org/rfc/rfc5227). Tests do not import
the product capture writer to generate their ARP bytes.

Reference Ethernet frame (42 bytes):

```text
ffffffffffff0200000000100806
0001080006040001
020000000010c000020a
000000000000c0000214
```

The four lines are Ethernet destination/source/type; ARP hardware/protocol
types, lengths and opcode; SHA/SPA; THA/TPA. Frame SHA-256:
`22ae5ebac15903fb34a0606c8c003d7e009f1755770d261af4565ae2767d2596`.
Single-record acceptance PCAP SHA-256:
`4a7a7214b2736fa5f93c8640fac704cb9bff022e31d3e6b7c0a34e38bdf055fb`.

| Evidence | Before | Accepted behavior |
|---|---|---|
| SPA `192.0.2.10` | Generic source address | Explicit sender claim; unresolved catalog address |
| TPA `192.0.2.20` | Generic destination and catalog host | Referenced target only; no host or mapping proposal |
| Ethernet destination | Target's destination MAC | Explicit broadcast delivery in `flow.arp` |
| SHA/THA and opcode | Lost on aggregation | Preserved; distinct claims remain distinct groups |
| `0.0.0.0` probe SPA | Catalog address | Retained message field, excluded from host catalog |
| Reconciliation | Unsupported protocol | Remains unsupported; no native reachability query |

Command (PowerShell sets `$env:PYTHONPATH = 'src'` first):

```text
.venv/Scripts/python.exe -m pytest tests/test_capture_arp_semantics.py tests/test_capture_observations.py tests/test_capture_reconciliation.py tests/test_capture_independent_semantics.py -q --basetemp=.pytest_tmp/arp-v13-15-receipt
```

Actual result on Windows/Python 3.14.5: **212 passed in 4.27s**, including **62 ARP
cases**. These suites overlap the full final regression and must not be added to
its count. Raw console receipt: `output/v13-15-arp/pytest.txt`. Raw reference PCAP,
exported observations and module/test hashes are beside `receipt.json`.

Coverage includes ordinary request/reply; broadcast, unicast and multicast wire
delivery; gratuitous ARP; zero-SPA probes; every truncated frame prefix; unsupported
hardware/protocol/address sizes; unknown opcodes; target-only and subsequently
transmitting addresses; differing SHA/THA and Ethernet addresses; conflicting
claims for one IP; deterministic repeats; unchanged input bytes; absence of an
ARP-derived reachability query; and explicit legacy-version rejection.

Ruff passed and strict mypy passed the four owned Python files. Integrated lint,
formatting, tests and installed distributions are rechecked in V13-20.

## D. Quality

ARP interpretation is restricted to Ethernet/IPv4 with hardware/protocol lengths
6/4 and request/reply opcodes 1/2. Other opcodes preserve available header fields
but are unsupported and cannot supply catalog identities. Unsupported formats
and incomplete headers do not supply ARP address identity evidence. Capture error,
offload and truncation status still suppress supported ARP host evidence.

No networking, payload export, reassembly or runtime dependencies were added.
Existing flow/host/allocation budgets apply before retention; fixed per-flow
accounting covers the bounded ARP header fields. Deterministic JSON hashing
continues to bind the complete observation. The fictional acceptance evidence
contains only documentation-range addresses and locally generated bytes.

## E. Risks

No packet proves an authentic host, IP ownership, a response or reachability.
Spoofing, NAT, DHCP, address reuse and sensor visibility remain unresolved.
Different hardware claims are retained, not resolved into physical devices.
No DHCP-state or conflict-detection conclusions are introduced. Browser evidence
and hosted platform results must be taken from their own gates.

## F. Next step

Integrate the specialized ARP labels/layout and version-2 consumer contract, then
verify the exact versioned installed candidate. No remote write is needed for
this gate; hosted acceptance retains the explicit owner authorization boundary.
