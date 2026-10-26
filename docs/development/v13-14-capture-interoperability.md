# V13-14 — Independent capture interoperability

## A. Executive status

**PASS for the supported local subset on Windows/Python 3.14.5.** Independent
synthetic interoperability is demonstrated. Operational captures were not used;
broad real-world validation is not claimed. Python 3.12 and other operating
systems remain subject to V13-21 hosted acceptance.

## B. Changes and identity

Base commit: `dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98`. This gate adds
`tools/independent_capture_corpus.py`, `tests/test_capture_interoperability.py`,
and `tests/fixtures/capture-interoperability/` plus this report. No production
parser changes or runtime dependencies were required. Final source commit and
archive identities are recorded by V13-20 after integration.

The corpus combines a separately authored format writer and unmodified
Wireshark text2pcap 4.6.7 output. Both use original fictional bytes, independently
of the product's existing synthetic fixture generator. The installed tools were
evaluated first; no tool or capture download was needed. No live capture,
interface enumeration, driver access, or administrator action occurred.

The [corpus manifest](../../tests/fixtures/capture-interoperability/manifest.json)
contains every specimen's origin, generator version, size, exact SHA-256,
expected count or diagnostic and compatibility features. Manifest SHA-256:
`4d3918e7d5a09a6ec71d926a8cf8a8e2e89dae05c7da42912520a236599264d7`.
The [reference decoder receipt](../../tests/fixtures/capture-interoperability/reference-decoder.json)
has SHA-256 `00abf66670ba0f9abf9b53821f42247b30fe26b2e6d749ae406196b53335552e`.
The [corpus README](../../tests/fixtures/capture-interoperability/README.md)
documents origin, license, privacy, specifications and rebuilding.

## C. Independent evidence

| Specimens | Expected | Actual local result |
|---|---|---|
| `spec-{le,be}-{us,ns}.data` (4) | 2 packets each; four classic PCAP magic variants | PASS; exact timestamps and frame lengths match TShark ISO receipts |
| `spec-empty.data` | Valid empty classic capture | PASS; zero packets |
| `spec-unsupported-link.data` | Valid framing, linktype 147; unsupported decoding | PASS; statistics retained, no false host/transport conclusion |
| `spec-truncated.data` | Fatal truncated packet record | PASS; `CAPTURE_INVALID`, no output |
| `spec-sections.data` | 4 packets, 3 interfaces across 2 sections, one unknown block | PASS; 3 decoded, 1 unsupported; section-local interface references reset correctly |
| `spec-unsupported-section.data` | Unsupported major version rejected | PASS; `CAPTURE_INVALID`, no output |
| `spec-inconsistent-length.data` | Redundant lengths disagree | PASS; `CAPTURE_INVALID`, no output |
| `spec-invalid-interface.data` | Invalid interface reference rejected | PASS; `CAPTURE_INVALID`, no output |
| `spec-hostile-block.data` | Forged huge aligned block bounded before allocation | PASS; `LIMIT_EXCEEDED`, no output |
| `spec-hostile-record.data` | Forged huge captured record bounded before allocation | PASS; `LIMIT_EXCEEDED`, no output |
| `text2pcap-{pcap,nsecpcap,pcapng}.data` (3) | 12 packets each, independent container writer | PASS; packet count, interface references, timestamp precision and lengths match independent decoder |

The mixed-section PCAPNG fixture exercises both endiannesses, EPB, SPB, decimal
and binary resolution, signed timestamp offsets, unknown blocks/options, valid
alignment and mixed supported/unsupported encapsulation. SPB has no timestamp;
the product preserves `None` rather than inventing one. Invalid length,
interface, section-version and excessive-size cases distinguish complete fatal
rejection from successful limited decoding.

The 12 text2pcap frames cover Ethernet; IPv4/IPv6; TCP/UDP; ICMP/ICMPv6; ARP;
802.1Q VLAN; IPv4 fragmentation; truncated Ethernet; incomplete TCP metadata;
and a malformed TCP data offset. Eight packets decode, one is fragmented, two
are truncated and one malformed. Unsupported linktype specimens retain
explicit unsupported accounting. All filenames use unrelated extensions.

TShark 4.6.7 independently checks all valid containers' packet counts, interface
references, timestamps and lengths. Detailed differential checks compare only
fully decoded supported fields: IP/MAC addresses, IP protocol, TCP/UDP ports,
VLAN and ARP header fields. Wireshark may display partial transport ports on
fragmented or malformed packets; the product intentionally suppresses these.
No disagreement was used as an automatic reason to change the implementation.

One reference display discrepancy was investigated: `-T fields` represents
the negative timestamp `7/4 - 3` as `-2.750000000`, whereas `-T json` gives
`1969-12-31T23:59:58.750000000Z`. The latter and the specification's exact
arithmetic both equal `-5/4`. Tests use ISO timestamps for the container
differential; the product's rational timestamp is correct and unchanged.

Commands actually run:

```powershell
.venv\Scripts\python.exe -m tools.independent_capture_corpus --output tests/fixtures/capture-interoperability --wireshark-bin 'C:\Program Files\Wireshark'
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest tests/test_capture_interoperability.py tests/test_capture_parser.py tests/test_capture_independent_parser.py tests/test_capture_independent_resources.py -q --basetemp=.pytest_tmp/v13-14-source
.venv\Scripts\python.exe -m ruff check tools/independent_capture_corpus.py tests/test_capture_interoperability.py
.venv\Scripts\python.exe -m ruff format --check tools/independent_capture_corpus.py tests/test_capture_interoperability.py
$env:MYPYPATH='src'
.venv\Scripts\python.exe -m mypy tools/independent_capture_corpus.py tests/test_capture_interoperability.py
```

Actual result: **158 passed in 3.54 seconds**, including the 36 new corpus
tests. These counts overlap; they must not be added. Ruff and strict mypy pass.
Raw source-test receipt: `output/v13-14/pytest-source.txt` (ignored local evidence).

An initial command without `PYTHONPATH=src` resolved the existing `.venv` regular
installation rather than current source: 17 earlier security/resource
regressions failed against that stale install (141 passed). Its diagnostic
receipt is retained as `output/v13-14/pytest.txt`; it is not source acceptance
evidence. Source identity was corrected explicitly, giving the 158-pass result.
Fresh exact-version wheel/sdist installs remain mandatory in V13-20.

## D. Quality

Tests verify input SHA-256 before analysis, unchanged bytes afterwards,
deterministic repeated scans and analyses, fatal CLI failures without successful
stdout or published/staging output, and packet/file byte budget boundaries.
Socket construction and name resolution are denied during external-corpus
analysis. Existing independent allocation/read-budget tests run in the same
158-test subset. This demonstrates enforced bounded processing; the tiny corpus
is not an RSS or throughput benchmark. No payload or original capture is
introduced into generated reports. Test files carry no operational data.

## E. Risks and limitations

No production parser defect was discovered by this gate. The corpus is synthetic,
small, and intentionally bounded. It does not validate every producer, timestamp
precision extreme, arbitrary option, platform or real operational capture.
Unknown content remains unassessed. PCAPNG unsupported section features are
explicitly rejected; their rejection is not a supported-feature claim.
ARP's separate interpretation/host catalog correction belongs to V13-15.
Accessibility and installed archive acceptance belong to later gates.

## F. Next step

Integrate ARP semantics (V13-15), then rerun the committed corpus as part of
the exact versioned source and fresh installed distributions in V13-20.
V13-21 must exercise the same tests on all six required hosted configurations
after explicit owner authorization. No remote write was performed.
