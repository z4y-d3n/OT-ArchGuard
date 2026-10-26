"""EtherNet/IP encapsulation and a deliberately small explicit-CIP envelope.

Reference: Wireshark v4.6.7 packet-enip.c / packet-cip.c wire definitions.
No upstream code is incorporated. CIP values and EPATH identifiers are discarded.
TCP only: UDP implicit I/O is never interpreted as an explicit CIP request.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    HeaderValue,
    ProtocolView,
    Status,
    record,
)

COMMAND_CATEGORIES = {
    0x00: "nop",
    0x04: "list_services",
    0x63: "list_identity",
    0x64: "list_interfaces",
    0x65: "register_session",
    0x66: "unregister_session",
    0x6F: "explicit_unconnected",
    0x70: "explicit_connected",
}
CIP_OPERATIONS = {
    1: "read_type",
    2: "write_type",
    5: "reset_type",
    14: "read_type",
    16: "write_type",
}
_LIMITATIONS = (
    "Encapsulation and supported CPF/CIP envelope only; application values are not interpreted.",
    "CIP metadata is separate from encapsulation recognition; opaque content remains unassessed.",
    "Service/response headers prove neither authorization nor successful operation execution.",
    "TCP only; no implicit UDP I/O, reassembly, session tracking or device identity inference.",
)


def _u16(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def _cip(data: bytes) -> tuple[Status | None, str, tuple[tuple[str, HeaderValue], ...]]:
    if len(data) < 2:
        return Status.MALFORMED, "CIP_HEADER_INCOMPLETE", ()
    service = data[0]
    response = bool(service & 0x80)
    if response:
        if len(data) < 4 or data[1] != 0 or 4 + data[3] * 2 > len(data):
            return Status.MALFORMED, "CIP_RESPONSE_ENVELOPE_INVALID", ()
    else:
        end = 2 + data[1] * 2
        if not data[1] or end > len(data):
            return Status.MALFORMED, "CIP_REQUEST_PATH_LENGTH_INVALID", ()
        position = 2
        # Only logical 8/16-bit class, instance and attribute segments. Unknown
        # path variants retain encapsulation recognition, never CIP metadata.
        while position < end:
            segment = data[position]
            if segment in {0x20, 0x24, 0x30}:
                position += 2
            elif segment in {0x21, 0x25, 0x31}:
                if position + 4 > end or data[position + 1] != 0:
                    return Status.MALFORMED, "CIP_LOGICAL_PATH_INVALID", ()
                position += 4
            else:
                return None, "unsupported", ()
        if position != end:
            return Status.MALFORMED, "CIP_LOGICAL_PATH_INVALID", ()
    base = service & 0x7F
    if base not in CIP_OPERATIONS:
        return None, "unsupported", ()
    return (
        None,
        "recognized",
        (
            ("cip_service", service),
            ("cip_response", response),
            ("cip_operation", CIP_OPERATIONS[base]),
        ),
    )


def _cpf(data: bytes, maximum: int) -> tuple[str | None, list[tuple[int, bytes]]]:
    if len(data) < 2:
        return "CPF_COUNT_MISSING", []
    count = _u16(data)
    if count > maximum:
        return "CPF_ITEM_ITERATION_LIMIT", []
    position = 2
    items: list[tuple[int, bytes]] = []
    for _ in range(count):
        if position + 4 > len(data):
            return "CPF_ITEM_HEADER_INCOMPLETE", []
        kind, size = _u16(data, position), _u16(data, position + 2)
        position += 4
        end = position + size
        if end > len(data):
            return "CPF_ITEM_LENGTH_INVALID", []
        items.append((kind, data[position:end]))
        position = end
    if position != len(data):
        return "CPF_TRAILING_BYTES", []
    return None, items


def _body(
    command: int, body: bytes, limits: EnrichmentLimits
) -> tuple[Status | None, str, tuple[tuple[str, HeaderValue], ...]]:
    if command in {0, 0x66}:
        return (
            (None, "not_present", ())
            if not body
            else (Status.MALFORMED, "COMMAND_LENGTH_INVALID", ())
        )
    if command == 0x65:
        if len(body) != 4:
            return Status.MALFORMED, "REGISTER_SESSION_LENGTH_INVALID", ()
        if body != b"\x01\x00\x00\x00":
            return Status.UNSUPPORTED_VARIANT, "REGISTER_SESSION_VERSION_OR_OPTIONS_UNSUPPORTED", ()
        return None, "not_present", ()
    if command in {4, 0x63, 0x64} and not body:
        return None, "not_present", ()
    cpf = body
    if command in {0x6F, 0x70}:
        if len(body) < 8:
            return Status.MALFORMED, "SEND_DATA_ENVELOPE_INCOMPLETE", ()
        if body[:4] != b"\x00" * 4:
            return Status.UNSUPPORTED_VARIANT, "INTERFACE_HANDLE_UNSUPPORTED", ()
        cpf = body[6:]
    reason, items = _cpf(cpf, limits.dcp_blocks)
    if reason:
        status = (
            Status.UNSUPPORTED_VARIANT if reason.endswith("ITERATION_LIMIT") else Status.MALFORMED
        )
        return status, reason, ()
    if command in {4, 0x63, 0x64}:
        expected = {4: 0x100, 0x63: 0x0C}.get(command)
        if command == 0x64:
            return (
                (None, "not_present", ())
                if not items
                else (Status.UNSUPPORTED_VARIANT, "INTERFACE_ITEMS_UNSUPPORTED", ())
            )
        if not items:
            return Status.MALFORMED, "LIST_RESPONSE_ITEMS_MISSING", ()
        for kind, value in items:
            if kind != expected:
                return Status.UNSUPPORTED_VARIANT, "LIST_ITEM_TYPE_UNSUPPORTED", ()
            if command == 4 and (len(value) != 20 or value[:2] != b"\x01\x00"):
                return Status.MALFORMED, "LIST_SERVICES_ITEM_INVALID", ()
            if command == 0x63 and (len(value) < 34 or 34 + value[32] != len(value)):
                return Status.MALFORMED, "LIST_IDENTITY_ITEM_INVALID", ()
            if command == 0x63:
                if value[:2] != b"\x01\x00" or value[2:4] != b"\x00\x02":
                    return (
                        Status.UNSUPPORTED_VARIANT,
                        "IDENTITY_VERSION_OR_SOCKET_FAMILY_UNSUPPORTED",
                        (),
                    )
                if value[10:18] != b"\x00" * 8:
                    return Status.MALFORMED, "IDENTITY_SOCKET_PADDING_INVALID", ()
        return None, "not_present", ()
    if len(items) != 2:
        return Status.MALFORMED, "EXPLICIT_CPF_ITEM_COUNT_INVALID", ()
    (address_kind, address), (data_kind, value) = items
    if command == 0x6F:
        if address_kind != 0 or address or data_kind != 0xB2:
            return Status.UNSUPPORTED_VARIANT, "UNCONNECTED_CPF_LAYOUT_UNSUPPORTED", ()
        return _cip(value)
    if address_kind != 0xA1 or len(address) != 4 or data_kind != 0xB1 or len(value) < 2:
        return Status.MALFORMED, "CONNECTED_CPF_LAYOUT_INVALID", ()
    # Connected transport needs session context to establish the application
    # profile. Validate its CPF/sequence envelope and leave its contents opaque.
    return None, "opaque", ()


def decode_enip(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or 44818 not in {view.source_port, view.destination_port}:
        return ()

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            "ethernet_ip",
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
        if len(data) - offset < 24:
            result.append(
                stopped(Status.TRUNCATED, "ENCAPSULATION_HEADER_INCOMPLETE_OR_SEGMENTED", offset)
            )
            break
        command, size = _u16(data, offset), _u16(data, offset + 2)
        if command not in COMMAND_CATEGORIES:
            result.append(
                stopped(Status.UNSUPPORTED_VARIANT, "ENCAPSULATION_COMMAND_UNSUPPORTED", offset)
            )
            break
        if data[offset + 20 : offset + 24] != b"\x00" * 4:
            result.append(
                stopped(Status.UNSUPPORTED_VARIANT, "ENCAPSULATION_OPTIONS_UNSUPPORTED", offset)
            )
            break
        end = offset + 24 + size
        if end > len(data):
            result.append(
                stopped(Status.TRUNCATED, "ENCAPSULATION_DATA_INCOMPLETE_OR_SEGMENTED", offset)
            )
            break
        status = int.from_bytes(data[offset + 8 : offset + 12], "little")
        extra: tuple[tuple[str, HeaderValue], ...]
        if status and size == 0:
            failure, metadata, extra = None, "not_present", ()
        else:
            failure, metadata, extra = _body(command, data[offset + 24 : end], limits)
        if failure is not None:
            result.append(stopped(failure, metadata, offset))
            break
        fields: tuple[tuple[str, HeaderValue], ...] = (
            ("encapsulation_command", command),
            ("encapsulation_status", status),
            ("encapsulation_length", size),
            ("cip_metadata", metadata),
        ) + extra
        result.append(
            record(
                "ethernet_ip",
                "HEADER_STRUCTURE",
                Status.STRUCTURALLY_VALID,
                offset=offset,
                category=COMMAND_CATEGORIES[command],
                fields=fields,
                limitations=_LIMITATIONS,
            )
        )
        offset = end
    return tuple(result)
