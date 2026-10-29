# V14-05 parser and capture trust-transition review

Executed 29 October 2026 on Windows 11 / Python 3.14.5 against the regular
installed V14-04 package at `d898516e24dec922179696e4cb50a262b3466a46`.
The new `tests/test_v145_interoperability.py` contains **30 unique cases**:
30 PASS, no failures/errors/skips, 0.82 seconds. No production correction was
necessary for these counterexamples. This result concerns the documented bounded
subsets; it is not a complete protocol implementation or deployment assessment.

| Area | Independent expectation | Actual result | Remaining limitation |
|---|---|---|---|
| Modbus TCP | FC6 keeps write-type framing, excludes register address/value; impossible MBAP length stops later records | PASS; sensitive substitutions retain identical public records and changed capture/enrichment identities | No command completion, request direction or transaction correlation |
| PROFINET DCP | FEFD/Set excludes configuration bytes; Get selectors count independently | PASS; two selectors accepted at ceiling 2 and abstain at ceiling 1 | DCP service envelope only; EtherType alone does not identify DCP |
| EtherNet/IP | RegisterSession excludes session/context; unknown encapsulation command stops scanning | PASS; changed private bytes do not change retained fields; unsupported middle record has no fields | No session legitimacy or deeper CIP interpretation in this example |
| Classic S7comm | WriteVar excludes PDU reference, S7ANY identifiers and value; nonzero TPKT reserved byte is malformed | PASS; exact public records unchanged by private substitutions; later records are not recovered | Classic supported S7ANY subset only; S7comm Plus and segmentation remain unsupported |
| IEC-104 | Type1 I-format excludes information-object address/value; S-format length contradiction is malformed | PASS; private substitutions retain identical fields; no later resynchronization | Cause/type semantics and process state are unassessed |
| OPC UA Binary | HEL endpoint string is discarded; size below eight-byte fixed header is malformed | PASS; hostile endpoint-like bytes are absent from output and later messages are not recovered | Secure services and arbitrary nonstandard ports remain unassessed |
| DNP3/TCP | Response body is opaque; mandatory link CRC mismatch is malformed | PASS; CRC-correct changed opaque body retains public fields, corrupt middle frame stops scanning | Response objects and authentication remain unassessed; CRC is not authentication |
| Shared packet bounds | Two complete records fit ceiling 2; a third replaces the final retained record with explicit unsupported accounting | PASS for all six TCP families, exact offsets retained | Terminal unsupported record deliberately replaces a positive; it is not silent complete decoding |
| Shared byte bounds | Exact application view accepted, one extra byte abstains; exact outer packet size accepted, one less rejects | PASS for all seven views and DCP outer envelope | Work ceilings do not promise memory or latency bounds |
| Container/provenance | Seven-family capture preserves packet order, record offsets, exact rational timestamps and totals under four classic PCAP formats | PASS for little/big endian and micro/nanosecond precision; seven records fit global ceiling 7, ceiling 6 rejects | These cases do not add container/linktype support |
| Unsupported linktypes | Recognizable inner Modbus bytes cannot override DLT_NULL or Linux SLL | PASS; zero protocol records, exact `LINKTYPE_UNSUPPORTED` skip denominator | NULL/SLL remain unsupported; original framing is preserved |
| Misleading ports | Source 502/destination4840 selects documented Modbus precedence, without payload-driven fallback to UA | PASS; only port-hint evidence; arbitrary port12345 gives no record | Explicit `inspect_modbus=True` remains the sole nonstandard-port selection exception |
| Failed publication | A valid first protocol packet followed by truncated/contradictory PCAP record cannot publish an enrichment file | PASS; CLI exit2, diagnostic only, no successful output file | Local single-writer publication model remains authoritative |

Fixtures are original fictional literals and minimal PCAP/IP/TCP envelopes in
the test module. No third-party capture bytes are embedded, acquired or
redistributed. Field expectations come from the existing
[enrichment contract](v14-enrichment-contract.md),
[ENIP/S7 subset](v14-enip-s7.md), and
[IEC/OPC/DNP subset](v14-iec-opc-dnp.md). The independent normal-polynomial DNP
CRC oracle is anchored to `123456789 -> EA82`; it imports no decoder helper.
Privacy substitution is an explicit metamorphic oracle: excluded-value changes
must preserve retained fields while changing exact source identity. It does not
claim independent decoding of every exported field; the separately committed
V14-05 corpus/oracle evidence covers that distinct responsibility.

The four generated seven-family PCAPs are each 657 bytes:

| Byte order / precision | SHA-256 |
|---|---|
| Little / microsecond | `c0e0cc06fe83ddbb00319e471143af7b8ac0a4296e1f0caab2ea90864b056e98` |
| Little / nanosecond | `e2f678ef351160158d80ccaba252fbf7bbbe0778986cfa33558396aaee6a12c7` |
| Big / microsecond | `6b6a07eb97fbd349e019a92399c5782505361e76bb2d118510d33e2da3ff719c` |
| Big / nanosecond | `cfcb5848ab92f4f085d510f52af84bf730fb1f5eef71427c7828c0e8a534ba5d` |

Local receipts are `output/v145-interoperability.xml` and
`output/v145-interoperability.json`; the latter records fixture hashes and exact
test-file identity. Ordinary CI recreates the bytes in temporary directories and
requires neither TShark nor external connectivity. Repeated runs do not add
unique cases. Reproduce the focused cases with:

```powershell
python -m pytest tests/test_v145_interoperability.py -q --basetemp=output/v145-interop-recheck --junitxml=output/v145-interop-recheck.xml
python -m ruff check tests/test_v145_interoperability.py
python -m ruff format --check tests/test_v145_interoperability.py
$env:MYPYPATH = 'src'
python -m mypy tests/test_v145_interoperability.py
```

Focused Ruff lint/format and strict mypy pass. Mypy requires the source root
because the regular installed package has no `py.typed` marker; the production
code itself is unchanged. Full source, installed distributions, frozen native
compatibility and new hosted CI are integration-owner gates, not results inferred
from these 30 cases. External Modbus/DCP/IEC104 positive gaps, NULL/SLL support,
stream reassembly, and production-deployment validation remain separate limits.
