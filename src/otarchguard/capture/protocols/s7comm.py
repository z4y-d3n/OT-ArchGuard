"""Classic S7comm over complete RFC1006 TPKT and class-0 COTP data TPDUs.

Supported functions: setup communication and S7ANY read/write variable envelopes.
Wire references: RFC1006 section 6 and Wireshark v4.6.7 packet-s7comm.c.
No memory addresses, process values, program data or error payloads are exported.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    HeaderValue,
    ProtocolView,
    Status,
    record,
)

PDU_CATEGORIES = {1: "job", 2: "ack", 3: "ack_data", 7: "userdata"}
FUNCTION_CATEGORIES = {4: "read_type", 5: "write_type", 0xF0: "setup_communication"}
_LIMITATIONS = (
    "Classic S7comm header and supported parameter/data envelopes only; values are not retained.",
    "ROSCTR/function metadata proves neither authorization nor operation acceptance or execution.",
    "No S7comm-plus, COTP/TCP reassembly, memory addresses, programs or credentials.",
)


def _data_items(data: bytes, count: int) -> bool:
    position = 0
    for index in range(count):
        if position + 4 > len(data):
            return False
        transport = data[position + 1]
        if transport not in {0, 3, 4, 5, 7, 9}:
            return False
        length = int.from_bytes(data[position + 2 : position + 4], "big")
        size = (length + 7) // 8 if transport in {3, 4, 5} else length
        if transport == 0 and size:
            return False
        position += 4 + size
        if index + 1 < count and size % 2:
            if position >= len(data) or data[position] != 0:
                return False
            position += 1
        if position > len(data):
            return False
    return position == len(data)


def _parameters(rosctr: int, parameter: bytes, data: bytes) -> tuple[Status | None, str]:
    if not parameter or parameter[0] not in FUNCTION_CATEGORIES:
        return Status.UNSUPPORTED_VARIANT, "S7_FUNCTION_UNSUPPORTED"
    function = parameter[0]
    if function == 0xF0:
        if len(parameter) != 8 or parameter[1] != 0 or data:
            return Status.MALFORMED, "S7_SETUP_ENVELOPE_INVALID"
        return None, ""
    if len(parameter) < 2 or not parameter[1]:
        return Status.MALFORMED, "S7_VARIABLE_ITEM_COUNT_INVALID"
    count = parameter[1]
    if rosctr == 1:
        if len(parameter) != 2 + 12 * count:
            return Status.MALFORMED, "S7_VARIABLE_PARAMETER_LENGTH_INVALID"
        for offset in range(2, len(parameter), 12):
            if parameter[offset : offset + 3] != b"\x12\x0a\x10":
                return Status.UNSUPPORTED_VARIANT, "S7_VARIABLE_SYNTAX_UNSUPPORTED"
        valid_data = not data if function == 4 else _data_items(data, count)
    else:
        if len(parameter) != 2:
            return Status.MALFORMED, "S7_RESPONSE_PARAMETER_LENGTH_INVALID"
        valid_data = _data_items(data, count) if function == 4 else len(data) == count
    return (None, "") if valid_data else (Status.MALFORMED, "S7_VARIABLE_DATA_ENVELOPE_INVALID")


def decode_s7comm(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or 102 not in {view.source_port, view.destination_port}:
        return ()

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            "s7comm",
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
    result: list[EnrichmentRecord] = []
    offset = 0
    while offset < len(data):
        if len(result) == limits.records_per_packet:
            result[-1] = stopped(
                Status.UNSUPPORTED_VARIANT, "RECORD_ITERATION_LIMIT", result[-1].record_offset
            )
            break
        if data[offset] != 3:
            result.append(stopped(Status.PORT_HINT, "TPKT_VERSION_NOT_RECOGNIZED", offset))
            break
        if len(data) - offset < 4:
            result.append(stopped(Status.TRUNCATED, "TPKT_HEADER_INCOMPLETE_OR_SEGMENTED", offset))
            break
        length = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if data[offset + 1] != 0 or length < 7:
            result.append(stopped(Status.MALFORMED, "TPKT_HEADER_INVALID", offset))
            break
        end = offset + length
        if end > len(data):
            result.append(stopped(Status.TRUNCATED, "TPKT_INCOMPLETE_OR_SEGMENTED", offset))
            break
        cotp = data[offset + 4 : end]
        if cotp[0] + 1 > len(cotp) or cotp[0] < 2:
            result.append(stopped(Status.MALFORMED, "COTP_HEADER_LENGTH_INVALID", offset))
            break
        if cotp[1] != 0xF0:
            result.append(stopped(Status.UNSUPPORTED_VARIANT, "COTP_NON_DATA_TPDU", offset))
            break
        if cotp[0] != 2:
            result.append(
                stopped(Status.UNSUPPORTED_VARIANT, "COTP_DATA_HEADER_UNSUPPORTED", offset)
            )
            break
        if cotp[2] != 0x80:
            result.append(
                stopped(
                    Status.UNSUPPORTED_VARIANT, "COTP_SEGMENTATION_OR_SEQUENCE_UNSUPPORTED", offset
                )
            )
            break
        pdu = cotp[3:]
        if not pdu:
            result.append(stopped(Status.MALFORMED, "S7_HEADER_MISSING", offset))
            break
        if pdu[0] != 0x32:
            result.append(
                stopped(Status.UNSUPPORTED_VARIANT, "S7COMM_PLUS_OR_OTHER_APPLICATION", offset)
            )
            break
        if len(pdu) < 10:
            result.append(stopped(Status.MALFORMED, "S7_HEADER_INCOMPLETE_INSIDE_TPKT", offset))
            break
        rosctr = pdu[1]
        if rosctr not in PDU_CATEGORIES:
            result.append(stopped(Status.UNSUPPORTED_VARIANT, "S7_ROSCTR_UNSUPPORTED", offset))
            break
        header = 12 if rosctr in {2, 3} else 10
        parameter_length = int.from_bytes(pdu[6:8], "big")
        data_length = int.from_bytes(pdu[8:10], "big")
        if pdu[2:4] != b"\x00\x00" or header + parameter_length + data_length != len(pdu):
            result.append(stopped(Status.MALFORMED, "S7_HEADER_LENGTH_OR_RESERVED_INVALID", offset))
            break
        fields: tuple[tuple[str, HeaderValue], ...] = (
            ("protocol_id", 0x32),
            ("rosctr", rosctr),
            ("pdu_category", PDU_CATEGORIES[rosctr]),
            ("parameter_length", parameter_length),
            ("data_length", data_length),
            ("tpkt_length", length),
        )
        category = "pdu_header"
        if rosctr == 7:
            result.append(stopped(Status.UNSUPPORTED_VARIANT, "S7_USERDATA_UNSUPPORTED", offset))
            break
        if rosctr == 2 or (rosctr == 3 and pdu[10:12] != b"\x00\x00"):
            if parameter_length or data_length:
                result.append(
                    stopped(Status.UNSUPPORTED_VARIANT, "S7_ERROR_OR_ACK_BODY_UNSUPPORTED", offset)
                )
                break
        else:
            parameter = pdu[header : header + parameter_length]
            failure, reason = _parameters(rosctr, parameter, pdu[header + parameter_length :])
            if failure is not None:
                result.append(stopped(failure, reason, offset))
                break
            function = parameter[0]
            fields += (("function_code", function),)
            category = FUNCTION_CATEGORIES[function]
        result.append(
            record(
                "s7comm",
                "HEADER_STRUCTURE",
                Status.STRUCTURALLY_VALID,
                offset=offset,
                category=category,
                fields=fields,
                limitations=_LIMITATIONS,
            )
        )
        offset = end
    return tuple(result)
