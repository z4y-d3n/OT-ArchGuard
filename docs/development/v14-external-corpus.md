# V14-01 external protocol reference validation

Executed 2026-10-26 on Windows / TShark 4.6.7. Eight exact external files were
downloaded into Git-ignored `output/v14-external/`, initially quarantined,
hashed, reviewed and then added as **Tier 3 local-analysis references**. None of
their packet bytes is committed or included in either distribution archive.
These are public protocol-parser examples, not evidence of production-plant
validation. Original capture collectors and collection circumstances are not
independently established.

## Provenance, rights and exact bytes

The source repositories publish BSD-3-Clause root licenses and Battelle notices.
Those terms were read at the pinned revisions below. A repository-level license
does not independently establish the original collector's per-capture grant.
Accordingly every acquired entry has `redistribution: unknown`; redistribution
is **unapproved**, including the examples that name open62541 or Snap7. Approval
in `review_status: approved_external` means local analysis of the public test
reference, not permission to package the file. If a separate redistribution grant
is obtained, preserve the applicable license, Battelle notice and source credit.

| Source repository | Pinned revision | License / notice reviewed |
|---|---|---|
| [CISA ICSNPP ENIP](https://github.com/cisagov/icsnpp-enip/tree/3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e) | `3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e` | BSD-3-Clause; copyright 2023 Battelle Energy Alliance; root NOTICE.txt |
| [CISA ICSNPP S7comm](https://github.com/cisagov/icsnpp-s7comm/tree/102a35c8f967f20640bd2427bb28a7c609b37493) | `102a35c8f967f20640bd2427bb28a7c609b37493` | Same repository-level terms; collector-specific grant unresolved |
| [CISA ICSNPP OPC UA Binary](https://github.com/cisagov/icsnpp-opcua-binary/tree/d7fd8894d23baabcaf59989abc3cbab6b469c074) | `d7fd8894d23baabcaf59989abc3cbab6b469c074` | Same repository-level terms; collector-specific grant unresolved |
| [CISA ICSNPP DNP3](https://github.com/cisagov/icsnpp-dnp3/tree/b31dbadeceb1cbcda16aef89c650559cd177dd7e) | `b31dbadeceb1cbcda16aef89c650559cd177dd7e` | Same repository-level terms; collector-specific grant unresolved |

All source files are under the respective pinned `testing/traces/` directory.
The manifest stores their exact original HTTPS download locations. Sizes and
hashes below were calculated from actual downloaded capture bytes, not LFS
pointers or advertised sizes.

| Corpus ID / original filename | Actual bytes | Actual SHA-256 |
|---|---:|---|
| `cisa-enip-multiple` / `multiple_service_packet_cip.pcapng` | 344 | `4eed29d01d6fe3c827e3c947694526e7669d937ff8973d5c420979565597087c` |
| `cisa-enip-set-attribute` / `set_attribute_single_service_cip.pcapng` | 500 | `9b24d02e6f15a40f2109c2476bb117e2273bc9485077a50044269d3738cea8dc` |
| `cisa-snap7` / `snap7.pcap` | 8,260 | `2b91f6a8a203ec83e4f2dbb69d5e61602845f23da0baa31d95d029fb24cbd427` |
| `cisa-s7-plus-mixed` / `s7comm_plus.pcap` | 33,464 | `2f9befe0667443fb86b7184b6ff7fcc4eb61fae67d3ce30793ce7b2937067b0c` |
| `cisa-open62541` / `open62541_client-server_mainloop.pcap` | 22,412 | `07dd69db7de730928601e4f66d94382d94257a344ae3a5f9147b7dec108bcefd` |
| `cisa-open62541-nonstandard` / `open62541_client-server_mainloop-no-handshake-12345.pcap` | 17,159 | `da507c9d8798e978ef452efa761da3ab8a3b28c5ad9cb68c150edfb27c7619a9` |
| `cisa-dnp3` / `dnp3_example.pcap` | 115,403 | `d9b22ee7b5ece4a78d8f9995aff20d55bfb315752ce136f97c77eb5ce73511bf` |
| `cisa-opcua-gap` / `opcua_with-gap_with-handshake.pcap` | 83,524 | `030950345b2c79eaf3bedf8a04c2325cfe4a5d8b40225d250ed693daf350b6b6` |

The sensitivity review is limited to capture container/header structure,
protocol observations and whether the deliberately retained metadata is safe.
These files can contain application data, private network addresses, endpoint
strings and other unreviewed contents. They remain local. Header receipts retain
no process values, endpoint URLs, certificates, memory addresses or packet bytes.
Source filenames suggesting a client/server example are not proof of collection
authority or real plant provenance.

## Actual independent and product results

The independent executable identified itself as
`TShark (Wireshark) 4.6.7 (v4.6.7-0-gb439fb7b47a9).`
TCP, ENIP and DNP3 desegmentation were disabled. The receipt counts header-bearing
packets, not successful sessions or complete application operations.

| File / family | Capture packets | TShark packets with selected headers | Product result | Selected safe-field comparisons |
|---|---:|---:|---|---:|
| ENIP multiple service | 1 | 1 | 1 encapsulation positive; connected CIP stays opaque | 1 matched |
| ENIP set attribute | 1 | 1 | 1 encapsulation positive; connected CIP stays opaque | 1 matched |
| Snap7 classic | 64 | 64 | 11 positives; 33 unsupported functions; 20 unsupported userdata | 21 matched |
| S7comm-plus mixed | 262 | 34 classic headers | 262 `LINKTYPE_UNSUPPORTED` (Linux SLL) | None; explicit unsupported outcome |
| open62541 mainloop | 154 | 66 | 154 `LINKTYPE_UNSUPPORTED` (DLT_NULL) | None; explicit unsupported outcome |
| open62541 TCP/12345 | 113 | 54 with explicit TShark decode-as | 113 `LINKTYPE_UNSUPPORTED` (DLT_NULL) | None; wrong-port product behavior is covered synthetically, not demonstrated by this outer-unsupported capture |
| DNP3 example | 834 | 834 | 365 positives; 267 unsupported functions; 202 unsupported transport fragments | 1,460 matched |
| OPC UA gap/handshake | 411 | 240 | 237 positives; 171 hints; 3 truncated messages | 711 matched |

Across five captures with supported outer framing, **615 positive records and
2,194 selected field comparisons matched**, with zero observed mismatches.
This statement is confined to emitted supported fields. Unsupported cases are
not counted as interoperability passes. It does not prove complete protocol
coverage, command success, authentication or device identity.

Selected comparisons are ENIP command; S7 ROSCTR and supported function; OPC UA
type, chunk marker and declared size; DNP3 source/destination protocol addresses,
link function and emitted application function. Comparisons join the product's
original packet index to TShark `frame.number`. No byte normalization or capture
conversion was used. The DNP3 reference reported no incorrect header/data CRC
flags; the product independently requires both CRC coverages for each positive.

An additional independent corruption audit took the first original 18-byte DNP3
application view and flipped every bit individually: all 144 mutations abstained,
with no retained fields. Outcomes were 64 user-data CRC failures, 58 link-header
CRC failures, 16 start-byte hints, 5 truncated declared frames and 1 invalid link
length. The original unmodified view was positive. This is a finite external-byte
mutation observation, not a proof against every adversarial input.

Negative and unsupported expectations were retained:

- ENIP connected CPF payloads do not acquire the reference decoder's deeper CIP
  interpretations. TShark identifies services 0x0A/0x10; the product exports
  `cip_metadata: opaque` for this connected subset.
- Classic Snap7 programming and userdata remain unsupported. The mixed S7-plus
  file also contains classic messages; its filename is not an all-negative oracle.
  Its Linux SLL envelope currently prevents normal product application inspection.
- DNP3 SELECT/OPERATE application functions and fragmented transport remain
  unsupported. CRC-valid link bytes do not establish application operation success.
- OPC UA's three incomplete message starts remain `TRUNCATED`; eleven later
  continuation payloads have only type-mismatch hints, and 160 packets have no
  application bytes. No stream reconstruction or service-body interpretation was
  added to increase recognition counts.
- The NULL/SLL captures were preserved as actual unsupported outcomes. No implicit
  outer-linktype conversion was performed to disguise that limitation.

Machine-readable receipts are
`tests/fixtures/protocol-corpus/external-tshark-receipts.json` and
`external-product-receipts.json`. They bind exact source SHA-256/size, tool
version, bounded header examples, counts and product enrichment digests. The
product receipt also records the protocol source-file hashes exercised. Reference
examples are bounded to 16 positive and 8 other rows per capture. Complete
selected-field comparison was executed locally; ordinary offline tests validate
the receipts and joins, and do not claim to rerun the external captures.

To reproduce a TShark receipt, read its `arguments`, replace `INPUT` with the
verified local capture, append `-e FIELD` for each ordered item in `fields`, and
invoke the recorded TShark version. The nonstandard-port reference uses explicit
`-d tcp.port==12345,opcua`; that choice is not enabled in the product scanner.
Run `otarchguard capture enrich CAPTURE --output NEW_FILE.json` for the independent
product artifact, then compare the selected fields above by original packet index.

## Safe optional reacquisition

`tools.protocol_external` is development-only. It is never called by the runtime
or normal tests. It requires explicit network opt-in and an existing local output
directory. Eight reviewed fixed raw-GitHub HTTPS URLs, exact hashes and byte sizes
are hardcoded separately from the manifest. Changing a manifest cannot authorize
a different source or first-use digest. All redirects fail closed. Reads are
bounded to expected size plus one, with the existing 16 MiB ceiling, at most eight
distinct files per invocation and no archives. Publication uses Windows
no-replace rename or POSIX no-replace hardlinks after verification. A later failure
can leave earlier individually verified files; no successful complete-run result
is returned. Existing files are never overwritten.

Example, from this checkout, using a fresh Git-ignored directory:

```powershell
New-Item -ItemType Directory output/v14-reference-recheck
python -m tools.protocol_external --manifest tests/fixtures/protocol-corpus/manifest.json --id cisa-snap7 --id cisa-dnp3 --id cisa-opcua-gap --directory output/v14-reference-recheck --allow-network
python -m tools.protocol_corpus --manifest tests/fixtures/protocol-corpus/manifest.json --verify cisa-snap7 --file output/v14-reference-recheck/snap7.pcap
```

For sources without an established expected hash, use a separate local quarantine
review and record actual bytes, original source, rights and sensitivity before
editing the reviewed allowlist. This tool has no trust-on-first-download mode.

## Requested candidate sources and remaining gaps

| Candidate | Actual research outcome / blocker |
|---|---|
| [PCAP4SICS](https://www.netresec.com/?page=PCAP4SICS) | Source explicitly describes the 4SICS Geek Lounge industrial lab and asks for CS3Sthlm credit/link when sharing or using in training. Advertised captures are 25/134/200 MB. Even the smallest exceeds the 16 MiB development ceiling; no file downloaded or hash invented. This is lab traffic, not production-plant traffic. |
| [tjcruz-dei/ICS_PCAPS](https://github.com/tjcruz-dei/ICS_PCAPS/tree/84bc8896b79cb077d72863e140146dee7b4f53b5) | README at `84bc8896b79cb077d72863e140146dee7b4f53b5` attributes research captures to University of Coimbra / ATENA H2020, states CC BY 3.0 for repository content and requests the cited CRITIS 2018 publication. Release `MODBUSTCP#1` assets are ZIPs of 669,680,240 / 194,810,610 / 224,051,839 bytes. They exceed the ceiling and require archive handling; not downloaded. No underlying PCAP hash claimed. |
| [Wireshark SampleCaptures](https://wiki.wireshark.org/SampleCaptures) | IEC104 sample links remain available in the index, including `iec104.pcap` and `IEC104_SQ.pcapng`. Per-file collector/rights and approved immutable payload identity were not established; no bytes acquired. Other S7/DNP candidates remain candidates. |
| [Wireshark DCP](https://wiki.wireshark.org/PROFINET/DCP) | Index still links `ChangeIPUsingDCP.pcap`; no per-capture grant established. No bytes acquired or real DCP interoperability claimed. |
| [automayt/ICS-pcap](https://github.com/automayt/ICS-pcap/tree/13b7ae335529146b40535c2d7aa756886040d8ad) | Existing mixed-source repository review remains unresolved; no root grant established. The previously inspected Modbus object is an LFS pointer, not actual capture bytes. No automatic mirror/LFS payload acquisition. |
| [Official lib60870](https://github.com/mz-automation/lib60870/tree/7a388e3e133999e1ca77ba7521d55d074b7cd2bc) | Pinned tree `7a388e3e133999e1ca77ba7521d55d074b7cd2bc` has no `.pcap`, `.pcapng` or `.cap` test files. The CISA ICSNPP inventory has no IEC104 parser/capture submodule; a guessed `icsnpp-iec104` endpoint returned 404. No external IEC104 validation is claimed. |

External Modbus, DCP and IEC104 positive coverage remains a precise V14-02 corpus
gap. Their independent synthetic tests remain distinct from real external bytes.
Next acquisition should target small per-file-authorized captures in these three
families, followed by CRC/segmentation and privacy-preserving differential receipts.
