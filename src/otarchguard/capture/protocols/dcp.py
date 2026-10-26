"""PROFINET DCP frame/service header and bounded selector/TLV framing.

Wire references: Wireshark PROFINET FrameID constants and DCP dissector;
no upstream implementation is copied. Only service metadata is exposed.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    ProtocolView,
    Status,
    record,
)

_LIMITATIONS = (
    "DCP selectors/block framing only; names, addresses and configuration values are not retained.",
    "Observed service metadata proves neither ownership nor successful configuration.",
)
DCP_FRAME_IDS = frozenset({0xFEFC, 0xFEFD, 0xFEFE, 0xFEFF})


def decode_dcp(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "ethernet" or view.ethertype != 0x8892:
        return ()

    def stopped(status: Status, reason: str) -> tuple[EnrichmentRecord, ...]:
        return (
            record("profinet_dcp", "ETHERTYPE", status, reason=reason, limitations=_LIMITATIONS),
        )

    data = view.data
    if len(data) < 2:
        return ()
    frame = int.from_bytes(data[:2], "big")
    if frame not in DCP_FRAME_IDS:
        return ()
    if len(data) > limits.view_bytes:
        return stopped(Status.UNSUPPORTED_VARIANT, "VIEW_BYTE_LIMIT")
    if frame == 0xFEFC:
        return stopped(Status.UNSUPPORTED_VARIANT, "DCP_HELLO_NOT_SUPPORTED")
    if len(data) < 12:
        return stopped(Status.TRUNCATED, "DCP_HEADER_TRUNCATED")
    service, kind = data[2], data[3]
    if service not in {3, 4, 5} or kind not in {0, 1, 5}:
        return stopped(Status.UNSUPPORTED_VARIANT, "DCP_SERVICE_NOT_SUPPORTED")
    if not (
        (frame == 0xFEFD and service in {3, 4})
        or (frame == 0xFEFE and service == 5 and kind == 0)
        or (frame == 0xFEFF and service == 5 and kind in {1, 5})
    ):
        return stopped(Status.MALFORMED, "DCP_FRAME_SERVICE_MISMATCH")
    if not (service == 5 and kind == 0) and data[8:10] != b"\x00\x00":
        return stopped(Status.MALFORMED, "DCP_RESERVED_FIELD_NONZERO")
    length = int.from_bytes(data[10:12], "big")
    end = 12 + length
    if end > len(data):
        return stopped(Status.TRUNCATED, "DCP_DATA_TRUNCATED")
    if length % 2:
        return stopped(Status.MALFORMED, "DCP_DATA_ALIGNMENT_INVALID")
    # Captured Ethernet minimum-size padding is outside DCPDataLength.
    if len(data) > max(46, end):
        return stopped(Status.UNSUPPORTED_VARIANT, "DCP_TRAILING_BYTES_OUTSIDE_PADDING")
    position, blocks = 12, 0
    while position < end:
        blocks += 1
        if blocks > limits.dcp_blocks:
            return stopped(Status.UNSUPPORTED_VARIANT, "DCP_BLOCK_ITERATION_LIMIT")
        if service == 3 and kind == 0:
            position += 2  # Get request selectors have no TLV length.
            continue
        if end - position < 4:
            return stopped(Status.MALFORMED, "DCP_BLOCK_HEADER_INVALID")
        size = int.from_bytes(data[position + 2 : position + 4], "big")
        position += 4 + size + size % 2
        if position > end:
            return stopped(Status.MALFORMED, "DCP_BLOCK_LENGTH_INVALID")
        if (kind == 1 or service == 4) and size < 2:
            return stopped(Status.MALFORMED, "DCP_BLOCK_INFO_MISSING")
    if not length and kind != 5:
        return stopped(Status.UNSUPPORTED_VARIANT, "DCP_EMPTY_DATA_NOT_SUPPORTED")
    return (
        record(
            "profinet_dcp",
            "HEADER_STRUCTURE",
            Status.STRUCTURALLY_VALID,
            category={3: "get", 4: "set", 5: "identify"}[service],
            fields=(
                ("frame_id", frame),
                ("service_id", service),
                ("service_type", kind),
                ("data_length", length),
                ("blocks", blocks),
            ),
            limitations=_LIMITATIONS,
        ),
    )
