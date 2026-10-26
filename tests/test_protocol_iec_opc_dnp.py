"""Independent IEC-104, UA TCP and DNP3 wire fixtures and adversarial oracles.

Fixture builders do not import decoder helpers. DNP CRC uses a different,
non-reflected polynomial computation and a published check vector.
"""

import json
import random
import struct
from collections.abc import Callable
from dataclasses import asdict, replace

import pytest

from otarchguard.capture.protocols.contract import (
    ENRICHMENT_LIMITS,
    EnrichmentLimits,
    EnrichmentRecord,
    ProtocolView,
    Status,
)
from otarchguard.capture.protocols.dnp3 import decode_dnp3
from otarchguard.capture.protocols.iec104 import decode_iec104
from otarchguard.capture.protocols.opcua import decode_opcua

Decoder = Callable[[ProtocolView, EnrichmentLimits], tuple[EnrichmentRecord, ...]]


def _view(data: bytes, port: int, reverse: bool = False) -> ProtocolView:
    return ProtocolView(data, "tcp", port if reverse else 40000, 40000 if reverse else port)


def _iec(control: bytes = b"\x07\0\0\0", asdu: bytes = b"") -> bytes:
    return b"\x68" + bytes([4 + len(asdu)]) + control + asdu


def _asdu(kind: int = 1, objects: bytes = b"\0\0\0\x01", count: int = 1) -> bytes:
    return bytes([kind, count, 3, 0, 1, 0]) + objects


def _ua(kind: bytes = b"HEL", body: bytes | None = None, chunk: bytes = b"F") -> bytes:
    if body is None:
        body = struct.pack("<IIIIIi", 0, 8192, 8192, 0, 0, 0)
    return kind + chunk + struct.pack("<I", len(body) + 8) + body


def _string(value: bytes) -> bytes:
    return struct.pack("<i", len(value)) + value


def _fixture_crc(data: bytes) -> bytes:
    crc = 0
    for value in data:
        reflected = int(f"{value:08b}"[::-1], 2)
        crc ^= reflected << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x3D65 if crc & 0x8000 else 0)) & 65535
    crc = int(f"{crc:016b}"[::-1], 2) ^ 65535
    return struct.pack("<H", crc)


def _dnp(user: bytes = b"", control: int = 0xC0, destination: int = 5, source: int = 100) -> bytes:
    header = b"\x05\x64" + bytes([5 + len(user), control]) + struct.pack("<HH", destination, source)
    result = header + _fixture_crc(header)
    for offset in range(0, len(user), 16):
        block = user[offset : offset + 16]
        result += block + _fixture_crc(block)
    return result


def _one(decoder: Decoder, data: bytes, port: int) -> EnrichmentRecord:
    (result,) = decoder(_view(data, port), ENRICHMENT_LIMITS)
    return result


@pytest.mark.parametrize(
    "code,name",
    [
        (7, "startdt_act"),
        (11, "startdt_con"),
        (19, "stopdt_act"),
        (35, "stopdt_con"),
        (67, "testfr_act"),
        (131, "testfr_con"),
    ],
)
def test_iec_u_functions(code: int, name: str) -> None:
    result = _one(decode_iec104, _iec(bytes([code, 0, 0, 0])), 2404)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields) == {"frame_format": "U", "apdu_length": 6, "u_function": name}


def test_iec_s_and_i_header_fields_only() -> None:
    s = _one(decode_iec104, _iec(b"\x01\0\x02\0"), 2404)
    assert s.status == Status.STRUCTURALLY_VALID
    assert dict(s.fields) == {"frame_format": "S", "apdu_length": 6}
    i = _one(decode_iec104, _iec(b"\0\0\x02\0", _asdu()), 2404)
    assert i.status == Status.STRUCTURALLY_VALID
    assert dict(i.fields) == {"frame_format": "I", "apdu_length": 16, "asdu_type": 1}
    assert i.message_category == "information_transfer"


@pytest.mark.parametrize(
    "kind,width",
    [
        (1, 1),
        (3, 1),
        (9, 3),
        (11, 3),
        (13, 5),
        (30, 8),
        (31, 8),
        (45, 1),
        (46, 1),
        (100, 1),
        (101, 1),
        (102, 0),
        (103, 7),
    ],
)
def test_iec_supported_complete_asdu_envelopes(kind: int, width: int) -> None:
    message = _iec(b"\0" * 4, _asdu(kind, b"\x01\x02\x03" + b"\0" * width))
    assert _one(decode_iec104, message, 2404).status == Status.STRUCTURALLY_VALID


def test_iec_sequence_multiple_objects_and_nonsequence() -> None:
    for count, objects in [(0x82, b"\0\0\0\x01\x00"), (2, b"\0\0\0\x01" * 2)]:
        result = _one(decode_iec104, _iec(b"\0" * 4, _asdu(1, objects, count)), 2404)
        assert result.status == Status.STRUCTURALLY_VALID


@pytest.mark.parametrize(
    "message,status,reason",
    [
        (b"", Status.PORT_HINT, "NO_APPLICATION_BYTES"),
        (b"HTTP/1.1", Status.PORT_HINT, "APCI_START_NOT_RECOGNIZED"),
        (b"\x68", Status.TRUNCATED, "APCI_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (b"\x68\x03\0\0\0", Status.MALFORMED, "APDU_LENGTH_INVALID"),
        (b"\x68\xfe" + b"\0" * 254, Status.MALFORMED, "APDU_LENGTH_INVALID"),
        (_iec()[:-1], Status.TRUNCATED, "APDU_INCOMPLETE_OR_SEGMENTED"),
        (_iec(b"\0\0\1\0", _asdu()), Status.MALFORMED, "I_CONTROL_RESERVED_BIT"),
        (_iec(b"\0" * 4), Status.MALFORMED, "ASDU_HEADER_INCOMPLETE"),
        (_iec(b"\0" * 4, _asdu(255)), Status.UNSUPPORTED_VARIANT, "ASDU_LAYOUT_NOT_SUPPORTED"),
        (_iec(b"\0" * 4, _asdu(count=0)), Status.MALFORMED, "ASDU_OBJECT_COUNT_ZERO"),
        (
            _iec(b"\0" * 4, _asdu(objects=b"\0" * 3)),
            Status.MALFORMED,
            "ASDU_OBJECT_ENVELOPE_INVALID",
        ),
        (_iec(b"\x05\0\0\0"), Status.MALFORMED, "S_CONTROL_OR_LENGTH_INVALID"),
        (_iec(b"\x01\0\x01\0"), Status.MALFORMED, "S_CONTROL_OR_LENGTH_INVALID"),
        (_iec(b"\x07\0\0\x01"), Status.MALFORMED, "U_CONTROL_OR_LENGTH_INVALID"),
        (_iec(b"\x03\0\0\0"), Status.UNSUPPORTED_VARIANT, "U_FUNCTION_NOT_SUPPORTED"),
        (_iec(b"\x0f\0\0\0"), Status.UNSUPPORTED_VARIANT, "U_FUNCTION_NOT_SUPPORTED"),
        (
            _iec(b"\0" * 4, _asdu(100, b"\0" * 4, 0x81)),
            Status.UNSUPPORTED_VARIANT,
            "ASDU_SEQUENCE_NOT_SUPPORTED",
        ),
    ],
)
def test_iec_abstentions(message: bytes, status: Status, reason: str) -> None:
    result = _one(decode_iec104, message, 2404)
    assert (result.status, result.reason) == (status, reason)
    assert result.fields == () and result.message_category is None


@pytest.mark.parametrize(
    "kind,body,category",
    [
        (
            b"HEL",
            struct.pack("<IIIII", 0, 8192, 8192, 0, 0) + _string(b"opc.tcp://private"),
            "connection_handshake",
        ),
        (b"ACK", struct.pack("<IIIII", 0, 8192, 8192, 0, 0), "connection_handshake"),
        (b"ERR", struct.pack("<I", 0x80000000) + _string(b"sensitive reason"), "connection_error"),
        (
            b"RHE",
            _string(b"private:server") + _string(b"opc.tcp://private"),
            "connection_handshake",
        ),
        (
            b"OPN",
            b"\0" * 4
            + _string(b"security-policy")
            + _string(b"certificate")
            + _string(b"t" * 20)
            + b"opaque-sequence",
            "secure_channel_opaque",
        ),
        (b"MSG", b"\x01" * 16 + b"opaque-secret-service", "secure_channel_opaque"),
        (b"CLO", b"\x01" * 16 + b"opaque-secret-service", "secure_channel_opaque"),
    ],
)
def test_opcua_outer_messages_never_export_contents(
    kind: bytes, body: bytes, category: str
) -> None:
    message = _ua(kind, body)
    result = _one(decode_opcua, message, 4840)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields) == {
        "message_type": kind.decode(),
        "chunk_type": "F",
        "message_size": len(message),
    }
    assert result.message_category == category
    serialized = json.dumps(asdict(result))
    assert "private" not in serialized and "sensitive reason" not in serialized
    assert "opaque-secret-service" not in serialized


@pytest.mark.parametrize(
    "message,status,reason",
    [
        (b"", Status.PORT_HINT, "NO_APPLICATION_BYTES"),
        (b"HTTP/1.1", Status.PORT_HINT, "MESSAGE_TYPE_NOT_RECOGNIZED"),
        (b"HE", Status.TRUNCATED, "MESSAGE_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (b"HEL", Status.TRUNCATED, "MESSAGE_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (_ua(chunk=b"X"), Status.UNSUPPORTED_VARIANT, "CHUNK_MARKER_NOT_SUPPORTED"),
        (_ua(chunk=b"C"), Status.MALFORMED, "HANDSHAKE_CHUNK_MARKER_INVALID"),
        (_ua(b"MSG", b"\0" * 16, b"A"), Status.UNSUPPORTED_VARIANT, "ABORT_CHUNK_NOT_SUPPORTED"),
        (b"HELF\x07\0\0\0", Status.MALFORMED, "MESSAGE_SIZE_INVALID"),
        (b"HELF\xff\xff\xff\xff", Status.UNSUPPORTED_VARIANT, "MESSAGE_SIZE_LIMIT"),
        (_ua()[:-1], Status.TRUNCATED, "MESSAGE_INCOMPLETE_OR_SEGMENTED"),
        (_ua(b"HEL", b"\0" * 19), Status.MALFORMED, "HANDSHAKE_FIXED_HEADER_INCOMPLETE"),
        (_ua(b"ACK", b"\0" * 21), Status.MALFORMED, "HANDSHAKE_LAYOUT_INVALID"),
        (
            _ua(b"ACK", b"\x01" + b"\0" * 19),
            Status.UNSUPPORTED_VARIANT,
            "UACP_VERSION_NOT_SUPPORTED",
        ),
        (
            _ua(b"HEL", b"\0" * 20 + struct.pack("<i", -2)),
            Status.MALFORMED,
            "HANDSHAKE_LAYOUT_INVALID",
        ),
        (
            _ua(b"HEL", b"\0" * 20 + _string(b"a") + b"extra"),
            Status.MALFORMED,
            "HANDSHAKE_LAYOUT_INVALID",
        ),
        (
            _ua(b"ERR", b"\0" * 4 + struct.pack("<i", 9000)),
            Status.MALFORMED,
            "ERROR_LAYOUT_INVALID",
        ),
        (_ua(b"RHE", _string(b"a")), Status.MALFORMED, "REVERSE_HELLO_LAYOUT_INVALID"),
        (
            _ua(b"OPN", b"\0" * 4 + struct.pack("<i", -2)),
            Status.MALFORMED,
            "ASYMMETRIC_HEADER_LAYOUT_INVALID",
        ),
        (_ua(b"OPN", b"\0" * 16), Status.MALFORMED, "SECURE_CHUNK_TOO_SHORT"),
        (_ua(b"MSG", b"\0" * 15), Status.MALFORMED, "SECURE_CHUNK_TOO_SHORT"),
        (_ua(b"CLO", b"\0" * 15), Status.MALFORMED, "SECURE_CHUNK_TOO_SHORT"),
    ],
)
def test_opcua_abstentions(message: bytes, status: Status, reason: str) -> None:
    result = _one(decode_opcua, message, 4840)
    assert (result.status, result.reason) == (status, reason)
    assert result.fields == () and result.message_category is None


@pytest.mark.parametrize("kind", [b"MSG"])
def test_opcua_continuation_is_only_outer_framing(kind: bytes) -> None:
    body = b"\0" * 17
    result = _one(decode_opcua, _ua(kind, body, b"C"), 4840)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields)["chunk_type"] == "C"
    assert any("do not prove a complete application" in t for t in result.limitations)


@pytest.mark.parametrize("kind", [b"OPN", b"CLO"])
def test_opcua_secure_types_other_than_msg_cannot_continue(kind: bytes) -> None:
    result = _one(decode_opcua, _ua(kind, b"\0" * 25, b"C"), 4840)
    assert result.status == Status.MALFORMED
    assert result.reason == "SECURE_CHUNK_MARKER_INVALID"


@pytest.mark.parametrize(
    "body",
    [
        b"\0" * 4 + _string(b"x" * 256) + _string(b"") + _string(b"") + b"\0" * 9,
        b"\0" * 4 + _string(b"") + _string(b"") + _string(b"x" * 19) + b"\0" * 9,
        b"\0" * 4 + _string(b"") + _string(b"") + _string(b"x" * 21) + b"\0" * 9,
    ],
)
def test_opcua_asymmetric_header_mandatory_length_constraints(body: bytes) -> None:
    result = _one(decode_opcua, _ua(b"OPN", body), 4840)
    assert result.status == Status.MALFORMED
    assert result.reason == "ASYMMETRIC_HEADER_LAYOUT_INVALID"


@pytest.mark.parametrize(
    "kind,body", [(b"MSG", b"\0" * 16), (b"CLO", b"\0" * 16), (b"OPN", b"\0" * 24)]
)
def test_opcua_sequence_without_any_body_is_incomplete_layout(kind: bytes, body: bytes) -> None:
    result = _one(decode_opcua, _ua(kind, body), 4840)
    assert result.status == Status.MALFORMED
    assert result.reason == "SECURE_CHUNK_TOO_SHORT"


def test_iec_reserved_cause_is_unsupported() -> None:
    asdu = bytearray(_asdu())
    asdu[2] = 0
    result = _one(decode_iec104, _iec(b"\0" * 4, bytes(asdu)), 2404)
    assert result.status == Status.UNSUPPORTED_VARIANT
    assert result.reason == "ASDU_CAUSE_NOT_SUPPORTED"


def test_independent_dnp_crc_known_check_vector() -> None:
    assert _fixture_crc(b"123456789") == b"\x82\xea"
    # Widely documented reset-link frame CRC, independently fixed bytes.
    assert _dnp(destination=1, source=1024) == bytes.fromhex("056405c001000004e921")
    assert (
        _one(decode_dnp3, bytes.fromhex("056405c001000004e921"), 20000).status
        == Status.STRUCTURALLY_VALID
    )


@pytest.mark.parametrize("control", [0xC0, 0xC1, 0xD2, 0xC9, 0, 1, 11, 14, 15, 0x90])
def test_dnp_link_management(control: int) -> None:
    result = _one(decode_dnp3, _dnp(control=control), 20000)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields) == {
        "link_status": "crc_valid",
        "link_primary": bool(control & 64),
        "link_function": control & 15,
        "protocol_source": 100,
        "protocol_destination": 5,
        "frame_length": 10,
    }
    assert result.message_category == "link_management"


@pytest.mark.parametrize(
    "function,control,body,category",
    [
        (0, 0xC4, b"", "confirm"),
        (1, 0xC4, b"\x3c\x01\x06", "read_type"),
        (13, 0xC4, b"", "cold_restart_type"),
        (14, 0xC4, b"", "warm_restart_type"),
        (129, 0x44, b"\0\0", "response"),
        (130, 0x44, b"\0\0", "unsolicited_response"),
    ],
)
def test_dnp_complete_application_header(
    function: int, control: int, body: bytes, category: str
) -> None:
    app_control = 0xD0 if function == 130 else 0xC0
    message = _dnp(b"\xc0" + bytes([app_control, function]) + body, control)
    result = _one(decode_dnp3, message, 20000)
    assert result.status == Status.STRUCTURALLY_VALID
    fields = dict(result.fields)
    assert fields["application_function"] == function and fields["application_category"] == category
    assert fields["frame_length"] == len(message)


def test_dnp_crc_every_block_and_last_partial_block() -> None:
    user = b"\xc0\xc0\x81\0\0" + b"secret-points" * 15
    message = _dnp(user, 0x44)
    positive = _one(decode_dnp3, message, 20000)
    assert positive.status == Status.STRUCTURALLY_VALID
    assert "secret-points" not in json.dumps(asdict(positive))
    for offset in range(8, len(message)):
        changed = bytearray(message)
        changed[offset] ^= 0x01
        result = _one(decode_dnp3, bytes(changed), 20000)
        assert result.status == Status.MALFORMED
        assert result.reason in {"LINK_HEADER_CRC_INVALID", "USER_DATA_CRC_INVALID"}


@pytest.mark.parametrize(
    "message,status,reason",
    [
        (b"", Status.PORT_HINT, "NO_APPLICATION_BYTES"),
        (b"\x05", Status.TRUNCATED, "LINK_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (b"HTTP/1.1", Status.PORT_HINT, "LINK_START_NOT_RECOGNIZED"),
        (b"\x05\x64", Status.TRUNCATED, "LINK_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (b"\x05\x64\x04" + b"\0" * 7, Status.MALFORMED, "LINK_LENGTH_INVALID"),
        (
            _dnp(b"\xc0\xc0\x01\x3c\1\6", 0xC4)[:-1],
            Status.TRUNCATED,
            "LINK_FRAME_INCOMPLETE_OR_SEGMENTED",
        ),
        (_dnp(control=0xC5), Status.UNSUPPORTED_VARIANT, "LINK_FUNCTION_NOT_SUPPORTED"),
        (_dnp(control=0x20), Status.MALFORMED, "LINK_CONTROL_INVALID"),
        (_dnp(control=0xD0), Status.MALFORMED, "LINK_CONTROL_INVALID"),
        (_dnp(control=0xC2), Status.MALFORMED, "LINK_CONTROL_INVALID"),
        (_dnp(control=0xC4), Status.MALFORMED, "LINK_FUNCTION_LENGTH_INVALID"),
        (
            _dnp(b"\x80\xc0\0", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "TRANSPORT_FRAGMENTATION_NOT_SUPPORTED",
        ),
        (
            _dnp(b"\x40\xc0\0", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "TRANSPORT_FRAGMENTATION_NOT_SUPPORTED",
        ),
        (_dnp(b"\xc0", 0xC4), Status.MALFORMED, "APPLICATION_HEADER_INCOMPLETE"),
        (
            _dnp(b"\xc0\x80\0", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "APPLICATION_FRAGMENTATION_NOT_SUPPORTED",
        ),
        (
            _dnp(b"\xc0\xc0\xff", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "APPLICATION_FUNCTION_NOT_SUPPORTED",
        ),
        (_dnp(b"\xc0\xc0\x81\0\0", 0xC4), Status.MALFORMED, "APPLICATION_RESPONSE_HEADER_INVALID"),
        (_dnp(b"\xc0\xc0\x81", 0x44), Status.MALFORMED, "APPLICATION_RESPONSE_HEADER_INVALID"),
        (_dnp(b"\xc0\xc0\x82\0\0", 0x44), Status.MALFORMED, "APPLICATION_RESPONSE_HEADER_INVALID"),
        (_dnp(b"\xc0\xe0\0", 0xC4), Status.MALFORMED, "APPLICATION_CONFIRM_HEADER_INVALID"),
        (_dnp(b"\xc0\xc0\1\x3c\1\6", 0x44), Status.MALFORMED, "APPLICATION_REQUEST_HEADER_INVALID"),
        (
            _dnp(b"\xc0\xc0\x0d\0", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "RESTART_OBJECTS_NOT_SUPPORTED",
        ),
        (_dnp(b"\xc0\xc0\1", 0xC4), Status.MALFORMED, "READ_OBJECT_HEADER_INVALID"),
        (
            _dnp(b"\xc0\xc0\1\x01\1\6", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "READ_OBJECT_LAYOUT_NOT_SUPPORTED",
        ),
        (
            _dnp(b"\xc0\xc0\3", 0xC4),
            Status.UNSUPPORTED_VARIANT,
            "APPLICATION_FUNCTION_NOT_SUPPORTED",
        ),
    ],
)
def test_dnp_abstentions(message: bytes, status: Status, reason: str) -> None:
    result = _one(decode_dnp3, message, 20000)
    assert (result.status, result.reason) == (status, reason)
    assert result.fields == () and result.message_category is None


CASES: list[tuple[Decoder, int, bytes]] = [
    (decode_iec104, 2404, _iec()),
    (decode_opcua, 4840, _ua()),
    (decode_dnp3, 20000, _dnp()),
]


@pytest.mark.parametrize("decoder,port,message", CASES)
def test_standard_ports_and_transport_only(decoder: Decoder, port: int, message: bytes) -> None:
    assert decoder(_view(message, 12345), ENRICHMENT_LIMITS) == ()
    assert decoder(ProtocolView(message, "ethernet", ethertype=0x8892), ENRICHMENT_LIMITS) == ()
    forward = decoder(_view(message, port), ENRICHMENT_LIMITS)
    assert forward == decoder(_view(message, port, True), ENRICHMENT_LIMITS)
    assert forward[0].status == Status.STRUCTURALLY_VALID


@pytest.mark.parametrize("decoder,port,message", CASES)
def test_multiple_frames_and_record_budget(decoder: Decoder, port: int, message: bytes) -> None:
    results = decoder(_view(message * 3, port), ENRICHMENT_LIMITS)
    assert len(results) == 3
    assert [r.record_offset for r in results] == [0, len(message), 2 * len(message)]
    limited = decoder(_view(message * 3, port), replace(ENRICHMENT_LIMITS, records_per_packet=2))
    assert len(limited) == 2 and limited[0].status == Status.STRUCTURALLY_VALID
    assert limited[-1].reason == "RECORD_ITERATION_LIMIT" and not limited[-1].fields


@pytest.mark.parametrize("decoder,port,message", CASES)
def test_every_split_prefix_abstains(decoder: Decoder, port: int, message: bytes) -> None:
    for end in range(len(message)):
        first = decoder(_view(message[:end], port), ENRICHMENT_LIMITS)
        assert all(r.status != Status.STRUCTURALLY_VALID for r in first)


@pytest.mark.parametrize("decoder,port,message", CASES)
def test_view_ceiling_and_determinism(decoder: Decoder, port: int, message: bytes) -> None:
    result = decoder(_view(message, port), replace(ENRICHMENT_LIMITS, view_bytes=len(message) - 1))
    assert result[0].reason == "VIEW_BYTE_LIMIT"
    assert decoder(_view(message, port), ENRICHMENT_LIMITS) == decoder(
        _view(message, port), ENRICHMENT_LIMITS
    )


@pytest.mark.parametrize("decoder,port,message", CASES)
def test_seeded_hostile_mutations_are_finite_and_payload_free(
    decoder: Decoder, port: int, message: bytes
) -> None:
    rng = random.Random(20261026)
    for _ in range(400):
        candidate = bytearray(message)
        for _ in range(rng.randrange(1, 5)):
            candidate[rng.randrange(len(candidate))] = rng.randrange(256)
        results = decoder(_view(bytes(candidate), port), ENRICHMENT_LIMITS)
        assert 1 <= len(results) <= ENRICHMENT_LIMITS.records_per_packet
        for item in results:
            assert all(type(value) in {int, str, bool} for _, value in item.fields)
            if item.status != Status.STRUCTURALLY_VALID:
                assert item.fields == () and item.message_category is None
            assert len(json.dumps(asdict(item))) < 2500
