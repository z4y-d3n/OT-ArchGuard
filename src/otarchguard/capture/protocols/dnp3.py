"""CRC-checked DNP3 link framing and a small complete application-header subset.

Wire references: Wireshark packet-dnp.c and CRC-16/DNP (reflected 0xA6BC,
initial zero, final complement). No points, object values or authentication data.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    HeaderValue,
    ProtocolView,
    Status,
    record,
)

_PRIMARY = {0, 1, 2, 3, 4, 9}
_SECONDARY = {0, 1, 11, 14, 15}
_APPLICATION = {
    0: "confirm",
    1: "read_type",
    13: "cold_restart_type",
    14: "warm_restart_type",
    129: "response",
    130: "unsolicited_response",
}
_LIMITATIONS = (
    "CRC-validated supported link framing; protocol addresses are not approved assets.",
    "Only complete single-transport/single-application fragments are supported.",
    "Application-header categories do not prove object validity, authorization or execution.",
    "No process points, control values, configuration, files or authentication payloads.",
    "No stream reassembly, transport-sequence correlation or authenticity assessment.",
)


def _crc(data: bytes) -> int:
    value = 0
    for octet in data:
        value ^= octet
        for _ in range(8):
            value = (value >> 1) ^ (0xA6BC if value & 1 else 0)
    return value ^ 0xFFFF


def _application(
    user: bytes, direction: bool
) -> tuple[Status | None, str, tuple[tuple[str, HeaderValue], ...]]:
    if user[0] & 0xC0 != 0xC0:
        return Status.UNSUPPORTED_VARIANT, "TRANSPORT_FRAGMENTATION_NOT_SUPPORTED", ()
    app = user[1:]
    if len(app) < 2:
        return Status.MALFORMED, "APPLICATION_HEADER_INCOMPLETE", ()
    control, function = app[:2]
    if control & 0xC0 != 0xC0:
        return Status.UNSUPPORTED_VARIANT, "APPLICATION_FRAGMENTATION_NOT_SUPPORTED", ()
    if function not in _APPLICATION:
        return Status.UNSUPPORTED_VARIANT, "APPLICATION_FUNCTION_NOT_SUPPORTED", ()
    if function in {129, 130}:
        if direction or len(app) < 4 or bool(control & 0x10) != (function == 130):
            return Status.MALFORMED, "APPLICATION_RESPONSE_HEADER_INVALID", ()
    elif function == 0:
        if len(app) != 2 or control & 0x20:
            return Status.MALFORMED, "APPLICATION_CONFIRM_HEADER_INVALID", ()
    elif not direction or control & 0x30:
        return Status.MALFORMED, "APPLICATION_REQUEST_HEADER_INVALID", ()
    elif function in {13, 14}:
        if len(app) != 2:
            return Status.UNSUPPORTED_VARIANT, "RESTART_OBJECTS_NOT_SUPPORTED", ()
    else:
        # Supported class reads have complete three-byte object headers only:
        # group 60, variations 1..4, qualifier all-objects (0x06).
        objects = app[2:]
        if not objects or len(objects) % 3:
            return Status.MALFORMED, "READ_OBJECT_HEADER_INVALID", ()
        if any(
            objects[i] != 60 or objects[i + 1] not in {1, 2, 3, 4} or objects[i + 2] != 6
            for i in range(0, len(objects), 3)
        ):
            return Status.UNSUPPORTED_VARIANT, "READ_OBJECT_LAYOUT_NOT_SUPPORTED", ()
    return (
        None,
        "",
        (("application_function", function), ("application_category", _APPLICATION[function])),
    )


def decode_dnp3(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or 20000 not in {view.source_port, view.destination_port}:
        return ()

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            "dnp3",
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
        if len(rest) < 2:
            status, reason = Status.TRUNCATED, "LINK_HEADER_INCOMPLETE_OR_SEGMENTED"
        elif rest[:2] != b"\x05\x64":
            status, reason = Status.PORT_HINT, "LINK_START_NOT_RECOGNIZED"
        elif len(rest) < 10:
            status, reason = Status.TRUNCATED, "LINK_HEADER_INCOMPLETE_OR_SEGMENTED"
        elif rest[2] < 5:
            status, reason = Status.MALFORMED, "LINK_LENGTH_INVALID"
        else:
            length = rest[2] - 5
            size = 10 + length + 2 * ((length + 15) // 16)
            if len(rest) < size:
                status, reason = Status.TRUNCATED, "LINK_FRAME_INCOMPLETE_OR_SEGMENTED"
            elif _crc(rest[:8]) != int.from_bytes(rest[8:10], "little"):
                status, reason = Status.MALFORMED, "LINK_HEADER_CRC_INVALID"
            else:
                control = rest[3]
                primary, function = bool(control & 0x40), control & 15
                if function not in (_PRIMARY if primary else _SECONDARY):
                    status, reason = Status.UNSUPPORTED_VARIANT, "LINK_FUNCTION_NOT_SUPPORTED"
                elif (
                    (not primary and control & 0x20)
                    or (primary and bool(control & 0x10) != (function in {2, 3}))
                    or (primary and function not in {2, 3} and control & 0x20)
                ):
                    status, reason = Status.MALFORMED, "LINK_CONTROL_INVALID"
                elif bool(length) != (primary and function in {3, 4}):
                    status, reason = Status.MALFORMED, "LINK_FUNCTION_LENGTH_INVALID"
                else:
                    user = bytearray()
                    position = 10
                    remaining = length
                    valid_crc = True
                    while remaining:
                        block_size = min(remaining, 16)
                        block = rest[position : position + block_size]
                        if _crc(block) != int.from_bytes(
                            rest[position + block_size : position + block_size + 2], "little"
                        ):
                            valid_crc = False
                            break
                        user.extend(block)
                        position += block_size + 2
                        remaining -= block_size
                    if not valid_crc:
                        status, reason = Status.MALFORMED, "USER_DATA_CRC_INVALID"
                    else:
                        fields: tuple[tuple[str, HeaderValue], ...] = (
                            ("link_status", "crc_valid"),
                            ("protocol_source", int.from_bytes(rest[6:8], "little")),
                            ("protocol_destination", int.from_bytes(rest[4:6], "little")),
                            ("link_function", function),
                            ("link_primary", primary),
                            ("frame_length", size),
                        )
                        status, reason = None, ""
                        if length:
                            status, reason, app_fields = _application(
                                bytes(user), bool(control & 128)
                            )
                            fields += app_fields
                        if status is None:
                            results.append(
                                record(
                                    "dnp3",
                                    "HEADER_STRUCTURE",
                                    Status.STRUCTURALLY_VALID,
                                    offset=offset,
                                    category="user_data" if length else "link_management",
                                    fields=fields,
                                    limitations=_LIMITATIONS,
                                )
                            )
                            offset += size
                            continue
        assert status is not None
        results.append(stopped(status, reason, offset))
        break
    return tuple(results)
