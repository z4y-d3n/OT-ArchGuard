# V13-08 — independent parser and security audit

Date: 2026-10-25. Reviewed starting revision:
`4fb9b4863ee59684211e7a3315221ff89102bebb`, on
`codex/v13-01-capture-foundation`. This new record does not revise V13-00–07.
Reviewer A independently inspected `capture/parser.py`, the packet decoder and
aggregation in `capture/observations.py`, the local-path helpers, and the capture
CLI. The integration owner made production corrections; Reviewer A wrote a
separate byte corpus and reran it against the corrected checkout source.

## Finding register

| ID / severity | Affected location at original revision | Reproduction / actual behavior | Expected / impact / disposition |
| --- | --- | --- | --- |
| A-01 / High, analytical integrity | `capture/observations.py::_ipv4`, option loop before `_transport` | A raw IPv4 SYN with options `00 01 00 00`, `07 02 00 00`, `44 02 00 00`, or `88 02 00 00` retained `status=decoded`, destination port 502 and initiation evidence. Two independently built captures with accepted exact endpoint mappings each invoked one native query. | EOL padding and mandatory known-option fields must be checked before retaining transport evidence. Malformed packets must remain malformed, with no ports/SYN and no native result. **Corrected:** zero-padding check; RR, Timestamp and StreamID field/size checks; unimplemented IPv4 options conservative `unsupported`. |
| A-02 / Medium, observation integrity | `capture/observations.py::_ipv6`, extension-header loop | Hop-by-Hop or Destination Options headers with a PadN length of 255 inside an eight-byte header, a missing option-length byte, or nonzero PadN contents retained ports and SYN. Unknown extension options and an unknown Routing Type with Segments Left=1 were also skipped as decoded. | Traverse option TLVs within their header; validate Pad1/PadN; do not interpret unsupported option/routing semantics as valid transport evidence. **Corrected:** bounded TLV validation and explicit unsupported unimplemented options/routing headers. IPv6 native evaluation was already unsupported, limiting the native analytical impact. |

These are reproducible correctness defects. No code execution, filesystem escape,
or unbounded-allocation vulnerability was demonstrated. High severity for A-01
reflects violation of the explicit malformed-evidence/native-query boundary; a
model-reachable result still did not claim deployed authorization.

## Independent corpus and before/after evidence

`tests/test_capture_independent_parser.py` constructs PCAP, PCAPNG, IP and TCP
bytes directly; it imports no production capture fixture generator. Its oracles
are fixed expected structures, rational timestamps and documented protocol fields.

| Corpus | Before correction | Corrected checkout |
| --- | --- | --- |
| First 13 cases: malformed IPv4/IPv6 options, valid IPv6 padding, mixed-endian PCAPNG timestamp oracle | 10 failed, 3 passed | Included in 23 passing independent cases |
| Extended 23 cases: additional valid IPv4 controls, unknown-option conservatism, Routing Header conservatism, malformed-SYN comparison boundary | 16 failed, 7 passed | Included in 221 passing integrated cases below |
| Existing parser and observations tests | 134 passed in 3.71 s | Included in 221 passing integrated cases |

Before-correction commands used the baseline regular installation in `.venv`:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_capture_independent_parser.py -q --basetemp=.pytest_tmp/parser-independent-initial --tb=short
.venv\Scripts\python.exe -m pytest tests/test_capture_independent_parser.py -q --basetemp=.pytest_tmp/parser-independent-extended --tb=short
.venv\Scripts\python.exe -m pytest tests/test_capture_parser.py tests/test_capture_observations.py -q --basetemp=.pytest_tmp/parser-historical-audit --tb=short
```

The first independent invocation without `--basetemp` encountered 13 sandbox-temp
setup errors. Moving pytest's temporary root into the workspace resolved that
environmental error. It was not counted as a product defect or a passing run.
The existing `.venv` is a regular installation, so it does not automatically pick
up edits under `src`. An interim run against that installation still reproduced
the old defects; it is not evidence against the corrected source.

Corrected-source verification explicitly selected and printed the checkout origin:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -c "import otarchguard.capture.observations as o; print(o.__file__)"
.venv\Scripts\python.exe -m pytest tests/test_capture_independent_parser.py tests/test_capture_parser.py tests/test_capture_observations.py tests/test_capture_reconciliation.py -q --basetemp=.pytest_tmp/parser-integrated-source --tb=short
```

Observed origin:
`C:\Users\PC\Desktop\OT-ArchGuard-CLEAN\src\otarchguard\capture\observations.py`.
Result: **221 passed in 4.20 s, exit 0**, no skips. This includes the new cases;
the rows above must not be added as independent test totals. The new test file
passed Ruff lint and formatting. Final frozen-source regression and installed
distribution receipts are recorded separately in V13-12.

## Confirmed strengths

- Container reads are incremental with independent file, record, packet and block
  ceilings. Forged aligned block lengths and captured lengths are rejected before
  allocating the claimed large buffer.
- Classic PCAP byte order and micro/nanosecond magic variants are explicit.
  PCAPNG changes byte order per section, resets interface IDs per section, checks
  repeated block lengths and section boundaries, and rejects missing references.
- An independent mixed-endian corpus verifies decimal/binary resolution and
  signed offsets using expected `-5/4` and `4007/1000` timestamps. SPB records do
  not acquire invented timestamps.
- The PCAPNG zero-padding rule is supported by the referenced draft; removing it
  would have weakened validation. Missing end-of-options markers at an exact block
  boundary are accepted as the draft directs.
- TCP option TLV bounds, known option lengths, EOL padding and reserved-bit
  handling were inspected and existing regression cases passed. The initial-SYN
  predicate rejects SYN-ACK, SYN-FIN and SYN-RST as initiation evidence.
- Fragmented, truncated, unknown-linktype, reported link-error and segmentation
  offload cases clear ports and initiation evidence. Payloads, names, comments,
  secrets and unsupported custom-block contents are not exported.
- Regular-file checks, descriptor identity comparison, post-read mutation checks,
  and ancestor symlink/junction rejection mitigate ordinary input replacement.

## Specifications, choices and limitations

References checked during this audit:

- [PCAPNG draft-ietf-opsawg-pcapng-06](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcapng-06.html),
  sections 3.5, 3.6.2, 4.2–4.4. This is a work-in-progress format specification;
  it requires zero alignment padding and documents reader acceptance of a missing
  option terminator at the block boundary.
- [RFC 791](https://www.rfc-editor.org/rfc/rfc791.html), section 3.1, defines IPv4
  header padding and the mandatory fields of the tested options.
- [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html), sections 4.2 and 4.4,
  defines option TLVs, PadN contents and unknown-routing-type behavior. Conservatively
  classifying unimplemented routing headers is this product's subset policy; the
  RFC does not require every routing header to be malformed.

No independent general packet-decoder implementation, real industrial capture
corpus, unrestricted fuzz campaign, or comprehensive protocol conformance claim
is made. Checksums are intentionally not validated because of capture offload;
`decoded` remains metadata interpretation, never proof that a receiving stack
accepted the packet. Input provenance hashes identify bytes, not authenticity.
All TCP/IP option semantics are not implemented; unsupported options remain
explicit rather than silently authoritative. ARP metadata is observational and
does not establish host ownership.

The path model assumes a trusted local single-writer directory. Symlink/junction
checks and file identities are not OS-level isolation against an attacker who
can concurrently replace path ancestors or restore metadata. Mapped remote
drives and arbitrary reparse-provider behavior have not been proven offline.
No Windows-junction race or hostile filesystem proof was executed. Output
publication review, accessibility and package/CI evidence belong to V13-10–13.

## Gate assessment

The two confirmed parser/decoder findings are corrected and independently covered.
No unresolved critical/high finding remains in this review's inspected scope.
This local audit is supporting evidence, not a comprehensive security certification
or cross-platform release acceptance. The final candidate identity and complete
regression/packaging conclusions must be taken from V13-12 and V13-13.
