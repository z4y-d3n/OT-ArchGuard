# V14-01 IEC-104, OPC UA and DNP3 supported envelopes

These decoders add bounded header evidence, independent from native observations,
reachability, approved associations and operation execution. Standard TCP ports
2404, 4840 and 20000 select candidates. No stream reconstruction, arbitrary byte
search, IP fragment reconstruction or UDP interpretation is added. Complete
in-packet messages are processed in wire order within existing byte/record limits.

## IEC 60870-5-104

The [Wireshark IEC-104 dissector constants and envelope layouts](https://raw.githubusercontent.com/wireshark/wireshark/master/epan/dissectors/packet-iec104.c)
were independently consulted. Supported APCI start is `68`, declared length4..253.
I frames require even send/receive control encodings and a complete six-byte ASDU
header. S frames require the exact supported reserved/control bits and length4.
U frames require length4, zero remaining controls and exactly one supported
STARTDT, STOPDT or TESTFR act/con control code.

I-frame ASDU types1,3,9,11,13,30,31,45,46,100,101,102,103 have explicit object-width
checks, a nonzero object count and exact sequential/nonsequential envelope lengths.
Sequence addressing is supported for the listed monitoring types only. Reserved
causes outside1..13/20..47 and other types/layouts remain unsupported. Metadata is
only frame format, APDU wire length, optional ASDU type or U-control name. Object
addresses, timestamps, quality, measurements and command values are never exported.
Cause/type combinations, object contents and direction/session semantics are not
evaluated. A complete I frame does not establish an executed command.

## OPC UA Binary over UA TCP

Primary wire references are OPC Foundation Part6
[connection message headers](https://reference.opcfoundation.org/specs/OPC-10000-6/7.1.2.2),
[HEL](https://reference.opcfoundation.org/specs/OPC-10000-6/7.1.2.3),
[ACK](https://reference.opcfoundation.org/specs/OPC-10000-6/7.1.2.4),
[ERR](https://reference.opcfoundation.org/specs/OPC-10000-6/7.1.2.5),
[RHE](https://reference.opcfoundation.org/specs/OPC-10000-6/7.1.2.6),
[secure message headers](https://reference.opcfoundation.org/specs/OPC-10000-6/6.7.2.2)
and [security headers](https://reference.opcfoundation.org/specs/OPC-10000-6/6.7.2.3).

HEL/ACK/ERR/RHE require final markerF and complete fixed/length-prefixed fields;
HEL/ACK support transport version0. MSG accepts F/C; OPN/CLO require F. AbortA
is explicitly unsupported. All require exact declared outer size and a bounded
complete chunk. MSG/CLO require channel/token/sequence envelope and at least one
opaque body byte. OPN additionally checks three asymmetric length envelopes,
including policy URI maximum255 and thumbprint length-1/0/20. No string is decoded
or retained. Metadata is message type, marker, size and handshake/error/opaque
secure-channel category. Certificates, URLs, service data and secrets remain opaque.
Encryption, authenticity, negotiated buffers, security policy and readable service
semantics are unassessed. A continuation chunk never proves a complete operation.

## DNP3 over TCP

The [Wireshark DNP dissector constants](https://raw.githubusercontent.com/wireshark/wireshark/master/epan/dissectors/packet-dnp.c)
were consulted independently. Supported link frames require start0564, length>=5,
complete fixed header and mandatory CRC-16/DNP for the first eight header bytes
and every data block (maximum16 bytes each). The reflected polynomial isA6BC,
initial0, final complement; the independent test oracle uses nonreflected3D65
and the fixed check vector `123456789` -> `EA82`.

Primary link functions0,1,2,3,4,9 and secondary0,1,11,14,15 have control/FCV,
reserved-bit and user-data-length consistency checks. Link metadata includes
CRC status, primary flag, function, wire length and source/destination explicitly
named protocol addresses. They never establish approved assets.

Data-bearing frames require a complete single transport and single application
fragment. Transport sequence continuity across frames is unassessed. Application
header functions0(confirm),1(read),13/14(restart-type),129/130(response) are the
small supported subset. Read requests support complete class object headers
(group60, variation1..4, qualifier06) only. Restart/confirm requests require their
exact supported no-object shape. Response headers require both indication bytes;
their remaining objects are opaque and their validity is explicitly unassessed.
Function/direction and unsolicited-header consistency are checked. SELECT/OPERATE,
write, Secure Authentication and all other functions remain unsupported. A valid
CRC is integrity evidence, never origin authenticity or successful operation.

## Independent synthetic verification

`tests/test_protocol_iec_opc_dnp.py` contains original fixture builders, fixed
oracles, every-prefix split cases, coalescing, incorrect ports, deterministic
mutations, record/view budgets and serialization privacy checks. No fixture is
constructed by a product parser. External capture results and TShark receipts are
tracked separately in the corpus acceptance record; these synthetic tests do not
establish production-plant interoperability.
