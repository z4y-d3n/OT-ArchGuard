"""UA TCP outer framing only, from OPC Foundation Part 6 §§7.1.2 and 6.7.2.

Secure-channel bodies remain opaque, including apparently readable MSG bodies.
Length-prefixed strings are skipped without decoding or retaining their values.
"""

from otarchguard.capture.protocols.contract import (
    EnrichmentLimits,
    EnrichmentRecord,
    ProtocolView,
    Status,
    record,
)

_TYPES = {b"HEL", b"ACK", b"ERR", b"RHE", b"OPN", b"MSG", b"CLO"}
_LIMITATIONS = (
    "UA TCP outer framing only; secure-channel contents remain opaque and unassessed.",
    "No URLs, certificates, identities, NodeIds, service contents or secrets are retained.",
    "Complete chunks do not prove a complete application message, authorization or execution.",
    "No stream reassembly, security-policy assessment or cryptographic validation.",
)


def _string_end(data: bytes, offset: int, maximum: int) -> int | None:
    if offset + 4 > len(data):
        return None
    length = int.from_bytes(data[offset : offset + 4], "little", signed=True)
    if length < -1 or length > maximum:
        return None
    end = offset + 4 + max(length, 0)
    return end if end <= len(data) else None


def _shape(message: bytes, kind: bytes) -> tuple[Status | None, str]:
    size = len(message)
    if kind in {b"HEL", b"ACK"}:
        if size < 28:
            return Status.MALFORMED, "HANDSHAKE_FIXED_HEADER_INCOMPLETE"
        if int.from_bytes(message[8:12], "little") != 0:
            return Status.UNSUPPORTED_VARIANT, "UACP_VERSION_NOT_SUPPORTED"
        if kind == b"ACK":
            valid = size == 28
        else:
            valid = _string_end(message, 28, 4096) == size
        return (None, "") if valid else (Status.MALFORMED, "HANDSHAKE_LAYOUT_INVALID")
    if kind == b"ERR":
        valid = size >= 16 and _string_end(message, 12, 4096) == size
        return (None, "") if valid else (Status.MALFORMED, "ERROR_LAYOUT_INVALID")
    if kind == b"RHE":
        end = _string_end(message, 8, 4096)
        valid = end is not None and _string_end(message, end, 4096) == size
        return (None, "") if valid else (Status.MALFORMED, "REVERSE_HELLO_LAYOUT_INVALID")
    if kind in {b"MSG", b"CLO"}:
        # SecureChannelId, symmetric token header and at least a sequence header.
        # The latter can be encrypted: it is never interpreted or authenticated.
        return (None, "") if size >= 25 else (Status.MALFORMED, "SECURE_CHUNK_TOO_SHORT")
    # OPN has the asymmetric header: policy URI, sender certificate and receiver
    # certificate thumbprint. Only their bounded length envelopes are inspected.
    end = 12
    for maximum in (255, len(message), 20):
        if maximum == 20 and end + 4 <= size:
            thumbprint_length = int.from_bytes(message[end : end + 4], "little", signed=True)
            if thumbprint_length not in {-1, 0, 20}:
                return Status.MALFORMED, "ASYMMETRIC_HEADER_LAYOUT_INVALID"
        next_end = _string_end(message, end, maximum)
        if next_end is None:
            return Status.MALFORMED, "ASYMMETRIC_HEADER_LAYOUT_INVALID"
        end = next_end
    return (None, "") if end + 9 <= size else (Status.MALFORMED, "SECURE_CHUNK_TOO_SHORT")


def decode_opcua(view: ProtocolView, limits: EnrichmentLimits) -> tuple[EnrichmentRecord, ...]:
    if view.transport != "tcp" or 4840 not in {view.source_port, view.destination_port}:
        return ()

    def stopped(status: Status, reason: str, offset: int = 0) -> EnrichmentRecord:
        return record(
            "opcua_binary",
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
        kind = rest[:3]
        status: Status | None
        if len(rest) < 3:
            status, reason = Status.TRUNCATED, "MESSAGE_HEADER_INCOMPLETE_OR_SEGMENTED"
        elif kind not in _TYPES:
            status, reason = Status.PORT_HINT, "MESSAGE_TYPE_NOT_RECOGNIZED"
        elif len(rest) < 8:
            status, reason = Status.TRUNCATED, "MESSAGE_HEADER_INCOMPLETE_OR_SEGMENTED"
        elif rest[3] not in b"FCA":
            status, reason = Status.UNSUPPORTED_VARIANT, "CHUNK_MARKER_NOT_SUPPORTED"
        elif kind in {b"HEL", b"ACK", b"ERR", b"RHE"} and rest[3] != ord("F"):
            status, reason = Status.MALFORMED, "HANDSHAKE_CHUNK_MARKER_INVALID"
        elif rest[3] == ord("A"):
            status, reason = Status.UNSUPPORTED_VARIANT, "ABORT_CHUNK_NOT_SUPPORTED"
        elif kind in {b"OPN", b"CLO"} and rest[3] != ord("F"):
            status, reason = Status.MALFORMED, "SECURE_CHUNK_MARKER_INVALID"
        else:
            size = int.from_bytes(rest[4:8], "little")
            if size < 8:
                status, reason = Status.MALFORMED, "MESSAGE_SIZE_INVALID"
            elif size > limits.view_bytes:
                status, reason = Status.UNSUPPORTED_VARIANT, "MESSAGE_SIZE_LIMIT"
            elif size > len(rest):
                status, reason = Status.TRUNCATED, "MESSAGE_INCOMPLETE_OR_SEGMENTED"
            else:
                status, reason = _shape(rest[:size], kind)
                if status is None:
                    category = (
                        "connection_error"
                        if kind == b"ERR"
                        else "connection_handshake"
                        if kind in {b"HEL", b"ACK", b"RHE"}
                        else "secure_channel_opaque"
                    )
                    results.append(
                        record(
                            "opcua_binary",
                            "HEADER_STRUCTURE",
                            Status.STRUCTURALLY_VALID,
                            offset=offset,
                            category=category,
                            fields=(
                                ("message_type", kind.decode("ascii")),
                                ("chunk_type", chr(rest[3])),
                                ("message_size", size),
                            ),
                            limitations=_LIMITATIONS,
                        )
                    )
                    offset += size
                    continue
        assert status is not None
        results.append(stopped(status, reason, offset))
        break
    return tuple(results)
