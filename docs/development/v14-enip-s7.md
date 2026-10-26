# V14-01 EtherNet/IP and classic S7comm subsets

These passive decoders consume complete TCP application views at offset zero on
ports 44818 and 102 respectively. Port direction does not establish a legitimate
client/server relationship. Multiple complete in-packet messages retain their
original relative offsets; split messages abstain. The common view-byte and
record ceilings apply. CPF item iteration additionally uses the existing
`dcp_blocks` ceiling, without extending the frozen limits interface.

## EtherNet/IP and CIP

The decoder checks the 24-byte little-endian encapsulation header, known command,
zero options, complete declared body and the supported command-specific envelope.
NOP and UnregisterSession have empty supported bodies. RegisterSession supports
protocol version 1 and zero option flags. ListServices, ListIdentity and
ListInterfaces support empty request bodies; response CPF items require exact
boundaries. ListServices supports version-1, 20-byte service items. ListIdentity
requires version 1, IPv4 socket family 2, zero socket padding, its minimum
envelope and exact product-name length but discards all
identity, socket, serial and product-name bytes. ListInterfaces supports an empty
item list only. Nonzero encapsulation status with an empty body is a header-only
error observation, never an application result.

SendRRData supports interface handle zero, bounded CPF, a null address item and
an unconnected data item. CIP interpretation supports generic services
GetAttributesAll (1), SetAttributesAll (2), Reset (5), GetAttributeSingle (14) and
SetAttributeSingle (16). Request paths support complete logical 8/16-bit class,
instance and attribute segment envelopes; identifiers are discarded. Response
headers require their reserved byte and additional-status word boundaries.
Service payload values remain unassessed. A response service bit does not establish
success or operation execution.

Positive encapsulation records explicitly label `cip_metadata` as `not_present`,
`recognized`, `unsupported` or `opaque`. CIP service/response/operation fields
exist only for `recognized`. An unknown complete service/path retains outer
encapsulation recognition without claiming that its CIP message is valid.
Contradictory CPF/CIP bounds are malformed. Unsupported commands/interfaces are
explicit abstentions. SendUnitData validates connected-address/data CPF and the
sequence envelope; its application contents remain opaque without session context.
UDP implicit I/O, vendor tag services, recursive/multiple-service payloads, secure
encapsulation and nonstandard ports are outside the subset.

Allowlisted fields are `encapsulation_command`, `encapsulation_status`,
`encapsulation_length`, `cip_metadata`, and optional `cip_service`, `cip_response`,
`cip_operation`. Sender context and session identifiers are not exported.

## Classic S7comm

The decoder checks TPKT version 3, zero reserved byte, complete length, class-0
COTP data header `02 f0 80`, classic protocol identifier `32`, known ROSCTR,
zero reserved bytes and exact parameter/data joins. COTP connection traffic,
segmentation/nonzero sequence, unknown ROSCTR and S7comm-plus abstain.

The supported functions are SetupCommunication (`f0`, exact eight-byte parameter
envelope), ReadVar (`04`) and WriteVar (`05`). Jobs require complete counted S7ANY
parameter items. Read jobs have no data. Write jobs and read replies validate
counted data-item transport/length envelopes and inter-item alignment without
retaining values. Write replies require one status byte per item, without
interpreting acceptance. Plain ACK and empty-body error ACK_DATA retain header
metadata only. Programming functions, Userdata, other variable syntaxes and error
bodies are explicit unsupported cases.

Allowlisted fields are `protocol_id`, `rosctr`, `pdu_category`, `parameter_length`,
`data_length`, `tpkt_length` and optional `function_code`. Memory areas, addresses,
PDU references, values, error details and program contents are not exported.

## Independent specification and verification

Wire references were read without incorporating implementation code:

- [RFC1006 section 6](https://www.rfc-editor.org/rfc/rfc1006.html#section-6).
- [Wireshark v4.6.7 EtherNet/IP reference](https://github.com/wireshark/wireshark/blob/v4.6.7/epan/dissectors/packet-enip.c).
- [Wireshark v4.6.7 classic S7comm reference](https://github.com/wireshark/wireshark/blob/v4.6.7/epan/dissectors/packet-s7comm.c).

`tests/test_protocol_enip_s7.py` authors original byte builders independently of
product code, including requests/replies, malformed nested bounds, unsupported
variants, coalescing, splitting, wrong ports, privacy, deterministic limits and
fixed-seed byte mutation. External capture verification and its precise provenance
are recorded separately; synthetic results are not production-plant evidence.
