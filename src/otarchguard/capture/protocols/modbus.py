"""Modbus TCP MBAP plus bounded, allowlisted PDU shape checks.

Wire reference: Modbus Messaging on TCP/IP Implementation Guide V1.0b,
sections 3.1.2/3.1.3; Application Protocol V1.1b3, function layouts.
No process values are exposed. Request/response direction remains unassessed.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    ProtocolView,
    Status,
    record,
)

_PROTOCOL = "modbus_tcp"
_FUNCTIONS = {1, 2, 3, 4, 5, 6, 8, 15, 16, 22, 23}
_LIMITATIONS = (
    "Header and PDU shape only; application values are neither interpreted nor retained.",
    "Request/response direction is unassessed; write-type metadata never proves execution.",
    "No stream reassembly, speculative offset matching or transaction correlation.",
)


def _shape(pdu: bytes, function: int) -> bool:
    # Check mandatory sizes/byte-count framing without retaining data fields.
    if function & 0x80:
        return len(pdu) == 2
    if function in {1, 2, 3, 4}:
        return len(pdu) == 5 or (
            len(pdu) >= 3 and pdu[1] == len(pdu) - 2 and (function in {1, 2} or pdu[1] % 2 == 0)
        )
    if function in {5, 6, 8}:
        return len(pdu) == 5
    if function in {15, 16}:
        return len(pdu) == 5 or (len(pdu) >= 7 and pdu[5] == len(pdu) - 6)
    if function == 22:
        return len(pdu) == 7
    if function == 23:
        return (len(pdu) >= 11 and pdu[9] == len(pdu) - 10) or (
            len(pdu) >= 4 and pdu[1] == len(pdu) - 2 and pdu[1] % 2 == 0
        )
    return False


def decode_modbus(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or not (
        502 in {view.source_port, view.destination_port} or view.inspect_modbus
    ):
        return ()
    method = "PORT_ASSOCIATION" if not view.inspect_modbus else "EXPLICIT_PROTOCOL_SELECTION"

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            _PROTOCOL, method, status, offset=offset, reason=reason, limitations=_LIMITATIONS
        )

    data = view.data
    if len(data) > limits.view_bytes:
        return (stopped(Status.UNSUPPORTED_VARIANT, "VIEW_BYTE_LIMIT"),)
    if not data:
        return (stopped(Status.PORT_HINT, "NO_APPLICATION_BYTES"),)
    result: list[EnrichmentRecord] = []
    offset = 0
    while offset < len(data):
        if len(result) == limits.records_per_packet:
            result[-1] = stopped(
                Status.UNSUPPORTED_VARIANT, "RECORD_ITERATION_LIMIT", result[-1].record_offset
            )
            break
        remaining = len(data) - offset
        if remaining < 7:
            result.append(stopped(Status.TRUNCATED, "MBAP_HEADER_INCOMPLETE_OR_SEGMENTED", offset))
            break
        protocol_id = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if protocol_id != 0:
            result.append(stopped(Status.PORT_HINT, "MBAP_PROTOCOL_NOT_RECOGNIZED", offset))
            break
        length = int.from_bytes(data[offset + 4 : offset + 6], "big")
        if not 2 <= length <= 254:
            result.append(stopped(Status.MALFORMED, "MBAP_LENGTH_INVALID", offset))
            break
        end = offset + 6 + length
        if end > len(data):
            result.append(stopped(Status.TRUNCATED, "ADU_INCOMPLETE_OR_SEGMENTED", offset))
            break
        function = data[offset + 7]
        base = function & 0x7F
        if base not in _FUNCTIONS:
            result.append(stopped(Status.UNSUPPORTED_VARIANT, "FUNCTION_NOT_SUPPORTED", offset))
            break
        if not _shape(data[offset + 7 : end], function):
            result.append(stopped(Status.MALFORMED, "PDU_SHAPE_INVALID", offset))
            break
        category = (
            "exception_response"
            if function & 0x80
            else (
                "read_type"
                if base in {1, 2, 3, 4}
                else "diagnostic_type"
                if base == 8
                else "read_write_type"
                if base == 23
                else "write_type"
            )
        )
        result.append(
            record(
                _PROTOCOL,
                "HEADER_STRUCTURE",
                Status.STRUCTURALLY_VALID,
                offset=offset,
                category=category,
                fields=(
                    ("transaction_id", int.from_bytes(data[offset : offset + 2], "big")),
                    ("protocol_id", 0),
                    ("unit_id", data[offset + 6]),
                    ("function_code", function),
                    ("exception_response", bool(function & 0x80)),
                    ("adu_length", 6 + length),
                ),
                limitations=_LIMITATIONS,
            )
        )
        offset = end
    return tuple(result)
