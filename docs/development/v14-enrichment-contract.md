# V14-00 protocol enrichment contract (development version 1)

This is the implemented development slice, not the final v1.4 release freeze.
Only Modbus TCP and PROFINET DCP have decoders here. The other five requested
families remain outstanding. Frozen observation version 2, capture version 1,
association version 1 and native comparison version 1 are unchanged. The new
artifact neither approves identities nor changes reachability or owner decisions.

## References and supported matrix

The wire references are the Modbus Organization's
[Messaging on TCP/IP Implementation Guide V1.0b](https://www.modbus.org/file/secure/messagingimplementationguide.pdf),
sections 3.1.2–3.1.3, and its
[Application Protocol Specification V1.1b3](https://www.modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf),
function layouts. PROFINET references are the independently maintained
[Wireshark FrameID definitions](https://www.wireshark.org/docs/wsar_html/packet-pn_8h_source.html),
[Wireshark DCP service constants and wire framing](https://raw.githubusercontent.com/wireshark/wireshark/master/plugins/epan/profinet/packet-pn-dcp.c),
and the pinned [Apache PLC4X wire schema](https://apache.googlesource.com/plc4x/+/60ef1313a6c06b09a8fabb932e3ed077e79ceacd/protocols/profinet/src/main/resources/protocols/profinet/profinet.mspec).
These are reference sources, not incorporated implementation code. The IEC
61158-6-10 specification itself was not acquired or redistributed during this slice.

| Dimension | Modbus TCP | PROFINET DCP |
|---|---|---|
| Identification | TCP source or destination port 502; explicit nonstandard-port API selection | Ethernet EtherType `0x8892`; supported DCP FrameID required for a positive result |
| Framing | Complete MBAP at payload offset zero, protocol identifier zero, length 2–254, complete ADU | FrameID `FEFD` for Get/Set, `FEFE` Identify request, `FEFF` Identify response; complete 12-byte header and declared data |
| Supported subset | Functions 1, 2, 3, 4, 5, 6, 8, 15, 16, 22, 23 and corresponding exception headers; mandatory PDU size/byte-count shape | Get service 3, Set service 4, Identify service 5; types request 0, response 1, unsupported-service response 5; Get selectors or aligned TLV boundaries |
| Safe header fields | `transaction_id`, `protocol_id`, `unit_id`, `function_code`, `exception_response`, `adu_length` | `frame_id`, `service_id`, `service_type`, `data_length`, `blocks` |
| Categories | `read_type`, `write_type`, `diagnostic_type`, `read_write_type`, `exception_response` | `get`, `set`, `identify` |
| Abstentions | Incomplete/segmented record, unsupported function, invalid MBAP/PDU shape, resource ceiling, nonmatching protocol identifier | Unrelated PROFINET FrameID, Hello, unknown service/type, incompatible FrameID/service/type, invalid TLV or reserved field, truncation, unsupported trailing bytes |
| Privacy | No register/coil values, addresses, setpoints or arbitrary data objects exported | No device names, DCP IP parameters, names or configuration values exported |

Validation is scoped to these headers and mandatory layout shapes. Payload values,
full application semantics, cryptographic authenticity, correct device behavior and
command execution are unassessed. A Modbus function can occur in a request or a
response; port direction does not settle this. The product therefore labels
write-type metadata without calling it an executed write or an established request.
An unrelated or unidentified PROFINET FrameID never produces a DCP record.
It is accounted for by `NON_DCP_PROFINET_FRAME_ID` or
`PROFINET_FRAME_ID_MISSING` in `skipped_packets`. Known DCP Hello FrameID `FEFC`
produces an explicit unsupported-family-variant result, without header fields.

## API and packet framing

`capture.protocols.decode(ProtocolView(...), limits)` returns immutable typed
records from one validated payload view. Views and byte slices are transient.
`inspect_modbus=True` explicitly selects Modbus on a nonstandard TCP port through
this Python API; capture scanning does not search arbitrary ports automatically.
`enrich_capture(path, *, limits=..., capture_limits=...)` independently uses the
existing bounded `scan_capture` callback and returns a metadata dictionary.

Ethernet with up to two VLAN tags, raw IP, unfragmented IPv4 TCP and direct IPv6
TCP are supported by this bridge. Existing private `_decode` and `_reference`
helpers gate outer IP/TCP validity and construct original packet references;
their frozen source is unchanged. IPv6 extension chains are unassessed by this
new bridge even where the v1.3 observation decoder supports them. Link-error,
offloaded and snapshot-truncated records cannot yield application metadata.

TCP payloads must start at an ADU boundary; no session tracking, deduplication,
stream reassembly, recovery of missing segments or speculative offset search
exists. Multiple complete in-packet Modbus ADUs are processed in order. Invalid
framing stops the packet. The record ceiling produces an explicit terminal
`UNSUPPORTED_VARIANT` record and can replace the last retained positive record
when more input remains. DCP allows Ethernet minimum-frame padding outside its
declared data length, but no additional coalesced DCP record interpretation.

## Status and method semantics

| Status | Meaning |
|---|---|
| `PORT_HINT` | Port association only; empty payload or MBAP identifier mismatch does not identify Modbus |
| `ETHERTYPE_HINT` | Defined taxonomy value; not emitted by this slice because EtherType alone must not label a packet DCP |
| `STRUCTURALLY_VALID` | The documented complete header and mandatory framing subset passed; never authenticity or operational authorization |
| `TRUNCATED` | Candidate bytes needed for framing are missing; TCP segmentation and malformed incomplete traffic cannot be distinguished here |
| `MALFORMED` | Candidate framing has a demonstrable supported-layout contradiction; never an application-success conclusion |
| `UNSUPPORTED_VARIANT` | A candidate family/function/layout or bounded iteration/byte ceiling is outside the implemented subset |

`recognition_method` is `HEADER_STRUCTURE` only for positive results. Other
methods are `PORT_ASSOCIATION`, `ETHERTYPE` or `EXPLICIT_PROTOCOL_SELECTION`.
No probabilities or generic confirmed-protocol label are generated. Each record
has a bounded reason and explicit limitations. Nonpositive records contain no
decoded header fields or operation category. Encrypted/opaque protocol families
are outside this two-decoder slice, so no such positive decoder is claimed.

## Artifact and identity

The `protocol-enrichment.json` root has exactly these fields:

- `enrichment_version: 1`, `decoder_version: 1`.
- `capture_sha256`, original frozen `capture` metadata.
- `observations_sha256: null`: this independent scan binds the capture, without
  claiming that an observation artifact was validated or owner-approved.
- `supported_protocols: ["modbus_tcp", "profinet_dcp"]`.
- `records`, `counts`, `packets_with_records`, `skipped_packets`.
- `limits`, `limitations`, `enrichment_sha256`.

Records are ordered by `(packet.index, record_offset)` strictly ascending.
`record_offset` is relative to the TCP application or Ethernet protocol data view,
not the beginning of the capture file. Each record contains `protocol`,
`recognition_method`, `status`, nullable `message_category`, allowlisted `fields`,
`record_offset`, nullable `reason`, `limitations`, `packet`, nullable source and
destination IP/port fields, and `vlans`. The root capture SHA binds every packet
reference; packet records retain index, capture record/block offset, section,
interface, captured/original length and exact original timestamp or null.
Capture timestamps are neither rounded to floating point nor fabricated.

`counts` maps `protocol:STATUS` to retained record counts. It counts records,
not independent sessions or unique network assets. `packets_with_records` plus
all `skipped_packets` counts equals the original packet count. Unsupported outer
packets have explicit skip reasons; they are not silently counted as parsed
application traffic. Duplicated frames remain duplicated observations.

JSON uses sorted keys, ASCII escaping, two-space indentation and one final LF.
The digest is SHA-256 over compact sorted-key ASCII JSON, separators `,`/`:`,
excluding only `enrichment_sha256`. No filename, absolute path, import time,
wall-clock generation time, payload or local execution duration enters identity.
The same capture bytes and same limits produce the same artifact and digest.

`validate_enrichment` checks version, canonical digest, safe fields, categories,
count denominators, ordering, packet bounds, interface joins and exact timestamp
resolution/offset joins. Capture hashes are integrity references; validation does
not reopen the capture or authenticate the source or assertions' truth.

## Bounds and compatibility policy

Defaults and immutable version-1 ceilings are 16,384 bytes per application view,
8 retained results per packet, 64 DCP selectors/blocks, 20,000 retained records,
and 16 MiB serialized output. Callers can lower these ceilings. The existing
capture limits additionally bound container bytes, interfaces, packets and frame
buffers. Aggregate/output exhaustion fails without returning a valid partial
artifact. The output check includes pretty serialization and final LF.

This new metadata-only contract rejects unknown versions, statuses and structural
fields, including privacy-expanding record/header fields. Future extensions need
an explicitly reviewed decoder/contract revision or an explicit compatible-field
allowlist change and independent rejection tests. Unknown fields do not acquire
positive meanings. This policy does not change the existing frozen v1.3 consumer's
unknown-optional-field behavior. Do not migrate owner decisions onto enriched
application meanings automatically.

## Validation evidence and remaining gaps

`tests/test_protocol_enrichment.py` independently authors positive and negative
wire bytes, complete and split/coalesced ADUs, bad lengths/functions/services,
false port/EtherType associations, VLAN/raw-IP/IPv6 cases, limits, privacy,
rehashed artifact tampering, random bytes and byte mutations. An independently
authored four-packet fixture in `tests/fixtures/protocol-corpus/` has a separate
TShark 4.6.7 receipt; integration compares selected safe fields and requires
unrelated PROFINET traffic to be skipped without a DCP record. Independent audit tests additionally
challenge service IDs, malformed response shape and recomputed-hash tampering.

The corpus manifest separately records public-source licensing/provenance
research. The committed fixture and its TShark receipt are synthetic evidence,
not real-world industrial interoperability validation. External industrial
captures, a broader DCP service matrix, the remaining five protocols, hostile
real-world segmentation, hosted CI and final release freeze remain outstanding.
