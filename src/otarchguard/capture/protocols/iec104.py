"""Bounded IEC-104 APCI and selected ASDU envelope shapes; no process values.

Framing reference: Wireshark packet-iec104.c (APCI constants and ASDU types).
No stream reconstruction or operation-success interpretation is performed.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    HeaderValue,
    ProtocolView,
    Status,
    record,
)

_U_FUNCTIONS = {
    0x07: "startdt_act",
    0x0B: "startdt_con",
    0x13: "stopdt_act",
    0x23: "stopdt_con",
    0x43: "testfr_act",
    0x83: "testfr_con",
}
# Object body widths, excluding the three-byte information-object address.
# Values, addresses, quality and timestamps are only skipped, never exported.
_ASDU_WIDTHS = {
    1: 1,
    3: 1,
    9: 3,
    11: 3,
    13: 5,
    30: 8,
    31: 8,
    45: 1,
    46: 1,
    100: 1,
    101: 1,
    102: 0,
    103: 7,
}
_LIMITATIONS = (
    "APCI and selected ASDU envelope shapes only; no process values or object addresses.",
    "No stream reassembly or session validation; command execution remains unassessed.",
    "Direction is unassessed; message classes do not establish authorization or success.",
)


def decode_iec104(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or 2404 not in {view.source_port, view.destination_port}:
        return ()

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            "iec104",
            "PORT_ASSOCIATION",
            status,
            offset=offset,
            reason=reason,
            limitations=_LIMITATIONS,
        )

    data = view.data
    if len(data) > limits.view_bytes:
        return (stopped(Status.UNSUPPORTED_VARIANT, "VIEW_BYTE_LIMIT"),)
    if not data:
        return (stopped(Status.PORT_HINT, "NO_APPLICATION_BYTES"),)
    results: list[EnrichmentRecord] = []
    offset = 0
    while offset < len(data):
        if len(results) == limits.records_per_packet:
            results[-1] = stopped(
                Status.UNSUPPORTED_VARIANT, "RECORD_ITERATION_LIMIT", results[-1].record_offset
            )
            break
        rest = data[offset:]
        status: Status | None = None
        reason = ""
        fields: tuple[tuple[str, HeaderValue], ...] = ()
        category = ""
        if rest[0] != 0x68:
            status, reason = Status.PORT_HINT, "APCI_START_NOT_RECOGNIZED"
        elif len(rest) < 2:
            status, reason = Status.TRUNCATED, "APCI_HEADER_INCOMPLETE_OR_SEGMENTED"
        elif not 4 <= rest[1] <= 253:
            status, reason = Status.MALFORMED, "APDU_LENGTH_INVALID"
        elif len(rest) < rest[1] + 2:
            status, reason = Status.TRUNCATED, "APDU_INCOMPLETE_OR_SEGMENTED"
        else:
            end = rest[1] + 2
            control = rest[2:6]
            first = control[0]
            if first & 1 == 0:
                if control[2] & 1:
                    status, reason = Status.MALFORMED, "I_CONTROL_RESERVED_BIT"
                elif end < 12:
                    status, reason = Status.MALFORMED, "ASDU_HEADER_INCOMPLETE"
                else:
                    asdu = rest[6:end]
                    kind, count = asdu[0], asdu[1] & 0x7F
                    if kind not in _ASDU_WIDTHS:
                        status, reason = Status.UNSUPPORTED_VARIANT, "ASDU_LAYOUT_NOT_SUPPORTED"
                    elif asdu[2] & 0x3F not in {*range(1, 14), *range(20, 48)}:
                        status, reason = Status.UNSUPPORTED_VARIANT, "ASDU_CAUSE_NOT_SUPPORTED"
                    elif count == 0:
                        status, reason = Status.MALFORMED, "ASDU_OBJECT_COUNT_ZERO"
                    else:
                        width = _ASDU_WIDTHS[kind]
                        expected = 6 + (
                            3 + count * width if asdu[1] & 0x80 else count * (3 + width)
                        )
                        if len(asdu) != expected:
                            status, reason = Status.MALFORMED, "ASDU_OBJECT_ENVELOPE_INVALID"
                        elif kind >= 45 and asdu[1] & 0x80:
                            status, reason = (
                                Status.UNSUPPORTED_VARIANT,
                                "ASDU_SEQUENCE_NOT_SUPPORTED",
                            )
                        else:
                            fields = (
                                ("frame_format", "I"),
                                ("apdu_length", end),
                                ("asdu_type", kind),
                            )
                            category = "information_transfer"
            elif first & 3 == 1:
                if end != 6 or control[:2] != b"\x01\x00" or control[2] & 1:
                    status, reason = Status.MALFORMED, "S_CONTROL_OR_LENGTH_INVALID"
                else:
                    fields = (("frame_format", "S"), ("apdu_length", end))
                    category = "supervisory"
            elif end != 6 or control[1:] != b"\x00\x00\x00":
                status, reason = Status.MALFORMED, "U_CONTROL_OR_LENGTH_INVALID"
            elif first not in _U_FUNCTIONS:
                status, reason = Status.UNSUPPORTED_VARIANT, "U_FUNCTION_NOT_SUPPORTED"
            else:
                fields = (
                    ("frame_format", "U"),
                    ("apdu_length", end),
                    ("u_function", _U_FUNCTIONS[first]),
                )
                category = "unnumbered_control"
        if status is not None:
            results.append(stopped(status, reason, offset))
            break
        results.append(
            record(
                "iec104",
                "HEADER_STRUCTURE",
                Status.STRUCTURALLY_VALID,
                offset=offset,
                category=category,
                fields=fields,
                limitations=_LIMITATIONS,
            )
        )
        offset += rest[1] + 2
    return tuple(results)
