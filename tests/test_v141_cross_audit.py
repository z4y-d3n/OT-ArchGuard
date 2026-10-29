"""Independent adversarial review of the other V14-01 decoder implementations.

OPC markers/minimum-body oracles come from OPC Foundation Part6 6.7.2.2.
DNP CRC uses normal polynomial long division, independently of reflected product
implementation, and is anchored to the standard CRC-16/DNP check value 0xEA82.
"""

import json
import struct
from dataclasses import asdict

import pytest

from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS, ProtocolView, Status
from otarchguard.capture.protocols.dnp3 import decode_dnp3
from otarchguard.capture.protocols.iec104 import decode_iec104
from otarchguard.capture.protocols.opcua import decode_opcua


def _ua(kind: bytes, chunk: bytes, body: bytes) -> bytes:
    return kind + chunk + struct.pack("<I", len(body) + 8) + body


def _binary(value: bytes | None) -> bytes:
    return struct.pack("<i", -1 if value is None else len(value)) + (value or b"")


def _normal_crc(data: bytes) -> int:
    register = 0
    for value in data:
        reflected = int(f"{value:08b}"[::-1], 2)
        register ^= reflected << 8
        for _ in range(8):
            register = ((register << 1) ^ (0x3D65 if register & 0x8000 else 0)) & 0xFFFF
    return int(f"{register:016b}"[::-1], 2) ^ 0xFFFF


def _dnp(user: bytes, control: int = 0x44) -> bytes:
    header = b"\x05\x64" + bytes([len(user) + 5, control]) + b"\x01\x00\x02\x00"
    result = header + struct.pack("<H", _normal_crc(header))
    for offset in range(0, len(user), 16):
        block = user[offset : offset + 16]
        result += block + struct.pack("<H", _normal_crc(block))
    return result


@pytest.mark.parametrize("kind", [b"OPN", b"CLO"])
@pytest.mark.parametrize("chunk", [b"C", b"A"])
def test_opc_non_msg_never_accepts_intermediate_or_abort(kind: bytes, chunk: bytes) -> None:
    body = b"\x00" * 4 + _binary(None) * 3 + b"\x00" * 9 if kind == b"OPN" else b"\x00" * 17
    (result,) = decode_opcua(
        ProtocolView(_ua(kind, chunk, body), "tcp", 1, 4840), ENRICHMENT_LIMITS
    )
    assert result.status != Status.STRUCTURALLY_VALID
    assert not result.fields


@pytest.mark.parametrize("kind", [b"MSG", b"CLO", b"OPN"])
def test_opc_header_sequence_without_body_is_incomplete(kind: bytes) -> None:
    body = b"\x00" * 4 + _binary(None) * 3 + b"\x00" * 8 if kind == b"OPN" else b"\x00" * 16
    (result,) = decode_opcua(ProtocolView(_ua(kind, b"F", body), "tcp", 1, 4840), ENRICHMENT_LIMITS)
    assert result.status == Status.MALFORMED
    assert not result.fields


@pytest.mark.parametrize("chunk", [b"C", b"F"])
def test_opc_secure_contents_remain_opaque_even_when_readable(chunk: bytes) -> None:
    secret = b"PASSWORD_PRIVATE_NODEID_ENDPOINT_CERTIFICATE"
    payload = _ua(b"MSG", chunk, b"\x00" * 16 + secret)
    (result,) = decode_opcua(ProtocolView(payload, "tcp", 4840, 1), ENRICHMENT_LIMITS)
    assert result.status == Status.STRUCTURALLY_VALID
    assert result.message_category == "secure_channel_opaque"
    assert dict(result.fields) == {
        "message_type": "MSG",
        "chunk_type": chunk.decode(),
        "message_size": len(payload),
    }
    assert secret.decode() not in json.dumps(asdict(result))


@pytest.mark.parametrize("thumbprint", [b"X", b"X" * 19, b"X" * 21])
def test_opc_thumbprint_has_exact_supported_length(thumbprint: bytes) -> None:
    payload = _ua(b"OPN", b"F", b"\x00" * 4 + _binary(None) * 2 + _binary(thumbprint) + b"\x00" * 9)
    (result,) = decode_opcua(ProtocolView(payload, "tcp", 1, 4840), ENRICHMENT_LIMITS)
    assert result.status != Status.STRUCTURALLY_VALID
    assert not result.fields


def test_opc_asymmetric_lengths_do_not_consume_next_chunk() -> None:
    bad = _ua(b"OPN", b"F", b"\x00" * 4 + struct.pack("<i", 100))
    next_chunk = _ua(b"MSG", b"F", b"\x00" * 17)
    (result,) = decode_opcua(ProtocolView(bad + next_chunk, "tcp", 1, 4840), ENRICHMENT_LIMITS)
    assert result.status == Status.MALFORMED
    assert not result.fields


def test_opc_endpoint_is_discarded_after_hello_envelope_check() -> None:
    endpoint = b"opc.tcp://PRIVATE_TOPOLOGY:4840/PRIVATE_ENDPOINT"
    fixed = struct.pack("<IIIII", 0, 8192, 8192, 0, 0)
    (result,) = decode_opcua(
        ProtocolView(_ua(b"HEL", b"F", fixed + _binary(endpoint)), "tcp", 1, 4840),
        ENRICHMENT_LIMITS,
    )
    assert result.status == Status.STRUCTURALLY_VALID
    assert endpoint.decode() not in json.dumps(asdict(result))


@pytest.mark.parametrize("kind", [0, 2, 44, 47, 99, 104, 255])
def test_iec_unknown_complete_asdu_layout_abstains(kind: int) -> None:
    asdu = bytes([kind, 1, 3, 0, 1, 0]) + b"\x01\x00\x00\x00"
    frame = b"\x68" + bytes([4 + len(asdu)]) + b"\x00" * 4 + asdu
    (result,) = decode_iec104(ProtocolView(frame, "tcp", 1, 2404), ENRICHMENT_LIMITS)
    assert result.status == Status.UNSUPPORTED_VARIANT
    assert not result.fields


@pytest.mark.parametrize("first", [3, 15, 31, 63, 127, 255])
def test_iec_unknown_u_combinations_never_gain_control_type(first: int) -> None:
    frame = b"\x68\x04" + bytes([first, 0, 0, 0])
    (result,) = decode_iec104(ProtocolView(frame, "tcp", 2404, 1), ENRICHMENT_LIMITS)
    assert result.status == Status.UNSUPPORTED_VARIANT
    assert not result.fields


def test_iec_coalesced_valid_control_and_invalid_asdu_keep_exact_offset() -> None:
    valid = bytes.fromhex("680407000000")
    invalid = bytes.fromhex("680a00000000630103000100")
    first, second = decode_iec104(ProtocolView(valid + invalid, "tcp", 1, 2404), ENRICHMENT_LIMITS)
    assert first.status == Status.STRUCTURALLY_VALID
    assert second.status == Status.UNSUPPORTED_VARIANT and second.record_offset == 6
    assert not second.fields


def test_dnp_independent_crc_is_anchored_to_published_check() -> None:
    assert _normal_crc(b"123456789") == 0xEA82


def test_dnp_three_crc_blocks_and_protocol_addresses_only() -> None:
    secret = b"PRIVATE_PROCESS_VALUES_0123456789_PRIVATE"
    frame = _dnp(b"\xc0\xc0\x81\x00\x00" + secret)
    (result,) = decode_dnp3(ProtocolView(frame, "tcp", 20000, 1), ENRICHMENT_LIMITS)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields)["protocol_source"] == 2
    assert dict(result.fields)["protocol_destination"] == 1
    assert dict(result.fields)["application_category"] == "response"
    assert secret.decode() not in json.dumps(asdict(result))


@pytest.mark.parametrize("crc_offset", [8, 9, 26, 27, 44, 45])
def test_dnp_integrity_required_on_every_block(crc_offset: int) -> None:
    frame = bytearray(_dnp(b"\xc0\xc0\x81\x00\x00" + b"x" * 35))
    frame[crc_offset] ^= 1
    (result,) = decode_dnp3(ProtocolView(bytes(frame), "tcp", 1, 20000), ENRICHMENT_LIMITS)
    assert result.status == Status.MALFORMED
    assert not result.fields


@pytest.mark.parametrize(
    ("user", "control", "status"),
    [
        (b"\xc0\xc0\x81\x00\x00", 0xC4, Status.MALFORMED),
        (b"\xc0\xc0\x01\x3c\x01\x06", 0x44, Status.MALFORMED),
        (b"\x80\xc0\x01\x3c\x01\x06", 0xC4, Status.UNSUPPORTED_VARIANT),
        (b"\x40\xc0\x01\x3c\x01\x06", 0xC4, Status.UNSUPPORTED_VARIANT),
        (b"\xc0\xc0\x03", 0xC4, Status.UNSUPPORTED_VARIANT),
        (b"\xc0\xc0\x20", 0xC4, Status.UNSUPPORTED_VARIANT),
    ],
)
def test_dnp_direction_fragmentation_and_unsupported_commands(
    user: bytes, control: int, status: Status
) -> None:
    (result,) = decode_dnp3(ProtocolView(_dnp(user, control), "tcp", 1, 20000), ENRICHMENT_LIMITS)
    assert result.status == status
    assert not result.fields
